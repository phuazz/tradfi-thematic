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
    series = rj(ROOT / "data" / "phase2_series.json", None)
    name_series = rj(ROOT / "data" / "name_series.json", None)
    detail = rj(ROOT / "data" / "payload_detail.json", None)
    health = rj(ROOT / "data" / "data_health.json", None)
    k10_null = rj(ROOT / "data" / "k10_null.json", None)
    honest = rj(ROOT / "data" / "honest_window.json", None)
    pit = rj(ROOT / "data" / "pit_listing_check.json", None)
    hurdle_blend = rj(ROOT / "data" / "hurdle_blend_measurement.json", None)

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
    cluster_by_base = {r["base"]: r["cluster"] for r in uni}

    # Execution quality: realised fills against the price the MODEL would have
    # filled at, captured on each fill. This is what the FAIL-EXECUTION trigger
    # reads (median round-trip cost above 15bp fails the shadow).
    slips = [r["slippage_bp"] for r in log
             if r.get("type") == "execution" and r.get("slippage_bp") is not None]
    slips_sorted = sorted(slips)
    median_slip = (slips_sorted[len(slips_sorted) // 2] if len(slips_sorted) % 2
                   else (slips_sorted[len(slips_sorted) // 2 - 1] + slips_sorted[len(slips_sorted) // 2]) / 2) \
        if slips_sorted else None
    execution = {
        "n_measured": len(slips),
        "median_slippage_bp": round(median_slip, 1) if median_slip is not None else None,
        "worst_slippage_bp": round(max(slips), 1) if slips else None,
        "trigger_bp": 15.0,
        "breached": (median_slip is not None and median_slip > 15.0),
    }

    # Index-beta share: how much of the book is broad-index exposure rather
    # than single-name selection, now versus the simulated history.
    live_picks = []
    if detail and detail.get("weeks"):
        live_picks = detail["weeks"][-1].get("picks", [])
    order_bases = [o["symbol"].replace("USDT", "") for o in orders.get("orders", [])]
    now_bases = order_bases or live_picks
    idx_now = sum(1 for b in now_bases if cluster_by_base.get(b) == "index-broad")
    idx_hist_pos = idx_hist_tot = 0
    if detail:
        for w in detail.get("weeks", []):
            for b in w.get("picks", []):
                idx_hist_tot += 1
                if cluster_by_base.get(b) == "index-broad":
                    idx_hist_pos += 1
    index_beta = {
        "now_count": idx_now, "now_total": len(now_bases),
        "now_pct": round(idx_now / len(now_bases) * 100, 1) if now_bases else 0.0,
        "hist_pct": round(idx_hist_pos / idx_hist_tot * 100, 2) if idx_hist_tot else 0.0,
    }

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
        "grid_full": results.get("cells", {}),
    }

    clusters = {}
    for r in uni:
        if not r["excluded"]:
            clusters[r["cluster"]] = clusters.get(r["cluster"], 0) + 1

    decisions = [r for r in log if r.get("type") == "ops"][::-1][:60]
    fills = [r for r in log if r.get("type") == "execution"][::-1]

    data = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of": {
            "orders": orders.get("ts_utc"),
            "scan": scan.get("generated_at_utc"),
            "results": results.get("computed_at_utc"),
            "series": (series or {}).get("computed_at_utc"),
            "detail": (detail or {}).get("computed_at_utc"),
            "name_series": (name_series or {}).get("computed_at_utc"),
            "universe": umap.get("generated_at_utc"),
        },
        # Live signal state, straight from the evaluator's own order list so the
        # page cannot disagree with the file the operator executes from.
        "gated": orders.get("gated"),
        "breadth": orders.get("breadth"),
        "signal_asof": orders.get("signal_asof"),
        "fill_reference_asof": orders.get("fill_reference_asof"),
        "under_filled": orders.get("under_filled"),
        "cash_pct": orders.get("cash_pct"),
        "n_target_positions": orders.get("n_target_positions"),
        "skipped_funding": orders.get("skipped_funding_rule", []),
        "execution": execution,
        "index_beta": index_beta,
        "max_loss_usd": 5000.0,
        "honest": honest,
        "pit": pit,
        "hurdle_blend": hurdle_blend,
        "book_cap": 5000.0, "n_members": n_members, "target_usd": target,
        "orders_mode": orders.get("mode"),
        "orders": order_rows, "book": book_rows,
        "book_value": round(sum(r["value"] for r in book_rows), 2),
        "n_filled": len(filled_syms),
        "shadow_books": scan.get("shadow_books"),
        "universe": uni, "clusters": clusters,
        "verdict": verdict,
        "series": series,
        "name_series": name_series,
        "detail": detail,
        "health": health,
        "k10_null": k10_null,
        "fills": fills,
        "decisions": decisions,
        "rules": {
            "signal": "distance of underlying adjusted close above its own 200-day moving average (P/MA200 − 1), computed on the underlying, traded via the perp",
            "floor": "+5% above the MA to qualify (the deployed sleeve-C floor, inherited, not fitted)",
            "gate": "if fewer than 30% of the eligible universe clears the floor, the whole sleeve goes to cash for the week",
            "cadence": ("the signal is read on the session BEFORE the fill. The backtest decides on one close and "
                        "fills at the next; the live book decides on the same earlier close and executes within "
                        "hours of that next close (Saturday 07:30–09:30 SGT, about 3½ hours after the Friday US "
                        "close). No look-ahead by construction, pinned by test. Until Amendment 3 the live rule "
                        "read a session fresher than the tested one — that divergence is now closed."),
            "basket": "the shipping product: every eligible name equal-weighted weekly; selection had to beat this by +0.10 Sharpe across the funding band and did not",
            "funding_rule": "live only: a name whose trailing 30-day funding exceeds +30%/yr is not bought that week (the scanner's deployed threshold; insurance, not edge — it cannot be backtested because the contracts are months old)",
            "maintenance": "Saturday window: trade only names drifted beyond ±25% of target, plus entries of newly eligible names and exits of delisted ones",
            "costs": "every backtest figure is net of 10bp round-trip fees (stressed 2× and 4×), a {0,+3,+6}%/yr funding band on invested days, and forgone dividends",
        },
        "amendments": [
            {"date": "2026-08-16", "what": "Countersign and activation — Option A, US$5,000 book cap at 1× leverage; establishment tranches of 30 in the 07:30–09:30 SGT window."},
            {"date": "2026-08-16", "what": "Amendment 1 (pre-fills): EQUITY-ONLY — the commodity cluster excluded on owner instruction; membership 59 → 51; re-anchor indistinguishable from the filed full-menu basket, so the shipping bar carries."},
            {"date": "2026-08-17", "what": "Published to GitHub Pages on owner instruction; the evaluator pushes each morning's rebuild."},
            {"date": "2026-08-20", "what": "Amendment 2 (pre-fills): the live payload pivots from the EW basket to the K=10 cluster-cap-2 ROTATION (US$5,000, ~US$500/name, ~3.3 orders/week) — owner grounds: operational load and listing-chase exposure (membership grew 51 → 57 in four days). SEEN-DATA CAVEAT carried: every grid cell was observed before this pick; the filed verdict (basket ships) stands in the record, overridden for the live book only. Gate, stated before its result: a fresh 1,000-path null at the K=10 shape — strategy at the 99.9th percentile. Passed."},
            {"date": "2026-08-20", "what": "Defect correction: TQQQ and TBT had escaped the levered-ETP filter (\\bultra\\b cannot match inside UltraPro/UltraShort) — surfaced when TQQQ appeared in a live pick list. Filter fixed (16 levered excluded), and the panel, engine results, anchor, gate and every chart series were rerun on the corrected universe. The SMH shadow was descoped not-started the same day (separate owner decision)."},
            {"date": "2026-08-20", "what": "Amendment 3, from a three-lens review of this page: the LIVE rule was reading the latest session's signal while the backtest reads the session before the fill — not look-ahead, but a different and unpriced rule. Live is now aligned to the tested convention, at the cost of a day of information. The review also found three health checks that could not fail (now falsifiable), an under-fill state the backtest never modelled (the funding block can leave slots empty — now surfaced and warned), and the null chart plotting the K=5 shape while the live payload is K=10 (now plots K=10)."},
        ],
        "glossary": [
            ["Above MA200", "how far a share price sits above its own average price of the last 200 trading days — the strategy's one measure of trend."],
            ["The +5% floor", "a name must be at least 5% above that average to be eligible at all."],
            ["Theme cap", "no more than two holdings from the same theme, so the book cannot become all semiconductors."],
            ["Cash gate", "if fewer than 30% of the universe clears the floor, the strategy holds nothing and waits."],
            ["Funding", "the recurring payment between the two sides of a perpetual contract. Positive means holders of the long side pay; it is a running cost of holding, quoted here annualised."],
            ["Funding band", "because these contracts are too young to have a usable funding history, the backtest charges a flat 0%, 3% or 6% a year instead. A result only counts if it survives all three."],
            ["Random-portfolio test", "the same strategy shape run 1,000 times picking names at random, to see whether the real ranking beats luck."],
            ["Seen-data pick", "a configuration chosen after its results were visible. It is disclosed rather than hidden, because it cannot be undone by argument."],
        ],
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
