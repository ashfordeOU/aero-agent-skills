"""Dry lubrication design for a spacecraft mechanism.

Anchor: ECSS-E-ST-33-01C clause 4.7.3.2 (dry lubrication -- solid lubricant
films such as molybdenum disulphide, tungsten disulphide, graphite and PTFE,
applied under a controlled deposition process, used where the duty is hot,
slow or low in cycle count). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether the duty is in the dry-lubrication domain at all: a hot limit
   beyond what a fluid survives, or a combination of low sliding speed and low
   cycle count. A fast, high-cycle, cool duty is counter-indicated and says so.
2. Check the chosen solid against the environment it works in, separately for
   the vacuum phases and for the ground phases, because the two invert for
   several of these materials.
3. Size the film: sliding distance from stroke and cycles, Archard wear volume
   from the wear coefficient, load and distance, wear depth over the contact
   area, and the cycle count at which the usable film is consumed.
4. Grade the deposition process window -- film thickness, deposition rate,
   substrate roughness and batch thickness uniformity -- because a solid film
   is made by its process and a film outside the window is a different film.
5. Report the wear-life margin against the required cycles together with every
   process and environment finding.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "DRY_SPEED_CEILING_M_S",
    "DRY_CYCLE_CEILING",
    "FLUID_TEMPERATURE_CEILING_C",
    "DRY_LUBRICANTS",
    "validate_positive",
    "validate_non_negative",
    "at_least",
    "sliding_distance_m",
    "archard_wear_volume_mm3",
    "wear_depth_um",
    "film_wear_life_cycles",
    "duty_indication",
    "environment_compatibility",
    "deposition_process_findings",
    "assess_dry_lubrication",
]

# Ratio comparisons of declared numbers; absorb representation error only.
MARGIN_TOLERANCE = 1e-9

# Above this sliding speed a solid film is being asked to do a fluid's job.
DRY_SPEED_CEILING_M_S = 0.15

# Above this cycle count a solid film is outside its usual domain.
DRY_CYCLE_CEILING = 1.0e5

# Above this temperature a space-qualified fluid is no longer the candidate.
FLUID_TEMPERATURE_CEILING_C = 200.0

# Behaviour of the common solid lubricants. 'needs_adsorbed_moisture' inverts
# the usual vacuum argument: graphite lubricates because of adsorbed water and
# loses that in vacuum, while the dichalcogenides do their best work there.
DRY_LUBRICANTS = {
    "mos2": {
        "temperature_c": (-200.0, 350.0),
        "wear_coefficient_mm3_per_nm": 1.0e-6,
        "needs_adsorbed_moisture": False,
        "degrades_in_humid_air": True,
    },
    "ws2": {
        "temperature_c": (-200.0, 450.0),
        "wear_coefficient_mm3_per_nm": 1.2e-6,
        "needs_adsorbed_moisture": False,
        "degrades_in_humid_air": True,
    },
    "graphite": {
        "temperature_c": (-100.0, 450.0),
        "wear_coefficient_mm3_per_nm": 2.0e-6,
        "needs_adsorbed_moisture": True,
        "degrades_in_humid_air": False,
    },
    "ptfe": {
        "temperature_c": (-200.0, 260.0),
        "wear_coefficient_mm3_per_nm": 5.0e-6,
        "needs_adsorbed_moisture": False,
        "degrades_in_humid_air": False,
    },
}


def validate_positive(label, value):
    """Return value as a strictly positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def at_least(capability, requirement):
    """Return True when capability meets requirement within the tolerance."""
    capability = float(capability)
    requirement = float(requirement)
    if capability >= requirement:
        return True
    return math.isclose(capability, requirement, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0)


def sliding_distance_m(stroke_mm, cycles):
    """Return the total sliding distance of a reciprocating contact, in m.

    One cycle travels the stroke out and back, so the distance per cycle is
    twice the stroke.
    """
    stroke = validate_positive("stroke_mm", stroke_mm)
    count = validate_non_negative("cycles", cycles)
    return 2.0 * stroke * count / 1000.0


def archard_wear_volume_mm3(wear_coefficient_mm3_per_nm, load_n, distance_m):
    """Return the Archard wear volume in mm3 for a sliding contact."""
    coefficient = validate_positive(
        "wear_coefficient_mm3_per_nm", wear_coefficient_mm3_per_nm
    )
    load = validate_positive("load_n", load_n)
    distance = validate_non_negative("distance_m", distance_m)
    return coefficient * load * distance


def wear_depth_um(volume_mm3, contact_area_mm2):
    """Convert a wear volume spread over the contact area into a depth in um."""
    volume = validate_non_negative("volume_mm3", volume_mm3)
    area = validate_positive("contact_area_mm2", contact_area_mm2)
    return volume / area * 1000.0


