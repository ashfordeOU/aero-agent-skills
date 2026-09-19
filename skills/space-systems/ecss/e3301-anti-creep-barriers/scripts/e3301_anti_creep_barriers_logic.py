"""Anti-creep barriers against fluid-lubricant migration.

Anchor: ECSS-E-ST-33-01C clause 4.7.3.3.3 (barriers designed to prevent a
fluid lubricant migrating to surfaces that are sensitive to it, or that are
deliberately un-lubricated). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Grade each barrier on the physics that makes it work: a barrier film of low
   critical surface energy against a lubricant of higher surface tension gives
   a negative spreading coefficient and a finite contact angle, so the oil
   beads instead of running.
2. Grade each barrier on the things that make the physics irrelevant when they
   are wrong: a band narrower than the minimum, a band that is not continuous
   around the path, and a film used beyond its temperature rating.
3. Walk every declared migration path from a lubricant source to a sensitive or
   un-lubricated surface and confirm at least one sound barrier intercepts it.
4. Treat vapour separately. A surface barrier stops creep along a surface, not
   transport through the gas phase, so a path with a line of sight to a
   sensitive surface needs its own vapour control.
5. Report each unprotected path by name rather than a count, because the fix is
   per path.
"""

import math

__all__ = [
    "ANGLE_TOLERANCE_DEG",
    "MARGIN_TOLERANCE",
    "DEFAULT_MIN_CONTACT_ANGLE_DEG",
    "DEFAULT_MIN_BAND_WIDTH_MM",
    "validate_positive",
    "validate_non_negative",
    "spreading_coefficient",
    "contact_angle_deg",
    "wetting_margin_mn_per_m",
    "grade_barrier",
    "grade_path",
    "assess_anti_creep_barriers",
]

# Contact angles are compared against a design minimum in degrees.
ANGLE_TOLERANCE_DEG = 1e-9

# Surface-energy differences are compared as declared numbers.
MARGIN_TOLERANCE = 1e-9

# A barrier that only just beads the oil does not survive a thermal cycle.
DEFAULT_MIN_CONTACT_ANGLE_DEG = 45.0

# A band narrower than this is bridged by a droplet or a handling smear.
DEFAULT_MIN_BAND_WIDTH_MM = 2.0


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


def spreading_coefficient(surface_energy_solid, surface_tension_liquid,
                          interfacial_energy_mn_per_m):
    """Return the spreading coefficient in mN/m; negative means the oil beads."""
    solid = validate_non_negative("surface_energy_solid", surface_energy_solid)
    liquid = validate_positive("surface_tension_liquid", surface_tension_liquid)
    interfacial = validate_non_negative(
        "interfacial_energy_mn_per_m", interfacial_energy_mn_per_m
    )
    return solid - liquid - interfacial


def contact_angle_deg(surface_energy_solid, surface_tension_liquid,
                      interfacial_energy_mn_per_m):
    """Return the Young equilibrium contact angle of the oil on the barrier."""
    solid = validate_non_negative("surface_energy_solid", surface_energy_solid)
    liquid = validate_positive("surface_tension_liquid", surface_tension_liquid)
    interfacial = validate_non_negative(
        "interfacial_energy_mn_per_m", interfacial_energy_mn_per_m
    )
    cosine = (solid - interfacial) / liquid
    if cosine > 1.0:
        if math.isclose(cosine, 1.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE):
            cosine = 1.0
        else:
            raise ValueError(
                "the declared energies describe complete wetting (cos theta = %g); "
                "Young equilibrium has no solution and there is no barrier" % cosine
            )
    if cosine < -1.0:
        if math.isclose(cosine, -1.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE):
            cosine = -1.0
        else:
            raise ValueError(
                "the declared energies describe complete dewetting (cos theta = %g); "
                "check the interfacial energy" % cosine
            )
    return math.degrees(math.acos(cosine))


def wetting_margin_mn_per_m(barrier_critical_energy, lubricant_surface_tension):
    """Return how far the lubricant surface tension sits above the barrier energy."""
    barrier = validate_non_negative("barrier_critical_energy", barrier_critical_energy)
    lubricant = validate_positive("lubricant_surface_tension", lubricant_surface_tension)
    return lubricant - barrier


