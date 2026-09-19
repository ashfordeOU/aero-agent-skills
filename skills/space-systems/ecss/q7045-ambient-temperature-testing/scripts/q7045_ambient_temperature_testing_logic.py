"""Rates, instrumentation and measurement for a room-temperature metal test.

Anchor: ECSS-Q-ST-70-45C, test-conditions clause (ambient-temperature
mechanical testing: loading rate, load measurement and strain measurement).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Convert the commanded crosshead speed into the strain rate the parallel
   length actually sees, and into the elastic stress rate through the modulus.
2. Grade the stress rate against the elastic window and the strain rate
   against the plastic window as two separate verdicts.
3. Compute the peak load from section and expected strength and express it as
   a fraction of the load-cell range, refusing a peak below the usable span.
4. Check the load-cell calibration covers the test date.
5. Choose the extensometer class from the quantity being read and check the
   device gauge length against the reported one.
"""

import math

__all__ = [
    "SECONDS_PER_MINUTE",
    "ELASTIC_STRESS_RATE_WINDOW_MPA_S",
    "PLASTIC_STRAIN_RATE_WINDOW_PER_S",
    "MIN_LOAD_CELL_UTILISATION",
    "MAX_LOAD_CELL_UTILISATION",
    "EXTENSOMETER_CLASS_FOR_QUANTITY",
    "GAUGE_LENGTH_MATCH_TOLERANCE_MM",
    "strain_rate_per_s",
    "stress_rate_mpa_s",
    "rate_within_window",
    "peak_load_kn",
    "load_cell_utilisation",
    "calibration_valid",
    "required_extensometer_class",
    "extensometer_suitable",
    "assess_ambient_test",
]

SECONDS_PER_MINUTE = 60.0

# Elastic region is controlled in stress rate; plastic region in strain rate.
ELASTIC_STRESS_RATE_WINDOW_MPA_S = (2.0, 20.0)
PLASTIC_STRAIN_RATE_WINDOW_PER_S = (0.00005, 0.0025)

# The usable span of a load cell: below the lower fraction the cell's own
# uncertainty dominates the reading.
MIN_LOAD_CELL_UTILISATION = 0.10
MAX_LOAD_CELL_UTILISATION = 1.0

# Class 1 devices are needed for a small-offset measurement; class 2 suffices
# for a large displacement read after fracture.
EXTENSOMETER_CLASS_FOR_QUANTITY = {
    "proof-strength": 1,
    "modulus": 1,
    "yield-strength": 1,
    "tensile-strength": 2,
    "elongation-after-fracture": 2,
    "reduction-of-area": 2,
}

GAUGE_LENGTH_MATCH_TOLERANCE_MM = 0.1


def _positive(value, label):
    """Return a validated strictly positive finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _token(value, label):
    """Return a stripped, lower-cased non-empty token."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % label)
    return token


def _window(window, label):
    """Return a validated (low, high) rate window."""
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _positive(window[0], "%s low" % label)
    high = _positive(window[1], "%s high" % label)
    if low >= high:
        raise ValueError("%s low %g must be below high %g" % (label, low, high))
    return (low, high)


def strain_rate_per_s(crosshead_speed_mm_min, parallel_length_mm):
    """Return the strain rate the parallel length sees, per second."""
    speed = _positive(crosshead_speed_mm_min, "crosshead_speed_mm_min")
    length = _positive(parallel_length_mm, "parallel_length_mm")
    return (speed / SECONDS_PER_MINUTE) / length


def stress_rate_mpa_s(strain_rate, modulus_mpa):
    """Return the elastic stress rate implied by a strain rate."""
    rate = _positive(strain_rate, "strain_rate")
    modulus = _positive(modulus_mpa, "modulus_mpa")
    return rate * modulus


def rate_within_window(rate, window):
    """Return whether a rate sits inside its window, boundaries included."""
    low, high = _window(window, "window")
    value = _positive(rate, "rate")
    below = value < low and not math.isclose(value, low, rel_tol=1e-12, abs_tol=0.0)
    above = value > high and not math.isclose(value, high, rel_tol=1e-12, abs_tol=0.0)
    return {
        "rate": value,
        "window": (low, high),
        "within": not (below or above),
        "too_slow": below,
        "too_fast": above,
    }


def peak_load_kn(area_mm2, expected_strength_mpa):
    """Return the peak load the piece will reach, in kilonewtons."""
    area = _positive(area_mm2, "area_mm2")
    strength = _positive(expected_strength_mpa, "expected_strength_mpa")
    return area * strength / 1000.0


def load_cell_utilisation(peak_kn, cell_range_kn,
                          minimum=MIN_LOAD_CELL_UTILISATION):
    """Return the peak load as a fraction of the cell range and its verdict."""
    peak = _positive(peak_kn, "peak_kn")
    cell_range = _positive(cell_range_kn, "cell_range_kn")
    floor_fraction = _positive(minimum, "minimum")
    fraction = peak / cell_range
    too_low = fraction < floor_fraction and not math.isclose(
        fraction, floor_fraction, rel_tol=1e-12, abs_tol=0.0
    )
    over_range = fraction > MAX_LOAD_CELL_UTILISATION and not math.isclose(
        fraction, MAX_LOAD_CELL_UTILISATION, rel_tol=1e-12, abs_tol=0.0
    )
    return {
        "fraction": fraction,
        "minimum": floor_fraction,
        "too_low": too_low,
        "over_range": over_range,
        "ok": not (too_low or over_range),
    }


