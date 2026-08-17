"""Persist the time series the dashboard charts — a presentation-layer
extraction reusing the FROZEN engine functions unchanged (no new research, no
new parameters; every series here was implied by the filed Phase 2 runs).

Writes data/phase2_series.json:
  dates              weekly grid (Friday closes)
  primary_b0/b3/b6   primary cell (K=5 cap=2) net equity, 1x costs, per band
  basket_b6          full-menu EW basket net equity, band edge
  basket_eq_b6       EQUITY-ONLY EW basket net equity, band edge (Amendment 1)
  breadth            % of eligible universe above the +5% floor, per week
  eligible_n         eligible universe count, per week
  gated              sleeve-breadth gate weeks (bool)
  null_sharpes       the 1,000 null path Sharpes (frozen seed, recomputed
                     deterministically — identical to the filed distribution)

Run: python scripts/persist_series.py
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


def equity(ser: pd.Series) -> list:
    return [round(float(v), 5) for v in (1.0 + ser).cumprod().values]


def main() -> int:
    d = engine.load_inputs()
    edge = prereg.FUNDING_BAND_ANN[-1]
    k, cap = prereg.PRIMARY_CELL["k"], prereg.PRIMARY_CELL["cluster_cap"]

    out = {"computed_at_utc": datetime.now(timezone.utc).isoformat()}

    series = {}
    for band in prereg.FUNDING_BAND_ANN:
        ser, _, _ = engine.run_cell(d, k, cap, 1.0, band)
        series[f"primary_b{int(band*100)}"] = ser
    basket_ser, _ = engine.run_basket(d, 1.0, edge)
    series["basket_b6"] = basket_ser

    # Equity-only basket (Amendment 1 view) — same filter as run_equity_anchor.
    d_eq = engine.load_inputs()
    d_eq["bases"] = [b for b in d_eq["bases"] if d_eq["clusters"].get(b) != "commodity"]
    for key in ("usd_ff", "signal", "obs_count", "staleness"):
        d_eq[key] = d_eq[key][d_eq["bases"]]
    basket_eq_ser, _ = engine.run_basket(d_eq, 1.0, edge)
    series["basket_eq_b6"] = basket_eq_ser

    out["dates"] = [t.strftime("%Y-%m-%d") for t in series["basket_b6"].index]
    for name, ser in series.items():
        aligned = ser.reindex(series["basket_b6"].index)
        out[name] = equity(aligned.fillna(0.0))

    # Breadth, eligible count and gate state per week, from the same frozen
    # inputs the engine reads.
    breadth, elig_n, gated = [], [], []
    us_index = d["us_index"]
    grid = engine.weekly_grid(us_index)
    grid = grid[grid >= pd.Timestamp(prereg.BACKTEST_START)]
    for wi in range(1, len(grid)):
        rd = grid[wi - 1]
        pos = us_index.get_loc(rd)
        sd = us_index[pos - prereg.SIGNAL_DAY_LAG]
        sig_row = d["signal"].loc[sd]
        eligible = (d["obs_count"].loc[sd] >= prereg.MIN_HISTORY_DAYS) & \
                   (d["staleness"].loc[sd] <= prereg.FFILL_LIMIT_SESSIONS)
        elig = [n for n in sig_row.index if eligible[n] and not np.isnan(sig_row[n])]
        above = [n for n in elig if sig_row[n] > prereg.ENTRY_FLOOR]
        b = (len(above) / len(elig)) if elig else 0.0
        breadth.append(round(b, 4))
        elig_n.append(len(elig))
        gated.append(b < prereg.SLEEVE_BREADTH_GATE)
    out["breadth"], out["eligible_n"], out["gated"] = breadth, elig_n, gated

    # Null distribution — identical construction and seed as the filed run.
    rng = np.random.default_rng(prereg.NULL_SEED)
    weeks2 = engine.precompute_weeks(d)
    fee_side = prereg.FEE_RT_BPS / 2.0 / 10_000.0
    null_sharpes = []
    for p in range(prereg.NULL_PATHS):
        rets, prev = [], set()
        for w in weeks2:
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
        null_sharpes.append(round(float(arr.mean() / sd_ * np.sqrt(52)) if sd_ > 0 else 0.0, 3))
    out["null_sharpes"] = null_sharpes

    p = ROOT / "data" / "phase2_series.json"
    p.write_text(json.dumps(out, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"wrote {p.name}: {len(out['dates'])} weeks, "
          f"{len(null_sharpes)} null paths, {sum(gated)} gated weeks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
