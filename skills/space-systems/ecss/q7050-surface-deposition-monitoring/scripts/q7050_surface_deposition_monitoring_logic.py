"""Surface deposition (fallout) monitoring with witness plates.

Anchor: ECSS-Q-ST-70-50C surface clause -- measuring the particulate fallout
that settles onto an exposed surface by exposing a witness plate beside the
hardware and counting what lands on it. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the plate: exposed area, exposure duration and orientation.
2. Convert the counted particles per size band into obscured area, treating
   each particle as a disc of its stated size, and express the total as a
   percentage of the plate area -- the percent area coverage.
3. Subtract the coverage of a control plate that was handled identically but
   not exposed, so the handling and the counting background do not enter the
   deposition figure.
4. Divide by the exposure to obtain a deposition rate, and project that rate
   forward onto the real hardware exposure to get the coverage the surface
   will have accumulated by the end of its exposure.
5. Grade the projected coverage against the allowed value, absorbing an
   equality at the limit with a tolerance rather than relaxing the limit, and
   report the findings the plate itself raises.
"""

import math

__all__ = [
    "MIN_PLATE_AREA_CM2",
    "MIN_EXPOSURE_HOURS",
    "CM2_TO_UM2",
    "PLATE_ORIENTATIONS",
    "COVERAGE_TOLERANCE_REL",
    "COVERAGE_BANDS",
    "validate_plate_area_cm2",
    "validate_exposure_hours",
    "validate_orientation",
    "validate_bands",
    "particle_area_um2",
    "obscured_area_um2",
    "percent_area_coverage",
    "net_coverage",
    "deposition_rate_per_hour",
    "project_coverage",
    "categorize_coverage",
    "assess_fallout",
]

# A plate smaller than this collects too few particles for the count to be
# representative of the zone it stands in.
MIN_PLATE_AREA_CM2 = 25.0

# Below this exposure the plate is reporting its own handling, not fallout.
MIN_EXPOSURE_HOURS = 1.0

CM2_TO_UM2 = 1.0e8

# Only an upward-facing plate collects gravitational fallout; the others are
# recorded because they answer a different question.
PLATE_ORIENTATIONS = ("upward", "vertical", "downward")

# Coverage comparisons are ratios: absorb an exact equality here rather than
# by moving the allowed value.
COVERAGE_TOLERANCE_REL = 1e-9

# Reporting bands for a projected coverage, ascending by upper bound.
COVERAGE_BANDS = (
    (0.01, "negligible"),
    (0.1, "low"),
    (1.0, "moderate"),
    (10.0, "high"),
)


def validate_plate_area_cm2(area_cm2):
    """Return the validated witness plate collecting area in square centimetres."""
    if not isinstance(area_cm2, (int, float)) or isinstance(area_cm2, bool):
        raise ValueError("plate_area_cm2 must be a real number, got %r" % (area_cm2,))
    value = float(area_cm2)
    if not math.isfinite(value):
        raise ValueError("plate_area_cm2 must be finite")
    if value <= 0.0:
        raise ValueError("plate_area_cm2 must be positive, got %g" % value)
    return value


def validate_exposure_hours(hours):
    """Return the validated plate exposure duration in hours."""
    if not isinstance(hours, (int, float)) or isinstance(hours, bool):
        raise ValueError("exposure_hours must be a real number, got %r" % (hours,))
    value = float(hours)
    if not math.isfinite(value):
        raise ValueError("exposure_hours must be finite")
    if value <= 0.0:
        raise ValueError("exposure_hours must be positive, got %g" % value)
    return value


def validate_orientation(orientation):
    """Return the validated plate orientation."""
    if not isinstance(orientation, str):
        raise ValueError("orientation must be a string, got %r" % (orientation,))
    value = orientation.strip().lower()
    if value not in PLATE_ORIENTATIONS:
        raise ValueError(
            "orientation must be one of %s, got %r"
            % (", ".join(PLATE_ORIENTATIONS), orientation)
        )
    return value


