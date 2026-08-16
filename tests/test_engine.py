"""Engine unit tests — must be green before any Phase 2 result is read.

Covers the pre-registration's required cases: month- and year-boundary date
behaviour on the weekly grid, no-look-ahead at the signal/execution seam, the
cluster cap, the floor and sleeve-breadth gate, under-fill weighting, the
quanto/FX conversion paths, turnover arithmetic and yield normalisation.

Python datetime/pandas: months are 1-indexed.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import engine  # noqa: E402
import prereg  # noqa: E402


def bdays(start, end):
    return pd.bdate_range(start, end)


# --- weekly grid: month and year boundaries (mandatory date cases) -----------

def test_weekly_grid_year_boundary():
    # US sessions across 2018 -> 2019: the last session of the year-end week is
    # Fri 2018-12-28; New Year's Day falls midweek and must not break the grid.
    idx = bdays("2018-12-17", "2019-01-11").drop(pd.Timestamp("2019-01-01"))
    grid = engine.weekly_grid(idx)
    assert pd.Timestamp("2018-12-28") in grid
    assert pd.Timestamp("2019-01-04") in grid
    # Exactly one grid date per ISO week present in the index.
    assert len(grid) == len(set(pd.DatetimeIndex(grid).to_period("W")))


def test_weekly_grid_month_boundary_and_friday_holiday():
    # A Friday holiday (Good Friday 2018-03-30): the week must anchor on
    # Thursday 2018-03-29, the true last session, spanning the month boundary.
    idx = bdays("2018-03-19", "2018-04-13").drop(pd.Timestamp("2018-03-30"))
    grid = engine.weekly_grid(idx)
    assert pd.Timestamp("2018-03-29") in grid
    assert pd.Timestamp("2018-03-30") not in grid
    assert pd.Timestamp("2018-04-06") in grid


# --- selection: floor, gate, cap, determinism, under-fill --------------------

def _sig(vals):
    return pd.Series(vals)


def test_floor_and_gate():
    sig = _sig({"A": 0.20, "B": 0.10, "C": 0.01, "D": -0.05})
    elig = pd.Series(True, index=sig.index)
    # 2 of 4 above the +5% floor = 50% breadth: passes the 30% gate.
    picks, diag = engine.select_names(sig, elig, {}, 2, None, 0.05, 0.30)
    assert picks == ["A", "B"]
    # Only 1 of 4 above floor = 25% breadth: gated to cash.
    sig2 = _sig({"A": 0.20, "B": 0.02, "C": 0.01, "D": -0.05})
    picks2, diag2 = engine.select_names(sig2, elig, {}, 2, None, 0.05, 0.30)
    assert picks2 is None and diag2["breadth"] == 0.25


def test_cluster_cap_and_underfill():
    sig = _sig({"A": 0.50, "B": 0.40, "C": 0.30, "D": 0.20, "E": 0.10})
    elig = pd.Series(True, index=sig.index)
    clusters = {"A": "semi", "B": "semi", "C": "semi", "D": "semi", "E": "soft"}
    picks, _ = engine.select_names(sig, elig, clusters, 4, 2, 0.05, 0.30)
    # Cap 2 per cluster: A, B (semi full), then E; C and D skipped -> under-fill 3 of 4.
    assert picks == ["A", "B", "E"]


def test_selection_determinism_on_ties():
    sig = _sig({"B": 0.30, "A": 0.30, "C": 0.10})
    elig = pd.Series(True, index=sig.index)
    picks, _ = engine.select_names(sig, elig, {}, 2, None, 0.05, 0.30)
    assert picks == ["A", "B"]  # tie broken alphabetically


def test_ineligible_names_never_picked():
    sig = _sig({"A": 0.50, "B": 0.40})
    elig = pd.Series({"A": False, "B": True})
    picks, diag = engine.select_names(sig, elig, {}, 1, None, 0.05, 0.30)
    assert picks == ["B"] and diag["n_eligible"] == 1


# --- no-look-ahead at the signal/execution seam ------------------------------

def test_no_lookahead_friday_jump_cannot_affect_friday_selection():
    # Both names trend up (so both clear the floor); A trends faster and ranks
    # first on Thursday. On the final Friday, B doubles. If the Friday decision
    # leaked Friday data, B would outrank A; reading Thursday's signal, it must
    # not.
    idx = bdays("2024-01-01", "2025-03-01")
    n = len(idx)
    px = pd.DataFrame({
        "A": 100.0 * (1.0 + 0.0010) ** np.arange(n),
        "B": 100.0 * (1.0 + 0.0009) ** np.arange(n),
    }, index=idx)
    friday = engine.weekly_grid(idx)[-1]
    px.loc[friday, "B"] = px.loc[friday, "B"] * 2.0
    ma = px.rolling(200, min_periods=200).mean()
    signal = px / ma - 1.0
    pos = idx.get_loc(friday)
    sd = idx[pos - prereg.SIGNAL_DAY_LAG]
    elig = pd.Series(True, index=["A", "B"])
    picks, _ = engine.select_names(signal.loc[sd], elig, {}, 1, None, 0.05, 0.30)
    assert picks == ["A"]  # Thursday ranking stands; B's Friday jump invisible
    # Control: reading FRIDAY's signal (the leak) would pick B — proving the
    # fixture can detect the defect it guards against.
    picks_leak, _ = engine.select_names(signal.loc[friday], elig, {}, 1, None, 0.05, 0.30)
    assert picks_leak == ["B"]


# --- conversions, turnover, yields ------------------------------------------

def test_quanto_keeps_local_and_kr_converts():
    idx = bdays("2024-01-01", "2024-01-31")
    local = pd.Series(1000.0, index=idx)
    fx = pd.Series(1300.0, index=idx)  # USD/KRW
    quanto = engine.to_usd("HK1810", local, "HK", fx, fx)
    assert (quanto == local).all()
    kr = engine.to_usd("SAMSUNG", local, "KR", fx, fx)
    assert np.allclose(kr.values, 1000.0 / 1300.0)


def test_turnover_counts_both_sides():
    prev = {"A": 0.2, "B": 0.2}
    new = {"B": 0.2, "C": 0.2}
    # Sell A (0.2) + buy C (0.2) = 0.4 total |dw|.
    assert abs(engine.turnover(prev, new) - 0.4) < 1e-12
    assert engine.turnover({}, {"A": 0.2}) == 0.2


def test_yield_normalisation_units():
    assert engine.normalise_yield(None) == 0.0
    assert abs(engine.normalise_yield(0.52) - 0.0052) < 1e-9   # percent form
    assert abs(engine.normalise_yield(0.012) - 0.012) < 1e-9   # fraction form
    assert engine.normalise_yield(45.0) <= 0.10                 # capped


def test_stats_from_weekly_shapes():
    rets = pd.Series([0.01] * 52)
    s = engine.stats_from_weekly(rets)
    assert s["n_weeks"] == 52 and s["max_dd"] == 0.0
    # stats round to 4dp, so the tolerance must sit above that quantum.
    assert abs(s["total_return"] - (1.01 ** 52 - 1)) < 5e-5
