"""Basket shadow evaluator — daily 07:15 SGT. LOGS AND ALERTS ONLY; never
places an order (frozen guard, WS17 pattern). Protocol:
reviews/2026-08-16_basket-shadow-protocol.md (Option A, US$5,000, activated
2026-08-16).

Per run:
  1. Update the rolling liquidity union from the scanner's latest scan (7-day
     window, so weekend-thin scans cannot wrongly exclude weekday-liquid names).
  2. Derive the current book from the append-only fill log.
  3. ESTABLISHMENT (book incomplete): emit the next tranche (<=30 names not yet
     held), equal-weight US$5,000/N, quantities rounded to the contract step,
     bumped to min notional where needed; funding rule: no BUY of a name whose
     trailing 30d funding exceeds +30%/yr (scanner field).
  4. SATURDAY (SGT) once established: maintenance list — names drifted beyond
     +/-25% of target, entries of newly eligible names, exits of names no
     longer trading. On Saturdays the underlying panel is refreshed first so
     eligibility (252-day history, freshness) is current.
  5. Write data/order_list_today.json, append ops row to
     data/basket_shadow_log.json, touch logs/last_success.txt (fleet-watch
     heartbeat), best-effort email, local commit (repo has no remote).

Python datetime: months are 1-indexed. Weekday(): Monday=0 ... Sunday=6.
"""

from __future__ import annotations

import json
import math
import os
import smtplib
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prereg  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCANNER_DATA = Path(r"C:\dev\Perp-Funding-Scanner\data")
MAP_PATH = PROJECT_ROOT / prereg.UNIVERSE_MAP
FILTERS_PATH = PROJECT_ROOT / "data" / "contract_filters.json"
LIQUID_ROLLING = PROJECT_ROOT / "data" / "liquid_rolling.json"
LOG_PATH = PROJECT_ROOT / "data" / "basket_shadow_log.json"
ORDER_LIST = PROJECT_ROOT / "data" / "order_list_today.json"
HEARTBEAT = PROJECT_ROOT / "logs" / "last_success.txt"

BOOK_CAP_USD = 5000.0           # owner, 2026-08-16, Option A
EQUITY_ONLY = True              # Amendment 1, 2026-08-16: commodity cluster excluded
ROTATION_K = 10                 # Amendment 2, 2026-08-20: K=10 cap=2 rotation payload
ROTATION_CLUSTER_CAP = 2        # (seen-data caveat carried; k10-shape null 99.9th pct)
TRANCHE_SIZE = 30               # retained for reference; rotation establishes in one list
DRIFT_BAND = 0.25               # maintenance only beyond +/-25% of target
LIQUID_WINDOW_DAYS = 7
SGT = timezone(timedelta(hours=8))


def now_utc():
    return datetime.now(timezone.utc)


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def append_log(rows):
    log = read_json(LOG_PATH, [])
    log.extend(rows)
    LOG_PATH.write_text(json.dumps(log, indent=1), encoding="utf-8")


def send_alert(subject, body):
    user, pw = os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pw:
        return False
    msg = MIMEText(body)
    msg["Subject"], msg["From"], msg["To"] = subject, user, user
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
        s.starttls(); s.login(user, pw); s.send_message(msg)
    return True


def update_liquid_rolling(scan):
    roll = read_json(LIQUID_ROLLING, {})
    day = scan["generated_at_utc"][:10]
    roll[day] = sorted({r["symbol"] for r in scan["rows"]})
    cutoff = (now_utc() - timedelta(days=LIQUID_WINDOW_DAYS)).strftime("%Y-%m-%d")
    roll = {d: v for d, v in roll.items() if d >= cutoff}
    LIQUID_ROLLING.write_text(json.dumps(roll, indent=1), encoding="utf-8")
    union = set()
    for v in roll.values():
        union.update(v)
    return union


def current_book(prices):
    """Holdings (qty) and USD weights from the append-only fill log."""
    qty = {}
    for row in read_json(LOG_PATH, []):
        if row.get("type") != "execution":
            continue
        sign = 1.0 if row["kind"].endswith("entry") or row["kind"] == "buy" else -1.0
        qty[row["symbol"]] = qty.get(row["symbol"], 0.0) + sign * float(row["qty"])
    qty = {s: q for s, q in qty.items() if abs(q) > 1e-12}
    val = {s: q * prices.get(s, 0.0) for s, q in qty.items()}
    return qty, val


def round_step(q, step):
    st = float(step)
    return math.floor(q / st) * st if st > 0 else q


