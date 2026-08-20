# Basket shadow protocol — Binance TradFi equal-weight basket (ACTIVATION-READY)

**Date drafted:** 2026-08-16 · **Context:** Personal · **Status:** awaiting ONE
owner input — the book cap (§2). Everything else is frozen at drafting, before
any live order. Pre-authorisation per the kickoff (owner, 2026-08-16) attaches:
bar 2 held at 2× costs, so activation requires the cap number only, no further
sign-off round. WS17 guard set inherited unchanged.

## 1. Objective

Generate the live evidence the backtest cannot: realised funding across a broad
TradFi holding (the band was an assumption; live funding concentrates in hot
names), realised fill costs on Binance TradFi perps at micro clips, and weekly
maintenance ops. NOT an expected-return claim — the menu-survivorship caveat
stands.

## 2. Book (the one owner input)

- **Option A — full basket:** all rotation-eligible names with listed, liquid
  perps (scanner ADV ≥ US$5M at establishment), equal weight; practical floor
  ≈ US$20–50 per name → **US$3–7k book**.
- **Option B — defined tranche:** the top-N names by perp ADV (N chosen at
  activation, e.g. 50), equal weight, ~US$1.5–3k; narrower funding evidence,
  same ops evidence.
- Leverage **1×** (fully collateralised); any margin call is FAIL-OPS.

**Book cap: US$5,000 (owner, in session, 2026-08-16)** · **Option: A — full basket.**
Activated 2026-08-16 on the owner's number, per the standing pre-authorisation.
Equal-weight target = cap / N over the establishment-eligible set; names whose
target falls below the contract's minimum notional are bumped to the minimum
(logged as deviations), the rest renormalised.

**Execution windows (documented at activation):** establishment tranches on
weekday mornings 07:30–09:30 SGT (≤5 sessions from 2026-08-17); weekly
maintenance in the SATURDAY 07:30–09:30 SGT window — closest to the model's
Friday-close rebalance, with the known weekend-liquidity caveat carried
deliberately: thin Saturday fills are exactly the execution evidence this
shadow exists to measure. **Liquidity gate at establishment:** membership in
the scanner's liquid set over the trailing seven days' scans (rolling union),
so weekend-window scans cannot wrongly exclude weekday-liquid names.

## Amendment 1 (2026-08-16, before any fill was logged) — EQUITY-ONLY membership

Owner instruction at end of session: "focus on tradfi equity only." Membership
narrows to equity underlyings — the commodity cluster (gold, silver, platinum,
palladium, WTI, Brent, copper, natural gas) is excluded from the live basket.
No fill had been logged, so nothing unwinds; tranche 1 regenerates tonight.
Disclosed divergence: the FILED bar-2 verdict was computed on the full menu
including commodities; the equity-only basket is re-anchored by a supplementary
engine run (same frozen cost model, no parameters to tune in an equal-weight
basket) recorded in the memo, and the register record's tested object stands
as filed. Display names accompany tickers on every order list from this
amendment onward.

## Amendment 2 (2026-08-20, before any fill was ever logged) — PAYLOAD PIVOT TO ROTATION

Owner decision, 2026-08-20: the equal-weight basket is rejected for the live
book on two grounds — operational load (51+ standing positions and orders) and
listing-chase exposure (membership grew 51 → 57 in four days as Binance listed
more perps; an equal-weight book mechanically follows the venue's listing
choices). Zero fills were logged, so nothing unwinds; establishment never
started.

**New live payload: the K=10, cluster-cap-2 rotation** at the same US$5,000
cap (~US$500 per name), same 1× leverage, same FAIL triggers, same 2026-09-13
close-out. Filed grid figures: net Sharpe +1.20 / +1.14 / +1.07 across the
{0,+3,+6}%/yr band, MaxDD −41% to −47%; measured trade load ~3.3 orders per
week with a quarter of weeks needing none.

