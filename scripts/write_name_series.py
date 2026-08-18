"""Per-name weekly series for the dashboard's click-through charts.

For every eligible base: weekly closes on the SIGNAL basis (adjusted closes,
local currency for KR/HK — the series the decision is actually made on) plus
the 200-day moving average computed on dailies and sampled weekly. The +5%
floor line is derived client-side as MA x 1.05, so the chart shows the rule,
not just the price. ~1MB inlined at 4 significant digits — the bte precedent
for data-carrying Pages files.

Run: python scripts/write_name_series.py -> data/name_series.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402
import prereg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def sig4(v):
    if v != v or v is None:
        return None
    return float(f"{v:.4g}")


def main() -> int:
    panel = pd.read_parquet(ROOT / "data" / "underlyings.parquet")
    umap = json.loads((ROOT / prereg.UNIVERSE_MAP).read_text(encoding="utf-8"))["rows"]

    us_index = panel[engine.US_ANCHOR].dropna().index
    us_index = us_index[us_index >= pd.Timestamp("2016-01-01")]
    grid = engine.weekly_grid(us_index)
    grid = grid[grid >= pd.Timestamp(prereg.BACKTEST_START)]

    px_out, ma_out = {}, {}
    for base, e in sorted(umap.items()):
        if e.get("status") != "verified" or e.get("levered_etp") or base in prereg.EXPLICIT_DROPS:
            continue
        cand = e.get("candidate")
        if cand not in panel.columns:
            continue
        ser = panel[cand].dropna()
        if ser.empty:
            continue
        daily = ser.reindex(us_index).ffill()
        ma = daily.rolling(prereg.MA_WINDOW, min_periods=prereg.MA_WINDOW).mean()
        px_out[base] = [sig4(v) for v in daily.reindex(grid).values]
        ma_out[base] = [sig4(v) for v in ma.reindex(grid).values]

    out = {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "weekly closes on the signal basis (adjusted; local ccy for KR/HK); ma200 sampled weekly from dailies; floor = ma x 1.05 client-side",
        "dates": [t.strftime("%Y-%m-%d") for t in grid],
        "px": px_out,
        "ma": ma_out,
    }
    p = ROOT / "data" / "name_series.json"
    p.write_text(json.dumps(out, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"wrote {p.name}: {len(px_out)} names x {len(out['dates'])} weeks, "
          f"{p.stat().st_size/1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
