#!/usr/bin/env python3
"""Solar-array arc-characterization requirement (ECSS-E-ST-20-06C, clause 7.2.2).

Offline, deterministic, stdlib-only implementation of the clause 7.2.2
decision: a photovoltaic array whose exposed surfaces do not satisfy the
surface-grounding provisions must be supported by an arc-characterization
analysis. The module categorizes each array surface element, checks it
against the grounding provisions, computes the triple-junction primary-arc
inception threshold, compares it with the worst-case differential potential
and derives the characterization scope that the array has to carry.

The threshold and rate relations are engineering surrogate models with
explicit reference points; they are monotonic, clamped and deterministic so
that a campaign can be graded reproducibly. No standard text is reproduced.
"""

import math

# ---------------------------------------------------------------------------
# Surface element taxonomy
# ---------------------------------------------------------------------------

CONDUCTIVE_ELEMENTS = frozenset(
    {"interconnect", "busbar", "substrate-facesheet", "hinge-fitting"}
)
DIELECTRIC_ELEMENTS = frozenset(
    {"coverglass", "cell-edge", "adhesive-fillet", "harness-insulation", "kapton-blanket"}
)
SURFACE_ELEMENT_TYPES = CONDUCTIVE_ELEMENTS | DIELECTRIC_ELEMENTS

# ---------------------------------------------------------------------------
# Grounding provision limits (clause 7.2.2 anchor values)
# ---------------------------------------------------------------------------

BOND_PATH_RESISTANCE_LIMIT_OHM = 1.0e6
COATING_RESISTIVITY_LIMIT_OHM_PER_SQUARE = 1.0e9
UNGROUNDED_DIELECTRIC_AREA_LIMIT_CM2 = 10.0

# ---------------------------------------------------------------------------
# Triple-junction inception surrogate model
# ---------------------------------------------------------------------------

REFERENCE_COVERGLASS_THICKNESS_UM = 100.0
REFERENCE_INTERCONNECT_GAP_MM = 0.90
REFERENCE_TEMPERATURE_C = 20.0
BASE_INCEPTION_VOLTAGE_V = 120.0
GAP_SENSITIVITY_PER_MM = 0.35
TEMPERATURE_SENSITIVITY_PER_C = 0.0015
MINIMUM_INCEPTION_VOLTAGE_V = 40.0

# Primary-arc rate surrogate model.
ARC_RATE_COEFFICIENT_PER_M_PER_HOUR = 0.02
ARC_RATE_EXPONENT = 1.6

# Above this string voltage the characterization has to cover sustained arcing.
SUSTAINED_ARC_REVIEW_VOLTAGE_V = 55.0

# Representation tolerance: absorbs the few-ULP error of a summed potential or
# a summed bond-path resistance. It never widens an engineering limit.
COMPARISON_TOLERANCE = 1e-9


def _almost_le(value, limit, tol=COMPARISON_TOLERANCE):
    """True when value is at or below limit, absorbing float representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=tol, abs_tol=tol)


def _almost_ge(value, limit, tol=COMPARISON_TOLERANCE):
    """True when value is at or above limit, absorbing float representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=tol, abs_tol=tol)


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _positive(value, label):
    value = _finite(value, label)
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return value


def _non_negative(value, label):
    value = _finite(value, label)
    if value < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


# ---------------------------------------------------------------------------
# 1. Surface element validation and grounding provision check
# ---------------------------------------------------------------------------


def validate_surface_element(element):
    """Normalize one array surface element; raise ValueError on bad input."""
    if not isinstance(element, dict):
        raise ValueError("surface element must be a mapping, got %r" % (element,))
    element_id = element.get("id")
    if not isinstance(element_id, str) or not element_id.strip():
        raise ValueError("surface element needs a non-empty string 'id'")
    kind = element.get("type")
    if kind not in SURFACE_ELEMENT_TYPES:
        raise ValueError(
            "unknown surface element type %r for '%s'; expected one of %s"
            % (kind, element_id, ", ".join(sorted(SURFACE_ELEMENT_TYPES)))
        )
    area_cm2 = _positive(element.get("exposed_area_cm2", 0.0), "exposed_area_cm2")
    normalized = {
        "id": element_id.strip(),
        "type": kind,
        "category": "conductive" if kind in CONDUCTIVE_ELEMENTS else "dielectric",
        "exposed_area_cm2": area_cm2,
    }
    segments = element.get("bond_path_segments_ohm")
    if segments is None:
        normalized["bond_path_ohm"] = None
    else:
        if not isinstance(segments, (list, tuple)) or not segments:
            raise ValueError(
                "bond_path_segments_ohm for '%s' must be a non-empty sequence"
                % normalized["id"]
            )
        total = 0.0
        for seg in segments:
            total += _non_negative(seg, "bond path segment of '%s'" % normalized["id"])
        normalized["bond_path_ohm"] = total
    resistivity = element.get("surface_resistivity_ohm_per_square")
    if resistivity is None:
        normalized["surface_resistivity_ohm_per_square"] = None
    else:
        normalized["surface_resistivity_ohm_per_square"] = _positive(
            resistivity, "surface_resistivity_ohm_per_square of '%s'" % normalized["id"]
        )
    return normalized