def calibration_valid(test_date, calibration_due_date):
    """Return whether the calibration still covers the test date."""
    for label, value in (
        ("test_date", test_date),
        ("calibration_due_date", calibration_due_date),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s must be an ISO date string" % label)
        parts = value.strip().split("-")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise ValueError("%s must be an ISO yyyy-mm-dd date, got %r" % (label, value))
    return test_date.strip() <= calibration_due_date.strip()


def required_extensometer_class(quantity):
    """Return the extensometer class the measured quantity demands."""
    token = _token(quantity, "quantity")
    if token not in EXTENSOMETER_CLASS_FOR_QUANTITY:
        raise ValueError(
            "quantity %r is not one of %s"
            % (token, ", ".join(sorted(EXTENSOMETER_CLASS_FOR_QUANTITY)))
        )
    return EXTENSOMETER_CLASS_FOR_QUANTITY[token]


def extensometer_suitable(quantity, device_class, device_gauge_length_mm,
                          reported_gauge_length_mm):
    """Return whether the fitted extensometer suits the measured quantity."""
    required = required_extensometer_class(quantity)
    if not isinstance(device_class, int) or isinstance(device_class, bool):
        raise ValueError("device_class must be an integer class number")
    if device_class < 1:
        raise ValueError("device_class must be 1 or higher, got %d" % device_class)
    device_length = _positive(device_gauge_length_mm, "device_gauge_length_mm")
    reported_length = _positive(reported_gauge_length_mm, "reported_gauge_length_mm")
    findings = []
    # A lower class number is a tighter device, so it satisfies a looser need.
    if device_class > required:
        findings.append(
            "class %d extensometer is looser than the class %d a %s reading needs"
            % (device_class, required, _token(quantity, "quantity"))
        )
    mismatch = abs(device_length - reported_length)
    if mismatch > GAUGE_LENGTH_MATCH_TOLERANCE_MM and not math.isclose(
        mismatch, GAUGE_LENGTH_MATCH_TOLERANCE_MM, rel_tol=0.0, abs_tol=1e-12
    ):
        findings.append(
            "extensometer gauge length %.3f mm differs from the %.3f mm the result "
            "is reported on" % (device_length, reported_length)
        )
    return {
        "required_class": required,
        "device_class": device_class,
        "gauge_length_mismatch_mm": mismatch,
        "ok": not findings,
        "findings": findings,
    }


def assess_ambient_test(spec):
    """Grade a room-temperature test setup against the rate and instrument rules.

    spec keys: crosshead_speed_mm_min, parallel_length_mm, modulus_mpa,
    area_mm2, expected_strength_mpa, load_cell_range_kn, test_date,
    calibration_due_date, measured_quantity, extensometer_class,
    extensometer_gauge_length_mm, reported_gauge_length_mm, optional
    elastic_window_mpa_s and plastic_window_per_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "crosshead_speed_mm_min",
        "parallel_length_mm",
        "modulus_mpa",
        "area_mm2",
        "expected_strength_mpa",
        "load_cell_range_kn",
        "test_date",
        "calibration_due_date",
        "measured_quantity",
        "extensometer_class",
        "extensometer_gauge_length_mm",
        "reported_gauge_length_mm",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    findings = []
    strain_rate = strain_rate_per_s(
        spec["crosshead_speed_mm_min"], spec["parallel_length_mm"]
    )
    stress_rate = stress_rate_mpa_s(strain_rate, spec["modulus_mpa"])

    elastic = rate_within_window(
        stress_rate, spec.get("elastic_window_mpa_s", ELASTIC_STRESS_RATE_WINDOW_MPA_S)
    )
    plastic = rate_within_window(
        strain_rate, spec.get("plastic_window_per_s", PLASTIC_STRAIN_RATE_WINDOW_PER_S)
    )
    if elastic["too_fast"]:
        findings.append(
            "elastic stress rate %.3f MPa/s is above its window; a fast pull "
            "inflates the measured strength" % elastic["rate"]
        )
    if elastic["too_slow"]:
        findings.append(
            "elastic stress rate %.3f MPa/s is below its window" % elastic["rate"]
        )
    if plastic["too_fast"]:
        findings.append(
            "plastic strain rate %.3e /s is above its window; a fast pull inflates "
            "the measured strength" % plastic["rate"]
        )
    if plastic["too_slow"]:
        findings.append(
            "plastic strain rate %.3e /s is below its window" % plastic["rate"]
        )

    peak = peak_load_kn(spec["area_mm2"], spec["expected_strength_mpa"])
    utilisation = load_cell_utilisation(peak, spec["load_cell_range_kn"])
    if utilisation["too_low"]:
        findings.append(
            "peak load is %.1f %% of the cell range, below the %.1f %% usable span; "
            "fit a smaller cell"
            % (100.0 * utilisation["fraction"], 100.0 * utilisation["minimum"])
        )
    if utilisation["over_range"]:
        findings.append(
            "peak load is %.1f %% of the cell range; the cell is over-run"
            % (100.0 * utilisation["fraction"])
        )

    calibrated = calibration_valid(spec["test_date"], spec["calibration_due_date"])
    if not calibrated:
        findings.append(
            "load-cell calibration expired on %s, before the %s test date"
            % (spec["calibration_due_date"], spec["test_date"])
        )

    extensometer = extensometer_suitable(
        spec["measured_quantity"],
        spec["extensometer_class"],
        spec["extensometer_gauge_length_mm"],
        spec["reported_gauge_length_mm"],
    )
    findings.extend(extensometer["findings"])

    return {
        "strain_rate_per_s": strain_rate,
        "stress_rate_mpa_s": stress_rate,
        "elastic_rate": elastic,
        "plastic_rate": plastic,
        "peak_load_kn": peak,
        "load_cell": utilisation,
        "calibration_valid": calibrated,
        "extensometer": extensometer,
        "acceptable": not findings,
        "status": "run-valid" if not findings else "run-finding",
        "findings": findings,
    }
