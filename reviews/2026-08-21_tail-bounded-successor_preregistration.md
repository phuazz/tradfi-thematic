# Pre-registration — tail-bounded rotation, the second and FINAL look

**Status: DRAFT, awaiting owner sign-off.** Nothing in this design has been run.
On sign-off the constants freeze into `scripts/prereg_killtest2.py`, this
document is committed unchanged, and only then is anything computed.

**Date drafted:** Friday 2026-08-21 · **Context:** Personal · **Project:**
tradfi-thematic (successor to the 2026-08-20 kill-test) · **Author:** prepared
for ZH's review.

---

## 1. Why this study exists, and what it is not

The 2026-08-20 kill-test failed H1 as frozen: top-K rotation on MA200-distance
does not beat owning its own universe by ≥ +0.10 Sharpe across the funding
band. That verdict stands and is not re-litigated here. What the same declared
outputs showed alongside the failure:

- the selection ordering is real (100th percentile against a null whose median
  is negative);
- the tail behaviour is where the construction earns its keep — Calmar
  0.22/0.13/0.07 across the band against the basket's 0.10/0.05/0.00, with
  drawdown essentially financing-insensitive;
- caps and the gate are tail tools (≈11pp of MaxDD at K=5 and K=20 for ~+0.02
  Sharpe; gate −41% vs −66% MaxDD);
- 12-1 momentum ranks better than MA200-distance (+0.440 vs +0.368), the
  direction the signal-by-structure principle predicted for a broad universe.

This study asks ONE new question, declared before any new number exists: **does
a drawdown-bounded rotation — shape derived from risk policy, not tuned —
deliver materially better tail-adjusted returns than owning the same universe,
on data none of this workstream has touched?**

**Seen-data statement (binding).** Every design choice below — the metric, the
ranking statistic, K, the caps, the gate — was made after observing the
kill-test's results on the S&P 500 + Nasdaq-100 panel. That panel is therefore
SEEN and carries no verdict weight here. The only verdict-bearing evidence is a
single run on the held-out Russell arm (kill-test Amendment 1), which no result
of this workstream has touched. **This is the second and final look: if S1
fails on the confirmation run, the construction family closes permanently — no
third study, no re-specification, regardless of how near the miss.**

## 2. Hypotheses

**S1 — PRIMARY.** On the held-out universe, the constraints-derived rotation
beats owning the same universe on tail-adjusted return, robustly across the
funding band and cost stress, with the drawdown bound it claims.

**S2 — MECHANISM (theme definition).** A correlation-cluster theme cap
truncates drawdown at least as well as the GICS sector cap without giving up
ranking quality. This is the one genuinely NEW mechanism in the study; GICS
caps cannot see cross-sector theme piling (the AI complex spans four sectors).

Report-only, no verdict weight: gate on/off on Calmar; split-half
(2006–2015 / 2016–present); the SEEN S&P+NDX panel re-run under this exact
spec, labelled SEEN, for continuity; bootstrap confidence interval on the
Calmar margin.

## 3. Construction (derived, not tuned — no grid exists in this study)

Risk policy sets the shape; nothing is searched:

- single name ≤ 10% of book ⇒ with equal weights 1/K, **K = 10** (the minimum
  K satisfying the bound);
- theme ≤ 25% of book ⇒ **cap = 2 slots per theme** (2/10 = 20%);
- eligibility and gate inherited unchanged: price ≥ MA200 × 1.05 to qualify;
  fewer than 30% of the eligible universe qualifying ⇒ 100% cash;
- ranking: qualifiers ranked by **12-1 momentum** — P(t−21)/P(t−252) − 1 on
  the signal date, sessions not calendar days, exactly as the kill-test H3 arm
  computed it;
- weekly cadence, signal one session before the fill (SIGNAL_DAY_LAG = 1),
  equal weight 1/K, ties broken by signal then alphabetically.

**Theme definition (S2), frozen spec:** pairwise Pearson correlation of
trailing 104 weekly returns (minimum 52; shorter histories form singletons),
distance 1 − ρ, average linkage, tree cut at distance 0.5, clusters re-formed
on the first rebalance of January, April, July and October using only data
strictly before the formation date. Arms: cluster-cap vs GICS-sector-cap vs
uncapped. **Degeneracy guard, frozen:** if on any formation date the largest
cluster holds more than 40% of eligible names, or more than 60% of names are
singletons, clustering is declared degenerate and the study falls back to the
GICS cap throughout — no re-specification of the clustering.

