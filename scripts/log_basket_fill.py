"""Log a realised basket-shadow fill (append-only). Manual companion to
basket_evaluator.py — the operator executes in the window and records here.

Example:
    python scripts/log_basket_fill.py --symbol NVDAUSDT --kind basket-entry --qty 0.19 --px 183.20
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "basket_shadow_log.json"
KINDS = ("basket-entry", "basket-exit", "buy", "sell")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", required=True)
    p.add_argument("--kind", required=True, choices=KINDS)
    p.add_argument("--qty", required=True, type=float)
    p.add_argument("--px", required=True, type=float)
    p.add_argument("--note", default=None)
    a = p.parse_args()
    row = {"type": "execution", "ts_utc": datetime.now(timezone.utc).isoformat(),
           "symbol": a.symbol.upper(), "kind": a.kind, "qty": a.qty, "px": a.px,
           "notional_usd": round(a.qty * a.px, 2)}
    if a.note:
        row["note"] = a.note
    log = json.loads(LOG_PATH.read_text(encoding="utf-8")) if LOG_PATH.exists() else []
    log.append(row)
    LOG_PATH.write_text(json.dumps(log, indent=1), encoding="utf-8")
    print("logged:", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
