"""Laboratory environment control for metallic mechanical testing.

Anchor: ECSS-Q-ST-70-45C, test-conditions clause (the temperature, humidity
and atmosphere the test is carried out in, and the conditioning the test piece
owes). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate a recorded environmental series, in increasing time order.
2. Grade each sample against the permitted temperature and humidity bands.
3. Group consecutive out-of-band samples into excursions carrying a depth and
   a duration, and decide each against its allowance.
4. Separate an excursion in the conditioning window from one in the loaded
   window, because only the first can be recovered by extending the soak.
5. Check the dew point against the test-piece temperature as a condensation
   stop, derive the section-driven conditioning time, and decide the
   atmosphere from the material sensitivity and the test temperature.
"""

import math

__all__ = [
    "REFERENCE_AMBIENT_C",
    "AMBIENT_BAND_C",
    "CONTROLLED_HUMIDITY_BAND_PCT",
    "MAX_EXCURSION_DEPTH_C",
    "MAX_LOADED_EXCURSION_S",
    "MAX_CONDITIONING_EXCURSION_S",
    "MOISTURE_SENSITIVE_FAMILIES",
    "OXIDATION_SENSITIVE_FAMILIES",
    "OXIDATION_THRESHOLD_C",
    "CONDITIONING_MINUTES_PER_MM",
    "MIN_CONDITIONING_MINUTES",
    "validate_series",
    "within_band",
    "band_excursions",
    "humidity_control_required",
    "dew_point_c",
    "condensation_risk",
    "conditioning_minutes",
    "required_atmosphere",
    "assess_environment",
]

# The condition results are reported against, distinct from the band the room
# is allowed to sit in.
REFERENCE_AMBIENT_C = 23.0
AMBIENT_BAND_C = (18.0, 28.0)

# Where the material or the test type needs humidity held, this is the band.
CONTROLLED_HUMIDITY_BAND_PCT = (30.0, 60.0)

# An excursion is graded on depth and duration together.
MAX_EXCURSION_DEPTH_C = 2.0
MAX_LOADED_EXCURSION_S = 0.0          # nothing outside the band while loaded
MAX_CONDITIONING_EXCURSION_S = 300.0  # recoverable by extending the soak

MOISTURE_SENSITIVE_FAMILIES = frozenset(
    {"magnesium-alloy", "high-strength-steel", "aluminium-lithium-alloy"}
)

OXIDATION_SENSITIVE_FAMILIES = frozenset(
    {"titanium-alloy", "magnesium-alloy", "refractory-alloy", "beryllium-alloy"}
)

# Above this the surface grown during the soak becomes part of what is pulled.
OXIDATION_THRESHOLD_C = 250.0

# Thermal equilibration scales with the section that has to come to
# temperature.
CONDITIONING_MINUTES_PER_MM = 2.0
MIN_CONDITIONING_MINUTES = 15.0

_WINDOWS = ("conditioning", "loaded")


def _real(value, label):
    """Return a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _token(value, label):
    """Return a stripped, lower-cased non-empty token."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % label)
    return token


