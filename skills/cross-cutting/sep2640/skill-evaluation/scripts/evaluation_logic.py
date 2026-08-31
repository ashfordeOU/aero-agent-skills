#!/usr/bin/env python3
"""SEP-2640-style skill evaluation logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, sep-2640: gated false,
open specification): SEP-2640 is the MCP working group's Skills
Extension draft; the agentskills.io SKILL.md format stays the
canonical content form and SEP-2640 is an adapter for discovery and
delivery, emerging and not yet stable. Evaluating a delivered skill
therefore targets the stable conformance surface (frontmatter,
description with trigger, license, standards references), the
behavioral contract test, deterministic quality criteria, coverage,
and an acceptance verdict. Everything here is deterministic and
offline; stdlib only.
"""

import re

# Conservative allowlist of common stdlib modules. A module outside
# this list scores as non-stdlib; deterministic by construction.
STDLIB_MODULES = {
    "argparse", "collections", "csv", "dataclasses", "datetime",
    "decimal", "fractions", "functools", "itertools", "json", "math",
    "os", "pathlib", "random", "re", "statistics", "string", "struct",
    "sys", "time", "typing", "unittest",
}

REQUIRED_CHECKS = (
    "frontmatter_present",
    "name_kebab_case",
    "name_matches_folder",
    "description_has_trigger",
    "license_apache",
    "standards_referenced",
    "skill_md_present",
)


def _kebab(name):
    return bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name or ""))


def run_conformance_checks(package):
    """Run the conformance checks on a delivered skill package.

    package is a dict with keys: folder_name (leaf folder name), name,
    description, license, standards (frontmatter values), and files
    (list of files present in the package). Returns a dict mapping
    check name -> bool (True = pass).
    """
    if not isinstance(package, dict):
        raise ValueError("package must be a dict")
    folder = package.get("folder_name")
    name = package.get("name")
    description = package.get("description")
    license_ = package.get("license")
    standards = package.get("standards")
    files = package.get("files") or []

    checks = {
        "frontmatter_present": bool(
            folder and name and description and license_ and standards is not None
        ),
        "name_kebab_case": _kebab(name),
        "name_matches_folder": bool(folder and name == folder),
        "description_has_trigger": "Trigger:" in (description or ""),
        "license_apache": license_ == "Apache-2.0",
        "standards_referenced": bool(standards),
        "skill_md_present": "SKILL.md" in set(files),
    }
    return checks


def conformance_verdict(checks):
    """Combine individual check results into a verdict dict.

    Returns {"checks": {name: bool}, "conformant": bool, "failed":
    [names of failing checks]}. Fails the package when any check
    fails.
    """
    if not isinstance(checks, dict) or not checks:
        raise ValueError("checks must be a non-empty dict of name -> bool")
    for check_name, passed in checks.items():
        if not isinstance(passed, bool):
            raise ValueError("check %r result must be bool" % (check_name,))
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "checks": dict(checks),
        "conformant": not failed,
        "failed": failed,
    }


def weighted_score(scores, weights):
    """Weighted mean of quality scores, each 0.0-1.0.

    weights must cover exactly the same keys as scores and sum to
    1.0. Returns the weighted total in 0.0-1.0.
    """
    if not isinstance(scores, dict) or not scores:
        raise ValueError("scores must be a non-empty dict")
    if not isinstance(weights, dict):
        raise ValueError("weights must be a dict")
    if set(scores) != set(weights):
        raise ValueError("scores and weights must have the same keys")
    for value in scores.values():
        if not isinstance(value, (int, float)) or not (0.0 <= value <= 1.0):
            raise ValueError("each score must be a number in 0.0-1.0")
    for value in weights.values():
        if not isinstance(value, (int, float)) or value < 0.0:
            raise ValueError("each weight must be a non-negative number")
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("weights must sum to 1.0")
    return sum(scores[key] * weights[key] for key in scores)


def stdlib_only(imports):
    """Quality score: 1.0 when every import is stdlib, else 0.0.

    Uses a conservative stdlib allowlist; unknown modules count as
    non-stdlib.
    """
    if imports is None:
        raise ValueError("imports must be a list of module names")
    if not all(isinstance(m, str) for m in imports):
        raise ValueError("each import must be a module name string")
    return 1.0 if set(imports) <= STDLIB_MODULES else 0.0


def contract_score(calls_core):
    """Quality score for the behavioral contract: 1.0 when the
    contract test exercises the core logic, else 0.0."""
    if not isinstance(calls_core, bool):
        raise ValueError("calls_core must be bool")
    return 1.0 if calls_core else 0.0


def coverage_ratio(tested, total):
    """Ratio of tested behaviors to total behaviors, in 0.0-1.0."""
    if not isinstance(tested, int) or not isinstance(total, int):
        raise ValueError("tested and total must be integers")
    if tested < 0 or total <= 0:
        raise ValueError("require tested >= 0 and total > 0")
    if tested > total:
        raise ValueError("tested cannot exceed total")
    return tested / total


def acceptance_verdict(score, threshold):
    """Map a weighted score to accept/rework/reject.

    threshold is an (accept_threshold, rework_threshold) pair with
    0 <= rework <= accept <= 1. score >= accept -> accept;
    score >= rework -> rework; otherwise reject.
    """
    if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
        raise ValueError("score must be a number in 0.0-1.0")
    try:
        accept_t, rework_t = threshold
    except (TypeError, ValueError):
        raise ValueError("threshold must be an (accept, rework) pair")
    if not all(isinstance(t, (int, float)) for t in (accept_t, rework_t)):
        raise ValueError("threshold values must be numbers")
    if not (0.0 <= rework_t <= accept_t <= 1.0):
        raise ValueError("require 0 <= rework <= accept <= 1")
    if score >= accept_t:
        return "accept"
    if score >= rework_t:
        return "rework"
    return "reject"
