"""Displacement damage dose assurance for radiation-sensitive parts.

Anchor: ECSS-Q-ST-60-15C clause 5.2 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Work out the non-ionising dose a part receives. The shielding
   around a part is not one thickness, so the displacement damage dose
   is accumulated over directions: either a statistical sector ray
   trace, where the sphere around the part is divided into solid-angle
   sectors each carrying one equivalent aluminium thickness, or a
   Monte Carlo ray trace, where a sample of rays is drawn and the dose
   is their mean.
2. Say how much the Monte Carlo answer is worth. A sampled mean comes
   with a standard error; too few rays, or a spread too wide for the
   rays drawn, and the number is not yet an answer.
3. Divide the part's demonstrated displacement damage capability by
   that dose to get the achieved margin, and compare it with the
   minimum margin this clause holds every part to.
4. Insist on a test where the part family needs one. Devices whose
   function depends on minority-carrier lifetime -- optocouplers,
   bipolar linear parts, imaging detectors, solar cells, laser diodes
   -- are not covered by ionising dose data, and a margin computed
   against a capability with no displacement damage test behind it is
   arithmetic without evidence.
5. Aggregate: the tightest part drives the verdict, and the method
   used is reported with it so a wide margin resting on an under-
   sampled ray trace is visible.

Stdlib only, offline, deterministic.
"""

import math
import statistics

METHOD_SECTOR = "statistical-sector-ray-trace"
METHOD_MONTE_CARLO = "monte-carlo-ray-trace"
VALID_METHODS = (METHOD_SECTOR, METHOD_MONTE_CARLO)

# Minimum displacement damage design margin every part is held to.
MINIMUM_DDD_DESIGN_MARGIN = 2.0

# Monte Carlo ray trace acceptance: a minimum sample, and a ceiling on
# the standard error of the mean relative to the mean itself.
MINIMUM_RAY_COUNT = 50
MAX_RELATIVE_STANDARD_ERROR = 0.05

# Solid-angle fractions of a sector set have to close the sphere.
SOLID_ANGLE_CLOSURE_TOLERANCE = 1.0e-9

# A margin is a quotient of interpolated floats; this relative
# tolerance lets a part sitting exactly on the minimum margin pass
# without the minimum itself being moved.
MARGIN_RELATIVE_TOLERANCE = 1.0e-9

# Part families whose degradation is driven by displacement damage and
# which therefore owe a displacement damage test of their own.
DISPLACEMENT_SENSITIVE_FAMILIES = (
    "optocoupler",
    "bipolar-linear",
    "bipolar-digital",
    "imaging-detector",
    "solar-cell",
    "laser-diode",
    "photodiode",
)

FINDING_MARGIN_SHORTFALL = "displacement-margin-below-minimum"
FINDING_CAPABILITY_BELOW_DOSE = "capability-below-displacement-dose"
FINDING_TEST_REQUIRED = "displacement-damage-test-required"
FINDING_RAYS_TOO_FEW = "monte-carlo-ray-count-below-minimum"
FINDING_SAMPLING_NOISY = "monte-carlo-standard-error-above-ceiling"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def validate_ddd_depth_curve(curve):
    """Validate a displacement-damage-dose against shielding curve."""
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("ddd depth curve needs at least two points")
    points = []
    previous_thickness = None
    previous_dose = None
    for index, point in enumerate(curve):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("curve point %d must be a (thickness, ddd) pair" % index)
        thickness = _numeric("curve point %d thickness_mm" % index, point[0])
        dose = _numeric("curve point %d ddd_mev_per_g" % index, point[1])
        if thickness <= 0.0:
            raise ValueError("curve point %d thickness_mm must be positive" % index)
        if dose <= 0.0:
            raise ValueError("curve point %d ddd_mev_per_g must be positive" % index)
        if previous_thickness is not None and thickness <= previous_thickness:
            raise ValueError("curve thickness_mm must be strictly ascending")
        if previous_dose is not None and dose > previous_dose:
            raise ValueError("curve ddd_mev_per_g must not rise with shielding")
        previous_thickness = thickness
        previous_dose = dose
        points.append((thickness, dose))
    return tuple(points)


