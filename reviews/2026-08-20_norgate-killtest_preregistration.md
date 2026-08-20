# Pre-registration — Norgate kill-test: does the rotation rule survive an honest universe?

**Status: DRAFT, awaiting owner sign-off.** Nothing in this design has been run.
On sign-off the constants below are frozen into `scripts/prereg_killtest.py`, this
document is committed unchanged, and only then is the first result computed.

**Date drafted:** Thursday 2026-08-20 · **Context:** Personal · **Project:**
tradfi-thematic (continuation) · **Author:** prepared for ZH's review.

---

## 1. Why this study exists

The 2026-08-20 correction established that the tradfi backtest is not evidence:
the tradeable universe did not exist before 2025-12-11, 90% of contracts listed
after May 2026, and the top five contributors — 47.5% of the whole simulated
return — all had their contracts listed in 2026, after the runs the curve
claimed. Under a point-in-time listing gate the same rule earned −5.6% over the
only 37 weeks it could have been traded, against +10.1% for an equal-weight
basket and +13.1% for simply holding SPY.

That kills the *evidence*, not the *question*. The question is whether the RULE
— rank on distance above the 200-day average, hold the top K, cap per theme,
go to cash on weak breadth — has any merit at all. That can be answered
honestly, because Norgate's US archive supports a survivorship-free,
point-in-time universe over two decades.

**This is framed as a kill-test, not a search.** The prior (section 2) is that
it fails. The purpose is to establish that cleanly and close the workstream, or
to be surprised on evidence that could not have been reverse-engineered.

## 2. Ledger check — ADJACENT, and the prior is unfavourable

Run 2026-08-20 over `hypotheses_index.md` and `STUDIES_LEDGER.md`.

| Record | Verdict | What it says |
|---|---|---|
| 2026-07-02-breadth-thrust-etf-1 † | rejected | Alternative MA formulations (vol-scaled, ensemble, re-fitted horizon) all lose to the deployed 200-day, which sits on a **flat plateau**. Do not re-tune the MA. |
| 2026-07-03-breadth-thrust-etf-1 † | rejected | Deployed config kept across ~217 registered configurations — heavy search does not improve it. |
| 2026-07-03-breadth-thrust-etf-2 † | rejected | Annual full-config re-fit lost −0.205 out-of-sample. Fixed beats adaptive here. |
| 2026-07-15-crypto-breadth-7 † | no-effect | Concentration floors and per-name caps: five arms statistically indistinguishable. |
| 2026-07-04-crypto-breadth-4 † | conditional | The breadth gate IS load-bearing on a concentrated crypto universe (+0.61 Sharpe, +38pp drawdown vs no gate) — but only tested there. |
| 2026-08-16-tradfi-thematic-1 | rejected | Top-K selection never beat its own equal-weight basket by the +0.10 bar on the tradfi menu. |
| WS3 / sleeve C (2026-07-18 row) | on notice | Sleeve C's seat is under review precisely because rotation loses to equal-weight; the live tracker's first two OOS weeks read rotation vs EW **−2.58pp**. |

† = unreviewed extraction; treat the verdict as an unverified figure.

**Three filed results already say selection loses to its own basket.** This study
is the fourth look. It is worth running only because its universe is genuinely
new — survivorship-free, point-in-time, multi-cycle, and broad rather than a
venue's curated list — and because two sub-questions are unsettled anywhere in
the vault: whether the **breadth gate** earns its keep on a broad universe, and
whether **MA200-distance** beats plain price momentum as the ranking statistic.

**Non-interference with WS7 (binding).** The C-seat review is pre-registered for
Friday 2026-10-02 with gates pending countersign, and its watch line tracks the
same rotation-vs-equal-weight comparison out of sample. This study must not be
cited to pre-empt it, must not read `c_seat_watch.json` OOS gaps, and touches no
deployed sleeve. Its universe is US single stocks and ETFs, not sleeve C's
thematic menu.

## 3. Hypotheses (frozen)

**H1 — PRIMARY, the kill-test.** Over a survivorship-free point-in-time US
universe, top-K rotation on MA200-distance beats an equal-weight basket of the
same eligible universe, net of all modelled costs.

**H2 — the gate.** The 30% breadth-to-cash gate improves risk-adjusted return
against the identical construction with the gate disabled.

**H3 — the ranking statistic.** MA200-distance beats plain 12-1 price momentum
as the ranking input, holding everything else fixed.

**M1 — MEASUREMENT, not a hypothesis.** Running the identical rule restricted to
the 115 Binance-listed names quantifies the menu-selection premium: the gap
between the honest universe and the hindsight one. Deliberately contaminated,
reported as a number, never as a verdict.

## 4. Universe (frozen)

- **PRIMARY:** union of **S&P 500 and Nasdaq-100 point-in-time membership**, read
  per rebalance date from `index_constituent_timeseries`, including delisted
  names from the US Equities Delisted database.
- **ROBUSTNESS ARM:** Russell 1000 Current & Past, restricted at each date to the
  **top 250 by 60-day median dollar volume** — closer to "what a venue would
  plausibly list", noisier to define, reported alongside but not verdict-bearing.
- **MENU ARM (M1):** the 115 eligible tradfi names resolvable in Norgate.
- **Eligibility at date t:** member of the universe on t, ≥252 sessions of price
  history by t, price fresh within 3 sessions. A name delisted at t+1 keeps its
  terminal return; it is never silently dropped.
