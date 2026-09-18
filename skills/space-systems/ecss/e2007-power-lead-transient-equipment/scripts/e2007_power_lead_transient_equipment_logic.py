#!/usr/bin/env python3
"""Power-lead transient test equipment, ECSS-E-ST-20-07C 5.4.9.2.

Paraphrased equipment clause, no verbatim standard text. The clause lists
what a power-lead transient injection needs: a transient generator with the
right amplitude, edge and repetition, a coupling arrangement that puts the
pulse on the lead, a decoupling arrangement that keeps it out of the power
source, and a recording chain fast enough to show what actually arrived.
This module decides whether a declared bench can do that:

  divider    -> terminal amplitude -> the open-circuit output the source and
                load impedances demand of the generator
  edges      -> generator rise-time ceiling from the specified edge, and a
                much tighter ceiling on the recording chain
  recording  -> chain bandwidth from the edge, sample rate from the
                bandwidth, memory depth from the window
  isolation  -> decoupling impedance floor from the diversion allowed into
                the power source
  grading    -> each declared item adequate, marginal or inadequate, then
                the shortfall that governs

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Rise-time bandwidth product of a well-behaved recording chain.
RISE_TIME_BANDWIDTH_PRODUCT = 0.35

# How many times faster than the pulse edge the recording chain has to be
# before the recorded edge is the pulse's own rather than the chain's.
DEFAULT_CHAIN_SPEED_FACTOR = 5.0

# Samples per cycle of chain bandwidth before a peak can land between two
# samples and be recorded shorter and lower than it was.
DEFAULT_OVERSAMPLING = 5.0

# Fraction of a requirement within which a declared capability is reported as
# marginal rather than adequate. Instrument figures are typical, not
# guaranteed, so sitting on a requirement is a limitation.
DEFAULT_MARGINAL_FRACTION = 0.10

# Generic relative tolerance for comparisons against a derived requirement.
REL_TOL = 1e-12

ITEM_GENERATOR = "transient-generator"
ITEM_COUPLING = "coupling-network"
ITEM_DECOUPLING = "decoupling-network"
ITEM_OSCILLOSCOPE = "oscilloscope"
ITEM_VOLTAGE_PROBE = "voltage-probe"
REQUIRED_ITEMS = (
    ITEM_GENERATOR,
    ITEM_COUPLING,
    ITEM_DECOUPLING,
    ITEM_OSCILLOSCOPE,
    ITEM_VOLTAGE_PROBE,
)

FITNESS_ADEQUATE = "adequate"
FITNESS_MARGINAL = "marginal"
FITNESS_INADEQUATE = "inadequate"

SENSE_FLOOR = "floor"
SENSE_CEILING = "ceiling"

VERDICT_FIT = "bench-fit"
VERDICT_UNFIT = "bench-not-fit"


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


def _positive(value, name):
    number = _scalar(value, name)
    if number <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, number))
    return number


def _fraction(value, name):
    number = _scalar(value, name)
    if not 0.0 < number < 1.0:
        raise ValueError("%s must lie in (0, 1), got %g" % (name, number))
    return number


def generator_open_circuit_v(terminal_v, source_impedance_ohm, load_impedance_ohm):
    """Open-circuit output the generator needs to reach a terminal amplitude.

    The generator source impedance and the impedance the lead presents form a
    divider, so the amplitude asked for at the unit's terminals is never the
    amplitude the generator has to be set to.
    """
    terminal = _positive(terminal_v, "terminal_v")
    source = _scalar(source_impedance_ohm, "source_impedance_ohm")
    load = _positive(load_impedance_ohm, "load_impedance_ohm")
    if source < 0.0:
        raise ValueError("source_impedance_ohm must be >= 0, got %g" % source)
    return terminal * (source + load) / load


def terminal_amplitude_v(open_circuit_v, source_impedance_ohm, load_impedance_ohm):
    """Amplitude an open-circuit setting actually puts on the lead."""
    open_circuit = _positive(open_circuit_v, "open_circuit_v")
    source = _scalar(source_impedance_ohm, "source_impedance_ohm")
    load = _positive(load_impedance_ohm, "load_impedance_ohm")
    if source < 0.0:
        raise ValueError("source_impedance_ohm must be >= 0, got %g" % source)
    return open_circuit * load / (source + load)


def generator_rise_time_ceiling_s(specified_rise_s, tolerance_fraction=0.0):
    """Slowest edge the generator may have and still produce the pulse."""
    specified = _positive(specified_rise_s, "specified_rise_s")
    tolerance = _scalar(tolerance_fraction, "tolerance_fraction")
    if not 0.0 <= tolerance < 1.0:
        raise ValueError("tolerance_fraction must lie in [0, 1), got %g" % tolerance)
    return specified * (1.0 + tolerance)


def chain_rise_time_ceiling_s(specified_rise_s, speed_factor=DEFAULT_CHAIN_SPEED_FACTOR):
    """Slowest the recording chain may be and still show the pulse's own edge."""
    specified = _positive(specified_rise_s, "specified_rise_s")
    factor = _scalar(speed_factor, "speed_factor")
    if factor < 1.0:
        raise ValueError("speed_factor must be >= 1, got %g" % factor)
    return specified / factor


