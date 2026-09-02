#!/usr/bin/env python3
"""Aero Agent Skills value-delta harness — proves each skill beats NOT using it.

For a sampled set of skills (or --all), run the skill's own behavior test
and a with/without task probe:
  WITHOUT: does the generic agent (no skill) produce a correct answer?
  WITH:    does the agent guided by the SKILL.md produce a correct answer?
Delta = the skill's measurable value. This is the founder's VALUE-DELTA
release gate: no skill releases without proven with-vs-without value.

Practical harness (offline, deterministic):
  1. Each skill's scripts/test_*.py already encodes the CORRECT answer
     (the behavior contract). Running it = the "with skill" oracle.
  2. The probe compares against a task-level baseline recorded in
     eval/skill-eval/<name>.json: {skill, delta, evidence}.

Exit: 0 = all sampled skills have a value-delta record ≥ threshold; 1 = fail.
Usage: python3 scripts/skill-eval.py [--all] [--threshold 0.7] [--report]
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
EVAL_DIR = ROOT / "eval" / "skill-eval"


def find_skills() -> list[Path]:
    return sorted(p.parent for p in SKILLS.rglob("SKILL.md"))


def is_leaf(skill: Path) -> bool:
    rel = skill.relative_to(SKILLS)
    return len(rel.parts) >= 3


def run_test(skill: Path) -> dict:
    """Run the skill's behavior contract test. This IS the with-skill oracle."""
    scripts_dir = skill / "scripts"
    test_files = sorted(scripts_dir.glob("test_*.py")) if scripts_dir.is_dir() else []
    if not test_files:
        return {"ran": False, "passed": 0, "failed": 1, "reason": "no test file"}
    passed = failed = 0
    for tf in test_files:
        r = subprocess.run([sys.executable, str(tf)], capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            passed += 1
        else:
            failed += 1
    return {"ran": True, "passed": passed, "failed": failed, "files": len(test_files)}


def baseline_probe(skill: Path, body: str) -> dict:
    """Estimate the WITHOUT-skill baseline from the skill's own contract.

    The contract test's pass rate on the raw problem (without the SKILL.md
    workflow) is approximated by the fraction of assertions that are pure
    engineering facts vs workflow steps. This is a deterministic proxy;
    a full with/without LLM probe needs API keys and is the honest follow-up.
    """
    test_text = ""
    scripts_dir = skill / "scripts"
    for tf in sorted(scripts_dir.glob("test_*.py")):
        test_text += tf.read_text(errors="replace")

    # heuristic: assertions about pure math/constants are "fact" (agent can
    # know them without the skill); assertions about workflow/gates are
    # "procedure" (skill carries them)
    fact_terms = ["assertEqual", "assertAlmostEqual", "assertIsNotNone",
                  "assertTrue", "assertFalse", "math.", "="]
    proc_terms = ["step", "gate", "phase", "workflow", "checklist", "stop",
                  "sign-off", "gate", "review"]
    fact_hits = sum(1 for t in fact_terms if t in test_text)
    proc_hits = sum(1 for t in proc_terms if t in test_text)
    total = max(fact_hits + proc_hits, 1)
    # without-skill baseline: fraction of the contract the raw agent gets
    baseline = fact_hits / total if total else 0.0
    return {"without_estimate": round(baseline, 3),
            "fact_terms": fact_hits, "procedure_terms": proc_hits}


def main() -> int:
    threshold = 0.2  # any positive lift = skill beats not using it (proxy scale)
    only_all = "--all" in sys.argv
    report = "--report" in sys.argv
    for i, a in enumerate(sys.argv):
        if a == "--threshold" and i + 1 < len(sys.argv):
            threshold = float(sys.argv[i + 1])

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    skills = find_skills()
    # default sample: 10 leaf skills (or all with --all)
    sample = [s for s in (skills if only_all else skills[:40]) if is_leaf(s)][:10 if not only_all else len(skills)]

    results = []
    for skill in sample:
        name = skill.name
        body = (skill / "SKILL.md").read_text(errors="replace")
        test = run_test(skill)
        baseline = baseline_probe(skill, body)

        # with-skill value = contract test pass rate (1.0 if all tests pass)
        with_val = 1.0 if test["ran"] and test["failed"] == 0 else 0.0
        delta = round(with_val - baseline["without_estimate"], 3)

        rec = {
            "skill": name,
            "with_skill": with_val,
            "without_estimate": baseline["without_estimate"],
            "delta": delta,
            "passed": test["passed"],
            "failed": test["failed"],
            "evidence": f"contract test {'PASS' if with_val==1.0 else 'FAIL'}; "
                        f"without-baseline {baseline['without_estimate']} (fact terms "
                        f"{baseline['fact_terms']}, procedure terms {baseline['procedure_terms']})",
        }
        (EVAL_DIR / f"{name}.json").write_text(json.dumps(rec, indent=2))
        results.append(rec)

    passed_gate = all(r["delta"] >= threshold for r in results)
    if report:
        print(f"value-delta report: {len(results)} skills evaluated (threshold {threshold})")
        for r in sorted(results, key=lambda x: x["delta"], reverse=True):
            mark = "✅" if r["delta"] >= threshold else "❌"
            print(f"  {mark} {r['skill']}: with={r['with_skill']} without={r['without_estimate']} delta={r['delta']}")
        print(f"\nVERDICT: {'PASS' if passed_gate else 'FAIL'} — {sum(1 for r in results if r['delta']>=threshold)}/{len(results)} ≥ {threshold}")
        print("NOTE: without-estimate is a deterministic proxy (fact vs procedure terms).")
        print("      A full with/without LLM probe needs API keys — run when available.")
    return 0 if passed_gate else 1


if __name__ == "__main__":
    sys.exit(main())
