"""Phase 0 — mechanical half of the two-source universe map.

For every base in the seed TradFi roster (scanner tradfi_universe_log.json,
2026-08-16 snapshot), resolve a candidate underlying ticker and pull the vendor
record from yfinance: short/long name, sector, industry, quote type, exchange,
first-trade date, dividend yield. This is SOURCE TWO. Source one — the underlying
name Binance itself announced per contract — arrives separately from the
announcement extraction; the join adjudicates identity. Nothing in this script
decides identity on its own: every row leaves as pending-join.

Incremental: already-fetched bases are skipped on re-run (cache in the draft
output), so a rate-limit stall costs a re-run, not a restart.

Python datetime used for epochs (months are 1-indexed).

Run: python scripts/build_universe_map.py  -> data/universe_map_draft.json
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DRAFT_PATH = PROJECT_ROOT / "data" / "universe_map_draft.json"
ROSTER_PATH = Path(r"C:\dev\Perp-Funding-Scanner\data\tradfi_universe_log.json")

FETCH_SLEEP = 0.4

# Candidate-ticker overrides where the Binance base is not a US ticker string.
# These are CANDIDATES ONLY — identity is decided at the join against Binance's
# announced names, never here. Sources for the candidates: exchange-native
# listings (KRX/HKEX codes in yfinance suffix form), yfinance futures symbols
# for spot commodities, share-class punctuation differences.
CANDIDATE_OVERRIDES = {
    "BRKB": "BRK-B",
    "HK0700": "0700.HK",       # Tencent HKEX 700 (quanto contract, same share as TENCENT)
    "TENCENT": "0700.HK",      # Tencent HKEX 700 (USDT-priced contract) — ann. 2026-07-17
    "HK1810": "1810.HK",       # Xiaomi HKEX 1810 (quanto)
    "MEITUAN": "3690.HK",
    "KUAISHOU": "1024.HK",
    "POPMART": "9992.HK",
    "SKHYNIX": "000660.KS",
    "SAMSUNG": "005930.KS",
    "SAMSUNGEM": "009150.KS",  # Samsung Electro-Mechanics — ann. 2026-08-14
    "LGELECTRONICS": "066570.KS",
    "HYUNDAI": "005380.KS",
    "NAVER": "035420.KS",
    "HANMI": "042700.KS",      # HANMI Semiconductor — ann. 2026-08-14
    "KODEX200": "069500.KS",
    "GIGADEV": "3986.HK",      # GigaDevice H shares — ann. 2026-08-03
    "ZHONGJI": "3308.HK",      # ZhongJi Innolight H shares — ann. 2026-08-14
    "ZHIPU": "2513.HK",        # Knowledge Atlas (Zhipu AI), listed 2026-01-08 — ann. 2026-07-17
    "MINIMAX": "0100.HK",      # MiniMax Group, listed 2026-01-09 — ann. 2026-07-17
    "CSOPSAMSUNG2L": "7747.HK",   # CSOP 2x Samsung L&I product — ann. 2026-08-11
    "CSOPSKHYNIX2L": "7709.HK",   # CSOP 2x SK Hynix L&I product — ann. 2026-08-11
    # Crypto-perp ticker collisions forced renames on Binance's side; the
    # underlyings are the plain US listings — ann. 2026-06-11 / 06-01 / 05-29:
    "STXX": "STX",             # Seagate (STX crypto perp = Stacks)
    "BBX": "BB",               # BlackBerry (BB crypto perp = BounceBit)
    "QNTX": "QNT",             # Quantinuum, Nasdaq QNT (QNT crypto perp = Quant)
    # Commodities: continuous front-month futures as the signal series.
    "XAU": "GC=F", "XAG": "SI=F", "XPT": "PL=F", "XPD": "PA=F",
    "CL": "CL=F", "BZ": "BZ=F", "COPPER": "HG=F", "NATGAS": "NG=F",
}

# Pre-IPO / AI-lab marks with NO listed underlying (per the 2026 announcements).
# SPCX left OUT deliberately: SpaceX IPO'd on Nasdaq 2026-06-12, so it has a
# listed underlying with short history, handled by the history gate.
EXPECTED_NO_UNDERLYING = {"OPENAI", "ANTHROPIC"}


def fetch_vendor_record(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.get_info()
    if not isinstance(info, dict) or not info:
        return {"error": "empty info"}
    keys = {
        "shortName": info.get("shortName"),
        "longName": info.get("longName"),
        "quoteType": info.get("quoteType"),
        "exchange": info.get("fullExchangeName") or info.get("exchange"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency"),
        "dividendYield_raw": info.get("dividendYield"),
        "firstTradeDateEpochUtc": info.get("firstTradeDateEpochUtc"),
    }
    ep = keys["firstTradeDateEpochUtc"]
    if ep:
        keys["firstTradeDate"] = datetime.fromtimestamp(ep, tz=timezone.utc).strftime("%Y-%m-%d")
    return keys


def main() -> int:
    log = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    seed = next(s for s in log["snapshots"] if "roster" in s)
    bases = sorted({r["base"] for r in seed["roster"]})
    print(f"Seed roster: {len(bases)} bases ({seed['ts_utc']})")

    draft = json.loads(DRAFT_PATH.read_text(encoding="utf-8")) if DRAFT_PATH.exists() else {
        "generated_at_utc": None, "roster_ts": seed["ts_utc"], "rows": {}}
    rows = draft["rows"]

    fetched = 0
    for i, base in enumerate(bases, 1):
        if base in rows and "error" not in rows[base].get("vendor", {}):
            continue
        candidate = CANDIDATE_OVERRIDES.get(base, base)
        row = {"base": base, "candidate": candidate, "status": "pending-join"}
        if base in EXPECTED_NO_UNDERLYING:
            row["expected_no_underlying"] = True
        try:
            row["vendor"] = fetch_vendor_record(candidate)
        except Exception as e:  # noqa: BLE001 — recorded per name
            row["vendor"] = {"error": f"{type(e).__name__}: {e}"}
        rows[base] = row
        fetched += 1
        if i % 20 == 0:
            print(f"  [{i}/{len(bases)}]")
            DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)
            draft["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
            DRAFT_PATH.write_text(json.dumps(draft, indent=1), encoding="utf-8")
        time.sleep(FETCH_SLEEP)

    draft["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DRAFT_PATH.write_text(json.dumps(draft, indent=1), encoding="utf-8")

    ok = sum(1 for r in rows.values() if "error" not in r["vendor"])
    err = [b for b, r in rows.items() if "error" in r["vendor"]]
    print(f"Fetched this run: {fetched}; vendor records OK: {ok}/{len(bases)}")
    print(f"No vendor record ({len(err)}): {err}")

    # Pass 2 — price-series head/tail per candidate. yfinance get_info() no
    # longer returns firstTradeDateEpochUtc, and a name without a price series
    # is not an underlying at all (this catches placeholder stubs like a
    # private company carried as an empty EQUITY record). Monthly max-period
    # bars: one cheap request per name, incremental like pass 1.
    print("Pass 2: price-series coverage ...")
    fetched2 = 0
    for i, base in enumerate(bases, 1):
        row = rows[base]
        if "series" in row:
            continue
        try:
            hist = yf.Ticker(row["candidate"]).history(period="max", interval="1mo",
                                                       auto_adjust=False)
            if hist is None or len(hist) == 0:
                row["series"] = {"error": "no price series"}
            else:
                row["series"] = {
                    "first_bar": hist.index[0].strftime("%Y-%m-%d"),
                    "last_bar": hist.index[-1].strftime("%Y-%m-%d"),
                    "n_months": int(len(hist)),
                }
        except Exception as e:  # noqa: BLE001
            row["series"] = {"error": f"{type(e).__name__}: {e}"}
        fetched2 += 1
        if i % 25 == 0:
            print(f"  [{i}/{len(bases)}]")
            DRAFT_PATH.write_text(json.dumps(draft, indent=1), encoding="utf-8")
        time.sleep(FETCH_SLEEP)
    DRAFT_PATH.write_text(json.dumps(draft, indent=1), encoding="utf-8")
    with_series = sum(1 for r in rows.values() if "error" not in r.get("series", {"error": 1}))
    print(f"Pass 2 fetched: {fetched2}; series present: {with_series}/{len(bases)}")
    pre2018 = sum(1 for r in rows.values()
                  if r.get("series", {}).get("first_bar", "9999") <= "2018-01-31")
    print(f"Underlyings with history back to 2018 or earlier: {pre2018}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
