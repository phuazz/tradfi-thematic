# Basket shadow close-out — operations review

**Filed:** Wednesday 2026-10-14 · **Context:** Personal · **Due:** Sunday 2026-09-13
(protocol §5 and Amendment 5) · **Type:** operations close-out; no hypothesis is tested
and no register record is written · **Protocol:** `reviews/2026-08-16_basket-shadow-protocol.md`

## Outcome

The shadow closes **NOT EXERCISED**. Zero fills were logged between activation
(2026-08-16) and close-out, so the three frozen triggers read vacuously: none breached,
none evaluable. No sizing proposal follows (§5 requires a pass on exercised triggers),
and nothing is filed against a register record. The strategy case was already closed
permanently by the KT-2 verdict (`reviews/2026-08-21_kt2_verdict.md`, protocol
Amendment 5); this memo closes the operations record only.

## Record

| Date | Event |
|---|---|
| 2026-08-16 | Activated: Option A, US$5,000 cap at 1×. Amendment 1 (equity-only) the same day, before any fill. |
| 2026-08-20 | Amendment 2: live payload pivots to the K=10 cluster-cap-2 rotation. Amendment 3: live signal aligned to the tested session. Both before any fill. |
| 2026-08-21 | Amendment 4: book PAUSED on the kill-test H1 FAIL; establishment buys never executed. Amendment 5 the same day: closure made permanent after KT-2 failed S1. |
| 2026-08-21 → 2026-10-14 | Evaluator ran in paused mode, logging and rebuilding the page each morning. |
| 2026-10-14 | Close-out filed; evaluator disarmed (below). |

Evaluator log, `data/basket_shadow_log.json`, read at close-out:

- 67 rows, all `type: ops`, all `event: OK`. No FAIL or MISSED event was ever written.
- 13 rows in establishment mode (2026-08-16 to 2026-08-20 SGT). Each carried an order
  list of 8 to 30 orders; none was executed.
- 54 rows in paused mode, from 2026-08-21 07:14 SGT to 2026-10-14 07:15 SGT.
- Zero `execution` rows. Names held: 0 at every row. Book value: US$0 throughout.
- SGT calendar days with no row: 2026-09-10 (Thursday) and 2026-09-16 (Wednesday).
  Neither is a Saturday maintenance window; every Saturday in the period carries a row.
  Weekdays verified with Python `datetime`.

## Trigger read (protocol §4)

| Trigger | Bar | Read |
|---|---|---|
| FAIL-EXECUTION | median fill cost vs prior close > 15bp over ≥ 20 fills | 0 fills; not evaluable |
| FAIL-BAND | book funding drag > +6%/yr over any rolling 4 weeks | no positions, no funding paid; not evaluable |
| FAIL-OPS | two consecutive missed Saturday windows, or a margin call at 1× | no window missed (no orders were due while paused); no positions, so no margin call possible |

The live evidence the shadow was built to produce (realised funding across a broad
holding, fill cost at micro clips, weekly maintenance load) was **not generated**. The
backtest's funding band remains an assumption, never data, for this venue.

The payload re-decision added to the agenda by Amendment 3 is superseded, as Amendment 4
already recorded: the construction family is closed, so there is no payload to re-decide.

The WS17 xyz:SMH shadow, which shared this close-out date, was descoped not-started on
2026-08-20 with its task disabled and its fleet row removed at that time
(`STUDIES_LEDGER.md`, breadth-thrust-etf row of 2026-08-16). Nothing further is owed on it.

## Actions taken at close-out

1. Scheduled task `TradfiThematic-BasketShadow` **disabled** (not deleted). Last run
   2026-10-14 07:15 SGT. Re-arming it is not a route back to this book: Amendment 5
   requires any future live idea on this venue to start from a new pre-registration.
2. Fleet-watch row "tradfi rotation shadow evaluator" removed from
   `C:\dev\scripts\fleet_watch.json`.
3. Dashboard: the leading banner now reads closed out, and the close-out card shows the
   filing date in place of a countdown. Panels the evaluator alone maintained (live
   signal state, order list, funding block, per-name charts, payload detail, data health)
   are frozen as at the evaluator's last run, 2026-10-14 (signal session 2026-10-08), and
   the page says so.
4. Perp-Funding-Scanner shadow-book panel: the countdown (which had reached −31 days)
   replaced by the close-out date.
5. `README.md` status updated; protocol carries a pointer to this memo.

## What continues

The FV-1 paper track (`reviews/2026-08-21_rotation-forward-validation_preregistration.md`)
is a separate task (`TradfiThematic-FV1Track`, Saturday 08:30 SGT) with its own fleet row,
and is unaffected. It is now the only job that rebuilds and publishes the dashboard, so
the page refreshes weekly rather than daily.

## Why this was filed 31 days late

The decommissioning reminder relied on the fleet-watch row going stale. A task that keeps
running keeps its heartbeat fresh, so the row could never breach; the only prompt left
was the `NEXT.md` item. A temporary row needs an expiry date that the watcher itself
checks, not a note in prose. Proposed, not built: an optional `expires` field in
`fleet_watch.json` that raises a breach once the date has passed while the row is still
present.

## Not done in this sitting

`NEXT.md` attached a first spread-persistence read from
`Perp-Funding-Scanner/data/hl_funding_daily.json` to the same sitting. It is a research
read, not an operations step, and is carried forward in `NEXT.md`.