def grade_barrier(barrier, lubricant, min_contact_angle_deg=DEFAULT_MIN_CONTACT_ANGLE_DEG,
                  min_band_width_mm=DEFAULT_MIN_BAND_WIDTH_MM):
    """Evaluate one barrier band against the lubricant and the design minima.

    barrier keys: name, critical_surface_energy_mn_per_m,
    interfacial_energy_mn_per_m, band_width_mm, continuous (bool),
    temperature_c (pair).
    lubricant keys: surface_tension_mn_per_m, temperature_c (pair).
    """
    if not isinstance(barrier, dict):
        raise ValueError("barrier must be a mapping")
    if not isinstance(lubricant, dict):
        raise ValueError("lubricant must be a mapping")
    required = (
        "name",
        "critical_surface_energy_mn_per_m",
        "interfacial_energy_mn_per_m",
        "band_width_mm",
        "continuous",
        "temperature_c",
    )
    for key in required:
        if key not in barrier:
            raise ValueError("barrier missing required key '%s'" % key)
    for key in ("surface_tension_mn_per_m", "temperature_c"):
        if key not in lubricant:
            raise ValueError("lubricant missing required key '%s'" % key)
    name = barrier["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("barrier name must be a non-empty string")
    if not isinstance(barrier["continuous"], bool):
        raise ValueError("barrier '%s' key 'continuous' must be a boolean" % name)
    minimum_angle = validate_positive("min_contact_angle_deg", min_contact_angle_deg)
    minimum_width = validate_positive("min_band_width_mm", min_band_width_mm)
    width = validate_non_negative("band_width_mm", barrier["band_width_mm"])
    tension = validate_positive(
        "lubricant surface_tension_mn_per_m", lubricant["surface_tension_mn_per_m"]
    )
    findings = []
    energy = validate_non_negative(
        "critical_surface_energy_mn_per_m", barrier["critical_surface_energy_mn_per_m"]
    )
    interfacial = validate_non_negative(
        "interfacial_energy_mn_per_m", barrier["interfacial_energy_mn_per_m"]
    )
    # A barrier the oil wets completely has no Young equilibrium to report. That
    # is a barrier finding, not a reason to abandon the whole assessment.
    if (energy - interfacial) >= tension:
        angle = 0.0
        findings.append(
            "barrier %s is wetted completely by the lubricant; its critical surface "
            "energy %.3f mN/m is not low enough against a surface tension of %.3f mN/m"
            % (name, energy, tension)
        )
    else:
        angle = contact_angle_deg(
            barrier["critical_surface_energy_mn_per_m"],
            tension,
            barrier["interfacial_energy_mn_per_m"],
        )
    spreading = spreading_coefficient(
        barrier["critical_surface_energy_mn_per_m"],
        tension,
        barrier["interfacial_energy_mn_per_m"],
    )
    margin = wetting_margin_mn_per_m(
        barrier["critical_surface_energy_mn_per_m"], tension
    )
    if spreading > 0.0 and not math.isclose(
        spreading, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "barrier %s has a positive spreading coefficient %.3f mN/m; the "
            "lubricant wets it and runs across" % (name, spreading)
        )
    if angle < minimum_angle and not math.isclose(
        angle, minimum_angle, rel_tol=0.0, abs_tol=ANGLE_TOLERANCE_DEG
    ):
        findings.append(
            "barrier %s gives a contact angle of %.3f deg, below the %.3f deg minimum"
            % (name, angle, minimum_angle)
        )
    if width < minimum_width and not math.isclose(
        width, minimum_width, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "barrier %s band is %.3f mm wide, below the %.3f mm minimum"
            % (name, width, minimum_width)
        )
    if not barrier["continuous"]:
        findings.append(
            "barrier %s is not continuous around the path; a gap is the whole path"
            % name
        )
    barrier_range = barrier["temperature_c"]
    duty_range = lubricant["temperature_c"]
    for label, value in (("barrier", barrier_range), ("lubricant duty", duty_range)):
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError("%s temperature_c must be a (low, high) pair" % label)
    barrier_low = float(barrier_range[0])
    barrier_high = float(barrier_range[1])
    duty_low = float(duty_range[0])
    duty_high = float(duty_range[1])
    if barrier_low > barrier_high or duty_low > duty_high:
        raise ValueError("a temperature range is inverted")
    if duty_low < barrier_low and not math.isclose(
        duty_low, barrier_low, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "barrier %s is rated to %g C cold; the duty reaches %g C"
            % (name, barrier_low, duty_low)
        )
    if duty_high > barrier_high and not math.isclose(
        duty_high, barrier_high, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "barrier %s is rated to %g C hot; the duty reaches %g C"
            % (name, barrier_high, duty_high)
        )
    return {
        "name": name,
        "contact_angle_deg": angle,
        "spreading_coefficient_mn_per_m": spreading,
        "wetting_margin_mn_per_m": margin,
        "sound": not findings,
        "findings": findings,
    }


def grade_path(path, graded_barriers):
    """Evaluate one migration path against the barriers placed on it.

    path keys: name, source, destination, sensitive (bool), barriers (sequence
    of barrier names), optional line_of_sight (bool) and vapour_control (str).
    """
    if not isinstance(path, dict):
        raise ValueError("path must be a mapping")
    for key in ("name", "source", "destination", "sensitive", "barriers"):
        if key not in path:
            raise ValueError("path missing required key '%s'" % key)
    name = path["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("path name must be a non-empty string")
    if not isinstance(path["sensitive"], bool):
        raise ValueError("path '%s' key 'sensitive' must be a boolean" % name)
    barrier_names = path["barriers"]
    if not isinstance(barrier_names, (list, tuple)):
        raise ValueError("path '%s' key 'barriers' must be a sequence" % name)
    findings = []
    placed = []
    for barrier_name in barrier_names:
        if not isinstance(barrier_name, str):
            raise ValueError("path '%s' barrier names must be strings" % name)
        if barrier_name not in graded_barriers:
            raise ValueError(
                "path '%s' names barrier '%s', which is not declared" % (name, barrier_name)
            )
        placed.append(graded_barriers[barrier_name])
    sound = [record for record in placed if record["sound"]]
    if path["sensitive"]:
        if not placed:
            findings.append(
                "path %s runs from %s to the sensitive surface %s with no barrier"
                % (name, path["source"], path["destination"])
            )
        elif not sound:
            findings.append(
                "path %s is covered only by barriers that did not pass: %s"
                % (name, ", ".join(record["name"] for record in placed))
            )
        if path.get("line_of_sight", False) and not path.get("vapour_control"):
            findings.append(
                "path %s has a line of sight to %s; a surface barrier does not stop "
                "vapour transport and no vapour control is declared"
                % (name, path["destination"])
            )
    return {
        "name": name,
        "barrier_count": len(placed),
        "sound_barrier_count": len(sound),
        "protected": not findings,
        "findings": findings,
    }


def assess_anti_creep_barriers(spec):
    """Run the full clause 4.7.3.3.3 anti-creep barrier assessment.

    spec keys: lubricant, barriers (sequence), paths (sequence), optional
    min_contact_angle_deg and min_band_width_mm.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lubricant", "barriers", "paths"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    barriers = spec["barriers"]
    if not isinstance(barriers, (list, tuple)) or not barriers:
        raise ValueError("spec['barriers'] must be a non-empty sequence")
    paths = spec["paths"]
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("spec['paths'] must be a non-empty sequence")
    graded = {}
    for barrier in barriers:
        record = grade_barrier(
            barrier,
            spec["lubricant"],
            spec.get("min_contact_angle_deg", DEFAULT_MIN_CONTACT_ANGLE_DEG),
            spec.get("min_band_width_mm", DEFAULT_MIN_BAND_WIDTH_MM),
        )
        if record["name"] in graded:
            raise ValueError("barrier name '%s' is declared twice" % record["name"])
        graded[record["name"]] = record
    path_records = [grade_path(path, graded) for path in paths]
    names = [record["name"] for record in path_records]
    if len(set(names)) != len(names):
        raise ValueError("path names must be unique")
    findings = []
    for record in graded.values():
        findings.extend(record["findings"])
    for record in path_records:
        findings.extend(record["findings"])
    unprotected = tuple(
        record["name"] for record in path_records if not record["protected"]
    )
    return {
        "barriers": graded,
        "paths": path_records,
        "unprotected_paths": unprotected,
        "compliant": not findings,
        "findings": findings,
    }
