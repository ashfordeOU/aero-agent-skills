"""Programming and post-programming control of a Class 1 programmable device.

Anchor: ECSS-Q-ST-60-13C clause 4.6.4 (programmable devices bought under the
highest assurance class). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Categorize the site that performs the programming and decide whether the
   programming operation was carried out under procurement control.
2. Check the programming equipment against its calibration interval.
3. Grade the post-programming readback of the pattern against the
   zero-mismatch rule that the highest assurance class applies.
4. Build the post-programming screen plan for the storage technology and size
   the destructive-sample screens against the delivered lot.
5. Convert a data-retention requirement into a bake duration at the bake
   temperature through an Arrhenius acceleration factor.
6. Return an accept / accept-with-deviation / reject disposition together with
   the findings that drove it.
"""

import math

__all__ = [
    "BOLTZMANN_EV_PER_K",
    "HOURS_TOLERANCE",
    "SITE_CATEGORIES",
    "TECHNOLOGY_SCREENS",
    "DESTRUCTIVE_SCREENS",
    "programming_site_category",
    "calibration_status",
    "readback_verification",
    "acceleration_factor",
    "retention_bake_hours",
    "post_programming_screen_plan",
    "screen_sample_size",
    "assess_programmable_device_control",
]

BOLTZMANN_EV_PER_K = 8.617333262e-5

# A bake duration is a ratio of exponentials: an exactly satisfied requirement
# can land a few ULPs on the wrong side. Absorb the representation error here
# rather than relaxing the retention requirement itself.
HOURS_TOLERANCE = 1e-9

ABSOLUTE_ZERO_C = -273.15

# Where the pattern may be written for a highest-assurance-class procurement.
SITE_CATEGORIES = {
    "component-manufacturer": True,
    "approved-programming-centre": True,
    "approved-user-facility": True,
    "uncontrolled-facility": False,
}

# Post-programming screens that belong to each storage technology.
TECHNOLOGY_SCREENS = {
    "antifuse": ("programming-readback", "thermal-cycling", "electrical-endpoint"),
    "fuse-link": ("programming-readback", "thermal-cycling", "electrical-endpoint"),
    "floating-gate-otp": ("programming-readback", "retention-bake", "electrical-endpoint"),
    "eeprom": ("programming-readback", "retention-bake", "electrical-endpoint"),
    "flash": (
        "programming-readback",
        "retention-bake",
        "thermal-cycling",
        "electrical-endpoint",
    ),
}

# Screens consuming the parts they are run on: sampled, never applied to the
# whole delivered lot.
DESTRUCTIVE_SCREENS = ("retention-bake",)

SAMPLE_FRACTION = 0.10
MIN_SAMPLE = 2