def chain_bandwidth_hz(rise_time_s):
    """Bandwidth a chain needs to carry an edge of that rise time."""
    rise = _positive(rise_time_s, "rise_time_s")
    return RISE_TIME_BANDWIDTH_PRODUCT / rise


def sample_rate_hz(bandwidth_hz, oversampling=DEFAULT_OVERSAMPLING):
    """Sample rate that oversamples the chain bandwidth by the stated factor."""
    bandwidth = _positive(bandwidth_hz, "bandwidth_hz")
    factor = _scalar(oversampling, "oversampling")
    if factor < 1.0:
        raise ValueError("oversampling must be >= 1, got %g" % factor)
    return bandwidth * factor


def record_depth_samples(window_s, rate_hz):
    """Memory the capture window costs at that sample rate, in samples."""
    window = _positive(window_s, "window_s")
    rate = _positive(rate_hz, "rate_hz")
    return int(math.ceil(window * rate))


def decoupling_impedance_floor_ohm(eut_impedance_ohm, allowed_diversion_fraction):
    """Impedance the decoupling must present to keep the pulse off the source.

    The injected current divides between the unit and the path back into the
    power source; holding the share that reaches the source below an allowed
    fraction bounds the decoupling impedance from below.
    """
    eut = _positive(eut_impedance_ohm, "eut_impedance_ohm")
    fraction = _fraction(allowed_diversion_fraction, "allowed_diversion_fraction")
    return eut * (1.0 - fraction) / fraction


def coupling_impedance_ceiling_ohm(load_impedance_ohm, allowed_loss_fraction):
    """Series impedance the coupling path may add before the pulse is eaten."""
    load = _positive(load_impedance_ohm, "load_impedance_ohm")
    fraction = _fraction(allowed_loss_fraction, "allowed_loss_fraction")
    return load * fraction / (1.0 - fraction)


def probe_rating_v(terminal_v, headroom_factor=1.5):
    """Voltage the probe has to stand, with headroom over the pulse."""
    terminal = _positive(terminal_v, "terminal_v")
    factor = _scalar(headroom_factor, "headroom_factor")
    if factor < 1.0:
        raise ValueError("headroom_factor must be >= 1, got %g" % factor)
    return terminal * factor


def repetition_interval_floor_s(width_s, duty_fraction):
    """Shortest gap between pulses that keeps the generator inside its duty."""
    width = _positive(width_s, "width_s")
    fraction = _fraction(duty_fraction, "duty_fraction")
    return width / fraction


def delivered_energy_j(terminal_v, load_impedance_ohm, width_s):
    """Energy one pulse puts into the lead, joules, taken as rectangular."""
    terminal = _positive(terminal_v, "terminal_v")
    load = _positive(load_impedance_ohm, "load_impedance_ohm")
    width = _positive(width_s, "width_s")
    return terminal * terminal / load * width


