# RESEARCH_MEMO — tradfi-thematic

Running memo. Newest entries at the top. Verdicts and filed records go to the vault
ledger; this file is the working trail.

---

## 2026-08-21 — Post-verdict: successor exploration on DECLARED outputs; two omissions disclosed

Owner direction (Fable session): think through how the construction could work —
e.g. a ≤25% per-theme concentration bound — with more critical thinking. Every
number below reads pre-declared P1 outputs; no new configuration was run; the H1
kill verdict stands as filed.

- **The K × sector-cap family is exhausted.** All six declared cells fail H1 at
  the binding 0%-premium point; the best margin is k10_capNone at **+0.086**
  against the +0.10 bar. The pure selection edge with financing neutralised is
  +0.07 to +0.09 Sharpe — real (null median negative, 100th pct) but thin.
- **Sector caps are a tail tool, not a Sharpe tool.** cap2 minus capNone at the
  band centre: K=5 **+11.5pp** shallower MaxDD for +0.019 Sharpe; K=20
  **+10.5pp** for +0.013; K=10 a wash (−0.027 Sharpe, −0.5pp). The owner's ≤25%
  bound is already satisfied by the tested primary (2/10 = 20%). Gap worth a
  successor: GICS caps miss cross-sector theme piling (the AI complex spans
  four sectors) — a correlation-cluster theme definition is untested machinery.
- **The metric was the binder.** Calmar across the band: rotation (primary)
  0.22 / 0.13 / 0.07 vs basket 0.10 / 0.05 / 0.00; MaxDD is financing-
  insensitive (−36/−41/−46%) unlike the Sharpe margin that died at p0. Any
  metric change is a successor's frozen primary, never a retroactive pass.
- **Omission 1, closed:** the declared SPY context benchmark (§7) was missing
  from the P1 run. Computed 2026-08-21, price-only, same grid, zero researcher
  degrees of freedom: Sharpe +0.576, CAGR +9.0%, MaxDD −56%, 1,076 weeks;
  appended to killtest_results.json. Carries no financing or costs — context
  only; financing-matched it degrades toward the basket row.
- **Omission 2, open:** the declared Russell 1000 robustness arm (§4) was never
  built or run. Recommendation to owner: numbered amendment holding it out,
  un-run, as the successor's single confirmation set — the only untouched US
  universe left. Decision pending.
- Successor sketch put to owner: constraints-first shape (name ≤10%, theme ≤25%
  with 2 slots ⇒ K=10 cap 2 DERIVED, not tuned), 12-1 ranking (H3 +
  signal-by-structure prior), gate kept, correlation-cluster themes as the one
  new mechanism, Calmar-primary dual bar with a Sharpe floor, full {0,+3,+6}
  band retained, bars set against second-half levels (+0.20 era), Russell
  hold-out + walk-forward. Exclusions with priors: no vol knobs
  (risk-overlay-lab), no relative/residual momentum (WS5), no MA re-tuning
  (plateau).
- Live-book decision needed before the Sat 2026-08-22 07:30 SGT window
  (weekday verified by date library).

## 2026-08-21 — P1 RESULT: the kill-test kills it. H1 FAILS.

Honest universe (S&P 500 + Nasdaq-100 point-in-time, delisted included,
price-only, 1,076 weekly rebalances 2006-01 → 2026-08), bars read exactly as
pre-registered on 2026-08-20.

**H1 — rotation beats its own equal-weight basket: FAIL.** The bar required a
≥ +0.10 Sharpe margin at *every* point of the funding-premium band at 1× costs.

| premium | rotation | basket | margin | |
|---|---|---|---|---|
| 0% | +0.485 | +0.411 | **+0.074** | FAIL |
| +3% | +0.368 | +0.263 | +0.105 | pass |
| +6% | +0.251 | +0.115 | +0.136 | pass |

Legs 2 and 3 passed (rotation ≥ basket at 2× costs everywhere; null percentile
**100.0**, strategy +0.251 against a null p90 of −0.046). One failing band point
fails the hypothesis. **The strategy case closes per the frozen kill criterion.**

**Why it fails where it does — the mechanism matters.** The margin rises
monotonically with the funding premium because the rotation is invested less
than the basket (gate plus 10 names out of ~500), so it pays less financing.
With financing free, the advantage nearly vanishes. The edge is a
*cost-avoidance* edge, not a selection edge, and it is therefore fragile to the
assumption it is most sensitive to.

**H2 — the breadth gate: FAIL on the bar, load-bearing on the mechanism.**
Gate on +0.368 vs off +0.343 = +0.025, far below the +0.10 bar. But drawdown is
**−41.3% with the gate against −65.8% without**. A Sharpe-only bar cannot see
that; the pre-registration chose a Sharpe bar and it stands. Filed as
`no-effect` on the tested statistic with the drawdown result recorded, and
consistent with the crypto-breadth record where the gate cut drawdown 38pp.

