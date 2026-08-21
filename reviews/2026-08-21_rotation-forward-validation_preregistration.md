# Pre-registration — FV-1: the rotation as a sized sleeve, validated forward

**Status: DRAFT, awaiting owner sign-off.** Follows the owner's recorded
override of the KT-2 finality clause (2026-08-21). Nothing runs until signed.

## 1. What is being validated — and what is not

**Not selection alpha.** The claim "top-K momentum rotation beats owning its
own universe" was tested twice under frozen bars and rejected twice; those
verdicts stand and are not re-litigated by this protocol or by any future
result of it.

**The deployment claim instead:** the KT-2 construction — 12-1 momentum
ranking among MA200 +5% qualifiers, K=10, GICS sector cap 2, 30% breadth
gate to cash, weekly cadence, signal one session before the fill — serves as
the **risk asset inside the cash + margin blend**, at a weight sized by the
drawdown budget, and behaves forward as the seen-data measurement described:
equity-like return with a somewhat shallower, gate-truncated tail.

**Evidence status, binding:** every backtest number behind this protocol is
SEEN (both panels burned by KT-1/KT-2). The forward track is therefore the
ONLY verdict-bearing evidence. And honesty about power: 26 weeks of a
weekly-rebalanced blend proves nothing statistical about returns — the early
reviews below are operations, fidelity and no-surprises gates; the return
claim accrues over years, and the record will say so at every review.

## 2. Construction (fixed at sign-off; no knobs remain)

- Universe for the live computation: the KT-2 point-in-time rule on the
  Russell 1000 namespace (top-250 by trailing 60-session median dollar
  volume, ≥252 sessions history, fresh within 3), computed weekly from
  Norgate locally.
- Selection, cadence, gate: exactly the KT-2 frozen constants
  (`scripts/prereg_killtest2.py`); no parameter may change without a
  numbered amendment here.
- Blend: **w%** in the rotation, (100−w)% in 3-month T-bills, rebalanced to
  weight monthly; w is set by the margin adopted at the 2026-09-30 review
  (menu: `data/hurdle_blend_measurement.json`; the sizing corridor for
  cash+2pp is ~30%, capped so that w × 55% ≤ the whole-of-wealth budget
  share this sleeve is granted).
- Venue (owner blank): **cash equities** is the recommended and default
  answer — no financing drag, dividends kept, no listing-menu risk; the
  measured perp financing wedge (≈ T-bill +3%/yr) was the single largest
  cost in every filed result. The Binance book remains closed (protocol
  Amendment 5); this protocol cannot revive it.

## 3. Track mechanics

- **Paper track from sign-off**: the weekly list and blend NAV computed by
  the local Norgate machinery; published on the tradfi dashboard as derived
  values only (NAV, picks by name — never vendor price series), consistent
  with the standing publication discipline.
- **If and when capital attaches** (owner decision at a review, never
  automatic): fills logged with modelled references exactly as the shadow
  protocol did; slippage vs model is the first thing every review reads.
- Guard layer (required before the track runs unattended): capture-integrity
  check on the weekly computation, a fleet_watch row, and the no-look-ahead
  and cap asserts already pinned by the KT-2 test suite.

## 4. Reviews and stop conditions (frozen)

- **First review: 2026-09-30** (with the command-centre quarterly — margin
  and w adopted there), then quarterly.
- Early stop, any of: the sleeve's contribution breaches its granted share
  of the −30% budget (measured, not estimated); a fidelity failure (live vs
  model beyond declared tolerance once capital attaches); two consecutive
  missed weekly computations; owner discretion, logged.
- **What would count as forward validation** (declared now so it cannot be
  chosen later): after **104 weeks** of track, the realised blend sits
  within its seen-data envelope — rolling drawdown no deeper than the
  measured worst at that weight, and realised excess over T-bills not below
  the measurement's 10th percentile of same-length windows. Failing either
  files a rejection of the DEPLOYMENT claim; passing upgrades the sleeve
  from provisional to standing at the then-current review.

## 5. Scope

No interference with WS7 (sleeve C, 2026-10-02). No change to the engine or
any deployed book. No further backtests on the burned panels as evidence.
The 2026-09-13 Binance ops close-out proceeds unchanged.

---

**Sign-off (owner):** ______________  **Date:** ______________
*Blanks to confirm: the venue (cash equities recommended), and that w waits
for the margin decision at the 2026-09-30 review — the paper track can start
at a provisional w=30% immediately on sign-off and re-size at the review.*
