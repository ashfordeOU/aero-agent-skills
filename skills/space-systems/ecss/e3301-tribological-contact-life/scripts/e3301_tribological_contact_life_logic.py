"""Tribological contact-pair life demonstration for spacecraft mechanisms.

Anchor: ECSS-E-ST-33-01C clause 4.7.3.4.1 (demonstrate that a contact pair
survives the mission cycles, accounting for wear and material transfer, under
the worst-case combination of conditions). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Accumulate the sliding distance the contact pair actually sees: stroke,
   passes per cycle and mission cycles, including any ground-test cycles that
   are spent before flight.
2. Derate the nominal wear coefficient to the worst-case combination of
   environment conditions (vacuum, temperature, contamination, dwell, speed).
   A derating factor below unity is a relief and is refused: the clause asks
   for the worst case, not the nominal one.
3. Convert load and sliding distance into an Archard wear volume, then into a
   wear depth over the apparent contact area.
4. Take the limiting depth as the tighter of the allowable wear depth and the
   remaining thickness of a bonded dry-film coating, and report which one of
   the two governs.
5. Where the pair is self-lubricating, compute the sliding distance the
   transfer-film reservoir can sustain and the cycles that corresponds to, so
   film starvation can be seen to limit life before wear-through does.
6. Size the demonstration test: the cycles the life factor demands, and the
   ratio the cycles already run achieve against it.
"""

import math

__all__ = [
    "DEFAULT_LIFE_FACTOR",
    "DEPTH_TOLERANCE_MM",
    "ENVIRONMENT_FACTOR_KEYS",
    "sliding_distance_m",
    "worst_case_wear_coefficient",
    "archard_wear_volume_mm3",
    "wear_depth_mm",
    "limiting_wear_depth_mm",
    "transfer_limited_cycles",
    "required_test_cycles",
    "demonstrated_life_ratio",
    "assess_contact_life",
]

# Depth comparisons are differences of products of measured quantities; an
# exact equality at the limit can land a few ULPs on either side. Absorb the
# representation error here rather than by relaxing the allowable depth.
DEPTH_TOLERANCE_MM = 1e-12

# A life demonstration is not a one-for-one match of the mission cycles; the
# clause expects a factor on top. This is the default when none is declared.
DEFAULT_LIFE_FACTOR = 2.0

# The worst-case condition set a contact-pair derating is built from.
ENVIRONMENT_FACTOR_KEYS = (
    "vacuum",
    "temperature",
    "contamination",
    "dwell",
    "speed",
)


def _require_real(label, value):
    """Return value as a float, refusing anything that is not a real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(label, value):
    """Return value as a strictly positive float."""
    out = _require_real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return out


def _require_non_negative(label, value):
    """Return value as a non-negative float."""
    out = _require_real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def _require_count(label, value):
    """Return value as a strictly positive integer count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def sliding_distance_m(stroke_mm, passes_per_cycle, cycles, ground_test_cycles=0):
    """Return the total sliding distance in metres over mission plus ground use.

    One pass traverses the stroke once; a reciprocating contact makes two
    passes per cycle. Ground-test cycles are spent from the same life.
    """
    stroke = _require_positive("stroke_mm", stroke_mm)
    passes = _require_positive("passes_per_cycle", passes_per_cycle)
    mission = _require_count("cycles", cycles)
    if isinstance(ground_test_cycles, bool) or not isinstance(ground_test_cycles, int):
        raise ValueError("ground_test_cycles must be an integer, got %r" % (ground_test_cycles,))
    if ground_test_cycles < 0:
        raise ValueError("ground_test_cycles must be non-negative, got %d" % ground_test_cycles)
    total_cycles = mission + ground_test_cycles
    return stroke * passes * total_cycles / 1000.0