def validate_bands(bands, name="bands"):
    """Return validated (size_um, count) bands, strictly increasing in size."""
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("%s must be a non-empty sequence of (size_um, count) pairs" % name)
    rows = []
    for i, item in enumerate(bands):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be a (size_um, count) pair" % (name, i))
        size, count = item
        if not isinstance(size, (int, float)) or isinstance(size, bool):
            raise ValueError("%s[%d] size must be a real number" % (name, i))
        if not isinstance(count, (int, float)) or isinstance(count, bool):
            raise ValueError("%s[%d] count must be a real number" % (name, i))
        size = float(size)
        count = float(count)
        if not math.isfinite(size) or size <= 0.0:
            raise ValueError("%s[%d] size must be positive and finite" % (name, i))
        if not math.isfinite(count) or count < 0.0:
            raise ValueError("%s[%d] count must be finite and non-negative" % (name, i))
        rows.append((size, count))
    for i in range(1, len(rows)):
        if rows[i][0] <= rows[i - 1][0]:
            raise ValueError("%s sizes must strictly increase (index %d)" % (name, i))
    return rows


def particle_area_um2(size_um):
    """Return the projected area of one particle of this size, as a disc."""
    if not isinstance(size_um, (int, float)) or isinstance(size_um, bool):
        raise ValueError("size_um must be a real number, got %r" % (size_um,))
    size = float(size_um)
    if not math.isfinite(size) or size <= 0.0:
        raise ValueError("size_um must be positive and finite, got %r" % (size_um,))
    return math.pi * size * size / 4.0


def obscured_area_um2(bands):
    """Return the total projected area obscured by the counted particles."""
    rows = validate_bands(bands)
    return sum(particle_area_um2(size) * count for size, count in rows)


def percent_area_coverage(bands, plate_area_cm2):
    """Return the percentage of the plate area obscured by counted particles."""
    area = validate_plate_area_cm2(plate_area_cm2)
    obscured = obscured_area_um2(bands)
    return obscured / (area * CM2_TO_UM2) * 100.0


