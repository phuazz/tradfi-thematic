"""FV-1 weekly paper-track runner — log-and-publish only, never an order.

Chain (per FV-1 implementation notes 2-3, signed 2026-08-21):
  1. Rebuild the Russell panel fresh from Norgate.
  2. Freshness + universe-size floors (fail loudly, append nothing).
  3. Recompute the whole history on the shared code path; CAPTURE-INTEGRITY:
     the most recent already-logged weeks must reproduce from the fresh panel
     (identical picks over the last 4 logged weeks; weekly returns within
     5bp over the last 8 — vendor adjustment revisions beyond that abort).
  4. Append any newly COMPLETED weekly rows to data/fv1_track.json
     (baseline NAV = 100 at the last completed fill before sign-off).
  5. Rebuild fv1_detail + dashboard; commit and push (best-effort).

Scheduled weekly (Saturday morning SGT) as TradfiThematic-FV1Track; watched
by fleet_watch ("tradfi FV-1 paper track"). Run manually: python
scripts/fv1_paper_track.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TRACK = DATA / "fv1_track.json"
BASELINE = "2026-08-14"          # last completed weekly fill before sign-off
W = 0.30
MIN_UNIVERSE = 2000
MAX_STALE_WEEKDAYS = 5


def fail(msg: str) -> int:
    print(f"FV1-TRACK FAIL: {msg}")
    return 1


def main() -> int:
    r = subprocess.run([sys.executable, "scripts/build_killtest2_universe.py"],
                       cwd=ROOT, capture_output=True, text=True, timeout=1200)
    if r.returncode != 0:
        return fail(f"panel rebuild rc={r.returncode}: {r.stdout[-300:]} {r.stderr[-300:]}")

    import persist_fv1_detail as PF
    H = PF.compute_history()
    diags, cash, bill = H["diags"], H["cash_basis"], H["bill_w"]

    last_session = H["px_raw"].index.max()
    stale_days = len(pd.bdate_range(last_session, pd.Timestamp.now().normalize())) - 1
    if stale_days > MAX_STALE_WEEKDAYS:
        return fail(f"panel stale: last session {last_session.date()} ({stale_days} weekdays)")
    if H["px_raw"].shape[1] < MIN_UNIVERSE:
        return fail(f"universe collapsed: {H['px_raw'].shape[1]} symbols")

    fresh = {}
    for d, rr, rb in zip(diags, cash.values, bill.values):
        if d["date"] >= pd.Timestamp(BASELINE):
            fresh[d["date"].strftime("%Y-%m-%d")] = {
                "picks": d["held"], "breadth": round(d["breadth"], 3),
                "invested": d["invested"], "rot_ret": float(rr), "bill_ret": float(rb)}

    track = json.loads(TRACK.read_text(encoding="utf-8")) if TRACK.exists() else {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_date": BASELINE, "w": W,
        "protocol": "reviews/2026-08-21_rotation-forward-validation_preregistration.md",
        "rows": []}

    # --- capture integrity against already-logged rows -----------------------
    logged = track["rows"]
    for row in logged[-4:]:
        if row["date"] == BASELINE:
            continue
        f = fresh.get(row["date"])
        if f is None or f["picks"] != row["picks"]:
            return fail(f"picks for {row['date']} no longer reproduce from the fresh panel")
    for row in logged[-8:]:
        f = fresh.get(row["date"])
        if f and row.get("rot_ret") is not None and abs(f["rot_ret"] - row["rot_ret"]) > 5e-4:
            return fail(f"return for {row['date']} moved {abs(f['rot_ret']-row['rot_ret'])*1e4:.1f}bp on refresh")

    # --- append newly completed weeks ----------------------------------------
    have = {r_["date"] for r_ in logged}
    nav_rot = logged[-1]["nav_rot"] if logged else 100.0
    nav_blend = logged[-1]["nav_blend"] if logged else 100.0
    we = logged[-1].get("w_eff", W) if logged else W
    last_month = int(logged[-1]["date"][5:7]) if logged else int(BASELINE[5:7])
    added = 0
    for dstr in sorted(fresh):
        if dstr in have:
            continue
        f = fresh[dstr]
        if dstr == BASELINE:
            row = {"date": dstr, "nav_rot": 100.0, "nav_blend": 100.0, "w_eff": W,
                   "picks": f["picks"], "breadth": f["breadth"], "invested": f["invested"],
                   "rot_ret": None, "bill_ret": None, "note": "baseline"}
        else:
            m = int(dstr[5:7])
            if m != last_month:
                we = W
            r_bl = we * f["rot_ret"] + (1 - we) * f["bill_ret"]
            nav_rot *= (1 + f["rot_ret"])
            nav_blend *= (1 + r_bl)
            we = we * (1 + f["rot_ret"]) / (1 + r_bl) if (1 + r_bl) != 0 else W
            row = {"date": dstr, "nav_rot": round(nav_rot, 4), "nav_blend": round(nav_blend, 4),
                   "w_eff": round(we, 4), "picks": f["picks"], "breadth": f["breadth"],
                   "invested": f["invested"], "rot_ret": round(f["rot_ret"], 6),
                   "bill_ret": round(f["bill_ret"], 6)}
            last_month = m
        logged.append(row)
        have.add(dstr)
        added += 1
    track["rows"] = logged
    track["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    TRACK.write_text(json.dumps(track, indent=1), encoding="utf-8")
    print(f"track rows {len(logged)} (+{added}) · last {logged[-1]['date']} · "
          f"nav_blend {logged[-1]['nav_blend']}")

    for script in ("scripts/persist_fv1_detail.py", "scripts/build_dashboard.py"):
        rr = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True,
                            text=True, timeout=1800)
        if rr.returncode != 0:
            return fail(f"{script} rc={rr.returncode}: {rr.stderr[-300:]}")

    for cmd in (["git", "pull", "--rebase", "--autostash", "origin", "main"],
                ["git", "add", "data/fv1_track.json", "data/fv1_detail.json",
                 "data/killtest2_meta.json", "dashboard.html", "docs/index.html"],
                ["git", "commit", "-m", f"auto: FV-1 paper track {datetime.now(timezone.utc).date()}"],
                ["git", "push", "origin", "main"]):
        subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=300)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
