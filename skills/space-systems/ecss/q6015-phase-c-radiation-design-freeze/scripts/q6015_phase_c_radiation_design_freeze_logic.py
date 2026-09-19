"""Phase C characterization, equipment shielding and the hardness baseline freeze.

Anchor: ECSS-Q-ST-60-15C clause 4.4.3 (characterization testing, equipment
level shielding assessment and locking the hardness assurance baseline at the
critical design review). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Reduce a characterization lot sample to a design capability through a
   one-sided tolerance limit, so a small sample is penalised for its own
   uncertainty rather than being read at its mean.
2. Assess the equipment level shielding: add the spot shield to the inherent
   thickness, read the dose-depth curve at the total, and price the addition
   in mass.
3. Apply the design factor to obtain the specified level, take the radiation
   design margin of every part against it, and decide whether the hardness
   assurance baseline may be frozen at the critical design review.
"""

import math

__all__ = [
    "TOLERANCE_FACTORS",
    "MIN_CHARACTERIZATION_SAMPLE",
    "MARGIN_TOLERANCE",
    "tolerance_factor",
    "sample_mean",
    "sample_stdev",
    "characterized_capability",
    "total_shielding_mm",
    "shielded_dose",
    "spot_shield_mass_kg",
    "radiation_design_margin",
    "assess_part_freeze",
    "assess_design_freeze",
]

# One-sided tolerance factors keyed by characterization sample size. A sample
# between two tabulated sizes is read at the lower one, never interpolated up.
TOLERANCE_FACTORS = {
    3: 7.655,
    4: 5.145,
    5: 4.202,
    6: 3.707,
    7: 3.399,
    8: 3.188,
    10: 2.911,
    12: 2.736,
    15: 2.566,
    20: 2.396,
    25: 2.292,
    30: 2.220,
    40: 2.125,
    50: 2.065,
}

MIN_CHARACTERIZATION_SAMPLE = min(TOLERANCE_FACTORS)

# Margin comparisons are ratios of reduced test data; absorb the
# representation error at the bound rather than moving the bound.
MARGIN_TOLERANCE = 1e-9


