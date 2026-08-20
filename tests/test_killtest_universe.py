"""P0 guards for the Norgate kill-test — the four failure modes named in
section 8 of the pre-registration, pinned before any strategy result exists.

These are not unit tests of convenience; each one is a way the study could be
silently wrong, written so that the defect would turn them red.

Run: pytest tests/test_killtest_universe.py -q
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import killtest_common as KC  # noqa: E402
import prereg_killtest as P  # noqa: E402

DATA = ROOT / "data"
pytestmark = pytest.mark.skipif(not (DATA / "killtest_prices.parquet").exists(),
                                reason="P0 universe not built")


@pytest.fixture(scope="module")
def panel():
    px = pd.read_parquet(DATA / "killtest_prices.parquet")
    mem = pd.read_parquet(DATA / "killtest_members.parquet")
    meta = json.loads((DATA / "killtest_meta.json").read_text(encoding="utf-8"))
    rates = pd.read_parquet(DATA / "killtest_rates.parquet")["rf"]
    return px, mem, meta, rates


# --- GUARD 1: membership is point-in-time, not a current snapshot -----------

def test_membership_shows_real_index_turnover(panel):
    """Under a current-snapshot read, every historical date would contain only
    today's members and this count would be zero. It must not be."""
    _, mem, _, _ = panel
    early = mem.loc[:"2006-06-01"].iloc[-1]
    late = mem.iloc[-1]
    left_the_index = int((early & ~late).sum())
    joined_since = int((late & ~early).sum())
    assert left_the_index > 100, f"only {left_the_index} names left the index since 2006 — snapshot leak?"
    assert joined_since > 100, f"only {joined_since} names joined since 2006 — snapshot leak?"


def test_known_deletion_is_member_before_and_not_after(panel):
    """Altaba (ex-Yahoo!) sat in the S&P 500 and was removed in 2017. Pinning a
    real transition catches a membership read that returns 'always' or 'never'."""
    _, mem, _, _ = panel
    if "AABA-201910" not in mem.columns:
        pytest.skip("AABA-201910 not in this panel")
    col = mem["AABA-201910"]
    assert bool(col.loc[:"2010-01-04"].iloc[-1]) is True, "should be a member in 2010"
    assert bool(col.iloc[-1]) is False, "must not be a member today — it no longer exists"


def test_membership_count_is_stationary(panel):
    """A survivorship-contaminated panel grows toward the present. Index size
    should sit in a band instead."""
    _, mem, _, _ = panel
    per_day = mem.sum(axis=1)
    assert 450 <= per_day.min() <= per_day.max() <= 650, (per_day.min(), per_day.max())
    first, last = int(per_day.iloc[0]), int(per_day.iloc[-1])
    assert abs(first - last) < 100, f"membership drifted {first} -> {last}"


# --- GUARD 2: dead names are present, with real endings --------------------

def test_delisted_names_are_carried(panel):
    _, _, meta, _ = panel
    m = meta["meta"]
    dead = [s for s, v in m.items() if v["delisted"]]
    in_window = [s for s in dead if m[s]["last_bar"] >= P.BACKTEST_START]
    assert len(dead) > 300, f"only {len(dead)} delisted symbols — archive not loaded?"
    assert len(in_window) > 300, f"only {len(in_window)} delisted names die inside the window"


def test_missing_symbols_are_only_pre_window_delistings(panel):
    """Every symbol dropped at load must be one that died before the backtest
    starts. A 2006+ delisting going missing would be a survivorship hole."""
    _, _, meta, _ = panel
    for sym, reason in meta.get("unavailable", []):
        tail = sym.split("-")[-1]
        assert tail.isdigit() and int(tail[:4]) < 2005, f"{sym} dropped for {reason}"


def test_dead_names_stop_and_do_not_ffill_forever(panel):
    """A delisted name must have NaN after its final bar, so the engine cannot
    hold a corpse at a frozen price."""
    px, _, meta, _ = panel
    m = meta["meta"]
    dead = [s for s, v in m.items()
            if v["delisted"] and P.BACKTEST_START <= v["last_bar"] < "2020-01-01" and s in px.columns]
    assert dead, "no delisted names inside the window to check"
    for s in dead[:15]:
        last = pd.Timestamp(m[s]["last_bar"])
        after = px[s].loc[last + pd.Timedelta(days=5):]
        assert after.notna().sum() == 0, f"{s} still has prices after {last.date()}"


# --- GUARD 3: rate units --------------------------------------------------

def test_rate_conversion_units():
    assert KC.rate_to_fraction(3.7) == pytest.approx(0.037)
    assert KC.rate_to_fraction(0.0) == 0.0


def test_stored_rates_are_fractions_not_percents(panel):
    _, _, _, rates = panel
    assert 0.0 <= rates.max() <= 0.12, f"rate max {rates.max()} looks like percent, not fraction"
    assert rates.loc[:"2021-12-31"].tail(200).mean() < 0.01, "2021 rates should be near zero"
    assert rates.loc["2023-01-01":"2023-12-31"].mean() > 0.03, "2023 rates should be ~5%"


def test_weekly_carry_is_sane_across_rate_regimes():
    """Financing must cost ~ (rate+premium) a year on invested capital, and the
    gate must not be silently penalised: full cash at any rate costs nothing."""
    zirp = KC.weekly_carry(0.0003, 0.03, 1.0)      # 2021: ~3%/yr all-in
    tight = KC.weekly_carry(0.05, 0.03, 1.0)       # 2023: ~8%/yr all-in
    assert zirp * 52 == pytest.approx(0.0303, abs=2e-3)
    assert tight * 52 == pytest.approx(0.0803, abs=2e-3)
    assert tight > zirp * 2, "carry must rise with the policy rate"
    assert KC.weekly_carry(0.05, 0.03, 0.0) == pytest.approx(-0.05 * 7 / 365), "cash should earn the bill"


# --- GUARD 4: no look-ahead at the signal/fill seam -------------------------

def test_signal_always_precedes_fill(panel):
    px, _, _, _ = panel
    sessions = px.index
    grid = KC.weekly_grid(sessions)
    pairs = KC.signal_fill_pairs(sessions, grid)
    assert len(pairs) > 900, f"only {len(pairs)} rebalances over the window"
    for sd, fd in pairs:
        assert sd < fd, f"signal {sd} not before fill {fd}"
        assert sessions.get_loc(fd) - sessions.get_loc(sd) == P.SIGNAL_DAY_LAG


def test_weekly_grid_handles_holiday_weeks(panel):
    """Good Friday 2015-04-03: the week must anchor on Thursday 2015-04-02."""
    px, _, _, _ = panel
    grid = KC.weekly_grid(px.index)
    assert pd.Timestamp("2015-04-02") in grid
    assert pd.Timestamp("2015-04-03") not in grid


def test_weekly_grid_year_boundary(panel):
    px, _, _, _ = panel
    grid = KC.weekly_grid(px.index)
    g = pd.DatetimeIndex(grid)
    assert len(g) == len(set(g.to_period("W"))), "more than one grid date in some ISO week"
    assert pd.Timestamp("2015-12-31") in grid or pd.Timestamp("2016-01-01") in grid
