"""Geometry, machining and preparation rules for a metallic test piece.

Anchor: ECSS-Q-ST-70-45C, test-piece clause (shape, dimensions, machining and
preparation of the pieces used for mechanical testing of metallic materials).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Compute the original cross-sectional area from the declared shape.
2. Derive the proportional gauge length from that area and compare it with the
   gauge length the drawing carries.
3. Check the parallel length, transition radius and gripped-end length against
   the minima the section implies.
4. Grade the section dimensional tolerance relatively, not absolutely.
5. Grade the parallel-length and gripped-end roughness against their own
   separate limits, and require a final light cut where the material is
   sensitive to a cold-worked skin.
6. Confirm identity and orientation marking placed outside the parallel length.
"""

import math

__all__ = [
    "PROPORTIONAL_COEFFICIENT",
    "GAUGE_LENGTH_TOLERANCE_FRACTION",
    "PARALLEL_LENGTH_ALLOWANCE_ROUND",
    "PARALLEL_LENGTH_ALLOWANCE_FLAT",
    "MIN_TRANSITION_RADIUS_FRACTION",
    "SECTION_TOLERANCE_FRACTION",
    "PARALLEL_ROUGHNESS_LIMIT_UM",
    "GRIPPED_END_ROUGHNESS_LIMIT_UM",
    "COLD_WORK_SENSITIVE_FAMILIES",
    "cross_section_area_mm2",
    "characteristic_dimension_mm",
    "proportional_gauge_length_mm",
    "gauge_length_agrees",
    "minimum_parallel_length_mm",
    "minimum_transition_radius_mm",
    "section_tolerance_ok",
    "roughness_ok",
    "marking_ok",
    "assess_test_piece",
]

# Proportional pieces relate gauge length to the square root of the original
# area through a fixed coefficient, so elongation compares across sections.
PROPORTIONAL_COEFFICIENT = 5.65

# The drawn gauge length is rounded to a convenient value; agreement with the
# derived proportional length is judged relatively, not to the last micron.
GAUGE_LENGTH_TOLERANCE_FRACTION = 0.10

# Parallel length must exceed the gauge length by an allowance that keeps the
# transition fillet out of the measured region.
PARALLEL_LENGTH_ALLOWANCE_ROUND = 0.5   # of the diameter
PARALLEL_LENGTH_ALLOWANCE_FLAT = 1.5    # of the width

# Fillet radius below this fraction of the characteristic dimension raises the
# local stress enough to move the break out of the parallel length.
MIN_TRANSITION_RADIUS_FRACTION = 0.75

# The section dimension turns load into stress, so its tolerance is relative.
SECTION_TOLERANCE_FRACTION = 0.005

# Roughness in the measured length is a crack-starter question; on the gripped
# ends it is only a gripping question.
PARALLEL_ROUGHNESS_LIMIT_UM = 0.8
GRIPPED_END_ROUGHNESS_LIMIT_UM = 3.2

# Families where a cold-worked or heat-affected machined skin changes the
# measured strength, so a final light cut has to be declared.
COLD_WORK_SENSITIVE_FAMILIES = frozenset(
    {"titanium-alloy", "nickel-alloy", "stainless-steel", "beryllium-alloy"}
)

_SHAPES = ("round", "rectangular")


def _positive(value, label):
    """Return a validated strictly positive finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _non_negative(value, label):
    """Return a validated non-negative finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _shape(value):
    """Return a validated test-piece shape token."""
    if not isinstance(value, str):
        raise ValueError("shape must be a string, got %r" % (value,))
    token = value.strip().lower()
    if token not in _SHAPES:
        raise ValueError("shape %r is not one of %s" % (token, ", ".join(_SHAPES)))
    return token


def cross_section_area_mm2(shape, dimensions):
    """Return the original cross-sectional area of the test piece in mm^2."""
    token = _shape(shape)
    if not isinstance(dimensions, dict):
        raise ValueError("dimensions must be a mapping")
    if token == "round":
        diameter = _positive(dimensions.get("diameter_mm"), "diameter_mm")
        return math.pi * diameter * diameter / 4.0
    thickness = _positive(dimensions.get("thickness_mm"), "thickness_mm")
    width = _positive(dimensions.get("width_mm"), "width_mm")
    if width < thickness:
        raise ValueError(
            "width_mm %g is smaller than thickness_mm %g; the wider dimension is "
            "the width" % (width, thickness)
        )
    return thickness * width


