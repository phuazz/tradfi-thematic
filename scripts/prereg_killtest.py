"""FROZEN constants for the Norgate kill-test — committed at sign-off
(2026-08-20) with reviews/2026-08-20_norgate-killtest_preregistration.md,
before any strategy result was computed. The engine imports these and MUST NOT
redefine them; any change is a numbered amendment in that document, committed
before the affected result exists.
"""

# --- universe ---------------------------------------------------------------
PRIMARY_INDICES = ("S&P 500", "Nasdaq 100")          # point-in-time membership
PRIMARY_WATCHLISTS = ("S&P 500 Current & Past", "Nasdaq 100 Current & Past")
ROBUSTNESS_WATCHLIST = "Russell 1000 Current & Past"  # arm only, not verdict-bearing
ROBUSTNESS_TOP_N = 250                                # by 60d median dollar volume
UNIVERSE_START = "2005-01-01"                         # membership series begin
BACKTEST_START = "2006-01-01"                         # after warm-up
MIN_HISTORY_DAYS = 252
FFILL_LIMIT_SESSIONS = 3

# --- signal and construction (inherited, not re-tuned) ----------------------
MA_WINDOW = 200
ENTRY_FLOOR = 0.05
SLEEVE_BREADTH_GATE = 0.30
SIGNAL_DAY_LAG = 1                 # decide on one close, fill at the next
K_GRID = (5, 10, 20)
SECTOR_CAP_GRID = (2, None)
PRIMARY_CELL = {"k": 10, "sector_cap": 2}

# --- costs ------------------------------------------------------------------
FEE_RT_BPS = 10.0
COST_STRESS_MULTS = (1.0, 2.0, 4.0)
# funding = 3-month T-bill + premium, charged on invested capital only.
# Calibration 2026-08-20: realised funding across 65 live Binance TradFi perps
# had a median of +6.8%/yr against a 3.7% T-bill -> ~+3%/yr demand premium.
FUNDING_PREMIUM_BAND = (0.0, 0.03, 0.06)
RATE_SERIES = "^IRX"               # 13-week T-bill, quoted in PERCENT
CASH_EARNS_RATE = True             # gate weeks earn the T-bill, not zero
# Dividends are NOT charged: the panel uses split-adjusted (price-only) prices,
# which already exclude them. See implementation note 1 in the pre-registration.
CHARGE_DIVIDENDS = False

# --- comparators, null, bars -------------------------------------------------
NULL_PATHS = 1000
NULL_SEED = 20260820
SPLIT_HALF_BOUNDARY = "2016-01-01"
BENCHMARK = "SPY"                  # context only, no verdict weight

SELECTION_VS_BASKET_MARGIN = 0.10  # H1: across the whole premium band, 1x costs
NULL_PERCENTILE_MIN = 90.0         # H1
GATE_MARGIN = 0.10                 # H2, at the band centre
SIGNAL_FORM_MARGIN = 0.10          # H3, at the band centre
