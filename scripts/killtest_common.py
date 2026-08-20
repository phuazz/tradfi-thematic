"""Shared conventions for the kill-test — the pieces the guards pin and the
P1 engine will import, so live code and tests cannot drift apart.

Nothing here decides anything about a strategy; it is calendar and eligibility
plumbing only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prereg_killtest as P  # noqa: E402


def weekly_grid(sessions: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last trading session of each ISO week — the Friday close, or Thursday
    when Friday is a holiday. Built from the sessions that actually traded,
    never from weekday arithmetic."""
    s = pd.Series(sessions, index=sessions)
    return pd.DatetimeIndex(s.groupby(sessions.to_period("W")).max().values)


def signal_fill_pairs(sessions: pd.DatetimeIndex, grid: pd.DatetimeIndex,
                      lag: int = P.SIGNAL_DAY_LAG) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """(signal_date, fill_date) per rebalance. The signal is read `lag`
    sessions BEFORE the fill, so a decision can never use the price it is
    filled at. This is the one convention the whole study rests on."""
    out = []
    for rd in grid:
        pos = sessions.get_loc(rd)
        if pos - lag < 0:
            continue
        out.append((sessions[pos - lag], rd))
    return out


def rate_to_fraction(quoted_percent: float) -> float:
    """^IRX is quoted as an annualised PERCENT (3.7 means 3.7%/yr). Everything
    downstream works in fractions. Getting this wrong inflates funding a
    hundredfold, so it lives in one function with a test on it."""
    return quoted_percent / 100.0


def weekly_carry(rate_fraction: float, premium: float, invested: float,
                 cash_earns: bool = P.CASH_EARNS_RATE) -> float:
    """One week of net carry: financing charged on the invested fraction at
    (rate + premium), less the T-bill earned on whatever sits in cash."""
    financed = (rate_fraction + premium) * invested
    earned = rate_fraction * (1.0 - invested) if cash_earns else 0.0
    return (financed - earned) * 7.0 / 365.0
