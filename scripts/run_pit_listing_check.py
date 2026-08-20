"""Is the 2018-2026 backtest evidence, or hindsight?

Three measurements, no new parameters:

  A. RETURN CONCENTRATION — per-name contribution to the payload's cumulative
     return. If a handful of 2024-26 momentum names carry it, the curve is a
     story about those names, not about the rule.

  B. POINT-IN-TIME LISTING — rerun the identical rule, but a name is only
     eligible once its PERP ACTUALLY EXISTED (Binance onboard date). This is
     the only universe an investor could have traded. Everything before
     2025-12-11 becomes untradeable by construction.

  C. THE HONEST WINDOW — the payload, the basket and SPY over the live-universe
     era only.

Run: python scripts/run_pit_listing_check.py -> data/pit_listing_check.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402
import prereg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCANNER = Path(r"C:\dev\Perp-Funding-Scanner\data")
K, CAP = 10, 2


def onboard_dates() -> dict[str, pd.Timestamp]:
    log = json.loads((SCANNER / "tradfi_universe_log.json").read_text(encoding="utf-8"))
    seed = next(s for s in log["snapshots"] if "roster" in s)
    out = {}
    for r in seed["roster"]:
        ms = r.get("onboard_ms")
        if ms:
            out[r["base"]] = pd.Timestamp(datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date())
    return out


def run_with_listing_gate(d, listed, k, cap, band, fee_mult=1.0):
    """The frozen rule, plus one extra eligibility condition: the contract must
    already have existed on the decision date."""
    us_index = d["us_index"]
    grid = engine.weekly_grid(us_index)
    grid = grid[grid >= pd.Timestamp(prereg.BACKTEST_START)]
    weekly_px = d["usd_ff"].reindex(grid)
    weekly_ret = weekly_px.pct_change()
    fee_side = prereg.FEE_RT_BPS / 2.0 / 10_000.0 * fee_mult
    rets, prev_w = [], {}
    n_invested = 0
    for wi in range(1, len(grid)):
        rd = grid[wi - 1]
        pos = us_index.get_loc(rd)
        sd = us_index[pos - prereg.SIGNAL_DAY_LAG]
        sig_row = d["signal"].loc[sd]
        elig = (d["obs_count"].loc[sd] >= prereg.MIN_HISTORY_DAYS) & \
               (d["staleness"].loc[sd] <= prereg.FFILL_LIMIT_SESSIONS)
        for b in sig_row.index:                       # the listing gate
            ob = listed.get(b)
            if ob is None or ob > rd:
                elig[b] = False
        picks, _ = engine.select_names(sig_row, elig, d["clusters"], k, cap,
                                       prereg.ENTRY_FLOOR, prereg.SLEEVE_BREADTH_GATE)
        new_w = {} if picks is None else {n: 1.0 / k for n in picks}
        if new_w:
            n_invested += 1
        cost = fee_side * engine.turnover(prev_w, new_w)
        carry = (band * sum(new_w.values())
                 + sum(w * d["yields"][n] for n, w in new_w.items())) * 7.0 / 365.0
        gross = sum(w * weekly_ret[n].iloc[wi] for n, w in new_w.items()
                    if not np.isnan(weekly_ret[n].iloc[wi]))
        rets.append(gross - cost - carry)
        prev_w = new_w
    ser = pd.Series(rets, index=grid[1:])
    return ser, engine.stats_from_weekly(ser), n_invested


def main() -> int:
    d = engine.load_inputs()
    listed = onboard_dates()
    edge = prereg.FUNDING_BAND_ANN[-1]
    umap = json.loads((ROOT / prereg.UNIVERSE_MAP).read_text(encoding="utf-8"))["rows"]
    name_of = {b: (e.get("vendor_name") or b) for b, e in umap.items()}
    out = {"computed_at_utc": datetime.now(timezone.utc).isoformat()}

    # --- A. contribution by name (unrestricted, the published backtest) ------
    ser, stats, picks_log = engine.run_cell(d, K, CAP, 1.0, edge, collect_picks=True)
    grid = pd.to_datetime([p["date"] for p in picks_log])
    weekly_ret = d["usd_ff"].reindex(grid).pct_change()
    contrib: dict[str, float] = {}
    for i, p in enumerate(picks_log):
        if i + 1 >= len(grid):
            break
        for b in p["picks"]:
            r = weekly_ret[b].iloc[i + 1]
            if not np.isnan(r):
                contrib[b] = contrib.get(b, 0.0) + r / K
    total = sum(contrib.values())
    top = sorted(contrib.items(), key=lambda kv: -kv[1])[:12]
    out["contribution"] = {
        "sum_of_weekly_contributions_pct": round(total * 100, 1),
        "top": [{"base": b, "name": name_of.get(b, b), "pct": round(v * 100, 1),
                 "share_of_total": round(v / total * 100, 1) if total else None,
                 "perp_listed": str(listed.get(b, "—"))} for b, v in top],
        "top5_share_pct": round(sum(v for _, v in top[:5]) / total * 100, 1) if total else None,
    }

    # --- B. point-in-time listing gate --------------------------------------
    pit_ser, pit_stats, n_inv = run_with_listing_gate(d, listed, K, CAP, edge)
    first_live = min(listed.values()) if listed else None
    out["pit_listing"] = {
        "stats_full_window": pit_stats,
        "weeks_invested": n_inv,
        "weeks_total": len(pit_ser),
        "first_possible_listing": str(first_live.date()) if first_live is not None else None,
        "note": ("a name is eligible only once its perp actually existed; before the first "
                 "listing the strategy is untradeable and holds nothing"),
    }

    # --- C. the honest window ------------------------------------------------
    if first_live is not None:
        mask = pit_ser.index >= first_live
        live_era = pit_ser[mask]
        unrestricted_era = ser[ser.index >= first_live]
        basket_ser, _ = engine.run_basket(d, 1.0, edge)
        basket_era = basket_ser[basket_ser.index >= first_live]
        bench = d["usd_ff"]["SPY"].reindex(pit_ser.index).ffill().pct_change()
        bench_era = bench[bench.index >= first_live]
        out["honest_window"] = {
            "from": str(first_live.date()),
            "weeks": int(len(live_era)),
            "payload_pit_listing": engine.stats_from_weekly(live_era),
            "payload_unrestricted_same_window": engine.stats_from_weekly(unrestricted_era),
            "equal_weight_basket": engine.stats_from_weekly(basket_era),
            "spy_buy_hold": engine.stats_from_weekly(bench_era.fillna(0.0)),
        }

    (ROOT / "data" / "pit_listing_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    print("=== A. RETURN CONCENTRATION (published backtest) ===")
    print(f"sum of weekly contributions: {out['contribution']['sum_of_weekly_contributions_pct']}%"
          f" · top 5 names = {out['contribution']['top5_share_pct']}% of it")
    for t in out["contribution"]["top"][:8]:
        print(f"  {t['name'][:34]:<34} {t['pct']:>8.1f}%  ({t['share_of_total']:>4.1f}% of total)  perp listed {t['perp_listed']}")
    print()
    print("=== B. POINT-IN-TIME LISTING GATE ===")
    print(f"first perp listing: {out['pit_listing']['first_possible_listing']}")
    print(f"weeks actually invested: {n_inv} of {len(pit_ser)}")
    print(f"full-window stats: {pit_stats}")
    print()
    if "honest_window" in out:
        h = out["honest_window"]
        print(f"=== C. THE ONLY HONEST WINDOW ({h['from']} onward, {h['weeks']} weeks) ===")
        for k_, v in (("payload, PIT listing", h["payload_pit_listing"]),
                      ("payload, unrestricted", h["payload_unrestricted_same_window"]),
                      ("equal-weight basket", h["equal_weight_basket"]),
                      ("SPY buy-and-hold", h["spy_buy_hold"])):
            print(f"  {k_:<26} Sharpe {v['sharpe']:+.2f}  total {v['total_return']*100:+.1f}%  MaxDD {v['max_dd']*100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