def categorize_capability(
    declared, required, sense, marginal_fraction=DEFAULT_MARGINAL_FRACTION
):
    """Categorize one declared capability against its derived requirement."""
    value = _scalar(declared, "declared")
    requirement = _positive(required, "required")
    fraction = _scalar(marginal_fraction, "marginal_fraction")
    if sense not in (SENSE_FLOOR, SENSE_CEILING):
        raise ValueError(
            "sense must be %r or %r, got %r" % (SENSE_FLOOR, SENSE_CEILING, sense)
        )
    if not 0.0 <= fraction < 1.0:
        raise ValueError("marginal_fraction must lie in [0, 1), got %g" % fraction)
    if value <= 0.0:
        raise ValueError("declared must be > 0, got %g" % value)
    if sense == SENSE_FLOOR:
        if value < requirement * (1.0 - REL_TOL):
            return FITNESS_INADEQUATE
        if value <= requirement * (1.0 + fraction):
            return FITNESS_MARGINAL
        return FITNESS_ADEQUATE
    if value > requirement * (1.0 + REL_TOL):
        return FITNESS_INADEQUATE
    if value >= requirement * (1.0 - fraction):
        return FITNESS_MARGINAL
    return FITNESS_ADEQUATE


def shortfall_factor(declared, required, sense):
    """How far short a capability falls, as a factor of its requirement."""
    value = _positive(declared, "declared")
    requirement = _positive(required, "required")
    if sense not in (SENSE_FLOOR, SENSE_CEILING):
        raise ValueError(
            "sense must be %r or %r, got %r" % (SENSE_FLOOR, SENSE_CEILING, sense)
        )
    if sense == SENSE_FLOOR:
        return max(1.0, requirement / value)
    return max(1.0, value / requirement)


def normalize_inventory(inventory):
    """Normalize a declared bench, refusing unknown and duplicated items."""
    if not isinstance(inventory, (list, tuple)):
        raise ValueError("inventory: must be a list of declared item records")
    normalized = {}
    for index, item in enumerate(inventory):
        if not isinstance(item, dict):
            raise ValueError("inventory[%d]: must be a mapping" % index)
        if "item" not in item:
            raise ValueError("inventory[%d]: missing required field 'item'" % index)
        name = item["item"]
        if not isinstance(name, str):
            raise ValueError("inventory[%d]: 'item' must be a string" % index)
        key = name.strip().lower()
        if key not in REQUIRED_ITEMS:
            raise ValueError(
                "inventory[%d]: unrecognized item %r; recognized: %s"
                % (index, name, ", ".join(REQUIRED_ITEMS))
            )
        if key in normalized:
            raise ValueError("inventory[%d]: item %r declared twice" % (index, key))
        record = dict(item)
        record.pop("item")
        normalized[key] = record
    return normalized


def derive_requirements(pulse):
    """Every requirement the specified pulse puts on the bench."""
    if not isinstance(pulse, dict):
        raise ValueError("pulse: record must be a mapping")
    terminal = _positive(_number(pulse, "terminal_v", "pulse"), "pulse.terminal_v")
    rise = _positive(_number(pulse, "rise_time_s", "pulse"), "pulse.rise_time_s")
    width = _positive(_number(pulse, "width_s", "pulse"), "pulse.width_s")
    window = _positive(_number(pulse, "window_s", "pulse"), "pulse.window_s")
    source_z = _number(pulse, "source_impedance_ohm", "pulse")
    load_z = _positive(
        _number(pulse, "load_impedance_ohm", "pulse"), "pulse.load_impedance_ohm"
    )
    eut_z = _positive(
        _number(pulse, "eut_impedance_ohm", "pulse"), "pulse.eut_impedance_ohm"
    )
    diversion = _fraction(
        _number(pulse, "allowed_diversion_fraction", "pulse"),
        "pulse.allowed_diversion_fraction",
    )
    loss = _fraction(
        _number(pulse, "allowed_coupling_loss_fraction", "pulse"),
        "pulse.allowed_coupling_loss_fraction",
    )
    duty = _fraction(
        _number(pulse, "duty_fraction", "pulse"), "pulse.duty_fraction"
    )
    if width < rise:
        raise ValueError(
            "pulse: width_s %g cannot be shorter than rise_time_s %g" % (width, rise)
        )
    if window < width:
        raise ValueError(
            "pulse: window_s %g cannot be shorter than width_s %g" % (window, width)
        )
    chain_rise = chain_rise_time_ceiling_s(rise)
    bandwidth = chain_bandwidth_hz(chain_rise)
    rate = sample_rate_hz(bandwidth)
    return {
        "open_circuit_v": generator_open_circuit_v(terminal, source_z, load_z),
        "generator_rise_time_ceiling_s": generator_rise_time_ceiling_s(rise),
        "repetition_interval_floor_s": repetition_interval_floor_s(width, duty),
        "coupling_impedance_ceiling_ohm": coupling_impedance_ceiling_ohm(load_z, loss),
        "decoupling_impedance_floor_ohm": decoupling_impedance_floor_ohm(
            eut_z, diversion
        ),
        "chain_rise_time_ceiling_s": chain_rise,
        "bandwidth_hz": bandwidth,
        "sample_rate_hz": rate,
        "record_depth_samples": record_depth_samples(window, rate),
        "probe_rating_v": probe_rating_v(terminal),
        "delivered_energy_j": delivered_energy_j(terminal, load_z, width),
    }


