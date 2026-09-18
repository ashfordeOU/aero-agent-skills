#!/usr/bin/env python3
"""Build records and traceability for additive manufacturing.

Anchor: ECSS-Q-ST-70-80C, Records. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A build record is the only surviving evidence that a part was made the
way the qualification says it was made. It has to answer four questions
years after the machine has been re-tooled:

    what was run        machine, parameter set, layer thickness,
                        atmosphere, scan strategy, build layout
    what it was made of powder lot identities and the blend, including
                        how many times each contribution has been
                        through a machine already
    what came out       inspection results, witness coupon results,
                        non-conformances raised and their disposition
    who says so         operator, approver, and the references that
                        carry each of the above to a retrievable
                        document

The two failure modes this module separates are a field nobody filled
in and a field somebody filled in with nothing. A missing field is an
open record; a blank field is a record that looks closed and is not.
Neither is a pass, and neither is a zero.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_CLASSES = ("class-a", "class-b", "class-c")

PRESENT = "present"
BLANK = "blank"
MISSING = "missing"

CORE_RECORD_FIELDS = (
    "build_id",
    "machine_id",
    "parameter_set_id",
    "layer_thickness_mm",
    "build_atmosphere",
    "powder_lots",
    "build_layout_id",
    "operator_id",
    "inspection_result_ref",
)

DEFAULT_RECORD_POLICY = {
    "extra_fields": {
        "class-a": (
            "witness_coupon_ref",
            "thermal_post_process_ref",
            "non_conformance_ref",
            "approver_id",
            "scan_strategy_id",
        ),
        "class-b": (
            "witness_coupon_ref",
            "thermal_post_process_ref",
            "approver_id",
        ),
        "class-c": (),
    },
    "traceable_fields": (
        "inspection_result_ref",
        "witness_coupon_ref",
        "thermal_post_process_ref",
        "non_conformance_ref",
    ),
    "min_virgin_mass_fraction": {
        "class-a": 0.5,
        "class-b": 0.3,
        "class-c": 0.0,
    },
    "max_reuse_generation": {"class-a": 3, "class-b": 6, "class-c": 12},
    "retention_years": {"class-a": 20, "class-b": 15, "class-c": 10},
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_record_policy(policy):
    """Check a records policy covers every part class coherently."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    extra = policy.get("extra_fields")
    if not isinstance(extra, dict):
        raise ValueError("policy extra_fields must be a mapping")
    for part_class in PART_CLASSES:
        if not isinstance(extra.get(part_class), (list, tuple)):
            raise ValueError("policy extra_fields is missing %s" % part_class)
    if not isinstance(policy.get("traceable_fields"), (list, tuple)):
        raise ValueError("policy traceable_fields must be a sequence")
    virgin = policy.get("min_virgin_mass_fraction")
    if not isinstance(virgin, dict):
        raise ValueError("policy min_virgin_mass_fraction must be a mapping")
    generations = policy.get("max_reuse_generation")
    if not isinstance(generations, dict):
        raise ValueError("policy max_reuse_generation must be a mapping")
    retention = policy.get("retention_years")
    if not isinstance(retention, dict):
        raise ValueError("policy retention_years must be a mapping")
    for part_class in PART_CLASSES:
        if part_class not in virgin:
            raise ValueError("policy min_virgin_mass_fraction is missing %s" % part_class)
        _require_fraction(
            "min_virgin_mass_fraction[%s]" % part_class, virgin[part_class]
        )
        if part_class not in generations:
            raise ValueError("policy max_reuse_generation is missing %s" % part_class)
        _require_count(
            "max_reuse_generation[%s]" % part_class, generations[part_class], 0
        )
        if part_class not in retention:
            raise ValueError("policy retention_years is missing %s" % part_class)
        _require_count("retention_years[%s]" % part_class, retention[part_class], 1)
    return policy


def required_fields(part_class, policy=None):
    """Fields a build record of this class has to carry."""
    policy = DEFAULT_RECORD_POLICY if policy is None else policy
    validate_record_policy(policy)
    _require_choice("part_class", part_class, PART_CLASSES)
    return tuple(CORE_RECORD_FIELDS) + tuple(policy["extra_fields"][part_class])


def _field_state(value):
    if value is None:
        return BLANK
    if isinstance(value, str):
        return BLANK if not value.strip() else PRESENT
    if isinstance(value, (list, tuple, dict, set)):
        return BLANK if len(value) == 0 else PRESENT
    return PRESENT


def field_status(record, part_class, policy=None):
    """Sort every required field into present, blank or missing.

    A key that is absent and a key that is present with nothing in it
    are different defects: the first is an open record, the second is a
    record that looks closed. Neither is treated as a value.
    """
    policy = DEFAULT_RECORD_POLICY if policy is None else policy
    validate_record_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    needed = required_fields(part_class, policy)
    status = {}
    for field in needed:
        if field not in record:
            status[field] = MISSING
        else:
            status[field] = _field_state(record[field])
    return status


def completeness_score(status):
    """Share of the required fields that actually carry a value."""
    if not isinstance(status, dict) or not status:
        raise ValueError("status must be a non-empty mapping")
    present = sum(1 for state in status.values() if state == PRESENT)
    return present / float(len(status))


