#!/usr/bin/env python3
"""Cable injection susceptibility equipment, ECSS-E-ST-20-07C clause 5.4.8.2.

Paraphrased procedure, no verbatim standard text. The clause lists what a
bench needs to couple a susceptibility signal onto a harness bundle: a
modulated signal source, the amplifier behind it, the probe that does the
coupling, the probe that monitors what actually flowed, a pulse generator
for the transient part of the run, and the coupler that lets forward power
be told from reflected. This module turns that list into a deterministic
fitness assessment:

  injection target + coupling losses -> forward power the amplifier owes
  target current + headroom           -> probe current rating
  receiver sensitivity + target       -> monitor transfer impedance floor
  band ceiling                        -> pulse generator edge ceiling
  declared inventory vs requirement   -> adequate / marginal / inadequate

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Requirements are derived through logarithms and
# powers, so a capability that exactly meets one can land a few units in
# the last place off it. These absorb representation error only; they
# never relax a requirement.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# Rise time to bandwidth product of a single-pole edge: the pulse the
# generator produces has to carry spectrum to the top of the band.
RISE_BANDWIDTH_PRODUCT = 0.35

# A capability has to clear its requirement by this ratio before it is
# adequate rather than merely usable. Instrument figures are typical, not
# guaranteed, so sitting on a requirement is a limitation.
MARGINAL_RATIO = 1.1

# Defaults for the parts of the target a programme does not always state.
DEFAULT_DRIVE_HEADROOM_DB = 3.0
DEFAULT_CURRENT_HEADROOM = 1.5
DEFAULT_MODULATION_DEPTH_PCT = 80.0
DEFAULT_COUPLER_DIRECTIVITY_DB = 20.0

ADEQUATE = "adequate"
MARGINAL = "marginal"
INADEQUATE = "inadequate"

FLOOR = "floor"
CEILING = "ceiling"

VERDICT_FIT = "bench-fit"
VERDICT_FIT_WITH_LIMITATIONS = "bench-fit-with-limitations"
VERDICT_NOT_FIT = "bench-not-fit"

SIGNAL_GENERATOR = "modulated-signal-generator"
POWER_AMPLIFIER = "power-amplifier"
INJECTION_PROBE = "injection-probe"
MONITOR_PROBE = "current-monitor-probe"
PULSE_GENERATOR = "pulse-generator"
DIRECTIONAL_COUPLER = "directional-coupler"

REQUIRED_ITEMS = (
    SIGNAL_GENERATOR,
    POWER_AMPLIFIER,
    INJECTION_PROBE,
    MONITOR_PROBE,
    PULSE_GENERATOR,
    DIRECTIONAL_COUPLER,
)

# Which way each declared quantity is compared with its requirement. A
# floor has to be reached; a ceiling must not be exceeded.
QUANTITY_SENSE = {
    (SIGNAL_GENERATOR, "max_frequency_hz"): FLOOR,
    (SIGNAL_GENERATOR, "min_frequency_hz"): CEILING,
    (SIGNAL_GENERATOR, "modulation_depth_pct"): FLOOR,
    (POWER_AMPLIFIER, "forward_power_w"): FLOOR,
    (POWER_AMPLIFIER, "max_frequency_hz"): FLOOR,
    (POWER_AMPLIFIER, "min_frequency_hz"): CEILING,
    (INJECTION_PROBE, "current_rating_a"): FLOOR,
    (INJECTION_PROBE, "max_frequency_hz"): FLOOR,
    (INJECTION_PROBE, "min_frequency_hz"): CEILING,
    (INJECTION_PROBE, "insertion_loss_db"): CEILING,
    (MONITOR_PROBE, "transfer_impedance_ohm"): FLOOR,
    (MONITOR_PROBE, "max_frequency_hz"): FLOOR,
    (PULSE_GENERATOR, "rise_time_s"): CEILING,
    (PULSE_GENERATOR, "amplitude_v"): FLOOR,
    (DIRECTIONAL_COUPLER, "directivity_db"): FLOOR,
}


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_target(target):
    """Validate the injection target the whole bench is sized from."""
    where = "target"
    if not isinstance(target, dict):
        raise ValueError("%s: must be a mapping" % where)

    values = {}
    for key in ("injection_current_a", "common_mode_impedance_ohm",
                "band_low_hz", "band_high_hz", "receiver_sensitivity_v"):
        value = _number(target, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        values[key] = value
    if values["band_high_hz"] <= values["band_low_hz"]:
        raise ValueError(
            "%s: band_high_hz (%g) must exceed band_low_hz (%g)"
            % (where, values["band_high_hz"], values["band_low_hz"])
        )

    loss = _number(target, "probe_insertion_loss_db", where)
    if loss < 0.0:
        raise ValueError(
            "%s: probe_insertion_loss_db must be >= 0, got %g" % (where, loss)
        )
    values["probe_insertion_loss_db"] = loss

    headroom = _scalar(
        target.get("drive_headroom_db", DEFAULT_DRIVE_HEADROOM_DB), "drive_headroom_db"
    )
    if headroom < 0.0:
        raise ValueError("%s: drive_headroom_db must be >= 0, got %g" % (where, headroom))
    values["drive_headroom_db"] = headroom

    factor = _scalar(
        target.get("current_headroom", DEFAULT_CURRENT_HEADROOM), "current_headroom"
    )
    if factor < 1.0:
        raise ValueError("%s: current_headroom must be >= 1, got %g" % (where, factor))
    values["current_headroom"] = factor

    depth = _scalar(
        target.get("modulation_depth_pct", DEFAULT_MODULATION_DEPTH_PCT),
        "modulation_depth_pct",
    )
    if not 0.0 < depth <= 100.0:
        raise ValueError(
            "%s: modulation_depth_pct must be in (0, 100], got %g" % (where, depth)
        )
    values["modulation_depth_pct"] = depth

    directivity = _scalar(
        target.get("coupler_directivity_db", DEFAULT_COUPLER_DIRECTIVITY_DB),
        "coupler_directivity_db",
    )
    if directivity <= 0.0:
        raise ValueError(
            "%s: coupler_directivity_db must be > 0, got %g" % (where, directivity)
        )
    values["coupler_directivity_db"] = directivity
    return values


def required_forward_power_w(current_a, impedance_ohm, insertion_loss_db,
                             headroom_db=DEFAULT_DRIVE_HEADROOM_DB):
    """Forward power the amplifier owes to drive a current through the probe."""
    current = _scalar(current_a, "current_a")
    impedance = _scalar(impedance_ohm, "impedance_ohm")
    loss = _scalar(insertion_loss_db, "insertion_loss_db")
    headroom = _scalar(headroom_db, "headroom_db")
    if current <= 0.0:
        raise ValueError("current_a must be > 0, got %g" % current)
    if impedance <= 0.0:
        raise ValueError("impedance_ohm must be > 0, got %g" % impedance)
    if loss < 0.0:
        raise ValueError("insertion_loss_db must be >= 0, got %g" % loss)
    if headroom < 0.0:
        raise ValueError("headroom_db must be >= 0, got %g" % headroom)
    delivered = current * current * impedance
    return delivered * math.pow(10.0, (loss + headroom) / 10.0)


def required_probe_current_rating_a(current_a, headroom=DEFAULT_CURRENT_HEADROOM):
    """Peak current the injection probe has to pass without saturating."""
    current = _scalar(current_a, "current_a")
    factor = _scalar(headroom, "headroom")
    if current <= 0.0:
        raise ValueError("current_a must be > 0, got %g" % current)
    if factor < 1.0:
        raise ValueError("headroom must be >= 1, got %g" % factor)
    return current * factor


def required_transfer_impedance_ohm(receiver_sensitivity_v, current_a):
    """Monitor transfer impedance that lifts the target current off the noise floor."""
    sensitivity = _scalar(receiver_sensitivity_v, "receiver_sensitivity_v")
    current = _scalar(current_a, "current_a")
    if sensitivity <= 0.0:
        raise ValueError("receiver_sensitivity_v must be > 0, got %g" % sensitivity)
    if current <= 0.0:
        raise ValueError("current_a must be > 0, got %g" % current)
    return sensitivity / current


def required_pulse_rise_time_s(band_high_hz):
    """Edge the pulse generator owes to carry spectrum to the top of the band."""
    top = _scalar(band_high_hz, "band_high_hz")
    if top <= 0.0:
        raise ValueError("band_high_hz must be > 0, got %g" % top)
    return RISE_BANDWIDTH_PRODUCT / top


def required_pulse_amplitude_v(current_a, impedance_ohm):
    """Open-circuit amplitude the pulse generator owes into the coupled loop."""
    current = _scalar(current_a, "current_a")
    impedance = _scalar(impedance_ohm, "impedance_ohm")
    if current <= 0.0:
        raise ValueError("current_a must be > 0, got %g" % current)
    if impedance <= 0.0:
        raise ValueError("impedance_ohm must be > 0, got %g" % impedance)
    return current * impedance


def derive_requirements(target):
    """Every bench requirement the injection target implies, with its sense."""
    spec = validate_target(target)
    power = required_forward_power_w(
        spec["injection_current_a"],
        spec["common_mode_impedance_ohm"],
        spec["probe_insertion_loss_db"],
        spec["drive_headroom_db"],
    )
    requirements = {
        (SIGNAL_GENERATOR, "max_frequency_hz"): spec["band_high_hz"],
        (SIGNAL_GENERATOR, "min_frequency_hz"): spec["band_low_hz"],
        (SIGNAL_GENERATOR, "modulation_depth_pct"): spec["modulation_depth_pct"],
        (POWER_AMPLIFIER, "forward_power_w"): power,
        (POWER_AMPLIFIER, "max_frequency_hz"): spec["band_high_hz"],
        (POWER_AMPLIFIER, "min_frequency_hz"): spec["band_low_hz"],
        (INJECTION_PROBE, "current_rating_a"): required_probe_current_rating_a(
            spec["injection_current_a"], spec["current_headroom"]
        ),
        (INJECTION_PROBE, "max_frequency_hz"): spec["band_high_hz"],
        (INJECTION_PROBE, "min_frequency_hz"): spec["band_low_hz"],
        (INJECTION_PROBE, "insertion_loss_db"): spec["probe_insertion_loss_db"],
        (MONITOR_PROBE, "transfer_impedance_ohm"): required_transfer_impedance_ohm(
            spec["receiver_sensitivity_v"], spec["injection_current_a"]
        ),
        (MONITOR_PROBE, "max_frequency_hz"): spec["band_high_hz"],
        (PULSE_GENERATOR, "rise_time_s"): required_pulse_rise_time_s(
            spec["band_high_hz"]
        ),
        (PULSE_GENERATOR, "amplitude_v"): required_pulse_amplitude_v(
            spec["injection_current_a"], spec["common_mode_impedance_ohm"]
        ),
        (DIRECTIONAL_COUPLER, "directivity_db"): spec["coupler_directivity_db"],
    }
    return spec, requirements


def shortfall_factor(declared, required, sense):
    """How far short a capability falls; at or above 1 means it does not reach."""
    value = _scalar(declared, "declared")
    bound = _scalar(required, "required")
    if sense not in (FLOOR, CEILING):
        raise ValueError("sense must be %r or %r, got %r" % (FLOOR, CEILING, sense))
    if value <= 0.0:
        raise ValueError("declared must be > 0, got %g" % value)
    if bound <= 0.0:
        raise ValueError("required must be > 0, got %g" % bound)
    return bound / value if sense == FLOOR else value / bound


def categorize_capability(declared, required, sense, marginal_ratio=MARGINAL_RATIO):
    """Grade one declared capability against the requirement that governs it."""
    ratio = _scalar(marginal_ratio, "marginal_ratio")
    if ratio < 1.0:
        raise ValueError("marginal_ratio must be >= 1, got %g" % ratio)
    short = shortfall_factor(declared, required, sense)
    if at_most(short, 1.0 / ratio):
        return ADEQUATE
    if at_most(short, 1.0):
        return MARGINAL
    return INADEQUATE


def normalize_inventory(declared_items):
    """Normalize the declared bench inventory, refusing unknown or repeated items."""
    if isinstance(declared_items, dict) or not isinstance(
        declared_items, (tuple, list)
    ):
        raise ValueError("inventory: must be a sequence of item records")
    if not declared_items:
        raise ValueError("inventory: must not be empty")

    normalized = {}
    for index, record in enumerate(declared_items):
        where = "inventory[%d]" % index
        if not isinstance(record, dict):
            raise ValueError("%s: item record must be a mapping" % where)
        if "item" not in record:
            raise ValueError("%s: missing required field 'item'" % where)
        name = record["item"]
        if not isinstance(name, str):
            raise ValueError("%s: 'item' must be a string, got %r" % (where, name))
        name = name.strip().lower()
        if name not in REQUIRED_ITEMS:
            raise ValueError(
                "%s: unrecognized item %r; recognized: %s"
                % (where, record["item"], ", ".join(REQUIRED_ITEMS))
            )
        if name in normalized:
            raise ValueError("%s: item %r is declared twice" % (where, name))
        entry = {key: value for key, value in record.items() if key != "item"}
        normalized[name] = entry
    return normalized


def assess_injection_equipment(target, inventory, marginal_ratio=MARGINAL_RATIO):
    """Full clause 5.4.8.2 fitness assessment of a cable injection bench."""
    spec, requirements = derive_requirements(target)
    declared = normalize_inventory(inventory)

    findings = []
    limitations = []
    checks = {}
    worst = None

    for item in REQUIRED_ITEMS:
        if item not in declared:
            findings.append(
                "%s is not declared; the bench cannot couple or monitor the "
                "injection without it" % item
            )

    for (item, quantity), required in sorted(requirements.items()):
        if item not in declared:
            continue
        record = declared[item]
        if quantity not in record:
            findings.append(
                "%s declares no %s, so it cannot be compared with the %g it owes"
                % (item, quantity, required)
            )
            continue
        value = _number(record, quantity, "inventory[%s]" % item)
        if value <= 0.0:
            raise ValueError(
                "inventory[%s]: %s must be > 0, got %g" % (item, quantity, value)
            )
        sense = QUANTITY_SENSE[(item, quantity)]
        category = categorize_capability(value, required, sense, marginal_ratio)
        short = shortfall_factor(value, required, sense)
        checks[(item, quantity)] = {
            "declared": value,
            "required": required,
            "sense": sense,
            "category": category,
            "shortfall_factor": short,
        }
        if category == INADEQUATE:
            findings.append(
                "%s %s is %g against the %g it owes as a %s, short by a factor of "
                "%.2f" % (item, quantity, value, required, sense, short)
            )
            if worst is None or short > worst[0]:
                worst = (short, item, quantity)
        elif category == MARGINAL:
            limitations.append(
                "%s %s is %g against the %g it owes; it is usable but sits on the "
                "requirement, and instrument figures are typical rather than "
                "guaranteed" % (item, quantity, value, required)
            )

    if findings:
        verdict = VERDICT_NOT_FIT
    elif limitations:
        verdict = VERDICT_FIT_WITH_LIMITATIONS
    else:
        verdict = VERDICT_FIT

    return {
        "target": spec,
        "requirements": requirements,
        "declared_items": sorted(declared),
        "missing_items": sorted(set(REQUIRED_ITEMS) - set(declared)),
        "checks": checks,
        "governing_shortfall": None if worst is None else (worst[1], worst[2]),
        "governing_shortfall_factor": None if worst is None else worst[0],
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
    }
