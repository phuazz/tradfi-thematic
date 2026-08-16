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
