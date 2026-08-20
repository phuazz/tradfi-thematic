"""Phase 0 — the join: two-source identity adjudication + mechanical clusters.

Inputs:
  data/universe_map_draft.json      — vendor records + price-series coverage
  data/binance_announced_names.txt  — Binance's own announced underlying per
                                      contract (agent extraction), pipe rows:
                                      SYMBOL | name | native listing | url | confidence

Identity rule: a name is `verified` only when the announced name and the vendor
record agree (normalised token containment), or when it appears in the
ADJUDICATED dict below — every entry there is a human judgement made looking at
BOTH sources, recorded in code so it is reviewable. Everything else is
`flagged` and stays OUT of the universe. Pre-IPO/synthetic contracts are
`no-underlying` by rule.

Cluster assignment is mechanical: ETPs by name keywords (leveraged tier
identified and flagged), equities by vendor sector/industry with explicit
keyword overrides, commodities by candidate suffix. Region from the native
listing. Nothing is assigned by unrecorded judgement.

Output: data/universe_map.json + printed summary and review list.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DRAFT = PROJECT_ROOT / "data" / "universe_map_draft.json"
ANNOUNCED = PROJECT_ROOT / "data" / "binance_announced_names.txt"
OUT = PROJECT_ROOT / "data" / "universe_map.json"

FULL_WINDOW_BAR = "2018-01-31"   # first_bar at or before this = full-window history

STOP_TOKENS = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited",
    "plc", "sa", "spa", "nv", "ag", "the", "class", "a", "b", "adr", "adrs",
    "american", "depositary", "shares", "share", "receipt", "receipts", "etf",
    "trust", "fund", "holdings", "holding", "group", "technologies", "technology",
    "usdt", "perpetual", "perp", "usd", "and", "of", "-", "&",
}

# Human-adjudicated identities: cases where the mechanical token match cannot
# succeed (transliteration, abbreviation, share-line nuance) but BOTH sources
# were inspected and agree on the underlying. Each entry: base -> evidence.
# The exchange CODE agreement (announcement's native listing vs the candidate
# suffix actually fetched) is the operative second confirmation in all of these.
ADJUDICATED: dict[str, str] = {
    "XAU": "Gold: vendor is the front-month future (GC=F, 'Gold Dec 26') of the announced commodity",
    "XAG": "Silver: front-month future SI=F of the announced commodity",
    "XPT": "Platinum: front-month future PL=F of the announced commodity",
    "XPD": "Palladium: front-month future PA=F of the announced commodity",
    "COPPER": "Copper: front-month future HG=F of the announced commodity",
    "SAMSUNG": "Yahoo KRX short name 'SamsungElec' = Samsung Electronics; code 005930.KS matches the announced KRX 005930",
    "SAMSUNGEM": "'SamsungElecMech' = Samsung Electro-Mechanics; 009150.KS matches announced KRX 009150",
    "HANMI": "'HANMISemi' = HANMI Semiconductor (not Hanmi Pharm); 042700.KS matches announced KRX 042700",
    "HYUNDAI": "'HyundaiMtr' = Hyundai Motor; 005380.KS matches the announced line",
    "LGELECTRONICS": "Yahoo concatenates 'LGELECTRONICS'; 066570.KS matches announced KRX 066570",
    "CSOPSAMSUNG2L": "HKEX L&I code name 'XL2CSOPSMSN'; 7747.HK matches announced HKEX 7747 (levered ETP, excluded from rotation anyway)",
    "CSOPSKHYNIX2L": "'XL2CSOPHYNIX'; 7709.HK matches announced HKEX 7709 (levered ETP, excluded from rotation anyway)",
}

# Pre-IPO / synthetic marks: no listed underlying exists. SPCX, ZHIPU and
# MINIMAX are NOT here — all three IPO'd (Nasdaq 2026-06-12, HKEX 2026-01-08,
# HKEX 2026-01-09 respectively) and carry real short-history series.
NO_UNDERLYING = {"OPENAI", "ANTHROPIC"}

# "UltraPro" and "UltraShort" are single words, so \bultra\b and \bshort\b
# never fired on them — TQQQ and TBT escaped the levered filter until the
# rotation surfaced TQQQ in a live pick list (2026-08-20 defect correction).
LEVERED_PAT = re.compile(r"(?i)\b(2x|3x|-1x|ultra\w*|bull|bear|short|daily target|leveraged|inverse)\b|\b2X\b")

ETF_CLUSTER_KEYWORDS = [
    ("semi|memory|soxx|soxl|soxs", "semis-hardware"),
    ("bitcoin|crypto|ether", "crypto-equity"),
    ("korea|kospi", "country-korea"),
    ("japan|nikkei", "country-japan"),
    ("taiwan", "country-taiwan"),
    ("brazil", "country-brazil"),
    ("china", "china-tech"),
    ("biotech|health", "health"),
    ("energy", "energy"),
    ("uranium", "materials"),
    ("treasury|bond", "rates"),
    ("vix|volatility", "volatility"),
    ("s&p|500|nasdaq|qqq|russell|star 50|dow", "index-broad"),
]

EQUITY_INDUSTRY_RULES = [
    ("semiconductor", "semis-hardware"),
    ("software|information technology services|internet", "software-ai"),
    ("computer hardware|electronic|communication equipment|storage", "semis-hardware"),
]

EQUITY_SECTOR_MAP = {
    "Technology": "software-ai",
    "Communication Services": "platforms-media",
    "Consumer Cyclical": "consumer",
    "Consumer Defensive": "consumer",
    "Financial Services": "financials",
    "Healthcare": "health",
    "Industrials": "industrials-space",
    "Energy": "energy",
    "Basic Materials": "materials",
    "Real Estate": "financials",
    "Utilities": "energy",
}

# Keyword overrides that outrank the sector map (crypto-treasury equities are a
# theme of their own regardless of listed sector).
EQUITY_NAME_OVERRIDES = [
    ("strategy inc|microstrategy|bitmine|coinbase|circle|robinhood|galaxy|marathon|riot", "crypto-equity"),
    ("space exploration|rocket lab|ast spacemobile|intuitive machines", "space"),
    ("rare earth", "materials"),
]


def tokens(s: str | None) -> set[str]:
    if not s:
        return set()
    return {t for t in re.split(r"[^a-z0-9]+", s.lower()) if t and t not in STOP_TOKENS}


def parse_announced() -> dict[str, dict]:
    out = {}
    for line in ANNOUNCED.read_text(encoding="utf-8").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2 or not parts[0] or " " in parts[0]:
            continue
        out[parts[0].upper()] = {
            "announced_name": parts[1],
            "native_listing": parts[2] if len(parts) > 2 else None,
            "source": parts[3] if len(parts) > 3 else None,
            "confidence": (parts[4].lower() if len(parts) > 4 else None),
        }
    return out


def region_from(native: str | None, exchange: str | None, candidate: str) -> str:
    s = f"{native or ''} {exchange or ''} {candidate}".lower()
    if "krx" in s or ".ks" in s or "kosdaq" in s or "korea" in s:
        return "KR"
    if "hkex" in s or ".hk" in s or "hong kong" in s:
        return "HK"
    if "tse" in s or "tokyo" in s or ".t " in s:
        return "JP"
    if "=f" in candidate.lower():
        return "COMMODITY"
    return "US"


def cluster_for(row: dict, announced_name: str | None) -> tuple[str, bool]:
    """Return (cluster, levered_flag)."""
    v = row["vendor"]
    name = " ".join(filter(None, [v.get("shortName"), v.get("longName"), announced_name]))
    levered = bool(LEVERED_PAT.search(name or ""))
    if row["candidate"].endswith("=F"):
        return "commodity", False
    if (v.get("quoteType") or "").upper() in ("ETF", "MUTUALFUND"):
        low = (name or "").lower()
        for pat, cl in ETF_CLUSTER_KEYWORDS:
            if re.search(pat, low):
                return cl, levered
        return "etf-other", levered
    low = (name or "").lower()
    for pat, cl in EQUITY_NAME_OVERRIDES:
        if re.search(pat, low):
            return cl, levered
    ind = (v.get("industry") or "").lower()
    for pat, cl in EQUITY_INDUSTRY_RULES:
        if re.search(pat, ind):
            return cl, levered
    return EQUITY_SECTOR_MAP.get(v.get("sector") or "", "unclassified"), levered


def main() -> int:
    draft = json.loads(DRAFT.read_text(encoding="utf-8"))
    announced = parse_announced()
    rows_out = {}
    review = []
    for base, row in sorted(draft["rows"].items()):
        v = row["vendor"]
        series = row.get("series", {})
        ann = announced.get(base, {})
        ann_name = ann.get("announced_name")
        entry = {
            "base": base,
            "candidate": row["candidate"],
            "vendor_name": v.get("shortName") or v.get("longName"),
            "announced_name": ann_name,
            "native_listing": ann.get("native_listing"),
            "announce_confidence": ann.get("confidence"),
            "quote_type": v.get("quoteType"),
            "sector": v.get("sector"),
            "industry": v.get("industry"),
            "dividend_yield_raw": v.get("dividendYield_raw"),
            "first_bar": series.get("first_bar"),
            "last_bar": series.get("last_bar"),
            "full_window_history": bool(series.get("first_bar") and series["first_bar"] <= FULL_WINDOW_BAR),
        }
        # Identity adjudication. "no-underlying" only for the declared pre-IPO
        # marks — a "pre-IPO" mention in a history note (SPCX, QNTX later
        # IPO'd) must not trigger it, so the textual rule keys on the explicit
        # "NOT a listed security" phrasing.
        if base in NO_UNDERLYING or (ann_name and "NOT a listed security" in ann_name):
            status = "no-underlying"
        elif "error" in v or "error" in series:
            status = "flagged"
            entry["flag_reason"] = v.get("error") or series.get("error")
        elif base in ADJUDICATED:
            status = "verified"
            entry["adjudicated"] = ADJUDICATED[base]
        elif ann_name:
            tv, ta = tokens(entry["vendor_name"]), tokens(ann_name)
            overlap = tv & ta
            if overlap and (len(overlap) >= 2 or len(tv) <= 2 or len(ta) <= 2):
                status = "verified"
            else:
                status = "flagged"
                entry["flag_reason"] = "announced/vendor name mismatch"
                review.append((base, ann_name, entry["vendor_name"]))
        else:
            status = "flagged"
            entry["flag_reason"] = "no announced name found"
            review.append((base, None, entry["vendor_name"]))
        entry["status"] = status
        cl, lev = cluster_for(row, ann_name)
        entry["cluster"] = cl
        entry["levered_etp"] = lev
        entry["region"] = region_from(ann.get("native_listing"), v.get("exchange"), row["candidate"])
        rows_out[base] = entry

    out = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "roster_ts": draft.get("roster_ts"),
        "full_window_bar": FULL_WINDOW_BAR,
        "rows": rows_out,
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    n = len(rows_out)
    by_status = {}
    for e in rows_out.values():
        by_status[e["status"]] = by_status.get(e["status"], 0) + 1
    verified_full = sum(1 for e in rows_out.values()
                        if e["status"] == "verified" and e["full_window_history"] and not e["levered_etp"])
    levered = sum(1 for e in rows_out.values() if e["levered_etp"])
    clusters = {}
    for e in rows_out.values():
        if e["status"] == "verified" and not e["levered_etp"]:
            clusters[e["cluster"]] = clusters.get(e["cluster"], 0) + 1
    print(f"Universe map: {n} bases -> {by_status}")
    print(f"Levered ETPs (excluded-recommended): {levered}")
    print(f"Verified, unlevered, full 2018+ history: {verified_full}")
    print("Clusters (verified, unlevered):", json.dumps(clusters, indent=1, sort_keys=True))
    if review:
        print(f"\nREVIEW LIST ({len(review)}) — adjudicate into ADJUDICATED or leave flagged:")
        for b, a, vn in review:
            print(f"  {b:<14} announced={a!s:<45} vendor={vn}")
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
