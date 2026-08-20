"""P0 — the honest universe: survivorship-free, point-in-time, delisted included.

Builds, for the S&P 500 + Nasdaq-100 "Current & Past" union:
  data/killtest_prices.parquet      split-adjusted (PRICE-ONLY) closes, wide
  data/killtest_members.parquet     daily point-in-time membership, boolean
  data/killtest_dollarvol.parquet   daily dollar volume (for the robustness arm)
  data/killtest_meta.json           GICS sector, first/last bar, delisted flag
  data/killtest_rates.parquet       3-month T-bill, converted to a FRACTION

Two properties this file exists to guarantee, and which the guards then verify:
  * a name is in the universe on date t only if it was ACTUALLY in the index on
    date t — membership is read per date, never as a current snapshot;
  * names that died are present with their real history and their real ending.

Prices use StockPriceAdjustmentType.CAPITAL — splits adjusted, dividends
excluded — because a perpetual future tracks price, not total return. This is
exact, replacing the estimated dividend subtraction the tradfi study used.

NO STRATEGY LOGIC LIVES HERE. P0 produces the universe and nothing else.

Run: python scripts/build_killtest_universe.py
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
import prereg_killtest as P  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ADJ = nd.StockPriceAdjustmentType.CAPITAL


def universe_symbols() -> list[str]:
    syms: set[str] = set()
    for wl in P.PRIMARY_WATCHLISTS:
        syms.update(nd.watchlist_symbols(wl))
    return sorted(syms)


def main() -> int:
    t0 = time.time()
    syms = universe_symbols()
    print(f"universe (current & past union): {len(syms)} symbols")

    closes, dvols, meta = {}, {}, {}
    fails = []
    for i, s in enumerate(syms, 1):
        try:
            df = nd.price_timeseries(s, stock_price_adjustment_setting=ADJ,
                                     start_date=P.UNIVERSE_START,
                                     format="pandas-dataframe")
        except Exception as e:  # noqa: BLE001
            fails.append((s, f"{type(e).__name__}"))
            continue
        if df is None or df.empty:
            fails.append((s, "empty"))
            continue
        closes[s] = df["Close"].astype(float)
        if "Turnover" in df.columns:
            dvols[s] = df["Turnover"].astype(float)
        elif "Volume" in df.columns:
            dvols[s] = (df["Volume"].astype(float) * df["Close"].astype(float))
        try:
            sector = nd.classification_at_level(s, "GICS", "name", 1)
        except Exception:  # noqa: BLE001
            sector = None
        meta[s] = {
            "sector": sector,
            "first_bar": df.index.min().strftime("%Y-%m-%d"),
            "last_bar": df.index.max().strftime("%Y-%m-%d"),
            # A dated suffix is Norgate's delisted convention (e.g. AAMRQ-201312).
            "delisted": "-" in s and s.split("-")[-1].isdigit(),
            "n_bars": int(len(df)),
        }
        if i % 250 == 0:
            print(f"  [{i}/{len(syms)}] prices loaded ({time.time() - t0:.0f}s)")

    px = pd.DataFrame(closes).sort_index()
    px.index = pd.to_datetime(px.index).tz_localize(None)
    dv = pd.DataFrame(dvols).sort_index()
    dv.index = pd.to_datetime(dv.index).tz_localize(None)
    print(f"price panel: {px.shape[0]} sessions x {px.shape[1]} symbols; {len(fails)} unavailable")

    # ---- point-in-time membership -----------------------------------------
    print("reading point-in-time index membership ...")
    member = pd.DataFrame(False, index=px.index, columns=px.columns)
    got = 0
    for i, s in enumerate(px.columns, 1):
        flag = None
        for idx in P.PRIMARY_INDICES:
            try:
                ts = nd.index_constituent_timeseries(
                    s, idx, start_date=P.UNIVERSE_START, format="pandas-dataframe")
            except Exception:  # noqa: BLE001
                continue
            if ts is None or ts.empty:
                continue
            col = ts.iloc[:, 0].astype(float)
            col.index = pd.to_datetime(col.index).tz_localize(None)
            flag = col if flag is None else flag.add(col, fill_value=0.0)
        if flag is not None:
            member[s] = (flag.reindex(px.index).fillna(0.0) > 0).values
            got += 1
        if i % 250 == 0:
            print(f"  [{i}/{len(px.columns)}] membership ({time.time() - t0:.0f}s)")
    print(f"membership series found for {got} of {px.shape[1]} symbols")

    # ---- rates -------------------------------------------------------------
    import yfinance as yf
    r = yf.download(P.RATE_SERIES, start=P.UNIVERSE_START, progress=False, auto_adjust=False)["Close"]
    if hasattr(r, "columns"):
        r = r.iloc[:, 0]
    r = r.dropna()
    r.index = pd.to_datetime(r.index).tz_localize(None)
    rates = (r / 100.0).rename("rf")          # PERCENT -> FRACTION, once, here
    rates = rates.reindex(px.index).ffill().bfill()

    DATA.mkdir(exist_ok=True)
    px.to_parquet(DATA / "killtest_prices.parquet")
    member.to_parquet(DATA / "killtest_members.parquet")
    dv.to_parquet(DATA / "killtest_dollarvol.parquet")
    rates.to_frame().to_parquet(DATA / "killtest_rates.parquet")

    n_delisted = sum(1 for m in meta.values() if m["delisted"])
    members_per_day = member.sum(axis=1)
    cov = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "price_adjustment": "CAPITAL (split-adjusted, dividends excluded — price-only)",
        "n_symbols": int(px.shape[1]),
        "n_sessions": int(px.shape[0]),
        "first_session": px.index.min().strftime("%Y-%m-%d"),
        "last_session": px.index.max().strftime("%Y-%m-%d"),
        "n_delisted_symbols": n_delisted,
        "n_unavailable": len(fails),
        "unavailable": fails[:40],
        "members_first_day": int(members_per_day.iloc[0]),
        "members_last_day": int(members_per_day.iloc[-1]),
        "members_min": int(members_per_day.min()),
        "members_max": int(members_per_day.max()),
        "rate_series": P.RATE_SERIES,
        "rate_units": "fraction (converted from quoted percent at load)",
        "rate_last": round(float(rates.iloc[-1]), 5),
        "meta": meta,
    }
    (DATA / "killtest_meta.json").write_text(json.dumps(cov, indent=1), encoding="utf-8")

    print()
    print(f"delisted symbols carried: {n_delisted} of {px.shape[1]}")
    print(f"index members per day: first {cov['members_first_day']}, last {cov['members_last_day']}, "
          f"min {cov['members_min']}, max {cov['members_max']}")
    print(f"T-bill last: {rates.iloc[-1]:.4f} (fraction)")
    print(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