- **Window:** 2006-01-01 → present (membership series begin 2005; one year of
  warm-up for the 200-day average and the 252-day eligibility rule).
- **Theme:** GICS sector from Norgate, read point-in-time where available.

## 5. Signal and construction (inherited unchanged — no re-tuning)

Identical to the frozen tradfi rule: rank on `close / MA200 − 1`; entry floor
**+5%**; **30%** sleeve-breadth gate to cash; equal weight 1/K; signal read one
session before the fill, executed at that next close; weekly cadence.

**Declared grid, primary named now:** K ∈ {5, **10**, 20} × sector cap ∈ {2, none}.
**PRIMARY CELL: K=10, cap 2.** Every cell is reported; the verdict reads only the
primary. Ties broken by signal then alphabetically.

## 6. Cost model (frozen) — funding becomes rate-linked

Fees: **10bp round trip** per unit turnover, stressed at **2× and 4×**.

Funding replaces the flat band with the economics of a financed equity position:

> **funding_t = 3-month T-bill rate at t + premium**, premium ∈ {**0, +3, +6**} %/yr,
> charged on invested capital only.

Calibration, measured 2026-08-20 from 90 days of realised settlements across 65
live Binance TradFi perps: universe median **+6.8%/yr**, mean +8.0%, p90 +17.2%,
against a 3-month T-bill of **3.7%** — implying a demand premium near **+3%/yr**,
which is the middle of the declared band. Rate history from `^IRX` (1995→). This
matters because a flat band is wrong in both directions across history: it
overcharges the 2021 zero-rate years (~3% true carry) and undercharges 2023
(~8%).

Dividends: per-name trailing yield subtracted on holdings (perps are price-only).
Cash earns the T-bill rate when the gate is active — an improvement on the tradfi
model, which paid zero on cash and thereby penalised the gate.

## 7. Comparators, null and bars (frozen)

- **PRIMARY comparator:** equal-weight basket of the same eligible universe,
  same costs, same funding treatment.
- **Null:** 1,000 cost-matched random same-shape portfolios (same K, cap, floor,
  gate, turnover), frozen seed **20260820**.
- **Context benchmark:** SPY total return (no verdict weight).
- **Split-half:** 2006–2015 vs 2016–present, report only.

**H1 passes** only if the primary cell's net Sharpe exceeds the basket's by
**≥ +0.10 across the entire premium band at 1× costs**, AND is ≥ the basket at
2× costs, AND sits at or above the **90th percentile** of the null.

**H2 passes** if gate-on beats gate-off by **≥ +0.10 Sharpe** at the band centre.

**H3 passes** if MA200-distance beats 12-1 momentum by **≥ +0.10 Sharpe** at the
band centre, primary cell.

**KILL CRITERION.** If H1 fails, the rule does not beat owning the same universe
on the only honest evidence available, and **the strategy case closes**: the
tradfi workstream is filed as rejected, the live book continues only as a
venue/execution test with no claimed edge, or stops at the owner's discretion.
No further configurations are searched. A failure here is the deliverable.

## 8. The ways this could be silently wrong (stated before any code)

1. **Membership read as current rather than point-in-time** — the classic way
   survivorship creeps back in. *Guard:* assert membership is queried per date;
   pin a test on a known deletion (a name removed from the S&P 500) proving it is
   present before its removal date and absent after.
2. **Delisted names dropped instead of realised** — if a failing name silently
   leaves the panel, the universe quietly becomes winners-only, which is the exact
   defect this study exists to avoid. *Guard:* count delisted holdings and assert
   terminal losses appear; assert universe size is roughly stationary over time
   rather than growing toward the present.
3. **Rate units** — `^IRX` quotes an annualised percentage (3.7), not a fraction
   (0.037). Using it raw inflates funding a hundredfold. *Guard:* unit test on the
   conversion plus an assertion that modelled funding averages ~3% in 2021 and
   ~8% in 2023.
4. **Look-ahead at the signal seam** — inherited convention; re-pin the existing
   no-look-ahead test with its leak-detection control on the new data path.

## 9. Scope — what this study does NOT do

No change to any deployed book. No new live capital. No interaction with WS7 and
no reading of sleeve C's OOS gaps before 2026-10-02. No re-tuning of the MA
horizon, the floor or the gate threshold (all inherited; the plateau finding
stands). No non-US extension — the 2026-08-13 procurement memo already
established that survivorship-free European and Asian data is unavailable at
sane cost, so the 17 KR/HK names stay out and that limit is stated in the verdict
rather than worked around.

## 10. Deliverable and phases

- **P0 — universe build (Mon 2026-08-24):** Norgate point-in-time membership
  loader, delisted-inclusive price panel, GICS sectors, the four guards of
  section 8 green before any strategy result is computed.
- **P1 — freeze and run (Thu 2026-08-27):** constants frozen in code, grid ×
  premium band × cost stress, null, split-half, plus arms M1/H2/H3.
- **P2 — verdict (Mon 2026-08-31):** bars read exactly as written; ledger row,
  register records, all four filing guards; dashboard updated with whatever the
  answer is.

Deliberately ahead of the 2026-09-13 shadow close-out, so that the close-out can
read this verdict when it re-decides the live payload.

---

**Sign-off (owner):** ______________  **Date:** ______________

*Two things to confirm when signing: the PRIMARY universe (S&P 500 + Nasdaq-100
point-in-time) and the PRIMARY cell (K=10, cap 2). Both are named now precisely
so they cannot be chosen after the results are visible.*
