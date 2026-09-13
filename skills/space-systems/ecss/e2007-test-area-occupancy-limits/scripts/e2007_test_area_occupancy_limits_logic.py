#!/usr/bin/env python3
"""Occupancy control for a shielded electromagnetic measurement enclosure.

Anchor: ECSS-E-ST-20-07C clause 5.2.5.2 -- only the people and the hardware
the running step actually needs stay inside the enclosure while it runs.
The clause is paraphrased here into an implementable procedure; no
normative text is reproduced.

Two independent reasons drive the rule, and the module keeps them apart:

* safety -- an energized radiating or high-voltage run exposes whoever is
  inside, and an evacuation route has a finite capacity;
* measurement integrity -- every body and every unneeded object inside the
  quiet zone scatters and absorbs the field the measurement depends on, so
  occupancy is also a source of measurement error.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Roles recognised on an occupancy roster.
KNOWN_ROLES = (
    "run-conductor",
    "measurement-engineer",
    "safety-officer",
    "article-operator",
    "quality-witness",
    "observer",
    "visitor",
)

# Roles the enclosure needs for each run mode, before the situational
# additions (in-enclosure commanding, formal witnessing) are applied.
_BASE_ROLES = {
    "radiated-emission": ("run-conductor", "measurement-engineer"),
    "radiated-susceptibility": (
        "run-conductor",
        "measurement-engineer",
        "safety-officer",
    ),
    "conducted-emission": ("run-conductor", "measurement-engineer"),
    "conducted-susceptibility": (
        "run-conductor",
        "measurement-engineer",
        "safety-officer",
    ),
    "enclosure-calibration": ("measurement-engineer",),
}

RUN_MODES = tuple(sorted(_BASE_ROLES))

# Functions a declared item can serve inside the enclosure.
KNOWN_FUNCTIONS = (
    "article-under-verification",
    "support-equipment",
    "measurement-instrument",
    "field-probe",
)

STRAY_ITEM = "stray-item"

# Occupied floor area attributed to one standing person, in square metres.
PERSON_FOOTPRINT_M2 = 0.35

# Fraction of the quiet-zone floor area that occupancy may take up before
# the scattered and absorbed field invalidates the measurement.
PERTURBATION_LIMIT = 0.10

BOUNDARY_REL_TOL = 1e-12
BOUNDARY_ABS_TOL = 1e-15


def _not_above(value, limit):
    """Return True when value <= limit, absorbing representation error.

    A fraction assembled by summing footprints can land a few units in the
    last place above a limit it is physically equal to. That error is
    absorbed here; the perturbation limit itself is never widened.
    """
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL, abs_tol=BOUNDARY_ABS_TOL)


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def necessary_roles(run_mode, in_enclosure_commanding=False, witnessed=False):
    """Roles the enclosure genuinely needs for one run mode.

    An article that must be commanded from inside adds its operator; a
    formally witnessed acceptance run adds the quality witness. Nothing
    else is necessary, so an observer or a visitor can never appear here.
    """
    if run_mode not in _BASE_ROLES:
        raise ValueError(
            "unrecognized run mode %r (expected one of %s)"
            % (run_mode, ", ".join(RUN_MODES))
        )
    if not isinstance(in_enclosure_commanding, bool):
        raise ValueError("in_enclosure_commanding must be a boolean")
    if not isinstance(witnessed, bool):
        raise ValueError("witnessed must be a boolean")
    roles = set(_BASE_ROLES[run_mode])
    if in_enclosure_commanding:
        roles.add("article-operator")
    if witnessed:
        roles.add("quality-witness")
    return frozenset(roles)


def evaluate_personnel(occupants, run_mode, in_enclosure_commanding=False, witnessed=False):
    """Split a roster into essential occupants and occupants to withdraw.

    Each occupant is a mapping with 'badge', 'role' and an optional
    'justification' string. An occupant whose role the run does not need is
    withdrawn; so is an occupant filling a needed role with no run-step
    justification recorded, because the justification is what ties the
    person to the step actually running.
    """
    if not isinstance(occupants, (list, tuple)):
        raise ValueError("occupants must be a list of roster entries")
    needed = necessary_roles(run_mode, in_enclosure_commanding, witnessed)
    seen = set()
    essential = []
    findings = []
    for entry in occupants:
        if not isinstance(entry, dict):
            raise ValueError("each roster entry must be a mapping")
        badge = entry.get("badge")
        if not badge or not isinstance(badge, str):
            raise ValueError("each roster entry needs a non-empty string 'badge'")
        if badge in seen:
            raise ValueError("duplicate badge %r on the roster" % badge)
        seen.add(badge)
        role = entry.get("role")
        if role not in KNOWN_ROLES:
            raise ValueError(
                "unrecognized role %r (expected one of %s)"
                % (role, ", ".join(KNOWN_ROLES))
            )
        if role not in needed:
            findings.append(
                {"badge": badge, "role": role, "finding": "role-not-needed-for-run-mode"}
            )
            continue
        justification = entry.get("justification")
        if not justification or not isinstance(justification, str):
            findings.append(
                {"badge": badge, "role": role, "finding": "no-run-step-justification"}
            )
            continue
        essential.append({"badge": badge, "role": role})
    covered = {item["role"] for item in essential}
    for role in sorted(needed - covered):
        findings.append({"role": role, "finding": "required-role-absent"})
    return {
        "necessary_roles": sorted(needed),
        "essential": essential,
        "findings": findings,
    }


def categorize_item(item):
    """Sort one declared item into the function it serves, or stray.

    An item with an unrecognized function, or with no run-step
    justification, is uncategorized for the run and comes back as stray so
    it is withdrawn before the run starts.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    item_id = item.get("id")
    if not item_id or not isinstance(item_id, str):
        raise ValueError("each item needs a non-empty string 'id'")
    function = item.get("function")
    if function is None:
        return STRAY_ITEM
    if function not in KNOWN_FUNCTIONS:
        raise ValueError(
            "unrecognized item function %r (expected one of %s)"
            % (function, ", ".join(KNOWN_FUNCTIONS))
        )
    justification = item.get("justification")
    if not justification or not isinstance(justification, str):
        return STRAY_ITEM
    return function


