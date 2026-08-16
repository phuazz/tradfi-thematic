"""FROZEN pre-registration constants — committed 2026-08-16 with the Phase 1
document (reviews/2026-08-16_phase1_preregistration.md), before any backtest of
this design existed. The Phase 2 engine imports these and MUST NOT redefine
them; any change is a numbered amendment in the pre-registration document,
committed before the affected result is computed.
"""

# --- Universe (Phase 0 map is the identity contract) ------------------------
UNIVERSE_MAP = "data/universe_map.json"
# Same-issuer / duplicate-line drops, decided and justified in prereg section 1.
EXPLICIT_DROPS = {"SKHY", "HK0700", "STRC"}
# Quanto contracts: P&L is the LOCAL-currency return (no FX conversion).
QUANTO_BASES = {"HK1810"}
MIN_HISTORY_DAYS = 252          # ex-ante membership: underlying history by t
LIVE_MIN_ADV_USD_M = 5.0        # live-only additional gate (scanner bar)

# --- Signal and construction (sleeve-C conventions, inherited) ---------------
MA_WINDOW = 200                 # P/MA200 - 1 on underlying adjusted closes
ENTRY_FLOOR = 0.05              # +5% above MA to qualify
SLEEVE_BREADTH_GATE = 0.30      # <30% of universe above floor -> all cash
SIGNAL_DAY_LAG = 1              # signal on Thursday close, execute Friday close
FFILL_LIMIT_SESSIONS = 3        # non-US stale-close tolerance, else ineligible

# Selection grid — declared in full; verdict reads ONLY the primary cell.
K_GRID = (5, 10)
CLUSTER_CAP_GRID = (2, None)    # max names per Phase 0 cluster in the book
PRIMARY_CELL = {"k": 5, "cluster_cap": 2}

# Funding-aware term: LIVE-ONLY exclusion (cannot be backtested — no history).
LIVE_FUNDING_EXCLUDE_ANN = 30.0  # %/yr trailing 30d; scanner's deployed line

# --- Cost model --------------------------------------------------------------
FEE_RT_BPS = 10.0               # per unit turnover, round trip (5bp/side)
COST_STRESS_MULTS = (1.0, 2.0, 4.0)
FUNDING_BAND_ANN = (0.0, 0.03, 0.06)   # charged on invested fraction, in-market
CASH_YIELD = 0.0

# --- Backtest window and robustness ------------------------------------------
BACKTEST_START = "2018-01-01"
SPLIT_HALF_BOUNDARY = "2022-01-01"     # report-only split
NULL_PATHS = 1000
NULL_SEED = 20260816

# --- Success bars (verdict reads these EXACTLY; band edge unless stated) ------
ROTATION_VS_BASKET_SHARPE_MARGIN = 0.10   # at 1x costs, across whole band
ROTATION_NULL_PERCENTILE_MIN = 90.0
BASKET_ABS_SHARPE_MIN = 0.40              # EW-basket shipping bar (WS17 bar)