def characteristic_dimension_mm(shape, dimensions):
    """Return the dimension the length and radius minima are scaled from."""
    token = _shape(shape)
    if not isinstance(dimensions, dict):
        raise ValueError("dimensions must be a mapping")
    if token == "round":
        return _positive(dimensions.get("diameter_mm"), "diameter_mm")
    return _positive(dimensions.get("width_mm"), "width_mm")


def proportional_gauge_length_mm(area_mm2, coefficient=PROPORTIONAL_COEFFICIENT):
    """Return the proportional gauge length derived from the original area."""
    area = _positive(area_mm2, "area_mm2")
    k = _positive(coefficient, "coefficient")
    return k * math.sqrt(area)


def gauge_length_agrees(drawn_mm, derived_mm, tolerance=GAUGE_LENGTH_TOLERANCE_FRACTION):
    """Return whether a drawn gauge length agrees with the derived one."""
    drawn = _positive(drawn_mm, "drawn_mm")
    derived = _positive(derived_mm, "derived_mm")
    frac = _positive(tolerance, "tolerance")
    deviation = abs(drawn - derived) / derived
    within = deviation < frac or math.isclose(deviation, frac, rel_tol=0.0, abs_tol=1e-12)
    return {"deviation_fraction": deviation, "within": within, "tolerance": frac}


def minimum_parallel_length_mm(shape, dimensions, gauge_length_mm):
    """Return the shortest parallel length that keeps the fillet out of gauge."""
    token = _shape(shape)
    gauge = _positive(gauge_length_mm, "gauge_length_mm")
    characteristic = characteristic_dimension_mm(token, dimensions)
    if token == "round":
        allowance = PARALLEL_LENGTH_ALLOWANCE_ROUND * characteristic
    else:
        allowance = PARALLEL_LENGTH_ALLOWANCE_FLAT * characteristic
    return gauge + allowance


def minimum_transition_radius_mm(shape, dimensions):
    """Return the smallest acceptable shoulder fillet radius."""
    characteristic = characteristic_dimension_mm(shape, dimensions)
    return MIN_TRANSITION_RADIUS_FRACTION * characteristic


def section_tolerance_ok(dimension_mm, tolerance_mm, fraction=SECTION_TOLERANCE_FRACTION):
    """Return whether a section tolerance is tight enough relative to the size."""
    dimension = _positive(dimension_mm, "dimension_mm")
    tolerance = _non_negative(tolerance_mm, "tolerance_mm")
    frac = _positive(fraction, "fraction")
    relative = tolerance / dimension
    ok = relative < frac or math.isclose(relative, frac, rel_tol=0.0, abs_tol=1e-12)
    return {"relative": relative, "limit": frac, "ok": ok}


def roughness_ok(value_um, limit_um):
    """Return whether a measured roughness sits at or below its own limit."""
    value = _non_negative(value_um, "value_um")
    limit = _positive(limit_um, "limit_um")
    return value < limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=1e-12)


def marking_ok(marking):
    """Return the findings raised by the identity and orientation marking."""
    if not isinstance(marking, dict):
        raise ValueError("marking must be a mapping")
    findings = []
    identity = marking.get("identity")
    if not isinstance(identity, str) or not identity.strip():
        findings.append("test piece carries no identity mark")
    orientation = marking.get("orientation")
    if not isinstance(orientation, str) or not orientation.strip():
        findings.append("test piece carries no orientation mark")
    location = marking.get("location")
    if location is None:
        findings.append("marking location is not declared")
    else:
        if not isinstance(location, str) or not location.strip():
            raise ValueError("marking location must be a non-empty string when given")
        if location.strip().lower() in ("parallel-length", "gauge-length", "gripped-end"):
            findings.append(
                "marking placed on %s, which preparation or gripping consumes"
                % location.strip().lower()
            )
    return {"ok": not findings, "findings": findings}