## 4. Universe — the held-out confirmation set

- **Russell 1000 Current & Past** (Norgate), delisted names included via the
  US Equities Delisted database, prices CAPITAL-adjusted (price-only, as a
  perp tracks).
- Eligible at signal date t: ≥ 252 sessions of history; price fresh within 3
  sessions; and in the **top 250 by trailing 60-session median dollar volume**
  among Current & Past names alive at t. The screen uses trailing data only.
- Window 2006-01-01 → present; GICS sectors from Norgate for the sector-cap
  arm.
- The S&P 500 + Nasdaq-100 panel is used ONLY for the labelled SEEN
  continuity run.

## 5. Costs and funding (inherited unchanged from the kill-test)

10bp round-trip fees per unit turnover, stressed at 2× and 4×; funding =
3-month T-bill + premium, premium ∈ {0, +3, +6} %/yr on invested capital;
cash earns the T-bill; no dividend charge (prices are dividend-free by
construction). The full band including the 0% point is retained deliberately:
drawdown was financing-insensitive in the kill-test (−36/−41/−46% across the
band), so a tail-metric bar does not hinge on the optimistic edge the way the
Sharpe margin did — and if it turns out to, that is a finding, not a nuisance.

## 6. Bars (frozen; read once, on the single confirmation run)

**S1 passes** iff, on the Russell confirmation run at 1× costs, at EVERY
premium in {0, +3, +6}:

- (a) Calmar(rotation) − Calmar(basket) ≥ **+0.05**;
- (b) Sharpe(rotation) ≥ Sharpe(basket);
- (c) MaxDD(rotation) ≤ **0.75 ×** MaxDD(basket), magnitudes;

AND at 2× costs, (a) holds with margin ≥ 0.00 and (b), (c) hold unchanged;
AND (d) at the band edge, rotation Calmar ≥ the **90th percentile** of 1,000
cost-matched random same-shape portfolios, frozen seed **20260821**.

The comparator basket is the equal-weight of the same eligible top-250 set,
identical costs and funding treatment. Calmar = CAGR / |MaxDD| on the weekly
series, whole window.

**S2 adopts the cluster cap** iff, at the band centre and 1× costs, its MaxDD
is the shallowest of {cluster-cap, GICS-cap, uncapped} AND its Sharpe is
within 0.03 of the best of the three; otherwise the GICS cap is the shipped
definition. The degeneracy guard above overrides.

**Kill criterion.** S1 failing closes the construction family for good. The
Binance book never un-pauses for this strategy; the workstream keeps only its
venue and execution learnings. There is no KT-3.

## 7. The ways this could be silently wrong (stated before any code)

1. **Liquidity screen look-ahead** — ranking by dollar volume computed over a
   window that touches the future admits winners early. *Guard:* the median
   uses sessions strictly before t; pinned by a test that shifts the window
   forward and asserts the eligible set changes.
2. **Cluster formation leak** — clusters formed with returns from on or after
   the formation date import the future into the cap structure. *Guard:* a
   synthetic leak control — inject a spike after the formation date, assert
   cluster assignments are unchanged.
3. **Calmar fragility** — MaxDD is a single order statistic; Calmar on one
   path is noisy. *Mitigations, declared:* margins against a basket sharing
   the same shocks (level noise nets out), a 20-year window, and a bootstrap
   CI reported alongside. The residual fragility is stated in the verdict,
   not hidden.
4. **Inherited failure modes** — survivorship (index turnover, dead-name
   endings), rate units, signal-precedes-fill: the kill-test's guard tests are
   re-pinned on the new panel before any strategy result is computed.

## 8. Scope — what this study does NOT do

