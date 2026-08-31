#!/usr/bin/env python3
"""AeroSkills number snapshot engine (deterministic, no LLM).

Live-verifies the `tracked` section of ops/automation/numbers.yaml against the
GitHub API via `gh` (authed as arjun-0077). Writes a timestamped snapshot JSON
to the snapshot state dir (default ops/automation/state/). Exit 0 only when
every tracked repo's live stars are within the expected range AND the derived
"largest aerospace repo" matches; exit 1 on drift with a diff; exit 2 on API
failure (never a silent network fallback).

Modes:
  --live     query GitHub API, write snapshot, check ranges
  --offline  read the newest snapshot, re-check recorded live values against
             the CURRENT register (never silent drift: missing snapshot = exit 1)

Env overrides:
  NUMBERS_YAML         register path (default ops/automation/numbers.yaml)
  SNAPSHOT_STATE_DIR   snapshot dir (default ops/automation/state)
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_YAML = os.path.join(REPO_ROOT, "ops", "automation", "numbers.yaml")
DEFAULT_STATE = os.path.join(REPO_ROOT, "ops", "automation", "state")


def load_register(path):
    import yaml
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def gh_stars(repo):
    """Live star count via gh api. Raises RuntimeError on failure (no fallback)."""
    try:
        out = subprocess.run(
            ["gh", "api", f"repos/{repo}", "--jq", ".stargazers_count"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except FileNotFoundError:
        raise RuntimeError("gh CLI not found on PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"gh api timed out for {repo}")
    if out.returncode != 0:
        raise RuntimeError(f"gh api failed for {repo}: {out.stderr.strip()}")
    try:
        return int(out.stdout.strip())
    except ValueError:
        raise RuntimeError(f"unparseable gh output for {repo}: {out.stdout.strip()!r}")


def within(expected, live, entry):
    if entry.get("tolerance_abs") is not None:
        return abs(live - expected) <= entry["tolerance_abs"]
    pct = entry.get("tolerance_pct", 5)
    return abs(live - expected) <= max(1, expected * pct / 100.0)


def snapshot_paths(state_dir):
    os.makedirs(state_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return os.path.join(state_dir, f"stars-snapshot-{ts}.json"), os.path.join(state_dir, "stars-latest.json")


def run_live(reg, state_dir):
    tracked = reg["tracked"]
    results = []
    api_fail = None
    for entry in tracked:
        try:
            live = gh_stars(entry["repo"])
        except RuntimeError as exc:
            api_fail = str(exc)
            print(f"ERROR number-snapshot: {exc}", file=sys.stderr)
            break
        results.append({
            "id": entry["id"], "repo": entry["repo"],
            "expected": entry["stars"], "live": live,
            "within_tolerance": within(entry["stars"], live, entry),
            "tolerance_pct": entry.get("tolerance_pct"),
            "tolerance_abs": entry.get("tolerance_abs"),
        })
    if api_fail:
        # do not write a snapshot claiming success; exit 2 (clear, non-zero)
        print("ERROR number-snapshot: API failure — no silent fallback; no snapshot written.", file=sys.stderr)
        return 2

    # derived: largest aerospace repo = max(live ajhcs, live devideamax)
    live_by_id = {r["id"]: r["live"] for r in results}
    d_res = {"id": "largest_aerospace_repo", "expected": None, "live": None,
             "within_tolerance": False, "tolerance_pct": None, "tolerance_abs": None}
    total = {"id": "total_aerospace_stars", "expected": None, "source": "missing in register",
             "note": "informational — not re-derivable from tracked set"}
    for d in reg.get("derived", []):
        if d["id"] == "largest_aerospace_repo":
            largest_expected = d["value"]
            largest_live = max(live_by_id.get("ajhcs", -1), live_by_id.get("devideamax", -1))
            d_res = {
                "id": d["id"], "expected": largest_expected, "live": largest_live,
                "within_tolerance": within(largest_expected, largest_live, d),
                "tolerance_pct": d.get("tolerance_pct"), "tolerance_abs": d.get("tolerance_abs"),
            }
        elif d["id"] == "total_aerospace_stars":
            total = {"id": d["id"], "expected": d["value"], "source": d["source"],
                     "note": "informational — not re-derivable from tracked set"}

    ok = all(r["within_tolerance"] for r in results) and d_res["within_tolerance"]
    snapshot = {
        "schema": "aeroskills-stars-snapshot/v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "as_of": reg.get("as_of"),
        "register": os.path.basename(os.environ.get("NUMBERS_YAML", DEFAULT_YAML)),
        "mode": "live",
        "tracked": results,
        "derived": [d_res],
        "total_aerospace_stars": total,
        "exit": 0 if ok else 1,
    }
    ts_path, latest = snapshot_paths(state_dir)
    with open(ts_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2)
    with open(latest, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2)

    for r in results:
        mark = "OK " if r["within_tolerance"] else "FAIL"
        print(f"{mark} number-snapshot {r['repo']}: expected {r['expected']}, live {r['live']}")
    mark = "OK " if d_res["within_tolerance"] else "FAIL"
    print(f"{mark} number-snapshot derived {d_res['id']}: expected {d_res['expected']}, live {d_res['live']}")
    print(f"INFO number-snapshot total_aerospace_stars: {total['expected']} (informational, {total['source']})")
    print(f"INFO number-snapshot written: {ts_path}")
    return 0 if ok else 1


def run_offline(reg, state_dir):
    latest = os.path.join(state_dir, "stars-latest.json")
    if not os.path.exists(latest):
        print("ERROR number-snapshot --offline: no snapshot exists; run --live first (never silent drift).", file=sys.stderr)
        return 1
    with open(latest, "r", encoding="utf-8") as fh:
        snap = json.load(fh)
    tracked_by_id = {e["id"]: e for e in reg["tracked"]}
    ok = True
    print(f"INFO number-snapshot --offline using snapshot from {snap.get('timestamp_utc')}")
    for r in snap.get("tracked", []):
        entry = tracked_by_id.get(r["id"])
        if entry is None:
            print(f"FAIL number-snapshot --offline: {r['id']} no longer in register", file=sys.stderr)
            ok = False
            continue
        rec = within(entry["stars"], r["live"], entry)
        mark = "OK " if rec else "FAIL"
        print(f"{mark} number-snapshot --offline {r['repo']}: expected {entry['stars']}, recorded {r['live']}")
        ok = ok and rec
    for d in snap.get("derived", []):
        for regd in reg.get("derived", []):
            if regd["id"] == d["id"] and regd["id"] == "largest_aerospace_repo":
                rec = within(regd["value"], d["live"], regd)
                mark = "OK " if rec else "FAIL"
                print(f"{mark} number-snapshot --offline derived {d['id']}: expected {regd['value']}, recorded {d['live']}")
                ok = ok and rec
    return 0 if ok else 1


def main():
    args = [a for a in sys.argv[1:] if a.startswith("--")]
    mode = "offline"
    if "--live" in args:
        mode = "live"
    reg = load_register(os.environ.get("NUMBERS_YAML", DEFAULT_YAML))
    state_dir = os.environ.get("SNAPSHOT_STATE_DIR", DEFAULT_STATE)
    if mode == "live":
        return run_live(reg, state_dir)
    return run_offline(reg, state_dir)


if __name__ == "__main__":
    sys.exit(main())
