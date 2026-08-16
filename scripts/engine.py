"""Phase 2 engine — weekly rotation backtest under the FROZEN pre-registration.

Every constant comes from prereg.py (imported, never redefined). Basis notes,
stated once and used everywhere:

- WEEKLY Friday-close basis throughout: returns are Friday-to-Friday on USD
  closes, Sharpe is weekly mean/sd x sqrt(52), MaxDD on the weekly equity line
  (intraweek drawdown is understated; identical for every comparator).
- Signal read on the PREVIOUS US session (Thursday), executed at the Friday
  close — the bte get_loc(rd)-1 convention. Asia closes dated the same calendar
  day occur BEFORE the US close, so date-level alignment carries no look-ahead.
- Costs: fees = (FEE_RT_BPS/2) bp per unit |dw| at each rebalance x stress
  multiple; funding = band x 7/365 x invested fraction, charged weekly;
  dividends = holding-weighted trailing yield x 7/365, charged weekly (perps
  are price-only while the price panel is total-return).
- Under-fill: if fewer than K names survive floor + cluster cap, each selected
  name still weighs 1/K and the remainder sits in cash (the sleeve-B cash-floor
  convention).
- Python datetime/pandas throughout; months are 1-indexed.

Run: python scripts/engine.py -> data/phase2_results.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prereg  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PANEL_PATH = PROJECT_ROOT / "data" / "underlyings.parquet"
MAP_PATH = PROJECT_ROOT / prereg.UNIVERSE_MAP
OUT_PATH = PROJECT_ROOT / "data" / "phase2_results.json"

US_ANCHOR = "AAPL"   # defines the US trading calendar grid


# ---------------------------------------------------------------------------
# Pure functions (unit-tested in tests/test_engine.py)
# ---------------------------------------------------------------------------

def normalise_yield(raw) -> float:
    """yfinance dividendYield arrives in percent in current versions (0.52 =
    0.52%) but historically as a fraction. Values above 0.15 are read as
    percent; the result is capped at 10%/yr as a sanity bound."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return 0.0
    v = float(raw)
    if v > 0.15:
        v = v / 100.0
    return min(max(v, 0.0), 0.10)


def to_usd(base: str, local: pd.Series, region: str, fx_krw: pd.Series,
           fx_hkd: pd.Series) -> pd.Series:
    """USD return series per prereg section 4. Quanto bases keep the LOCAL
    series (their perp P&L is the local-currency return). KR/HK divide by the
    USD/local rate; everything else is already USD."""
    if base in prereg.QUANTO_BASES:
        return local
    if region == "KR":
        return local / fx_krw.reindex(local.index).ffill()
    if region == "HK":
        return local / fx_hkd.reindex(local.index).ffill()
    return local