def worst_case_wear_coefficient(nominal_k, environment_factors=None):
    """Return the nominal wear coefficient derated to the worst-case condition set.

    Every declared factor multiplies the coefficient. A factor below unity
    would make the worst case milder than the nominal case and is refused;
    an unrecognised condition name is refused rather than silently ignored.
    """
    k = _require_positive("nominal_k", nominal_k)
    if environment_factors is None:
        return k
    if not isinstance(environment_factors, dict):
        raise ValueError("environment_factors must be a mapping of condition to factor")
    out = k
    for name, factor in environment_factors.items():
        if name not in ENVIRONMENT_FACTOR_KEYS:
            raise ValueError(
                "unknown environment condition %r; expected one of %s"
                % (name, ", ".join(ENVIRONMENT_FACTOR_KEYS))
            )
        value = _require_positive("environment factor %r" % (name,), factor)
        if value < 1.0:
            raise ValueError(
                "environment factor %r is %g; a worst-case derating cannot relieve the "
                "nominal wear coefficient" % (name, value)
            )
        out *= value
    return out


def archard_wear_volume_mm3(wear_coefficient, load_n, distance_m, hardness_mpa):
    """Return the Archard wear volume in mm^3 for a contact pair.

    V = k * F * s / H with the load in newtons, the sliding distance converted
    to millimetres and the hardness in MPa (N/mm^2), so the volume is mm^3.
    """
    k = _require_positive("wear_coefficient", wear_coefficient)
    load = _require_positive("load_n", load_n)
    distance = _require_non_negative("distance_m", distance_m)
    hardness = _require_positive("hardness_mpa", hardness_mpa)
    return k * load * (distance * 1000.0) / hardness


def wear_depth_mm(volume_mm3, contact_area_mm2):
    """Return the wear depth in mm spread over the apparent contact area."""
    volume = _require_non_negative("volume_mm3", volume_mm3)
    area = _require_positive("contact_area_mm2", contact_area_mm2)
    return volume / area


def limiting_wear_depth_mm(allowable_depth_mm, coating_thickness_mm=None):
    """Return the governing depth limit and the name of the limit that governs.

    A bonded dry-film coating cannot be worn past its own thickness, so the
    tighter of the two limits is the one the demonstration has to meet.
    """
    allowable = _require_positive("allowable_depth_mm", allowable_depth_mm)
    if coating_thickness_mm is None:
        return (allowable, "allowable-wear-depth")
    coating = _require_positive("coating_thickness_mm", coating_thickness_mm)
    if coating < allowable:
        return (coating, "dry-film-coating-thickness")
    return (allowable, "allowable-wear-depth")


def transfer_limited_cycles(reservoir_volume_mm3, transfer_rate_mm3_per_m,
                            sliding_per_cycle_m):
    """Return the cycles a transfer-film reservoir can replenish before starving."""
    reservoir = _require_positive("reservoir_volume_mm3", reservoir_volume_mm3)
    rate = _require_positive("transfer_rate_mm3_per_m", transfer_rate_mm3_per_m)
    per_cycle = _require_positive("sliding_per_cycle_m", sliding_per_cycle_m)
    distance_available_m = reservoir / rate
    return distance_available_m / per_cycle


def required_test_cycles(mission_cycles, life_factor=DEFAULT_LIFE_FACTOR):
    """Return the demonstration cycles the life factor demands, rounded up."""
    mission = _require_count("mission_cycles", mission_cycles)
    factor = _require_positive("life_factor", life_factor)
    if factor < 1.0:
        raise ValueError("life_factor must be at least 1.0, got %g" % factor)
    return int(math.ceil(mission * factor - 1e-9))


def demonstrated_life_ratio(test_cycles, mission_cycles, life_factor=DEFAULT_LIFE_FACTOR):
    """Return the ratio of cycles already run to the cycles the factor demands."""
    if isinstance(test_cycles, bool) or not isinstance(test_cycles, int):
        raise ValueError("test_cycles must be an integer, got %r" % (test_cycles,))
    if test_cycles < 0:
        raise ValueError("test_cycles must be non-negative, got %d" % test_cycles)
    needed = required_test_cycles(mission_cycles, life_factor)
    return float(test_cycles) / float(needed)


