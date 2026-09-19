"""Fracture toughness and crack growth testing of metallic materials.

Anchor: ECSS-Q-ST-70-45, methods clause, generating the fracture data a
damage tolerance assessment to ECSS-E-ST-32-01 consumes -- a pre-cracked
compact specimen is loaded to a conditional toughness, the result is tested
against the plane-strain size criterion, and cyclic growth is reduced to a
rate law. Paraphrased into an implementable procedure; no standard text is
reproduced.

What this module decides
------------------------
Whether a toughness test produced a plane-strain material property or only a
number for that specimen, and what growth rate the cyclic data supports.

1. The conditional toughness comes first. It is computed from the load, the
   section and the geometry factor at the measured crack depth, and only then
   is it eligible to be a material property.
2. Validity is a size question. The thickness, the crack depth and the
   remaining ligament each have to exceed a requirement that scales with the
   square of the toughness-to-yield ratio; failing any one of them leaves a
   specimen-specific number.
3. The load record has to behave. A maximum load far above the conditional
   load means the specimen was tearing, not cracking, before it broke.
4. Growth data is a power law in the cyclic stress intensity, fitted in
   logarithms, and it is only as wide as the range of stress intensity that
   was actually cycled.
"""

import math

__all__ = [
    "CT_ALPHA_BAND",
    "SIZE_FACTOR",
    "PMAX_PQ_LIMIT",
    "MIN_GROWTH_POINTS",
    "ct_geometry_factor",
    "conditional_toughness",
    "plane_strain_size_requirement_mm",
    "size_findings",
    "load_record_findings",
    "fit_paris_law",
    "growth_rate_at",
    "assess_fracture_test",
]

# Crack depth as a fraction of specimen width, over which the compact
# specimen geometry factor is defined.
CT_ALPHA_BAND = (0.45, 0.70)

# Multiplier on the squared toughness-to-yield ratio in the size criterion.
SIZE_FACTOR = 2.5

# How far the maximum load may exceed the conditional load.
PMAX_PQ_LIMIT = 1.10

# A line through two points is not a growth law.
MIN_GROWTH_POINTS = 3

# Comparisons at a limit are inclusive; absorb representation error there.
REL_TOLERANCE = 1e-9


def _as_finite_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_finite_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _slack(reference):
    return REL_TOLERANCE * max(abs(reference), 1.0)


def ct_geometry_factor(alpha):
    """Return the compact specimen geometry factor at a crack depth ratio."""
    ratio = _as_positive_float(alpha, "alpha")
    low, high = CT_ALPHA_BAND
    if ratio < low - _slack(low) or ratio > high + _slack(high):
        raise ValueError(
            "crack depth ratio %.4f is outside the %.2f to %.2f range the "
            "compact specimen factor is defined over" % (ratio, low, high)
        )
    a2 = ratio * ratio
    a3 = a2 * ratio
    a4 = a3 * ratio
    bracket = 0.886 + 4.64 * ratio - 13.32 * a2 + 14.72 * a3 - 5.6 * a4
    remainder = 1.0 - ratio
    return (2.0 + ratio) * bracket / (remainder * math.sqrt(remainder))


def conditional_toughness(load_n, thickness_mm, width_mm, alpha):
    """Return the conditional toughness in MPa root-metre from the load record."""
    load = _as_positive_float(load_n, "load_n")
    thickness_m = _as_positive_float(thickness_mm, "thickness_mm") / 1000.0
    width_m = _as_positive_float(width_mm, "width_mm") / 1000.0
    factor = ct_geometry_factor(alpha)
    pascal_root_metre = load / (thickness_m * math.sqrt(width_m)) * factor
    return pascal_root_metre / 1.0e6


def plane_strain_size_requirement_mm(toughness, yield_strength_mpa):
    """Return the dimension every controlling length has to reach, in mm."""
    k = _as_positive_float(toughness, "toughness")
    yield_strength = _as_positive_float(yield_strength_mpa, "yield_strength_mpa")
    ratio = k / yield_strength
    return SIZE_FACTOR * ratio * ratio * 1000.0


def size_findings(requirement_mm, thickness_mm, crack_length_mm, ligament_mm):
    """Return findings for each controlling length that misses the requirement."""
    needed = _as_positive_float(requirement_mm, "requirement_mm")
    lengths = (
        ("thickness", _as_positive_float(thickness_mm, "thickness_mm")),
        ("crack depth", _as_positive_float(crack_length_mm, "crack_length_mm")),
        ("remaining ligament", _as_positive_float(ligament_mm, "ligament_mm")),
    )
    findings = []
    for name, value in lengths:
        if value < needed - _slack(needed):
            findings.append(
                "%s of %.4f mm is below the %.4f mm the plane-strain size "
                "criterion requires" % (name, value, needed)
            )
    return findings


