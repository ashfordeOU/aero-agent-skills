"""Screening-regime assessment for Class 1 EEE parts on flight hardware.

Anchor: ECSS-Q-ST-60C clause 4.3.3 — the screening regime applied to Class 1
parts destined for flight standard hardware. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared hardware standard. Flight standard hardware takes
   the full regime on every delivered device; a sampled screen leaves
   unscreened devices in the build and is a finding, not a trade.
2. Check the performed screen set against the set the part family requires,
   and report a screen dropped from it.
3. Validate the screening facility. A screen run by a facility the customer
   has not approved produces data nobody can disposition against.
4. Convert the burn-in actually performed to its equivalent at the reference
   condition using an Arrhenius acceleration on absolute temperature, and
   report a shortfall. A hotter burn-in buys hours; a cooler one owes them.
5. Measure the drift of each monitored parameter across burn-in and count a
   device whose drift exceeds the delta limit as a removal, alongside the
   catastrophic failures.
6. Compute the percent defective over the devices that entered burn-in and
   disposition the lot against the allowable percentage; a lot over the
   allowance is rejected as a lot, not merely trimmed of its removals.
7. Report the per-device records and a verdict carrying every finding.
"""

import math

__all__ = [
    "BOLTZMANN_EV_PER_K",
    "KELVIN_OFFSET",
    "ABSOLUTE_ZERO_C",
    "FLIGHT_STANDARD",
    "HARDWARE_STANDARDS",
    "FAMILY_SCREENS",
    "SCREENING_TOLERANCE",
    "normalize_token",
    "family_screens",
    "missing_screens",
    "acceleration_factor",
    "equivalent_burn_in_hours",
    "burn_in_findings",
    "drift_percent",
    "delta_removals",
    "percent_defective",
    "lot_disposition",
    "assess_screening_regime",
]

# Physical constants used by the burn-in equivalence.
BOLTZMANN_EV_PER_K = 8.617333262e-5
KELVIN_OFFSET = 273.15
ABSOLUTE_ZERO_C = -KELVIN_OFFSET

# Only flight standard hardware takes the full Class 1 regime on every device.
FLIGHT_STANDARD = "flight"
HARDWARE_STANDARDS = ("flight", "flight-spare", "engineering-model", "ground-support")

# The screen set each part family carries, in the order it is performed.
FAMILY_SCREENS = {
    "microcircuit": (
        "internal-visual",
        "temperature-cycling",
        "constant-acceleration",
        "particle-impact-noise-detection",
        "pre-burn-in-electrical",
        "burn-in",
        "post-burn-in-electrical",
        "seal-fine-and-gross-leak",
        "radiographic-inspection",
        "external-visual",
    ),
    "discrete-semiconductor": (
        "internal-visual",
        "temperature-cycling",
        "constant-acceleration",
        "pre-burn-in-electrical",
        "burn-in",
        "post-burn-in-electrical",
        "seal-fine-and-gross-leak",
        "external-visual",
    ),
    "hermetic-passive": (
        "thermal-shock",
        "pre-burn-in-electrical",
        "burn-in",
        "post-burn-in-electrical",
        "seal-fine-and-gross-leak",
        "external-visual",
    ),
    "non-hermetic-passive": (
        "thermal-shock",
        "pre-burn-in-electrical",
        "burn-in",
        "post-burn-in-electrical",
        "external-visual",
    ),
}

