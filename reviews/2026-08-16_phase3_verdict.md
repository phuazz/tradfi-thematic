# Phase 3 — verdict (filed)

**Date:** 2026-08-16 · **Context:** Personal · Reads the frozen bars of
`reviews/2026-08-16_phase1_preregistration.md` EXACTLY as written, against
`data/phase2_results.json` (engine ab33206, results fad7eca; 11-test suite green
including the no-look-ahead fixture before any result was read).

## Verdicts

1. **Top-K momentum selection beats its own equal-weight basket (bar 1):
   REJECTED.** Primary cell (K=5, cluster cap 2), 1× costs, net Sharpe
   +1.03 / +0.98 / +0.94 across the {0, +3, +6}%/yr funding band against the
   basket's +1.20 / +1.07 / +0.94 — never ahead by the required +0.10.
   The filed sleeve-C failure mode replicated on this menu: concentration
   doubles CAGR (+46.5% vs +21.0% at the band edge) at −57.4% MaxDD vs −39.9%,
   and loses on the frozen risk-adjusted metric.
2. **The momentum ranking carries real selection information (null check):
   CONFIRMED.** Net Sharpe 0.942 at the band edge sits at the **97.4th
   percentile** of 1,000 cost-matched random same-shape selections (null p50
   0.557, p90 0.818; frozen seed). The ordering is real; the concentrated
   shape is what loses to the basket.
3. **The equal-weight TradFi basket clears the shipping bar (bar 2):
   CONFIRMED, and it ships.** Net Sharpe +0.94 at the band edge (bar ≥ +0.40),
   positive net totals everywhere, invariant to 2× and 4× cost stress
   (+0.94 / +0.94 — weekly turnover is tiny). Split-half +0.80 / +1.09
   (primary-cell series; report-only).

## Standing caveats (carried on every number above)

- **Menu survivorship**: the universe is Binance's 2025–26 selection; every
  ABSOLUTE level is upward-biased by construction, and the own-the-menu basket
  is the shape that bias flatters most. The bar-2 pass licenses a micro shadow
  that generates live funding and fill evidence — it is not a forecast of
  +21%/yr.
- **Funding was a band, not data**; the live +30%/yr funding-exclusion rule is
  untested by construction and remains insurance, not edge.
- Weekly-close basis understates intraweek drawdown identically across all
  comparators.

## Observation filed for a FUTURE pre-registration (no verdict weight)

The declared grid's widest cell, K=10 uncapped, printed +1.24 at the band edge
— above the basket. Under the freeze this cannot be promoted (best-cell
selection after results is the exact practice the primary-cell discipline
exists to prevent). A successor study may pre-register wider-book selection as
its primary; it inherits this register.

## Shadow state (bar 4)

Pre-authorisation conditions are met: the shipping configuration held its bar
at 2× costs. The basket shadow protocol is drafted activation-ready
(`reviews/2026-08-16_basket-shadow-protocol.md`) with ONE owner input
outstanding — the book cap (the ~140-name basket is bounded below by exchange
minimum order sizes; approximately US$3–7k for ~US$20–50 per name, or a defined
tranche). Activation on that number; combined close-out with the WS17 SMH
shadow remains targeted at 2026-09-13.
