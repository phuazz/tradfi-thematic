"""DESIGN INPUT — drawdown anatomy of the KT-2 rotation. NOT a study.

Both US panels are SEEN: nothing computed here can validate anything, and no
configuration is searched. This is a post-mortem of the ALREADY-FILED series
(adopted GICS arm, band centre), asking one question: WHERE did the −49%
live, and what would any rotation of this class have needed to see in time?

Per episode (drawdowns beyond −15%): peak/trough/recovery dates, depth,
speed, the gate's behaviour (breadth path, weeks until the book actually
stood in cash), the share of the loss taken while invested, and the episode's
contribution at a SIZED weight (30% of a cash+rotation blend) — the number
that matters for the hurdle deployment.

Run: python scripts/diagnose_rotation_drawdowns.py -> data/rotation_dd_anatomy.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import killtest2_engine as E2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MID = 0.03
DD_EPISODE_FLOOR = -0.15
SIZED_W = 0.30


def main() -> int:
    px_raw = pd.read_parquet(DATA / "killtest2_prices.parquet")
    dvol = pd.read_parquet(DATA / "killtest2_dollarvol.parquet")
    rates = pd.read_parquet(DATA / "killtest2_rates.parquet")["rf"]
    meta = json.loads((DATA / "killtest2_meta.json").read_text(encoding="utf-8"))["meta"]
    sectors = {s: (v.get("sector") or "unclassified") for s, v in meta.items()}
    weeks, _, _ = E2.precompute(px_raw, dvol, rates, sectors)
    r, diags = E2.simulate(weeks, sectors, "gics", MID, collect=True)
    d = pd.DataFrame(diags).set_index("date")

    eq = (1.0 + r).cumprod()
    hwm = eq.cummax()
    dd = eq / hwm - 1.0

    episodes = []
    in_ep, trough, trough_i = False, 0.0, None
    peak_i = 0
    for i in range(len(dd)):
        if not in_ep and dd.iloc[i] < 0:
            in_ep, trough, trough_i = True, dd.iloc[i], i
            peak_i = i - 1 if i else 0
        elif in_ep:
            if dd.iloc[i] < trough:
                trough, trough_i = dd.iloc[i], i
            if dd.iloc[i] >= 0 or i == len(dd) - 1:
                if trough <= DD_EPISODE_FLOOR:
                    episodes.append((peak_i, trough_i, i, trough))
                in_ep = False
    out_eps = []
    for peak_i, trough_i, rec_i, depth in episodes:
        seg = r.iloc[peak_i + 1:trough_i + 1]
        dseg = d.iloc[peak_i + 1:trough_i + 1]
        invested_loss = float(seg[dseg["invested"].values > 0].sum())
        cash_weeks = int((dseg["invested"].values == 0).sum())
        first_cash = None
        for j, inv in enumerate(dseg["invested"].values):
            if inv == 0:
                first_cash = j + 1
                break
        recovered = bool(dd.iloc[rec_i] >= 0)
        out_eps.append({
            "peak": str(r.index[peak_i].date()),
            "trough": str(r.index[trough_i].date()),
            "recovered": str(r.index[rec_i].date()) if recovered else "not yet",
            "depth_pct": round(depth * 100, 1),
            "weeks_peak_to_trough": int(trough_i - peak_i),
            "weeks_to_recover": int(rec_i - trough_i) if recovered else None,
            "breadth_at_peak": round(float(d["breadth"].iloc[peak_i]), 2),
            "weeks_until_book_in_cash": first_cash,
            "weeks_in_cash_during_fall": cash_weeks,
            "loss_while_invested_pp": round(invested_loss * 100, 1),
            "sized_30pct_contribution_pp": round(depth * SIZED_W * 100, 1),
        })
    out_eps.sort(key=lambda e: e["depth_pct"])

    tot_weeks = len(r)
    out = {"computed_at_utc": datetime.now(timezone.utc).isoformat(),
           "label": "DESIGN INPUT - seen data, no verdict, no configuration searched",
           "series": "KT-2 adopted arm (GICS cap), band centre, as filed",
           "episodes_beyond_15pct": out_eps,
           "pct_weeks_in_cash_overall": round(float((d["invested"] == 0).mean() * 100), 1),
           "sized_note": f"sized contribution = episode depth x {SIZED_W:.0%} blend weight (T-bill leg adds back its accrual)"}
    (DATA / "rotation_dd_anatomy.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"weeks {tot_weeks}, in cash {out['pct_weeks_in_cash_overall']}% of all weeks")
    for e in out_eps:
        print(f"{e['peak']} -> {e['trough']}  {e['depth_pct']:>6}%  fall {e['weeks_peak_to_trough']:>3}w  "
              f"recover {e['weeks_to_recover']}w  breadth@peak {e['breadth_at_peak']:.2f}  "
              f"cash after {e['weeks_until_book_in_cash']}w  cash weeks {e['weeks_in_cash_during_fall']:>3}  "
              f"lost-invested {e['loss_while_invested_pp']:>6}pp  sized(30%) {e['sized_30pct_contribution_pp']:>5}pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
