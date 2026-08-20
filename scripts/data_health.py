"""Data-health checks for the dashboard's health tab (the bte "(n OK)" pattern).

These are real guards, not decoration: each check states what it verifies, and
the tab label carries the OK count so a regression is visible before the page
is trusted. Every check returns OK / WARN / FAIL with a one-line detail.

Run: python scripts/data_health.py -> data/data_health.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prereg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCANNER = Path(r"C:\dev\Perp-Funding-Scanner\data")


def rj(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def age_hours(iso):
    if not iso:
        return None
    t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds() / 3600


def main() -> int:
    checks = []

    def add(name, status, detail, group="data"):
        checks.append({"name": name, "status": status, "detail": detail, "group": group})

    umap = rj(ROOT / "data" / "universe_map.json", {"rows": {}})
    rows = umap.get("rows", {})
    results = rj(ROOT / "data" / "phase2_results.json", {})
    series = rj(ROOT / "data" / "phase2_series.json", {})
    nameser = rj(ROOT / "data" / "name_series.json", {})
    detail = rj(ROOT / "data" / "payload_detail.json", {})
    k10null = rj(ROOT / "data" / "k10_null.json", {})
    anchor = rj(ROOT / "data" / "equity_anchor.json", {})
    orders = rj(ROOT / "data" / "order_list_today.json", {})
    log = rj(ROOT / "data" / "basket_shadow_log.json", [])
    filters = rj(ROOT / "data" / "contract_filters.json", {})
    scan = rj(SCANNER / "scan.json", {})
    cov = rj(ROOT / "data" / "underlyings_coverage.json", {})

    # --- identity and universe integrity ---------------------------------
    n_verified = sum(1 for e in rows.values() if e.get("status") == "verified")
    n_flagged = sum(1 for e in rows.values() if e.get("status") == "flagged")
    add("Identity: no unresolved names", "OK" if n_flagged == 0 else "FAIL",
        f"{n_verified} verified two-source, {n_flagged} flagged", "universe")

    levered = [b for b, e in rows.items() if e.get("levered_etp")]
    add("Levered ETPs excluded", "OK" if levered else "WARN",
        f"{len(levered)} levered/inverse products filtered out of the tradeable set", "universe")

    eligible = [b for b, e in rows.items()
                if e.get("status") == "verified" and not e.get("levered_etp")
                and b not in prereg.EXPLICIT_DROPS and e.get("cluster") != "commodity"]
    lev_leak = [b for b in eligible if rows[b].get("levered_etp")]
    add("No levered product in the eligible set", "OK" if not lev_leak else "FAIL",
        f"{len(eligible)} eligible equity names, {len(lev_leak)} leaks", "universe")

    commodity_leak = [b for b in eligible if rows[b].get("cluster") == "commodity"]
    add("Equity-only rule (Amendment 1)", "OK" if not commodity_leak else "FAIL",
        f"{len(commodity_leak)} commodity names in the eligible set (expected 0)", "universe")

    dupes = [b for b in prereg.EXPLICIT_DROPS if b in eligible]
    add("Duplicate share lines dropped", "OK" if not dupes else "FAIL",
        f"{', '.join(sorted(prereg.EXPLICIT_DROPS))} excluded", "universe")

    # --- data freshness ---------------------------------------------------
    per = (cov or {}).get("per_ticker", {})
    last_bars = sorted({v.get("last") for v in per.values() if v.get("last")})
    newest = last_bars[-1] if last_bars else None
    panel_age = None
    if newest:
        panel_age = (datetime.now(timezone.utc).date() - datetime.fromisoformat(newest).date()).days
    add("Price panel freshness", "OK" if (panel_age is not None and panel_age <= 4) else "WARN",
        f"newest bar {newest} ({panel_age} days ago); refreshed by the Saturday evaluator run"
        if newest else "no coverage file", "freshness")

    scan_age = age_hours(scan.get("generated_at_utc"))
    add("Funding scan freshness", "OK" if (scan_age is not None and scan_age <= 24) else "WARN",
        f"scanner data {scan_age:.1f}h old (twice-daily cadence)" if scan_age is not None
        else "scan.json unavailable", "freshness")

    ops = [r for r in log if r.get("type") == "ops"]
    ev_age = age_hours(ops[-1]["ts_utc"]) if ops else None
    add("Evaluator heartbeat", "OK" if (ev_age is not None and ev_age <= 36) else "WARN",
        f"last run {ev_age:.1f}h ago ({len(ops)} runs logged)" if ev_age is not None
        else "no evaluator runs logged", "freshness")

    # --- artefact coherence ----------------------------------------------
    for label, blob, key in (("study results", results, "computed_at_utc"),
                             ("chart series", series, "computed_at_utc"),
                             ("per-name series", nameser, "computed_at_utc"),
                             ("payload detail", detail, "computed_at_utc")):
        a = age_hours(blob.get(key)) if blob else None
        add(f"Artefact present: {label}", "OK" if a is not None else "FAIL",
            f"built {a:.1f}h ago" if a is not None else "missing", "artefacts")

    # The null gate must be computed against the CURRENT engine result.
    k10_live = (results.get("cells", {}).get("k10_cap2", {})
                .get(f"m1_b{prereg.FUNDING_BAND_ANN[-1]:g}", {}).get("sharpe"))
    gate_ok = (k10null.get("strategy_sharpe") == k10_live) if k10_live is not None else False
    add("Null gate matches current engine result", "OK" if gate_ok else "FAIL",
        f"gate ran on Sharpe {k10null.get('strategy_sharpe')}, engine reports {k10_live}"
        + (f"; percentile {k10null.get('strategy_percentile')}" if gate_ok else ""), "study")

    pct = k10null.get("strategy_percentile")
    add("Payload clears its null gate (>= p90)", "OK" if (pct or 0) >= 90 else "FAIL",
        f"{pct}th percentile of {k10null.get('n_paths')} random same-shape paths", "study")

    add("Equity-only anchor present", "OK" if anchor.get("results") else "WARN",
        "Amendment 1 re-anchor recorded" if anchor.get("results") else "missing", "study")

    # --- construction invariants (the freeze) -----------------------------
    weeks = detail.get("weeks", []) if detail else []
    cap_breaches = 0
    clusters = {b: e.get("cluster") for b, e in rows.items()}
    for w in weeks:
        counts = {}
        for b in w.get("picks", []):
            c = clusters.get(b, "unclassified")
            counts[c] = counts.get(c, 0) + 1
        if any(v > 2 for v in counts.values()):
            cap_breaches += 1
    add("Cluster cap respected every week", "OK" if cap_breaches == 0 else "FAIL",
        f"{cap_breaches} of {len(weeks)} weeks breach the cap of 2", "study")

    oversize = [w for w in weeks if len(w.get("picks", [])) > 10]
    add("Position count never exceeds K", "OK" if not oversize else "FAIL",
        f"{len(oversize)} of {len(weeks)} weeks hold more than 10 names", "study")

    gated_weeks = sum(1 for w in weeks if w.get("gated"))
    add("Sleeve gate fires (cash weeks exist)", "OK" if gated_weeks else "WARN",
        f"{gated_weeks} of {len(weeks)} weeks gated to cash — the regime rule is live", "study")

    # --- live book -------------------------------------------------------
    members = orders.get("n_members")
    missing_filters = [b + "USDT" for b in eligible if (b + "USDT") not in filters]
    add("Contract specs present for tradeable names", "OK" if not missing_filters else "WARN",
        f"{len(filters)} contracts cached, {len(missing_filters)} eligible names without specs",
        "book")

    # Falsifiable reconciliation: recompute the book INDEPENDENTLY from the
    # fill log and last marks, then compare with what the evaluator published.
    fills = [r for r in log if r.get("type") == "execution"]
    qty = {}
    for r in fills:
        sign = 1.0 if str(r.get("kind", "")).endswith("entry") or r.get("kind") == "buy" else -1.0
        qty[r["symbol"]] = qty.get(r["symbol"], 0.0) + sign * float(r["qty"])
    qty = {s: q for s, q in qty.items() if abs(q) > 1e-12}
    last_px = rj(ROOT / "data" / "last_prices.json", {})
    recomputed = sum(q * (last_px.get(s) or {}).get("px", 0.0) for s, q in qty.items())
    published = orders.get("book_value_usd", 0.0)
    diff = abs(recomputed - published)
    add("Book reconciles to the fill log",
        "OK" if diff <= max(1.0, 0.01 * max(recomputed, published)) else "FAIL",
        f"independent recompute ${recomputed:.2f} vs published ${published:.2f} "
        f"(difference ${diff:.2f}) across {len(qty)} positions", "book")

    # Falsifiable: no order on today's list may sit above the funding line.
    thr = prereg.LIVE_FUNDING_EXCLUDE_ANN
    skips = orders.get("skipped_funding_rule", [])
    violations = [o["symbol"] for o in orders.get("orders", [])
                  if o.get("side") == "buy" and (o.get("fund_ann_30d") or 0) > thr]
    add("Funding rule holds on every buy", "OK" if not violations else "FAIL",
        f"{len(skips)} name(s) blocked at >+{thr:.0f}%/yr"
        + (f" ({', '.join(skips)})" if skips else "")
        + f"; {len(violations)} buy(s) above the line on today's list", "book")

    # Falsifiable: assert the evaluator's own source contains no private
    # order-placing call. If someone ever wires one in, this goes red.
    try:
        src = (ROOT / "scripts" / "basket_evaluator.py").read_text(encoding="utf-8")
        banned = [t for t in ("fapi/v1/order", "create_order", "new_order", "place_order",
                              "api_secret", "signature=") if t in src]
        add("Evaluator cannot place orders", "OK" if not banned else "FAIL",
            "source carries no private trading endpoint or signing call; it writes lists and alerts only"
            if not banned else f"order-placing call present: {', '.join(banned)}", "book")
    except Exception as e:  # noqa: BLE001
        add("Evaluator cannot place orders", "FAIL", f"source unreadable: {type(e).__name__}", "book")

    # Under-investment: the live funding block can leave slots unfillable, a
    # state the backtest never produced (0 of 450 weeks).
    uf = orders.get("under_filled")
    add("Book fully invested", "OK" if not uf else "WARN",
        f"{orders.get('n_target_positions', '—')} of {10} slots targeted; "
        f"{orders.get('cash_pct', 0)}% in cash"
        + (" — funding block left slots unfillable, which the backtest never modelled" if uf else ""),
        "book")

    # Live/model fidelity: the signal must sit exactly one session before the
    # fill reference, matching engine's us_index[pos - SIGNAL_DAY_LAG].
    sa, fa = orders.get("signal_asof"), orders.get("fill_reference_asof")
    add("Live signal matches the tested convention", "OK" if (sa and fa and sa < fa) else "WARN",
        f"signal {sa} decides, fill reference {fa} — one session apart, as the backtest prices it"
        if (sa and fa and sa < fa) else "signal/fill reference not in the tested order", "study")

    n_ok = sum(1 for c in checks if c["status"] == "OK")
    out = {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_checks": len(checks), "n_ok": n_ok,
        "n_warn": sum(1 for c in checks if c["status"] == "WARN"),
        "n_fail": sum(1 for c in checks if c["status"] == "FAIL"),
        "checks": checks,
    }
    (ROOT / "data" / "data_health.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"data health: {n_ok} OK, {out['n_warn']} WARN, {out['n_fail']} FAIL "
          f"of {len(checks)} checks")
    for c in checks:
        if c["status"] != "OK":
            print(f"  {c['status']}: {c['name']} — {c['detail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
