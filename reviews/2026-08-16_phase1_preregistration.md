# Phase 1 — pre-registration (FROZEN at commit; amendments must be numbered and disclosed)

**Date:** 2026-08-16 · **Context:** Personal · Landed ahead of the 2026-08-21 due
date. This document and `scripts/prereg.py` freeze the design; the Phase 2 engine
imports the constants and may not redefine them. Nothing below was computed on
strategy results — no backtest of this design existed when this was committed.

## 1. Universe (from the Phase 0 verified map — `data/universe_map.json`)

Rotation-eligible = verified ∧ unlevered ∧ has underlying series, minus explicit
same-issuer/duplicate drops, frozen here:

- **Drop SKHY** (Nasdaq ADR) — same issuer as SKHYNIX (KRX line kept: longer
  history, more liquid perp).
- **Drop HK0700** (quanto Tencent) — same share as TENCENT (USDT-priced kept).
- **Drop STRC** (Strategy preferred) — same issuer as MSTR common; a rate-like
  instrument, not an equity momentum candidate.

That yields **143 names**. The 14 levered ETPs and 2 pre-IPO marks are out by
Phase 0 rule. **HK1810 (Xiaomi) is quanto with no USDT-priced twin: it stays, and
its return is modelled as the LOCAL-currency return** (quanto P&L carries no FX);
all other KR/HK names are FX-converted to USD (see §4).

