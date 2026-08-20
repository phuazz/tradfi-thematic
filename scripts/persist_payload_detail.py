"""Detail series for the bte-style dashboard: the live payload's week-by-week
picks, its trade ledger, allocation-over-time, right-tail metrics and a
benchmark curve.

Everything here is EXTRACTION from the frozen engine — run_cell with
collect_picks, the same construction the verdict was filed on. No new
parameters, no re-fitting.

Writes data/payload_detail.json:
  weeks[]            date, picks[], breadth, n_eligible, gated
  ledger[]           date, action (buy/sell), name, base, cluster
  alloc              cluster weights per week (stacked-area input)
  ranked_now[]       today's ranked candidates with signal, cluster, held flag
  tail               right-tail metrics for payload / basket / benchmark
  bench              SPY weekly equity on the same basis
  monthly            payload monthly returns (calendar heatmap input)

Run: python scripts/persist_payload_detail.py
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
K, CAP = 10, 2
BENCH = "SPY"


def tail_metrics(rets: pd.Series) -> dict:
    """Right-tail / left-tail behaviour on the weekly basis used throughout."""
    r = rets.dropna()
    if r.empty:
        return {}
    eq = (1.0 + r).cumprod()
    dd = (eq / eq.cummax() - 1.0)
    ann = float(r.mean() * 52)
    downside = r[r < 0]
    sortino = float(r.mean() / downside.std() * np.sqrt(52)) if len(downside) and downside.std() > 0 else None
    maxdd = float(dd.min())
    return {
        "best_week": round(float(r.max()) * 100, 2),
        "worst_week": round(float(r.min()) * 100, 2),
        "pct_positive_weeks": round(float((r > 0).mean()) * 100, 1),
        "top_decile_mean": round(float(r[r >= r.quantile(0.9)].mean()) * 100, 2),
        "bottom_decile_mean": round(float(r[r <= r.quantile(0.1)].mean()) * 100, 2),
        "skew": round(float(r.skew()), 2),
        "sortino": round(sortino, 2) if sortino is not None else None,
        "calmar": round(ann / abs(maxdd), 2) if maxdd < 0 else None,
        "max_dd": round(maxdd * 100, 1),
        "worst_4wk": round(float(r.rolling(4).sum().min()) * 100, 2),
        "best_4wk": round(float(r.rolling(4).sum().max()) * 100, 2),
    }


def main() -> int:
    d = engine.load_inputs()
    umap = json.loads((ROOT / prereg.UNIVERSE_MAP).read_text(encoding="utf-8"))["rows"]
    name_of = {b: (e.get("vendor_name") or b) for b, e in umap.items()}
    edge = prereg.FUNDING_BAND_ANN[-1]

    ser, stats, picks_log = engine.run_cell(d, K, CAP, 1.0, edge, collect_picks=True)
    basket_ser, _ = engine.run_basket(d, 1.0, edge)

    # Weeks + ledger + allocation
    weeks, ledger, alloc_rows = [], [], []
    prev: set[str] = set()
    for row in picks_log:
        cur = set(row["picks"] or [])
        for b in sorted(prev - cur):
            ledger.append({"date": row["date"], "action": "sell", "base": b,
                           "name": name_of.get(b, b), "cluster": d["clusters"].get(b)})
        for b in sorted(cur - prev):
            ledger.append({"date": row["date"], "action": "buy", "base": b,
                           "name": name_of.get(b, b), "cluster": d["clusters"].get(b)})
        weeks.append({"date": row["date"], "picks": sorted(cur),
                      "breadth": round(row.get("breadth", 0.0), 4),
                      "n_eligible": row.get("n_eligible"),
                      "gated": not cur})
        cw: dict[str, float] = {}
        for b in cur:
            c = d["clusters"].get(b, "unclassified")
            cw[c] = cw.get(c, 0.0) + 1.0 / K
        alloc_rows.append(cw)
        prev = cur

    clusters_seen = sorted({c for r in alloc_rows for c in r})
    alloc = {"dates": [w["date"] for w in weeks], "clusters": clusters_seen,
             "series": {c: [round(r.get(c, 0.0) * 100, 2) for r in alloc_rows]
                        for c in clusters_seen}}

    # Today's ranked candidates (the live "signal" table)
    sd = d["us_index"][-1]
    sig_row = d["signal"].loc[sd]
    elig = (d["obs_count"].loc[sd] >= prereg.MIN_HISTORY_DAYS) & \
           (d["staleness"].loc[sd] <= prereg.FFILL_LIMIT_SESSIONS)
    live_picks = set(weeks[-1]["picks"]) if weeks else set()
    ranked = []
    for b in sig_row.index:
        if not elig[b] or np.isnan(sig_row[b]):
            continue
        ranked.append({"base": b, "name": name_of.get(b, b),
                       "cluster": d["clusters"].get(b),
                       "signal_pct": round(float(sig_row[b]) * 100, 2),
                       "above_floor": bool(sig_row[b] > prereg.ENTRY_FLOOR),
                       "selected": b in live_picks})
    ranked.sort(key=lambda r: -r["signal_pct"])
    for i, r in enumerate(ranked, 1):
        r["rank"] = i

    # Benchmark on the same weekly grid
    grid = pd.to_datetime([w["date"] for w in weeks])
    bench_eq = None
    if BENCH in d["usd_ff"].columns:
        bpx = d["usd_ff"][BENCH].reindex(grid).ffill()
        bench_ret = bpx.pct_change().fillna(0.0)
        bench_eq = [round(float(v), 5) for v in (1.0 + bench_ret).cumprod().values]

    # Monthly returns of the payload
    m = ser.copy()
    m.index = pd.to_datetime(m.index)
    monthly = (1.0 + m).resample("ME").prod() - 1.0
    monthly_out = [{"month": t.strftime("%Y-%m"), "ret": round(float(v) * 100, 2)}
                   for t, v in monthly.items()]

    out = {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "construction": f"K={K} cap={CAP}, band edge {edge:.0%}, 1x costs (frozen engine)",
        "signal_asof": str(sd.date()),
        "stats": stats,
        "weeks": weeks,
        "ledger": ledger[::-1],          # newest first for display
        "n_trades_total": len(ledger),
        "alloc": alloc,
        "ranked_now": ranked,
        "bench": {"name": BENCH, "equity": bench_eq},
        "tail": {
            "payload": tail_metrics(ser),
            "basket": tail_metrics(basket_ser),
            "benchmark": tail_metrics(d["usd_ff"][BENCH].reindex(grid).ffill().pct_change())
            if BENCH in d["usd_ff"].columns else {},
        },
        "monthly": monthly_out,
    }
    p = ROOT / "data" / "payload_detail.json"
    p.write_text(json.dumps(out, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"wrote {p.name}: {len(weeks)} weeks, {len(ledger)} trades, "
          f"{len(ranked)} ranked candidates, {p.stat().st_size/1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