**H3 — MA200-distance vs 12-1 momentum: FAIL, and backwards.** Plain 12-1
momentum scores **+0.440** against MA200-distance's +0.368. The inherited
ranking statistic is not merely un-superior; it is worse by 0.072. Not adopted —
adopting a better cell after seeing the grid is the exact practice the freeze
exists to prevent — but registered as a candidate primary for any successor.

**M1 — the hindsight premium, measured.** Restricting the identical machinery to
the 69 Binance-listed names present in the panel adds **+0.478 Sharpe to the
rotation** (+0.846 vs +0.368) and **+0.369 to the basket**. That single number
explains the 2026-08-20 correction: the menu, not the rule, was the story.

**Scale, for calibration.** Honest CAGR is +7.9% / +5.4% / +3.0% across the
band, against the hindsight backtest's +37%. Split-half +0.313 / +0.199.

**What survives.** Selection carries real information on an honest universe —
100th percentile against a null whose median is *negative* (−0.172), meaning
random picking among floor-passers loses money after costs. And the gate is a
genuine drawdown truncator. Neither rescues H1.

## 2026-08-20 — Amendment 2 (payload pivot) + levered-filter defect correction

**Pivot.** Owner rejected the shipped EW basket for the live book (operational load;
listing-chase exposure — membership grew 51 → 57 in four days) with zero fills
logged, and separately descoped the WS17 SMH shadow (not-started). New live payload:
**K=10 cluster-cap-2 rotation**, US$5,000, ~US$500/name, ~3.3 orders/week measured.
Seen-data caveat carried permanently (every grid cell observed before the pick; WS6b
precedent). Gate stated before its result: a fresh 1,000-path null at the K=10 shape
must place the strategy ≥ p90 — **first run 99.9th pct; rerun on the corrected
universe below, still 99.9th** (`data/k10_null.json`). The filed verdict (basket
ships) stands in the record; the amendment overrides the live-book choice only.

**Defect correction.** The rotation's first live pick list surfaced TQQQ —
"UltraPro" defeats `\bultra\b`, so TQQQ and TBT had escaped the levered-ETP filter
since Phase 0 (14 → 16 levered after the fix). Panel refreshed to 2026-08-19 and
every affected artefact rerun on the corrected universe. Deltas, old → new, all at
1× costs (orderings unchanged; every verdict robust):

- Rotation K=5 cap=2, band edge: Sharpe +0.94 → **+0.95** (null percentile 97.4 →
  **97.7**, null p90 0.818 → 0.801)