def net_coverage(sample_coverage, control_coverage=0.0):
    """Return the sample coverage with the control plate coverage removed."""
    for label, value in (
        ("sample_coverage", sample_coverage),
        ("control_coverage", control_coverage),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number, got %r" % (label, value))
        if not math.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("%s must be finite and non-negative, got %r" % (label, value))
    sample = float(sample_coverage)
    control = float(control_coverage)
    if control > sample and not math.isclose(
        control, sample, rel_tol=COVERAGE_TOLERANCE_REL, abs_tol=0.0
    ):
        raise ValueError(
            "control coverage %g%% exceeds the exposed plate %g%%; the exposure is not "
            "separable from the handling background" % (control, sample)
        )
    return max(sample - control, 0.0)


def deposition_rate_per_hour(coverage_percent, exposure_hours):
    """Return the coverage accumulated per hour of exposure."""
    if not isinstance(coverage_percent, (int, float)) or isinstance(coverage_percent, bool):
        raise ValueError("coverage_percent must be a real number")
    coverage = float(coverage_percent)
    if not math.isfinite(coverage) or coverage < 0.0:
        raise ValueError("coverage_percent must be finite and non-negative")
    hours = validate_exposure_hours(exposure_hours)
    return coverage / hours


def project_coverage(rate_per_hour, hardware_exposure_hours, initial_coverage=0.0):
    """Project the coverage a surface reaches after its own exposure."""
    if not isinstance(rate_per_hour, (int, float)) or isinstance(rate_per_hour, bool):
        raise ValueError("rate_per_hour must be a real number")
    rate = float(rate_per_hour)
    if not math.isfinite(rate) or rate < 0.0:
        raise ValueError("rate_per_hour must be finite and non-negative")
    if not isinstance(initial_coverage, (int, float)) or isinstance(initial_coverage, bool):
        raise ValueError("initial_coverage must be a real number")
    start = float(initial_coverage)
    if not math.isfinite(start) or start < 0.0:
        raise ValueError("initial_coverage must be finite and non-negative")
    hours = validate_exposure_hours(hardware_exposure_hours)
    return start + rate * hours


def categorize_coverage(coverage_percent):
    """Return the reporting band a projected coverage falls in."""
    if not isinstance(coverage_percent, (int, float)) or isinstance(coverage_percent, bool):
        raise ValueError("coverage_percent must be a real number")
    coverage = float(coverage_percent)
    if not math.isfinite(coverage) or coverage < 0.0:
        raise ValueError("coverage_percent must be finite and non-negative")
    for bound, label in COVERAGE_BANDS:
        if coverage < bound or math.isclose(
            coverage, bound, rel_tol=COVERAGE_TOLERANCE_REL, abs_tol=0.0
        ):
            return label
    return "excessive"


def assess_fallout(spec):
    """Grade a witness-plate fallout result and project it onto the hardware.

    spec keys: plate_area_cm2, exposure_hours, bands, hardware_exposure_hours,
    allowed_coverage_percent; optional orientation, control_bands,
    control_plate_area_cm2, initial_coverage_percent.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "plate_area_cm2",
        "exposure_hours",
        "bands",
        "hardware_exposure_hours",
        "allowed_coverage_percent",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    plate_area = validate_plate_area_cm2(spec["plate_area_cm2"])
    exposure = validate_exposure_hours(spec["exposure_hours"])
    hardware_exposure = validate_exposure_hours(spec["hardware_exposure_hours"])
    orientation = validate_orientation(spec.get("orientation", "upward"))
    allowed = spec["allowed_coverage_percent"]
    if not isinstance(allowed, (int, float)) or isinstance(allowed, bool):
        raise ValueError("allowed_coverage_percent must be a real number")
    allowed = float(allowed)
    if not math.isfinite(allowed) or allowed <= 0.0:
        raise ValueError("allowed_coverage_percent must be positive and finite")

    gross = percent_area_coverage(spec["bands"], plate_area)
    control_bands = spec.get("control_bands")
    if control_bands is None:
        control = 0.0
    else:
        control = percent_area_coverage(
            control_bands, spec.get("control_plate_area_cm2", plate_area)
        )
    net = net_coverage(gross, control)
    rate = deposition_rate_per_hour(net, exposure)
    projected = project_coverage(
        rate, hardware_exposure, spec.get("initial_coverage_percent", 0.0)
    )

    at_limit = math.isclose(projected, allowed, rel_tol=COVERAGE_TOLERANCE_REL, abs_tol=0.0)
    compliant = at_limit or projected < allowed

    findings = []
    if plate_area < MIN_PLATE_AREA_CM2:
        findings.append(
            "plate area %g cm2 is below the %g cm2 minimum; the count is not "
            "representative of the zone" % (plate_area, MIN_PLATE_AREA_CM2)
        )
    if exposure < MIN_EXPOSURE_HOURS:
        findings.append(
            "exposure %g h is below the %g h minimum; the plate is reporting handling, "
            "not fallout" % (exposure, MIN_EXPOSURE_HOURS)
        )
    if orientation != "upward":
        findings.append(
            "plate orientation %r does not collect gravitational fallout; the rate is "
            "not a settling rate" % orientation
        )
    if control_bands is None:
        findings.append(
            "no control plate reported; the handling and counting background is inside "
            "the deposition figure"
        )
    if hardware_exposure > exposure * 10.0:
        findings.append(
            "hardware exposure %g h is more than ten times the plate exposure %g h; the "
            "projection is extrapolating far past what was measured"
            % (hardware_exposure, exposure)
        )
    if not compliant:
        findings.append(
            "projected coverage %.4g%% exceeds the allowed %.4g%%" % (projected, allowed)
        )

    return {
        "plate_area_cm2": plate_area,
        "exposure_hours": exposure,
        "orientation": orientation,
        "gross_coverage_percent": gross,
        "control_coverage_percent": control,
        "net_coverage_percent": net,
        "rate_percent_per_hour": rate,
        "projected_coverage_percent": projected,
        "allowed_coverage_percent": allowed,
        "band": categorize_coverage(projected),
        "compliant": compliant,
        "findings": findings,
    }
