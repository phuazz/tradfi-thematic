# Verdict — Norgate kill-test (filed record)

**Study:** does the rotation rule survive an honest universe?
**Pre-registration:** `reviews/2026-08-20_norgate-killtest_preregistration.md`
(signed 2026-08-20; bars frozen before any result; Amendment 1 withholds the
Russell arm). **Working trail:** `RESEARCH_MEMO.md`, entries of 2026-08-21.
**Artefacts:** `data/killtest_results.json`, `data/killtest_meta.json`,
`scripts/killtest_engine.py`, guards in `tests/test_killtest_universe.py`
(12 tests, each demonstrated to fail on the defect it exists to catch).

**Basis, stated once:** S&P 500 + Nasdaq-100 point-in-time membership, 464
delisted names carried, 1,076 weekly rebalances 2006-01 → 2026-08, price-only
(CAPITAL adjustment), signal one session before the fill, fees 10bp RT,
funding = 3-month T-bill + premium {0, +3, +6}%/yr on invested capital, cash
earning the bill. All figures net.

---

## H1 — rotation beats its own equal-weight basket: REJECTED

Bar: ≥ +0.10 net Sharpe over the basket at EVERY premium at 1× costs, AND
≥ basket at 2×, AND ≥ p90 of the null.

| premium | rotation (K=10 cap 2) | basket | margin | bar |
|---|---|---|---|---|
| 0% | +0.485 | +0.411 | +0.074 | **FAIL** |
| +3% | +0.368 | +0.263 | +0.105 | pass |
| +6% | +0.251 | +0.115 | +0.136 | pass |

Legs 2 and 3 passed (≥ basket at 2× everywhere; null 100.0th percentile
against a **negative** median, −0.172, 1,000 paths, seed 20260820). One
failing band point fails the hypothesis; **the strategy case closes per the
frozen kill criterion**, and no further configurations were searched.

**No declared cell clears.** Margins at the binding 0% point across the full
declared grid: k5_cap2 +0.011, k5_capNone −0.015, k10_cap2 +0.074,
k10_capNone +0.086 (best), k20_cap2 +0.070, k20_capNone +0.031. The K × cap
family is exhausted.

**Mechanism.** The margin rises monotonically with the funding premium because
the rotation is invested less than the basket (10 names of ~500, plus gate
weeks); it pays less financing. The edge is financing-avoidance, not
selection. The pure selection edge over owning the universe — financing
neutralised — is +0.07 to +0.09 Sharpe: real, but under the bar.

## H2 — the breadth gate: NO-EFFECT on the tested statistic

Gate on +0.368 vs off +0.343 = **+0.025** against a +0.10 Sharpe bar.
Recorded alongside, outside the tested statistic: **MaxDD −41.3% gated vs
−65.8% ungated** — a 24.5pp truncation a Sharpe-only bar cannot see,
concordant with the crypto-breadth gate result (−38pp). The bar stands as
frozen; the drawdown finding is preserved here and feeds KT-2's design.

## H3 — MA200-distance vs 12-1 momentum: REJECTED, and backwards

12-1 momentum ranks **+0.440** against MA200-distance's +0.368 (−0.072),
everything else fixed. Direction consistent with the signal-by-structure
prior (broad diversified universe → price momentum). Not adopted
retroactively — that is post-hoc cell selection — but declared as the ranking
of the signed successor.

## M1 — the hindsight premium, measured (not a hypothesis)

Restricting the identical machinery to the 69 Binance-listed names present in
the panel adds **+0.478 Sharpe to the rotation** (+0.846 vs +0.368) and
+0.369 to the basket. This is the size of the menu-selection bias that
invalidated the original 8.7-year backtest: the menu, not the rule, was the
story.

## Context and stability

SPY price-only on the same grid, no costs or financing (context only,
computed post-run as a disclosed omission — zero researcher degrees of
freedom): Sharpe +0.576, CAGR +9.0%, MaxDD −56%. Split-half (primary, band
edge basis): +0.313 / +0.199 — the second half is the calibration any
successor bar should expect. Calmar across the band: rotation 0.22 / 0.13 /
0.07 vs basket 0.10 / 0.05 / 0.00, with MaxDD essentially
financing-insensitive (−36/−41/−46%).

## Disclosures and amendments

1. **SPY benchmark omission** — declared in §7, missing from the P1 run;
   computed 2026-08-21 and appended to the results artefact.
2. **Russell arm (Amendment 1)** — declared in §4, never built or run;
   **withheld un-run** by owner decision 2026-08-21 as the successor's single
   confirmation set. Recorded as withheld, not missing.
3. **Live book paused** (shadow protocol Amendment 4, same day): the Binance
   establishment buys were never executed; `BOOK_PAUSED = True`; un-pause
   only by explicit owner amendment.

## Disposition

Successor **KT-2 signed 2026-08-21**
(`reviews/2026-08-21_tail-bounded-successor_preregistration.md`): tail-metric
primary on the held-out Russell arm, second and FINAL look — its S1 failing
closes the family permanently. Close-out 2026-09-13 becomes an operations
review if the book is still empty.

*Caveats carried permanently: the seen-data status of everything computed on
the S&P+NDX panel after this filing; the menu-survivorship caveat on any
Binance-menu figure; liquidation value after a delisted name's final bar is
not modelled (slightly optimistic for bankruptcies).*
