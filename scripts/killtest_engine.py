"""P1 — the kill-test engine. Imports the frozen constants; defines no new ones.

Reads the P0 universe (point-in-time membership, price-only closes, GICS
sectors, T-bill) and runs the pre-registered grid, arms and null.

Basis, stated once and used everywhere:
  * weekly rebalance on the last session of each ISO week; the signal is read
    SIGNAL_DAY_LAG sessions earlier, so a decision never uses the price it
    fills at (pinned by tests/test_killtest_universe.py);
  * prices are split-adjusted and dividend-free, so returns are price-only —
    what a perpetual actually tracks — and no dividend estimate is charged;
  * carry = (T-bill + premium) on invested capital less the T-bill earned on
    cash, so the breadth gate is neither rewarded nor punished by assumption;
  * a name that delists realises its final observed move in the week it dies
    and is ineligible thereafter. Liquidation value after the final bar is not
    modelled — for bankruptcies that makes returns slightly optimistic.

Run: python scripts/killtest_engine.py -> data/killtest_results.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import killtest_common as KC  # noqa: E402
import prereg_killtest as P  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


# ---------------------------------------------------------------------------
# Per-week state, computed once
# ---------------------------------------------------------------------------

def precompute():
    px_raw = pd.read_parquet(DATA / "killtest_prices.parquet")
    member = pd.read_parquet(DATA / "killtest_members.parquet")
    rates = pd.read_parquet(DATA / "killtest_rates.parquet")["rf"]
    meta = json.loads((DATA / "killtest_meta.json").read_text(encoding="utf-8"))["meta"]
    sectors = {s: (v.get("sector") or "unclassified") for s, v in meta.items()}

    sessions = px_raw.index
    px = px_raw.ffill()
    ma = px.rolling(P.MA_WINDOW, min_periods=P.MA_WINDOW).mean()
    dist = px / ma - 1.0                                   # MA200 distance
    mom = px.shift(21) / px.shift(252) - 1.0               # 12-1 momentum
    obs = px_raw.notna().cumsum()
    marker = pd.DataFrame(
        np.where(px_raw.notna(), np.arange(len(sessions))[:, None], np.nan),
        index=sessions, columns=px_raw.columns).ffill()
    stale = pd.DataFrame(np.arange(len(sessions))[:, None] - marker.values,
                         index=sessions, columns=px_raw.columns)

    grid = KC.weekly_grid(sessions)
    grid = grid[grid >= pd.Timestamp(P.BACKTEST_START)]
    pairs = KC.signal_fill_pairs(sessions, grid)

    weeks = []
    for i, (sd, fd) in enumerate(pairs):
        if i + 1 >= len(pairs):
            break
        nfd = pairs[i + 1][1]
        elig = (member.loc[sd].values
                & (obs.loc[sd].values >= P.MIN_HISTORY_DAYS)
                & (stale.loc[sd].values <= P.FFILL_LIMIT_SESSIONS))
        cols = px.columns[elig]
        d_row, m_row = dist.loc[sd], mom.loc[sd]
        p0, p1 = px.loc[fd], px.loc[nfd]
        names, sig, momv, ret = [], {}, {}, {}
        for n in cols:
            dv = d_row[n]
            if np.isnan(dv):
                continue
            a, b = p0[n], p1[n]
            if np.isnan(a) or a <= 0:
                continue
            names.append(n)
            sig[n] = float(dv)
            mv = m_row[n]
            momv[n] = float(mv) if not np.isnan(mv) else -np.inf
            ret[n] = float(b / a - 1.0) if not np.isnan(b) else 0.0
        above = [n for n in names if sig[n] > P.ENTRY_FLOOR]
        weeks.append({
            "date": fd.strftime("%Y-%m-%d"), "names": names, "above": above,
            "sig": sig, "mom": momv, "ret": ret,
            "breadth": (len(above) / len(names)) if names else 0.0,
            "rf": float(rates.loc[fd]),
        })
    return weeks, sectors


# ---------------------------------------------------------------------------
# Selection and simulation
# ---------------------------------------------------------------------------

def pick(week, sectors, k, cap, rank_key, use_gate):
    if use_gate and week["breadth"] < P.SLEEVE_BREADTH_GATE:
        return []
    pool = week["above"]
    if not pool:
        return []
    key = week[rank_key]
    ranked = sorted(pool, key=lambda n: (-key[n], n))
    out, counts = [], {}
    for n in ranked:
        c = sectors.get(n, "unclassified")
        if cap is not None and counts.get(c, 0) >= cap:
            continue
        out.append(n)
        counts[c] = counts.get(c, 0) + 1
        if len(out) == k:
            break
    return out


def simulate(weeks, sectors, k, cap, premium, fee_mult=1.0,
             rank_key="sig", use_gate=True, mode="rotation", rng=None,
             restrict=None):
    fee_side = P.FEE_RT_BPS / 2.0 / 10_000.0 * fee_mult
    rets, prev = [], set()
    for w in weeks:
        if mode == "basket":
            names = w["names"] if restrict is None else [n for n in w["names"] if n in restrict]
            held = set(names)
            wt = (1.0 / len(held)) if held else 0.0
            invested = 1.0 if held else 0.0
            gross = sum(w["ret"][n] for n in held) * wt
        else:
            week = w
            if restrict is not None:
                week = dict(w)
                week["names"] = [n for n in w["names"] if n in restrict]
                week["above"] = [n for n in w["above"] if n in restrict]
                week["breadth"] = (len(week["above"]) / len(week["names"])) if week["names"] else 0.0
            if rng is not None:
                if use_gate and week["breadth"] < P.SLEEVE_BREADTH_GATE or not week["above"]:
                    held = set()
                else:
                    order = rng.permutation(len(week["above"]))
                    sel, counts = [], {}
                    for j in order:
                        n = week["above"][j]
                        c = sectors.get(n, "unclassified")
                        if cap is not None and counts.get(c, 0) >= cap:
                            continue
                        sel.append(n)
                        counts[c] = counts.get(c, 0) + 1
                        if len(sel) == k:
                            break
                    held = set(sel)
            else:
                held = set(pick(week, sectors, k, cap, rank_key, use_gate))
            wt = 1.0 / k
            invested = len(held) / k
            gross = sum(w["ret"][n] for n in held) * wt
        turnover = len(prev - held) + len(held - prev)
        cost = fee_side * turnover * (wt if mode != "basket" else wt)
        carry = KC.weekly_carry(w["rf"], premium, invested)
        rets.append(gross - cost - carry)
        prev = held
    return pd.Series(rets)


def stats(r: pd.Series) -> dict:
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min())
    sd = r.std()
    years = len(r) / 52.0
    return {"sharpe": round(float(r.mean() / sd * np.sqrt(52)) if sd > 0 else 0.0, 3),
            "cagr": round(float(eq.iloc[-1] ** (1 / years) - 1.0), 4),
            "total_return": round(float(eq.iloc[-1] - 1.0), 4),
            "max_dd": round(dd, 4), "n_weeks": int(len(r))}


def main() -> int:
    weeks, sectors = precompute()
    print(f"weeks: {len(weeks)} from {weeks[0]['date']} to {weeks[-1]['date']}")
    print(f"eligible names per week: min {min(len(w['names']) for w in weeks)}, "
          f"max {max(len(w['names']) for w in weeks)}")
    band = P.FUNDING_PREMIUM_BAND
    mid = band[1]
    out = {"computed_at_utc": datetime.now(timezone.utc).isoformat(),
           "n_weeks": len(weeks), "first": weeks[0]["date"], "last": weeks[-1]["date"],
           "cells": {}, "basket": {}, "arms": {}, "null": {}, "split_half": {}}

    # --- grid x band x cost stress -----------------------------------------
    primary_key = f"k{P.PRIMARY_CELL['k']}_cap{P.PRIMARY_CELL['sector_cap']}"
    primary_series = {}
    for k in P.K_GRID:
        for cap in P.SECTOR_CAP_GRID:
            ck = f"k{k}_cap{cap}"
            out["cells"][ck] = {}
            for mult in P.COST_STRESS_MULTS:
                for prem in band:
                    s = simulate(weeks, sectors, k, cap, prem, mult)
                    out["cells"][ck][f"m{mult:g}_p{prem:g}"] = stats(s)
                    if ck == primary_key and mult == 1.0:
                        primary_series[prem] = s
            print(f"  cell {ck} done")

    # --- basket (the PRIMARY comparator) ------------------------------------
    for mult in P.COST_STRESS_MULTS:
        for prem in band:
            s = simulate(weeks, sectors, 0, None, prem, mult, mode="basket")
            out["basket"][f"m{mult:g}_p{prem:g}"] = stats(s)
    print("  basket done")

    # --- H2 gate on/off, H3 ranking statistic -------------------------------
    k, cap = P.PRIMARY_CELL["k"], P.PRIMARY_CELL["sector_cap"]
    out["arms"]["gate_on"] = stats(simulate(weeks, sectors, k, cap, mid))
    out["arms"]["gate_off"] = stats(simulate(weeks, sectors, k, cap, mid, use_gate=False))
    out["arms"]["rank_ma200"] = out["arms"]["gate_on"]
    out["arms"]["rank_mom12_1"] = stats(simulate(weeks, sectors, k, cap, mid, rank_key="mom"))
    print("  arms done")

    # --- M1: the Binance menu, as a measurement -----------------------------
    umap = json.loads((ROOT / "data" / "universe_map.json").read_text(encoding="utf-8"))["rows"]
    menu = {e["candidate"] for b, e in umap.items()
            if e.get("status") == "verified" and not e.get("levered_etp")
            and e.get("cluster") != "commodity"}
    panel_menu = menu & set(weeks[0]["sig"].keys() | {n for w in weeks for n in w["names"]})
    out["menu_arm"] = {
        "n_menu_names_in_panel": len(panel_menu),
        "rotation": stats(simulate(weeks, sectors, k, cap, mid, restrict=panel_menu)),
        "basket": stats(simulate(weeks, sectors, 0, None, mid, mode="basket", restrict=panel_menu)),
    }
    print(f"  menu arm done ({len(panel_menu)} names)")

    # --- null ---------------------------------------------------------------
    rng = np.random.default_rng(P.NULL_SEED)
    edge = band[-1]
    sharpes = []
    for i in range(P.NULL_PATHS):
        sharpes.append(stats(simulate(weeks, sectors, k, cap, edge, rng=rng))["sharpe"])
        if (i + 1) % 250 == 0:
            print(f"  null [{i+1}/{P.NULL_PATHS}]")
    a = np.array(sharpes)
    strat = stats(primary_series[edge])["sharpe"]
    out["null"] = {"n_paths": int(P.NULL_PATHS), "seed": P.NULL_SEED,
                   "p50": round(float(np.percentile(a, 50)), 3),
                   "p90": round(float(np.percentile(a, 90)), 3),
                   "p95": round(float(np.percentile(a, 95)), 3),
                   "strategy_sharpe": strat,
                   "strategy_percentile": round(float((a < strat).mean() * 100), 1),
                   "sharpes": [round(float(v), 3) for v in a]}

    # --- split half ---------------------------------------------------------
    s = primary_series[edge]
    idx = pd.to_datetime([w["date"] for w in weeks])
    s.index = idx
    b = pd.Timestamp(P.SPLIT_HALF_BOUNDARY)
    out["split_half"] = {"boundary": P.SPLIT_HALF_BOUNDARY,
                         "first": stats(s[s.index < b]), "second": stats(s[s.index >= b])}

    (DATA / "killtest_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    print("\n=== PRIMARY CELL (K=10, sector cap 2), 1x costs ===")
    for prem in band:
        st = out["cells"][primary_key][f"m1_p{prem:g}"]
        bk = out["basket"][f"m1_p{prem:g}"]
        print(f"  premium {prem:.0%}: rotation Sharpe {st['sharpe']:+.2f} CAGR {st['cagr']:+.1%} "
              f"DD {st['max_dd']:.1%}   |   basket {bk['sharpe']:+.2f} {bk['cagr']:+.1%} {bk['max_dd']:.1%}"
              f"   -> margin {st['sharpe']-bk['sharpe']:+.2f}")
    print(f"\nnull: p50 {out['null']['p50']} p90 {out['null']['p90']} | strategy {strat} "
          f"-> {out['null']['strategy_percentile']}th pct")
    print(f"H2 gate on {out['arms']['gate_on']['sharpe']:+.2f} vs off {out['arms']['gate_off']['sharpe']:+.2f}")
    print(f"H3 MA200 {out['arms']['rank_ma200']['sharpe']:+.2f} vs 12-1 mom {out['arms']['rank_mom12_1']['sharpe']:+.2f}")
    print(f"M1 menu-restricted rotation {out['menu_arm']['rotation']['sharpe']:+.2f} "
          f"vs basket {out['menu_arm']['basket']['sharpe']:+.2f}")
    print(f"split half: {out['split_half']['first']['sharpe']:+.2f} / {out['split_half']['second']['sharpe']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