def element_grounding_finding(element):
    """Check one element against the surface-grounding provisions."""
    item = validate_surface_element(element)
    if item["category"] == "conductive":
        bond = item["bond_path_ohm"]
        if bond is None:
            return dict(item, compliant=False, reason="conductive element left floating")
        if _almost_le(bond, BOND_PATH_RESISTANCE_LIMIT_OHM):
            return dict(item, compliant=True, reason="bonded to structure within limit")
        return dict(
            item,
            compliant=False,
            reason="bond path %.3e ohm exceeds %.3e ohm"
            % (bond, BOND_PATH_RESISTANCE_LIMIT_OHM),
        )
    resistivity = item["surface_resistivity_ohm_per_square"]
    if resistivity is not None and _almost_le(
        resistivity, COATING_RESISTIVITY_LIMIT_OHM_PER_SQUARE
    ):
        bond = item["bond_path_ohm"]
        if bond is None:
            return dict(
                item,
                compliant=False,
                reason="conductive coating present but no bleed path to structure",
            )
        if _almost_le(bond, BOND_PATH_RESISTANCE_LIMIT_OHM):
            return dict(item, compliant=True, reason="coated and bled to structure")
        return dict(
            item,
            compliant=False,
            reason="coating bleed path %.3e ohm exceeds %.3e ohm"
            % (bond, BOND_PATH_RESISTANCE_LIMIT_OHM),
        )
    if _almost_le(item["exposed_area_cm2"], UNGROUNDED_DIELECTRIC_AREA_LIMIT_CM2):
        return dict(
            item, compliant=True, reason="ungrounded dielectric area within allowance"
        )
    return dict(
        item,
        compliant=False,
        reason="ungrounded dielectric area %.2f cm2 exceeds %.2f cm2"
        % (item["exposed_area_cm2"], UNGROUNDED_DIELECTRIC_AREA_LIMIT_CM2),
    )


def assess_grounding_provisions(elements):
    """Aggregate the per-element findings for a whole array surface."""
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("elements must be a non-empty sequence of surface elements")
    findings = [element_grounding_finding(e) for e in elements]
    seen = set()
    for finding in findings:
        if finding["id"] in seen:
            raise ValueError("duplicate surface element id '%s'" % finding["id"])
        seen.add(finding["id"])
    deficient = [f for f in findings if not f["compliant"]]
    return {
        "findings": findings,
        "deficient_ids": [f["id"] for f in deficient],
        "compliant": not deficient,
        "element_count": len(findings),
    }


# ---------------------------------------------------------------------------
# 2. Triple-junction inception threshold and differential potential
# ---------------------------------------------------------------------------


def primary_arc_inception_threshold(
    coverglass_thickness_um, interconnect_gap_mm, temperature_c
):
    """Inception threshold of the coverglass/interconnect/vacuum triple junction."""
    thickness = _positive(coverglass_thickness_um, "coverglass_thickness_um")
    gap = _positive(interconnect_gap_mm, "interconnect_gap_mm")
    temperature = _finite(temperature_c, "temperature_c")
    if temperature < -273.15:
        raise ValueError("temperature_c below absolute zero: %r" % temperature)
    thickness_factor = math.sqrt(thickness / REFERENCE_COVERGLASS_THICKNESS_UM)
    gap_factor = 1.0 + GAP_SENSITIVITY_PER_MM * (gap - REFERENCE_INTERCONNECT_GAP_MM)
    if gap_factor <= 0.0:
        gap_factor = 0.0
    temperature_factor = 1.0 - TEMPERATURE_SENSITIVITY_PER_C * (
        REFERENCE_TEMPERATURE_C - temperature
    )
    if temperature_factor < 0.0:
        temperature_factor = 0.0
    raw = BASE_INCEPTION_VOLTAGE_V * thickness_factor * gap_factor * temperature_factor
    return max(raw, MINIMUM_INCEPTION_VOLTAGE_V)