def assess_test_piece(spec):
    """Grade a proposed test-piece drawing against the preparation rules.

    spec keys: shape, dimensions, gauge_length_mm, parallel_length_mm,
    transition_radius_mm, gripped_end_length_mm, grip_length_mm,
    section_tolerance_mm, parallel_roughness_um, gripped_end_roughness_um,
    material_family, final_light_cut (bool), marking, optional proportional
    (bool, default True) and coefficient.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "shape",
        "dimensions",
        "gauge_length_mm",
        "parallel_length_mm",
        "transition_radius_mm",
        "section_tolerance_mm",
        "parallel_roughness_um",
        "material_family",
        "marking",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    shape = _shape(spec["shape"])
    dimensions = spec["dimensions"]
    area = cross_section_area_mm2(shape, dimensions)
    characteristic = characteristic_dimension_mm(shape, dimensions)
    gauge = _positive(spec["gauge_length_mm"], "gauge_length_mm")
    findings = []

    proportional = spec.get("proportional", True)
    if not isinstance(proportional, bool):
        raise ValueError("proportional must be a boolean")
    derived = proportional_gauge_length_mm(
        area, spec.get("coefficient", PROPORTIONAL_COEFFICIENT)
    )
    if proportional:
        agreement = gauge_length_agrees(gauge, derived)
        if not agreement["within"]:
            findings.append(
                "drawn gauge length %.3f mm departs from the proportional %.3f mm "
                "by %.1f %%" % (gauge, derived, 100.0 * agreement["deviation_fraction"])
            )
    else:
        agreement = {"deviation_fraction": None, "within": None,
                     "tolerance": GAUGE_LENGTH_TOLERANCE_FRACTION}
        findings.append(
            "non-proportional gauge length %.3f mm: report it with every "
            "elongation figure, it does not compare with a proportional result"
            % gauge
        )

    parallel = _positive(spec["parallel_length_mm"], "parallel_length_mm")
    min_parallel = minimum_parallel_length_mm(shape, dimensions, gauge)
    parallel_ok = parallel > min_parallel or math.isclose(
        parallel, min_parallel, rel_tol=0.0, abs_tol=1e-9
    )
    if not parallel_ok:
        findings.append(
            "parallel length %.3f mm is below the %.3f mm the section needs; the "
            "transition fillet sits inside the measured region"
            % (parallel, min_parallel)
        )

    radius = _non_negative(spec["transition_radius_mm"], "transition_radius_mm")
    min_radius = minimum_transition_radius_mm(shape, dimensions)
    radius_ok = radius > min_radius or math.isclose(
        radius, min_radius, rel_tol=0.0, abs_tol=1e-9
    )
    if not radius_ok:
        findings.append(
            "transition radius %.3f mm is below the %.3f mm minimum; the break can "
            "move out of the parallel length" % (radius, min_radius)
        )

    gripped = spec.get("gripped_end_length_mm")
    grip = spec.get("grip_length_mm")
    if gripped is not None and grip is not None:
        gripped_v = _positive(gripped, "gripped_end_length_mm")
        grip_v = _positive(grip, "grip_length_mm")
        if gripped_v < grip_v and not math.isclose(
            gripped_v, grip_v, rel_tol=0.0, abs_tol=1e-9
        ):
            findings.append(
                "gripped end %.3f mm is shorter than the %.3f mm the machine grips"
                % (gripped_v, grip_v)
            )

    tolerance = section_tolerance_ok(characteristic, spec["section_tolerance_mm"])
    if not tolerance["ok"]:
        findings.append(
            "section tolerance is %.3f %% of the dimension, above the %.3f %% the "
            "stress calculation allows"
            % (100.0 * tolerance["relative"], 100.0 * tolerance["limit"])
        )

    if not roughness_ok(spec["parallel_roughness_um"], PARALLEL_ROUGHNESS_LIMIT_UM):
        findings.append(
            "parallel-length roughness above the %.2f um limit; machining marks in "
            "the measured length are crack starters" % PARALLEL_ROUGHNESS_LIMIT_UM
        )
    gripped_roughness = spec.get("gripped_end_roughness_um")
    if gripped_roughness is not None and not roughness_ok(
        gripped_roughness, GRIPPED_END_ROUGHNESS_LIMIT_UM
    ):
        findings.append(
            "gripped-end roughness above the %.2f um limit"
            % GRIPPED_END_ROUGHNESS_LIMIT_UM
        )

    family = spec["material_family"]
    if not isinstance(family, str) or not family.strip():
        raise ValueError("material_family must be a non-empty string")
    family_token = family.strip().lower()
    final_cut = spec.get("final_light_cut", False)
    if not isinstance(final_cut, bool):
        raise ValueError("final_light_cut must be a boolean")
    if family_token in COLD_WORK_SENSITIVE_FAMILIES and not final_cut:
        findings.append(
            "%s needs a declared final light cut to remove the cold-worked "
            "machined skin" % family_token
        )

    mark = marking_ok(spec["marking"])
    findings.extend(mark["findings"])

    return {
        "shape": shape,
        "area_mm2": area,
        "characteristic_dimension_mm": characteristic,
        "derived_gauge_length_mm": derived,
        "gauge_length_agreement": agreement,
        "minimum_parallel_length_mm": min_parallel,
        "minimum_transition_radius_mm": min_radius,
        "section_tolerance": tolerance,
        "marking": mark,
        "acceptable": not findings,
        "status": "acceptable" if not findings else "rework-required",
        "findings": findings,
    }