def main() -> int:
    stamp = now_utc().isoformat()
    scan = read_json(SCANNER_DATA / "scan.json", None)
    if scan is None:
        append_log([{"type": "ops", "ts_utc": stamp, "event": "MISSED",
                     "reason": "scan.json unavailable"}])
        send_alert("[basket shadow] MISSED", "scan.json unavailable")
        return 1
    liquid = update_liquid_rolling(scan)
    scan_rows = {r["symbol"]: r for r in scan["rows"]}
    # Rolling last-seen prices: a weekend scan carries only weekend-liquid
    # rows, so names absent from the LATEST scan keep their last-seen price
    # (stamped) rather than dropping off the order list.
    last_px_path = PROJECT_ROOT / "data" / "last_prices.json"
    last_px = read_json(last_px_path, {})
    for s, r in scan_rows.items():
        last_px[s] = {"px": float(r["price"]), "asof": scan["generated_at_utc"],
                      "fund": r.get("fund_ann_30d")}
    last_px_path.write_text(json.dumps(last_px, indent=1), encoding="utf-8")

    def fund_of(sym):
        """Trailing 30d funding, latest scan first, else last seen (stamped
        data beats a silent None for the frozen live exclusion rule)."""
        r = scan_rows.get(sym)
        if r is not None and r.get("fund_ann_30d") is not None:
            return r["fund_ann_30d"]
        return (last_px.get(sym) or {}).get("fund")
    filters = read_json(FILTERS_PATH, {})
    umap = read_json(MAP_PATH, {"rows": {}})["rows"]

    # Liquid, verified, unlevered equity membership (the candidate pool the
    # rotation selects FROM). Amendment 2: the live payload is the K=10
    # cluster-cap-2 rotation — selection is delegated to the FROZEN engine
    # function so live picks are bit-identical to the filed construction.
    members, names, clusters, base_of = [], {}, {}, {}
    for base, e in sorted(umap.items()):
        if e["status"] != "verified" or e["levered_etp"] or base in prereg.EXPLICIT_DROPS:
            continue
        if EQUITY_ONLY and e.get("cluster") == "commodity":
            continue
        sym = base + "USDT"
        if sym in filters and sym in liquid:
            members.append(sym)
            names[sym] = e.get("vendor_name") or (e.get("announced_name") or base).split("—")[0].strip()
            clusters[base] = e.get("cluster", "unclassified")
            base_of[sym] = base
    n = len(members)
    target_usd = BOOK_CAP_USD / ROTATION_K

    prices = {s: last_px[s]["px"] for s in members if s in last_px}
    price_asof = {s: last_px[s]["asof"] for s in members if s in last_px}
    qty_held, val_held = current_book(prices)
    held = set(qty_held)
    sgt_now = now_utc().astimezone(SGT)
    is_saturday = sgt_now.weekday() == 5  # Monday=0 ... Saturday=5

    orders, skipped_funding, skipped_price = [], [], []

    def order_row(sym, side, usd):
        px = prices.get(sym)
        if not px:
            skipped_price.append(sym)
            return None
        f = filters[sym]
        q = round_step(usd / px, f["step_size"])
        while q * px < f["min_notional"]:
            q += float(f["step_size"])
        fund = fund_of(sym)
        return {"symbol": sym, "name": names.get(sym, sym), "side": side,
                "qty": round(q, 8),
                "approx_usd": round(q * px, 2), "ref_price": px,
                "ref_price_asof": price_asof.get(sym),
                "fund_ann_30d": fund}

    # Rotation selection from the frozen engine: signal at the panel's last
    # session, eligibility (252d history, freshness), floor and sleeve gate,
    # ranked picks under the cluster cap. Funding rule (live-only): a hot name
    # is removed from CANDIDACY unless already held — buys are blocked, holds
    # are never force-sold by it.
    import engine  # local import: heavy, only needed for selection
    d = engine.load_inputs()
    sd = d["us_index"][-1]
    sig_row = d["signal"].loc[sd]
    elig = (d["obs_count"].loc[sd] >= prereg.MIN_HISTORY_DAYS) & \
           (d["staleness"].loc[sd] <= prereg.FFILL_LIMIT_SESSIONS)
    for b in list(sig_row.index):
        sym = b + "USDT"
        if sym not in members:
            elig[b] = False
            continue
        fund = fund_of(sym)
        if (fund is not None and fund > prereg.LIVE_FUNDING_EXCLUDE_ANN
                and sym not in held):
            elig[b] = False
            skipped_funding.append(f"{sym} ({fund:+.1f}%/yr)")
    picks, diag = engine.select_names(sig_row, elig, d["clusters"], ROTATION_K,
                                      ROTATION_CLUSTER_CAP, prereg.ENTRY_FLOOR,
                                      prereg.SLEEVE_BREADTH_GATE)
    target_syms = set() if picks is None else {b + "USDT" for b in picks}
    gated = picks is None

    if gated and held:
        mode = "gated-cash"
        for sym in sorted(held):
            row = order_row(sym, "sell", val_held.get(sym, 0.0))
            if row:
                orders.append(row)
    elif gated:
        mode = "gated-cash"
    elif not held:
        mode = "establishment"
        for sym in sorted(target_syms):
            row = order_row(sym, "buy", target_usd)
            if row:
                orders.append(row)
    elif is_saturday:
        mode = "rotation-rebalance"
        for sym in sorted(held - target_syms):
            row = order_row(sym, "sell", val_held.get(sym, 0.0))
            if row:
                orders.append(row)
        for sym in sorted(target_syms - held):
            row = order_row(sym, "buy", target_usd)
            if row:
                orders.append(row)
        for sym in sorted(held & target_syms):
            cur = val_held.get(sym, 0.0)
            drift = (cur - target_usd) / target_usd if target_usd else 0.0
            if abs(drift) > DRIFT_BAND:
                row = order_row(sym, "sell" if drift > 0 else "buy",
                                abs(cur - target_usd))
                if row:
                    orders.append(row)
    else:
        mode = "heartbeat"
    n_missing = len(target_syms - held)

    payload = {
        "ts_utc": stamp, "mode": mode, "book_cap_usd": BOOK_CAP_USD,
        "payload_construction": f"rotation K={ROTATION_K} cap={ROTATION_CLUSTER_CAP} (Amendment 2)",
        "n_members": n, "target_usd_per_name": round(target_usd, 2),
        "signal_asof": str(sd.date()),
        "breadth": round(diag.get("breadth", 0.0), 3) if diag else None,
        "gated": gated,
        "n_held": len(held), "n_missing": n_missing,
        "book_value_usd": round(sum(val_held.values()), 2),
        "orders": orders,
        "skipped_funding_rule": skipped_funding,
        "skipped_no_price": skipped_price,
        "window": "07:30-09:30 SGT; execution is manual, this file is a list, not an instruction to any system",
    }
    ORDER_LIST.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    append_log([{"type": "ops", "ts_utc": stamp, "event": "OK", "mode": mode,
                 "n_orders": len(orders), "n_held": len(held),
                 "n_members": n, "book_value_usd": payload["book_value_usd"],
                 "skipped_funding": skipped_funding,
                 "skipped_no_price": skipped_price}])
    HEARTBEAT.parent.mkdir(exist_ok=True)
    HEARTBEAT.write_text(stamp, encoding="utf-8")

    if orders:
        body = "\n".join(f"{o['side']:>4} {o['name'][:34]:<34} [{o['symbol']}] qty {o['qty']} (~${o['approx_usd']})"
                         for o in orders)
        if skipped_funding:
            body += "\nSkipped by +30%/yr funding rule: " + ", ".join(skipped_funding)
        send_alert(f"[basket shadow] {mode}: {len(orders)} orders", body)

    # Saturday: refresh the underlying panel and the chart series before the
    # dashboard rebuild (protocol section 4 — weekly data refresh). Fail-open.
    if is_saturday:
        for script, tmo in (("scripts/fetch_underlyings.py", 900),
                            ("scripts/write_name_series.py", 300),
                            ("scripts/persist_series.py", 900),
                            ("scripts/persist_payload_detail.py", 600)):
            try:
                subprocess.run([sys.executable, script], cwd=PROJECT_ROOT,
                               capture_output=True, timeout=tmo)
            except Exception:  # noqa: BLE001
                pass
    # Health checks then the dashboard rebuild, so the page is fresh — and
    # honestly labelled — before the execution window. Fail-open: the
    # evaluation itself must never die here.
    for script, tmo in (("scripts/data_health.py", 120),
                        ("scripts/build_dashboard.py", 180)):
        try:
            subprocess.run([sys.executable, script], cwd=PROJECT_ROOT,
                           capture_output=True, timeout=tmo)
        except Exception:  # noqa: BLE001
            pass

    subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"],
                   cwd=PROJECT_ROOT, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=PROJECT_ROOT, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"auto: basket shadow {mode} {stamp[:10]}"],
                   cwd=PROJECT_ROOT, capture_output=True)
    # Push is best-effort: the repo went public on owner instruction
    # (2026-08-17); a failed push leaves the commit local for the next run.
    subprocess.run(["git", "push", "origin", "main"], cwd=PROJECT_ROOT,
                   capture_output=True)

    print(f"mode={mode} members={n} held={len(held)} orders={len(orders)} "
          f"skipped_funding={len(skipped_funding)} target=${target_usd:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
