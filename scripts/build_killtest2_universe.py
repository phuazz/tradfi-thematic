"""KT-2 P0 — the held-out confirmation panel: Russell 1000 Current & Past,
survivorship-free, delisted included, price-only.

Writes:
  data/killtest2_prices.parquet     split-adjusted (PRICE-ONLY) closes, wide
  data/killtest2_dollarvol.parquet  daily dollar volume (Turnover, else V*C)
  data/killtest2_rates.parquet      3-month T-bill as a FRACTION, panel index
  data/killtest2_meta.json          GICS sector, first/last bar, delisted flag

Unlike KT-1 there is no index-membership step: the universe rule is the
point-in-time liquidity screen (top 250 by trailing 60-session median dollar
volume among names alive that day), computed by the engine per rebalance from
this panel. The Current & Past watchlist bounds the NAMESPACE; the screen
bounds the date-t universe.

NO STRATEGY LOGIC LIVES HERE, and nothing in this build reads a return.

Run: python scripts/build_killtest2_universe.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import norgatedata as nd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prereg_killtest2 as P2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ADJ = nd.StockPriceAdjustmentType.CAPITAL


def main() -> int:
    t0 = time.time()
    syms = sorted(set(nd.watchlist_symbols(P2.CONFIRM_WATCHLIST)))
    print(f"namespace ({P2.CONFIRM_WATCHLIST}): {len(syms)} symbols")

    closes, dvols, meta = {}, {}, {}
    fails = []
    for i, s in enumerate(syms, 1):
        try:
            df = nd.price_timeseries(s, stock_price_adjustment_setting=ADJ,
                                     start_date=P2.UNIVERSE_START,
                                     format="pandas-dataframe")
        except Exception as e:  # noqa: BLE001
            fails.append((s, type(e).__name__))
            continue
        if df is None or df.empty:
            fails.append((s, "empty"))
            continue
        closes[s] = df["Close"].astype(float)
        if "Turnover" in df.columns and df["Turnover"].notna().any():
            dvols[s] = df["Turnover"].astype(float)
        else:
            dvols[s] = df["Volume"].astype(float) * df["Close"].astype(float)
        try:
            sector = nd.classification_at_level(s, "GICS", "name", 1)
        except Exception:  # noqa: BLE001
            sector = None
        meta[s] = {"sector": sector,
                   "first_bar": df.index.min().strftime("%Y-%m-%d"),
                   "last_bar": df.index.max().strftime("%Y-%m-%d"),
                   "delisted": "-" in s and s.split("-")[-1].isdigit(),
                   "n_bars": int(len(df))}
        if i % 500 == 0:
            print(f"  [{i}/{len(syms)}] loaded ({time.time() - t0:.0f}s)")

    px = pd.DataFrame(closes).sort_index()
    px.index = pd.to_datetime(px.index).tz_localize(None)
    dv = pd.DataFrame(dvols).sort_index()
    dv.index = pd.to_datetime(dv.index).tz_localize(None)
    dv = dv.reindex(px.index)

    # Missing-symbol audit: only names that died BEFORE the window may be
    # absent. A 2005+ delisting with no data would be a survivorship hole.
    post = [(s, r) for s, r in fails
            if not (s.split("-")[-1].isdigit() and int(s.split("-")[-1][:4]) < 2005)]
    print(f"panel: {px.shape[0]} sessions x {px.shape[1]} symbols; "
          f"{len(fails)} unavailable of which {len(post)} are NOT pre-2005 delistings")
    if post:
        print("  !! investigate:", post[:10])

    import yfinance as yf
    r = yf.download(P2.RATE_SERIES, start=P2.UNIVERSE_START, progress=False,
                    auto_adjust=False)["Close"]
    if hasattr(r, "columns"):
        r = r.iloc[:, 0]
    r = r.dropna()
    r.index = pd.to_datetime(r.index).tz_localize(None)
    rates = (r / 100.0).rename("rf").reindex(px.index).ffill().bfill()

    px.to_parquet(DATA / "killtest2_prices.parquet")
    dv.to_parquet(DATA / "killtest2_dollarvol.parquet")
    rates.to_frame().to_parquet(DATA / "killtest2_rates.parquet")

    n_delisted = sum(1 for m in meta.values() if m["delisted"])
    out = {"built_at_utc": datetime.now(timezone.utc).isoformat(),
           "watchlist": P2.CONFIRM_WATCHLIST,
           "price_adjustment": "CAPITAL (split-adjusted, dividends excluded — price-only)",
           "n_symbols": int(px.shape[1]), "n_sessions": int(px.shape[0]),
           "first_session": px.index.min().strftime("%Y-%m-%d"),
           "last_session": px.index.max().strftime("%Y-%m-%d"),
           "n_delisted_symbols": n_delisted,
           "n_unavailable": len(fails),
           "n_unavailable_post2005": len(post),
           "unavailable_post2005": post[:40],
           "rate_units": "fraction (converted from quoted percent at load)",
           "rate_last": round(float(rates.iloc[-1]), 5),
           "meta": meta}
    (DATA / "killtest2_meta.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"delisted symbols carried: {n_delisted} of {px.shape[1]}")
    print(f"T-bill last: {rates.iloc[-1]:.4f} (fraction) · done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