_CHECKS = (
    (ITEM_GENERATOR, "open_circuit_v", "open_circuit_v", SENSE_FLOOR),
    (ITEM_GENERATOR, "rise_time_s", "generator_rise_time_ceiling_s", SENSE_CEILING),
    (
        ITEM_GENERATOR,
        "repetition_interval_s",
        "repetition_interval_floor_s",
        SENSE_FLOOR,
    ),
    (
        ITEM_COUPLING,
        "series_impedance_ohm",
        "coupling_impedance_ceiling_ohm",
        SENSE_CEILING,
    ),
    (
        ITEM_DECOUPLING,
        "impedance_ohm",
        "decoupling_impedance_floor_ohm",
        SENSE_FLOOR,
    ),
    (ITEM_OSCILLOSCOPE, "bandwidth_hz", "bandwidth_hz", SENSE_FLOOR),
    (ITEM_OSCILLOSCOPE, "sample_rate_hz", "sample_rate_hz", SENSE_FLOOR),
    (ITEM_OSCILLOSCOPE, "record_depth_samples", "record_depth_samples", SENSE_FLOOR),
    (ITEM_VOLTAGE_PROBE, "rating_v", "probe_rating_v", SENSE_FLOOR),
    (ITEM_VOLTAGE_PROBE, "rise_time_s", "chain_rise_time_ceiling_s", SENSE_CEILING),
)


def assess_transient_bench(
    pulse, inventory, marginal_fraction=DEFAULT_MARGINAL_FRACTION
):
    """Full clause 5.4.9.2 judgement on a declared transient-injection bench."""
    requirements = derive_requirements(pulse)
    declared = normalize_inventory(inventory)

    missing = [name for name in REQUIRED_ITEMS if name not in declared]

    checks = []
    for item, field, requirement_key, sense in _CHECKS:
        if item not in declared:
            continue
        record = declared[item]
        if field not in record:
            checks.append(
                {
                    "item": item,
                    "quantity": field,
                    "declared": None,
                    "required": requirements[requirement_key],
                    "sense": sense,
                    "fitness": FITNESS_INADEQUATE,
                    "shortfall_factor": float("inf"),
                }
            )
            continue
        value = _number(record, field, "%s.%s" % (item, field))
        required = requirements[requirement_key]
        fitness = categorize_capability(value, required, sense, marginal_fraction)
        checks.append(
            {
                "item": item,
                "quantity": field,
                "declared": value,
                "required": required,
                "sense": sense,
                "fitness": fitness,
                "shortfall_factor": shortfall_factor(value, required, sense),
            }
        )

    inadequate = [c for c in checks if c["fitness"] == FITNESS_INADEQUATE]
    marginal = [c for c in checks if c["fitness"] == FITNESS_MARGINAL]

    governing = None
    if inadequate:
        governing = max(
            inadequate,
            key=lambda c: (c["shortfall_factor"], c["item"], c["quantity"]),
        )

    findings = []
    limitations = []
    for name in missing:
        findings.append("required item %s was never declared" % name)
    for check in inadequate:
        if check["declared"] is None:
            findings.append(
                "%s declares no %s" % (check["item"], check["quantity"])
            )
        else:
            findings.append(
                "%s %s of %.4g is %s the %.4g required"
                % (
                    check["item"],
                    check["quantity"],
                    check["declared"],
                    "under" if check["sense"] == SENSE_FLOOR else "over",
                    check["required"],
                )
            )
    for check in marginal:
        limitations.append(
            "%s %s of %.4g sits on the %.4g required"
            % (check["item"], check["quantity"], check["declared"], check["required"])
        )

    return {
        "requirements": requirements,
        "checks": checks,
        "missing_items": missing,
        "governing_shortfall": governing,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_FIT if not findings else VERDICT_UNFIT,
    }