**Disclosures that make this honest:**
- **Seen-data caveat, carried permanently:** every grid cell's result was
  observed before this pick, so K=10 cap=2 is a seen-data selection (the WS6b
  deploy-with-caveat precedent). The pre-registered PRIMARY (K=5 cap=2) and
  the filed verdict (basket ships) stand unchanged in the record; this
  amendment overrides the shipping decision for the live book only, by owner
  instruction.
- **Gate run before activation, stated before its result was known:** the
  original null was K=5-shaped, so a fresh 1,000-path null at the K=10 cap=2
  shape (same frozen seed and construction) was required to clear ≥ the 90th
  percentile. **Result: strategy 1.07 = 99.9th percentile** (null p50 0.614,
  p90 0.831, p95 0.877; `data/k10_null.json`). Passed.
- **Cadence in live form:** the panel refreshes Saturdays, so the rotation
  list is computed from the Friday close and executed in the SATURDAY
  07:30–09:30 SGT window — one session later than the model fills, the same
  offset the maintenance window already carried. Weekday runs are
  establishment (until 10 names are held) and heartbeats. The live
  funding-exclusion rule applies to BUYS only; a held name is never
  force-sold by it. A sleeve-breadth gate week goes to cash (sell list).
- The SMH shadow was descoped the same day (separate owner decision); the
  2026-09-13 close-out now reads this rotation shadow alone.

## Amendment 5 (2026-08-21, later same day) — closure made PERMANENT

KT-2's held-out confirmation run **failed S1 on the drawdown bound**
(`reviews/2026-08-21_kt2_verdict.md`); per the finality clause the owner
confirmed at sign-off, the construction family is closed permanently. The
Amendment 4 pause therefore converts to **permanent closure for this
payload**: the book never un-pauses for this strategy, and no successor study
exists to trigger an un-pause. The evaluator continues in paused mode purely
to keep the record surfaces live until the **2026-09-13 close-out**, which
proceeds as an operations review (disarm the schtask, remove the fleet row,
file the close-out memo). Any future live idea on this venue starts from a
NEW pre-registration of a different construction family, not from this book.

## Amendment 4 (2026-08-21, zero fills ever logged) — book PAUSED

Owner decision 2026-08-21, taken the day the honest-universe kill-test returned
its verdict (H1 FAIL — see `reviews/2026-08-20_norgate-killtest_preregistration.md`
and `RESEARCH_MEMO.md` 2026-08-21): the establishment buys are **not executed**.

**Scope.** `BOOK_PAUSED = True` in the evaluator. Signal, health checks,
dashboard and heartbeat continue unchanged; BUY orders are suppressed from the
order list; risk-reducing SELLS would still be listed if positions existed
(none do — the book has zero fills). The pause is a code-level switch shown as
the leading banner on the dashboard, so no surface can hand the operator a buy
list the owner has declined.

**Un-pause condition.** An explicit owner instruction recorded here as a
further amendment — expected trigger: the successor study's confirmation
verdict (`reviews/2026-08-21_tail-bounded-successor_preregistration.md`).
Never an edit made in passing.

**Close-out.** The 2026-09-13 close-out stands. If the book is still paused
and empty then, the close-out is an operations review only: the execution
triggers read vacuously on zero fills, and the payload re-decision item added
by Amendment 3 is superseded by the kill-test verdict and the successor study.

## Amendment 3 (2026-08-20, still pre-fills) — live aligned to the tested rule

From a three-lens review (quant PM / CIO / CPM) of the dashboard, owner
instruction "aligning live to the model and fix all".

**The defect.** The live evaluator read the signal from the LATEST session,
while the engine reads the session BEFORE the fill (`us_index[pos −
SIGNAL_DAY_LAG]`). Not look-ahead — Friday's close is genuinely known by
Saturday morning — but a **different, unpriced rule**, and slightly more
favourable than the one tested (fresher signal, shorter signal-to-fill gap).
The dashboard asserted both conventions in different places.

