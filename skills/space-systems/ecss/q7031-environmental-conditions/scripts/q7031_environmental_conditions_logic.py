"""Application-environment control for paint and coating application.

Anchor: ECSS-Q-ST-70-31C, Application. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the measured booth air temperature, the substrate temperature and
   the relative humidity of the application area.
2. Grade air temperature and relative humidity against the application window
   the paint system's process document declares, absorbing representation
   error at the band edges with a named tolerance.
3. Derive the dew point of the booth air from the Magnus relation and form the
   substrate dew-point margin: substrate temperature minus dew point. A
   substrate at or below the dew point carries a condensed water film that no
   downstream cleanliness or adhesion step can recover.
4. Convert an airborne-cleanliness requirement expressed as an ISO 14644-1
   class into a per-size concentration limit and grade the measured counts
   against it, size by size.
5. Report the verdict with every finding named, so an out-of-window run is
   stopped before the gun is triggered rather than dispositioned afterwards.
"""

import math

__all__ = [
    "BAND_TOLERANCE",
    "MAGNUS_A",
    "MAGNUS_B",
    "MIN_PLAUSIBLE_TEMP_C",
    "MAX_PLAUSIBLE_TEMP_C",
    "validate_temperature_c",
    "validate_relative_humidity",
    "validate_band",
    "within_band",
    "dew_point_c",
    "dew_point_margin_c",
    "iso14644_limit_per_m3",
    "assess_cleanliness",
    "assess_application_environment",
]

# Band comparisons are differences of floats that a calibrated instrument can
# report exactly on the limit. Absorb the representation error here rather than
# by widening the declared process window.
BAND_TOLERANCE = 1e-9

# Magnus coefficients for water over a liquid surface in the booth range.
MAGNUS_A = 17.62
MAGNUS_B = 243.12

MIN_PLAUSIBLE_TEMP_C = -80.0
MAX_PLAUSIBLE_TEMP_C = 250.0

# ISO 14644-1 concentration exponent on the particle-size ratio.
_SIZE_EXPONENT = 2.08
_REFERENCE_SIZE_UM = 0.1


def _real(value, label):
    """Return value as a finite float, or raise on anything that is not one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_temperature_c(value, label="temperature_c"):
    """Return a validated temperature in degrees Celsius."""
    out = _real(value, label)
    if out < MIN_PLAUSIBLE_TEMP_C or out > MAX_PLAUSIBLE_TEMP_C:
        raise ValueError(
            "%s %g degC is outside the plausible application range [%g, %g]"
            % (label, out, MIN_PLAUSIBLE_TEMP_C, MAX_PLAUSIBLE_TEMP_C)
        )
    return out


def validate_relative_humidity(value, label="relative_humidity_pct"):
    """Return a validated relative humidity in percent."""
    out = _real(value, label)
    if out < 0.0 or out > 100.0:
        raise ValueError("%s must lie in [0, 100] percent, got %g" % (label, out))
    return out


def validate_band(band, label="band"):
    """Return a validated (low, high) numeric band."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _real(band[0], "%s low" % label)
    high = _real(band[1], "%s high" % label)
    if low > high:
        raise ValueError("%s low %g exceeds high %g" % (label, low, high))
    return (low, high)


def within_band(value, band, tolerance=BAND_TOLERANCE):
    """Return True when value sits inside the band, limits included."""
    low, high = validate_band(band)
    val = _real(value, "value")
    tol = _real(tolerance, "tolerance")
    if tol < 0.0:
        raise ValueError("tolerance must be non-negative, got %g" % tol)
    return (val >= low - tol) and (val <= high + tol)


def dew_point_c(air_temperature_c, relative_humidity_pct):
    """Return the dew point of the booth air in degrees Celsius."""
    temp = validate_temperature_c(air_temperature_c, "air_temperature_c")
    rh = validate_relative_humidity(relative_humidity_pct)
    if rh <= 0.0:
        raise ValueError(
            "relative_humidity_pct must be positive to define a dew point, got %g" % rh
        )
    gamma = (MAGNUS_A * temp) / (MAGNUS_B + temp) + math.log(rh / 100.0)
    return (MAGNUS_B * gamma) / (MAGNUS_A - gamma)


def dew_point_margin_c(substrate_temperature_c, air_temperature_c, relative_humidity_pct):
    """Return substrate temperature minus dew point, in kelvin of margin."""
    substrate = validate_temperature_c(substrate_temperature_c, "substrate_temperature_c")
    return substrate - dew_point_c(air_temperature_c, relative_humidity_pct)


