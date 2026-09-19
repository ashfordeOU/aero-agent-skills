"""Thermal control for elevated and low temperature metallic mechanical tests.

Anchor: ECSS-Q-ST-70-45C, test-conditions clause (testing away from ambient:
soaking the piece, measuring its temperature and holding it while loaded).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the deviation allowance for the nominal temperature off a ladder.
2. Size the soak from the section and the mode, hot or cold, and compare it
   with the soak actually held.
3. Take the number of measurement points the parallel length requires.
4. Grade the mean piece temperature against the allowance, and the axial
   gradient across the points against its own separate limit.
5. Grade the stability of the readings across the loaded window.
6. Check the strain device rating covers the nominal temperature.
"""

import math

__all__ = [
    "AMBIENT_C",
    "DEVIATION_LADDER_C",
    "AXIAL_GRADIENT_LIMIT_FRACTION",
    "MIN_AXIAL_GRADIENT_LIMIT_C",
    "SOAK_MINUTES_PER_MM_HOT",
    "SOAK_MINUTES_PER_MM_COLD",
    "MIN_SOAK_MINUTES",
    "THERMOCOUPLE_LENGTH_STEP_MM",
    "MAX_THERMOCOUPLES",
    "deviation_allowance_c",
    "thermal_mode",
    "required_soak_minutes",
    "required_thermocouples",
    "mean_temperature_c",
    "axial_gradient_c",
    "axial_gradient_limit_c",
    "loaded_window_stability_c",
    "device_rating_ok",
    "assess_thermal_test",
]

AMBIENT_C = 23.0

# Allowance ladder, read off the nominal temperature. Each entry is an upper
# bound in degrees Celsius paired with the allowance that applies at or below
# it; the last entry carries everything hotter.
DEVIATION_LADDER_C = (
    (-150.0, 2.0),   # deep cryogenic: the property moves fast with temperature
    (0.0, 2.0),
    (600.0, 3.0),
    (900.0, 4.0),
    (float("inf"), 5.0),
)

# The spread across the parallel length is its own acceptance, scaled with the
# allowance but never tighter than the instrumentation can resolve.
AXIAL_GRADIENT_LIMIT_FRACTION = 1.0
MIN_AXIAL_GRADIENT_LIMIT_C = 1.0

# Equilibration scales with the section; a cold soak is the slower of the two.
SOAK_MINUTES_PER_MM_HOT = 3.0
SOAK_MINUTES_PER_MM_COLD = 4.0
MIN_SOAK_MINUTES = 20.0

# One measurement point per step of parallel length, so a gradient is visible.
THERMOCOUPLE_LENGTH_STEP_MM = 50.0
MAX_THERMOCOUPLES = 3


def _real(value, label):
    """Return a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _temperature(value, label):
    """Return a validated temperature in degrees Celsius."""
    number = _real(value, label)
    if number < -273.15:
        raise ValueError("%s %g degC is below absolute zero" % (label, number))
    return number


def _positive(value, label):
    """Return a validated strictly positive finite float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def deviation_allowance_c(nominal_c):
    """Return the permitted deviation of the piece from the nominal, in kelvin."""
    nominal = _temperature(nominal_c, "nominal_c")
    for upper, allowance in DEVIATION_LADDER_C:
        if nominal < upper or math.isclose(nominal, upper, rel_tol=0.0, abs_tol=1e-9):
            return allowance
    return DEVIATION_LADDER_C[-1][1]


def thermal_mode(nominal_c):
    """Return whether the run is an elevated, an ambient or a low temperature one."""
    nominal = _temperature(nominal_c, "nominal_c")
    if nominal > AMBIENT_C and not math.isclose(
        nominal, AMBIENT_C, rel_tol=0.0, abs_tol=1e-9
    ):
        return "elevated"
    if nominal < AMBIENT_C and not math.isclose(
        nominal, AMBIENT_C, rel_tol=0.0, abs_tol=1e-9
    ):
        return "low"
    return "ambient"


