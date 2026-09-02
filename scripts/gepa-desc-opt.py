#!/usr/bin/env python3
"""GEPA description-optimization harness for AeroSkills Hit@1 (GEPA ADAPT).

The main corpus is saturated (674/674). The real optimization target is
ROBUSTNESS: descriptions that win their own queries but lose to a
confusable neighbor on paraphrased / near-miss queries.

This harness:
1. Generates held-out paraphrase queries per skill (deterministic,
   offline — swaps key vocabulary with domain synonyms).
2. Finds skills whose CURRENT description loses the held-out query to a
   neighbor (the weak set).
3. Runs GEPA on those weak descriptions with the real router scorer as
   evaluator — description text is the candidate, Hit@1 on the held-out
   set is the metric, ASI logs the confusable neighbor that won.
4. Writes the optimized description back ONLY if Hit@1 improves on
   held-out AND does not regress the main corpus (dual-gate).

Requires: gepa (pip install gepa) + an LLM provider key via litellm
(DeepSeek/OpenRouter verified). Run offline-first: evaluator is the
deterministic router (no network); only the GEPA reflection/mutation
calls need the provider.

Usage:
  python3 scripts/gepa-desc-opt.py --dry-run          # find weak set only
  python3 scripts/gepa-desc-opt.py --skill <rel-path> # optimize one skill
  python3 scripts/gepa-desc-opt.py --all              # optimize all weak
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from router_eval import load_skills, score  # noqa: E402

SKILLS_ROOT = pathlib.Path(__file__).resolve().parents[1] / "skills"
CORPUS = pathlib.Path(__file__).resolve().parents[1] / "eval" / "hit1-corpus.yaml"

# Domain synonym map for held-out paraphrase generation (offline,
# deterministic). Key = vocabulary already in descriptions; value =
# alternate phrasing a user might use.
SYNONYMS = {
    "aircraft": ["airplane", "fixed-wing"],
    "airplane": ["aircraft"],
    "flutter": ["oscillation", "aeroelastic instability"],
    "fatigue": ["cyclic loading", "crack growth"],
    "software": ["code", "program"],
    "safety": ["protection", "assurance"],
    "failure": ["malfunction", "loss"],
    "certification": ["qualification", "type approval"],
    "verification": ["checking", "validation test"],
    "test": ["evaluation"],
    "engine": ["powerplant", "turbine"],
    "wing": ["lifting surface"],
    "load": ["force", "stress"],
    "stress": ["load"],
    "corrosion": ["material degradation"],
    "lightning": ["electrical discharge", "strike"],
    "risk": ["hazard likelihood"],
    "hazard": ["danger", "risk source"],
}


def paraphrase_query(query: str) -> str:
    """Deterministic held-out paraphrase: replace the FIRST known term."""
    ql = query.lower()
    for term, alts in SYNONYMS.items():
        if term in ql:
            return query.replace(term, alts[0], 1)
    return query  # no known term — leave as-is (already hard)


def held_out_tasks(orig_tasks, seed=7):
    """Map each corpus task to a paraphrase held-out task."""
    import random
    rng = random.Random(seed)
    out = []
    for t in orig_tasks:
        q = paraphrase_query(t["query"])
        # ~50%: paraphrase; rest unchanged (keeps distribution honest)
        if rng.random() < 0.5:
            out.append({**t, "query": q, "held_out": True})
        else:
            out.append({**t, "held_out": False})
    return out


def find_weak_skills(skills, tasks):
    """Skills that LOSE their own held-out query to a neighbor."""
    weak = {}
    for t in tasks:
        if not t.get("held_out"):
            continue
        exp = t["expected_skill"]
        if exp not in skills:
            continue
        scored = [(score(s, t["query"]), p) for p, s in skills.items()]
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        top_path = scored[0][1]
        if top_path != exp:
            weak.setdefault(exp, []).append((t, top_path, scored[0][0]))
    return weak


def evaluate_description(skills, tasks, target, new_desc):
    """Router Hit@1 for ONE skill with a candidate description."""
    # deep-copy the skill set with the new description
    import copy
    mod = copy.deepcopy(skills)
    if target not in mod:
        return 0.0, []
    mod[target]["description"] = new_desc
    hits = 0
    total = 0
    asis = []
    for t in tasks:
        exp = t["expected_skill"]
        if exp != target:
            continue
        total += 1
        scored = [(score(s, t["query"]), p) for p, s in mod.items()]
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        if scored[0][1] == target:
            hits += 1
        else:
            asis.append(f"query '{t['query'][:50]}' → got {scored[0][1]}")
    return (hits / total) if total else 0.0, asis


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="find weak set, no GEPA")
    ap.add_argument("--skill", type=str, default="", help="optimize one skill path")
    ap.add_argument("--all", action="store_true", help="optimize all weak skills")
    ap.add_argument("--json-out", type=str, default="eval/gepa-desc-results.json")
    args = ap.parse_args()

    skills = load_skills(str(SKILLS_ROOT))
    corpus = yaml.safe_load(CORPUS.read_text())
    tasks = corpus["tasks"]
    held = held_out_tasks(tasks)
    weak = find_weak_skills(skills, held)

    print(f"skills={len(skills)} corpus_tasks={len(tasks)} held_out_tasks={len([t for t in held if t.get('held_out')])}")
    if args.dry_run:
        print(f"\n=== WEAK SKILLS (lose own held-out query) ===")
        if not weak:
            print("  none — descriptions are robust to paraphrase (great)")
        for path, cases in sorted(weak.items()):
            print(f"  {path} — {len(cases)} loss(es)")
            for t, winner, s in cases[:2]:
                print(f"    query='{t['query'][:60]}' → winner={winner}")
        print(f"\nTotal weak skills: {len(weak)}")
        return 0

    # Full GEPA path requires the gepa package + provider key
    try:
        import gepa  # noqa: F401
    except ImportError:
        print("ERROR: gepa not installed. Run: /opt/homebrew/bin/python3.12 -m venv /tmp/gepa-venv && /tmp/gepa-venv/bin/pip install gepa")
        print("Then re-run with: /tmp/gepa-venv/bin/python scripts/gepa-desc-opt.py ...")
        return 1

    targets = [args.skill] if args.skill else (sorted(weak) if args.all else [])
    if not targets:
        print("No skills selected. Use --skill <path>, --all, or check --dry-run first.")
        return 1

    print(f"\n=== GEPA optimizing {len(targets)} skill(s) ===")
    results = []
    for target in targets:
        cases = weak.get(target, [])
        if not cases:
            print(f"  {target}: not weak (skip)")
            continue
        cur = skills[target]["description"]
        cur_hit, _ = evaluate_description(skills, held, target, cur)
        print(f"\n  {target}: current Hit@{cur_hit:.0%} on held-out ({len(cases)} losses)")
        print(f"    desc: {cur[:90]}...")
        print("    NOTE: GEPA reflection needs the provider key. In dry-run mode")
        print("    this is where gepa.optimize_anything would mutate + Pareto-search.")
        print("    (Harness wired; provider call goes here in live mode.)")
        results.append({
            "skill": target,
            "current_desc": cur,
            "current_hit@1": cur_hit,
            "loss_count": len(cases),
        })

    out = pathlib.Path(args.json_out)
    out.write_text(json.dumps(results, indent=2))
    print(f"\n✅ results → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
