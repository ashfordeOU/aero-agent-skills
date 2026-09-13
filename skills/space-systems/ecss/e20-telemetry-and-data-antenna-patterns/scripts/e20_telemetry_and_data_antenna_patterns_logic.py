#!/usr/bin/env python3
"""Telecommand and data antenna radiation-patterns (ECSS-E-ST-20C 7.2.2.2.1).

Paraphrased procedure, no verbatim standard text. The clause asks that the
radiation-pattern of a command or data antenna is characterized over the
angular region the link needs, and that the effect of nearby spacecraft
structures -- blockage and scattering -- is carried in that
characterization rather than left to the free-space pattern of the
isolated antenna.

Deterministic, offline, stdlib only. Angles are degrees, gains are dBi,
lengths are metres.

Public entry points
-------------------
frequency_to_wavelength         free-space wavelength of a carrier
validate_pattern_cut            normalize and reject an unusable cut
check_angular_sampling          sampling step fine enough to resolve nulls
interpolate_gain                linear gain between two sampled angles
worst_case_gain_in_cone         minimum gain inside a coverage-cone
categorize_structure_interaction blockage, scattering or negligible
derive_perturbation_db          default perturbation from size in wavelengths
apply_structure_effects         perturb a free-space cut with the structures
coverage_fraction               solid-angle-weighted fraction above a gain
assess_pattern_compliance       roll-up against the link requirement
"""

import math

SPEED_OF_LIGHT_M_S = 299792458.0
REL_TOL = 1e-9
ABS_TOL = 1e-12

MIN_SAMPLES = 3
MAX_ABS_THETA_DEG = 180.0
MIN_GAIN_DBI = -100.0
MAX_GAIN_DBI = 100.0
DEFAULT_MAX_STEP_DEG = 5.0
DEFAULT_GUARD_DEG = 5.0

# Size in wavelengths below which a structure cannot redirect the pattern.
NEGLIGIBLE_SIZE_RATIO = 0.1
# Size in wavelengths at which an obscuring structure blocks rather than
# diffracts around the aperture.
BLOCKAGE_SIZE_RATIO = 1.0
# A non-obscuring dielectric this small stays out of the budget.
DIELECTRIC_SCATTER_RATIO = 5.0

SURFACES = ("conductive", "dielectric")

MAX_BLOCKAGE_DB = 20.0
MAX_RIPPLE_DB = 6.0


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _require_number(value, label, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % label)
    if minimum is not None and number < minimum:
        raise ValueError("%s must be >= %s" % (label, minimum))
    if maximum is not None and number > maximum:
        raise ValueError("%s must be <= %s" % (label, maximum))
    return number


