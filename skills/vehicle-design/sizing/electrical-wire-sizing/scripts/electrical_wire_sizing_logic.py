"""Electrical wire sizing logic for aircraft power feeders (pure stdlib).

Implements the standard engineering model for conductor selection on a
derated bundled ampacity basis and the round-trip voltage drop check:

- ampacity(gauge, ambient_c): base free-air 30 C ampacity multiplied by
  the bundle derate and the linear temperature derate.
- select_gauge(load_current, ambient_c): smallest gauge whose derated
  ampacity meets the continuous load.
- resistance_per_meter(gauge, temp_c): copper resistance at the
  operating temperature from resistivity, temperature coefficient and
  the conductor cross section.
- voltage_drop(load_current, length_m, gauge, temp_c): round-trip drop
  over the run.
- percent_drop(voltage_drop, bus_voltage): drop as a percent of the bus.
- wire_size_review(...): the gauge selection and drop verdict bundle.

Documented model constants (copper conductor reference data set). The
0.94 temperature derate constant is the linear model value at the
40 C calibration point; the slope keeps 1.0 at 30 C and the 45 C
worked-example value at 0.91 as anchored in the validation list.
"""

AMPACITY_TABLE = {
    "22": 5.0,
    "20": 7.5,
    "18": 10.0,
    "16": 13.0,
    "14": 17.0,
    "12": 23.0,
    "10": 33.0,
    "8": 46.0,
    "6": 60.0,
}

AREA_MM2 = {
    "22": 0.324,
    "20": 0.519,
    "18": 0.823,
    "16": 1.31,
    "14": 2.08,
    "12": 3.31,
    "10": 5.26,
    "8": 8.37,
    "6": 13.3,
}

BUNDLE_DERATE = 0.60  # bundle of 5 or more wires
TEMP_DERATE = 0.94  # linear model value at the 40 C calibration reference
TEMP_DERATE_REF_AMBIENT_C = 40.0  # ambient where the derate equals 0.94
TEMP_DERATE_BASE_C = 30.0  # ambient where the derate equals 1.0
MIN_TEMP_DERATE = 0.5  # floor of the linear temperature derate model
TEMP_DERATE_SLOPE_PER_C = (
    (1.0 - TEMP_DERATE) / (TEMP_DERATE_REF_AMBIENT_C - TEMP_DERATE_BASE_C)
)  # 0.006 derate loss per C above 30

RESISTIVITY_COPPER = 1.72e-8  # ohm m at 20 C
TEMP_COEFFICIENT = 0.00393  # 1/C
REFERENCE_TEMP_C = 20.0

MAX_PERCENT_DROP = 3.0  # percent, bus tolerance for the run

MIN_AMBIENT_C = 30.0
MAX_AMBIENT_C = 100.0

GAUGES = tuple(AMPACITY_TABLE.keys())  # "22" up to "6", ascending


def _validate_gauge(gauge):
    if gauge not in AMPACITY_TABLE:
        raise ValueError("unknown gauge %r; use one of %s" % (gauge, list(GAUGES)))


def _temp_derate_at(ambient_c):
    """Linear temperature derate: 1.0 at 30 C minus 0.006 per C above 30."""
    return max(
        1.0 - TEMP_DERATE_SLOPE_PER_C * (ambient_c - TEMP_DERATE_BASE_C),
        MIN_TEMP_DERATE,
    )


def ampacity(gauge, ambient_c):
    """Derated bundled ampacity in amperes for the gauge at the ambient.

    base free-air 30 C ampacity * BUNDLE_DERATE * temperature derate.
    """
    _validate_gauge(gauge)
    if ambient_c < MIN_AMBIENT_C or ambient_c > MAX_AMBIENT_C:
        raise ValueError(
            "ambient %r C outside the model band [%r, %r]"
            % (ambient_c, MIN_AMBIENT_C, MAX_AMBIENT_C)
        )
    derate = _temp_derate_at(ambient_c)
    return AMPACITY_TABLE[gauge] * BUNDLE_DERATE * derate


def select_gauge(load_current, ambient_c):
    """Smallest gauge whose derated ampacity meets the continuous load.

    Raises ValueError when the load exceeds the 6 AWG capacity.
    """
    if load_current <= 0:
        raise ValueError("load current must be positive, got %r" % load_current)
    for gauge in GAUGES:
        if ampacity(gauge, ambient_c) >= load_current:
            return gauge
    raise ValueError(
        "load current %r A exceeds the 6 AWG derated ampacity %r A"
        % (load_current, ampacity("6", ambient_c))
    )


def resistance_per_meter(gauge, temp_c):
    """Conductor resistance in ohm per meter at the operating temperature."""
    _validate_gauge(gauge)
    resistivity = RESISTIVITY_COPPER * (
        1.0 + TEMP_COEFFICIENT * (temp_c - REFERENCE_TEMP_C)
    )
    return resistivity / (AREA_MM2[gauge] * 1e-6)


def voltage_drop(load_current, length_m, gauge, temp_c):
    """Round-trip voltage drop in volts over the run at the load current."""
    if load_current < 0:
        raise ValueError("load current must be non-negative, got %r" % load_current)
    if length_m < 0:
        raise ValueError("run length must be non-negative, got %r" % length_m)
    return (
        2.0
        * length_m
        * load_current
        * resistance_per_meter(gauge, temp_c)
    )


def percent_drop(voltage_drop_v, bus_voltage):
    """Voltage drop as a percent of the bus voltage."""
    if bus_voltage <= 0:
        raise ValueError("bus voltage must be positive, got %r" % bus_voltage)
    return 100.0 * voltage_drop_v / bus_voltage


def wire_size_review(load_current, length_m, bus_voltage, ambient_c, temp_c):
    """Gauge selection and drop verdict for the wire run.

    Returns dict with keys gauge, ampacity, margin_A, voltage_drop_V,
    percent_drop, verdict ("pass" when percent_drop <= MAX_PERCENT_DROP
    else "fail").
    """
    gauge = select_gauge(load_current, ambient_c)
    capacity = ampacity(gauge, ambient_c)
    drop = voltage_drop(load_current, length_m, gauge, temp_c)
    pct = percent_drop(drop, bus_voltage)
    verdict = "pass" if pct <= MAX_PERCENT_DROP else "fail"
    return {
        "gauge": gauge,
        "ampacity": capacity,
        "margin_A": capacity - load_current,
        "voltage_drop_V": drop,
        "percent_drop": pct,
        "verdict": verdict,
    }