def worst_case_differential_potential(
    coverglass_potential_v, interconnect_potential_v, string_bias_v=0.0
):
    """Magnitude of the dielectric-to-conductor potential difference."""
    surface = _finite(coverglass_potential_v, "coverglass_potential_v")
    conductor = _finite(interconnect_potential_v, "interconnect_potential_v")
    bias = _finite(string_bias_v, "string_bias_v")
    return abs(surface - (conductor + bias))


def inception_margin(differential_potential_v, threshold_v):
    """Compare the differential potential with the inception threshold."""
    differential = _non_negative(differential_potential_v, "differential_potential_v")
    threshold = _positive(threshold_v, "threshold_v")
    reached = _almost_ge(differential, threshold)
    return {
        "differential_v": differential,
        "threshold_v": threshold,
        "margin_v": threshold - differential,
        "ratio": differential / threshold,
        "inception_reached": reached,
    }


def predicted_primary_arc_count(
    differential_potential_v, threshold_v, triple_junction_length_m, exposure_hours
):
    """Expected number of primary arcs over the exposure period."""
    margin = inception_margin(differential_potential_v, threshold_v)
    length = _positive(triple_junction_length_m, "triple_junction_length_m")
    hours = _non_negative(exposure_hours, "exposure_hours")
    if not margin["inception_reached"]:
        return 0.0
    overdrive = (margin["differential_v"] - margin["threshold_v"]) / margin["threshold_v"]
    if overdrive < 0.0:
        overdrive = 0.0
    rate = ARC_RATE_COEFFICIENT_PER_M_PER_HOUR * length * (overdrive ** ARC_RATE_EXPONENT)
    return rate * hours


# ---------------------------------------------------------------------------
# 3. Characterization scope and top-level assessment
# ---------------------------------------------------------------------------


def arc_characterization_scope(grounding_compliant, inception_reached, string_voltage_v):
    """Deliverables the arc-characterization analysis has to contain."""
    if not isinstance(grounding_compliant, bool):
        raise ValueError("grounding_compliant must be a bool")
    if not isinstance(inception_reached, bool):
        raise ValueError("inception_reached must be a bool")
    voltage = _non_negative(string_voltage_v, "string_voltage_v")
    if grounding_compliant and not inception_reached:
        return []
    scope = ["inception-threshold-determination", "arc-site-identification"]
    if inception_reached:
        scope.append("primary-arc-rate-prediction")
        scope.append("discharge-energy-and-capacitance-budget")
    if not grounding_compliant:
        scope.append("grounding-deficiency-justification")
    if _almost_ge(voltage, SUSTAINED_ARC_REVIEW_VOLTAGE_V):
        scope.append("sustained-arc-susceptibility-review")
    return scope


def assess_solar_array_arc_requirement(design):
    """Top-level clause 7.2.2 assessment for one array design."""
    if not isinstance(design, dict):
        raise ValueError("design must be a mapping, got %r" % (design,))
    for key in ("surface_elements", "coverglass_thickness_um", "interconnect_gap_mm"):
        if key not in design:
            raise ValueError("design missing required key '%s'" % key)
    grounding = assess_grounding_provisions(design["surface_elements"])
    threshold = primary_arc_inception_threshold(
        design["coverglass_thickness_um"],
        design["interconnect_gap_mm"],
        design.get("temperature_c", REFERENCE_TEMPERATURE_C),
    )
    differential = worst_case_differential_potential(
        design.get("coverglass_potential_v", 0.0),
        design.get("interconnect_potential_v", 0.0),
        design.get("string_bias_v", 0.0),
    )
    margin = inception_margin(differential, threshold)
    arcs = predicted_primary_arc_count(
        differential,
        threshold,
        design.get("triple_junction_length_m", 1.0),
        design.get("exposure_hours", 0.0),
    )
    scope = arc_characterization_scope(
        grounding["compliant"],
        margin["inception_reached"],
        design.get("string_voltage_v", 0.0),
    )
    drivers = []
    if not grounding["compliant"]:
        drivers.append("grounding-provisions-not-satisfied")
    if margin["inception_reached"]:
        drivers.append("differential-potential-at-or-above-inception")
    return {
        "grounding": grounding,
        "inception": margin,
        "predicted_primary_arcs": arcs,
        "characterization_required": bool(drivers),
        "drivers": drivers,
        "characterization_scope": scope,
        "compliant_without_characterization": not drivers,
    }