def weekly_grid(us_index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last US session of each ISO week (the Friday close, or Thursday on a
    Friday holiday). Built from the anchor's own trading days, never from
    hand-computed weekday arithmetic."""
    s = pd.Series(us_index, index=us_index)
    return pd.DatetimeIndex(s.groupby(us_index.to_period("W")).max().values)


def select_names(sig_row: pd.Series, eligible: pd.Series, clusters: dict,
                 k: int, cluster_cap, floor: float, gate: float):
    """One rebalance decision. Returns (picks, diagnostics) where picks is a
    list of names (possibly shorter than k) or None when the sleeve is gated
    to cash. Deterministic: ties broken by signal then name."""
    elig_names = [n for n in sig_row.index if eligible[n] and not np.isnan(sig_row[n])]
    if not elig_names:
        return None, {"n_eligible": 0, "breadth": 0.0}
    above = [n for n in elig_names if sig_row[n] > floor]
    breadth = len(above) / len(elig_names)
    if breadth < gate:
        return None, {"n_eligible": len(elig_names), "breadth": breadth}
    ranked = sorted(above, key=lambda n: (-sig_row[n], n))
    picks, counts = [], {}
    for n in ranked:
        c = clusters.get(n, "unclassified")
        if cluster_cap is not None and counts.get(c, 0) >= cluster_cap:
            continue
        picks.append(n)
        counts[c] = counts.get(c, 0) + 1
        if len(picks) == k:
            break
    return picks, {"n_eligible": len(elig_names), "breadth": breadth,
                   "n_above_floor": len(above)}


def turnover(prev_w: dict, new_w: dict) -> float:
    """Sum of |dw| across names (both sides of every switch)."""
    names = set(prev_w) | set(new_w)
    return float(sum(abs(new_w.get(n, 0.0) - prev_w.get(n, 0.0)) for n in names))


def stats_from_weekly(rets: pd.Series) -> dict:
    eq = (1.0 + rets).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min()) if len(eq) else 0.0
    mu, sd = rets.mean(), rets.std()
    years = len(rets) / 52.0
    return {
        "sharpe": round(float(mu / sd * np.sqrt(52)) if sd > 0 else 0.0, 3),
        "cagr": round(float(eq.iloc[-1] ** (1 / years) - 1.0) if years > 0 else 0.0, 4),
        "total_return": round(float(eq.iloc[-1] - 1.0), 4),
        "max_dd": round(dd, 4),
        "n_weeks": int(len(rets)),
    }


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------

def load_inputs():
    panel = pd.read_parquet(PANEL_PATH)
    rows = json.loads(MAP_PATH.read_text(encoding="utf-8"))["rows"]
    fx_krw, fx_hkd = panel.get("KRW=X"), panel.get("HKD=X")

    bases, usd, local, clusters, yields = [], {}, {}, {}, {}
    for base, e in sorted(rows.items()):
        if e["status"] != "verified" or e["levered_etp"] or base in prereg.EXPLICIT_DROPS:
            continue
        cand = e["candidate"]
        if cand not in panel.columns:
            continue
        ser = panel[cand].dropna()
        if ser.empty:
            continue
        bases.append(base)
        local[base] = ser
        usd[base] = to_usd(base, ser, e.get("region", "US"), fx_krw, fx_hkd)
        clusters[base] = e.get("cluster", "unclassified")
        yields[base] = normalise_yield(e.get("dividend_yield_raw"))

    us_index = panel[US_ANCHOR].dropna().index
    us_index = us_index[us_index >= pd.Timestamp("2016-01-01")]

    usd_px = pd.DataFrame(usd).reindex(us_index)
    local_px = pd.DataFrame(local).reindex(us_index)
    obs_count = local_px.notna().cumsum()
    # Freshness: sessions since the last genuine observation on the US grid,
    # vectorised — forward-fill an index marker and difference.
    marker = pd.DataFrame(
        np.where(local_px.notna(), np.arange(len(us_index))[:, None], np.nan),
        index=us_index, columns=local_px.columns).ffill()
    staleness = pd.DataFrame(
        np.arange(len(us_index))[:, None] - marker.values,
        index=us_index, columns=local_px.columns)

    usd_ff = usd_px.ffill()
    local_ff = local_px.ffill()
    ma = local_ff.rolling(prereg.MA_WINDOW, min_periods=prereg.MA_WINDOW).mean()
    signal = local_ff / ma - 1.0

    return {
        "bases": bases, "us_index": us_index, "usd_ff": usd_ff,
        "signal": signal, "obs_count": obs_count, "staleness": staleness,
        "clusters": clusters, "yields": yields,
    }


# ---------------------------------------------------------------------------
# Backtest loops (weekly basis)
# ---------------------------------------------------------------------------

def run_cell(d, k, cluster_cap, fee_mult, band, rng=None, collect_picks=False):
    """One configuration. rng=None -> momentum ranking; rng set -> random
    selection among the same floor-passers with the same cap (the null)."""
    us_index = d["us_index"]
    grid = weekly_grid(us_index)
    grid = grid[grid >= pd.Timestamp(prereg.BACKTEST_START)]
    weekly_px = d["usd_ff"].reindex(grid)
    weekly_ret = weekly_px.pct_change()

    fee_side = prereg.FEE_RT_BPS / 2.0 / 10_000.0 * fee_mult
    rets, picks_log = [], []
    prev_w: dict[str, float] = {}
    gated_weeks = 0
    for wi in range(1, len(grid)):
        rd = grid[wi - 1]                      # decision Friday
        pos = us_index.get_loc(rd)
        sd = us_index[pos - prereg.SIGNAL_DAY_LAG]   # Thursday signal day
        sig_row = d["signal"].loc[sd]
        eligible = (d["obs_count"].loc[sd] >= prereg.MIN_HISTORY_DAYS) & \
                   (d["staleness"].loc[sd] <= prereg.FFILL_LIMIT_SESSIONS)
        if rng is None:
            picks, diag = select_names(sig_row, eligible, d["clusters"], k,
                                       cluster_cap, prereg.ENTRY_FLOOR,
                                       prereg.SLEEVE_BREADTH_GATE)
        else:
            picks, diag = random_picks(sig_row, eligible, d["clusters"], k,
                                       cluster_cap, rng)
        if picks is None:
            new_w = {}
            gated_weeks += 1
        else:
            new_w = {n: 1.0 / k for n in picks}
        cost = fee_side * turnover(prev_w, new_w)
        invested = sum(new_w.values())
        carry = (band * invested + sum(w * d["yields"][n] for n, w in new_w.items())) * 7.0 / 365.0
        gross = sum(w * weekly_ret[n].iloc[wi] for n, w in new_w.items()
                    if not np.isnan(weekly_ret[n].iloc[wi]))
        rets.append(gross - cost - carry)
        if collect_picks:
            picks_log.append({"date": grid[wi - 1].strftime("%Y-%m-%d"),
                              "picks": picks or [], **diag})
        prev_w = new_w
    ser = pd.Series(rets, index=grid[1:])
    out = stats_from_weekly(ser)
    out["pct_weeks_gated"] = round(gated_weeks / max(len(rets), 1), 3)
    return ser, out, picks_log


def precompute_weeks(d):
    """Shared per-week state for the null: signal day, floor-passers, gate
    status and weekly returns — identical to what run_cell derives, computed
    once."""
    us_index = d["us_index"]
    grid = weekly_grid(us_index)
    grid = grid[grid >= pd.Timestamp(prereg.BACKTEST_START)]
    weekly_px = d["usd_ff"].reindex(grid)
    weekly_ret = weekly_px.pct_change()
    out = []
    for wi in range(1, len(grid)):
        rd = grid[wi - 1]
        pos = us_index.get_loc(rd)
        sd = us_index[pos - prereg.SIGNAL_DAY_LAG]
        sig_row = d["signal"].loc[sd]
        eligible = (d["obs_count"].loc[sd] >= prereg.MIN_HISTORY_DAYS) & \
                   (d["staleness"].loc[sd] <= prereg.FFILL_LIMIT_SESSIONS)
        elig_names = [n for n in sig_row.index if eligible[n] and not np.isnan(sig_row[n])]
        above = [n for n in elig_names if sig_row[n] > prereg.ENTRY_FLOOR]
        breadth = (len(above) / len(elig_names)) if elig_names else 0.0
        row = weekly_ret.iloc[wi]
        out.append({
            "gated": breadth < prereg.SLEEVE_BREADTH_GATE,
            "above": above,
            "ret": {n: float(row[n]) for n in above if not np.isnan(row[n])},
        })
    return out


def random_picks(sig_row, eligible, clusters, k, cluster_cap, rng):
    elig_names = [n for n in sig_row.index if eligible[n] and not np.isnan(sig_row[n])]
    if not elig_names:
        return None, {"n_eligible": 0, "breadth": 0.0}
    above = [n for n in elig_names if sig_row[n] > prereg.ENTRY_FLOOR]
    breadth = len(above) / len(elig_names)
    if breadth < prereg.SLEEVE_BREADTH_GATE:
        return None, {"n_eligible": len(elig_names), "breadth": breadth}
    order = list(rng.permutation(above))
    picks, counts = [], {}
    for n in order:
        c = clusters.get(n, "unclassified")
        if cluster_cap is not None and counts.get(c, 0) >= cluster_cap:
            continue
        picks.append(n)
        counts[c] = counts.get(c, 0) + 1
        if len(picks) == k:
            break
    return picks, {"n_eligible": len(elig_names), "breadth": breadth}


def run_basket(d, fee_mult, band):
    """Equal-weight ALL eligible names weekly (no floor, no gate)."""
    us_index = d["us_index"]
    grid = weekly_grid(us_index)
    grid = grid[grid >= pd.Timestamp(prereg.BACKTEST_START)]
    weekly_px = d["usd_ff"].reindex(grid)
    weekly_ret = weekly_px.pct_change()
    fee_side = prereg.FEE_RT_BPS / 2.0 / 10_000.0 * fee_mult
    rets = []
    prev_w: dict[str, float] = {}
    for wi in range(1, len(grid)):
        rd = grid[wi - 1]
        pos = us_index.get_loc(rd)
        sd = us_index[pos - prereg.SIGNAL_DAY_LAG]
        eligible = (d["obs_count"].loc[sd] >= prereg.MIN_HISTORY_DAYS) & \
                   (d["staleness"].loc[sd] <= prereg.FFILL_LIMIT_SESSIONS)
        names = [n for n in d["bases"] if eligible[n]]
        new_w = {n: 1.0 / len(names) for n in names} if names else {}
        cost = fee_side * turnover(prev_w, new_w)
        carry = (band * sum(new_w.values())
                 + sum(w * d["yields"][n] for n, w in new_w.items())) * 7.0 / 365.0
        gross = sum(w * weekly_ret[n].iloc[wi] for n, w in new_w.items()
                    if not np.isnan(weekly_ret[n].iloc[wi]))
        rets.append(gross - cost - carry)
        prev_w = new_w
    ser = pd.Series(rets, index=grid[1:])
    return ser, stats_from_weekly(ser)


def main() -> int:
    d = load_inputs()
    print(f"Loaded {len(d['bases'])} bases on {len(d['us_index'])} US sessions")

    results = {"computed_at_utc": datetime.now(timezone.utc).isoformat(),
               "n_bases": len(d["bases"]), "cells": {}, "basket": {},
               "null": {}, "split_half": {}}

    # Grid cells x cost stress x band
    primary_key = f"k{prereg.PRIMARY_CELL['k']}_cap{prereg.PRIMARY_CELL['cluster_cap']}"
    primary_series = {}
    for k in prereg.K_GRID:
        for cap in prereg.CLUSTER_CAP_GRID:
            cell_key = f"k{k}_cap{cap}"
            results["cells"][cell_key] = {}
            for mult in prereg.COST_STRESS_MULTS:
                for band in prereg.FUNDING_BAND_ANN:
                    ser, st, _ = run_cell(d, k, cap, mult, band)
                    results["cells"][cell_key][f"m{mult:g}_b{band:g}"] = st
                    if cell_key == primary_key and mult == 1.0:
                        primary_series[band] = ser
            print(f"  cell {cell_key} done")

    # Basket
    for mult in prereg.COST_STRESS_MULTS:
        for band in prereg.FUNDING_BAND_ANN:
            ser, st = run_basket(d, mult, band)
            results["basket"][f"m{mult:g}_b{band:g}"] = st
            if mult == 1.0 and band == prereg.FUNDING_BAND_ANN[-1]:
                basket_edge_series = ser
    print("  basket done")

    # Null at 1x costs, band edge, primary cell shape. Per-week state is
    # precomputed ONCE (eligibility, floor-passers, gate, weekly returns);
    # each of the 1,000 paths then only permutes and walks the cap.
    rng = np.random.default_rng(prereg.NULL_SEED)
    edge = prereg.FUNDING_BAND_ANN[-1]
    weeks = precompute_weeks(d)
    k = prereg.PRIMARY_CELL["k"]
    cap = prereg.PRIMARY_CELL["cluster_cap"]
    fee_side = prereg.FEE_RT_BPS / 2.0 / 10_000.0
    null_sharpes = []
    for p in range(prereg.NULL_PATHS):
        rets = []
        prev = set()
        for w in weeks:
            if w["gated"] or not w["above"]:
                picks = set()
            else:
                order = rng.permutation(len(w["above"]))
                picks, counts = [], {}
                for j in order:
                    n = w["above"][j]
                    c = d["clusters"].get(n, "unclassified")
                    if cap is not None and counts.get(c, 0) >= cap:
                        continue
                    picks.append(n)
                    counts[c] = counts.get(c, 0) + 1
                    if len(picks) == k:
                        break
                picks = set(picks)
            to = (len(prev) + len(picks) - 2 * len(prev & picks)) / k
            invested = len(picks) / k
            carry = (edge * invested + sum(d["yields"][n] for n in picks) / k) * 7.0 / 365.0
            gross = sum(w["ret"].get(n, 0.0) for n in picks) / k
            rets.append(gross - fee_side * to - carry)
            prev = picks
        arr = pd.Series(rets)
        sd_ = arr.std()
        null_sharpes.append(float(arr.mean() / sd_ * np.sqrt(52)) if sd_ > 0 else 0.0)
        if (p + 1) % 200 == 0:
            print(f"  null [{p + 1}/{prereg.NULL_PATHS}]")
    null_sharpes = np.array(null_sharpes)
    strat_edge_sharpe = stats_from_weekly(primary_series[edge])["sharpe"]
    results["null"] = {
        "basis": "weekly net Sharpe, 1x costs, band edge, primary-cell shape",
        "n_paths": int(prereg.NULL_PATHS), "seed": prereg.NULL_SEED,
        "p05": round(float(np.percentile(null_sharpes, 5)), 3),
        "p50": round(float(np.percentile(null_sharpes, 50)), 3),
        "p90": round(float(np.percentile(null_sharpes, 90)), 3),
        "p95": round(float(np.percentile(null_sharpes, 95)), 3),
        "strategy_sharpe": strat_edge_sharpe,
        "strategy_percentile": round(float((null_sharpes < strat_edge_sharpe).mean() * 100), 1),
    }

    # Split-half (primary cell, 1x costs, band edge)
    ser = primary_series[edge]
    b = pd.Timestamp(prereg.SPLIT_HALF_BOUNDARY)
    results["split_half"] = {
        "boundary": prereg.SPLIT_HALF_BOUNDARY,
        "first": stats_from_weekly(ser[ser.index < b]),
        "second": stats_from_weekly(ser[ser.index >= b]),
    }

    OUT_PATH.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(PROJECT_ROOT)}")

    pk = results["cells"][primary_key]
    print("\nPRIMARY CELL (k5_cap2) net, 1x costs:")
    for band in prereg.FUNDING_BAND_ANN:
        s = pk[f"m1_b{band:g}"]
        print(f"  band {band:.0%}: Sharpe {s['sharpe']:+.2f}  CAGR {s['cagr']:+.1%}  "
              f"MaxDD {s['max_dd']:.1%}  gated {s['pct_weeks_gated']:.0%}")
    print("BASKET net, 1x costs:")
    for band in prereg.FUNDING_BAND_ANN:
        s = results["basket"][f"m1_b{band:g}"]
        print(f"  band {band:.0%}: Sharpe {s['sharpe']:+.2f}  CAGR {s['cagr']:+.1%}  "
              f"MaxDD {s['max_dd']:.1%}")
    n = results["null"]
    print(f"NULL: p50 {n['p50']} p90 {n['p90']} | strategy {n['strategy_sharpe']} "
          f"-> percentile {n['strategy_percentile']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