**The fix.** The evaluator now reads `us_index[−1 − SIGNAL_DAY_LAG]` and
publishes both `signal_asof` and `fill_reference_asof`, one session apart, on
every order list. Fidelity is chosen over freshness: the shadow exists to
measure execution against a frozen model, and that comparison is only
interpretable if live runs the model's rule. A health check now asserts the
two dates stay in the tested order.

**Also closed in the same pass:**
- Three health checks could not fail (hardcoded OK). Now falsifiable: the book
  is reconciled by independent recomputation against the published value; the
  funding rule is asserted against every buy on the list; and the evaluator's
  own source is scanned for order-placing or signing calls.
- **Under-fill is now surfaced and warned.** The live funding block can leave
  slots unfillable — it does today, 9 of 10 with 10% cash — a state the
  simulation never produced in 450 weeks because it has no funding rule. The
  live book therefore runs less invested than the backtest; disclosed on the
  page and in the footer.
- The null chart plotted the K=5 distribution while the live payload is K=10;
  it now plots K=10 (99.9th percentile) and quotes K=5 beneath.
- Execution quality is instrumented: `log_basket_fill.py` captures the
  modelled reference price at fill time and computes signed slippage, which is
  what FAIL-EXECUTION reads. Positive means worse than the model.

**Missed-window rule (previously undefined, now frozen).** If the Saturday
07:30–09:30 SGT window is missed: execute at the next available window within
48 hours and log the fill as LATE (it still counts toward the execution
statistics). Beyond 48 hours, **skip the week entirely** — do not chase the
trade at a stale signal, and do not double-trade the following week. Two
consecutive missed maintenance windows remain FAIL-OPS.

**Payload re-decision at close-out (added to the agenda).** The 2026-09-13
close-out reads the execution triggers; it must ALSO re-decide the payload
itself — the rotation is a seen-data choice standing against a filed verdict
that went to the equal-weight basket. Passing the execution triggers does not
by itself ratify the construction.

## 3. Mechanics (frozen)

- **Establishment:** orders placed manually across ≤5 sessions in the WS17
  window (07:30–09:30 SGT), logged per fill via `scripts/ws17_log_fill.py`
  conventions (kind `basket-entry`).
- **Weekly maintenance (the live analogue of re-equal-weighting):** trade ONLY
  names whose weight drifts beyond ±25% of target, plus entries of newly
  eligible names and exits of delisted/ineligible ones. Expected: a handful of
  orders per week — the backtest's tiny turnover, made operational.
- **Funding-exclusion rule (live, per pre-registration §2):** a name whose
  trailing 30d funding exceeds +30%/yr is not BOUGHT at establishment or
  maintenance that week (existing holdings are not force-sold by this rule).
- **Logging:** append-only `data/basket_shadow_log.json` — establishment fills
  vs prior-close marks; weekly per-name funding accrued (scanner data joins
  this automatically — `funding_history.json` already covers the universe);
  weekly maintenance orders; ops rows.

## 4. Triggers (frozen; WS17 multiples)

- **FAIL-EXECUTION:** median establishment fill cost vs prior US close exceeds
  15bp (1.5× the modelled 10bp round trip's half), measured over ≥20 fills.
- **FAIL-BAND:** book-level realised funding drag, annualised over any rolling
  4 weeks, exceeds +6%/yr (the band edge the verdict rests on).
- **FAIL-OPS:** two consecutive missed weekly maintenance windows, or any
  margin call at 1×.

## 5. Completion and outcome

- Runs to the combined close-out **2026-09-13** with the WS17 SMH shadow; one
  sitting, both records, one close-out memo either way.
- Pass (no FAIL triggers): a sizing proposal memo for a standing allocation —
  a separate owner decision. Any FAIL: filed against the register record and
  stopped.

## 6. Build prerequisite (starts once the cap lands)

A weekly evaluator in the WS17 pattern (logs and alerts only, never places
orders): computes target weights from the frozen engine, diffs against the
logged book, emails the maintenance order list Friday morning SGT, verifies
freshness, appends ops rows, carries a fleet_watch row (temporary, removed at
close-out). Estimated half a day.