**Ex-ante membership at each rebalance date t (backtest):** a name is eligible
when its underlying has ≥252 trading days of history by t. Short-history names
enter as they mature. **Live additionally requires:** perp listed on Binance and
30-day ADV ≥ US$5M (the scanner's own liquidity bar), evaluated per rebalance.

**Stated bias, carried beside every headline:** the menu was selected by Binance
in 2025–26 — names that thrived got listed. Every ABSOLUTE level in this backtest
is biased upward by construction, and no methodology here removes that. The
SELECTION question (top-K vs equal-weight vs random-selection null) is asked
within the same menu, so it nets the bias out; the absolute-level question does
not. The point-in-time listing log bounds the bias prospectively from 2026-08-16.

## 2. Signal and construction (sleeve-C conventions, not re-tuned)

- **Signal:** distance of underlying adjusted close above its own 200-day MA,
  `P/MA200 − 1`, per name. Entry floor **+5%** (the filed sleeve-C floor).
- **Sleeve-breadth gate:** if fewer than **30%** of the eligible universe clears
  the floor, the whole sleeve goes to cash for that week (cash earns zero). Both
  numbers are the deployed sleeve-C values, inherited, not fitted.
- **Cadence:** weekly. Signal computed on the **Thursday US close**, executed at
  the **Friday US close** (the bte `get_loc(rd)−1` convention; no look-ahead by
  construction, to be pinned by test in Phase 2). Non-US closes as of the signal
  instant: last available close, forward-filled ≤3 sessions, else the name is
  ineligible that week.
- **Selection grid (declared in full, PRIMARY cell named now, no cherry-pick):**
  K ∈ {5, 10} × cluster-cap ∈ {2, none}; equal weight within the book.
  **PRIMARY: K=5, cap=2** (cap = max names per Phase 0 cluster inside the book —
  the semis-concentration mitigation; semis-hardware + software-AI are half the
  menu by count). All four cells are reported; the verdict reads ONLY the
  primary. Ties in rank broken by higher signal, then alphabetical (determinism).
- **Funding-aware term (live-only risk rule, adopted by design, NOT backtested):**
  at each live rebalance, any name whose trailing 30-day annualised funding
  exceeds **+30%/yr** (the scanner's deployed stretched-long threshold — an
  existing production constant, no new parameter) is excluded from selection that
  week. Historical funding does not exist for these contracts, so this rule
  CANNOT be honestly backtested; in the backtest its place is taken by the
  funding cost band (§3). This is insurance in the v3.2 single-name-cap sense —
  a crowding guard, not a claimed edge.

## 3. Cost model (frozen)

- **Fees + slippage:** 10bp round trip per unit of turnover (5bp per side on
  |Δweight| weekly, entries and exits included). Stress arms at **2× and 4×**
  (WS13 convention).
- **Funding band:** {0, +3, +6} %/yr charged on the invested fraction, in-market
  days only (WS17 H2b machinery). The verdict must hold across the ENTIRE band.
- **Dividends forgone:** per-name trailing yield (Phase 0 map) charged on
  holdings — perps are price-only; signal series are total-return-adjusted, so
  the subtraction restores perp economics to first order (stated approximation).
- Cash earns zero. No leverage anywhere; weights sum to ≤1.

## 4. Data basis

Underlying adjusted daily closes (yfinance), 2018-01-01 → present. KR and HK
names: prices converted to USD at the daily FX close (`KRW=X`, `HKD=X`,
forward-filled) for RETURN computation; the MA-distance signal is computed on
local-currency prices (scale-invariant). HK1810 exempted from FX conversion
(quanto, §1). Commodity names use front-month continuous futures (Phase 0 map).

## 5. Comparators, null, and success bars (frozen)

- **PRIMARY comparison: the equal-weight basket** — all eligible names, weekly
  re-equal-weighted, identical costs and band. (The filed sleeve-C prior:
  selection lost to its own basket. It must not happen silently here.)
- **Cost-matched random-selection null:** 1,000 paths; at each rebalance, K
  names drawn uniformly from the same eligible set (same cap applied), same
  costs, same band. The strategy's placement in that distribution measures
  whether SELECTION is real.
- **Context benchmark:** SPY total return (no verdict weight).
- **Split-half robustness report:** 2018–2021 vs 2022–present (report only).

**Bars (all at the +6%/yr band edge unless stated):**

1. **Rotation ships** if primary-cell net Sharpe exceeds the EW basket's by
   ≥ **+0.10** at 1× costs across the whole band, AND is ≥ the basket at 2×
   costs, AND sits at or above the **90th percentile** of the random-selection
   null. (+0.10 is the saa-trend-overlay precedent bar.)
2. **Otherwise the EW basket ships** (owner decision, 2026-08-16) if the basket's
   own net Sharpe ≥ **+0.40** across the band with positive net total return
   (the WS17 bar, reused).
3. **Neither clears → nothing ships**; the workstream files a rejection.
4. **Micro-live pre-authorisation** (owner decision, 2026-08-16) attaches to
   whichever configuration ships under 1 or 2, only if its bar held at 2× costs;
   the shadow inherits the WS17 guard set unchanged, book cap to be confirmed by
   the owner at Phase 3 (default K × US$300).

## 6. The ways this could be silently wrong (stated before any code)

1. **Menu survivorship** (§1): absolute levels biased up by Binance's 2026
   selection; defended for the selection question by the within-menu null and
   basket, undefended for the absolute question — stated beside every headline.
2. **Funding regime-correlation:** the band charges funding independently of
   positions, but live funding concentrates exactly in the names momentum buys
   (+30–46%/yr measured on hot names, 2026-08-15/16). Defences: the +6% band
   edge carries the verdict; the live exclusion rule (§2); the shadow measures
   realised funding before any sizing grows.
3. **Cross-calendar and currency seams:** KR/HK closes precede the US signal
   instant by hours (stale-close drift), FX conversion adds a second series with
   its own gaps, and the quanto exemption is easy to mis-implement. Defences:
   ≤3-session forward-fill rule with ineligibility beyond it; month- and
   year-boundary date tests plus a no-look-ahead test required green before any
   result is read (Phase 2); HK1810 handled by an explicit code path with its
   own test.
4. **TR-vs-price approximation:** dividend subtraction on TR series only
   approximates price-only perp economics; the error is bounded by yield levels
   (menu-typical 0–2%/yr) and is common to strategy, basket and null.

## 7. Deliverable boundary

Phase 2 produces: the engine + tests, the four grid cells, the basket, the null,
the split-half report, all at three cost multiples × three band points. Phase 3
reads the bars EXACTLY as written above and files the verdict with the vault
ledger row for the workstream (kickoff → pre-registration → verdict in one row,
WS17-style). Any deviation from this document is a numbered amendment committed
before the affected result is computed.