def iso14644_limit_per_m3(iso_class, particle_size_um):
    """Return the ISO 14644-1 concentration limit in particles per cubic metre."""
    cls = _real(iso_class, "iso_class")
    size = _real(particle_size_um, "particle_size_um")
    if cls < 1.0 or cls > 9.0:
        raise ValueError("iso_class must lie in [1, 9], got %g" % cls)
    if size <= 0.0:
        raise ValueError("particle_size_um must be positive, got %g" % size)
    return math.pow(10.0, cls) * math.pow(_REFERENCE_SIZE_UM / size, _SIZE_EXPONENT)


def assess_cleanliness(particle_counts, iso_class):
    """Grade measured airborne counts against an ISO 14644-1 class."""
    if not isinstance(particle_counts, dict) or not particle_counts:
        raise ValueError("particle_counts must be a non-empty mapping of size_um -> per m3")
    rows = []
    findings = []
    for raw_size in sorted(particle_counts, key=lambda k: _real(k, "particle size")):
        size = _real(raw_size, "particle size")
        measured = _real(particle_counts[raw_size], "count at %g um" % size)
        if measured < 0.0:
            raise ValueError("count at %g um must be non-negative, got %g" % (size, measured))
        limit = iso14644_limit_per_m3(iso_class, size)
        ok = measured <= limit * (1.0 + BAND_TOLERANCE)
        rows.append(
            {
                "particle_size_um": size,
                "measured_per_m3": measured,
                "limit_per_m3": limit,
                "within_limit": ok,
            }
        )
        if not ok:
            findings.append(
                "airborne count %g per m3 at %g um exceeds the ISO class %g limit %g"
                % (measured, size, _real(iso_class, "iso_class"), limit)
            )
    return {"rows": rows, "findings": findings, "within_limit": not findings}


def assess_application_environment(spec):
    """Run the full application-environment assessment for one spray run.

    spec keys: air_temperature_c, substrate_temperature_c, relative_humidity_pct,
    temperature_band, humidity_band, min_dew_point_margin_c, optional iso_class
    and particle_counts.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "air_temperature_c",
        "substrate_temperature_c",
        "relative_humidity_pct",
        "temperature_band",
        "humidity_band",
        "min_dew_point_margin_c",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    air = validate_temperature_c(spec["air_temperature_c"], "air_temperature_c")
    substrate = validate_temperature_c(spec["substrate_temperature_c"], "substrate_temperature_c")
    rh = validate_relative_humidity(spec["relative_humidity_pct"])
    temp_band = validate_band(spec["temperature_band"], "temperature_band")
    hum_band = validate_band(spec["humidity_band"], "humidity_band")
    min_margin = _real(spec["min_dew_point_margin_c"], "min_dew_point_margin_c")
    if min_margin < 0.0:
        raise ValueError("min_dew_point_margin_c must be non-negative, got %g" % min_margin)

    findings = []
    temp_ok = within_band(air, temp_band)
    if not temp_ok:
        findings.append(
            "booth air %g degC is outside the application window [%g, %g]"
            % (air, temp_band[0], temp_band[1])
        )
    hum_ok = within_band(rh, hum_band)
    if not hum_ok:
        findings.append(
            "relative humidity %g percent is outside the application window [%g, %g]"
            % (rh, hum_band[0], hum_band[1])
        )

    dew = dew_point_c(air, rh)
    margin = substrate - dew
    margin_ok = margin >= min_margin - BAND_TOLERANCE
    if not margin_ok:
        findings.append(
            "substrate dew-point margin %.3f K is below the required %.3f K"
            % (margin, min_margin)
        )

    cleanliness = None
    if "iso_class" in spec and spec.get("particle_counts"):
        cleanliness = assess_cleanliness(spec["particle_counts"], spec["iso_class"])
        findings.extend(cleanliness["findings"])

    return {
        "air_temperature_c": air,
        "substrate_temperature_c": substrate,
        "relative_humidity_pct": rh,
        "dew_point_c": dew,
        "dew_point_margin_c": margin,
        "temperature_within_band": temp_ok,
        "humidity_within_band": hum_ok,
        "dew_point_margin_met": margin_ok,
        "cleanliness": cleanliness,
        "findings": findings,
        "release_to_spray": not findings,
    }
