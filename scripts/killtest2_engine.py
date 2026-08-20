"""KT-2 — the single confirmation run. Imports the frozen constants; defines
no new ones. Everything selection-critical routes through killtest2_common,
where the P0 guards pinned it.

Basis, stated once:
  * Russell 1000 C&P panel, price-only (CAPITAL); eligibility at the signal
    date = fresh within 3 sessions AND >= 252 sessions of history AND in the
    top-250 trailing-median dollar-volume screen (strictly-before window);
  * MA200 +5% floor qualifies, 30% breadth gate to cash; QUALIFIERS ranked by
    12-1 momentum; K=10, theme cap 2; signal one session before the fill;
  * carry = (T-bill + premium) on invested, T-bill earned on cash; fees 10bp
    RT per unit turnover; no dividend charge (prices are dividend-free);
  * hard asserts run throughout: picks within the eligible set, cap respected
    per label, invested <= 1. A violation raises rather than degrades.

Run: python scripts/killtest2_engine.py -> data/killtest2_results.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import killtest2_common as KC2  # noqa: E402
import prereg_killtest2 as P2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def stats(r: pd.Series) -> dict:
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min())
    sd = r.std()
    years = len(r) / 52.0
    cagr = float(eq.iloc[-1] ** (1 / years) - 1.0)
    return {"sharpe": round(float(r.mean() / sd * np.sqrt(52)) if sd > 0 else 0.0, 3),
            "cagr": round(cagr, 4),
            "total_return": round(float(eq.iloc[-1] - 1.0), 4),
            "max_dd": round(dd, 4),
            "calmar": round(cagr / abs(dd), 3) if dd < 0 else None,
            "n_weeks": int(len(r))}


def _staleness(px_raw: pd.DataFrame) -> pd.DataFrame:
    marker = pd.DataFrame(np.where(px_raw.notna(), np.arange(len(px_raw))[:, None], np.nan),
                          index=px_raw.index, columns=px_raw.columns).ffill()
    return pd.DataFrame(np.arange(len(px_raw))[:, None] - marker.values,
                        index=px_raw.index, columns=px_raw.columns)


def _formations(pairs, wr, stale):
    """Cluster labels per formation date (first rebalance of Jan/Apr/Jul/Oct),
    formed over names fresh at the formation date, data strictly before it."""
    out, seen_q, stats_all = [], set(), []
    for _, fd in pairs:
        q = (fd.year, fd.month)
        if fd.month in P2.CLUSTER_REFORM_MONTHS and q not in seen_q:
            seen_q.add(q)
            fresh = set(stale.columns[stale.loc[fd] <= P2.FFILL_LIMIT_SESSIONS])
            labels, st = KC2.form_clusters(wr, sorted(fresh), fd)
            out.append((fd, labels))
            stats_all.append({"date": fd.strftime("%Y-%m-%d"), **st,
                              "degenerate": KC2.clustering_degenerate(st)})
    return out, stats_all


def precompute(px_raw, dv, rates, sectors, member=None):
    """Per-week state. member=None -> Russell liquidity-screen eligibility;
    member=DataFrame -> SEEN-panel membership eligibility (KT-1 rule)."""
    sessions = px_raw.index
    px = px_raw.ffill()
    dist = px / px.rolling(P2.MA_WINDOW, min_periods=P2.MA_WINDOW).mean() - 1.0
    mom = px.shift(P2.MOM_SHORT) / px.shift(P2.MOM_LONG) - 1.0
    obs = px_raw.notna().cumsum()
    stale = _staleness(px_raw)
    full_grid = KC2.weekly_grid(sessions)
    wr = px.reindex(full_grid).pct_change()
    grid = full_grid[full_grid >= pd.Timestamp(P2.BACKTEST_START)]
    pairs = KC2.signal_fill_pairs(sessions, grid)
    forms, form_stats = _formations(pairs, wr, stale)

    weeks = []
    for i, (sd, fd) in enumerate(pairs):
        if i + 1 >= len(pairs):
            break
        nfd = pairs[i + 1][1]
        fresh = set(px.columns[stale.loc[sd] <= P2.FFILL_LIMIT_SESSIONS])
        hist_ok = obs.loc[sd] >= P2.MIN_HISTORY_DAYS
        if member is None:
            pool = KC2.liquid_set(dv, sessions, sd, fresh=fresh)
        else:
            pool = set(px.columns[member.loc[sd].values]) & fresh
        elig = sorted(n for n in pool if hist_ok[n])
        d_row, m_row = dist.loc[sd], mom.loc[sd]
        quals, sig = [], {}
        for n in elig:
            dv_ = d_row[n]
            if not np.isnan(dv_) and dv_ > P2.ENTRY_FLOOR:
                quals.append(n)
                mv = m_row[n]
                sig[n] = float(mv) if not np.isnan(mv) else -np.inf
        p0, p1 = px.loc[fd], px.loc[nfd]
        ret = {n: (float(p1[n] / p0[n] - 1.0)
                   if not (np.isnan(p0[n]) or np.isnan(p1[n]) or p0[n] <= 0) else 0.0)
               for n in elig}
        labels = None
        for f_date, lab in forms:
            if f_date <= fd:
                labels = lab
        weeks.append({"date": fd, "elig": elig, "quals": quals, "sig": sig, "ret": ret,
                      "breadth": (len(quals) / len(elig)) if elig else 0.0,
                      "rf": float(rates.loc[fd]), "clusters": labels})
    return weeks, form_stats, sectors


def _label(week, sectors, kind, n):
    if kind == "cluster":
        lab = week["clusters"] or {}
        return lab.get(n, ("solo", n))
    if kind == "gics":
        return sectors.get(n, "unclassified")
    return None


def simulate(weeks, sectors, kind, premium, fee_mult=1.0, use_gate=True,
             mode="rotation", rng=None):
    """kind in {'cluster','gics','none'} for the rotation theme cap."""
    fee_side = P2.FEE_RT_BPS / 2.0 / 10_000.0 * fee_mult
    rets, prev = [], set()
    for w in weeks:
        if mode == "basket":
            held = set(w["elig"])
            wt = (1.0 / len(held)) if held else 0.0
            invested = 1.0 if held else 0.0
        else:
            if (use_gate and w["breadth"] < P2.SLEEVE_BREADTH_GATE) or not w["quals"]:
                held = set()
            else:
                order = (list(rng.permutation(len(w["quals"])))
                         if rng is not None else None)
                ranked = ([w["quals"][j] for j in order] if order is not None
                          else sorted(w["quals"], key=lambda n: (-w["sig"][n], n)))
                sel, counts = [], {}
                for n in ranked:
                    c = _label(w, sectors, kind, n)
                    if kind != "none" and c is not None and counts.get(c, 0) >= P2.THEME_CAP:
                        continue
                    sel.append(n)
                    counts[c] = counts.get(c, 0) + 1
                    if len(sel) == P2.K:
                        break
                held = set(sel)
                assert held <= set(w["elig"]), "pick outside the eligible set"
                if kind != "none":
                    assert all(v <= P2.THEME_CAP for v in counts.values()), "cap violated"
            wt = 1.0 / P2.K
            invested = len(held) / P2.K
            assert invested <= 1.0 + 1e-9
        turnover = len(prev - held) + len(held - prev)
        cost = fee_side * turnover * wt
        gross = sum(w["ret"].get(n, 0.0) for n in held) * wt
        rets.append(gross - cost - KC2.weekly_carry(w["rf"], premium, invested))
        prev = held
    return pd.Series(rets, index=[w["date"] for w in weeks])


def main() -> int:
    px_raw = pd.read_parquet(DATA / "killtest2_prices.parquet")
    dvol = pd.read_parquet(DATA / "killtest2_dollarvol.parquet")
    rates = pd.read_parquet(DATA / "killtest2_rates.parquet")["rf"]
    meta = json.loads((DATA / "killtest2_meta.json").read_text(encoding="utf-8"))["meta"]
    sectors = {s: (v.get("sector") or "unclassified") for s, v in meta.items()}

    print("precomputing weeks (screen + clusters) ...")
    weeks, form_stats, _ = precompute(px_raw, dvol, rates, sectors)
    n_degen = sum(1 for f in form_stats if f["degenerate"])
    print(f"weeks {len(weeks)} from {weeks[0]['date'].date()} to {weeks[-1]['date'].date()}"
          f" · formations {len(form_stats)} · degenerate {n_degen}")

    band, mid, edge = P2.FUNDING_PREMIUM_BAND, P2.FUNDING_PREMIUM_BAND[1], P2.FUNDING_PREMIUM_BAND[-1]
    out = {"computed_at_utc": datetime.now(timezone.utc).isoformat(),
           "n_weeks": len(weeks), "first": str(weeks[0]["date"].date()),
           "last": str(weeks[-1]["date"].date()),
           "cluster_formations": form_stats, "n_degenerate_formations": n_degen}

    # --- S2: theme-definition selection at the band centre, 1x ---------------
    arms_mid = {k: stats(simulate(weeks, sectors, k, mid)) for k in ("cluster", "gics", "none")}
    out["s2_arms_mid"] = arms_mid
    if n_degen > 0:
        adopted, why = "gics", f"degeneracy guard: {n_degen} formation(s) tripped"
    else:
        dd = {k: abs(arms_mid[k]["max_dd"]) for k in arms_mid}
        best_sh = max(v["sharpe"] for v in arms_mid.values())
        if (dd["cluster"] <= min(dd.values()) + 1e-12
                and arms_mid["cluster"]["sharpe"] >= best_sh - P2.S2_SHARPE_TOL):
            adopted, why = "cluster", "shallowest MaxDD and Sharpe within tolerance of best"
        else:
            adopted, why = "gics", "cluster cap failed the S2 criterion"
    out["s2"] = {"adopted": adopted, "why": why}
    print(f"S2 -> adopted theme definition: {adopted} ({why})")

    # --- adopted arm and basket: full band x cost stress ----------------------
    out["rotation"], out["basket"] = {}, {}
    rot_series = {}
    for mult in P2.COST_STRESS_MULTS:
        for prem in band:
            key = f"m{mult:g}_p{prem:g}"
            s = simulate(weeks, sectors, adopted, prem, mult)
            out["rotation"][key] = stats(s)
            if mult == 1.0:
                rot_series[prem] = s
            out["basket"][key] = stats(simulate(weeks, sectors, adopted, prem, mult, mode="basket"))
    print("grid done")

    # --- bars (section 6), read exactly --------------------------------------
    def bar_read(mult, margin_req):
        reads = []
        for prem in band:
            r_, b_ = out["rotation"][f"m{mult:g}_p{prem:g}"], out["basket"][f"m{mult:g}_p{prem:g}"]
            reads.append({"premium": prem,
                          "calmar_margin": round(r_["calmar"] - b_["calmar"], 3),
                          "a_pass": (r_["calmar"] - b_["calmar"]) >= margin_req - 1e-12,
                          "sharpe_rot": r_["sharpe"], "sharpe_bask": b_["sharpe"],
                          "b_pass": r_["sharpe"] >= b_["sharpe"],
                          "dd_ratio": round(abs(r_["max_dd"]) / abs(b_["max_dd"]), 3),
                          "c_pass": abs(r_["max_dd"]) <= P2.DD_RATIO_MAX * abs(b_["max_dd"])})
        return reads

    s1_1x = bar_read(1.0, P2.CALMAR_MARGIN)
    s1_2x = bar_read(2.0, 0.0)

    rng = np.random.default_rng(P2.NULL_SEED)
    null_calmars = []
    for i in range(P2.NULL_PATHS):
        st = stats(simulate(weeks, sectors, adopted, edge, rng=rng))
        null_calmars.append(st["calmar"] if st["calmar"] is not None else 0.0)
        if (i + 1) % 250 == 0:
            print(f"  null [{i + 1}/{P2.NULL_PATHS}]")
    a = np.array(null_calmars, dtype=float)
    strat_cal = out["rotation"][f"m1_p{edge:g}"]["calmar"]
    d_pct = round(float((a < strat_cal).mean() * 100), 1)
    out["null"] = {"n_paths": P2.NULL_PATHS, "seed": P2.NULL_SEED, "basis": "calmar at band edge",
                   "p50": round(float(np.percentile(a, 50)), 3),
                   "p90": round(float(np.percentile(a, 90)), 3),
                   "strategy_calmar": strat_cal, "strategy_percentile": d_pct,
                   "calmars": [round(float(v), 3) for v in a]}

    s1_pass = (all(r["a_pass"] and r["b_pass"] and r["c_pass"] for r in s1_1x)
               and all(r["a_pass"] and r["b_pass"] and r["c_pass"] for r in s1_2x)
               and d_pct >= P2.NULL_PCTL_MIN)
    out["bars"] = {"s1_1x": s1_1x, "s1_2x": s1_2x, "d_null_pctl": d_pct,
                   "s1_pass": bool(s1_pass)}

    # --- report-only arms -----------------------------------------------------
    out["gate_off_mid"] = stats(simulate(weeks, sectors, adopted, mid, use_gate=False))
    s_edge = rot_series[edge]
    b_ = pd.Timestamp(P2.SPLIT_HALF_BOUNDARY)
    out["split_half"] = {"boundary": P2.SPLIT_HALF_BOUNDARY,
                         "first": stats(s_edge[s_edge.index < b_]),
                         "second": stats(s_edge[s_edge.index >= b_])}

    rng2 = np.random.default_rng(20260822)          # NULL_SEED + 1, report-only
    rot_mid = rot_series[mid].values
    bask_mid = simulate(weeks, sectors, adopted, mid, mode="basket").values
    n, blk = len(rot_mid), 13
    margins = []
    for _ in range(2000):
        starts = rng2.integers(0, n, size=n // blk + 1)
        idx = np.concatenate([np.arange(s0, s0 + blk) % n for s0 in starts])[:n]
        r_s, b_s = pd.Series(rot_mid[idx]), pd.Series(bask_mid[idx])
        sr, sb = stats(r_s), stats(b_s)
        if sr["calmar"] is not None and sb["calmar"] is not None:
            margins.append(sr["calmar"] - sb["calmar"])
    out["bootstrap_margin_mid"] = {"block_weeks": blk, "draws": 2000, "seed": 20260822,
                                   "p5": round(float(np.percentile(margins, 5)), 3),
                                   "p50": round(float(np.percentile(margins, 50)), 3),
                                   "p95": round(float(np.percentile(margins, 95)), 3)}

    import norgatedata as nd
    spy = nd.price_timeseries(P2.BENCHMARK,
                              stock_price_adjustment_setting=nd.StockPriceAdjustmentType.CAPITAL,
                              start_date=P2.UNIVERSE_START, format="pandas-dataframe")["Close"].astype(float)
    spy.index = pd.to_datetime(spy.index).tz_localize(None)
    g = KC2.weekly_grid(px_raw.index)
    g = g[g >= pd.Timestamp(P2.BACKTEST_START)]
    out["benchmark_spy"] = {"basis": "price-only, no costs or financing — context only",
                            "stats": stats(spy.reindex(px_raw.index).ffill().reindex(g).pct_change().dropna())}

    # --- SEEN continuity run (labelled; no verdict weight) --------------------
    print("SEEN continuity run (S&P+NDX panel, KT-2 construction) ...")
    px1 = pd.read_parquet(DATA / "killtest_prices.parquet")
    mem1 = pd.read_parquet(DATA / "killtest_members.parquet")
    r1 = pd.read_parquet(DATA / "killtest_rates.parquet")["rf"]
    meta1 = json.loads((DATA / "killtest_meta.json").read_text(encoding="utf-8"))["meta"]
    sec1 = {s: (v.get("sector") or "unclassified") for s, v in meta1.items()}
    w1, fs1, _ = precompute(px1, None, r1, sec1, member=mem1)
    kind1 = adopted if not any(f["degenerate"] for f in fs1) else "gics"
    out["seen_panel"] = {"label": "SEEN — S&P 500 + Nasdaq-100, membership eligibility, KT-2 construction",
                         "arm": kind1,
                         "rotation_mid": stats(simulate(w1, sec1, kind1, mid)),
                         "basket_mid": stats(simulate(w1, sec1, kind1, mid, mode="basket"))}

    (DATA / "killtest2_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    print("\n=== KT-2 CONFIRMATION — bars read exactly (adopted arm:", adopted, ") ===")
    for tag, reads in (("1x", s1_1x), ("2x", s1_2x)):
        for r_ in reads:
            print(f"  {tag} premium {r_['premium']:.0%}: Calmar margin {r_['calmar_margin']:+.3f} "
                  f"[a {'P' if r_['a_pass'] else 'F'}] Sharpe {r_['sharpe_rot']:+.3f} vs "
                  f"{r_['sharpe_bask']:+.3f} [b {'P' if r_['b_pass'] else 'F'}] "
                  f"DD ratio {r_['dd_ratio']:.2f} [c {'P' if r_['c_pass'] else 'F'}]")
    print(f"  (d) null Calmar percentile {d_pct} (bar >= {P2.NULL_PCTL_MIN})")
    print(f"\nS1 VERDICT: {'PASS' if s1_pass else 'FAIL'}")
    print(f"gate off (mid): {out['gate_off_mid']['sharpe']:+.3f} / DD {out['gate_off_mid']['max_dd']:.1%}"
          f" vs on {out['rotation'][f'm1_p{mid:g}']['sharpe']:+.3f} / {out['rotation'][f'm1_p{mid:g}']['max_dd']:.1%}")
    print(f"split-half (edge): {out['split_half']['first']['sharpe']:+.3f} / {out['split_half']['second']['sharpe']:+.3f}")
    print(f"bootstrap margin CI (mid): [{out['bootstrap_margin_mid']['p5']:+.3f}, "
          f"{out['bootstrap_margin_mid']['p95']:+.3f}]")
    print(f"SEEN: rotation {out['seen_panel']['rotation_mid']['sharpe']:+.3f} "
          f"vs basket {out['seen_panel']['basket_mid']['sharpe']:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