def powder_blend(contributions):
    """Virgin share and reuse generations of the powder actually loaded.

    Each contribution carries a mass and the number of builds it has
    already been through. Virgin powder is generation zero; anything
    else has been sieved back from a previous build and has a history.
    """
    if not isinstance(contributions, (list, tuple)) or not contributions:
        raise ValueError("contributions must be a non-empty sequence")
    total_mass = 0.0
    virgin_mass = 0.0
    weighted = 0.0
    highest = 0
    lots = []
    for entry in contributions:
        if not isinstance(entry, dict):
            raise ValueError("each contribution must be a mapping, got %r" % (entry,))
        lot = entry.get("lot_id")
        if not isinstance(lot, str) or not lot.strip():
            raise ValueError("every powder contribution needs a lot_id")
        mass = _require_positive("mass_kg", entry.get("mass_kg"))
        generation = _require_count("reuse_generation", entry.get("reuse_generation"), 0)
        total_mass += mass
        weighted += mass * generation
        if generation == 0:
            virgin_mass += mass
        highest = max(highest, generation)
        lots.append(lot)
    if len(set(lots)) != len(lots):
        raise ValueError("the same powder lot is listed twice in one blend")
    return {
        "lots": lots,
        "total_mass_kg": total_mass,
        "virgin_mass_fraction": virgin_mass / total_mass,
        "mean_reuse_generation": weighted / total_mass,
        "max_reuse_generation": highest,
    }


def blend_acceptable(blend, part_class, policy=None):
    """Whether a powder blend meets the limits this class sets."""
    policy = DEFAULT_RECORD_POLICY if policy is None else policy
    validate_record_policy(policy)
    _require_choice("part_class", part_class, PART_CLASSES)
    if not isinstance(blend, dict):
        raise ValueError("blend must be a mapping, got %r" % (blend,))
    virgin = _require_fraction(
        "virgin_mass_fraction", blend.get("virgin_mass_fraction")
    )
    generation = _require_count(
        "max_reuse_generation", blend.get("max_reuse_generation"), 0
    )
    findings = []
    virgin_limit = policy["min_virgin_mass_fraction"][part_class]
    generation_limit = policy["max_reuse_generation"][part_class]
    if not _at_least(virgin, virgin_limit):
        findings.append(
            "virgin powder is %.1f%% of the blend against the %.1f%% a %s part "
            "needs" % (100.0 * virgin, 100.0 * virgin_limit, part_class)
        )
    if not _at_most(generation, generation_limit):
        findings.append(
            "powder at reuse generation %d against the %d a %s part allows"
            % (generation, generation_limit, part_class)
        )
    return {"acceptable": not findings, "findings": findings}


def traceability_gaps(record, document_index, policy=None):
    """References in the record that no retrievable document answers."""
    policy = DEFAULT_RECORD_POLICY if policy is None else policy
    validate_record_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    if not isinstance(document_index, (list, tuple, set, dict)):
        raise ValueError("document_index must be a collection, got %r" % (document_index,))
    known = set(document_index)
    gaps = []
    for field in policy["traceable_fields"]:
        value = record.get(field)
        if _field_state(value) != PRESENT:
            continue
        references = value if isinstance(value, (list, tuple)) else [value]
        for reference in references:
            if not isinstance(reference, str) or not reference.strip():
                raise ValueError("%s carries a reference that is not a name" % field)
            if reference not in known:
                gaps.append({"field": field, "reference": reference})
    return gaps


def retention_status(years_held, part_class, policy=None):
    """Whether the record has been held as long as the class requires."""
    policy = DEFAULT_RECORD_POLICY if policy is None else policy
    validate_record_policy(policy)
    _require_choice("part_class", part_class, PART_CLASSES)
    held = _require_count("years_held", years_held, 0)
    required = policy["retention_years"][part_class]
    return {
        "years_held": held,
        "years_required": required,
        "years_remaining": max(0, required - held),
        "disposable": held >= required,
    }


def audit_build_record(case, policy=None):
    """Full records verdict for one build."""
    policy = DEFAULT_RECORD_POLICY if policy is None else policy
    validate_record_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    part_class = _require_choice("part_class", case.get("part_class"), PART_CLASSES)
    record = case.get("record")
    if not isinstance(record, dict):
        raise ValueError("case record must be a mapping")
    status = field_status(record, part_class, policy)
    score = completeness_score(status)
    missing = sorted(f for f, state in status.items() if state == MISSING)
    blank = sorted(f for f, state in status.items() if state == BLANK)
    findings = []
    for field in missing:
        findings.append("%s is absent from the record; the build is not closed" % field)
    for field in blank:
        findings.append(
            "%s is present but carries nothing; a blank field is not a value" % field
        )
    blend = None
    blend_result = None
    if _field_state(record.get("powder_lots")) == PRESENT:
        blend = powder_blend(record["powder_lots"])
        blend_result = blend_acceptable(blend, part_class, policy)
        findings.extend(blend_result["findings"])
    gaps = traceability_gaps(record, case.get("document_index", ()), policy)
    for gap in gaps:
        findings.append(
            "%s points at %s, which no retrievable document answers"
            % (gap["field"], gap["reference"])
        )
    retention = retention_status(case.get("years_held", 0), part_class, policy)
    traceable = not missing and not blank and not gaps
    material_ok = blend_result is not None and blend_result["acceptable"]
    if not traceable:
        verdict = "record-incomplete"
    elif not material_ok:
        verdict = "material-history-unacceptable"
    else:
        verdict = "record-complete-and-traceable"
    return {
        "part_class": part_class,
        "field_status": status,
        "completeness": score,
        "missing_fields": missing,
        "blank_fields": blank,
        "powder_blend": blend,
        "traceability_gaps": gaps,
        "retention": retention,
        "complete": verdict == "record-complete-and-traceable",
        "verdict": verdict,
        "findings": findings,
    }
