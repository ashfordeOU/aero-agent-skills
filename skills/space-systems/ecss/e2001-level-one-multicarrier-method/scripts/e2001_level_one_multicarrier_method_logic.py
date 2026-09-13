#!/usr/bin/env python3
"""Level-one multicarrier multipactor method (ECSS-E-ST-20-01C clause 5.3.2.2.4).

Deterministic, offline, stdlib-only implementation of the first-level procedure
for several carriers sharing one critical region: build the worst-case voltage
envelope from the individual carrier voltages, compare its peak against the
single-carrier boundary voltage carried over from the single-carrier method,
and where the peak exceeds the boundary, fall back on the build-up criterion --
the envelope must not stay above the boundary long enough for the resonance to
grow through the agreed number of gap crossings.

No standard text is reproduced; the clause is cited as the anchor only.
"""

import math

DEFAULT_IMPEDANCE_OHM = 50.0

# Gap crossings a resonance needs before it counts as an established discharge.
DEFAULT_GAP_CROSSINGS = 20

# Decibel margin owed by each verification route; project-agreed defaults.
ROUTE_MARGIN_DB = {
    "analysis-only": 6.0,
    "test-supported": 3.0,
}

# Sampling of one half envelope period before the crossing is bisected.
ENVELOPE_SAMPLES = 4096
BISECTION_STEPS = 80

VERDICT_PEAK_ENVELOPE = "compliant-by-peak-envelope"
VERDICT_CROSSING_RULE = "compliant-by-gap-crossing-rule"
VERDICT_PREDICTED = "multipaction-predicted"

# Commensurability tolerance, in hertz, for the envelope period.
FREQUENCY_GRID_HZ = 1.0e-3

REL_TOL = 1e-9


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return value


def validate_carrier_set(carriers):
    """Return the carrier set as sorted (frequency_hz, power_w) pairs.

    Raises ValueError for fewer than two carriers, a malformed entry, a
    non-positive frequency or power, or a repeated frequency.
    """
    if not isinstance(carriers, (list, tuple)):
        raise ValueError("carriers must be a sequence of mappings")
    if len(carriers) < 2:
        raise ValueError("the multicarrier method needs at least two carriers")
    seen = set()
    normalized = []
    for carrier in carriers:
        if not isinstance(carrier, dict):
            raise ValueError("each carrier must be a mapping, got %r" % (type(carrier),))
        frequency = _require_positive("frequency_hz", carrier.get("frequency_hz"))
        power = _require_positive("power_w", carrier.get("power_w"))
        key = round(frequency, 6)
        if key in seen:
            raise ValueError("duplicate carrier frequency %r Hz" % (frequency,))
        seen.add(key)
        normalized.append((frequency, power))
    normalized.sort()
    return normalized


def total_average_power_w(carriers):
    """Return the summed carrier-power of the set, in watts."""
    return sum(power for _, power in validate_carrier_set(carriers))


def carrier_peak_voltages(
    carriers,
    impedance_ohm=DEFAULT_IMPEDANCE_OHM,
    vswr=1.0,
    field_concentration=1.0,
):
    """Return the peak gap voltage each carrier contributes, in volts."""
    normalized = validate_carrier_set(carriers)
    impedance_ohm = _require_positive("impedance_ohm", impedance_ohm)
    field_concentration = _require_positive("field_concentration", field_concentration)
    vswr = _require_number("vswr", vswr)
    if vswr < 1.0 and not math.isclose(vswr, 1.0, rel_tol=REL_TOL):
        raise ValueError("vswr must be at least 1.0, got %r" % (vswr,))
    gamma = (max(vswr, 1.0) - 1.0) / (max(vswr, 1.0) + 1.0)
    scale = (1.0 + gamma) * field_concentration
    return [
        math.sqrt(2.0 * power * impedance_ohm) * scale for _, power in normalized
    ]


def peak_envelope_voltage(amplitudes):
    """Return the worst-case envelope peak: every carrier crest aligned."""
    if not isinstance(amplitudes, (list, tuple)) or not amplitudes:
        raise ValueError("amplitudes must be a non-empty sequence")
    total = 0.0
    for amplitude in amplitudes:
        total += _require_positive("amplitude", amplitude)
    return total


