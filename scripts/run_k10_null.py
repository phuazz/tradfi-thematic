"""Amendment 2 gate: 1,000-path cost-matched random-selection null at the
K=10 cluster-cap-2 shape (frozen seed, band edge, 1x costs). The pivot to the
K=10 rotation as the live payload requires the strategy's net Sharpe to sit at
or above the null's 90th percentile — stated before the first run's result was
known. Rerun whenever the universe or engine inputs change; the strategy
Sharpe is read fresh from data/phase2_results.json, never hard-coded.

Run: python scripts/run_k10_null.py -> data/k10_null.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402
import prereg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
K, CAP = 10, 2


def main() -> int:
    d = engine.load_inputs()
    weeks = engine.precompute_weeks(d)
    edge = prereg.FUNDING_BAND_ANN[-1]
    fee_side = prereg.FEE_RT_BPS / 2.0 / 10_000.0
    rng = np.random.default_rng(prereg.NULL_SEED)
    sharpes = []
    for _ in range(prereg.NULL_PATHS):
        rets, prev = [], set()
        for w in weeks:
            if w["gated"] or not w["above"]:
                picks = set()
            else:
                order = rng.permutation(len(w["above"]))
                picks, counts = [], {}
                for j in order:
                    nname = w["above"][j]
                    c = d["clusters"].get(nname, "unclassified")
                    if counts.get(c, 0) >= CAP:
                        continue
                    picks.append(nname)
                    counts[c] = counts.get(c, 0) + 1
                    if len(picks) == K:
                        break
                picks = set(picks)
            to = (len(prev) + len(picks) - 2 * len(prev & picks)) / K
            inv = len(picks) / K
            carry = (edge * inv + sum(d["yields"][nname] for nname in picks) / K) * 7.0 / 365.0
            gross = sum(w["ret"].get(nname, 0.0) for nname in picks) / K
            rets.append(gross - fee_side * to - carry)
            prev = picks
        arr = pd.Series(rets)
        sd = arr.std()
        sharpes.append(float(arr.mean() / sd * np.sqrt(52)) if sd > 0 else 0.0)
    a = np.array(sharpes)
    results = json.loads((ROOT / "data" / "phase2_results.json").read_text(encoding="utf-8"))
    strat = results["cells"][f"k{K}_cap{CAP}"][f"m1_b{edge:g}"]["sharpe"]
    out = {"k": K, "cap": CAP, "n_paths": len(a), "seed": prereg.NULL_SEED,
           "p50": round(float(np.percentile(a, 50)), 3),
           "p90": round(float(np.percentile(a, 90)), 3),
           "p95": round(float(np.percentile(a, 95)), 3),
           "strategy_sharpe": strat,
           "strategy_percentile": round(float((a < strat).mean() * 100), 1),
           "gate": "strategy_percentile >= 90 required for the Amendment 2 payload",
           # Full distribution so the dashboard can plot the null at the shape
           # the LIVE payload actually runs, rather than the K=5 one.
           "sharpes": [round(float(v), 3) for v in a]}
    (ROOT / "data" / "k10_null.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