def _band(band, label):
    """Return a validated (low, high) band with a positive width."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _real(band[0], "%s low" % label)
    high = _real(band[1], "%s high" % label)
    if low >= high:
        raise ValueError("%s low %g must be below high %g" % (label, low, high))
    return (low, high)


def validate_series(series):
    """Return the validated environmental samples in increasing time order."""
    if not isinstance(series, (list, tuple)) or not series:
        raise ValueError("series must be a non-empty sequence of samples")
    samples = []
    previous_time = None
    for index, sample in enumerate(series):
        if not isinstance(sample, dict):
            raise ValueError("series[%d] must be a mapping" % index)
        for key in ("time_s", "temperature_c"):
            if key not in sample:
                raise ValueError("series[%d] omits '%s'" % (index, key))
        time_s = _real(sample["time_s"], "series[%d] time_s" % index)
        if time_s < 0.0:
            raise ValueError("series[%d] time_s must not be negative" % index)
        if previous_time is not None and time_s <= previous_time:
            raise ValueError(
                "series[%d] time %g does not increase past %g"
                % (index, time_s, previous_time)
            )
        previous_time = time_s
        entry = {
            "time_s": time_s,
            "temperature_c": _real(
                sample["temperature_c"], "series[%d] temperature_c" % index
            ),
        }
        if sample.get("humidity_pct") is not None:
            humidity = _real(sample["humidity_pct"], "series[%d] humidity_pct" % index)
            if humidity < 0.0 or humidity > 100.0:
                raise ValueError(
                    "series[%d] humidity_pct %g is outside 0-100" % (index, humidity)
                )
            entry["humidity_pct"] = humidity
        window = sample.get("window", "loaded")
        token = _token(window, "series[%d] window" % index)
        if token not in _WINDOWS:
            raise ValueError(
                "series[%d] window %r is not one of %s"
                % (index, token, ", ".join(_WINDOWS))
            )
        entry["window"] = token
        samples.append(entry)
    return samples


def within_band(value, band):
    """Return whether a reading sits inside its band, boundary included."""
    low, high = _band(band, "band")
    reading = _real(value, "value")
    if reading < low and not math.isclose(reading, low, rel_tol=0.0, abs_tol=1e-12):
        return False
    if reading > high and not math.isclose(reading, high, rel_tol=0.0, abs_tol=1e-12):
        return False
    return True


def band_excursions(series, band, key="temperature_c"):
    """Group consecutive out-of-band samples into excursions."""
    samples = validate_series(series)
    low, high = _band(band, "band")
    excursions = []
    current = None
    for sample in samples:
        if key not in sample:
            if current is not None:
                excursions.append(current)
                current = None
            continue
        reading = sample[key]
        inside = within_band(reading, (low, high))
        if inside:
            if current is not None:
                excursions.append(current)
                current = None
            continue
        depth = low - reading if reading < low else reading - high
        if current is None or current["window"] != sample["window"]:
            if current is not None:
                excursions.append(current)
            current = {
                "start_s": sample["time_s"],
                "end_s": sample["time_s"],
                "depth_c": depth,
                "window": sample["window"],
                "samples": 1,
            }
        else:
            current["end_s"] = sample["time_s"]
            current["depth_c"] = max(current["depth_c"], depth)
            current["samples"] += 1
    if current is not None:
        excursions.append(current)
    for excursion in excursions:
        excursion["duration_s"] = excursion["end_s"] - excursion["start_s"]
    return excursions


def humidity_control_required(material_family, test_type):
    """Return whether the run owes a controlled relative humidity."""
    family = _token(material_family, "material_family")
    kind = _token(test_type, "test_type")
    moisture_driven = kind in (
        "stress-corrosion",
        "sustained-load",
        "fatigue",
        "fatigue-crack-growth",
    )
    return family in MOISTURE_SENSITIVE_FAMILIES or moisture_driven


def dew_point_c(temperature_c, humidity_pct):
    """Return the dew point of the room from its temperature and humidity."""
    temperature = _real(temperature_c, "temperature_c")
    humidity = _real(humidity_pct, "humidity_pct")
    if humidity <= 0.0 or humidity > 100.0:
        raise ValueError(
            "humidity_pct must lie in (0, 100], got %g" % humidity
        )
    # Magnus form, the usual engineering approximation over laboratory range.
    a = 17.62
    b = 243.12
    gamma = (a * temperature) / (b + temperature) + math.log(humidity / 100.0)
    return (b * gamma) / (a - gamma)


def condensation_risk(piece_temperature_c, room_temperature_c, humidity_pct):
    """Return whether the test piece sits at or below the room dew point."""
    piece = _real(piece_temperature_c, "piece_temperature_c")
    dew = dew_point_c(room_temperature_c, humidity_pct)
    at_or_below = piece < dew or math.isclose(piece, dew, rel_tol=0.0, abs_tol=1e-9)
    return {"dew_point_c": dew, "piece_temperature_c": piece, "risk": at_or_below}


def conditioning_minutes(section_mm, rate=CONDITIONING_MINUTES_PER_MM,
                         floor_minutes=MIN_CONDITIONING_MINUTES):
    """Return the conditioning time the section owes before loading."""
    section = _real(section_mm, "section_mm")
    if section <= 0.0:
        raise ValueError("section_mm must be positive, got %g" % section)
    per_mm = _real(rate, "rate")
    if per_mm <= 0.0:
        raise ValueError("rate must be positive, got %g" % per_mm)
    floor_value = _real(floor_minutes, "floor_minutes")
    if floor_value < 0.0:
        raise ValueError("floor_minutes must not be negative")
    return max(floor_value, per_mm * section)


def required_atmosphere(material_family, test_temperature_c):
    """Return the atmosphere the material and temperature together demand."""
    family = _token(material_family, "material_family")
    temperature = _real(test_temperature_c, "test_temperature_c")
    hot = temperature > OXIDATION_THRESHOLD_C and not math.isclose(
        temperature, OXIDATION_THRESHOLD_C, rel_tol=0.0, abs_tol=1e-9
    )
    if family in OXIDATION_SENSITIVE_FAMILIES and hot:
        return {
            "atmosphere": "inert-or-vacuum",
            "reason": "%s above %.0f degC grows a surface in air that becomes part "
                      "of what is pulled" % (family, OXIDATION_THRESHOLD_C),
        }
    return {"atmosphere": "air", "reason": "no oxidation sensitivity at this temperature"}


def assess_environment(spec):
    """Grade a recorded laboratory environment against the test conditions.

    spec keys: series, material_family, test_type, test_temperature_c,
    section_mm, soak_minutes, optional temperature_band_c, humidity_band_pct,
    piece_temperature_c, atmosphere.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "series",
        "material_family",
        "test_type",
        "test_temperature_c",
        "section_mm",
        "soak_minutes",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    samples = validate_series(spec["series"])
    temperature_band = _band(
        spec.get("temperature_band_c", AMBIENT_BAND_C), "temperature_band_c"
    )
    findings = []

    temperature_excursions = band_excursions(samples, temperature_band, "temperature_c")
    for excursion in temperature_excursions:
        too_deep = excursion["depth_c"] > MAX_EXCURSION_DEPTH_C and not math.isclose(
            excursion["depth_c"], MAX_EXCURSION_DEPTH_C, rel_tol=0.0, abs_tol=1e-9
        )
        if excursion["window"] == "loaded":
            # The soak can be extended; the loaded run cannot be repeated in a
            # different room, so any departure here costs the result.
            excursion["recoverable"] = False
            excursion["acceptable"] = False
            findings.append(
                "temperature left the band by up to %.2f K for %.1f s during the "
                "loaded window; the loading cannot be re-run in a different room"
                % (excursion["depth_c"], excursion["duration_s"])
            )
            continue
        too_long = excursion["duration_s"] > MAX_CONDITIONING_EXCURSION_S and not (
            math.isclose(
                excursion["duration_s"],
                MAX_CONDITIONING_EXCURSION_S,
                rel_tol=0.0,
                abs_tol=1e-9,
            )
        )
        excursion["recoverable"] = not too_deep
        excursion["acceptable"] = not (too_long or too_deep)
        if too_deep:
            findings.append(
                "conditioning-window excursion of %.2f K exceeds the %.2f K "
                "allowance" % (excursion["depth_c"], MAX_EXCURSION_DEPTH_C)
            )
        if too_long:
            findings.append(
                "conditioning-window excursion lasting %.1f s exceeds the %.1f s "
                "allowance; extend the soak and re-condition"
                % (excursion["duration_s"], MAX_CONDITIONING_EXCURSION_S)
            )

    humidity_needed = humidity_control_required(
        spec["material_family"], spec["test_type"]
    )
    humidity_excursions = []
    if humidity_needed:
        humidity_band = _band(
            spec.get("humidity_band_pct", CONTROLLED_HUMIDITY_BAND_PCT),
            "humidity_band_pct",
        )
        if not any("humidity_pct" in sample for sample in samples):
            findings.append(
                "this material and test type owe a controlled relative humidity, "
                "but the log records none"
            )
        else:
            humidity_excursions = band_excursions(samples, humidity_band, "humidity_pct")
            for excursion in humidity_excursions:
                findings.append(
                    "relative humidity outside its band for %.1f s in the %s window"
                    % (excursion["duration_s"], excursion["window"])
                )

    condensation = None
    piece_temperature = spec.get("piece_temperature_c")
    if piece_temperature is not None:
        humid_samples = [s for s in samples if "humidity_pct" in s]
        if humid_samples:
            worst = max(humid_samples, key=lambda s: s["humidity_pct"])
            condensation = condensation_risk(
                piece_temperature, worst["temperature_c"], worst["humidity_pct"]
            )
            if condensation["risk"]:
                findings.append(
                    "test piece at %.2f degC sits at or below the %.2f degC dew "
                    "point; condensation stops the run whatever the humidity "
                    "reading says"
                    % (condensation["piece_temperature_c"], condensation["dew_point_c"])
                )

    owed = conditioning_minutes(spec["section_mm"])
    held = _real(spec["soak_minutes"], "soak_minutes")
    if held < 0.0:
        raise ValueError("soak_minutes must not be negative")
    soak_ok = held > owed or math.isclose(held, owed, rel_tol=0.0, abs_tol=1e-9)
    if not soak_ok:
        findings.append(
            "conditioning held for %.1f min against the %.1f min the %.1f mm section "
            "owes; the piece is loaded with a gradient"
            % (held, owed, float(spec["section_mm"]))
        )

    atmosphere = required_atmosphere(spec["material_family"], spec["test_temperature_c"])
    declared = spec.get("atmosphere")
    if declared is not None:
        declared_token = _token(declared, "atmosphere")
        if atmosphere["atmosphere"] == "inert-or-vacuum" and declared_token not in (
            "inert",
            "argon",
            "nitrogen",
            "vacuum",
            "inert-or-vacuum",
        ):
            findings.append(
                "declared atmosphere %r does not meet the requirement: %s"
                % (declared_token, atmosphere["reason"])
            )

    return {
        "samples": samples,
        "temperature_band_c": temperature_band,
        "temperature_excursions": temperature_excursions,
        "humidity_control_required": humidity_needed,
        "humidity_excursions": humidity_excursions,
        "condensation": condensation,
        "conditioning_minutes_owed": owed,
        "conditioning_minutes_held": held,
        "required_atmosphere": atmosphere,
        "acceptable": not findings,
        "status": "environment-acceptable" if not findings else "environment-finding",
        "findings": findings,
    }