def equivalent_single_carrier_power_w(
    envelope_voltage_v,
    impedance_ohm=DEFAULT_IMPEDANCE_OHM,
    vswr=1.0,
    field_concentration=1.0,
):
    """Return the one-carrier power that would reach the same envelope peak."""
    envelope_voltage_v = _require_positive("envelope_voltage_v", envelope_voltage_v)
    impedance_ohm = _require_positive("impedance_ohm", impedance_ohm)
    field_concentration = _require_positive("field_concentration", field_concentration)
    vswr = _require_number("vswr", vswr)
    if vswr < 1.0 and not math.isclose(vswr, 1.0, rel_tol=REL_TOL):
        raise ValueError("vswr must be at least 1.0, got %r" % (vswr,))
    gamma = (max(vswr, 1.0) - 1.0) / (max(vswr, 1.0) + 1.0)
    line_v = envelope_voltage_v / ((1.0 + gamma) * field_concentration)
    return (line_v * line_v) / (2.0 * impedance_ohm)


def envelope_repetition_period_s(frequencies):
    """Return the repetition period of the carrier envelope, in seconds.

    The envelope repeats at the reciprocal of the greatest common divisor of
    the carrier spacings. Raises ValueError when the frequencies do not sit on
    a common grid, because then no finite repetition period exists.
    """
    if not isinstance(frequencies, (list, tuple)) or len(frequencies) < 2:
        raise ValueError("at least two carrier frequencies are needed")
    grid = []
    for frequency in frequencies:
        frequency = _require_positive("frequency_hz", frequency)
        nearest = round(frequency)
        if abs(frequency - nearest) > FREQUENCY_GRID_HZ:
            raise ValueError(
                "carrier frequency %r Hz is off the 1 Hz grid the envelope "
                "period is derived on" % (frequency,)
            )
        grid.append(int(nearest))
    reference = min(grid)
    divisor = 0
    for value in grid:
        divisor = math.gcd(divisor, abs(value - reference))
    if divisor == 0:
        raise ValueError("every carrier sits at the same frequency: no envelope")
    return 1.0 / float(divisor)


def envelope_voltage_at(amplitudes, frequencies, t_s):
    """Return the envelope magnitude at a time offset from the crest, in volts."""
    if len(amplitudes) != len(frequencies):
        raise ValueError("amplitudes and frequencies must have equal length")
    if not amplitudes:
        raise ValueError("at least one carrier is needed")
    t_s = _require_number("t_s", t_s)
    reference = _require_positive("frequency_hz", frequencies[0])
    real = 0.0
    imaginary = 0.0
    for amplitude, frequency in zip(amplitudes, frequencies):
        amplitude = _require_positive("amplitude", amplitude)
        frequency = _require_positive("frequency_hz", frequency)
        phase = 2.0 * math.pi * (frequency - reference) * t_s
        real += amplitude * math.cos(phase)
        imaginary += amplitude * math.sin(phase)
    return math.hypot(real, imaginary)


def longest_dwell_above_threshold_s(amplitudes, frequencies, threshold_v):
    """Return how long the envelope crest stays above a voltage, in seconds.

    The envelope is even about the instant every carrier crest aligns, so the
    dwell is twice the first downward crossing after that instant. A crest that
    never reaches the voltage dwells zero; one that never drops below it within
    the repetition period dwells the whole period.
    """
    threshold_v = _require_positive("threshold_v", threshold_v)
    period = envelope_repetition_period_s(list(frequencies))
    peak = envelope_voltage_at(amplitudes, frequencies, 0.0)
    if peak < threshold_v or math.isclose(peak, threshold_v, rel_tol=REL_TOL):
        return 0.0
    half = 0.5 * period
    step = half / ENVELOPE_SAMPLES
    low = 0.0
    high = None
    for index in range(1, ENVELOPE_SAMPLES + 1):
        t_s = index * step
        if envelope_voltage_at(amplitudes, frequencies, t_s) < threshold_v:
            high = t_s
            low = t_s - step
            break
    if high is None:
        return period
    for _ in range(BISECTION_STEPS):
        middle = 0.5 * (low + high)
        if envelope_voltage_at(amplitudes, frequencies, middle) < threshold_v:
            high = middle
        else:
            low = middle
    return 2.0 * (0.5 * (low + high))


def gap_crossing_time_s(frequency_hz):
    """Return the time one electron gap crossing takes: half a carrier period."""
    frequency_hz = _require_positive("frequency_hz", frequency_hz)
    return 1.0 / (2.0 * frequency_hz)


