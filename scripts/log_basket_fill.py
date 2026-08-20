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

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "data" / "basket_shadow_log.json"
ORDER_LIST = ROOT / "data" / "order_list_today.json"
KINDS = ("basket-entry", "basket-exit", "buy", "sell")


def modelled_reference(symbol):
    """The price the MODEL would have filled at — the reference close carried
    on today's order list. Captured at fill time because the order list is
    overwritten daily, and the FAIL-EXECUTION trigger needs realised slippage
    against it."""
    try:
        o = json.loads(ORDER_LIST.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None, None
    for row in o.get("orders", []):
        if row.get("symbol") == symbol:
            return row.get("ref_price"), o.get("fill_reference_asof")
    return None, None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", required=True)
    p.add_argument("--kind", required=True, choices=KINDS)
    p.add_argument("--qty", required=True, type=float)
    p.add_argument("--px", required=True, type=float)
    p.add_argument("--note", default=None)
    p.add_argument("--ref", type=float, default=None,
                   help="modelled reference price; taken from today's order list when omitted")
    a = p.parse_args()
    sym = a.symbol.upper()
    row = {"type": "execution", "ts_utc": datetime.now(timezone.utc).isoformat(),
           "symbol": sym, "kind": a.kind, "qty": a.qty, "px": a.px,
           "notional_usd": round(a.qty * a.px, 2)}
    ref, ref_asof = (a.ref, None) if a.ref else modelled_reference(sym)
    if ref:
        # Signed so that positive always means WORSE than the model: paying up
        # on a buy, receiving less on a sell.
        side = -1.0 if a.kind in ("basket-exit", "sell") else 1.0
        row["ref_price"] = ref
        row["ref_asof"] = ref_asof
        row["slippage_bp"] = round(side * (a.px / ref - 1.0) * 10_000, 1)
    if a.note:
        row["note"] = a.note
    log = json.loads(LOG_PATH.read_text(encoding="utf-8")) if LOG_PATH.exists() else []
    log.append(row)
    LOG_PATH.write_text(json.dumps(log, indent=1), encoding="utf-8")
    print("logged:", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