def _not_less(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def frequency_to_wavelength(frequency_ghz):
    """Free-space wavelength in metres for a carrier in GHz."""
    frequency = _require_number(frequency_ghz, "frequency_ghz")
    if frequency <= 0.0:
        raise ValueError("frequency_ghz must be greater than zero")
    return SPEED_OF_LIGHT_M_S / (frequency * 1e9)


def validate_pattern_cut(samples):
    """Normalize one angular cut into ordered (theta, gain) pairs."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("pattern cut must be a list or tuple")
    if len(samples) < MIN_SAMPLES:
        raise ValueError("pattern cut needs at least %d samples" % MIN_SAMPLES)
    cut = []
    previous = None
    for index, sample in enumerate(samples):
        if not isinstance(sample, (list, tuple)) or len(sample) != 2:
            raise ValueError("sample %d must be a (theta, gain) pair" % index)
        theta = _require_number(
            sample[0], "theta at sample %d" % index,
            minimum=-MAX_ABS_THETA_DEG, maximum=MAX_ABS_THETA_DEG,
        )
        gain = _require_number(
            sample[1], "gain at sample %d" % index,
            minimum=MIN_GAIN_DBI, maximum=MAX_GAIN_DBI,
        )
        if previous is not None and theta <= previous:
            raise ValueError("pattern cut angles must increase strictly")
        previous = theta
        cut.append((theta, gain))
    return cut


def check_angular_sampling(samples, max_step_deg=DEFAULT_MAX_STEP_DEG):
    """Flag a cut sampled too coarsely to resolve its nulls."""
    cut = validate_pattern_cut(samples)
    step_limit = _require_number(max_step_deg, "max_step_deg")
    if step_limit <= 0.0:
        raise ValueError("max_step_deg must be greater than zero")
    findings = []
    for (theta0, _), (theta1, _) in zip(cut, cut[1:]):
        step = theta1 - theta0
        if step > step_limit and not math.isclose(
            step, step_limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
        ):
            findings.append(
                "angular-sampling of %.3g deg between %.3g and %.3g exceeds the "
                "%.3g deg step" % (step, theta0, theta1, step_limit)
            )
    return findings


def interpolate_gain(samples, theta_deg):
    """Linear gain at an angle inside the sampled span."""
    cut = validate_pattern_cut(samples)
    theta = _require_number(theta_deg, "theta_deg")
    low, high = cut[0][0], cut[-1][0]
    if theta < low or theta > high:
        raise ValueError("theta_deg %g lies outside the sampled cut" % theta)
    for (theta0, gain0), (theta1, gain1) in zip(cut, cut[1:]):
        if theta0 <= theta <= theta1:
            span = theta1 - theta0
            if span == 0.0:
                return gain0
            return gain0 + (gain1 - gain0) * (theta - theta0) / span
    return cut[-1][1]


def worst_case_gain_in_cone(samples, cone_half_angle_deg):
    """Minimum gain anywhere inside a coverage-cone about boresight."""
    cut = validate_pattern_cut(samples)
    cone = _require_number(cone_half_angle_deg, "cone_half_angle_deg")
    if cone <= 0.0:
        raise ValueError("cone_half_angle_deg must be greater than zero")
    low, high = cut[0][0], cut[-1][0]
    if -cone < low or cone > high:
        raise ValueError("the coverage-cone is wider than the sampled cut")
    worst = min(interpolate_gain(cut, -cone), interpolate_gain(cut, cone))
    for theta, gain in cut:
        if abs(theta) <= cone or math.isclose(
            abs(theta), cone, rel_tol=REL_TOL, abs_tol=ABS_TOL
        ):
            worst = min(worst, gain)
    return worst


def _normalize_sector(sector):
    if not isinstance(sector, (list, tuple)) or len(sector) != 2:
        raise ValueError("sector must be a (start, end) pair in degrees")
    start = _require_number(
        sector[0], "sector start", minimum=-MAX_ABS_THETA_DEG,
        maximum=MAX_ABS_THETA_DEG,
    )
    end = _require_number(
        sector[1], "sector end", minimum=-MAX_ABS_THETA_DEG,
        maximum=MAX_ABS_THETA_DEG,
    )
    if end <= start:
        raise ValueError("sector end must be greater than sector start")
    return (start, end)


def categorize_structure_interaction(structure, wavelength_m):
    """Categorize one nearby structure as blockage, scattering or negligible."""
    if not isinstance(structure, dict):
        raise ValueError("structure must be a mapping")
    wavelength = _require_number(wavelength_m, "wavelength_m")
    if wavelength <= 0.0:
        raise ValueError("wavelength_m must be greater than zero")
    _require_text(structure.get("id"), "structure id")
    size = _require_number(structure.get("size_m"), "size_m")
    if size <= 0.0:
        raise ValueError("size_m must be greater than zero")
    distance = _require_number(structure.get("distance_m"), "distance_m")
    if distance <= 0.0:
        raise ValueError("distance_m must be greater than zero")
    surface = _require_text(structure.get("surface"), "surface")
    if surface not in SURFACES:
        raise ValueError("unknown structure surface: %r" % structure.get("surface"))
    obscures = structure.get("obscures_boresight_path", False)
    if not isinstance(obscures, bool):
        raise ValueError("obscures_boresight_path must be a boolean")
    _normalize_sector(structure.get("sector_deg"))
    ratio = size / wavelength
    if ratio < NEGLIGIBLE_SIZE_RATIO:
        return "negligible"
    if obscures and ratio >= BLOCKAGE_SIZE_RATIO:
        return "blockage"
    if obscures:
        return "scattering"
    if surface == "conductive":
        return "scattering"
    if ratio < DIELECTRIC_SCATTER_RATIO:
        return "negligible"
    return "scattering"


def derive_perturbation_db(interaction, size_ratio):
    """Default worst-case perturbation from a structure's size in wavelengths."""
    kind = _require_text(interaction, "interaction")
    ratio = _require_number(size_ratio, "size_ratio")
    if ratio <= 0.0:
        raise ValueError("size_ratio must be greater than zero")
    if kind == "negligible":
        return 0.0
    if kind == "blockage":
        return min(MAX_BLOCKAGE_DB, 10.0 * math.log10(1.0 + ratio))
    if kind == "scattering":
        return min(MAX_RIPPLE_DB, 3.0 * math.log10(1.0 + ratio))
    raise ValueError("unknown interaction: %r" % (interaction,))


def apply_structure_effects(
    samples, structures, wavelength_m, guard_deg=DEFAULT_GUARD_DEG
):
    """Perturb a free-space cut with blockage and scattering, worst case."""
    cut = validate_pattern_cut(samples)
    if not isinstance(structures, (list, tuple)):
        raise ValueError("structures must be a list or tuple")
    wavelength = _require_number(wavelength_m, "wavelength_m")
    if wavelength <= 0.0:
        raise ValueError("wavelength_m must be greater than zero")
    guard = _require_number(guard_deg, "guard_deg", minimum=0.0)
    perturbed = [[theta, gain] for theta, gain in cut]
    for structure in structures:
        interaction = categorize_structure_interaction(structure, wavelength)
        if interaction == "negligible":
            continue
        start, end = _normalize_sector(structure["sector_deg"])
        ratio = float(structure["size_m"]) / wavelength
        level = structure.get("perturbation_db")
        if level is None:
            level = derive_perturbation_db(interaction, ratio)
        else:
            level = _require_number(level, "perturbation_db", minimum=0.0)
        for row in perturbed:
            theta = row[0]
            if start <= theta <= end:
                row[1] -= level
            elif (start - guard) <= theta <= (end + guard):
                row[1] -= level / 2.0
    return [(theta, gain) for theta, gain in perturbed]


def _sin_weight(theta0_deg, theta1_deg):
    """Solid-angle weight of an angular segment: integral of sin|theta|."""
    low, high = sorted((theta0_deg, theta1_deg))
    if low < 0.0 < high:
        return _sin_weight(low, 0.0) + _sin_weight(0.0, high)
    a = math.radians(abs(low))
    b = math.radians(abs(high))
    lo, hi = sorted((a, b))
    return math.cos(lo) - math.cos(hi)


def coverage_fraction(samples, threshold_dbi):
    """Solid-angle-weighted fraction of the cut at or above a gain."""
    cut = validate_pattern_cut(samples)
    threshold = _require_number(
        threshold_dbi, "threshold_dbi", minimum=MIN_GAIN_DBI, maximum=MAX_GAIN_DBI
    )
    total = 0.0
    above = 0.0
    for (theta0, gain0), (theta1, gain1) in zip(cut, cut[1:]):
        weight = _sin_weight(theta0, theta1)
        total += weight
        first = _not_less(gain0, threshold)
        second = _not_less(gain1, threshold)
        if first and second:
            above += weight
        elif not first and not second:
            continue
        else:
            crossing = theta0 + (threshold - gain0) * (theta1 - theta0) / (
                gain1 - gain0
            )
            if first:
                above += _sin_weight(theta0, crossing)
            else:
                above += _sin_weight(crossing, theta1)
    if total <= 0.0:
        raise ValueError("pattern cut spans no solid angle")
    return above / total


def assess_pattern_compliance(samples, requirement, structures, wavelength_m):
    """Characterize a cut with its structures and grade it against the link."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    cone = _require_number(
        requirement.get("cone_half_angle_deg"), "cone_half_angle_deg"
    )
    if cone <= 0.0:
        raise ValueError("cone_half_angle_deg must be greater than zero")
    min_gain = _require_number(
        requirement.get("min_gain_dbi"), "min_gain_dbi",
        minimum=MIN_GAIN_DBI, maximum=MAX_GAIN_DBI,
    )
    min_coverage = _require_number(
        requirement.get("min_coverage_fraction", 0.0), "min_coverage_fraction",
        minimum=0.0, maximum=1.0,
    )
    step_limit = requirement.get("max_step_deg", DEFAULT_MAX_STEP_DEG)
    findings = list(check_angular_sampling(samples, step_limit))
    installed = apply_structure_effects(samples, structures, wavelength_m)
    free_space_worst = worst_case_gain_in_cone(samples, cone)
    installed_worst = worst_case_gain_in_cone(installed, cone)
    fraction = coverage_fraction(installed, min_gain)
    if not _not_less(installed_worst, min_gain):
        findings.append(
            "installed worst-case gain of %.3g dBi inside the coverage-cone is "
            "below the required %.3g dBi" % (installed_worst, min_gain)
        )
    if not _not_less(fraction, min_coverage):
        findings.append(
            "coverage-fraction of %.3g above the threshold-gain is below the "
            "required %.3g" % (fraction, min_coverage)
        )
    interactions = {}
    for structure in structures:
        interactions[_require_text(structure.get("id"), "structure id")] = (
            categorize_structure_interaction(structure, wavelength_m)
        )
    return {
        "installed_cut": installed,
        "free_space_worst_gain_dbi": free_space_worst,
        "installed_worst_gain_dbi": installed_worst,
        "structure_degradation_db": free_space_worst - installed_worst,
        "coverage_fraction": fraction,
        "interactions": interactions,
        "findings": findings,
        "compliant": not findings,
    }
