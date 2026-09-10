#!/usr/bin/env python3
"""ECSS-E-ST-10-03C clause 5.2 equipment qualification test baseline
logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
qualification test baseline for equipment is a fixed catalogue of test
families run in a defined sequence, tailored to the equipment by Table
5-1, with functional/performance checks bracketing the environmental
exposures. Table 5-2 derives each applicable test's qualification
level and duration from its reference level/duration by applying a
margin and a duration factor. This module implements the family
applicability selection, the baseline sequence, and the level/duration
derivation; it does not implement the per-family numeric rules for
mechanical, pressure, thermal, electrical, or mission-specific tests
(see the sibling e1003-eq-mechanical / e1003-eq-pressure /
e1003-eq-thermal / e1003-eq-electrical / e1003-eq-mission leaves) or
the acceptance/protoflight baselines (see e1003-eq-acceptance /
e1003-eq-protoflight).
"""

ENVIRONMENTAL_ORDER = ("mechanical", "pressure_integrity", "thermal", "electrical")
LEVEL_FAMILIES = frozenset(ENVIRONMENTAL_ORDER) | {"mission_specific"}
MARGIN_MODES = ("multiplicative", "additive")


def select_applicable_families(equipment):
    """Table 5-1 applicability for one equipment dict. Required keys:
    has_mechanical_loads, is_pressurized, has_electronics,
    has_mission_specific_test (bools). physical_properties,
    functional_performance, and thermal are always applicable; the
    remaining families are enabled by the matching attribute. Returns a
    new list, in catalogue order (not yet the run sequence)."""
    applicable = ["physical_properties", "functional_performance", "thermal"]
    if equipment["has_mechanical_loads"]:
        applicable.append("mechanical")
    if equipment["is_pressurized"]:
        applicable.append("pressure_integrity")
    if equipment["has_electronics"]:
        applicable.append("electrical")
    if equipment["has_mission_specific_test"]:
        applicable.append("mission_specific")
    return applicable


def build_baseline_sequence(equipment):
    """Ordered qualification test sequence (Table 5-1 baseline order):
    physical-properties and an initial functional/performance check
    first, then the applicable environmental families in their fixed
    clause order (mechanical, pressure_integrity, thermal, electrical),
    then a closing functional/performance retest, then a
    mission-specific test if applicable. Returns a list of
    {"family": str, "phase": "initial"|"final"|None} dicts; does not
    mutate the input."""
    applicable = select_applicable_families(equipment)
    sequence = []
    if "physical_properties" in applicable:
        sequence.append({"family": "physical_properties", "phase": "initial"})
    if "functional_performance" in applicable:
        sequence.append({"family": "functional_performance", "phase": "initial"})
    for family in ENVIRONMENTAL_ORDER:
        if family in applicable:
            sequence.append({"family": family, "phase": None})
    if "functional_performance" in applicable:
        sequence.append({"family": "functional_performance", "phase": "final"})
    if "mission_specific" in applicable:
        sequence.append({"family": "mission_specific", "phase": None})
    return sequence


def compute_qualification_level(reference_level, margin, mode="multiplicative"):
    """Table 5-2 qualification level derivation: reference_level scaled
    by margin (mode 'multiplicative') or offset by margin (mode
    'additive'). Raises ValueError for an unknown mode."""
    if mode not in MARGIN_MODES:
        raise ValueError("unknown margin mode: %r" % (mode,))
    if mode == "multiplicative":
        return reference_level * margin
    return reference_level + margin


def compute_qualification_duration(reference_duration, duration_factor):
    """Table 5-2 qualification duration derivation: reference_duration
    scaled by duration_factor. Raises ValueError if duration_factor is
    not strictly positive."""
    if duration_factor <= 0:
        raise ValueError("duration factor must be positive: %r" % (duration_factor,))
    return reference_duration * duration_factor


def build_test_requirement(family, reference_level, reference_duration, margin,
                            duration_factor, mode="multiplicative"):
    """Table 5-2 qualification level/duration requirement for one test
    family. Returns a new dict; raises ValueError via the underlying
    derivation calls for an unknown mode or non-positive duration
    factor."""
    return {
        "family": family,
        "reference_level": reference_level,
        "qualification_level": compute_qualification_level(reference_level, margin, mode),
        "reference_duration": reference_duration,
        "qualification_duration": compute_qualification_duration(reference_duration, duration_factor),
        "margin": margin,
        "duration_factor": duration_factor,
        "margin_mode": mode,
    }


def build_qualification_baseline(equipment, test_configs):
    """Full baseline: the Table 5-1 sequence for this equipment, with a
    Table 5-2 requirement attached to every environmental step whose
    family has a matching entry in test_configs (dict family -> dict
    with reference_level, reference_duration, margin, duration_factor,
    and optional mode). A step for a family without a matching config
    gets requirement=None rather than raising, so callers can inspect
    what is still missing. Does not mutate equipment or test_configs."""
    sequence = build_baseline_sequence(equipment)
    baseline = []
    for step in sequence:
        family = step["family"]
        entry = dict(step)
        config = test_configs.get(family) if family in LEVEL_FAMILIES else None
        if config is not None:
            entry["requirement"] = build_test_requirement(
                family,
                config["reference_level"],
                config["reference_duration"],
                config["margin"],
                config["duration_factor"],
                config.get("mode", "multiplicative"),
            )
        else:
            entry["requirement"] = None
        baseline.append(entry)
    return baseline


def missing_requirements(baseline):
    """Environmental/mission-specific families in the baseline that
    still have no Table 5-2 requirement attached, in sequence order,
    de-duplicated. physical_properties and functional_performance never
    appear -- they do not carry a Table 5-2 level/duration."""
    missing = []
    for step in baseline:
        family = step["family"]
        if family in LEVEL_FAMILIES and step["requirement"] is None and family not in missing:
            missing.append(family)
    return missing


def baseline_complete(baseline):
    """True once every environmental/mission-specific family in the
    baseline has a Table 5-2 requirement attached."""
    return len(missing_requirements(baseline)) == 0
