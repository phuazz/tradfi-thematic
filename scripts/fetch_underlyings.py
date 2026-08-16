"""Phase 2 — underlying price panel for the 143 rotation-eligible names + FX.

Downloads daily adjusted closes (yfinance) from 2016-01-01 (two years of
warm-up ahead of the 2018 backtest start, for the 200d MA and the 252-day
ex-ante history rule) for every eligible candidate in the Phase 0 map, plus
KRW=X and HKD=X for the currency conversion the pre-registration specifies.

Cache: data/underlyings.parquet (gitignored — sizes; the committed artefact is
data/underlyings_coverage.json with per-name first/last bar and row counts, so
the panel a result was computed on is always reconstructible).

Run: python scripts/fetch_underlyings.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prereg  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = PROJECT_ROOT / prereg.UNIVERSE_MAP
PANEL_PATH = PROJECT_ROOT / "data" / "underlyings.parquet"
COVERAGE_PATH = PROJECT_ROOT / "data" / "underlyings_coverage.json"

FETCH_START = "2016-01-01"
FX_TICKERS = {"KRW=X", "HKD=X"}
BATCH = 25


def eligible_bases(rows: dict) -> dict[str, dict]:
    out = {}
    for base, e in rows.items():
        if e["status"] != "verified" or e["levered_etp"]:
            continue
        if base in prereg.EXPLICIT_DROPS:
            continue
        if not e.get("first_bar"):
            continue
        out[base] = e
    return out


def main() -> int:
    rows = json.loads(MAP_PATH.read_text(encoding="utf-8"))["rows"]
    elig = eligible_bases(rows)
    tickers = sorted({e["candidate"] for e in elig.values()} | FX_TICKERS)
    print(f"Eligible bases: {len(elig)}; tickers to fetch: {len(tickers)}")

    frames = {}
    for i in range(0, len(tickers), BATCH):
        chunk = tickers[i:i + BATCH]
        data = yf.download(chunk, start=FETCH_START, interval="1d",
                           auto_adjust=True, progress=False, group_by="ticker",
                           threads=True)
        for t in chunk:
            try:
                ser = data[t]["Close"].dropna() if len(chunk) > 1 else data["Close"].dropna()
            except (KeyError, TypeError):
                continue
            if len(ser):
                frames[t] = ser
        print(f"  [{min(i + BATCH, len(tickers))}/{len(tickers)}] fetched")
        time.sleep(1.0)

    panel = pd.DataFrame(frames).sort_index()
    panel.index = pd.to_datetime(panel.index).tz_localize(None)
    PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL_PATH)

    coverage = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "fetch_start": FETCH_START,
        "n_tickers_requested": len(tickers),
        "n_tickers_with_data": int(panel.shape[1]),
        "missing": sorted(set(tickers) - set(panel.columns)),
        "per_ticker": {
            t: {"first": panel[t].first_valid_index().strftime("%Y-%m-%d"),
                "last": panel[t].last_valid_index().strftime("%Y-%m-%d"),
                "n": int(panel[t].notna().sum())}
            for t in panel.columns
        },
    }
    COVERAGE_PATH.write_text(json.dumps(coverage, indent=1), encoding="utf-8")
    print(f"Panel: {panel.shape[0]} rows x {panel.shape[1]} tickers -> {PANEL_PATH.name}")
    print(f"Missing entirely: {coverage['missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
