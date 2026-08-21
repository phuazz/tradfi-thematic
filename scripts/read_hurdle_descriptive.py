"""DESCRIPTIVE READ — the filed series against an absolute 4%/yr USD hurdle.

This is NOT a study and files no verdict. It re-reads the ALREADY-DECLARED
cells (KT-2 adopted arm and basket at the band centre; KT-1 primary at the
band centre; SPY; T-bills) against a hurdle the owner stated on 2026-08-21
("beat 4% USD p.a."). No new configuration, parameter, or selection rule is
computed. Both panels are SEEN; nothing here may be cited as confirmation.

The decision-relevant statistics for an absolute hurdle are path statistics:
a 20-year CAGR above 4% is compatible with years spent below it, so the read
is rolling 3-year and 5-year windows, not the terminal number.

Run: python scripts/read_hurdle_descriptive.py -> data/hurdle_read.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HURDLE = 0.04                      # absolute, USD, per annum
W3, W5 = 156, 260                  # 3y and 5y in weeks


def path_stats(r: pd.Series) -> dict:
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min())
    years = len(r) / 52.0
    cagr = float(eq.iloc[-1] ** (1 / years) - 1.0)

    def roll(win):
        if len(r) <= win:
            return None
        g = eq.values[win:] / eq.values[:-win]
        ann = g ** (52.0 / win) - 1.0
        return {"pct_windows_below_hurdle": round(float((ann < HURDLE).mean() * 100), 1),
                "worst_ann": round(float(ann.min()), 4),
                "best_ann": round(float(ann.max()), 4)}

    return {"cagr": round(cagr, 4), "max_dd": round(dd, 4),
            "roll_3y": roll(W3), "roll_5y": roll(W5), "n_weeks": int(len(r))}


def main() -> int:
    out = {"computed_at_utc": datetime.now(timezone.utc).isoformat(),
           "hurdle_pa": HURDLE,
           "label": "DESCRIPTIVE — no verdict; both panels SEEN; declared cells only"}

    # --- KT-2 panel (Russell), adopted arm + basket at band centre -----------
    import killtest2_engine as E2
    px_raw = pd.read_parquet(DATA / "killtest2_prices.parquet")
    dvol = pd.read_parquet(DATA / "killtest2_dollarvol.parquet")
    rates = pd.read_parquet(DATA / "killtest2_rates.parquet")["rf"]
    meta = json.loads((DATA / "killtest2_meta.json").read_text(encoding="utf-8"))["meta"]
    sectors = {s: (v.get("sector") or "unclassified") for s, v in meta.items()}
    weeks, _, _ = E2.precompute(px_raw, dvol, rates, sectors)
    mid = 0.03
    rot2 = E2.simulate(weeks, sectors, "gics", mid)
    bask2 = E2.simulate(weeks, sectors, "gics", mid, mode="basket")
    out["kt2_rotation_mid"] = path_stats(rot2)
    out["kt2_basket_mid"] = path_stats(bask2)

    # SPY and T-bills on the same grid (context; SPY carries no costs/financing)
    import norgatedata as nd
    spy = nd.price_timeseries("SPY",
                              stock_price_adjustment_setting=nd.StockPriceAdjustmentType.CAPITAL,
                              start_date="2005-01-01", format="pandas-dataframe")["Close"].astype(float)
    spy.index = pd.to_datetime(spy.index).tz_localize(None)
    grid_dates = pd.DatetimeIndex([w["date"] for w in weeks])
    spy_w = spy.reindex(px_raw.index).ffill().reindex(grid_dates).pct_change().dropna()
    out["spy_price_only"] = path_stats(spy_w)
    rf_w = pd.Series([w["rf"] * 7.0 / 365.0 for w in weeks], index=grid_dates)
    out["tbill"] = path_stats(rf_w)

    # --- KT-1 panel (S&P+NDX), primary cell at band centre -------------------
    import killtest_engine as E1
    w1, sec1 = E1.precompute()
    rot1 = E1.simulate(w1, sec1, 10, 2, mid)
    idx1 = pd.to_datetime([w["date"] for w in w1])
    rot1.index = idx1
    out["kt1_rotation_mid"] = path_stats(rot1)

    (DATA / "hurdle_read.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"=== DESCRIPTIVE read vs {HURDLE:.0%}/yr absolute (no verdict) ===")
    for k in ("kt2_rotation_mid", "kt2_basket_mid", "kt1_rotation_mid", "spy_price_only", "tbill"):
        s = out[k]
        r3, r5 = s["roll_3y"], s["roll_5y"]
        print(f"{k:<18} CAGR {s['cagr']:+7.1%}  DD {s['max_dd']:6.1%}  "
              f"3y<hurdle {r3['pct_windows_below_hurdle']:5.1f}%  "
              f"5y<hurdle {r5['pct_windows_below_hurdle']:5.1f}%  worst5y {r5['worst_ann']:+7.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
