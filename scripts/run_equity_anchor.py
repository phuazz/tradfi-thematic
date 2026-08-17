"""Amendment 1 re-anchor: the equal-weight basket on EQUITY-ONLY membership
(commodity cluster excluded), same frozen cost model. An equal-weight basket
has no parameters, so this is a supplementary computation, not a new search.

Run: python scripts/run_equity_anchor.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine
import prereg

d = engine.load_inputs()
excluded = [b for b in d["bases"] if d["clusters"].get(b) == "commodity"]
d["bases"] = [b for b in d["bases"] if d["clusters"].get(b) != "commodity"]
d["usd_ff"] = d["usd_ff"][d["bases"]]
d["signal"] = d["signal"][d["bases"]]
d["obs_count"] = d["obs_count"][d["bases"]]
d["staleness"] = d["staleness"][d["bases"]]
print(f"equity-only bases: {len(d['bases'])} (excluded commodities: {excluded})")

out = {}
for band in prereg.FUNDING_BAND_ANN:
    _, st = engine.run_basket(d, 1.0, band)
    out[f"band_{band:g}"] = st
    print(f"  band {band:.0%}: Sharpe {st['sharpe']:+.2f}  CAGR {st['cagr']:+.1%}  "
          f"MaxDD {st['max_dd']:.1%}")
_, st2 = engine.run_basket(d, 2.0, prereg.FUNDING_BAND_ANN[-1])
out["band_0.06_2x"] = st2
print(f"  2x costs, band edge: Sharpe {st2['sharpe']:+.2f}")

p = Path(__file__).resolve().parent.parent / "data" / "equity_anchor.json"
p.write_text(json.dumps({"excluded": excluded, "results": out}, indent=1), encoding="utf-8")
print(f"wrote {p.name}")