No change to any deployed book; the Binance book stays paused (protocol
Amendment 4) regardless of interim results. No interference with the WS7
C-seat review (2026-10-02) and no reading of its OOS tracker. No re-tuning of
MA window, floor, gate threshold, K or caps — all inherited or derived. No
vol targeting, stops, or overlay knobs (risk-overlay-lab: six failures). No
relative or residual momentum (WS5). No non-US extension (2026-08-13
procurement memo). Entry-point discipline applies to any eventual deployment
decision: deploy after flat or negative stretches of the strategy, not after
strong runs.

## 9. Phases

- **KT-1 filing first (due Mon 2026-08-24):** the kill-test's ledger row,
  register records (H1/H2/H3/M1) and the four filing guards go in BEFORE this
  study runs, so the record cannot be coloured by what follows.
- **P0 — Russell panel build + guards (Mon 2026-08-24):** universe, liquidity
  screen, sectors, clusters machinery; all guards of section 7 green; no
  strategy number computed.
- **P1 — freeze (at sign-off):** constants into `prereg_killtest2.py`.
- **P2 — single confirmation run (Thu 2026-08-27):** S1, S2, arms, null,
  bars read exactly as written.
- **P3 — verdict and filing (Mon 2026-08-31):** ledger + register + guards;
  dashboard updated with whatever the answer is. Ahead of the 2026-09-13
  close-out, which then reads this verdict.

All dates weekday-verified by date library (Python `datetime`, months
1-indexed): 2026-08-24 Monday, 2026-08-27 Thursday, 2026-08-31 Monday.

---

**Sign-off (owner):** SIGNED — ZH, in session. **Date:** 2026-08-21 (Friday).
The three named confirmations stand as written: Calmar-primary bars (§6), the
Russell 1000 C&P top-250 confirmation universe, and the finality clause.

## Implementation notes recorded at P0 (before any strategy result)

1. **Liquidity screen, frozen details.** Candidates at t are names with a
   fresh bar (staleness ≤ 3 sessions); the trailing 60-session median dollar
   volume requires ≥ 30 non-missing sessions in the window (`DV_MIN_OBS = 30`)
   so a newly listed or dying name cannot be ranked on a handful of prints.
   The window ends the session BEFORE t — pinned by a guard test that injects
   a future volume spike and asserts the selection is unchanged.
2. **Clustering implementation.** scipy 1.17.1 average-linkage on 1 − ρ with
   `squareform`; pairs with insufficient overlap take distance 1 (never
   co-clustered); names under 52 weeks form singletons. The degeneracy
   detector is itself guard-tested on constructed degenerate data.
3. **Schedule.** P0 run 2026-08-21, ahead of the planned Monday, at owner
   instruction — in the same sitting as, and after, the KT-1 filing, so the
   record order (filing first) is preserved. No strategy number was computed
   in P0.

## Implementation notes recorded at P2, committed BEFORE the run

1. **Run brought forward** from Thu 2026-08-27 to 2026-08-21 at owner
   instruction. Schedule only: the panel is static history and nothing
   matures by waiting. The engine and these notes are committed before the
   run; the run happens once.
2. **2×-costs clause read at EVERY premium** — the strictest available
   reading of §6, declared here before any number exists.
3. **Cluster formation name-set:** all names fresh (≤ 3 sessions) at the
   formation date; a name entering the universe mid-quarter is a singleton
   until the next formation, so the cap cannot bind it.
4. **Split-half basis:** the adopted arm at the band edge (matches KT-1's
   convention). Report-only.
5. **Bootstrap CI (report-only):** joint circular block bootstrap of the
   (rotation, basket) weekly pairs at the band centre — blocks of 13 weeks,
   2,000 draws, seed 20260822. Blocks preserve some drawdown autocorrelation;
   the residual understatement is acknowledged, not hidden.
6. **SEEN continuity run:** KT-1 membership eligibility with KT-2
   construction; theme arm = whichever the Russell run adopts (falling back
   to GICS if the SEEN panel's own clustering is degenerate).
7. **Hard asserts live in the engine** (picks within the eligible set, cap
   respected per label, invested ≤ 1) — a violation raises rather than
   degrades.

*Three things to confirm when signing, named now so they cannot move later:
the primary metric (Calmar margins vs the basket, bars in §6), the held-out
confirmation universe (Russell 1000 C&P, top-250 by dollar volume), and the
finality clause — S1 failing ends the family with no third study.*