def _real(value, label, positive=True, allow_zero=False):
    """Return value as a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive:
        if allow_zero:
            if out < 0.0:
                raise ValueError("%s must be non-negative, got %g" % (label, out))
        elif out <= 0.0:
            raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _kelvin(temp_c, label):
    """Return an absolute temperature in kelvin from a celsius input."""
    value = _real(temp_c, label, positive=False)
    if value <= ABSOLUTE_ZERO_C:
        raise ValueError("%s must be above absolute zero, got %g C" % (label, value))
    return value - ABSOLUTE_ZERO_C


def programming_site_category(site):
    """Categorize the programming site and say whether it was under control."""
    if not isinstance(site, str) or not site.strip():
        raise ValueError("site must be a non-empty string")
    key = site.strip().lower()
    if key not in SITE_CATEGORIES:
        raise ValueError(
            "unknown programming site '%s'; expected one of %s"
            % (site, ", ".join(sorted(SITE_CATEGORIES)))
        )
    return {"category": key, "under_procurement_control": SITE_CATEGORIES[key]}


def calibration_status(days_since_calibration, interval_days):
    """Return the calibration standing of the programming equipment."""
    elapsed = _real(days_since_calibration, "days_since_calibration", allow_zero=True)
    interval = _real(interval_days, "interval_days")
    remaining = interval - elapsed
    return {
        "days_since_calibration": elapsed,
        "interval_days": interval,
        "days_remaining": remaining,
        "valid": remaining >= -HOURS_TOLERANCE,
    }


def readback_verification(bits_programmed, bits_mismatched):
    """Grade the post-programming readback against the zero-mismatch rule."""
    for label, value in (
        ("bits_programmed", bits_programmed),
        ("bits_mismatched", bits_mismatched),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
    if bits_programmed <= 0:
        raise ValueError("bits_programmed must be positive, got %d" % bits_programmed)
    if bits_mismatched < 0:
        raise ValueError("bits_mismatched must be non-negative, got %d" % bits_mismatched)
    if bits_mismatched > bits_programmed:
        raise ValueError(
            "bits_mismatched %d exceeds bits_programmed %d"
            % (bits_mismatched, bits_programmed)
        )
    return {
        "bits_programmed": bits_programmed,
        "bits_mismatched": bits_mismatched,
        "mismatch_fraction": bits_mismatched / float(bits_programmed),
        "verified": bits_mismatched == 0,
    }


def acceleration_factor(use_temp_c, stress_temp_c, activation_energy_ev):
    """Return the Arrhenius acceleration factor from use to stress temperature."""
    t_use = _kelvin(use_temp_c, "use_temp_c")
    t_stress = _kelvin(stress_temp_c, "stress_temp_c")
    energy = _real(activation_energy_ev, "activation_energy_ev")
    exponent = (energy / BOLTZMANN_EV_PER_K) * (1.0 / t_use - 1.0 / t_stress)
    return math.exp(exponent)


def retention_bake_hours(required_retention_hours, use_temp_c, bake_temp_c,
                         activation_energy_ev):
    """Return the bake duration that demonstrates the retention requirement."""
    retention = _real(required_retention_hours, "required_retention_hours")
    factor = acceleration_factor(use_temp_c, bake_temp_c, activation_energy_ev)
    if factor <= 0.0:
        raise ValueError("acceleration factor collapsed to zero; check the inputs")
    return retention / factor


def post_programming_screen_plan(technology, radiation_lot_sample=False):
    """Return the ordered post-programming screens for a storage technology."""
    if not isinstance(technology, str) or not technology.strip():
        raise ValueError("technology must be a non-empty string")
    key = technology.strip().lower()
    if key not in TECHNOLOGY_SCREENS:
        raise ValueError(
            "unknown storage technology '%s'; expected one of %s"
            % (technology, ", ".join(sorted(TECHNOLOGY_SCREENS)))
        )
    if not isinstance(radiation_lot_sample, bool):
        raise ValueError("radiation_lot_sample must be a boolean")
    screens = list(TECHNOLOGY_SCREENS[key])
    if radiation_lot_sample:
        screens.append("radiation-lot-sample")
    return tuple(screens)


def screen_sample_size(lot_size, screen):
    """Return how many parts a named post-programming screen is run on."""
    if not isinstance(lot_size, int) or isinstance(lot_size, bool):
        raise ValueError("lot_size must be an integer, got %r" % (lot_size,))
    if lot_size < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot_size)
    if not isinstance(screen, str) or not screen.strip():
        raise ValueError("screen must be a non-empty string")
    key = screen.strip().lower()
    if key in DESTRUCTIVE_SCREENS:
        sample = int(math.ceil(SAMPLE_FRACTION * lot_size))
        sample = max(sample, MIN_SAMPLE)
        return min(sample, lot_size)
    return lot_size


def assess_programmable_device_control(spec):
    """Run the full clause 4.6.4 programming-control assessment.

    spec keys: programming_site, days_since_calibration, calibration_interval_days,
    bits_programmed, bits_mismatched, technology, lot_size, required_retention_hours,
    use_temp_c, bake_temp_c, activation_energy_ev, bake_hours_performed,
    screens_performed, and optional lot_identifier, programming_record_id,
    reverified_on_calibrated_equipment, radiation_lot_sample, documented_deviations.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "programming_site",
        "days_since_calibration",
        "calibration_interval_days",
        "bits_programmed",
        "bits_mismatched",
        "technology",
        "lot_size",
        "required_retention_hours",
        "use_temp_c",
        "bake_temp_c",
        "activation_energy_ev",
        "bake_hours_performed",
        "screens_performed",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    site = programming_site_category(spec["programming_site"])
    calibration = calibration_status(
        spec["days_since_calibration"], spec["calibration_interval_days"]
    )
    readback = readback_verification(spec["bits_programmed"], spec["bits_mismatched"])
    plan = post_programming_screen_plan(
        spec["technology"], bool(spec.get("radiation_lot_sample", False))
    )
    performed = spec["screens_performed"]
    if not isinstance(performed, (list, tuple, set)):
        raise ValueError("screens_performed must be a sequence of screen names")
    performed_keys = set()
    for item in performed:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("each performed screen must be a non-empty string")
        performed_keys.add(item.strip().lower())

    deviations = spec.get("documented_deviations") or []
    if not isinstance(deviations, (list, tuple, set)):
        raise ValueError("documented_deviations must be a sequence of screen names")
    deviation_keys = {str(item).strip().lower() for item in deviations}

    required_bake = retention_bake_hours(
        spec["required_retention_hours"],
        spec["use_temp_c"],
        spec["bake_temp_c"],
        spec["activation_energy_ev"],
    )
    performed_bake = _real(spec["bake_hours_performed"], "bake_hours_performed",
                           allow_zero=True)

    samples = {screen: screen_sample_size(spec["lot_size"], screen) for screen in plan}

    findings = []
    blocking = False
    deviated = False

    if not site["under_procurement_control"]:
        findings.append(
            "programming performed at an %s; the pattern was written outside "
            "procurement control" % site["category"]
        )
        blocking = True

    if not calibration["valid"]:
        if bool(spec.get("reverified_on_calibrated_equipment", False)):
            findings.append(
                "programming equipment was %.1f days past its %.1f-day calibration "
                "interval; accepted on re-verification with calibrated equipment"
                % (calibration["days_since_calibration"], calibration["interval_days"])
            )
            deviated = True
        else:
            findings.append(
                "programming equipment was %.1f days past its %.1f-day calibration "
                "interval and the pattern was not re-verified"
                % (calibration["days_since_calibration"], calibration["interval_days"])
            )
            blocking = True

    if not readback["verified"]:
        findings.append(
            "post-programming readback returned %d mismatched bits of %d; the "
            "highest assurance class admits none"
            % (readback["bits_mismatched"], readback["bits_programmed"])
        )
        blocking = True

    missing = [screen for screen in plan if screen not in performed_keys]
    for screen in missing:
        if screen in deviation_keys:
            findings.append("screen '%s' waived under a documented deviation" % screen)
            deviated = True
        else:
            findings.append("required post-programming screen '%s' was not run" % screen)
            blocking = True

    if "retention-bake" in plan and "retention-bake" not in missing:
        short = required_bake - performed_bake
        if short > HOURS_TOLERANCE:
            findings.append(
                "retention bake ran %.4f h against the %.4f h the retention "
                "requirement needs at the bake temperature"
                % (performed_bake, required_bake)
            )
            blocking = True

    for key in ("lot_identifier", "programming_record_id"):
        value = spec.get(key)
        if not isinstance(value, str) or not value.strip():
            findings.append("traceability incomplete: '%s' is absent" % key)
            blocking = True

    if blocking:
        disposition = "reject"
    elif deviated:
        disposition = "accept-with-deviation"
    else:
        disposition = "accept"

    return {
        "site": site,
        "calibration": calibration,
        "readback": readback,
        "screen_plan": plan,
        "screen_samples": samples,
        "required_bake_hours": required_bake,
        "performed_bake_hours": performed_bake,
        "missing_screens": tuple(missing),
        "disposition": disposition,
        "findings": findings,
    }
