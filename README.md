# tradfi-thematic

Thematic rotation over the **full Binance TradFi perpetual menu** (163 contracts at
seed, 2026-08-16): long-only cross-sectional momentum computed on the UNDERLYINGS'
history, traded via the perps, with a funding-aware term frozen at pre-registration.
**Personal book. Research-grade — two micro shadow experiments live, nothing sized.**
Public on owner instruction (2026-08-17); previously local-only. **Live dashboard:**
[phuazz.github.io/tradfi-thematic](https://phuazz.github.io/tradfi-thematic/) —
names-first study and implementation surface, rebuilt each morning by the evaluator.
Not investment advice; the shadow books are micro-sized verification experiments and
every backtest figure carries the menu-survivorship caveat stated below.

Commissioned 2026-08-16; kickoff and interview record: `C:\dev\KICKOFF_tradfi-thematic.md`
(vault-docs). Owner-settled inputs: universe = ALL available TradFi perps; the
equal-weight basket ships if top-K selection fails its gate; a micro-live shadow is
pre-authorised if the pre-registered gates clear (WS17 guard set inherited).

## Status

- **Phase 0 — universe integrity (2026-08-16 → …): IN PROGRESS.** Deliverable: a
  verified perp-to-underlying map for all 163 contracts (two-source identity: the
  Binance listing announcement name × the underlying vendor record), history start,
  dividend yield, mechanical cluster assignment, ex-ante liquidity rule.
- Phase 1 — pre-registration frozen by 2026-08-21.
- Phase 2 — backtest (week of 2026-08-24): underlying history 2018+, point-in-time
  universe rules, equal-weight basket as PRIMARY comparison, cost-matched null,
  funding band {0,+3,+6}%/yr, 2×/4× cost stress.
- Phase 3 — verdict + conditional shadow activation (week of 2026-08-31).
- Phase 4 — combined close-out with the WS17 SMH shadow, by 2026-09-13.

## Data dependencies

- `C:\dev\Perp-Funding-Scanner\data\tradfi_universe_log.json` — point-in-time
  listing roster, appended per scan since 2026-08-16 (survivorship guard).
- `C:\dev\Perp-Funding-Scanner\data\scan.json` + `funding_history.json` — per-name
  funding and liquidity, twice daily.
- Underlying prices: yfinance (identity-verified tickers only).

## Honest limits, stated upfront

- The menu is Binance's choice — hindsight-selected by construction. The backtest
  on underlying history therefore carries an upward selection bias no methodology
  removes; it is stated beside every headline, and the point-in-time log bounds it
  prospectively from 2026-08-16.
- Perp funding history barely exists (contracts listed Dec 2025 – Jul 2026); all
  historical funding drag is an assumption band, never data.
- Pre-IPO and synthetic contracts have no underlying history and sit outside the
  momentum engine at launch.