- EW basket, band edge: +0.94 → **+0.93** (2× costs likewise +0.93)
- EW basket equity-only, band edge: +0.94 → **+0.93** (bar-2 margin intact)
- K=10 cap=2 (live payload): band 0/3/6 = +1.20/+1.14/+1.07 → **+1.16/+1.10/+1.04**
  (TQQQ's levered beta removed, four sessions added); gate percentile **99.9 both runs**
- Universe: 141 chartable names (TQQQ, TBT out); equity-only bases 135 → 133

**Bar reads after correction:** bar 1 still FAILS (rotation never +0.10 over the
basket — band 0: 1.04 vs 1.19); ranking still CONFIRMED (97.7th); bar 2 still PASSES
(+0.93 ≥ +0.40, cost-invariant). Nothing filed changes verdict; the ledger row
carries the update note.

## 2026-08-16 — Phase 2 CLOSED: engine run complete, bar reads

Engine and 11-test suite committed before results were read; tests green
including the no-look-ahead fixture with a leak-detection control. Full run in
`data/phase2_results.json` (weekly Friday-close basis, 2018-01 → present,
~449 weeks; all figures NET of fees, the funding band and dividends).

**Bar reads against the frozen pre-registration (formal filing at Phase 3):**

- **Bar 1 — rotation ships: FAILS.** Primary cell (K=5, cap=2) at 1× costs:
  Sharpe +1.03 / +0.98 / +0.94 across the {0,+3,+6}% band against the basket's
  +1.20 / +1.07 / +0.94 — never ahead by the required +0.10, behind at two of
  three band points. **The filed sleeve-C failure mode replicated on this
  menu**: selection concentration doubles CAGR (+46.5% vs +21.0% at the edge)
  and buys it with −57% MaxDD vs −40%, losing on the frozen risk-adjusted
  metric.
- **Bar 2 — the equal-weight basket ships: PASSES with margin.** Basket net
  Sharpe +0.94 at the band edge (bar: ≥ +0.40), positive totals everywhere,
  and essentially invariant to 2×/4× cost stress (+0.94 / +0.94) — its weekly
  turnover is tiny.
- **Null (selection-skill check): 97.4th percentile** (strategy 0.942 vs null
  p90 0.818, 1,000 paths, frozen seed). The momentum RANKING is real against
  random same-shape selection; what fails against the basket is the
  concentrated SHAPE, not the ordering.
- **Split-half (primary, edge): +0.80 / +1.09** — both halves positive.
- **Grid, reported in full (no verdict weight):** k5_capNone +1.07,
  k10_cap2 +1.07, **k10_capNone +1.24** at the edge — wider books do better,
  and the best cell beats the basket. Under the freeze this is an observation
  for a FUTURE pre-registration, not an actionable result: promoting the best
  cell after seeing results is exactly what the primary-cell discipline
  exists to prevent.

**Caveats carried, per pre-registration §6:** every ABSOLUTE level above is
upward-biased by the 2026 menu selection — and the basket, being
"own-the-menu", is the shape that bias flatters most. The bar-2 pass is
therefore a licence for a micro shadow with live funding data, not an expected
+21%/yr. Funding was charged as a band, not data; the live +30%/yr exclusion
rule remains untested by construction.

**Design point raised for Phase 3:** the pre-authorised micro-live shadow was
sized for a K-name book (default K × US$300). The SHIPPING config is a
~140-name basket; equal-weighting it at micro scale is bounded below by
Binance minimum order sizes, so the book cap the owner owes at Phase 3 is a
real sizing decision (order of US$3–7k for ~$20–50 per name), or a shadow on
a defined basket tranche. Flagged, not decided.

## 2026-08-16 — Phase 0 CLOSED: universe integrity

**Result: 160 of 162 bases verified two-source, 2 no-underlying (OPENAI, ANTHROPIC
pre-IPO marks), 0 flagged.** `data/universe_map.json` is the contract. Sources:
48 Binance announcement pages (agent extraction, per-row dates; the row file is
`data/binance_announced_names.txt`) × vendor records with real price series.
Twelve adjudications recorded in `join_universe_map.py` with exchange-code
evidence (KRX/HKEX code agreement, futures front-months for commodities).

**The two-source rule caught real poison.** The mechanical vendor pass had matched
STXX to the Tradr 2X Long STX Daily ETF — a real fund with exactly that ticker —
while Binance's announcement says STXX references **Seagate common** (the STX
symbol being taken by the Stacks crypto perp). Likewise BBX = BlackBerry (BB =
BounceBit) and QNTX = Quantinuum, Nasdaq QNT (QNT = Quant). A name-guess universe
would have carried a 2x ETF where Seagate belongs. Asymmetrically, SNXX really IS
the Tradr 2x SanDisk ETF — the pattern does not generalise either way.

Other identity facts that matter downstream: SPCX is a LISTED equity since
2026-06-12 (SpaceX IPO), so it is short-history, not no-underlying; ZHIPU and
MINIMAX are listed HK AI names; SKHY (Nasdaq ADR) and SKHYNIX (KRX 000660) are
different lines of the same issuer; TENCENT and HK0700 are the SAME share under
different contract conventions (USDT-priced vs quanto — P&L behaviour differs,
only one may enter the universe); PAYP is PayPay Japan, not PayPal; STRC is
Strategy's preferred, not MSTR common.

**Composition of the rotation-eligible set** (verified, unlevered = 146; the 14
levered ETPs are excluded-recommended and duplicate their parents): semis-hardware
47, software-AI 34 — **half the menu is one tech complex** — then consumer 12,
financials 9, commodity 8, crypto-equity 7, industrials/space 8, index-broad 4,
health 4, countries 5, platforms-media 3, energy 2, materials 2, rates 1.
95 of the 146 carry full 2018+ underlying history; the ~51 short-history names
are post-2018/2026 IPOs, handled by the history gate at Phase 1. Design
implication carried to pre-registration: without cluster caps, top-K momentum on
this menu is a semis-concentration engine by construction.

## 2026-08-16 — Phase 0 opened: universe integrity

Scope per kickoff: verified perp-to-underlying map for all 163 seed contracts
(two-source identity), history start and dividend yield per underlying, mechanical
cluster assignment, ex-ante liquidity rule.

Method: (a) background agent extracts each contract's underlying name from
Binance's own listing announcements (authoritative source one); (b) a mechanical
yfinance pass resolves candidate tickers and pulls shortName, sector/industry,
first-trade date and dividend yield (source two); (c) the join yields per-name
status: `verified` (both sources agree), `flagged` (disagreement or single
source — excluded until resolved), `no-underlying` (pre-IPO / synthetic —
outside the momentum engine by rule).

Cluster assignment is mechanical: yfinance sector/industry mapped through a
documented rule table, with explicit overrides for ETFs, leveraged products,
commodities and pre-IPO marks. Overrides live in code, not in judgement calls
scattered through a spreadsheet.

Ex-ante liquidity rule (frozen at Phase 1): rolling 30d Binance ADV ≥ US$5M,
evaluated per rebalance from scanner data; the seed backtest applies the listing
constraint plus the stated selection-bias caveat.
