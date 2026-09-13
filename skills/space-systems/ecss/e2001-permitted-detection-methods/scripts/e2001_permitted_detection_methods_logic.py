#!/usr/bin/env python3
"""Permitted multipactor-detection technique logic (ECSS-E-ST-20-01C 7.2).

Deterministic, offline, stdlib-only helpers that turn the clause 7.2
catalogue of global and local multipactor-detection techniques into the
subset a given facility and RF-item actually permit, and assemble a
suite from that subset:

- resolve a declared technique-name onto its catalogue entry,
- reject a technique whose facility-capabilities are missing,
- reject a technique the item's hardware conditions block,
- reject an intermodulation-technique under single-carrier-drive,
- select the fastest permitted primary technique per coverage-scope and
  hold the suite inside its latency-budget.

Anchor: ECSS-E-ST-20-01C clause 7.2 (paraphrased procedure only).
"""

import math

REL_TOL = 1e-9
ABS_TOL = 1e-12

DRIVE_MODES = {
    "single-carrier": "single-carrier-drive",
    "single-carrier-drive": "single-carrier-drive",
    "multi-carrier": "multi-carrier-drive",
    "multi-carrier-drive": "multi-carrier-drive",
    "multicarrier": "multi-carrier-drive",
}

COVERAGE_SCOPES = ("global-coverage", "local-coverage")

# Catalogue entry fields:
#   coverage     - global-coverage | local-coverage
#   family       - observable-family watched by the technique
#   needs        - facility-capabilities required to run it
#   blocked_by   - item conditions that physically defeat it
#   latency_ms   - nominal detection-latency
#   role         - primary (may fill a coverage-scope) | corroborating
#   drive_modes  - drive-modes under which the observable exists
CATALOGUE = {
    "forward-reflected-nulling": {
        "coverage": "global-coverage",
        "family": "rf-power-balance",
        "needs": ("nulling-bridge", "phase-stable-reference"),
        "blocked_by": ("isolator-masks-reflection",),
        "latency_ms": 0.05,
        "role": "primary",
        "drive_modes": ("single-carrier-drive", "multi-carrier-drive"),
    },
    "harmonic-rise": {
        "coverage": "global-coverage",
        "family": "spectral-harmonic",
        "needs": ("harmonic-receiver", "harmonic-transparent-output"),
        "blocked_by": ("output-filter-attenuates-harmonics",),
        "latency_ms": 0.2,
        "role": "primary",
        "drive_modes": ("single-carrier-drive", "multi-carrier-drive"),
    },
    "intermodulation-rise": {
        "coverage": "global-coverage",
        "family": "spectral-sideband",
        "needs": ("spectrum-receiver", "low-residual-intermodulation-chain"),
        "blocked_by": ("passive-intermodulation-floor-high",),
        "latency_ms": 0.5,
        "role": "primary",
        "drive_modes": ("multi-carrier-drive",),
    },
    "close-to-carrier-noise-rise": {
        "coverage": "global-coverage",
        "family": "spectral-sideband",
        "needs": ("spectrum-receiver", "low-phase-noise-source"),
        "blocked_by": ("noisy-drive-source",),
        "latency_ms": 0.4,
        "role": "primary",
        "drive_modes": ("single-carrier-drive", "multi-carrier-drive"),
    },
    "electron-probe-current": {
        "coverage": "local-coverage",
        "family": "charged-particle",
        "needs": ("biased-probe", "probe-feedthrough"),
        "blocked_by": ("sealed-region", "no-probe-access"),
        "latency_ms": 0.02,
        "role": "primary",
        "drive_modes": ("single-carrier-drive", "multi-carrier-drive"),
    },
    "optical-emission": {
        "coverage": "local-coverage",
        "family": "optical-emission",
        "needs": ("photodetector", "darkened-chamber"),
        "blocked_by": ("no-optical-view", "sealed-region"),
        "latency_ms": 0.03,
        "role": "primary",
        "drive_modes": ("single-carrier-drive", "multi-carrier-drive"),
    },
    "gas-pressure-rise": {
        "coverage": "local-coverage",
        "family": "gas-pressure",
        "needs": ("fast-vacuum-gauge", "vented-region"),
        "blocked_by": ("sealed-region",),
        "latency_ms": 8.0,
        "role": "primary",
        "drive_modes": ("single-carrier-drive", "multi-carrier-drive"),
    },
    "calorimetric-thermal-rise": {
        "coverage": "local-coverage",
        "family": "thermal-rise",
        "needs": ("temperature-sensor",),
        "blocked_by": (),
        "latency_ms": 5000.0,
        "role": "corroborating",
        "drive_modes": ("single-carrier-drive", "multi-carrier-drive"),
    },
}

