"""Venting of closed cavities in a mechanism.

Anchor: ECSS-E-ST-33-01C clause 4.7.5.4.11 (every closed cavity vented so no
damaging pressure differential builds up during ascent, and so the vent path
does not itself become a contamination trap). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Enumerate the closed cavities of the mechanism; a cavity with no vent at
   all is the first finding, not a zero-area calculation.
2. Turn each vent hole set into an effective flow area: the geometric area of
   the holes reduced by the discharge coefficient and again by the length-to-
   diameter loss of a deep vent channel.
3. Form the choked-flow venting time constant tau = V / (A_eff * c*), where c*
   is the critical discharge velocity of the vented gas at its temperature.
4. Multiply that time constant by the peak ascent depressurization rate to get
   the quasi-steady pressure the cavity lags behind ambient by, and compare it
   with the differential pressure the cavity structure allows.
5. Apply the heritage vent-area-to-volume screen as an independent check, so a
   cavity that passes on a favourable rate assumption is still caught.
6. Screen the vent path for contamination: a hole small enough to block, a
   blind pocket with no through path, and a vent discharging at a sensitive
   surface are each reported.
"""

import math

__all__ = [
    "GAMMA_AIR",
    "R_SPECIFIC_AIR",
    "DEFAULT_GAS_TEMPERATURE_K",
    "DEFAULT_DISCHARGE_COEFFICIENT",
    "CHANNEL_LOSS_FACTOR",
    "MIN_VENT_AREA_PER_LITRE_MM2",
    "MIN_VENT_DIAMETER_MM",
    "PRESSURE_TOLERANCE_PA",
    "validate_positive",
    "critical_discharge_velocity_m_s",
    "geometric_vent_area_mm2",
    "effective_vent_area_mm2",
    "venting_time_constant_s",
    "peak_differential_pressure_pa",
    "vent_area_per_litre_mm2",
    "contamination_findings",
    "assess_cavity",
    "assess_venting",
]

# Vented gas properties: ratio of specific heats and specific gas constant.
GAMMA_AIR = 1.4
R_SPECIFIC_AIR = 287.05

# Gas temperature assumed when the cavity does not declare one, in kelvin.
DEFAULT_GAS_TEMPERATURE_K = 293.15

# Discharge coefficient of a plain drilled vent hole.
DEFAULT_DISCHARGE_COEFFICIENT = 0.62

# Deep-channel loss: a vent through thick wall loses area as length over
# diameter grows.
CHANNEL_LOSS_FACTOR = 0.5

# Heritage screen: vent area per litre of cavity volume, in square
# millimetres, equivalent to one square inch per thousand cubic inches.
MIN_VENT_AREA_PER_LITRE_MM2 = 39.37

# A vent smaller than this blocks on handling debris or on a witness fibre.
MIN_VENT_DIAMETER_MM = 1.0

# Pressure comparisons pass through square roots and powers; absorb the
# representation error rather than relaxing the allowable.
PRESSURE_TOLERANCE_PA = 1e-6