def _positive(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def tolerance_factor(sample_size):
    """Return the one-sided tolerance factor for a characterization sample."""
    if not isinstance(sample_size, int) or isinstance(sample_size, bool):
        raise ValueError("sample_size must be an integer, got %r" % (sample_size,))
    if sample_size < MIN_CHARACTERIZATION_SAMPLE:
        raise ValueError(
            "a characterization sample of %d is below the minimum of %d"
            % (sample_size, MIN_CHARACTERIZATION_SAMPLE)
        )
    tabulated = [n for n in sorted(TOLERANCE_FACTORS) if n <= sample_size]
    return TOLERANCE_FACTORS[tabulated[-1]]


def _sample(values):
    if not isinstance(values, (list, tuple)) or len(values) < 2:
        raise ValueError("a characterization sample needs at least two results")
    numbers = []
    for index, value in enumerate(values):
        numbers.append(_positive("characterization result %d" % index, value))
    return numbers


def sample_mean(values):
    """Return the arithmetic mean of a characterization sample."""
    numbers = _sample(values)
    return sum(numbers) / len(numbers)


def sample_stdev(values):
    """Return the sample standard deviation of a characterization sample."""
    numbers = _sample(values)
    mean = sum(numbers) / len(numbers)
    variance = sum((value - mean) ** 2 for value in numbers) / (len(numbers) - 1)
    return math.sqrt(variance)


def characterized_capability(values):
    """Reduce a characterization sample to its one-sided design capability."""
    numbers = _sample(values)
    factor = tolerance_factor(len(numbers))
    return sample_mean(numbers) - factor * sample_stdev(numbers)


def total_shielding_mm(inherent_mm, spot_mm=0.0):
    """Return the total shielding an equipment location presents."""
    inherent = _positive("inherent_mm", inherent_mm)
    if not isinstance(spot_mm, (int, float)) or isinstance(spot_mm, bool):
        raise ValueError("spot_mm must be a real number")
    spot = float(spot_mm)
    if not math.isfinite(spot) or spot < 0.0:
        raise ValueError("spot_mm must be non-negative and finite, got %r" % (spot_mm,))
    return inherent + spot


def shielded_dose(curve, inherent_mm, spot_mm=0.0):
    """Return the dose behind the total equipment shielding."""
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("dose-depth curve needs at least two (thickness, dose) points")
    points = []
    for index, item in enumerate(curve):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("dose-depth point %d must be a (thickness_mm, dose) pair" % index)
        x = _positive("dose-depth point %d thickness" % index, item[0])
        y = _positive("dose-depth point %d dose" % index, item[1])
        points.append((x, y))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError("dose-depth thicknesses must strictly increase (index %d)" % index)
    thickness = total_shielding_mm(inherent_mm, spot_mm)
    lo, hi = points[0][0], points[-1][0]
    if thickness < lo or thickness > hi:
        raise ValueError(
            "dose-depth curve spans [%g, %g] mm; %g mm is outside it, extrapolation refused"
            % (lo, hi, thickness)
        )
    for index in range(1, len(points)):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        if thickness <= x1:
            if thickness == x0:
                return y0
            if thickness == x1:
                return y1
            t = (math.log(thickness) - math.log(x0)) / (math.log(x1) - math.log(x0))
            return math.exp(math.log(y0) + t * (math.log(y1) - math.log(y0)))
    return points[-1][1]


def spot_shield_mass_kg(area_cm2, spot_mm, density_g_cm3):
    """Return the mass a spot shield of a given footprint and thickness costs."""
    area = _positive("area_cm2", area_cm2)
    density = _positive("density_g_cm3", density_g_cm3)
    if not isinstance(spot_mm, (int, float)) or isinstance(spot_mm, bool):
        raise ValueError("spot_mm must be a real number")
    spot = float(spot_mm)
    if not math.isfinite(spot) or spot < 0.0:
        raise ValueError("spot_mm must be non-negative and finite")
    return area * (spot / 10.0) * density / 1000.0


def radiation_design_margin(capability, specified_level):
    """Return the ratio of a design capability to the level specified for it."""
    return _positive("capability", capability) / _positive("specified_level", specified_level)


def assess_part_freeze(part, specified_level, required_margin):
    """Decide whether one part is ready to be frozen into the baseline."""
    if not isinstance(part, dict):
        raise ValueError("part record must be a mapping")
    reference = part.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("part record must carry a non-empty 'reference'")
    level = _positive("specified_level", specified_level)
    required = _positive("required_margin", required_margin)
    results = part.get("characterization_results")
    if results is None:
        return {
            "reference": reference.strip(),
            "capability": None,
            "margin": None,
            "ready": False,
            "blocker": "no characterization data on record",
        }
    capability = characterized_capability(results)
    if capability <= 0.0:
        return {
            "reference": reference.strip(),
            "capability": capability,
            "margin": None,
            "ready": False,
            "blocker": "the characterization spread leaves no usable design capability",
        }
    margin = radiation_design_margin(capability, level)
    meets = margin > required or math.isclose(
        margin, required, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    return {
        "reference": reference.strip(),
        "capability": capability,
        "margin": margin,
        "ready": meets,
        "blocker": None
        if meets
        else "margin %.4f is below the required %.4f" % (margin, required),
    }


def assess_design_freeze(spec):
    """Run the clause 4.4.3 freeze assessment for one equipment.

    spec keys: parts, dose_depth_curve, inherent_shielding_mm, design_factor,
    required_margin; optional spot_shield_mm, spot_shield_area_cm2,
    spot_shield_density_g_cm3, shielding_mass_allocation_kg, open_waivers.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "parts",
        "dose_depth_curve",
        "inherent_shielding_mm",
        "design_factor",
        "required_margin",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    parts = spec["parts"]
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("parts must be a non-empty sequence of part records")
    spot = spec.get("spot_shield_mm", 0.0)
    location_dose = shielded_dose(spec["dose_depth_curve"], spec["inherent_shielding_mm"], spot)
    factor = _positive("design_factor", spec["design_factor"])
    specified_level = location_dose * factor
    required = _positive("required_margin", spec["required_margin"])
    assessed = [assess_part_freeze(part, specified_level, required) for part in parts]
    assessed.sort(key=lambda item: item["reference"])
    blockers = []
    for item in assessed:
        if item["blocker"] is not None:
            blockers.append("part %s: %s" % (item["reference"], item["blocker"]))
    mass_kg = None
    if spec.get("spot_shield_area_cm2") is not None:
        mass_kg = spot_shield_mass_kg(
            spec["spot_shield_area_cm2"], spot, spec.get("spot_shield_density_g_cm3", 2.70)
        )
        allocation = spec.get("shielding_mass_allocation_kg")
        if allocation is not None:
            allowed = _positive("shielding_mass_allocation_kg", allocation)
            if mass_kg > allowed and not math.isclose(
                mass_kg, allowed, rel_tol=0.0, abs_tol=1e-12
            ):
                blockers.append(
                    "spot shield mass %.4f kg exceeds the %.4f kg allocation"
                    % (mass_kg, allowed)
                )
    waivers = spec.get("open_waivers", ())
    if not isinstance(waivers, (list, tuple)):
        raise ValueError("open_waivers must be a sequence")
    for waiver in waivers:
        if not isinstance(waiver, str) or not waiver.strip():
            raise ValueError("an open waiver must be a non-empty string")
        blockers.append("open radiation waiver: %s" % waiver.strip())
    return {
        "location_dose_krad": location_dose,
        "total_shielding_mm": total_shielding_mm(spec["inherent_shielding_mm"], spot),
        "specified_level_krad": specified_level,
        "required_margin": required,
        "parts": assessed,
        "spot_shield_mass_kg": mass_kg,
        "blockers": blockers,
        "freeze_allowed": not blockers,
    }
