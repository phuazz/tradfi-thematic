"""Build the local names-first dashboard: dashboard_template.html + data
-> dashboard.html (self-contained, data inlined, no network, file:// friendly).

LOCAL PAGE ONLY — the repo and the book are local by owner default; nothing
here publishes. Rebuilt by basket_evaluator.py each morning so the page is
fresh before the 07:30-09:30 SGT execution window.

Sources (all already maintained by other jobs):
  data/universe_map.json          identity, names, clusters   (Phase 0)
  data/order_list_today.json      today's orders              (evaluator)
  data/basket_shadow_log.json     fills -> book, ops          (operator + evaluator)
  data/last_prices.json           marks for book valuation    (evaluator)
  data/phase2_results.json        frozen-bar results          (engine)
  data/equity_anchor.json         Amendment 1 re-anchor       (engine)
  Perp-Funding-Scanner data/scan.json   live funding + shadow_books summary

Run: python scripts/build_dashboard.py -> dashboard.html
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prereg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCANNER = Path(r"C:\dev\Perp-Funding-Scanner\data")


def rj(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — every block is optional on the page
        return default


def main() -> int:
    umap = rj(ROOT / "data" / "universe_map.json", {"rows": {}})
    orders = rj(ROOT / "data" / "order_list_today.json", {})
    log = rj(ROOT / "data" / "basket_shadow_log.json", [])
    last_px = rj(ROOT / "data" / "last_prices.json", {})
    results = rj(ROOT / "data" / "phase2_results.json", {})
    anchor = rj(ROOT / "data" / "equity_anchor.json", {})
    scan = rj(SCANNER / "scan.json", {})
    scan_rows = {r["symbol"]: r for r in scan.get("rows", [])}

    def fund_of(sym):
        r = scan_rows.get(sym)
        if r is not None and r.get("fund_ann_30d") is not None:
            return r["fund_ann_30d"]
        return (last_px.get(sym) or {}).get("fund")

    # --- book from fills ----------------------------------------------------
    qty = {}
    for row in log:
        if row.get("type") != "execution":
            continue
        sign = 1.0 if str(row.get("kind", "")).endswith("entry") or row.get("kind") == "buy" else -1.0
        qty[row["symbol"]] = qty.get(row["symbol"], 0.0) + sign * float(row["qty"])
    filled_syms = {s for s, q in qty.items() if abs(q) > 1e-12}

    # --- universe rows (every verified name, exclusion reason spelled out) ---
    uni = []
    for base, e in sorted(umap.get("rows", {}).items(), key=lambda kv: (kv[1].get("vendor_name") or kv[0])):
        if e.get("status") != "verified":
            continue
        name = e.get("vendor_name") or (e.get("announced_name") or base).split("—")[0].strip()
        if e.get("levered_etp"):
            reason = "levered ETP — excluded"
        elif base in prereg.EXPLICIT_DROPS:
            reason = "duplicate line — excluded"
        elif e.get("cluster") == "commodity":
            reason = "commodity — Amendment 1"
        else:
            reason = ""
        sym = base + "USDT"
        uni.append({
            "name": name, "base": base, "cluster": e.get("cluster"),
            "region": e.get("region"), "first_bar": e.get("first_bar"),
            "full_hist": bool(e.get("full_window_history")),
            "excluded": reason,
            "fund": fund_of(sym),
            "vol24": (scan_rows.get(sym) or {}).get("vol_24h_m"),
            "in_book": sym in filled_syms,
        })

    name_by_sym = {r["base"] + "USDT": r["name"] for r in uni}

    order_rows = []
    for o in orders.get("orders", []):
        order_rows.append({**o, "name": o.get("name") or name_by_sym.get(o["symbol"], o["symbol"]),
                           "status": "filled" if o["symbol"] in filled_syms else "pending"})

    n_members = orders.get("n_members") or 0
    target = orders.get("target_usd_per_name") or 0
    book_rows = []
    for s in sorted(filled_syms):
        px = (last_px.get(s) or {}).get("px", 0.0)
        val = qty[s] * px
        book_rows.append({
            "name": name_by_sym.get(s, s), "symbol": s, "qty": round(qty[s], 8),
            "value": round(val, 2),
            "drift_pct": round((val / target - 1) * 100, 1) if target else None,
            "fund": fund_of(s),
        })

    # --- verdict tables -----------------------------------------------------
    bands = [f"{b:g}" for b in prereg.FUNDING_BAND_ANN]
    cells = results.get("cells", {}).get("k5_cap2", {})
    basket = results.get("basket", {})
    verdict = {
        "bands": bands,
        "primary": {b: cells.get(f"m1_b{b}") for b in bands},
        "basket": {b: basket.get(f"m1_b{b}") for b in bands},
        "basket_2x_edge": basket.get(f"m2_b{bands[-1]}"),
        "equity_anchor": anchor.get("results", {}),
        "null": results.get("null", {}),
        "split_half": results.get("split_half", {}),
        "grid_note": {k: v.get(f"m1_b{bands[-1]}", {}).get("sharpe")
                      for k, v in results.get("cells", {}).items()},
    }

    clusters = {}
    for r in uni:
        if not r["excluded"]:
            clusters[r["cluster"]] = clusters.get(r["cluster"], 0) + 1

    data = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of": {
            "orders": orders.get("ts_utc"),
            "scan": scan.get("generated_at_utc"),
            "results": results.get("computed_at_utc"),
        },
        "book_cap": 5000.0, "n_members": n_members, "target_usd": target,
        "orders_mode": orders.get("mode"),
        "orders": order_rows, "book": book_rows,
        "book_value": round(sum(r["value"] for r in book_rows), 2),
        "n_filled": len(filled_syms),
        "shadow_books": scan.get("shadow_books"),
        "universe": uni, "clusters": clusters,
        "verdict": verdict,
    }

    template = (ROOT / "dashboard_template.html").read_text(encoding="utf-8")
    placeholder = "/*__DATA__*/null"
    assert placeholder in template, "placeholder missing"
    out = template.replace(placeholder, json.dumps(data, separators=(",", ":"), allow_nan=False))
    (ROOT / "dashboard.html").write_text(out, encoding="utf-8")
    # Published copy (owner instruction 2026-08-17): GitHub Pages serves docs/.
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "index.html").write_text(out, encoding="utf-8")
    print(f"dashboard built (root + docs/): {len(out)/1024:.0f} KB, {len(uni)} universe rows, "
          f"{len(order_rows)} orders, {len(book_rows)} holdings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