def ddd_at_shielding(curve, thickness_mm):
    """Displacement damage dose at one equivalent aluminium thickness."""
    points = validate_ddd_depth_curve(curve)
    thickness = _numeric("thickness_mm", thickness_mm)
    if thickness <= 0.0:
        raise ValueError("thickness_mm must be positive")
    low = points[0][0]
    high = points[-1][0]
    if thickness < low or thickness > high:
        raise ValueError(
            "thickness_mm %r is outside the tabulated span %r..%r; obtain "
            "curve data covering it rather than extrapolating"
            % (thickness, low, high)
        )
    for (t0, d0), (t1, d1) in zip(points, points[1:]):
        if t0 <= thickness <= t1:
            if d0 == d1:
                return d0
            fraction = (math.log(thickness) - math.log(t0)) / (
                math.log(t1) - math.log(t0)
            )
            return math.exp(math.log(d0) + fraction * (math.log(d1) - math.log(d0)))
    return points[-1][1]


def validate_sectors(sectors):
    """Validate a sector set and return it as normalized tuples."""
    if not isinstance(sectors, (list, tuple)) or not sectors:
        raise ValueError("sectors must be a non-empty sequence")
    normalized = []
    total = 0.0
    for index, sector in enumerate(sectors):
        if isinstance(sector, dict):
            raw_fraction = sector.get("solid_angle_fraction")
            raw_thickness = sector.get("thickness_mm")
        elif isinstance(sector, (list, tuple)) and len(sector) == 2:
            raw_fraction, raw_thickness = sector
        else:
            raise ValueError(
                "sector %d must be a mapping or a (fraction, thickness) pair"
                % index
            )
        fraction = _numeric(
            "sector %d solid_angle_fraction" % index, raw_fraction
        )
        if fraction <= 0.0:
            raise ValueError("sector %d solid_angle_fraction must be positive" % index)
        thickness = _numeric("sector %d thickness_mm" % index, raw_thickness)
        if thickness <= 0.0:
            raise ValueError("sector %d thickness_mm must be positive" % index)
        total += fraction
        normalized.append((fraction, thickness))
    if abs(total - 1.0) > SOLID_ANGLE_CLOSURE_TOLERANCE:
        raise ValueError(
            "sector solid_angle_fraction values sum to %r, must close the "
            "sphere at 1.0" % (total,)
        )
    return tuple(normalized)


def sector_ray_trace_ddd(curve, sectors):
    """Solid-angle weighted displacement damage dose over a sector set."""
    normalized = validate_sectors(sectors)
    total = 0.0
    for fraction, thickness in normalized:
        total += fraction * ddd_at_shielding(curve, thickness)
    return total


def monte_carlo_ray_trace_ddd(curve, ray_thicknesses):
    """Mean displacement damage dose over a sample of traced rays."""
    if not isinstance(ray_thicknesses, (list, tuple)) or len(ray_thicknesses) < 2:
        raise ValueError("ray_thicknesses needs at least two rays")
    doses = []
    for index, thickness in enumerate(ray_thicknesses):
        value = _numeric("ray %d thickness_mm" % index, thickness)
        if value <= 0.0:
            raise ValueError("ray %d thickness_mm must be positive" % index)
        doses.append(ddd_at_shielding(curve, value))
    count = len(doses)
    mean = statistics.fmean(doses)
    spread = statistics.stdev(doses)
    standard_error = spread / math.sqrt(count)
    relative = standard_error / mean if mean > 0.0 else float("inf")
    return {
        "ray_count": count,
        "mean_ddd_mev_per_g": mean,
        "sample_stdev": spread,
        "standard_error": standard_error,
        "relative_standard_error": relative,
    }


