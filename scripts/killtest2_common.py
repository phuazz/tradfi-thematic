"""KT-2 shared machinery — the pieces the P0 guards pin and the confirmation
engine will import, so live code and tests cannot drift apart.

Calendar and carry conventions are IMPORTED from killtest_common (identical by
design); this module adds only what KT-2 introduces: the point-in-time
liquidity screen and the frozen correlation-cluster theme definition.

Nothing here computes a strategy result.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prereg_killtest2 as P2  # noqa: E402
from killtest_common import (  # noqa: E402,F401  (re-exported conventions)
    rate_to_fraction, signal_fill_pairs, weekly_carry, weekly_grid)


def liquid_set(dv: pd.DataFrame, sessions: pd.DatetimeIndex, t: pd.Timestamp,
               fresh=None, top_n: int = P2.TOP_N, window: int = P2.DV_WINDOW,
               min_obs: int = P2.DV_MIN_OBS) -> set:
    """Top-N names by trailing median dollar volume, sessions STRICTLY before
    t — the point-in-time universe rule. `fresh` restricts candidacy to names
    alive at t (staleness within the ffill limit); a name cannot be ranked on
    fewer than `min_obs` prints."""
    pos = sessions.get_loc(t)
    win = dv.iloc[max(0, pos - window):pos]          # excludes session t
    med = win.median()
    med = med[win.notna().sum() >= min_obs]
    if fresh is not None:
        med = med[med.index.isin(fresh)]
    return set(med.nlargest(top_n).index)


def form_clusters(weekly_ret: pd.DataFrame, names, formation_date,
                  window: int = P2.CORR_WINDOW_WEEKS,
                  min_weeks: int = P2.CORR_MIN_WEEKS,
                  cut: float = P2.CLUSTER_CUT):
    """Frozen S2 spec: pairwise correlation of trailing weekly returns
    STRICTLY before the formation date, distance 1 - rho, average linkage,
    tree cut at `cut`. Names with under `min_weeks` observations form
    singletons; pairs with insufficient overlap take distance 1 (never
    co-clustered). Returns (labels, degeneracy_stats)."""
    names = list(names)
    r = weekly_ret[weekly_ret.index < pd.Timestamp(formation_date)].tail(window)
    labels: dict[str, int] = {}
    valid = [n for n in names if n in r.columns and r[n].notna().sum() >= min_weeks]
    if len(valid) >= 2:
        c = r[valid].corr(min_periods=min_weeks)
        d = (1.0 - c.fillna(0.0)).to_numpy(copy=True)   # copy: .values can be read-only
        np.fill_diagonal(d, 0.0)
        d = (d + d.T) / 2.0
        z = linkage(squareform(d, checks=False), method="average")
        for n, k in zip(valid, fcluster(z, t=cut, criterion="distance")):
            labels[n] = int(k)
    nxt = (max(labels.values()) if labels else 0) + 1
    for n in names:
        if n not in labels:
            labels[n] = nxt
            nxt += 1
    sizes = pd.Series(labels).value_counts()
    stats = {"largest_frac": float(sizes.iloc[0] / len(names)) if names else 0.0,
             "singleton_frac": float((sizes == 1).sum() / len(names)) if names else 0.0}
    return labels, stats


def clustering_degenerate(stats: dict) -> bool:
    """The frozen degeneracy guard: either trip means KT-2 falls back to the
    GICS sector cap throughout — no re-specification."""
    return (stats["largest_frac"] > P2.DEGEN_LARGEST_FRAC
            or stats["singleton_frac"] > P2.DEGEN_SINGLETON_FRAC)
