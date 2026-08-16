# CLAUDE.md — tradfi-thematic

Layered on top of `C:\dev\CLAUDE.md`; this file wins where they conflict. Context:
**Personal**.

## Rules that bind every phase

- **Signal on the underlying, trade the perp.** No signal is ever computed on perp
  price history (too short); no trade is ever assumed on an instrument that was not
  listed and liquid at that date under the ex-ante rules.
- **The universe is point-in-time from 2026-08-16 onward** via the scanner's
  `tradfi_universe_log.json`. Backtests before that date use the frozen seed menu
  and MUST carry the stated selection-bias caveat beside every headline number.
- **No name enters the universe without two-source identity verification** (the
  Binance announcement name × the vendor record). A NOT-FOUND stays out — a guess
  is poison. The verified map is `data/universe_map.json`; treat it as a contract.
- **Frozen means frozen.** The funding-term form, K/cap grid, cost model, success
  bars and IS/OOS split are set in the Phase 1 pre-registration commit and never
  tuned afterwards. Any change is a numbered, disclosed amendment.
- **The equal-weight basket is the PRIMARY comparison** (the filed sleeve-C prior:
  selection lost to its own basket at realistic costs). Selection must beat it net
  of everything or the basket ships.
- **Costs always:** perp fees, funding band {0,+3,+6}%/yr on in-trade days,
  per-name forgone dividends, 2×/4× stress per the WS13 convention.
- **No unattended job without a guard layer and a fleet_watch row.** Any evaluator
  follows the WS17 pattern: logs and alerts only, never places orders.
- Dates via date libraries only; two date edge-case tests minimum for any date
  logic; JavaScript months are 0-indexed, Python months are 1-indexed — state which
  applies in every file that touches dates.
