"""MEASUREMENT — the cash + margin blend over the longest clean window, with
implementation drag. No hypothesis, no bars, no verdict: a fixed-weight
two-asset blend has no parameters to fit, so every row is reported and none
is promoted. Feeds the owner's margin/horizon choice at the 2026-09-30
command-centre review; extends the 2006-start descriptive read
(data/hurdle_read.json) back to 1995, adding the 2000-02 bust.

Construction, frozen before running:
  * SPY total return (Norgate TOTALRETURN) and price return (CAPITAL); the
    weekly dividend component = TR minus PR, and withholding applies to that
    component only, when positive.
  * Cash leg = 3-month T-bill (^IRX, percent -> fraction), accrued weekly.
  * Blends w in {0,10,20,30,40,50,100}% equity, weekly rebalanced; the
    weekly-vs-monthly rebalance difference is MEASURED and reported, not
    assumed away.
  * Implementation scenarios (today's fees applied across history, stated):
      UCITS (Irish):  equity WHT 15%, bill interest 0% (portfolio-interest
                      exemption), TER 7bp equity / 10bp cash
      US-domiciled:   equity WHT 30%, bill distributions 0% (QII), TER 9bp
                      equity / 14bp cash
  * Metrics per row: net CAGR, excess over the T-bill, MaxDD, share of
    rolling 3y and 5y windows with annualised excess below +1/+2/+3pp,
    worst 3y excess. Sub-period split 1995-2005 / 2006-2026 for context.

Run: python scripts/measure_hurdle_blend.py -> data/hurdle_blend_measurement.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from killtest_common import weekly_grid  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEIGHTS = (0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 1.0)
SCEN = {"ucits": {"wht_div": 0.15, "wht_int": 0.0, "ter_eq": 0.0007, "ter_cash": 0.0010},
        "us_domiciled": {"wht_div": 0.30, "wht_int": 0.0, "ter_eq": 0.0009, "ter_cash": 0.0014}}
W3, W5 = 156, 260


def load_series():
    import norgatedata as nd
    import yfinance as yf
    tr = nd.price_timeseries("SPY", stock_price_adjustment_setting=nd.StockPriceAdjustmentType.TOTALRETURN,
                             format="pandas-dataframe")["Close"].astype(float)
    pr = nd.price_timeseries("SPY", stock_price_adjustment_setting=nd.StockPriceAdjustmentType.CAPITAL,
                             format="pandas-dataframe")["Close"].astype(float)
    for s in (tr, pr):
        s.index = pd.to_datetime(s.index).tz_localize(None)
    r = yf.download("^IRX", start="1994-01-01", progress=False, auto_adjust=False)["Close"]
    if hasattr(r, "columns"):
        r = r.iloc[:, 0]
    r = r.dropna()
    r.index = pd.to_datetime(r.index).tz_localize(None)
    rf_daily = (r / 100.0)
    start = max(tr.index.min(), rf_daily.index.min()) + pd.Timedelta(days=30)
    sessions = tr.index[tr.index >= start]
    g = weekly_grid(sessions)
    tr_w = tr.reindex(g).pct_change().dropna()
    pr_w = pr.reindex(g).pct_change().reindex(tr_w.index)
    rf_w = rf_daily.reindex(sessions).ffill().reindex(tr_w.index) * 7.0 / 365.0
    div_w = (tr_w - pr_w).clip(lower=0.0)
    return tr_w, pr_w, div_w, rf_w


def blend_returns(pr_w, div_w, rf_w, w, scen, rebalance_every=1):
    eq_net = pr_w + div_w * (1 - scen["wht_div"]) - scen["ter_eq"] / 52.0
    cash_net = rf_w * (1 - scen["wht_int"]) - scen["ter_cash"] / 52.0
    if rebalance_every == 1:
        return w * eq_net + (1 - w) * cash_net
    # drifting weights between rebalances
    out, we = [], w
    for i, (e, c) in enumerate(zip(eq_net.values, cash_net.values)):
        r = we * e + (1 - we) * c
        out.append(r)
        we = we * (1 + e) / (1 + r) if (1 + r) != 0 else w
        if (i + 1) % rebalance_every == 0:
            we = w
    return pd.Series(out, index=eq_net.index)


def row_stats(b, rf_w):
    eq, eqr = (1 + b).cumprod(), (1 + rf_w).cumprod()
    yrs = len(b) / 52.0
    cagr = float(eq.iloc[-1] ** (1 / yrs) - 1)
    rcagr = float(eqr.iloc[-1] ** (1 / yrs) - 1)
    dd = float((eq / eq.cummax() - 1).min())

    def roll(win):
        ba = (eq.values[win:] / eq.values[:-win]) ** (52 / win) - 1
        ra = (eqr.values[win:] / eqr.values[:-win]) ** (52 / win) - 1
        ex = ba - ra
        return {"below_1pp_pct": round(float((ex < 0.01).mean() * 100), 1),
                "below_2pp_pct": round(float((ex < 0.02).mean() * 100), 1),
                "below_3pp_pct": round(float((ex < 0.03).mean() * 100), 1),
                "worst_excess_ann": round(float(ex.min()), 4)}

    return {"cagr": round(cagr, 4), "excess_cagr": round(cagr - rcagr, 4),
            "max_dd": round(dd, 4), "roll_3y": roll(W3), "roll_5y": roll(W5)}


def main() -> int:
    tr_w, pr_w, div_w, rf_w = load_series()
    print(f"window {tr_w.index.min().date()} -> {tr_w.index.max().date()} ({len(tr_w)} weeks)")
    out = {"computed_at_utc": datetime.now(timezone.utc).isoformat(),
           "label": "MEASUREMENT - no verdict; fixed-weight blends, every row reported",
           "window": {"first": str(tr_w.index.min().date()), "last": str(tr_w.index.max().date()),
                      "n_weeks": int(len(tr_w))},
           "assumptions": {"scenarios": SCEN, "rebalance": "weekly; ~monthly drift delta measured",
                           "fees_note": "today's TERs applied across history",
                           "rates": "^IRX percent->fraction, weekly accrual 7/365"},
           "scenarios": {}}
    for name, scen in SCEN.items():
        rows = {}
        for w in WEIGHTS:
            rows[f"w{int(w * 100)}"] = row_stats(blend_returns(pr_w, div_w, rf_w, w, scen), rf_w)
        out["scenarios"][name] = rows
    # weekly vs ~monthly rebalance, 30% blend, UCITS
    a = row_stats(blend_returns(pr_w, div_w, rf_w, 0.30, SCEN["ucits"]), rf_w)
    m = row_stats(blend_returns(pr_w, div_w, rf_w, 0.30, SCEN["ucits"], rebalance_every=4), rf_w)
    out["rebalance_delta_w30"] = {"weekly_cagr": a["cagr"], "monthly4w_cagr": m["cagr"],
                                  "delta_bp_pa": round((a["cagr"] - m["cagr"]) * 10_000, 1)}
    # sub-periods, 30% UCITS
    b30 = blend_returns(pr_w, div_w, rf_w, 0.30, SCEN["ucits"])
    cut = pd.Timestamp("2006-01-01")
    out["subperiods_w30_ucits"] = {
        "1995_2005": row_stats(b30[b30.index < cut], rf_w[rf_w.index < cut]),
        "2006_2026": row_stats(b30[b30.index >= cut], rf_w[rf_w.index >= cut])}
    # series for the dashboard chart: rolling 3y annualised excess, w20/30/40 UCITS
    chart = {"dates": None}
    for w in (0.20, 0.30, 0.40):
        b = blend_returns(pr_w, div_w, rf_w, w, SCEN["ucits"])
        eq, eqr = (1 + b).cumprod(), (1 + rf_w).cumprod()
        ex = (eq.values[W3:] / eq.values[:-W3]) ** (52 / W3) - 1 \
            - ((eqr.values[W3:] / eqr.values[:-W3]) ** (52 / W3) - 1)
        if chart["dates"] is None:
            chart["dates"] = [d.strftime("%Y-%m-%d") for d in b.index[W3:]]
        chart[f"w{int(w * 100)}"] = [round(float(v), 4) for v in ex]
    out["chart_roll3y_excess"] = chart
    (DATA / "hurdle_blend_measurement.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"rebalance delta (30%, weekly vs ~monthly): {out['rebalance_delta_w30']['delta_bp_pa']} bp/yr")
    print(f"{'row':<6} {'CAGR':>6} {'excess':>7} {'MaxDD':>7}  {'3y<1pp':>7} {'3y<2pp':>7} {'3y<3pp':>7} {'worst3y':>8}")
    for name in SCEN:
        print(f"--- {name}")
        for w in WEIGHTS:
            s = out["scenarios"][name][f"w{int(w * 100)}"]
            r3 = s["roll_3y"]
            print(f"w{int(w * 100):<5} {s['cagr']:>6.1%} {s['excess_cagr']:>+6.1f}pp"[:0] or
                  f"w{int(w*100):<5} {s['cagr']*100:>5.1f}% {s['excess_cagr']*100:>+6.1f}pp {s['max_dd']*100:>6.1f}%  "
                  f"{r3['below_1pp_pct']:>6.1f}% {r3['below_2pp_pct']:>6.1f}% {r3['below_3pp_pct']:>6.1f}% "
                  f"{s['roll_3y']['worst_excess_ann']*100:>+7.1f}pp")
    sp = out["subperiods_w30_ucits"]
    print(f"w30 UCITS 1995-2005: CAGR {sp['1995_2005']['cagr']*100:.1f}% excess {sp['1995_2005']['excess_cagr']*100:+.1f}pp DD {sp['1995_2005']['max_dd']*100:.1f}%")
    print(f"w30 UCITS 2006-2026: CAGR {sp['2006_2026']['cagr']*100:.1f}% excess {sp['2006_2026']['excess_cagr']*100:+.1f}pp DD {sp['2006_2026']['max_dd']*100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
