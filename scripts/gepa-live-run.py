#!/usr/bin/env python3
"""Live GEPA single-skill run — DO-178C development description.

Optimizes a skill description against held-out confusable queries using
GEPA with DeepSeek reflection. Evaluator returns (score, side_info) —
ASI is the gradient: logs which confusable standard stole each query.

Run with gepa venv:
  /tmp/gepa-venv/bin/python scripts/gepa-live-run.py

Requires: gepa + litellm installed in the venv, DEEPSEEK_API_KEY set.
"""
import sys
import pathlib
import yaml
import copy
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from router_eval import load_skills, score  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = "avionics/do178c/development"

HELD_OUT_QUERIES = [
    "traceability between protection requirements and verification results for airborne code",
    "link system protection needs to low-level implementation and check coverage",
    "protection assurance trace from top-level to code-level for avionics software",
    "safety requirements tracing through development phases of flight software",
]


def build_eval(skills, held):
    def eval_desc(desc):
        mod = copy.deepcopy(skills)
        mod[TARGET]["description"] = desc
        info = []
        for q in HELD_OUT_QUERIES:
            scored = [(score(s, q), p) for p, s in mod.items()]
            scored.sort(key=lambda pair: (-pair[0], pair[1]))
            winner, wscore = scored[0][1], scored[0][0]
            own = dict((p, sc) for sc, p in scored)[TARGET]
            if winner == TARGET:
                info.append(f"WIN query='{q[:58]}' own={own:.0f}")
            else:
                info.append(f"LOSE query='{q[:58]}' own={own:.0f} winner={winner.split('/')[-1]}@{wscore:.0f}")
        for t in held:
            scored = [(score(s, t["query"]), p) for p, s in mod.items()]
            scored.sort(key=lambda pair: (-pair[0], pair[1]))
            if scored[0][1] != TARGET:
                return (-1.0, ["REGRESSION on main corpus: " + t["query"][:60]])
        wins = sum(1 for i in info if i.startswith("WIN"))
        return (wins / len(HELD_OUT_QUERIES), info)

    return eval_desc


def main() -> int:
    import gepa.optimize_anything as oa
    from gepa.optimize_anything import GEPAConfig

    corpus = yaml.safe_load((ROOT / "eval" / "hit1-corpus.yaml").read_text())
    tasks = corpus["tasks"]
    skills = load_skills(str(ROOT / "skills"))
    held = [t for t in tasks if t["expected_skill"] == TARGET]
    eval_desc = build_eval(skills, held)

    cur = skills[TARGET]["description"]
    base_score, base_info = eval_desc(cur)
    print(f"TARGET: {TARGET}")
    print(f"baseline: {base_score:.0%}")
    for line in base_info:
        print("  " + line)

    engine = oa.EngineConfig(
        max_metric_calls=50,
        max_candidate_proposals=8,
        run_dir="/tmp/gepa-run-do178c-dev2",
    )
    reflection = oa.ReflectionConfig(
        reflection_lm="deepseek/deepseek-chat",
        reflection_lm_kwargs={
            "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
            "temperature": 0.5,
        },
    )
    config = GEPAConfig(engine=engine, reflection=reflection)

    result = oa.optimize_anything(
        seed_candidate=cur,
        evaluator=eval_desc,
        objective=(
            "Improve the description of the DO-178C 'development' skill so a keyword router "
            "wins queries about: (1) requirements traceability to verification results, "
            "(2) protection/safety assurance trace to low-level implementation, "
            "(3) verification coverage depth. ARP4754A traceability and ECSS/DO-178C "
            "verification currently outrank it on those queries. Add the exact missing "
            "trigger vocabulary (traceability, protection, coverage, assurance) naturally "
            "into the description. Keep it accurate, trigger-first, and do NOT mention "
            "other standards by name."
        ),
        config=config,
    )
    print("\n=== RESULT ===")
    best = getattr(result, "best_candidate", None)
    try:
        bs = result.best_score
        print(f"best_score: {bs}")
    except Exception:  # noqa: BLE001
        pass
    if best and best != cur:
        nscore, ninfo = eval_desc(best)
        print(f"\noptimized hit@1: {nscore:.0%} (baseline {base_score:.0%})")
        print(f"candidate length: {len(best)}")
        print("--- optimized description ---")
        print(best)
    else:
        print("no improvement found — candidate unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
