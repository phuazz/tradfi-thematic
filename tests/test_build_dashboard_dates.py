"""Date edge cases for build_dashboard.sgt_date (UTC -> SGT calendar date).

The evaluator runs at 07:15 SGT, which is 23:15 UTC on the previous day, so a
UTC slice prints the wrong date. Python datetime: months are 1-indexed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from build_dashboard import sgt_date  # noqa: E402


def test_previous_utc_day_rolls_forward():
    assert sgt_date("2026-10-13T23:15:05.533955+00:00") == "2026-10-14"


def test_month_boundary():
    assert sgt_date("2026-08-31T16:00:00+00:00") == "2026-09-01"
    assert sgt_date("2026-08-31T15:59:59+00:00") == "2026-08-31"


def test_year_boundary():
    assert sgt_date("2026-12-31T23:15:00+00:00") == "2027-01-01"


def test_missing_timestamp():
    assert sgt_date(None) is None