def required_soak_minutes(section_mm, nominal_c):
    """Return the soak the section owes before the piece may be loaded."""
    section = _positive(section_mm, "section_mm")
    mode = thermal_mode(nominal_c)
    if mode == "ambient":
        raise ValueError(
            "an ambient nominal needs no soak from this clause; use the ambient "
            "conditioning rule instead"
        )
    rate = SOAK_MINUTES_PER_MM_COLD if mode == "low" else SOAK_MINUTES_PER_MM_HOT
    return max(MIN_SOAK_MINUTES, rate * section)


def required_thermocouples(parallel_length_mm):
    """Return the measurement points a parallel length needs to show a gradient."""
    length = _positive(parallel_length_mm, "parallel_length_mm")
    steps = int(math.ceil(length / THERMOCOUPLE_LENGTH_STEP_MM))
    return max(1, min(MAX_THERMOCOUPLES, steps))


def _readings(values, label):
    """Return a validated non-empty list of temperature readings."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("%s must be a non-empty sequence of readings" % label)
    return [_temperature(value, "%s reading" % label) for value in values]


def mean_temperature_c(readings):
    """Return the mean of the piece temperature readings."""
    values = _readings(readings, "readings")
    return math.fsum(values) / len(values)


def axial_gradient_c(readings):
    """Return the spread across the measurement points along the parallel length."""
    values = _readings(readings, "readings")
    return max(values) - min(values)


def axial_gradient_limit_c(nominal_c):
    """Return the permitted spread across the parallel length."""
    allowance = deviation_allowance_c(nominal_c)
    return max(MIN_AXIAL_GRADIENT_LIMIT_C, AXIAL_GRADIENT_LIMIT_FRACTION * allowance)


def loaded_window_stability_c(series, nominal_c):
    """Return the largest departure from nominal recorded while loaded."""
    if not isinstance(series, (list, tuple)) or not series:
        raise ValueError("series must be a non-empty sequence of samples")
    nominal = _temperature(nominal_c, "nominal_c")
    worst = None
    loaded = 0
    for index, sample in enumerate(series):
        if not isinstance(sample, dict):
            raise ValueError("series[%d] must be a mapping" % index)
        for key in ("time_s", "temperature_c", "window"):
            if key not in sample:
                raise ValueError("series[%d] omits '%s'" % (index, key))
        window = sample["window"]
        if not isinstance(window, str) or not window.strip():
            raise ValueError("series[%d] window must be a non-empty string" % index)
        if window.strip().lower() not in ("soak", "loaded"):
            raise ValueError(
                "series[%d] window %r is neither 'soak' nor 'loaded'" % (index, window)
            )
        if window.strip().lower() != "loaded":
            continue
        loaded += 1
        departure = abs(
            _temperature(sample["temperature_c"], "series[%d] temperature_c" % index)
            - nominal
        )
        if worst is None or departure > worst:
            worst = departure
    if loaded == 0:
        raise ValueError("series holds no sample taken while the piece was loaded")
    return {"max_departure_c": worst, "loaded_samples": loaded}


def device_rating_ok(nominal_c, rating_min_c, rating_max_c):
    """Return whether a strain device is rated for the nominal temperature."""
    nominal = _temperature(nominal_c, "nominal_c")
    low = _temperature(rating_min_c, "rating_min_c")
    high = _temperature(rating_max_c, "rating_max_c")
    if low >= high:
        raise ValueError("rating_min_c %g must be below rating_max_c %g" % (low, high))
    below = nominal < low and not math.isclose(nominal, low, rel_tol=0.0, abs_tol=1e-9)
    above = nominal > high and not math.isclose(nominal, high, rel_tol=0.0, abs_tol=1e-9)
    return not (below or above)


def assess_thermal_test(spec):
    """Grade a non-ambient test against the thermal-control rules.

    spec keys: nominal_c, section_mm, parallel_length_mm, soak_minutes,
    piece_readings_c, series, optional device_rating_c (a min/max pair).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "nominal_c",
        "section_mm",
        "parallel_length_mm",
        "soak_minutes",
        "piece_readings_c",
        "series",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    nominal = _temperature(spec["nominal_c"], "nominal_c")
    mode = thermal_mode(nominal)
    if mode == "ambient":
        raise ValueError(
            "nominal %g degC is an ambient test; grade it against the ambient "
            "clause, not this one" % nominal
        )
    findings = []
    allowance = deviation_allowance_c(nominal)

    owed_soak = required_soak_minutes(spec["section_mm"], nominal)
    held_soak = _real(spec["soak_minutes"], "soak_minutes")
    if held_soak < 0.0:
        raise ValueError("soak_minutes must not be negative")
    soak_ok = held_soak > owed_soak or math.isclose(
        held_soak, owed_soak, rel_tol=0.0, abs_tol=1e-9
    )
    if not soak_ok:
        findings.append(
            "soak held for %.1f min against the %.1f min the %.1f mm section owes; "
            "the core is not at temperature"
            % (held_soak, owed_soak, float(spec["section_mm"]))
        )

    readings = _readings(spec["piece_readings_c"], "piece_readings_c")
    needed_points = required_thermocouples(spec["parallel_length_mm"])
    if len(readings) < needed_points:
        findings.append(
            "%d measurement point(s) on a %.1f mm parallel length, where %d are "
            "needed; a gradient cannot be seen"
            % (len(readings), float(spec["parallel_length_mm"]), needed_points)
        )

    mean_value = mean_temperature_c(readings)
    mean_deviation = abs(mean_value - nominal)
    mean_ok = mean_deviation < allowance or math.isclose(
        mean_deviation, allowance, rel_tol=0.0, abs_tol=1e-9
    )
    if not mean_ok:
        findings.append(
            "mean piece temperature %.2f degC departs from the %.2f degC nominal by "
            "%.2f K, past the %.2f K allowance"
            % (mean_value, nominal, mean_deviation, allowance)
        )

    gradient = axial_gradient_c(readings)
    gradient_limit = axial_gradient_limit_c(nominal)
    gradient_ok = gradient < gradient_limit or math.isclose(
        gradient, gradient_limit, rel_tol=0.0, abs_tol=1e-9
    )
    if not gradient_ok:
        findings.append(
            "axial gradient %.2f K across the parallel length exceeds the %.2f K "
            "limit; the mean says nothing about the ends"
            % (gradient, gradient_limit)
        )

    stability = loaded_window_stability_c(spec["series"], nominal)
    stability_ok = stability["max_departure_c"] < allowance or math.isclose(
        stability["max_departure_c"], allowance, rel_tol=0.0, abs_tol=1e-9
    )
    if not stability_ok:
        findings.append(
            "temperature departed from nominal by %.2f K while the piece was "
            "loaded, past the %.2f K allowance; the property moved under the curve"
            % (stability["max_departure_c"], allowance)
        )

    rating = spec.get("device_rating_c")
    rated = None
    if rating is not None:
        if not isinstance(rating, (list, tuple)) or len(rating) != 2:
            raise ValueError("device_rating_c must be a (min, max) pair")
        rated = device_rating_ok(nominal, rating[0], rating[1])
        if not rated:
            findings.append(
                "strain device rated %g to %g degC is outside its rating at the "
                "%.2f degC nominal; part of the strain it reports is its own"
                % (float(rating[0]), float(rating[1]), nominal)
            )

    return {
        "mode": mode,
        "nominal_c": nominal,
        "allowance_c": allowance,
        "soak_minutes_owed": owed_soak,
        "soak_minutes_held": held_soak,
        "required_thermocouples": needed_points,
        "mean_temperature_c": mean_value,
        "mean_deviation_c": mean_deviation,
        "axial_gradient_c": gradient,
        "axial_gradient_limit_c": gradient_limit,
        "loaded_stability": stability,
        "device_rated": rated,
        "acceptable": not findings,
        "status": "thermal-control-met" if not findings else "thermal-control-finding",
        "findings": findings,
    }