ALIASES = {
    "nulling": "forward-reflected-nulling",
    "forward-reflected-power-nulling": "forward-reflected-nulling",
    "power-nulling": "forward-reflected-nulling",
    "harmonics": "harmonic-rise",
    "harmonic-detection": "harmonic-rise",
    "third-order-intermodulation": "intermodulation-rise",
    "intermodulation": "intermodulation-rise",
    "close-to-carrier-noise": "close-to-carrier-noise-rise",
    "phase-noise-rise": "close-to-carrier-noise-rise",
    "electron-probe": "electron-probe-current",
    "probe-current": "electron-probe-current",
    "optical-detection": "optical-emission",
    "light-emission": "optical-emission",
    "pressure-rise": "gas-pressure-rise",
    "outgassing-pressure-rise": "gas-pressure-rise",
    "calorimetric": "calorimetric-thermal-rise",
    "thermal-rise": "calorimetric-thermal-rise",
}


def _within(value, limit):
    """True when value <= limit, absorbing float summation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def canonical_technique(name):
    """Resolve a declared technique-name onto its catalogue key.

    Raises ValueError for an unrecognized name - an unknown technique
    has no coverage-scope and cannot be graded.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("technique name must be a non-empty string, got %r" % (name,))
    key = name.strip().lower()
    if key in CATALOGUE:
        return key
    if key in ALIASES:
        return ALIASES[key]
    raise ValueError("unrecognized multipactor-detection technique %r" % (name,))


def technique_record(name):
    """Return a copy of the catalogue entry for a declared technique."""
    key = canonical_technique(name)
    entry = dict(CATALOGUE[key])
    entry["technique"] = key
    return entry


def normalize_drive_mode(mode):
    """Resolve a declared drive-mode; raises ValueError on an unknown one."""
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("drive-mode must be a non-empty string, got %r" % (mode,))
    key = mode.strip().lower()
    if key not in DRIVE_MODES:
        raise ValueError("unrecognized drive-mode %r" % (mode,))
    return DRIVE_MODES[key]


def techniques_by_coverage(scope):
    """Catalogue keys of one coverage-scope, sorted for determinism."""
    if scope not in COVERAGE_SCOPES:
        raise ValueError("unrecognized coverage-scope %r" % (scope,))
    return sorted(k for k, v in CATALOGUE.items() if v["coverage"] == scope)


def _as_token_set(values, field):
    if values is None:
        return frozenset()
    if isinstance(values, str) or not hasattr(values, "__iter__"):
        raise ValueError("%s must be an iterable of tokens, got %r" % (field, values))
    tokens = set()
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("%s entries must be non-empty strings, got %r" % (field, item))
        tokens.add(item.strip().lower())
    return frozenset(tokens)


def unmet_prerequisites(name, facility_capabilities):
    """Facility-capabilities a technique needs and the facility lacks."""
    entry = technique_record(name)
    have = _as_token_set(facility_capabilities, "facility_capabilities")
    return sorted(set(entry["needs"]) - have)


def blocking_conditions(name, item_conditions):
    """Item conditions present that physically defeat the technique."""
    entry = technique_record(name)
    present = _as_token_set(item_conditions, "item_conditions")
    return sorted(set(entry["blocked_by"]) & present)