def assess_contact_life(spec):
    """Run the full clause 4.7.3.4.1 contact-pair life assessment.

    spec keys: stroke_mm, passes_per_cycle, mission_cycles, contact_load_n,
    nominal_wear_coefficient, hardness_mpa, contact_area_mm2,
    allowable_wear_depth_mm; optional environment_factors, coating_thickness_mm,
    ground_test_cycles, reservoir_volume_mm3, transfer_rate_mm3_per_m,
    life_factor, test_cycles.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "stroke_mm",
        "passes_per_cycle",
        "mission_cycles",
        "contact_load_n",
        "nominal_wear_coefficient",
        "hardness_mpa",
        "contact_area_mm2",
        "allowable_wear_depth_mm",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    mission_cycles = _require_count("mission_cycles", spec["mission_cycles"])
    ground_cycles = spec.get("ground_test_cycles", 0)
    distance = sliding_distance_m(
        spec["stroke_mm"], spec["passes_per_cycle"], mission_cycles, ground_cycles
    )
    per_cycle = sliding_distance_m(spec["stroke_mm"], spec["passes_per_cycle"], 1)
    k_worst = worst_case_wear_coefficient(
        spec["nominal_wear_coefficient"], spec.get("environment_factors")
    )
    volume = archard_wear_volume_mm3(
        k_worst, spec["contact_load_n"], distance, spec["hardness_mpa"]
    )
    depth = wear_depth_mm(volume, spec["contact_area_mm2"])
    limit, limit_name = limiting_wear_depth_mm(
        spec["allowable_wear_depth_mm"], spec.get("coating_thickness_mm")
    )

    findings = []
    depth_ok = depth < limit or math.isclose(
        depth, limit, rel_tol=0.0, abs_tol=DEPTH_TOLERANCE_MM
    )
    if not depth_ok:
        findings.append(
            "worst-case wear depth %.6g mm exceeds the governing %s of %.6g mm"
            % (depth, limit_name, limit)
        )

    transfer_cycles = None
    if "reservoir_volume_mm3" in spec or "transfer_rate_mm3_per_m" in spec:
        if "reservoir_volume_mm3" not in spec or "transfer_rate_mm3_per_m" not in spec:
            raise ValueError(
                "a transfer-film check needs both reservoir_volume_mm3 and "
                "transfer_rate_mm3_per_m"
            )
        transfer_cycles = transfer_limited_cycles(
            spec["reservoir_volume_mm3"], spec["transfer_rate_mm3_per_m"], per_cycle
        )
        if transfer_cycles < mission_cycles:
            findings.append(
                "transfer-film reservoir starves after %.6g cycles, short of the %d "
                "mission cycles" % (transfer_cycles, mission_cycles)
            )

    life_factor = spec.get("life_factor", DEFAULT_LIFE_FACTOR)
    needed = required_test_cycles(mission_cycles, life_factor)
    ratio = None
    if "test_cycles" in spec:
        ratio = demonstrated_life_ratio(spec["test_cycles"], mission_cycles, life_factor)
        if ratio < 1.0 and not math.isclose(ratio, 1.0, rel_tol=1e-12, abs_tol=0.0):
            findings.append(
                "demonstration has run %d of the %d cycles the life factor demands"
                % (spec["test_cycles"], needed)
            )

    if transfer_cycles is not None and transfer_cycles < mission_cycles:
        life_limiter = "transfer-film-starvation"
    elif not depth_ok:
        life_limiter = limit_name
    else:
        life_limiter = "none"

    return {
        "sliding_distance_m": distance,
        "sliding_per_cycle_m": per_cycle,
        "worst_case_wear_coefficient": k_worst,
        "wear_volume_mm3": volume,
        "wear_depth_mm": depth,
        "governing_depth_limit_mm": limit,
        "governing_depth_limit": limit_name,
        "transfer_limited_cycles": transfer_cycles,
        "required_test_cycles": needed,
        "demonstrated_life_ratio": ratio,
        "life_limiter": life_limiter,
        "compliant": not findings,
        "findings": findings,
    }