# Hours, percentages and drifts are compared as floats; a value set equal to
# its limit must not fail on representation alone.
SCREENING_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def normalize_token(value, label):
    """Return a lower-case hyphenated token from a free-text field."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def _require_real(value, label):
    """Return a finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _require_count(value, label):
    """Return a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_temperature(value, label):
    """Return a temperature in degrees Celsius above absolute zero."""
    number = _require_real(value, label)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError(
            "%s must be above absolute zero (%.2f C), got %g" % (label, ABSOLUTE_ZERO_C, number)
        )
    return number


def family_screens(family):
    """Return the ordered screen set a part family carries."""
    token = normalize_token(family, "part family")
    if token not in FAMILY_SCREENS:
        raise ValueError(
            "part family '%s' is not recognized; expected one of %s"
            % (token, ", ".join(sorted(FAMILY_SCREENS)))
        )
    return FAMILY_SCREENS[token]


def missing_screens(family, performed):
    """Return the required screens absent from the performed list."""
    required = family_screens(family)
    if not isinstance(performed, (list, tuple)):
        raise ValueError("performed screens must be a sequence")
    seen = []
    for index, value in enumerate(performed):
        token = normalize_token(value, "performed[%d]" % index)
        if token in seen:
            raise ValueError("screen '%s' is reported twice" % token)
        seen.append(token)
    return [name for name in required if name not in seen]


def acceleration_factor(reference_temperature_c, actual_temperature_c, activation_energy_ev):
    """Return the Arrhenius acceleration of the actual burn-in over the reference."""
    t_ref = _require_temperature(reference_temperature_c, "reference temperature")
    t_act = _require_temperature(actual_temperature_c, "actual temperature")
    energy = _require_real(activation_energy_ev, "activation energy")
    if energy <= 0.0:
        raise ValueError("activation energy must be positive, got %g" % energy)
    exponent = (energy / BOLTZMANN_EV_PER_K) * (
        1.0 / (t_ref + KELVIN_OFFSET) - 1.0 / (t_act + KELVIN_OFFSET)
    )
    return math.exp(exponent)


def equivalent_burn_in_hours(
    reference_hours, reference_temperature_c, actual_temperature_c, activation_energy_ev
):
    """Return the hours owed at the actual temperature to match the reference burn-in."""
    hours = _require_real(reference_hours, "reference hours")
    if hours <= 0.0:
        raise ValueError("reference hours must be positive, got %g" % hours)
    factor = acceleration_factor(
        reference_temperature_c, actual_temperature_c, activation_energy_ev
    )
    return hours / factor


def burn_in_findings(burn_in):
    """Return the findings raised by the burn-in actually performed."""
    if not isinstance(burn_in, dict):
        raise ValueError("burn_in must be a mapping")
    for key in (
        "hours",
        "temperature_c",
        "reference_hours",
        "reference_temperature_c",
        "activation_energy_ev",
    ):
        if key not in burn_in:
            raise ValueError("burn_in missing required key '%s'" % key)
    performed_hours = _require_real(burn_in["hours"], "burn-in hours")
    if performed_hours < 0.0:
        raise ValueError("burn-in hours must not be negative, got %g" % performed_hours)
    owed = equivalent_burn_in_hours(
        burn_in["reference_hours"],
        burn_in["reference_temperature_c"],
        burn_in["temperature_c"],
        burn_in["activation_energy_ev"],
    )
    findings = []
    if performed_hours < owed - SCREENING_TOLERANCE:
        findings.append(
            "burn-in ran %g h at %g C, short of the %.3f h that condition owes against "
            "the reference" % (performed_hours, float(burn_in["temperature_c"]), owed)
        )
    return {"hours_owed": owed, "hours_performed": performed_hours, "findings": findings}


def drift_percent(before, after):
    """Return the magnitude of the drift of a parameter across burn-in, in percent."""
    start = _require_real(before, "pre-burn-in reading")
    end = _require_real(after, "post-burn-in reading")
    if start == 0.0:
        raise ValueError("pre-burn-in reading must not be zero; drift is undefined")
    return abs(end - start) / abs(start) * 100.0


def delta_removals(devices, limit_percent):
    """Return the device records whose monitored drift exceeds the delta limit."""
    limit = _require_real(limit_percent, "delta limit")
    if limit < 0.0:
        raise ValueError("delta limit must not be negative, got %g" % limit)
    if not isinstance(devices, (list, tuple)):
        raise ValueError("devices must be a sequence")
    records = []
    seen = []
    for device in devices:
        if not isinstance(device, dict):
            raise ValueError("each device must be a mapping")
        for key in ("device_id", "parameter", "before", "after"):
            if key not in device:
                raise ValueError("device missing required key '%s'" % key)
        device_id = _require_text(device["device_id"], "device_id")
        parameter = _require_text(device["parameter"], "parameter")
        key = (device_id, parameter.lower())
        if key in seen:
            raise ValueError(
                "device '%s' reports parameter '%s' twice" % (device_id, parameter)
            )
        seen.append(key)
        drift = drift_percent(device["before"], device["after"])
        removed = drift > limit + SCREENING_TOLERANCE
        records.append(
            {
                "device_id": device_id,
                "parameter": parameter,
                "drift_percent": drift,
                "limit_percent": limit,
                "removed": removed,
            }
        )
    return records


def percent_defective(entered, removed):
    """Return the percent defective over the devices that entered burn-in."""
    started = _require_count(entered, "devices entered")
    failures = _require_count(removed, "devices removed")
    if started < 1:
        raise ValueError("devices entered must be at least 1")
    if failures > started:
        raise ValueError(
            "devices removed %d exceeds the %d that entered burn-in" % (failures, started)
        )
    return failures / float(started) * 100.0


def lot_disposition(entered, removed, allowable_percent):
    """Return the lot disposition against the allowable percent defective."""
    allowance = _require_real(allowable_percent, "allowable percent")
    if not 0.0 <= allowance <= 100.0:
        raise ValueError("allowable percent must lie in 0..100, got %g" % allowance)
    observed = percent_defective(entered, removed)
    accepted = observed <= allowance + SCREENING_TOLERANCE
    return {
        "percent_defective": observed,
        "allowable_percent": allowance,
        "accepted": accepted,
        "disposition": "lot-accepted" if accepted else "lot-rejected",
    }


def assess_screening_regime(spec):
    """Run the full clause 4.3.3 Class 1 screening assessment.

    spec keys: hardware_standard, part_family, lot_size, devices_screened,
    performed_screens, facility, burn_in, monitored_devices,
    delta_limit_percent, catastrophic_failures, allowable_percent.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "hardware_standard",
        "part_family",
        "lot_size",
        "devices_screened",
        "performed_screens",
        "facility",
        "burn_in",
        "monitored_devices",
        "delta_limit_percent",
        "catastrophic_failures",
        "allowable_percent",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    standard = normalize_token(spec["hardware_standard"], "hardware_standard")
    if standard not in HARDWARE_STANDARDS:
        raise ValueError(
            "hardware standard '%s' is not recognized; expected one of %s"
            % (standard, ", ".join(HARDWARE_STANDARDS))
        )

    lot_size = _require_count(spec["lot_size"], "lot_size")
    if lot_size < 1:
        raise ValueError("lot_size must be at least 1")
    screened = _require_count(spec["devices_screened"], "devices_screened")
    if screened > lot_size:
        raise ValueError(
            "devices_screened %d exceeds the lot size %d" % (screened, lot_size)
        )

    findings = []
    if standard == FLIGHT_STANDARD and screened != lot_size:
        findings.append(
            "flight standard hardware takes every device: %d of %d were screened"
            % (screened, lot_size)
        )

    absent = missing_screens(spec["part_family"], spec["performed_screens"])
    for name in absent:
        findings.append(
            "screen '%s' required by the %s family was not performed"
            % (name, normalize_token(spec["part_family"], "part family"))
        )

    facility = spec["facility"]
    if not isinstance(facility, dict):
        raise ValueError("facility must be a mapping")
    for key in ("name", "approved"):
        if key not in facility:
            raise ValueError("facility missing required key '%s'" % key)
    facility_name = _require_text(facility["name"], "facility name")
    if not isinstance(facility["approved"], bool):
        raise ValueError("facility approved must be a boolean")
    if not facility["approved"]:
        findings.append(
            "screening facility '%s' is not an approved source for the regime" % facility_name
        )

    burn_in = burn_in_findings(spec["burn_in"])
    findings.extend(burn_in["findings"])

    device_records = delta_removals(spec["monitored_devices"], spec["delta_limit_percent"])
    delta_failed = sorted(set(r["device_id"] for r in device_records if r["removed"]))
    catastrophic = _require_count(spec["catastrophic_failures"], "catastrophic_failures")

    entered = screened if screened > 0 else 1
    removed = len(delta_failed) + catastrophic
    if removed > entered:
        raise ValueError(
            "removals %d exceed the %d devices that entered burn-in" % (removed, entered)
        )
    disposition = lot_disposition(entered, removed, spec["allowable_percent"])
    if not disposition["accepted"]:
        findings.append(
            "percent defective %.4f exceeds the allowable %.4f; the lot is rejected"
            % (disposition["percent_defective"], disposition["allowable_percent"])
        )

    return {
        "hardware_standard": standard,
        "part_family": normalize_token(spec["part_family"], "part family"),
        "lot_size": lot_size,
        "devices_screened": screened,
        "missing_screens": absent,
        "facility": {"name": facility_name, "approved": facility["approved"]},
        "burn_in": burn_in,
        "devices": device_records,
        "delta_removed_devices": delta_failed,
        "catastrophic_failures": catastrophic,
        "percent_defective": disposition["percent_defective"],
        "disposition": disposition["disposition"],
        "regime_satisfied": not findings,
        "findings": findings,
    }
