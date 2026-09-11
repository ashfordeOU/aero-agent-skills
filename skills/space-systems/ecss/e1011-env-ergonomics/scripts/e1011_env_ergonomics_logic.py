"""
Environmental ergonomics logic for ECSS-E-ST-10-11 §4.6.5.

Covers six domains: noise, vibration, lighting, atmosphere, temperature,
and EVA suit internal atmosphere.  All functions are deterministic and
offline; stdlib only.

Reference: ECSS-E-ST-10-11C (Human factors engineering for space systems),
clause 4.6.5 — Environmental ergonomics.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Constants — derived from ECSS-E-ST-10-11 §4.6.5 limits (paraphrased)
# ---------------------------------------------------------------------------

# Noise (dB(A))
NOISE_LIMIT_HABITABLE_DBA = 55.0    # continuous, inhabited operational area
NOISE_LIMIT_SLEEP_DBA = 50.0        # sleep/rest quarters
NOISE_LIMIT_INTERMITTENT_DBA = 85.0 # short-term intermittent (< 15 min/day)
NOISE_LIMIT_ALARM_MARGIN_DB = 10.0  # alarm must exceed background by at least this

VALID_EXPOSURE_TYPES = {"continuous", "sleep", "intermittent"}

# Vibration — whole-body (ISO 2631-1 / ECSS reference, m/s² frequency-weighted RMS)
VIBRATION_LIMIT_8H_MS2 = 0.5        # 8-hour action value (m/s²)
VIBRATION_LIMIT_SHORT_MS2 = 1.0     # limit for exposures < 1 h

VALID_VIBRATION_AXES = {"x", "y", "z"}

# Lighting (lux)
LIGHTING_MIN_TASK_LUX = 300         # minimum for visual task areas
LIGHTING_MAX_TASK_LUX = 500         # upper recommendation for task areas
LIGHTING_MIN_GENERAL_LUX = 100      # general habitable zone
LIGHTING_MIN_EMERGENCY_LUX = 10     # emergency / minimal lighting
LIGHTING_MIN_SLEEP_LUX = 0          # sleep area minimum
LIGHTING_MAX_SLEEP_LUX = 50         # sleep area maximum (adjustable to darkness)

VALID_AREA_TYPES = {"task", "general", "emergency", "sleep"}

# Atmosphere (kPa)
ATMO_TOTAL_PRESSURE_MIN_KPA = 70.3   # minimum habitable total pressure
ATMO_TOTAL_PRESSURE_MAX_KPA = 101.3  # sea-level nominal
ATMO_PO2_MIN_KPA = 19.5              # minimum O₂ partial pressure
ATMO_PO2_MAX_KPA = 23.1              # maximum O₂ partial pressure (fire-risk ceiling)
ATMO_PCO2_MAX_KPA = 0.70             # continuous CO₂ partial pressure limit
ATMO_HUMIDITY_MIN_PCT = 25.0         # minimum relative humidity
ATMO_HUMIDITY_MAX_PCT = 75.0         # maximum relative humidity

# Temperature (°C / m/s)
TEMP_OPERATIVE_MIN_C = 18.0          # minimum operative temperature (activity)
TEMP_OPERATIVE_MAX_C = 26.0          # maximum operative temperature
TEMP_RADIANT_ASYMMETRY_MAX_C = 10.0  # maximum warm/cool surface delta
TEMP_AIR_VELOCITY_MAX_MS = 0.20      # maximum air speed for thermal comfort

# EVA suit atmosphere
EVA_SUIT_PRESSURE_MIN_KPA = 25.0     # minimum suit operating pressure (pure-O₂ suits)
EVA_SUIT_PRESSURE_MAX_KPA = 101.3    # maximum suit pressure
EVA_SUIT_O2_FRACTION_MIN = 0.21      # minimum O₂ mole fraction in suit
EVA_SUIT_PCO2_MAX_KPA = 1.0          # maximum suit CO₂ partial pressure


# ---------------------------------------------------------------------------
# Domain check functions
# ---------------------------------------------------------------------------

def check_noise(spl_db_a: float, exposure_type: str) -> dict:
    """
    Evaluate a noise level against the ECSS-E-ST-10-11 §4.6.5 sound-pressure
    limit for the given exposure type.

    Parameters
    ----------
    spl_db_a : float
        A-weighted sound pressure level in dB(A).
    exposure_type : str
        One of "continuous", "sleep", or "intermittent".

    Returns
    -------
    dict with keys:
        compliant (bool)  — True when no finding is raised.
        findings  (list)  — Human-readable finding strings (empty when compliant).
    """
    if not isinstance(spl_db_a, (int, float)):
        raise TypeError("spl_db_a must be a numeric value (dB(A))")
    if exposure_type not in VALID_EXPOSURE_TYPES:
        raise ValueError(
            f"exposure_type '{exposure_type}' not in {VALID_EXPOSURE_TYPES}"
        )

    findings = []
    limits = {
        "continuous": NOISE_LIMIT_HABITABLE_DBA,
        "sleep": NOISE_LIMIT_SLEEP_DBA,
        "intermittent": NOISE_LIMIT_INTERMITTENT_DBA,
    }
    limit = limits[exposure_type]

    if spl_db_a > limit:
        findings.append(
            f"Noise {spl_db_a:.1f} dB(A) exceeds {exposure_type} limit "
            f"{limit:.1f} dB(A) by {spl_db_a - limit:.1f} dB."
        )

    return {"compliant": len(findings) == 0, "findings": findings}


def check_alarm_audibility(alarm_spl_db_a: float, background_spl_db_a: float) -> dict:
    """
    Verify that a warning alarm is audible above the background noise level.

    The alarm SPL must exceed the background level by at least
    NOISE_LIMIT_ALARM_MARGIN_DB (10 dB).
    """
    if not isinstance(alarm_spl_db_a, (int, float)):
        raise TypeError("alarm_spl_db_a must be numeric")
    if not isinstance(background_spl_db_a, (int, float)):
        raise TypeError("background_spl_db_a must be numeric")

    findings = []
    margin = alarm_spl_db_a - background_spl_db_a
    if margin < NOISE_LIMIT_ALARM_MARGIN_DB:
        findings.append(
            f"Alarm margin {margin:.1f} dB is below the required "
            f"{NOISE_LIMIT_ALARM_MARGIN_DB:.0f} dB minimum above background."
        )
    return {"compliant": len(findings) == 0, "findings": findings}


def check_vibration(rms_ms2: float, duration_h: float, axis: str = "z") -> dict:
    """
    Check whole-body vibration exposure against ECSS-E-ST-10-11 §4.6.5
    (ISO 2631-1 basis).

    Parameters
    ----------
    rms_ms2    : frequency-weighted RMS acceleration (m/s²).
    duration_h : daily exposure duration (hours, 0 < duration_h ≤ 24).
    axis       : vibration axis — "x", "y", or "z".

    The 8-hour reference value is 0.5 m/s².  For durations shorter than
    1 h the upper limit rises to 1.0 m/s²; for ≥ 1 h the 8-h limit applies.
    """
    if not isinstance(rms_ms2, (int, float)) or rms_ms2 < 0:
        raise ValueError("rms_ms2 must be a non-negative number")
    if not isinstance(duration_h, (int, float)) or not (0 < duration_h <= 24):
        raise ValueError("duration_h must be in (0, 24]")
    if axis not in VALID_VIBRATION_AXES:
        raise ValueError(f"axis '{axis}' not in {VALID_VIBRATION_AXES}")

    findings = []
    limit = VIBRATION_LIMIT_SHORT_MS2 if duration_h < 1.0 else VIBRATION_LIMIT_8H_MS2

    if rms_ms2 > limit:
        findings.append(
            f"Vibration {rms_ms2:.3f} m/s² (axis {axis.upper()}, "
            f"{duration_h:.1f} h/day) exceeds limit {limit:.3f} m/s²."
        )

    return {"compliant": len(findings) == 0, "findings": findings}


def check_lighting(illuminance_lux: float, area_type: str) -> dict:
    """
    Check illuminance level against the operational area requirement.

    Parameters
    ----------
    illuminance_lux : measured or designed illuminance (lux, ≥ 0).
    area_type       : one of "task", "general", "emergency", "sleep".
    """
    if not isinstance(illuminance_lux, (int, float)) or illuminance_lux < 0:
        raise ValueError("illuminance_lux must be a non-negative number")
    if area_type not in VALID_AREA_TYPES:
        raise ValueError(f"area_type '{area_type}' not in {VALID_AREA_TYPES}")

    findings = []

    if area_type == "task":
        if illuminance_lux < LIGHTING_MIN_TASK_LUX:
            findings.append(
                f"Task-area illuminance {illuminance_lux:.0f} lux is below "
                f"minimum {LIGHTING_MIN_TASK_LUX:.0f} lux."
            )
        elif illuminance_lux > LIGHTING_MAX_TASK_LUX:
            findings.append(
                f"Task-area illuminance {illuminance_lux:.0f} lux exceeds "
                f"recommended maximum {LIGHTING_MAX_TASK_LUX:.0f} lux."
            )
    elif area_type == "general":
        if illuminance_lux < LIGHTING_MIN_GENERAL_LUX:
            findings.append(
                f"General-area illuminance {illuminance_lux:.0f} lux is below "
                f"minimum {LIGHTING_MIN_GENERAL_LUX:.0f} lux."
            )
    elif area_type == "emergency":
        if illuminance_lux < LIGHTING_MIN_EMERGENCY_LUX:
            findings.append(
                f"Emergency illuminance {illuminance_lux:.0f} lux is below "
                f"minimum {LIGHTING_MIN_EMERGENCY_LUX:.0f} lux."
            )
    elif area_type == "sleep":
        if illuminance_lux > LIGHTING_MAX_SLEEP_LUX:
            findings.append(
                f"Sleep-area illuminance {illuminance_lux:.0f} lux exceeds "
                f"maximum {LIGHTING_MAX_SLEEP_LUX:.0f} lux."
            )

    return {"compliant": len(findings) == 0, "findings": findings}


def check_atmosphere(
    total_pressure_kpa: float,
    o2_partial_kpa: float,
    co2_partial_kpa: float,
    humidity_pct: float,
) -> dict:
    """
    Evaluate the habitable-volume atmosphere against ECSS-E-ST-10-11 §4.6.5
    atmospheric ergonomics limits.

    Parameters
    ----------
    total_pressure_kpa : total cabin pressure (kPa).
    o2_partial_kpa     : oxygen partial pressure (kPa).
    co2_partial_kpa    : carbon-dioxide partial pressure (kPa).
    humidity_pct       : relative humidity (%).
    """
    for name, val in [
        ("total_pressure_kpa", total_pressure_kpa),
        ("o2_partial_kpa", o2_partial_kpa),
        ("co2_partial_kpa", co2_partial_kpa),
        ("humidity_pct", humidity_pct),
    ]:
        if not isinstance(val, (int, float)) or val < 0:
            raise ValueError(f"{name} must be a non-negative number")

    findings = []

    if total_pressure_kpa < ATMO_TOTAL_PRESSURE_MIN_KPA:
        findings.append(
            f"Total pressure {total_pressure_kpa:.1f} kPa below minimum "
            f"{ATMO_TOTAL_PRESSURE_MIN_KPA:.1f} kPa."
        )
    if total_pressure_kpa > ATMO_TOTAL_PRESSURE_MAX_KPA:
        findings.append(
            f"Total pressure {total_pressure_kpa:.1f} kPa exceeds maximum "
            f"{ATMO_TOTAL_PRESSURE_MAX_KPA:.1f} kPa."
        )

    if o2_partial_kpa < ATMO_PO2_MIN_KPA:
        findings.append(
            f"O₂ partial pressure {o2_partial_kpa:.2f} kPa below minimum "
            f"{ATMO_PO2_MIN_KPA:.1f} kPa (hypoxia risk)."
        )
    if o2_partial_kpa > ATMO_PO2_MAX_KPA:
        findings.append(
            f"O₂ partial pressure {o2_partial_kpa:.2f} kPa exceeds maximum "
            f"{ATMO_PO2_MAX_KPA:.1f} kPa (elevated fire risk)."
        )

    if co2_partial_kpa > ATMO_PCO2_MAX_KPA:
        findings.append(
            f"CO₂ partial pressure {co2_partial_kpa:.3f} kPa exceeds continuous "
            f"limit {ATMO_PCO2_MAX_KPA:.2f} kPa."
        )

    if humidity_pct < ATMO_HUMIDITY_MIN_PCT:
        findings.append(
            f"Relative humidity {humidity_pct:.1f}% below minimum "
            f"{ATMO_HUMIDITY_MIN_PCT:.0f}%."
        )
    if humidity_pct > ATMO_HUMIDITY_MAX_PCT:
        findings.append(
            f"Relative humidity {humidity_pct:.1f}% exceeds maximum "
            f"{ATMO_HUMIDITY_MAX_PCT:.0f}%."
        )

    return {"compliant": len(findings) == 0, "findings": findings}


def check_temperature(
    operative_temp_c: float,
    radiant_asymmetry_delta_c: float,
    air_velocity_ms: float,
) -> dict:
    """
    Check habitat thermal environment against ECSS-E-ST-10-11 §4.6.5 limits.

    Parameters
    ----------
    operative_temp_c         : operative temperature — combined dry-bulb and
                               mean radiant, °C.
    radiant_asymmetry_delta_c: temperature difference between the warmest and
                               coolest radiant surface visible to the occupant
                               (°C, ≥ 0).
    air_velocity_ms          : mean air velocity at occupant location (m/s, ≥ 0).
    """
    for name, val in [
        ("operative_temp_c", operative_temp_c),
        ("radiant_asymmetry_delta_c", radiant_asymmetry_delta_c),
        ("air_velocity_ms", air_velocity_ms),
    ]:
        if not isinstance(val, (int, float)):
            raise TypeError(f"{name} must be numeric")
    if radiant_asymmetry_delta_c < 0:
        raise ValueError("radiant_asymmetry_delta_c must be ≥ 0")
    if air_velocity_ms < 0:
        raise ValueError("air_velocity_ms must be ≥ 0")

    findings = []

    if operative_temp_c < TEMP_OPERATIVE_MIN_C:
        findings.append(
            f"Operative temperature {operative_temp_c:.1f} °C below minimum "
            f"{TEMP_OPERATIVE_MIN_C:.0f} °C."
        )
    if operative_temp_c > TEMP_OPERATIVE_MAX_C:
        findings.append(
            f"Operative temperature {operative_temp_c:.1f} °C exceeds maximum "
            f"{TEMP_OPERATIVE_MAX_C:.0f} °C."
        )

    if radiant_asymmetry_delta_c > TEMP_RADIANT_ASYMMETRY_MAX_C:
        findings.append(
            f"Radiant asymmetry {radiant_asymmetry_delta_c:.1f} °C exceeds "
            f"maximum {TEMP_RADIANT_ASYMMETRY_MAX_C:.0f} °C."
        )

    if air_velocity_ms > TEMP_AIR_VELOCITY_MAX_MS:
        findings.append(
            f"Air velocity {air_velocity_ms:.2f} m/s exceeds comfort limit "
            f"{TEMP_AIR_VELOCITY_MAX_MS:.2f} m/s."
        )

    return {"compliant": len(findings) == 0, "findings": findings}


def check_eva_suit(
    suit_pressure_kpa: float,
    o2_fraction: float,
    co2_partial_kpa: float,
) -> dict:
    """
    Audit the internal atmosphere of an EVA suit against ECSS-E-ST-10-11
    §4.6.5 EVA suit environment limits.

    Parameters
    ----------
    suit_pressure_kpa : suit total internal pressure (kPa).
    o2_fraction       : oxygen mole fraction in the suit (0 to 1).
    co2_partial_kpa   : CO₂ partial pressure in the suit (kPa).
    """
    if not isinstance(suit_pressure_kpa, (int, float)) or suit_pressure_kpa < 0:
        raise ValueError("suit_pressure_kpa must be a non-negative number")
    if not isinstance(o2_fraction, (int, float)) or not (0.0 <= o2_fraction <= 1.0):
        raise ValueError("o2_fraction must be in [0, 1]")
    if not isinstance(co2_partial_kpa, (int, float)) or co2_partial_kpa < 0:
        raise ValueError("co2_partial_kpa must be a non-negative number")

    findings = []

    if suit_pressure_kpa < EVA_SUIT_PRESSURE_MIN_KPA:
        findings.append(
            f"Suit pressure {suit_pressure_kpa:.1f} kPa below minimum "
            f"{EVA_SUIT_PRESSURE_MIN_KPA:.1f} kPa."
        )
    if suit_pressure_kpa > EVA_SUIT_PRESSURE_MAX_KPA:
        findings.append(
            f"Suit pressure {suit_pressure_kpa:.1f} kPa exceeds maximum "
            f"{EVA_SUIT_PRESSURE_MAX_KPA:.1f} kPa."
        )

    o2_partial_kpa = o2_fraction * suit_pressure_kpa
    if o2_fraction < EVA_SUIT_O2_FRACTION_MIN:
        findings.append(
            f"Suit O₂ fraction {o2_fraction:.3f} (pO₂ = {o2_partial_kpa:.2f} kPa) "
            f"below minimum fraction {EVA_SUIT_O2_FRACTION_MIN:.2f}."
        )

    if co2_partial_kpa > EVA_SUIT_PCO2_MAX_KPA:
        findings.append(
            f"Suit CO₂ partial pressure {co2_partial_kpa:.3f} kPa exceeds "
            f"maximum {EVA_SUIT_PCO2_MAX_KPA:.1f} kPa."
        )

    return {"compliant": len(findings) == 0, "findings": findings}


def assess_habitat(
    noise_spl_db_a: float,
    noise_exposure_type: str,
    vibration_rms_ms2: float,
    vibration_duration_h: float,
    lighting_lux: float,
    lighting_area_type: str,
    total_pressure_kpa: float,
    o2_partial_kpa: float,
    co2_partial_kpa: float,
    humidity_pct: float,
    operative_temp_c: float,
    radiant_asymmetry_delta_c: float,
    air_velocity_ms: float,
) -> dict:
    """
    Aggregate environmental ergonomics assessment for a crewed habitat station.

    Runs all six domain checks and returns a top-level compliance verdict
    plus per-domain findings.  The habitat is ergonomics-compliant only when
    every domain returns compliant=True.
    """
    noise_result = check_noise(noise_spl_db_a, noise_exposure_type)
    vibration_result = check_vibration(vibration_rms_ms2, vibration_duration_h)
    lighting_result = check_lighting(lighting_lux, lighting_area_type)
    atmo_result = check_atmosphere(
        total_pressure_kpa, o2_partial_kpa, co2_partial_kpa, humidity_pct
    )
    temp_result = check_temperature(
        operative_temp_c, radiant_asymmetry_delta_c, air_velocity_ms
    )

    domain_results = {
        "noise": noise_result,
        "vibration": vibration_result,
        "lighting": lighting_result,
        "atmosphere": atmo_result,
        "temperature": temp_result,
    }

    overall_compliant = all(r["compliant"] for r in domain_results.values())
    return {
        "compliant": overall_compliant,
        "domain_results": domain_results,
    }
