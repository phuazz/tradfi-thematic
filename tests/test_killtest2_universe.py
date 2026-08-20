"""KT-2 P0 guards — the failure modes named in section 7 of the signed
pre-registration, pinned before any strategy result exists. Each test is a way
the study could be silently wrong, written so the defect turns it red.

Run: pytest tests/test_killtest2_universe.py -q
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import killtest2_common as KC2  # noqa: E402
import prereg_killtest2 as P2  # noqa: E402

DATA = ROOT / "data"
pytestmark = pytest.mark.skipif(not (DATA / "killtest2_prices.parquet").exists(),
                                reason="KT-2 P0 panel not built")


@pytest.fixture(scope="module")
def panel():
    px = pd.read_parquet(DATA / "killtest2_prices.parquet")
    dv = pd.read_parquet(DATA / "killtest2_dollarvol.parquet")
    meta = json.loads((DATA / "killtest2_meta.json").read_text(encoding="utf-8"))
    rates = pd.read_parquet(DATA / "killtest2_rates.parquet")["rf"]
    return px, dv, meta, rates


@pytest.fixture(scope="module")
def fresh_by_date(panel):
    """Names alive (fresh within the ffill limit) per session — the screen's
    candidacy condition, computed once."""
    px, _, _, _ = panel
    marker = pd.DataFrame(np.where(px.notna(), np.arange(len(px))[:, None], np.nan),
                          index=px.index, columns=px.columns).ffill()
    stale = pd.DataFrame(np.arange(len(px))[:, None] - marker.values,
                         index=px.index, columns=px.columns)
    return stale


# --- GUARD A: survivorship on the confirmation panel ------------------------

def test_delisted_names_are_carried(panel):
    _, _, meta, _ = panel
    m = meta["meta"]
    dead = [s for s, v in m.items() if v["delisted"]]
    in_window = [s for s in dead if v_last(m, s) >= P2.BACKTEST_START]
    assert len(dead) > 400, f"only {len(dead)} delisted symbols — archive not loaded?"
    assert len(in_window) > 400, f"only {len(in_window)} die inside the window"


def v_last(m, s):
    return m[s]["last_bar"]


def test_no_post2005_delisting_is_missing(panel):
    """The build records any unavailable symbol that is not a pre-2005
    delisting. That count must be zero — anything else is a survivorship hole."""
    _, _, meta, _ = panel
    assert meta["n_unavailable_post2005"] == 0, meta["unavailable_post2005"]


def test_dead_names_stop_and_do_not_ffill_forever(panel):
    px, _, meta, _ = panel
    m = meta["meta"]
    dead = [s for s, v in m.items()
            if v["delisted"] and P2.BACKTEST_START <= v["last_bar"] < "2020-01-01"
            and s in px.columns]
    assert dead, "no delisted names inside the window to check"
    for s in dead[:15]:
        after = px[s].loc[pd.Timestamp(m[s]["last_bar"]) + pd.Timedelta(days=5):]
        assert after.notna().sum() == 0, f"{s} still has prices after its last bar"


# --- GUARD B: the liquidity screen is strictly point-in-time -----------------

def _grid(px):
    g = KC2.weekly_grid(px.index)
    return g[g >= pd.Timestamp(P2.BACKTEST_START)]


def test_screen_ignores_future_volume(panel, fresh_by_date):
    """Inject an enormous volume spike AT and AFTER t; the date-t selection
    must not move. This is the look-ahead the screen exists to exclude."""
    px, dv, _, _ = panel
    stale = fresh_by_date
    grid = _grid(px)
    for t in [grid[100], grid[500], grid[900]]:
        fresh = set(px.columns[stale.loc[t] <= P2.FFILL_LIMIT_SESSIONS])
        base = KC2.liquid_set(dv, px.index, t, fresh=fresh)
        poked = dv.copy()
        pos = px.index.get_loc(t)
        loser = sorted(set(px.columns) - base)[0]
        poked.iloc[pos:pos + 5, poked.columns.get_loc(loser)] = 1e15
        assert KC2.liquid_set(poked, px.index, t, fresh=fresh) == base, \
            f"future volume at {t.date()} changed the selection"


def test_leaky_screen_variant_is_detectable(panel, fresh_by_date):
    """Prove the guard has teeth against a leak the MEDIAN can actually see.
    A one-print spike cannot move a 60-session median (its robustness is part
    of why the spec chose it), so the demonstrated defect is a CENTRED window
    — 35 future sessions — the classic off-by-half leak. The shipped screen
    must ignore the same spiked data; the centred variant must admit it."""
    px, dv, _, _ = panel
    stale = fresh_by_date
    t = _grid(px)[500]
    fresh = set(px.columns[stale.loc[t] <= P2.FFILL_LIMIT_SESSIONS])
    base = KC2.liquid_set(dv, px.index, t, fresh=fresh)
    poked = dv.copy()
    pos = px.index.get_loc(t)
    loser = sorted(fresh - base)[0]
    poked.iloc[pos:pos + 35, poked.columns.get_loc(loser)] = 1e15
    assert KC2.liquid_set(poked, px.index, t, fresh=fresh) == base, \
        "the shipped screen must not see 35 future sessions of spike"
    win = poked.iloc[pos - 25:pos + 35]                        # centred: leaks the future
    med = win.median()
    med = med[win.notna().sum() >= P2.DV_MIN_OBS]
    leaky = set(med[med.index.isin(fresh)].nlargest(P2.TOP_N).index)
    assert loser in leaky and leaky != base, "the centred variant should admit the spiked name"


def test_screen_fills_to_top_n(panel, fresh_by_date):
    """From mid-2006 the eligible set must be exactly TOP_N essentially always
    — a shrinking set would mean the screen is quietly starving."""
    px, dv, _, _ = panel
    stale = fresh_by_date
    grid = _grid(px)
    grid = grid[grid >= pd.Timestamp("2006-07-01")]
    sample = grid[:: max(1, len(grid) // 60)]
    short = 0
    for t in sample:
        fresh = set(px.columns[stale.loc[t] <= P2.FFILL_LIMIT_SESSIONS])
        if len(KC2.liquid_set(dv, px.index, t, fresh=fresh)) < P2.TOP_N:
            short += 1
    assert short == 0, f"{short} of {len(sample)} sampled rebalances under {P2.TOP_N}"


def test_dead_names_flow_through_the_screen(panel, fresh_by_date):
    """Names that later died must actually traverse the top-250 while alive —
    otherwise the screen is winners-only and survivorship is back."""
    px, dv, meta, _ = panel
    stale = fresh_by_date
    grid = _grid(px)
    dead_cols = {s for s, v in meta["meta"].items() if v["delisted"]}
    years_hit = set()
    for t in grid[:: max(1, len(grid) // 40)]:
        fresh = set(px.columns[stale.loc[t] <= P2.FFILL_LIMIT_SESSIONS])
        sel = KC2.liquid_set(dv, px.index, t, fresh=fresh)
        if sel & dead_cols:
            years_hit.add(t.year)
    assert len(years_hit) >= 8, f"delisted names appear in the screen in only {sorted(years_hit)}"


# --- GUARD C: cluster formation cannot see the future ------------------------

def _weekly_ret(px):
    g = KC2.weekly_grid(px.index)
    return px.ffill().reindex(g).pct_change()


def test_cluster_formation_ignores_future_returns(panel):
    px, _, _, _ = panel
    wr = _weekly_ret(px)
    names = [c for c in px.columns if wr[c].notna().sum() > 160][:80]
    formation = pd.Timestamp("2015-01-02")
    base, _ = KC2.form_clusters(wr, names, formation)
    poked = wr.copy()
    poked.loc[poked.index >= formation, names[0]] = 5.0    # absurd future spike
    again, _ = KC2.form_clusters(poked, names, formation)
    assert again == base, "future returns changed cluster assignments"


def test_short_history_names_form_singletons(panel):
    px, _, _, _ = panel
    wr = _weekly_ret(px)
    names = [c for c in px.columns if wr[c].notna().sum() > 160][:20]
    fake = "SYNTH_SHORT"
    wr2 = wr.copy()
    wr2[fake] = np.nan
    wr2.iloc[-10:, wr2.columns.get_loc(fake)] = 0.01       # 10 weeks only
    labels, _ = KC2.form_clusters(wr2, names + [fake], wr2.index[-1])
    assert sum(1 for v in labels.values() if v == labels[fake]) == 1, \
        "a 10-week name must not co-cluster with anything"


def test_degeneracy_detector_fires_on_degenerate_data():
    """Constructed one-factor data → one giant cluster → detector trips.
    Constructed independent noise at high cut... instead: all-identical
    series must trip largest_frac; the detector is the fallback trigger."""
    rng = np.random.default_rng(7)
    idx = pd.date_range("2012-01-06", periods=160, freq="W-FRI")
    common = rng.normal(0, 0.02, len(idx))
    data = {f"N{i}": common + rng.normal(0, 0.001, len(idx)) for i in range(30)}
    wr = pd.DataFrame(data, index=idx)
    _, stats = KC2.form_clusters(wr, list(wr.columns), idx[-1])
    assert stats["largest_frac"] > P2.DEGEN_LARGEST_FRAC
    assert KC2.clustering_degenerate(stats)


# --- GUARD D: rates and calendar (re-pins on the new panel) ------------------

def test_rates_are_fractions_with_regime_shape(panel):
    _, _, _, rates = panel
    assert 0.0 <= rates.max() <= 0.12, f"rate max {rates.max()} looks like percent"
    assert rates.loc[:"2021-12-31"].tail(200).mean() < 0.01
    assert rates.loc["2023-01-01":"2023-12-31"].mean() > 0.03


def test_signal_precedes_fill_on_new_panel(panel):
    px, _, _, _ = panel
    pairs = KC2.signal_fill_pairs(px.index, _grid(px))
    assert len(pairs) > 1000
    for sd, fd in pairs:
        assert sd < fd
        assert px.index.get_loc(fd) - px.index.get_loc(sd) == P2.SIGNAL_DAY_LAG


def test_weekly_grid_holiday_and_year_boundary(panel):
    px, _, _, _ = panel
    grid = KC2.weekly_grid(px.index)
    assert pd.Timestamp("2015-04-02") in grid       # Good Friday week -> Thursday
    assert pd.Timestamp("2015-04-03") not in grid
    g = pd.DatetimeIndex(grid)
    assert len(g) == len(set(g.to_period("W")))