def load_record_findings(load_pq_n, load_pmax_n):
    """Return findings for a load record whose maximum ran away from P sub Q."""
    conditional = _as_positive_float(load_pq_n, "load_pq_n")
    maximum = _as_positive_float(load_pmax_n, "load_pmax_n")
    findings = []
    if maximum < conditional - _slack(conditional):
        findings.append(
            "maximum load %.2f N is below the conditional load %.2f N; the "
            "record is not a valid toughness test" % (maximum, conditional)
        )
        return findings
    ratio = maximum / conditional
    if ratio > PMAX_PQ_LIMIT + _slack(PMAX_PQ_LIMIT):
        findings.append(
            "maximum load is %.4f times the conditional load, above the %.2f "
            "limit; the specimen tore before it broke" % (ratio, PMAX_PQ_LIMIT)
        )
    return findings


def fit_paris_law(points):
    """Return the power-law growth fit over cyclic stress intensity.

    Each point carries delta_k (MPa root-metre) and rate_m_per_cycle. The
    relation fitted is log10(rate) = log10(C) + exponent * log10(delta_k).
    """
    if not isinstance(points, (list, tuple)) or len(points) < MIN_GROWTH_POINTS:
        raise ValueError(
            "a growth law needs at least %d points" % MIN_GROWTH_POINTS
        )
    xs = []
    ys = []
    for i, item in enumerate(points):
        if not isinstance(item, dict):
            raise ValueError("growth point %d must be a mapping" % i)
        for key in ("delta_k", "rate_m_per_cycle"):
            if key not in item:
                raise ValueError("growth point %d is missing '%s'" % (i, key))
        xs.append(math.log10(_as_positive_float(item["delta_k"],
                                                "point %d delta_k" % i)))
        ys.append(math.log10(_as_positive_float(item["rate_m_per_cycle"],
                                                "point %d rate_m_per_cycle" % i)))
    n = float(len(xs))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = 0.0
    sxy = 0.0
    for x, y in zip(xs, ys):
        sxx += (x - mean_x) * (x - mean_x)
        sxy += (x - mean_x) * (y - mean_y)
    if sxx <= 0.0:
        raise ValueError(
            "every growth point sits at the same cyclic stress intensity"
        )
    exponent = sxy / sxx
    intercept = mean_y - exponent * mean_x
    if exponent <= 0.0:
        raise ValueError(
            "the growth law falls with cyclic stress intensity; the data is "
            "not a crack growth curve"
        )
    return {
        "log10_coefficient": intercept,
        "exponent": exponent,
        "points_used": len(xs),
        "delta_k_min": 10.0 ** min(xs),
        "delta_k_max": 10.0 ** max(xs),
    }


def growth_rate_at(fit, delta_k):
    """Return the growth rate the fitted law places at a cyclic intensity.

    The law is not extrapolated: a cyclic intensity outside the range that was
    cycled has no fitted rate and raises instead of returning one.
    """
    if not isinstance(fit, dict):
        raise ValueError("fit must be a mapping")
    for key in ("log10_coefficient", "exponent", "delta_k_min", "delta_k_max"):
        if key not in fit:
            raise ValueError("fit is missing '%s'" % key)
    value = _as_positive_float(delta_k, "delta_k")
    low = _as_positive_float(fit["delta_k_min"], "delta_k_min")
    high = _as_positive_float(fit["delta_k_max"], "delta_k_max")
    if value < low - _slack(low) or value > high + _slack(high):
        raise ValueError(
            "%.4f is outside the cycled range %.4f to %.4f; the growth law is "
            "not extrapolated" % (value, low, high)
        )
    intercept = _as_finite_float(fit["log10_coefficient"], "log10_coefficient")
    exponent = _as_finite_float(fit["exponent"], "exponent")
    return 10.0 ** (intercept + exponent * math.log10(value))


def assess_fracture_test(spec):
    """Judge one toughness test and, when present, its crack growth data.

    spec keys: load_pq_n, load_pmax_n, thickness_mm, width_mm,
    crack_length_mm, yield_strength_mpa; optional growth_points.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("load_pq_n", "load_pmax_n", "thickness_mm", "width_mm",
                "crack_length_mm", "yield_strength_mpa"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    width = _as_positive_float(spec["width_mm"], "width_mm")
    crack = _as_positive_float(spec["crack_length_mm"], "crack_length_mm")
    if crack >= width:
        raise ValueError(
            "crack depth %.4f mm is not inside a specimen %.4f mm wide"
            % (crack, width)
        )
    alpha = crack / width
    ligament = width - crack
    factor = ct_geometry_factor(alpha)
    toughness = conditional_toughness(
        spec["load_pq_n"], spec["thickness_mm"], width, alpha
    )
    requirement = plane_strain_size_requirement_mm(
        toughness, spec["yield_strength_mpa"]
    )

    findings = []
    findings.extend(load_record_findings(spec["load_pq_n"], spec["load_pmax_n"]))
    findings.extend(
        size_findings(requirement, spec["thickness_mm"], crack, ligament)
    )

    growth = None
    if spec.get("growth_points") is not None:
        growth = fit_paris_law(spec["growth_points"])

    return {
        "crack_depth_ratio": alpha,
        "geometry_factor": factor,
        "conditional_toughness": toughness,
        "size_requirement_mm": requirement,
        "remaining_ligament_mm": ligament,
        "growth_law": growth,
        "findings": findings,
        "plane_strain_valid": not findings,
        "reportable_toughness": toughness if not findings else None,
    }
