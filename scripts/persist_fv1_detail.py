"""FV-1 detail for the dashboard: the signed construction's HISTORY (seen
data, labelled) and its full rotation ledger with company names.

Basis per FV-1 implementation note 1: cash-equity reconstruction from the
filed KT-2 series — add back the perp financing charge using the per-week
invested fraction; dividends excluded (conservative ~1.5-2pp/yr). Blend =
30% rotation / 70% T-bills, monthly reset to weight. Hurdle line = T-bill
+2pp compounded weekly. SPY price-only for context.

Run: python scripts/persist_fv1_detail.py -> data/fv1_detail.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import killtest2_engine as E2  # noqa: E402
import prereg_killtest2 as P2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
W = 0.30
MARGIN = 0.02
MID = 0.03


def compute_history():
    """One shared code path for the display and the weekly tracker: the
    cash-basis rotation, the 30/70 blend (monthly reset), bills, and the
    per-week diagnostics from the frozen engine."""
    px_raw = pd.read_parquet(DATA / "killtest2_prices.parquet")
    dvol = pd.read_parquet(DATA / "killtest2_dollarvol.parquet")
    rates = pd.read_parquet(DATA / "killtest2_rates.parquet")["rf"]
    meta = json.loads((DATA / "killtest2_meta.json").read_text(encoding="utf-8"))["meta"]
    sectors = {s: (v.get("sector") or "unclassified") for s, v in meta.items()}
    weeks, _, _ = E2.precompute(px_raw, dvol, rates, sectors)
    net, diags = E2.simulate(weeks, sectors, "gics", MID, collect=True)

    # cash-equity reconstruction: add back (rf + premium) x invested x 7/365
    inv = pd.Series([d["invested"] for d in diags], index=net.index)
    rf = pd.Series([w["rf"] for w in weeks], index=net.index)
    cash_basis = net + (rf + MID) * inv * 7.0 / 365.0
    bill_w = rf * 7.0 / 365.0

    # 30/70 blend with monthly reset to weight
    blend, we = [], W
    month = None
    for dt, r_rot, r_bill in zip(cash_basis.index, cash_basis.values, bill_w.values):
        if month is not None and dt.month != month:
            we = W
        month = dt.month
        r = we * r_rot + (1 - we) * r_bill
        blend.append(r)
        we = we * (1 + r_rot) / (1 + r) if (1 + r) != 0 else W
    blend = pd.Series(blend, index=cash_basis.index)
    return {"px_raw": px_raw, "sectors": sectors, "diags": diags,
            "cash_basis": cash_basis, "blend": blend, "bill_w": bill_w}


def main() -> int:
    H = compute_history()
    diags, cash_basis, blend, bill_w = H["diags"], H["cash_basis"], H["blend"], H["bill_w"]
    sectors, px_raw = H["sectors"], H["px_raw"]
    inv = pd.Series([d["invested"] for d in diags], index=cash_basis.index)

    import norgatedata as nd
    spy = nd.price_timeseries("SPY", stock_price_adjustment_setting=nd.StockPriceAdjustmentType.CAPITAL,
                              start_date=P2.UNIVERSE_START, format="pandas-dataframe")["Close"].astype(float)
    spy.index = pd.to_datetime(spy.index).tz_localize(None)
    spy_w = spy.reindex(px_raw.index).ffill().reindex(cash_basis.index).pct_change().fillna(0.0)

    def stats(r):
        eq = (1 + r).cumprod()
        dd = float((eq / eq.cummax() - 1).min())
        yrs = len(r) / 52
        cagr = float(eq.iloc[-1] ** (1 / yrs) - 1)
        sd = r.std()
        return {"cagr": round(cagr, 4), "max_dd": round(dd, 4),
                "sharpe": round(float(r.mean() / sd * (52 ** 0.5)), 3) if sd > 0 else 0.0}

    eqs = {k: [round(float(v), 5) for v in (1 + s).cumprod().values]
           for k, s in (("rotation", cash_basis), ("blend", blend),
                        ("hurdle", bill_w + MARGIN * 7 / 365), ("spy", spy_w))}

    # longer-term stats: trailing horizons on the simulated history (SEEN),
    # refreshed weekly by the tracker so the windows roll forward with it
    def horizon_stats(s, bills, n):
        r = s.tail(n) if n else s
        b = bills.tail(n) if n else bills
        eq = (1 + r).cumprod()
        yrs = len(r) / 52.0
        cagr = float(eq.iloc[-1] ** (1 / yrs) - 1)
        bill_cagr = float((1 + b).prod() ** (1 / yrs) - 1)
        dd = float((eq / eq.cummax() - 1).min())
        sd = r.std()
        return {"cagr": round(cagr, 4), "excess": round(cagr - bill_cagr, 4),
                "beats_hurdle": bool(cagr - bill_cagr >= MARGIN),
                "max_dd": round(dd, 4), "vol": round(float(sd * (52 ** 0.5)), 4),
                "sharpe": round(float(r.mean() / sd * (52 ** 0.5)), 3) if sd > 0 else 0.0}

    horizons = []
    for label, n in (("1y", 52), ("3y", 156), ("5y", 260), ("10y", 520), ("Full", None)):
        if n and len(blend) < n:
            continue
        horizons.append({"label": label,
                         "blend": horizon_stats(blend, bill_w, n),
                         "rotation": horizon_stats(cash_basis, bill_w, n),
                         "spy": horizon_stats(spy_w, bill_w, n)})

    # names for every symbol that ever appears
    all_syms = sorted({n for d in diags for n in d["held"]})
    names = {}
    for s in all_syms:
        try:
            nm = nd.security_name(s) or s
        except Exception:  # noqa: BLE001
            nm = s
        names[s] = nm.removesuffix(" Common").removesuffix(" Class A")

    # ledger: entries and exits, newest first
    ledger, prev = [], set()
    for d in diags:
        held = set(d["held"])
        for s in sorted(prev - held):
            ledger.append({"date": d["date"].strftime("%Y-%m-%d"), "side": "sell",
                           "sym": s, "name": names.get(s, s), "sector": sectors.get(s, "—")})
        for s in sorted(held - prev):
            ledger.append({"date": d["date"].strftime("%Y-%m-%d"), "side": "buy",
                           "sym": s, "name": names.get(s, s), "sector": sectors.get(s, "—")})
        prev = held
    ledger.reverse()

    # contiguous spans where the gate held the book fully in cash — the
    # chart's shaded bands (the analogue of the bte page's RISK_OFF bands)
    cash_spans, span_start, span_end = [], None, None
    for d in diags:
        if d["invested"] == 0:
            if span_start is None:
                span_start = d["date"]
            span_end = d["date"]
        elif span_start is not None:
            cash_spans.append([span_start.strftime("%Y-%m-%d"), span_end.strftime("%Y-%m-%d")])
            span_start = None
    if span_start is not None:
        cash_spans.append([span_start.strftime("%Y-%m-%d"), span_end.strftime("%Y-%m-%d")])

    last = diags[-1]
    out = {"computed_at_utc": datetime.now(timezone.utc).isoformat(),
           "label": "SEEN data - the record of the design, not validation; cash-equity basis, dividends excluded",
           "w": W, "margin": MARGIN,
           "dates": [t.strftime("%Y-%m-%d") for t in cash_basis.index],
           "equity": eqs,
           "stats": {"rotation": stats(cash_basis), "blend": stats(blend), "spy": stats(spy_w)},
           "horizons": horizons,
           "cash_spans": cash_spans,
           "n_trades_total": len(ledger),
           "trades_per_week": round(len(ledger) / len(diags), 2),
           "pct_weeks_in_cash": round(float((inv == 0).mean() * 100), 1),
           "ledger_recent": ledger[:400],
           "current": {"asof": last["date"].strftime("%Y-%m-%d"), "breadth": round(last["breadth"], 3),
                       "picks": [{"sym": s, "name": names.get(s, s), "sector": sectors.get(s, "—")}
                                 for s in last["held"]]}}
    (DATA / "fv1_detail.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"weeks {len(diags)} | trades {len(ledger)} ({out['trades_per_week']}/wk) | in cash {out['pct_weeks_in_cash']}%")
    print("stats:", {k: v for k, v in out["stats"].items()})
    print(f"current picks ({out['current']['asof']}):")
    for p in out["current"]["picks"]:
        print(f"  {p['name'][:40]:<40} {p['sym']:<8} {p['sector']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