def film_wear_life_cycles(spec):
    """Return the cycle count at which the usable film is consumed.

    spec keys: usable_film_thickness_um, stroke_mm, load_n, contact_area_mm2,
    wear_coefficient_mm3_per_nm.
    """
    if not isinstance(spec, dict):
        raise ValueError("wear spec must be a mapping")
    required = (
        "usable_film_thickness_um",
        "stroke_mm",
        "load_n",
        "contact_area_mm2",
        "wear_coefficient_mm3_per_nm",
    )
    for key in required:
        if key not in spec:
            raise ValueError("wear spec missing required key '%s'" % key)
    usable = validate_positive("usable_film_thickness_um", spec["usable_film_thickness_um"])
    per_cycle_distance = sliding_distance_m(spec["stroke_mm"], 1.0)
    per_cycle_volume = archard_wear_volume_mm3(
        spec["wear_coefficient_mm3_per_nm"], spec["load_n"], per_cycle_distance
    )
    per_cycle_depth = wear_depth_um(per_cycle_volume, spec["contact_area_mm2"])
    if per_cycle_depth <= 0.0:
        raise ValueError("wear depth per cycle resolved to zero; inputs are degenerate")
    return usable / per_cycle_depth


def duty_indication(duty):
    """Say whether the duty belongs in the dry-lubrication domain.

    duty keys: temperature_c (pair), sliding_speed_m_s, required_cycles.
    """
    if not isinstance(duty, dict):
        raise ValueError("duty must be a mapping")
    for key in ("temperature_c", "sliding_speed_m_s", "required_cycles"):
        if key not in duty:
            raise ValueError("duty missing required key '%s'" % key)
    temperature = duty["temperature_c"]
    if not isinstance(temperature, (list, tuple)) or len(temperature) != 2:
        raise ValueError("duty 'temperature_c' must be a (low, high) pair")
    low = float(temperature[0])
    high = float(temperature[1])
    if not math.isfinite(low) or not math.isfinite(high):
        raise ValueError("duty temperature limits must be finite")
    if low > high:
        raise ValueError("duty temperature_c is inverted: %g exceeds %g" % (low, high))
    speed = validate_non_negative("sliding_speed_m_s", duty["sliding_speed_m_s"])
    cycles = validate_non_negative("required_cycles", duty["required_cycles"])
    hot = high > FLUID_TEMPERATURE_CEILING_C
    slow = speed <= DRY_SPEED_CEILING_M_S or math.isclose(
        speed, DRY_SPEED_CEILING_M_S, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    )
    low_cycle = cycles <= DRY_CYCLE_CEILING or math.isclose(
        cycles, DRY_CYCLE_CEILING, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    )
    indicated = hot or (slow and low_cycle)
    findings = []
    if not indicated:
        findings.append(
            "duty is fast (%g m/s) and high-cycle (%g) without a hot limit beyond "
            "%g C; a fluid lubricant is the indicated choice"
            % (speed, cycles, FLUID_TEMPERATURE_CEILING_C)
        )
    return {
        "hot_duty": hot,
        "slow_duty": slow,
        "low_cycle_duty": low_cycle,
        "indicated": indicated,
        "findings": findings,
    }


def environment_compatibility(material, duty_temperature_c, operates_in_vacuum=True,
                              ground_humidity_pct=None, ground_purge=False):
    """Evaluate one solid lubricant against its operating environment."""
    if not isinstance(material, str):
        raise ValueError("material must be a string")
    key = material.strip().lower()
    if key not in DRY_LUBRICANTS:
        raise ValueError(
            "unknown solid lubricant '%s'; known materials: %s"
            % (material, ", ".join(sorted(DRY_LUBRICANTS)))
        )
    entry = DRY_LUBRICANTS[key]
    if not isinstance(duty_temperature_c, (list, tuple)) or len(duty_temperature_c) != 2:
        raise ValueError("duty_temperature_c must be a (low, high) pair")
    duty_low = float(duty_temperature_c[0])
    duty_high = float(duty_temperature_c[1])
    if duty_low > duty_high:
        raise ValueError("duty_temperature_c is inverted")
    rated_low, rated_high = entry["temperature_c"]
    findings = []
    if duty_low < rated_low and not math.isclose(
        duty_low, rated_low, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "%s is rated to %g C cold; the duty reaches %g C" % (key, rated_low, duty_low)
        )
    if duty_high > rated_high and not math.isclose(
        duty_high, rated_high, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "%s is rated to %g C hot; the duty reaches %g C" % (key, rated_high, duty_high)
        )
    if operates_in_vacuum and entry["needs_adsorbed_moisture"]:
        findings.append(
            "%s lubricates through adsorbed moisture and loses it in vacuum" % key
        )
    if ground_humidity_pct is not None:
        humidity = validate_non_negative("ground_humidity_pct", ground_humidity_pct)
        if humidity > 100.0:
            raise ValueError("ground_humidity_pct must not exceed 100")
        if entry["degrades_in_humid_air"] and humidity > 0.0 and not ground_purge:
            findings.append(
                "%s degrades in humid air at %g %% RH during ground phases; a dry "
                "purge or a controlled enclosure is required" % (key, humidity)
            )
    return {
        "material": key,
        "rated_temperature_c": entry["temperature_c"],
        "wear_coefficient_mm3_per_nm": entry["wear_coefficient_mm3_per_nm"],
        "compatible": not findings,
        "findings": findings,
    }