def validate_positive(label, value, allow_zero=False):
    """Return value as a finite positive (or non-negative) float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if v < 0.0:
            raise ValueError("%s must be non-negative, got %g" % (label, v))
    elif v <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, v))
    return v


def critical_discharge_velocity_m_s(temperature_k=DEFAULT_GAS_TEMPERATURE_K,
                                    gamma=GAMMA_AIR, gas_constant=R_SPECIFIC_AIR):
    """Choked-flow discharge velocity of the vented gas, in metres per second."""
    temperature = validate_positive("temperature_k", temperature_k)
    g = validate_positive("gamma", gamma)
    if g <= 1.0:
        raise ValueError("gamma must exceed 1, got %g" % g)
    r = validate_positive("gas_constant", gas_constant)
    sonic = math.sqrt(g * r * temperature)
    exponent = (g + 1.0) / (2.0 * (g - 1.0))
    return sonic * (2.0 / (g + 1.0)) ** exponent


def geometric_vent_area_mm2(diameter_mm, count):
    """Total geometric area of a vent hole set, in square millimetres."""
    diameter = validate_positive("diameter_mm", diameter_mm)
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("count must be an integer, got %r" % (count,))
    if count < 0:
        raise ValueError("count must be non-negative, got %d" % count)
    return count * math.pi * 0.25 * diameter * diameter


def effective_vent_area_mm2(diameter_mm, count, length_mm=0.0,
                            discharge_coefficient=DEFAULT_DISCHARGE_COEFFICIENT):
    """Flow-effective vent area after discharge and channel losses."""
    geometric = geometric_vent_area_mm2(diameter_mm, count)
    cd = validate_positive("discharge_coefficient", discharge_coefficient)
    if cd > 1.0:
        raise ValueError("discharge_coefficient must not exceed 1, got %g" % cd)
    length = validate_positive("length_mm", length_mm, allow_zero=True)
    diameter = float(diameter_mm)
    channel = math.sqrt(1.0 + CHANNEL_LOSS_FACTOR * length / diameter)
    return geometric * cd / channel


def venting_time_constant_s(volume_litre, effective_area_mm2,
                            temperature_k=DEFAULT_GAS_TEMPERATURE_K):
    """Choked-flow venting time constant of the cavity, in seconds."""
    volume = validate_positive("volume_litre", volume_litre)
    area = validate_positive("effective_area_mm2", effective_area_mm2)
    velocity = critical_discharge_velocity_m_s(temperature_k)
    volume_m3 = volume * 1.0e-3
    area_m2 = area * 1.0e-6
    return volume_m3 / (area_m2 * velocity)


def peak_differential_pressure_pa(time_constant_s, depressurization_rate_pa_per_s):
    """Quasi-steady pressure the cavity lags ambient by, in pascals."""
    tau = validate_positive("time_constant_s", time_constant_s)
    rate = validate_positive(
        "depressurization_rate_pa_per_s", depressurization_rate_pa_per_s
    )
    return tau * rate


def vent_area_per_litre_mm2(effective_area_mm2, volume_litre):
    """Effective vent area per litre of cavity volume."""
    area = validate_positive("effective_area_mm2", effective_area_mm2)
    volume = validate_positive("volume_litre", volume_litre)
    return area / volume


def contamination_findings(name, diameter_mm, blind_pocket=False,
                           discharges_at_sensitive_surface=False, screened=False):
    """Return the contamination-trap findings for one vent path."""
    diameter = validate_positive("diameter_mm", diameter_mm)
    findings = []
    if diameter < MIN_VENT_DIAMETER_MM and not math.isclose(
        diameter, MIN_VENT_DIAMETER_MM, rel_tol=0.0, abs_tol=1e-12
    ):
        findings.append(
            "cavity '%s' vents through %.2f mm holes, below the %.2f mm that "
            "resists blockage" % (name, diameter, MIN_VENT_DIAMETER_MM)
        )
    if blind_pocket:
        findings.append(
            "cavity '%s' is a blind pocket: the vent has no through path and traps "
            "cleaning fluid and particulate" % name
        )
    if discharges_at_sensitive_surface and not screened:
        findings.append(
            "cavity '%s' discharges at a sensitive surface with no screen on the "
            "vent path" % name
        )
    return findings


def assess_cavity(record):
    """Assess the venting of one closed cavity and return its record.

    record keys: name, volume_litre, vent_diameter_mm, vent_count,
    allowable_differential_pa, depressurization_rate_pa_per_s; optional
    vent_length_mm, discharge_coefficient, temperature_k, blind_pocket,
    discharges_at_sensitive_surface, screened.
    """
    if not isinstance(record, dict):
        raise ValueError("cavity record must be a mapping")
    required = (
        "name", "volume_litre", "vent_diameter_mm", "vent_count",
        "allowable_differential_pa", "depressurization_rate_pa_per_s",
    )
    for key in required:
        if key not in record:
            raise ValueError("cavity record missing required key '%s'" % key)
    name = record["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("cavity name must be a non-empty string")
    count = record["vent_count"]
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("vent_count must be an integer, got %r" % (count,))
    if count < 0:
        raise ValueError("vent_count must be non-negative, got %d" % count)
    volume = validate_positive("volume_litre", record["volume_litre"])
    allowable = validate_positive(
        "allowable_differential_pa", record["allowable_differential_pa"]
    )

    if count == 0:
        return {
            "name": name,
            "vented": False,
            "effective_area_mm2": 0.0,
            "area_per_litre_mm2": 0.0,
            "time_constant_s": None,
            "peak_differential_pa": None,
            "allowable_differential_pa": allowable,
            "compliant": False,
            "findings": [
                "cavity '%s' of %.3f litre is closed and unvented" % (name, volume)
            ],
        }

    temperature = record.get("temperature_k", DEFAULT_GAS_TEMPERATURE_K)
    area = effective_vent_area_mm2(
        record["vent_diameter_mm"], count, record.get("vent_length_mm", 0.0),
        record.get("discharge_coefficient", DEFAULT_DISCHARGE_COEFFICIENT),
    )
    tau = venting_time_constant_s(volume, area, temperature)
    peak = peak_differential_pressure_pa(
        tau, record["depressurization_rate_pa_per_s"]
    )
    per_litre = vent_area_per_litre_mm2(area, volume)

    findings = []
    pressure_ok = peak < allowable or math.isclose(
        peak, allowable, rel_tol=0.0, abs_tol=PRESSURE_TOLERANCE_PA
    )
    if not pressure_ok:
        findings.append(
            "cavity '%s' lags ambient by %.1f Pa against an allowable %.1f Pa"
            % (name, peak, allowable)
        )
    area_ok = per_litre > MIN_VENT_AREA_PER_LITRE_MM2 or math.isclose(
        per_litre, MIN_VENT_AREA_PER_LITRE_MM2, rel_tol=0.0, abs_tol=1e-9
    )
    if not area_ok:
        findings.append(
            "cavity '%s' vents %.2f mm2 per litre, below the %.2f mm2 per litre screen"
            % (name, per_litre, MIN_VENT_AREA_PER_LITRE_MM2)
        )
    trap_findings = contamination_findings(
        name, record["vent_diameter_mm"], record.get("blind_pocket", False),
        record.get("discharges_at_sensitive_surface", False),
        record.get("screened", False),
    )
    findings.extend(trap_findings)

    return {
        "name": name,
        "vented": True,
        "effective_area_mm2": area,
        "area_per_litre_mm2": per_litre,
        "time_constant_s": tau,
        "peak_differential_pa": peak,
        "allowable_differential_pa": allowable,
        "compliant": pressure_ok and area_ok and not trap_findings,
        "findings": findings,
    }


def assess_venting(spec):
    """Run the full clause 4.7.5.4.11 venting assessment.

    spec keys: cavities (a non-empty sequence of cavity records).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "cavities" not in spec:
        raise ValueError("spec missing required key 'cavities'")
    cavities = spec["cavities"]
    if not isinstance(cavities, (list, tuple)) or not cavities:
        raise ValueError("cavities must be a non-empty sequence of records")

    results = []
    seen = set()
    findings = []
    for record in cavities:
        assessed = assess_cavity(record)
        key = assessed["name"].strip().lower()
        if key in seen:
            raise ValueError("duplicate cavity name %r" % assessed["name"])
        seen.add(key)
        results.append(assessed)
        findings.extend(assessed["findings"])

    vented = [item for item in results if item["vented"]]
    governing = None
    if vented:
        governing = max(vented, key=lambda r: r["peak_differential_pa"])
    return {
        "cavities": results,
        "cavity_count": len(results),
        "unvented_count": len(results) - len(vented),
        "governing_cavity": governing["name"] if governing else None,
        "governing_differential_pa": (
            governing["peak_differential_pa"] if governing else None
        ),
        "compliant": all(item["compliant"] for item in results),
        "findings": findings,
    }
