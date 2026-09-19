"""Particle impact noise detection on sealed-cavity hybrid packages.

Anchor: ECSS-Q-ST-60-05C clause 10.3.6 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Decide whether the package can be tested at all. The method listens
   for loose debris striking the inside of a cavity, so it needs a
   cavity. A solid encapsulated body has nothing for a particle to move
   in and no volume for it to be heard across; running the method on one
   and recording a clean result is not a passed screen, it is a screen
   that never applied.
2. Excite the cavity properly. The unit is shocked to dislodge anything
   stuck down and then vibrated to keep it moving while the transducer
   listens. The vibration is a peak and a frequency together, and the
   stroke it implies is the physical thing the fixture has to deliver:
   the same peak at a low frequency needs a far larger displacement.
3. Repeat it. One shock-and-listen cycle can miss a particle that stayed
   in a corner, so the method owes several cycles and a unit that ran
   fewer has been listened to less thoroughly than the plan claims.
4. Know what the system can hear. A particle only matters when it is
   large enough to bridge the smallest conductor spacing inside the
   cavity, and that bridging size implies a mass. A system whose
   threshold sits above that mass returns clean results that mean
   nothing.
5. Bracket the block with a sensitivity verification. The check is a
   property of the block, not of one unit: if the check that closes the
   block fails, every unit listened to since the opening check was heard
   by an instrument of unknown sensitivity, and the whole block of clean
   results is withdrawn rather than the last unit alone.
6. Treat an indication as final for that unit. Clean units may be run
   again to clear a suspected artefact, but a unit that ever indicated
   is rejected: a later quiet run does not unhear the first one.

Stdlib only, offline, deterministic.
"""

import math

# Whether a package style presents an internal cavity a particle can
# move in and be heard across.
PACKAGE_STYLE_HAS_CAVITY = {
    "metal-can-sealed-cavity": True,
    "ceramic-sealed-cavity": True,
    "metal-lid-flatpack-cavity": True,
    "solid-encapsulated-body": False,
    "conformal-coated-open-assembly": False,
}

# Excitation conditions: (vibration peak in g, shock pulse peak in g).
PIND_CONDITIONS = {
    "A": (20.0, 1000.0),
    "B": (10.0, 500.0),
}

# Vibration frequency band, in hertz.
FREQUENCY_BAND_HZ = (40.0, 250.0)

# Shock-and-listen cycles a unit owes before its quiet result counts.
REQUIRED_CYCLES = 5

# Times a quiet unit may be re-run to clear a suspected artefact. A unit
# that indicated is not eligible for any of them.
MAX_TEST_RUNS = 3

# Densities in grams per cubic centimetre for the debris a cavity
# realistically carries.
PARTICLE_DENSITY_G_CM3 = {
    "gold-wire-offcut": 19.30,
    "aluminium-swarf": 2.70,
    "solder-ball": 8.40,
    "ceramic-chip-fragment": 3.90,
    "epoxy-flake": 1.20,
}

G0 = 9.80665
TWO_PI = 2.0 * math.pi

COMPARISON_TOLERANCE = 1.0e-12

PASS = "no-indication"
FAIL = "unit-rejected"


def _positive_number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("%s must be finite and positive, got %r" % (label, value))
    return float(value)


