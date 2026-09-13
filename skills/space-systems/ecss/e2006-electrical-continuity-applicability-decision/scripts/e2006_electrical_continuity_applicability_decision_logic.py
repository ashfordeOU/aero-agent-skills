#!/usr/bin/env python3
"""Electrical-continuity applicability decision (ECSS-E-ST-20-06C, 6.3.3.1).

Deterministic, offline, standard-library-only implementation of the
applicability decision diagram that decides whether the surface
electrical-continuity requirements govern a given spacecraft outer item,
whether the item is routed to a neighbouring clause instead, or whether it
qualifies for the small-isolated-conductive-part waiver.

Paraphrased procedure only; the standard is cited as an anchor and no
standard text is reproduced.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Named limits
# ---------------------------------------------------------------------------

#: Exposed area at or below which an electrically isolated conductive part
#: may be considered for the small-part waiver (square centimetres).
SMALL_ISOLATED_AREA_LIMIT_CM2 = 1.0

#: Stored electrostatic energy at or below which the discharge of an isolated
#: conductive part is treated as non-hazardous (joules).
STORED_ENERGY_LIMIT_J = 1.0e-4

#: Absolute operating potential at or above which the item is governed by the
#: high-voltage-surface rule rather than the general continuity rule (volts).
HIGH_VOLTAGE_ONSET_V = 55.0

#: Tolerances that absorb floating-point representation error at an exactly
#: compliant limit. They never widen the engineering limit itself.
LIMIT_REL_TOL = 1e-9
LIMIT_ABS_TOL = 1e-15

# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

EXPOSURE_KINDS = (
    "external-plasma-exposed",
    "external-partially-shielded",
    "internal-enclosed",
)

MATERIAL_FAMILIES = (
    "bulk-metal-conductor",
    "conductive-coating",
    "dissipative-coating",
    "dielectric-film",
    "bulk-dielectric",
)

CONDUCTIVE_FAMILIES = (
    "bulk-metal-conductor",
    "conductive-coating",
    "dissipative-coating",
)

DIELECTRIC_FAMILIES = ("dielectric-film", "bulk-dielectric")

SEVERE_CHARGING_ORBITS = (
    "geostationary-earth-orbit",
    "geostationary-transfer-orbit",
    "medium-earth-orbit",
    "highly-elliptical-orbit",
    "high-inclination-low-earth-orbit",
    "sun-synchronous-low-earth-orbit",
    "interplanetary-solar-wind",
)

BENIGN_CHARGING_ORBITS = (
    "low-inclination-low-earth-orbit",
    "equatorial-low-earth-orbit",
)

SEVERITY_SEVERE = "severe-surface-charging-environment"
SEVERITY_BENIGN = "benign-surface-charging-environment"

# ---------------------------------------------------------------------------
# Verdicts and governing clauses
# ---------------------------------------------------------------------------

VERDICT_NOT_APPLICABLE = "continuity-not-applicable-internal-item"
VERDICT_ROUTED_BIASED = "routed-to-deliberately-biased-surface-rule"
VERDICT_ROUTED_HIGH_VOLTAGE = "routed-to-high-voltage-surface-rule"
VERDICT_REQUIRED = "continuity-required-direct-bond"
VERDICT_REQUIRED_BACKING = "continuity-required-on-conductive-backing"
VERDICT_WAIVED_SMALL_PART = "continuity-waived-small-isolated-part"
VERDICT_RELAXED = "continuity-required-material-control-relaxed"

GOVERNING_CLAUSE = {
    VERDICT_NOT_APPLICABLE: "internal-electrostatic-discharge-rules",
    VERDICT_ROUTED_BIASED: "deliberately-biased-surface-rule",
    VERDICT_ROUTED_HIGH_VOLTAGE: "high-voltage-surface-rule",
    VERDICT_REQUIRED: "surface-electrical-continuity-rule",
    VERDICT_REQUIRED_BACKING: "surface-material-control-rule",
    VERDICT_WAIVED_SMALL_PART: "floating-conductive-part-exception",
    VERDICT_RELAXED: "surface-electrical-continuity-rule",
}


def _within_limit(value, limit):
    """True when value does not exceed limit, absorbing representation error.

    The comparison stays ``<=`` on the engineering limit; ``math.isclose``
    only rescues a value that is a few units in the last place above a limit
    it is physically equal to.
    """
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=LIMIT_REL_TOL, abs_tol=LIMIT_ABS_TOL)


def _require_finite(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (field, value))
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (field, value))
    return number


def _require_non_negative(value, field):
    number = _require_finite(value, field)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (field, value))
    return number


def _require_bool(value, field):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (field, value))
    return value


def normalize_surface(record):
    """Validate one outer-item record and return a normalized copy.

    Required keys: surface_id, exposure, material_family, orbit_regime,
    exposed_area_cm2, capacitance_to_structure_f, operating_potential_v,
    deliberately_biased, bonded_to_structure.
    """
    if not isinstance(record, dict):
        raise ValueError("surface record must be a mapping, got %r" % (type(record),))
    surface_id = record.get("surface_id")
    if not isinstance(surface_id, str) or not surface_id.strip():
        raise ValueError("surface_id must be a non-empty string")

    exposure = record.get("exposure")
    if exposure not in EXPOSURE_KINDS:
        raise ValueError(
            "unknown exposure %r for %s; expected one of %s"
            % (exposure, surface_id, ", ".join(EXPOSURE_KINDS))
        )

    family = record.get("material_family")
    if family not in MATERIAL_FAMILIES:
        raise ValueError(
            "unknown material_family %r for %s; expected one of %s"
            % (family, surface_id, ", ".join(MATERIAL_FAMILIES))
        )

    orbit = record.get("orbit_regime")
    if orbit not in SEVERE_CHARGING_ORBITS and orbit not in BENIGN_CHARGING_ORBITS:
        raise ValueError("unknown orbit_regime %r for %s" % (orbit, surface_id))

    return {
        "surface_id": surface_id.strip(),
        "exposure": exposure,
        "material_family": family,
        "orbit_regime": orbit,
        "exposed_area_cm2": _require_non_negative(
            record.get("exposed_area_cm2", 0.0), "exposed_area_cm2"
        ),
        "capacitance_to_structure_f": _require_non_negative(
            record.get("capacitance_to_structure_f", 0.0), "capacitance_to_structure_f"
        ),
        "operating_potential_v": _require_finite(
            record.get("operating_potential_v", 0.0), "operating_potential_v"
        ),
        "deliberately_biased": _require_bool(
            record.get("deliberately_biased", False), "deliberately_biased"
        ),
        "bonded_to_structure": _require_bool(
            record.get("bonded_to_structure", False), "bonded_to_structure"
        ),
    }


def environment_severity(orbit_regime):
    """Return the surface-charging severity of a mission orbit regime."""
    if orbit_regime in SEVERE_CHARGING_ORBITS:
        return SEVERITY_SEVERE
    if orbit_regime in BENIGN_CHARGING_ORBITS:
        return SEVERITY_BENIGN
    raise ValueError("unknown orbit_regime %r" % (orbit_regime,))


def stored_discharge_energy(capacitance_f, potential_v):
    """Electrostatic energy stored on an isolated part: 0.5 * C * V^2 (joules)."""
    capacitance = _require_non_negative(capacitance_f, "capacitance_f")
    potential = _require_finite(potential_v, "potential_v")
    return 0.5 * capacitance * potential * potential


def is_high_voltage_item(operating_potential_v, onset_v=HIGH_VOLTAGE_ONSET_V):
    """True when the absolute operating potential reaches the high-voltage onset."""
    onset = _require_non_negative(onset_v, "onset_v")
    potential = abs(_require_finite(operating_potential_v, "operating_potential_v"))
    if potential > onset:
        return True
    return math.isclose(potential, onset, rel_tol=LIMIT_REL_TOL, abs_tol=LIMIT_ABS_TOL)


def isolated_part_waiver(
    exposed_area_cm2,
    capacitance_to_structure_f,
    operating_potential_v,
    floating_potential_v=None,
    area_limit_cm2=SMALL_ISOLATED_AREA_LIMIT_CM2,
    energy_limit_j=STORED_ENERGY_LIMIT_J,
):
    """Evaluate the small-isolated-conductive-part waiver.

    The waiver needs both a small exposed area and a stored discharge energy
    that stays inside the non-hazardous limit. The energy is evaluated at the
    worst of the operating potential and the environment floating potential.
    """
    area = _require_non_negative(exposed_area_cm2, "exposed_area_cm2")
    area_limit = _require_non_negative(area_limit_cm2, "area_limit_cm2")
    energy_limit = _require_non_negative(energy_limit_j, "energy_limit_j")
    worst_potential = abs(_require_finite(operating_potential_v, "operating_potential_v"))
    if floating_potential_v is not None:
        worst_potential = max(
            worst_potential,
            abs(_require_finite(floating_potential_v, "floating_potential_v")),
        )
    energy = stored_discharge_energy(capacitance_to_structure_f, worst_potential)
    area_ok = _within_limit(area, area_limit)
    energy_ok = _within_limit(energy, energy_limit)
    reasons = []
    if not area_ok:
        reasons.append("exposed-area-above-small-part-limit")
    if not energy_ok:
        reasons.append("stored-discharge-energy-above-limit")
    return {
        "granted": bool(area_ok and energy_ok),
        "exposed_area_cm2": area,
        "area_limit_cm2": area_limit,
        "stored_energy_j": energy,
        "energy_limit_j": energy_limit,
        "worst_potential_v": worst_potential,
        "reasons": reasons,
    }


def decide_continuity_applicability(record, floating_potential_v=None):
    """Walk the applicability decision diagram for one outer item.

    Node order is fixed and reported in ``route``:
    1. plasma exposure, 2. deliberately-biased routing, 3. high-voltage
    routing, 4. material family, 5. small-isolated-part waiver,
    6. charging-environment severity.
    """
    surface = normalize_surface(record)
    route = []
    findings = []

    route.append("exposure:%s" % surface["exposure"])
    if surface["exposure"] == "internal-enclosed":
        return _decision(surface, VERDICT_NOT_APPLICABLE, route, findings,
                         "item has no view to the ambient plasma")

    severity = environment_severity(surface["orbit_regime"])

    route.append("deliberately-biased:%s" % str(surface["deliberately_biased"]).lower())
    if surface["deliberately_biased"]:
        return _decision(surface, VERDICT_ROUTED_BIASED, route, findings,
                         "potential is imposed on purpose, not left floating")

    high_voltage = is_high_voltage_item(surface["operating_potential_v"])
    route.append("high-voltage-surface:%s" % str(high_voltage).lower())
    if high_voltage:
        return _decision(surface, VERDICT_ROUTED_HIGH_VOLTAGE, route, findings,
                         "operating potential reaches the high-voltage onset")

    route.append("material-family:%s" % surface["material_family"])
    if surface["material_family"] in DIELECTRIC_FAMILIES:
        if surface["exposure"] == "external-partially-shielded":
            findings.append("partial-shielding-needs-justification")
        verdict = VERDICT_REQUIRED_BACKING
        if severity == SEVERITY_BENIGN:
            verdict = VERDICT_RELAXED
        route.append("environment:%s" % severity)
        if not surface["bonded_to_structure"]:
            findings.append("dielectric-backing-not-bonded-to-structure")
        return _decision(surface, verdict, route, findings,
                         "dielectric outer layer over a conductive backing")

    waiver = isolated_part_waiver(
        surface["exposed_area_cm2"],
        surface["capacitance_to_structure_f"],
        surface["operating_potential_v"],
        floating_potential_v=floating_potential_v,
    )
    route.append("isolated-part-waiver:%s" % str(waiver["granted"]).lower())
    if not surface["bonded_to_structure"] and waiver["granted"]:
        decision = _decision(surface, VERDICT_WAIVED_SMALL_PART, route, findings,
                             "isolated conductive part inside the small-part waiver")
        decision["waiver"] = waiver
        return decision

    route.append("environment:%s" % severity)
    verdict = VERDICT_REQUIRED
    if severity == SEVERITY_BENIGN:
        verdict = VERDICT_RELAXED
    if not surface["bonded_to_structure"]:
        findings.append("ungrounded-conductive-surface")
    if surface["exposure"] == "external-partially-shielded":
        findings.append("partial-shielding-needs-justification")
    decision = _decision(surface, verdict, route, findings,
                         "exposed conductive surface outside every waiver")
    decision["waiver"] = waiver
    return decision


def _decision(surface, verdict, route, findings, rationale):
    return {
        "surface_id": surface["surface_id"],
        "verdict": verdict,
        "governing_clause": GOVERNING_CLAUSE[verdict],
        "route": list(route),
        "findings": list(findings),
        "rationale": rationale,
        "anchor": "ECSS-E-ST-20-06C 6.3.3.1",
    }


def assess_surface_inventory(records, floating_potential_v=None):
    """Decide applicability for a whole outer-surface inventory."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple")
    if len(records) == 0:
        raise ValueError("records must not be empty")
    decisions = []
    seen = set()
    for record in records:
        decision = decide_continuity_applicability(
            record, floating_potential_v=floating_potential_v
        )
        if decision["surface_id"] in seen:
            raise ValueError("duplicate surface_id %r" % decision["surface_id"])
        seen.add(decision["surface_id"])
        decisions.append(decision)
    counts = {}
    for decision in decisions:
        counts[decision["verdict"]] = counts.get(decision["verdict"], 0) + 1
    open_findings = [
        (d["surface_id"], f) for d in decisions for f in d["findings"]
    ]
    return {
        "decisions": decisions,
        "verdict_counts": counts,
        "open_findings": open_findings,
        "in_scope_count": sum(
            1
            for d in decisions
            if d["verdict"] in (VERDICT_REQUIRED, VERDICT_REQUIRED_BACKING, VERDICT_RELAXED)
        ),
        "compliant": len(open_findings) == 0,
    }


def format_decision_report(assessment):
    """Render a deterministic plain-text applicability report."""
    if not isinstance(assessment, dict) or "decisions" not in assessment:
        raise ValueError("assessment must come from assess_surface_inventory")
    lines = ["ECSS-E-ST-20-06C 6.3.3.1 continuity applicability"]
    for decision in assessment["decisions"]:
        lines.append(
            "%s -> %s [%s]"
            % (decision["surface_id"], decision["verdict"], decision["governing_clause"])
        )
        for finding in decision["findings"]:
            lines.append("    finding: %s" % finding)
    lines.append(
        "in-scope=%d compliant=%s"
        % (assessment["in_scope_count"], str(assessment["compliant"]).lower())
    )
    return "\n".join(lines)