def evaluate_hardware(items, require_article=True):
    """Split declared hardware into needed items and items to withdraw.

    A verification run has to contain the article it verifies, so its
    absence is a finding; an enclosure-calibration run has no article and
    passes require_article as False.
    """
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list of hardware entries")
    if not isinstance(require_article, bool):
        raise ValueError("require_article must be a boolean")
    seen = set()
    needed = []
    findings = []
    for item in items:
        function = categorize_item(item)
        item_id = item["id"]
        if item_id in seen:
            raise ValueError("duplicate item id %r" % item_id)
        seen.add(item_id)
        if function == STRAY_ITEM:
            findings.append({"item": item_id, "finding": "unjustified-item-present"})
            continue
        needed.append({"item": item_id, "function": function})
    if require_article and not any(
        item["function"] == "article-under-verification" for item in needed
    ):
        findings.append({"finding": "article-under-verification-absent"})
    return {"needed": needed, "findings": findings}


def quiet_zone_perturbation(occupant_count, items, quiet_zone_area_m2):
    """Fraction of the quiet-zone floor area taken up by occupancy.

    Bodies count at a fixed standing footprint; each item contributes the
    footprint declared against it. Items sitting outside the quiet zone do
    not perturb it and are skipped.
    """
    if isinstance(occupant_count, bool) or not isinstance(occupant_count, int):
        raise ValueError("occupant_count must be an integer")
    if occupant_count < 0:
        raise ValueError("occupant_count must not be negative")
    area = _require_number(quiet_zone_area_m2, "quiet_zone_area_m2")
    if area <= 0.0:
        raise ValueError("quiet_zone_area_m2 must be positive")
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list of hardware entries")
    occupied = occupant_count * PERSON_FOOTPRINT_M2
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each item must be a mapping")
        if not bool(item.get("inside_quiet_zone", True)):
            continue
        footprint = _require_number(item.get("footprint_m2", 0.0), "footprint_m2")
        if footprint < 0.0:
            raise ValueError("footprint_m2 must not be negative")
        occupied += footprint
    return occupied / area


def evaluate_egress_capacity(occupant_count, egress_capacity):
    """Check the surviving headcount against the evacuation-route capacity."""
    if isinstance(occupant_count, bool) or not isinstance(occupant_count, int):
        raise ValueError("occupant_count must be an integer")
    if occupant_count < 0:
        raise ValueError("occupant_count must not be negative")
    if isinstance(egress_capacity, bool) or not isinstance(egress_capacity, int):
        raise ValueError("egress_capacity must be an integer")
    if egress_capacity < 1:
        raise ValueError("egress_capacity must be at least one person")
    findings = []
    if occupant_count > egress_capacity:
        findings.append(
            {
                "finding": "headcount-above-egress-capacity",
                "occupants": occupant_count,
                "capacity": egress_capacity,
            }
        )
    return {"occupants": occupant_count, "capacity": egress_capacity, "findings": findings}


def assess_enclosure_occupancy(plan):
    """Aggregate the clause 5.2.5.2 verdict for one run step.

    'plan' carries 'run_mode', 'occupants', 'items', 'quiet_zone_area_m2',
    'egress_capacity' and the optional 'in_enclosure_commanding' and
    'witnessed' flags. The step is clear to run only when personnel,
    hardware, egress and perturbation each return no finding.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    required = ("run_mode", "occupants", "items", "quiet_zone_area_m2", "egress_capacity")
    for key in required:
        if key not in plan:
            raise ValueError("plan is missing required key %r" % key)
    personnel = evaluate_personnel(
        plan["occupants"],
        plan["run_mode"],
        bool(plan.get("in_enclosure_commanding", False)),
        bool(plan.get("witnessed", False)),
    )
    hardware = evaluate_hardware(
        plan["items"], plan["run_mode"] != "enclosure-calibration"
    )
    headcount = len(personnel["essential"])
    egress = evaluate_egress_capacity(headcount, plan["egress_capacity"])
    retained = [
        item
        for item in plan["items"]
        if isinstance(item, dict)
        and item.get("id") in {entry["item"] for entry in hardware["needed"]}
    ]
    fraction = quiet_zone_perturbation(headcount, retained, plan["quiet_zone_area_m2"])
    perturbation_findings = []
    if not _not_above(fraction, PERTURBATION_LIMIT):
        perturbation_findings.append(
            {
                "finding": "quiet-zone-perturbation-above-allowance",
                "fraction": fraction,
                "allowance": PERTURBATION_LIMIT,
            }
        )
    findings = (
        personnel["findings"]
        + hardware["findings"]
        + egress["findings"]
        + perturbation_findings
    )
    return {
        "personnel": personnel,
        "hardware": hardware,
        "egress": egress,
        "perturbation_fraction": fraction,
        "findings": findings,
        "clear_to_run": not findings,
    }