def deposition_process_findings(parameters, window):
    """Grade the deposition process parameters against their control window.

    parameters keys: film_thickness_um, deposition_rate_um_per_min,
    substrate_roughness_ra_um, batch_thickness_spread_um.
    window keys: film_thickness_um (pair), deposition_rate_um_per_min (pair),
    max_substrate_roughness_ra_um, max_batch_uniformity_ratio.
    """
    if not isinstance(parameters, dict) or not isinstance(window, dict):
        raise ValueError("parameters and window must both be mappings")
    for key in (
        "film_thickness_um",
        "deposition_rate_um_per_min",
        "substrate_roughness_ra_um",
        "batch_thickness_spread_um",
    ):
        if key not in parameters:
            raise ValueError("process parameters missing required key '%s'" % key)
    for key in (
        "film_thickness_um",
        "deposition_rate_um_per_min",
        "max_substrate_roughness_ra_um",
        "max_batch_uniformity_ratio",
    ):
        if key not in window:
            raise ValueError("process window missing required key '%s'" % key)
    thickness = validate_positive("film_thickness_um", parameters["film_thickness_um"])
    rate = validate_positive(
        "deposition_rate_um_per_min", parameters["deposition_rate_um_per_min"]
    )
    roughness = validate_non_negative(
        "substrate_roughness_ra_um", parameters["substrate_roughness_ra_um"]
    )
    spread = validate_non_negative(
        "batch_thickness_spread_um", parameters["batch_thickness_spread_um"]
    )
    findings = []
    for label, value, bounds in (
        ("film thickness", thickness, window["film_thickness_um"]),
        ("deposition rate", rate, window["deposition_rate_um_per_min"]),
    ):
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("window entry for %s must be a (low, high) pair" % label)
        low = validate_positive("%s window low" % label, bounds[0])
        high = validate_positive("%s window high" % label, bounds[1])
        if low > high:
            raise ValueError("window entry for %s is inverted" % label)
        below = value < low and not math.isclose(value, low, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE)
        above = value > high and not math.isclose(
            value, high, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
        )
        if below or above:
            findings.append(
                "%s %g is outside the controlled window %g..%g" % (label, value, low, high)
            )
    max_roughness = validate_positive(
        "max_substrate_roughness_ra_um", window["max_substrate_roughness_ra_um"]
    )
    if roughness > max_roughness and not math.isclose(
        roughness, max_roughness, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "substrate roughness Ra %g um exceeds the %g um the process requires"
            % (roughness, max_roughness)
        )
    uniformity_ratio = spread / thickness
    max_uniformity = validate_positive(
        "max_batch_uniformity_ratio", window["max_batch_uniformity_ratio"]
    )
    if uniformity_ratio > max_uniformity and not math.isclose(
        uniformity_ratio, max_uniformity, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    ):
        findings.append(
            "batch thickness spread is %.4f of the nominal film, above the %.4f allowed"
            % (uniformity_ratio, max_uniformity)
        )
    return {
        "uniformity_ratio": uniformity_ratio,
        "in_control": not findings,
        "findings": findings,
    }


def assess_dry_lubrication(spec):
    """Run the full clause 4.7.3.2 dry-lubrication design assessment.

    spec keys: material, duty (temperature_c, sliding_speed_m_s,
    required_cycles), wear (usable_film_thickness_um, stroke_mm, load_n,
    contact_area_mm2), process (parameters), window, optional
    operates_in_vacuum, ground_humidity_pct, ground_purge.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("material", "duty", "wear", "process", "window"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    duty = spec["duty"]
    indication = duty_indication(duty)
    compatibility = environment_compatibility(
        spec["material"],
        duty["temperature_c"],
        spec.get("operates_in_vacuum", True),
        spec.get("ground_humidity_pct"),
        spec.get("ground_purge", False),
    )
    wear_spec = dict(spec["wear"])
    if not isinstance(wear_spec, dict):
        raise ValueError("spec['wear'] must be a mapping")
    wear_spec.setdefault(
        "wear_coefficient_mm3_per_nm", compatibility["wear_coefficient_mm3_per_nm"]
    )
    life_cycles = film_wear_life_cycles(wear_spec)
    required_cycles = validate_non_negative("required_cycles", duty["required_cycles"])
    findings = list(indication["findings"]) + list(compatibility["findings"])
    process = deposition_process_findings(spec["process"], spec["window"])
    findings.extend(process["findings"])
    if required_cycles > 0.0:
        wear_margin = life_cycles / required_cycles
        if not at_least(life_cycles, required_cycles):
            findings.append(
                "film is consumed after %.1f cycles, short of the required %.1f"
                % (life_cycles, required_cycles)
            )
    else:
        wear_margin = float("inf")
    return {
        "indication": indication,
        "compatibility": compatibility,
        "process": process,
        "wear_life_cycles": life_cycles,
        "wear_margin": wear_margin,
        "compliant": not findings,
        "findings": findings,
    }
