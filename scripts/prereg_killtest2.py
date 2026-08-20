"""FROZEN constants for KT-2, the tail-bounded successor — committed at
sign-off (2026-08-21) with reviews/2026-08-21_tail-bounded-successor_preregistration.md.
The engine imports these and MUST NOT redefine them; any change is a numbered
amendment in that document, committed before the affected result exists.

The shape is DERIVED from risk policy, not tuned: single name <= 10% => K = 10;
theme <= 25% with two slots => cap = 2 (2/10 = 20%). No grid exists in KT-2.
"""

# --- confirmation universe (held out by KT-1 Amendment 1) --------------------
CONFIRM_WATCHLIST = "Russell 1000 Current & Past"
TOP_N = 250                     # by trailing median dollar volume
DV_WINDOW = 60                  # sessions, strictly BEFORE the signal date
DV_MIN_OBS = 30                 # min non-missing sessions in the window to rank
UNIVERSE_START = "2005-01-01"
BACKTEST_START = "2006-01-01"
MIN_HISTORY_DAYS = 252
FFILL_LIMIT_SESSIONS = 3

# --- construction (derived / inherited, not tuned) ---------------------------
K = 10
THEME_CAP = 2
MA_WINDOW = 200                 # eligibility floor + gate only; NOT the ranking
ENTRY_FLOOR = 0.05
SLEEVE_BREADTH_GATE = 0.30
SIGNAL_DAY_LAG = 1
MOM_SHORT = 21                  # 12-1 momentum: P(t-21)/P(t-252) - 1, sessions
MOM_LONG = 252

# --- theme definition (S2), frozen spec --------------------------------------
CORR_WINDOW_WEEKS = 104
CORR_MIN_WEEKS = 52             # shorter histories form singletons
CLUSTER_CUT = 0.5               # distance = 1 - rho; average linkage
CLUSTER_REFORM_MONTHS = (1, 4, 7, 10)   # first rebalance of these months
DEGEN_LARGEST_FRAC = 0.40       # largest cluster > 40% of eligible names
DEGEN_SINGLETON_FRAC = 0.60     # > 60% of names are singletons
# Either degeneracy trips => the study falls back to the GICS cap throughout.

# --- costs and funding (inherited unchanged from KT-1) -----------------------
FEE_RT_BPS = 10.0
COST_STRESS_MULTS = (1.0, 2.0, 4.0)
FUNDING_PREMIUM_BAND = (0.0, 0.03, 0.06)
RATE_SERIES = "^IRX"            # quoted in PERCENT; converted once at load
CASH_EARNS_RATE = True
CHARGE_DIVIDENDS = False        # prices are CAPITAL-adjusted (dividend-free)

# --- bars (section 6 of the pre-registration; read once, on the single run) --
CALMAR_MARGIN = 0.05            # (a) at every premium, 1x costs
DD_RATIO_MAX = 0.75             # (c) rotation MaxDD <= 0.75 x basket MaxDD
S2_SHARPE_TOL = 0.03            # cluster cap within this of the best arm
NULL_PATHS = 1000
NULL_SEED = 20260821
NULL_PCTL_MIN = 90.0            # Calmar percentile at the band edge
SPLIT_HALF_BOUNDARY = "2016-01-01"
BENCHMARK = "SPY"               # context only, no verdict weight