def _positive_integer(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def package_has_cavity(package_style):
    """True when the package style presents a cavity to listen into."""
    if package_style not in PACKAGE_STYLE_HAS_CAVITY:
        raise ValueError(
            "unknown package_style %r (expected one of %s)"
            % (package_style, ", ".join(sorted(PACKAGE_STYLE_HAS_CAVITY)))
        )
    return PACKAGE_STYLE_HAS_CAVITY[package_style]


def condition_levels(condition):
    """Vibration peak and shock peak carried by an excitation condition."""
    if condition not in PIND_CONDITIONS:
        raise ValueError(
            "unknown condition %r (expected one of %s)"
            % (condition, ", ".join(sorted(PIND_CONDITIONS)))
        )
    return PIND_CONDITIONS[condition]


def vibration_displacement_mm(peak_g, frequency_hz):
    """Single-amplitude stroke a sinusoidal excitation implies, in mm."""
    peak = _positive_number("peak_g", peak_g)
    freq = _positive_number("frequency_hz", frequency_hz)
    omega = TWO_PI * freq
    return (peak * G0 / (omega * omega)) * 1000.0


def bridging_particle_mass_ug(conductor_spacing_mm, particle_material):
    """Mass of the smallest particle that can bridge a conductor spacing."""
    spacing = _positive_number("conductor_spacing_mm", conductor_spacing_mm)
    if particle_material not in PARTICLE_DENSITY_G_CM3:
        raise ValueError(
            "unknown particle_material %r (expected one of %s)"
            % (particle_material, ", ".join(sorted(PARTICLE_DENSITY_G_CM3)))
        )
    density = PARTICLE_DENSITY_G_CM3[particle_material]
    diameter_cm = spacing / 10.0
    volume_cm3 = (math.pi / 6.0) * diameter_cm ** 3
    return volume_cm3 * density * 1.0e6


def validate_unit(record):
    """Validate one detection record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    unit_id = record.get("id")
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("record needs a non-empty string id")
    style = record.get("package_style")
    package_has_cavity(style)
    condition = record.get("condition")
    condition_levels(condition)
    material = record.get("particle_material", "gold-wire-offcut")
    if material not in PARTICLE_DENSITY_G_CM3:
        raise ValueError(
            "unit %s names unknown particle_material %r" % (unit_id, material)
        )
    runs = _positive_integer("unit %s test_runs" % unit_id, record.get("test_runs", 1))
    return {
        "id": unit_id,
        "package_style": style,
        "condition": condition,
        "particle_material": material,
        "vibration_peak_g": _positive_number(
            "unit %s vibration_peak_g" % unit_id, record.get("vibration_peak_g")
        ),
        "frequency_hz": _positive_number(
            "unit %s frequency_hz" % unit_id, record.get("frequency_hz")
        ),
        "shock_peak_g": _positive_number(
            "unit %s shock_peak_g" % unit_id, record.get("shock_peak_g")
        ),
        "cycles_run": _positive_integer(
            "unit %s cycles_run" % unit_id, record.get("cycles_run")
        ),
        "conductor_spacing_mm": _positive_number(
            "unit %s conductor_spacing_mm" % unit_id,
            record.get("conductor_spacing_mm"),
        ),
        "system_threshold_ug": _positive_number(
            "unit %s system_threshold_ug" % unit_id,
            record.get("system_threshold_ug"),
        ),
        "test_runs": runs,
        "sensitivity_verified_before": _boolean(
            "unit %s sensitivity_verified_before" % unit_id,
            record.get("sensitivity_verified_before", True),
        ),
        "indication_recorded": _boolean(
            "unit %s indication_recorded" % unit_id,
            record.get("indication_recorded", False),
        ),
    }


def check_applicability(record):
    """Findings about running the method on a body with no cavity."""
    norm = validate_unit(record)
    if not package_has_cavity(norm["package_style"]):
        return ["package-style-has-no-cavity-to-listen-into"]
    return []


def check_excitation(record):
    """Findings about the shock and vibration the unit actually saw."""
    norm = validate_unit(record)
    vib_peak, shock_peak = condition_levels(norm["condition"])
    low, high = FREQUENCY_BAND_HZ
    findings = []
    if norm["vibration_peak_g"] < vib_peak * (1.0 - COMPARISON_TOLERANCE):
        findings.append("vibration-peak-below-the-condition")
    if not (
        low * (1.0 - COMPARISON_TOLERANCE)
        <= norm["frequency_hz"]
        <= high * (1.0 + COMPARISON_TOLERANCE)
    ):
        findings.append("vibration-frequency-outside-the-band")
    if norm["shock_peak_g"] < shock_peak * (1.0 - COMPARISON_TOLERANCE):
        findings.append("shock-pulse-below-the-condition")
    if norm["cycles_run"] < REQUIRED_CYCLES:
        findings.append("fewer-cycles-than-the-method-requires")
    return findings


def check_sensitivity(record):
    """Findings about what the listening system could actually hear."""
    norm = validate_unit(record)
    bridging = bridging_particle_mass_ug(
        norm["conductor_spacing_mm"], norm["particle_material"]
    )
    findings = []
    if not norm["sensitivity_verified_before"]:
        findings.append("system-sensitivity-not-verified-before-the-run")
    if norm["system_threshold_ug"] > bridging * (1.0 + COMPARISON_TOLERANCE):
        findings.append("threshold-coarser-than-the-bridging-particle")
    return findings


def check_indications(record):
    """Findings about indications and how many runs were taken."""
    norm = validate_unit(record)
    findings = []
    if norm["indication_recorded"]:
        findings.append("noise-indication-recorded")
    if norm["test_runs"] > MAX_TEST_RUNS:
        findings.append("more-test-runs-than-the-allowance")
    if norm["indication_recorded"] and norm["test_runs"] > 1:
        findings.append("indicating-unit-re-run-instead-of-rejected")
    return findings


def assess_unit(record):
    """Assess one detection record against clause 10.3.6."""
    norm = validate_unit(record)
    findings = list(check_applicability(norm))
    findings.extend(check_excitation(norm))
    findings.extend(check_sensitivity(norm))
    findings.extend(check_indications(norm))
    return {
        "id": norm["id"],
        "package_style": norm["package_style"],
        "has_cavity": package_has_cavity(norm["package_style"]),
        "condition": norm["condition"],
        "cycles_run": norm["cycles_run"],
        "required_cycles": REQUIRED_CYCLES,
        "stroke_mm": vibration_displacement_mm(
            norm["vibration_peak_g"], norm["frequency_hz"]
        ),
        "bridging_particle_mass_ug": bridging_particle_mass_ug(
            norm["conductor_spacing_mm"], norm["particle_material"]
        ),
        "system_threshold_ug": norm["system_threshold_ug"],
        "test_runs": norm["test_runs"],
        "findings": findings,
        "disposition": FAIL if findings else PASS,
    }


def block_withdrawal(records, closing_check_passed):
    """Units whose quiet result a failed closing sensitivity check withdraws.

    The sensitivity verification brackets a block of units, not one unit.
    When the check that closes the block fails, every unit listened to
    since the opening check was heard by an instrument of unknown
    sensitivity, so the whole block is withdrawn rather than the last
    unit alone.
    """
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    _boolean("closing_check_passed", closing_check_passed)
    ordered = []
    for record in records:
        norm = validate_unit(record)
        if norm["id"] in ordered:
            raise ValueError("duplicate unit id %r" % (norm["id"],))
        ordered.append(norm["id"])
    if closing_check_passed:
        return []
    return ordered


def assess_detection_lot(records, closing_check_passed=True):
    """Run the clause 10.3.6 method over a lot and grade the lot itself."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_unit(record)
        if result["id"] in seen:
            raise ValueError("duplicate unit id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    rejected = [r["id"] for r in results if r["disposition"] == FAIL]
    indicating = [
        r["id"] for r in results if "noise-indication-recorded" in r["findings"]
    ]
    return {
        "units": results,
        "accepted_ids": [r["id"] for r in results if r["disposition"] == PASS],
        "rejected_ids": rejected,
        "indicating_ids": indicating,
        "indication_fraction": len(indicating) / len(results),
        "withdrawn_ids": block_withdrawal(records, closing_check_passed),
        "lot_accepted": bool(closing_check_passed) and not rejected,
    }


def stroke_demand_ratio(peak_g, low_frequency_hz, high_frequency_hz):
    """How much more stroke the same peak needs at the lower frequency."""
    low = vibration_displacement_mm(peak_g, low_frequency_hz)
    high = vibration_displacement_mm(peak_g, high_frequency_hz)
    return low / high
