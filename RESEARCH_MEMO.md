# RESEARCH_MEMO — tradfi-thematic

Running memo. Newest entries at the top. Verdicts and filed records go to the vault
ledger; this file is the working trail.

---

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
