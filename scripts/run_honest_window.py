"""The honest window, like-for-like — plus an EMPIRICAL funding estimate.

Part 1: every construction under the SAME point-in-time listing gate (a name
is eligible only once its perp existed), over the live-universe era. The
earlier pass compared a gated rotation against an ungated basket, which breaks
the like-for-like rule; this fixes it.

Part 2: funding measured from the actual contracts rather than assumed as a
band. The scanner keeps 90 days of realised funding for every liquid Binance
USD-M perp; this annualises it per name and asks the question that matters:
does a MOMENTUM-selected book pay more funding than the universe average?

Run: python scripts/run_honest_window.py -> data/honest_window.json
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
from run_pit_listing_check import onboard_dates, run_with_listing_gate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCANNER = Path(r"C:\dev\Perp-Funding-Scanner\data")
K, CAP = 10, 2


def basket_with_listing_gate(d, listed, band, fee_mult=1.0):
    us_index = d["us_index"]
    grid = engine.weekly_grid(us_index)
    grid = grid[grid >= pd.Timestamp(prereg.BACKTEST_START)]
    weekly_px = d["usd_ff"].reindex(grid)
    weekly_ret = weekly_px.pct_change()
    fee_side = prereg.FEE_RT_BPS / 2.0 / 10_000.0 * fee_mult
    rets, prev_w = [], {}
    for wi in range(1, len(grid)):
        rd = grid[wi - 1]
        pos = us_index.get_loc(rd)
        sd = us_index[pos - prereg.SIGNAL_DAY_LAG]
        elig = (d["obs_count"].loc[sd] >= prereg.MIN_HISTORY_DAYS) & \
               (d["staleness"].loc[sd] <= prereg.FFILL_LIMIT_SESSIONS)
        names = [b for b in d["bases"]
                 if elig[b] and listed.get(b) is not None and listed[b] <= rd]
        new_w = {n: 1.0 / len(names) for n in names} if names else {}
        cost = fee_side * engine.turnover(prev_w, new_w)
        carry = (band * sum(new_w.values())
                 + sum(w * d["yields"][n] for n, w in new_w.items())) * 7.0 / 365.0
        gross = sum(w * weekly_ret[n].iloc[wi] for n, w in new_w.items()
                    if not np.isnan(weekly_ret[n].iloc[wi]))
        rets.append(gross - cost - carry)
        prev_w = new_w
    ser = pd.Series(rets, index=grid[1:])
    return ser


def realised_funding() -> dict:
    """Annualised realised funding per symbol from the scanner's 90-day
    history: sum of settlements over the actual span, scaled to a year."""
    blob = json.loads((SCANNER / "funding_history.json").read_text(encoding="utf-8"))
    hist = blob.get("history", {})
    out = {}
    for sym, rows in hist.items():
        if len(rows) < 10:
            continue
        ts = [int(t) for t, _ in rows]
        rates = [float(r) for _, r in rows]
        span_days = (max(ts) - min(ts)) / 86_400_000
        if span_days <= 5:
            continue
        out[sym] = sum(rates) / span_days * 365 * 100
    return out


def main() -> int:
    d = engine.load_inputs()
    listed = onboard_dates()
    edge = prereg.FUNDING_BAND_ANN[-1]
    first_live = min(listed.values())
    umap = json.loads((ROOT / prereg.UNIVERSE_MAP).read_text(encoding="utf-8"))["rows"]
    name_of = {b: (e.get("vendor_name") or b) for b, e in umap.items()}

    rot_ser, _, _ = run_with_listing_gate(d, listed, K, CAP, edge)
    bask_ser = basket_with_listing_gate(d, listed, edge)
    bench = d["usd_ff"]["SPY"].reindex(rot_ser.index).ffill().pct_change().fillna(0.0)

    era = lambda s: s[s.index >= first_live]  # noqa: E731
    like = {
        "rotation_K10_gated": engine.stats_from_weekly(era(rot_ser)),
        "equal_weight_basket_gated": engine.stats_from_weekly(era(bask_ser)),
        "spy_buy_and_hold": engine.stats_from_weekly(era(bench)),
    }

    # ---- empirical funding --------------------------------------------------
    fund = realised_funding()
    tradfi = {s: v for s, v in fund.items()
              if s.replace("USDT", "") in umap and umap[s.replace("USDT", "")].get("cluster") != "commodity"}
    universe_vals = sorted(tradfi.values())
    # What a momentum book actually holds today, and what it pays.
    orders = json.loads((ROOT / "data" / "order_list_today.json").read_text(encoding="utf-8"))
    picks = [o["symbol"] for o in orders.get("orders", [])]
    picked = {s: tradfi[s] for s in picks if s in tradfi}
    # And the top decile by trend, whether or not it passed the funding block.
    detail = json.loads((ROOT / "data" / "payload_detail.json").read_text(encoding="utf-8"))
    ranked = [r["base"] + "USDT" for r in detail.get("ranked_now", [])[:20]]
    top_trend = {s: tradfi[s] for s in ranked if s in tradfi}

    med = lambda v: round(float(np.median(list(v))), 1) if len(v) else None  # noqa: E731
    mean = lambda v: round(float(np.mean(list(v))), 1) if len(v) else None   # noqa: E731
    funding = {
        "n_contracts_measured": len(tradfi),
        "universe_median_ann_pct": med(universe_vals),
        "universe_mean_ann_pct": mean(universe_vals),
        "universe_p90_ann_pct": round(float(np.percentile(universe_vals, 90)), 1) if universe_vals else None,
        "book_today_median_ann_pct": med(picked.values()),
        "book_today_mean_ann_pct": mean(picked.values()),
        "top20_trend_median_ann_pct": med(top_trend.values()),
        "top20_trend_mean_ann_pct": mean(top_trend.values()),
        "book_today": sorted(({"symbol": s, "name": name_of.get(s.replace("USDT", ""), s),
                               "funding_ann_pct": round(v, 1)} for s, v in picked.items()),
                             key=lambda r: -r["funding_ann_pct"]),
        "band_assumed": [b * 100 for b in prereg.FUNDING_BAND_ANN],
    }

    eq = lambda s: [round(float(v), 5) for v in (1.0 + s).cumprod().values]  # noqa: E731
    out = {"computed_at_utc": datetime.now(timezone.utc).isoformat(),
           "window_from": str(first_live.date()),
           "weeks": int(len(era(rot_ser))),
           "like_for_like": like, "funding": funding,
           "series": {
               "dates": [t.strftime("%Y-%m-%d") for t in era(rot_ser).index],
               "rotation": eq(era(rot_ser)),
               "basket": eq(era(bask_ser)),
               "spy": eq(era(bench)),
           }}
    (ROOT / "data" / "honest_window.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"=== LIKE-FOR-LIKE, all gated by actual listing date ({out['window_from']} on, {out['weeks']} weeks) ===")
    for k_, v in like.items():
        print(f"  {k_:<28} Sharpe {v['sharpe']:+.2f}  total {v['total_return']*100:+6.1f}%  MaxDD {v['max_dd']*100:6.1f}%")
    print()
    print(f"=== REALISED FUNDING, {funding['n_contracts_measured']} live contracts (90d history, annualised) ===")
    print(f"  universe   median {funding['universe_median_ann_pct']:+.1f}%/yr   mean {funding['universe_mean_ann_pct']:+.1f}%/yr   p90 {funding['universe_p90_ann_pct']:+.1f}%/yr")
    print(f"  top-20 by trend  median {funding['top20_trend_median_ann_pct']}%/yr  mean {funding['top20_trend_mean_ann_pct']}%/yr")
    print(f"  today's book     median {funding['book_today_median_ann_pct']}%/yr  mean {funding['book_today_mean_ann_pct']}%/yr")
    print(f"  band assumed in the backtest: {funding['band_assumed']} %/yr")
    for r in funding["book_today"]:
        print(f"    {r['name'][:32]:<32} {r['funding_ann_pct']:+7.1f}%/yr")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