def required_dwell_time_s(frequencies, crossings=DEFAULT_GAP_CROSSINGS):
    """Return the dwell a resonance needs to build up, in seconds.

    The highest carrier crosses the gap fastest, so it sets the shortest
    build-up time and is the conservative choice.
    """
    if not isinstance(frequencies, (list, tuple)) or not frequencies:
        raise ValueError("at least one carrier frequency is needed")
    if isinstance(crossings, bool) or not isinstance(crossings, int):
        raise ValueError("crossings must be an integer, got %r" % (crossings,))
    if crossings < 1:
        raise ValueError("crossings must be at least 1, got %r" % (crossings,))
    fastest = max(_require_positive("frequency_hz", f) for f in frequencies)
    return crossings * gap_crossing_time_s(fastest)


def margin_db(threshold_v, applied_v):
    """Return the decibel margin of a boundary voltage over an applied voltage."""
    threshold_v = _require_positive("threshold_v", threshold_v)
    applied_v = _require_positive("applied_v", applied_v)
    return 20.0 * math.log10(threshold_v / applied_v)


def required_margin_db(route):
    """Return the decibel margin owed by a verification route."""
    if not isinstance(route, str) or not route.strip():
        raise ValueError("route must be a non-empty string")
    key = route.strip().lower()
    if key not in ROUTE_MARGIN_DB:
        raise ValueError("unknown verification route %r" % (route,))
    return ROUTE_MARGIN_DB[key]


def assess_multicarrier(
    carriers,
    single_carrier_threshold_v,
    route="analysis-only",
    impedance_ohm=DEFAULT_IMPEDANCE_OHM,
    vswr=1.0,
    field_concentration=1.0,
    crossings=DEFAULT_GAP_CROSSINGS,
    region_id="unnamed-region",
):
    """Run the whole first-level multicarrier procedure for one critical region.

    Step one is the worst-case envelope peak against the boundary voltage with
    the route's margin applied. Where that fails, step two is the build-up
    criterion: the envelope dwell above the derated boundary against the time
    the agreed number of gap crossings needs.
    """
    normalized = validate_carrier_set(carriers)
    frequencies = [frequency for frequency, _ in normalized]
    amplitudes = carrier_peak_voltages(
        carriers, impedance_ohm, vswr, field_concentration
    )
    boundary = _require_positive(
        "single_carrier_threshold_v", single_carrier_threshold_v
    )
    owed = required_margin_db(route)
    envelope_peak = peak_envelope_voltage(amplitudes)
    achieved = margin_db(boundary, envelope_peak)
    derated_boundary = boundary / (10.0 ** (owed / 20.0))
    record = {
        "region_id": region_id,
        "carrier_count": len(normalized),
        "total_average_power_w": sum(power for _, power in normalized),
        "peak_envelope_voltage_v": envelope_peak,
        "single_carrier_threshold_v": boundary,
        "derated_threshold_v": derated_boundary,
        "achieved_margin_db": achieved,
        "required_margin_db": owed,
        "envelope_period_s": envelope_repetition_period_s(frequencies),
        "dwell_above_threshold_s": 0.0,
        "required_dwell_s": required_dwell_time_s(frequencies, crossings),
        "verdict": VERDICT_PEAK_ENVELOPE,
        "actions": [],
    }
    if achieved >= owed or math.isclose(
        achieved, owed, rel_tol=REL_TOL, abs_tol=1e-12
    ):
        return record
    dwell = longest_dwell_above_threshold_s(
        amplitudes, frequencies, derated_boundary
    )
    record["dwell_above_threshold_s"] = dwell
    if dwell < record["required_dwell_s"] and not math.isclose(
        dwell, record["required_dwell_s"], rel_tol=REL_TOL
    ):
        record["verdict"] = VERDICT_CROSSING_RULE
        record["actions"].append(
            "credit rests on the build-up criterion: the envelope holds the "
            "derated boundary for %.4g s against the %.4g s the resonance "
            "needs, so the carrier plan is part of the evidence"
            % (dwell, record["required_dwell_s"])
        )
        return record
    record["verdict"] = VERDICT_PREDICTED
    record["actions"].append(
        "raise the gap or lower the carrier plan: the envelope holds the "
        "derated boundary for %.4g s, at or over the %.4g s the resonance needs"
        % (dwell, record["required_dwell_s"])
    )
    return record