def evaluate_technique(name, facility_capabilities, item_conditions, drive_mode):
    """Decide whether one technique is permitted, with the reasons."""
    entry = technique_record(name)
    mode = normalize_drive_mode(drive_mode)
    reasons = []
    missing = unmet_prerequisites(name, facility_capabilities)
    if missing:
        reasons.append("unmet facility-capability: %s" % ", ".join(missing))
    blockers = blocking_conditions(name, item_conditions)
    if blockers:
        reasons.append("blocked by item condition: %s" % ", ".join(blockers))
    if mode not in entry["drive_modes"]:
        reasons.append("observable absent under %s" % mode)
    return {
        "technique": entry["technique"],
        "coverage": entry["coverage"],
        "family": entry["family"],
        "role": entry["role"],
        "latency_ms": entry["latency_ms"],
        "permitted": not reasons,
        "reasons": reasons,
    }


def permitted_catalogue(candidates, facility_capabilities, item_conditions, drive_mode):
    """Evaluate every candidate technique; ordered by latency then name."""
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("candidate technique list must be non-empty")
    evaluated = [
        evaluate_technique(name, facility_capabilities, item_conditions, drive_mode)
        for name in candidates
    ]
    seen = set()
    for item in evaluated:
        if item["technique"] in seen:
            raise ValueError("duplicate technique %r in candidate list" % item["technique"])
        seen.add(item["technique"])
    evaluated.sort(key=lambda r: (r["latency_ms"], r["technique"]))
    return evaluated


def select_detection_suite(
    candidates,
    facility_capabilities,
    item_conditions,
    drive_mode,
    latency_budget_ms,
):
    """Assemble the permitted suite: fastest primary technique per scope.

    Returns a report dict with the selection, the rejected candidates
    and their reasons, the summed latency and the findings. permitted
    is True only when findings is empty.
    """
    budget = latency_budget_ms
    if isinstance(budget, bool) or not isinstance(budget, (int, float)):
        raise ValueError("latency_budget_ms must be a real number, got %r" % (budget,))
    budget = float(budget)
    if not math.isfinite(budget) or budget <= 0.0:
        raise ValueError("latency_budget_ms must be finite and > 0, got %r" % (budget,))
    evaluated = permitted_catalogue(
        candidates, facility_capabilities, item_conditions, drive_mode
    )
    selection = {}
    corroborating = []
    for item in evaluated:
        if not item["permitted"]:
            continue
        if item["role"] == "corroborating":
            corroborating.append(item["technique"])
            continue
        if item["coverage"] not in selection:
            selection[item["coverage"]] = item
    findings = []
    for scope in COVERAGE_SCOPES:
        if scope not in selection:
            findings.append("no permitted primary technique for %s" % scope)
    total_latency = sum(item["latency_ms"] for item in selection.values())
    if not _within(total_latency, budget):
        findings.append(
            "suite latency %.4f ms exceeds latency-budget %.4f ms"
            % (total_latency, budget)
        )
    rejected = [
        {"technique": r["technique"], "reasons": list(r["reasons"])}
        for r in evaluated
        if not r["permitted"]
    ]
    return {
        "evaluated": evaluated,
        "selection": {k: v["technique"] for k, v in sorted(selection.items())},
        "selected_records": [selection[k] for k in sorted(selection)],
        "corroborating": sorted(corroborating),
        "rejected": rejected,
        "total_latency_ms": total_latency,
        "latency_budget_ms": budget,
        "findings": findings,
        "permitted": not findings,
    }


def format_suite_report(report):
    """Render a suite selection as deterministic plain-text lines."""
    lines = [
        "permitted detection suite: %s"
        % ("PERMITTED" if report["permitted"] else "NOT PERMITTED"),
        "latency %.4f ms of %.4f ms budget"
        % (report["total_latency_ms"], report["latency_budget_ms"]),
    ]
    for scope, technique in report["selection"].items():
        lines.append("  %s <- %s" % (scope, technique))
    for item in report["rejected"]:
        lines.append("  REJECTED %s: %s" % (item["technique"], "; ".join(item["reasons"])))
    for finding in report["findings"]:
        lines.append("  FINDING: %s" % finding)
    return "\n".join(lines)
