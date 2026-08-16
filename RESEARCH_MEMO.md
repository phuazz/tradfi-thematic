# RESEARCH_MEMO — tradfi-thematic

Running memo. Newest entries at the top. Verdicts and filed records go to the vault
ledger; this file is the working trail.

---

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