def monte_carlo_findings(sampling):
    """Findings about the quality of a Monte Carlo ray-trace result."""
    if not isinstance(sampling, dict):
        raise ValueError("sampling must be a mapping")
    count = sampling.get("ray_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 2:
        raise ValueError("sampling ray_count must be an integer of at least 2")
    relative = _numeric(
        "sampling relative_standard_error", sampling.get("relative_standard_error"), 0.0
    )
    findings = []
    if count < MINIMUM_RAY_COUNT:
        findings.append(FINDING_RAYS_TOO_FEW)
    if relative > MAX_RELATIVE_STANDARD_ERROR * (1.0 + MARGIN_RELATIVE_TOLERANCE):
        findings.append(FINDING_SAMPLING_NOISY)
    return findings


def displacement_test_required(family):
    """True when a part family owes a displacement damage test."""
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string")
    return family in DISPLACEMENT_SENSITIVE_FAMILIES


def achieved_displacement_margin(capability_mev_per_g, ddd_mev_per_g):
    """Achieved displacement damage margin, capability over dose."""
    capability = _numeric("capability_mev_per_g", capability_mev_per_g, 0.0)
    dose = _numeric("ddd_mev_per_g", ddd_mev_per_g)
    if dose <= 0.0:
        raise ValueError("ddd_mev_per_g must be positive")
    return capability / dose


def margin_meets_minimum(achieved, minimum=MINIMUM_DDD_DESIGN_MARGIN):
    """True when an achieved margin meets the minimum at equality."""
    achieved = _numeric("achieved", achieved, 0.0)
    minimum = _numeric("minimum", minimum)
    if minimum <= 0.0:
        raise ValueError("minimum margin must be positive")
    return achieved >= minimum * (1.0 - MARGIN_RELATIVE_TOLERANCE)


def validate_part(part):
    """Validate one part record and return a normalized copy."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    part_id = part.get("id")
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part needs a non-empty string id")
    family = part.get("family")
    if not isinstance(family, str) or not family.strip():
        raise ValueError("part %s needs a non-empty family" % part_id)
    method = part.get("method")
    if method not in VALID_METHODS:
        raise ValueError(
            "part %s has unknown method %r (expected one of %s)"
            % (part_id, method, ", ".join(VALID_METHODS))
        )
    capability = _numeric(
        "part %s capability_mev_per_g" % part_id, part.get("capability_mev_per_g")
    )
    if capability <= 0.0:
        raise ValueError("part %s capability_mev_per_g must be positive" % part_id)
    reference = part.get("test_reference")
    if reference is not None and (
        not isinstance(reference, str) or not reference.strip()
    ):
        raise ValueError("part %s test_reference must be a non-empty string" % part_id)
    if method == METHOD_SECTOR:
        sectors = validate_sectors(part.get("sectors"))
        rays = None
    else:
        sectors = None
        rays = part.get("ray_thicknesses_mm")
        if not isinstance(rays, (list, tuple)) or len(rays) < 2:
            raise ValueError(
                "part %s needs at least two ray_thicknesses_mm for a Monte "
                "Carlo trace" % part_id
            )
        rays = tuple(rays)
    return {
        "id": part_id,
        "family": family,
        "method": method,
        "capability_mev_per_g": capability,
        "test_reference": reference,
        "sectors": sectors,
        "ray_thicknesses_mm": rays,
    }


def assess_part(part, curve):
    """Assess one part against the clause 5.2 displacement requirement."""
    norm = validate_part(part)
    findings = []
    sampling = None
    if norm["method"] == METHOD_SECTOR:
        dose = sector_ray_trace_ddd(curve, norm["sectors"])
    else:
        sampling = monte_carlo_ray_trace_ddd(curve, norm["ray_thicknesses_mm"])
        dose = sampling["mean_ddd_mev_per_g"]
        findings.extend(monte_carlo_findings(sampling))
    achieved = achieved_displacement_margin(norm["capability_mev_per_g"], dose)
    if displacement_test_required(norm["family"]) and not norm["test_reference"]:
        findings.append(FINDING_TEST_REQUIRED)
    if achieved < 1.0 - MARGIN_RELATIVE_TOLERANCE:
        findings.append(FINDING_CAPABILITY_BELOW_DOSE)
    if not margin_meets_minimum(achieved):
        findings.append(FINDING_MARGIN_SHORTFALL)
    return {
        "id": norm["id"],
        "family": norm["family"],
        "method": norm["method"],
        "ddd_mev_per_g": dose,
        "achieved_margin": achieved,
        "minimum_margin": MINIMUM_DDD_DESIGN_MARGIN,
        "sampling": sampling,
        "test_reference": norm["test_reference"],
        "findings": findings,
        "compliant": not findings,
    }


def assess_displacement_damage_dose(parts, curve):
    """Run the clause 5.2 assessment over a list of parts."""
    if not isinstance(parts, list) or not parts:
        raise ValueError("parts must be a non-empty list")
    validate_ddd_depth_curve(curve)
    results = []
    seen = set()
    for part in parts:
        result = assess_part(part, curve)
        if result["id"] in seen:
            raise ValueError("duplicate part id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    tightest = min(results, key=lambda r: (r["achieved_margin"], r["id"]))
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    return {
        "parts": results,
        "tightest_part_id": tightest["id"],
        "tightest_margin": tightest["achieved_margin"],
        "test_required_ids": [
            r["id"] for r in results if FINDING_TEST_REQUIRED in r["findings"]
        ],
        "non_compliant_ids": non_compliant,
        "compliant": not non_compliant,
    }
