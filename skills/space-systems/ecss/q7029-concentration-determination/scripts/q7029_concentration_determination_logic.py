"""Offgassing concentration determination from chromatographic response.

Anchor: ECSS-Q-ST-70-29 analysis step -- converting the integrated response of
an identified offgassing product into a concentration normalised to the sample
mass and to the collection-vessel volume. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the run conditions (sample mass, vessel volume, recovery fraction).
2. Validate the per-compound calibration series and refuse extrapolation.
3. Subtract the blank area before the calibration is applied.
4. Interpolate the corrected area onto the bracketing calibration points.
5. Divide by the recovery fraction to obtain the released mass.
6. Tag the record quantified, below-quantitation or non-detected against the
   declared limits of quantitation and detection.
7. Normalise to micrograms per gram of sample and milligrams per cubic metre
   of vessel volume, and aggregate the released mass across compounds.
"""

import math

__all__ = [
    "MASS_TOLERANCE_UG",
    "AREA_TOLERANCE",
    "STATE_QUANTIFIED",
    "STATE_BELOW_QUANTITATION",
    "STATE_NON_DETECTED",
    "validate_run_conditions",
    "validate_calibration",
    "blank_corrected_area",
    "mass_from_area",
    "recovery_corrected_mass",
    "quantitation_state",
    "mass_per_gram",
    "mass_per_cubic_metre",
    "determine_compound",
    "determine_concentrations",
]

# Masses are built from an interpolation and a division; a value that should sit
# exactly on a reporting limit can land a few ULP either side of it. Absorb the
# representation error here instead of by moving the limit.
MASS_TOLERANCE_UG = 1e-9
AREA_TOLERANCE = 1e-12

STATE_QUANTIFIED = "quantified"
STATE_BELOW_QUANTITATION = "below-quantitation"
STATE_NON_DETECTED = "non-detected"


def _real(label, value):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _positive(label, value):
    v = _real(label, value)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def _non_negative(label, value):
    v = _real(label, value)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def validate_run_conditions(sample_mass_g, vessel_volume_m3, recovery_fraction,
                            duration_h=None):
    """Return the validated run conditions of the offgassing collection."""
    mass = _positive("sample_mass_g", sample_mass_g)
    volume = _positive("vessel_volume_m3", vessel_volume_m3)
    recovery = _real("recovery_fraction", recovery_fraction)
    if recovery <= 0.0 or recovery > 1.0:
        raise ValueError(
            "recovery_fraction must lie in (0, 1], got %r" % (recovery_fraction,)
        )
    conditions = {
        "sample_mass_g": mass,
        "vessel_volume_m3": volume,
        "recovery_fraction": recovery,
    }
    if duration_h is not None:
        conditions["duration_h"] = _positive("duration_h", duration_h)
    return conditions


def validate_calibration(points, name="calibration"):
    """Return calibration points as (area, mass_ug) pairs, strictly increasing."""
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("%s needs at least two (area, mass_ug) points" % name)
    out = []
    for i, item in enumerate(points):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be an (area, mass_ug) pair" % (name, i))
        area = _positive("%s[%d] area" % (name, i), item[0])
        mass = _positive("%s[%d] mass_ug" % (name, i), item[1])
        out.append((area, mass))
    for i in range(1, len(out)):
        if out[i][0] <= out[i - 1][0]:
            raise ValueError("%s areas must strictly increase (index %d)" % (name, i))
        if out[i][1] <= out[i - 1][1]:
            raise ValueError("%s masses must strictly increase (index %d)" % (name, i))
    return out


def blank_corrected_area(sample_area, blank_area):
    """Return the blank-corrected area, clamped at zero for a non-detection."""
    sample = _non_negative("sample_area", sample_area)
    blank = _non_negative("blank_area", blank_area)
    corrected = sample - blank
    if corrected <= AREA_TOLERANCE:
        return 0.0
    return corrected


def mass_from_area(area, calibration):
    """Interpolate the calibration series at an area; refuse to extrapolate."""
    points = validate_calibration(calibration)
    value = _positive("area", area)
    lo, hi = points[0][0], points[-1][0]
    if value < lo or value > hi:
        raise ValueError(
            "area %g is outside the calibrated span [%g, %g]; extrapolation refused"
            % (value, lo, hi)
        )
    for i in range(1, len(points)):
        a0, m0 = points[i - 1]
        a1, m1 = points[i]
        if value <= a1:
            if value == a0:
                return m0
            if value == a1:
                return m1
            t = (value - a0) / (a1 - a0)
            return m0 + t * (m1 - m0)
    return points[-1][1]


def recovery_corrected_mass(recovered_mass_ug, recovery_fraction):
    """Return the released mass implied by a recovered mass and its recovery."""
    mass = _non_negative("recovered_mass_ug", recovered_mass_ug)
    recovery = _real("recovery_fraction", recovery_fraction)
    if recovery <= 0.0 or recovery > 1.0:
        raise ValueError(
            "recovery_fraction must lie in (0, 1], got %r" % (recovery_fraction,)
        )
    return mass / recovery


def quantitation_state(mass_ug, loq_ug, lod_ug):
    """Categorize a mass against the quantitation and detection limits."""
    mass = _non_negative("mass_ug", mass_ug)
    loq = _positive("loq_ug", loq_ug)
    lod = _positive("lod_ug", lod_ug)
    if lod > loq + MASS_TOLERANCE_UG:
        raise ValueError(
            "lod_ug %g must not exceed loq_ug %g" % (lod, loq)
        )
    if mass < lod - MASS_TOLERANCE_UG:
        return STATE_NON_DETECTED
    if mass < loq - MASS_TOLERANCE_UG:
        return STATE_BELOW_QUANTITATION
    return STATE_QUANTIFIED


def mass_per_gram(mass_ug, sample_mass_g):
    """Return micrograms of product released per gram of sample."""
    mass = _non_negative("mass_ug", mass_ug)
    sample = _positive("sample_mass_g", sample_mass_g)
    return mass / sample


def mass_per_cubic_metre(mass_ug, vessel_volume_m3):
    """Return milligrams per cubic metre of vessel volume."""
    mass = _non_negative("mass_ug", mass_ug)
    volume = _positive("vessel_volume_m3", vessel_volume_m3)
    return (mass / 1000.0) / volume


def determine_compound(entry, conditions):
    """Return the concentration record for one identified offgassing product."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping")
    for key in ("compound", "sample_area", "calibration", "loq_ug", "lod_ug"):
        if key not in entry:
            raise ValueError("entry missing required key '%s'" % key)
    compound = entry["compound"]
    if not isinstance(compound, str) or not compound.strip():
        raise ValueError("compound must be a non-empty string")
    corrected = blank_corrected_area(entry["sample_area"], entry.get("blank_area", 0.0))
    loq = _positive("loq_ug of %s" % compound, entry["loq_ug"])
    lod = _positive("lod_ug of %s" % compound, entry["lod_ug"])
    record = {
        "compound": compound.strip(),
        "corrected_area": corrected,
        "recovered_mass_ug": 0.0,
        "released_mass_ug": 0.0,
        "state": STATE_NON_DETECTED,
        "ug_per_g": 0.0,
        "mg_per_m3": 0.0,
        "reported_mass_ug": 0.0,
        "notes": [],
    }
    if corrected <= AREA_TOLERANCE:
        record["notes"].append("sample area does not exceed the blank; non-detection")
        return record
    recovered = mass_from_area(corrected, entry["calibration"])
    released = recovery_corrected_mass(recovered, conditions["recovery_fraction"])
    state = quantitation_state(released, loq, lod)
    record.update(
        recovered_mass_ug=recovered,
        released_mass_ug=released,
        state=state,
    )
    if state == STATE_NON_DETECTED:
        record["notes"].append("released mass below the detection limit")
        return record
    reported = released if state == STATE_QUANTIFIED else loq
    if state == STATE_BELOW_QUANTITATION:
        record["notes"].append(
            "released mass between detection and quantitation; reported at the "
            "quantitation limit, not as zero"
        )
    record.update(
        reported_mass_ug=reported,
        ug_per_g=mass_per_gram(reported, conditions["sample_mass_g"]),
        mg_per_m3=mass_per_cubic_metre(reported, conditions["vessel_volume_m3"]),
    )
    return record


def determine_concentrations(spec):
    """Run the full concentration determination over an identified product set.

    spec keys: entries (sequence), sample_mass_g, vessel_volume_m3,
    recovery_fraction, optional duration_h.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("entries", "sample_mass_g", "vessel_volume_m3", "recovery_fraction"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    entries = spec["entries"]
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("spec['entries'] must be a non-empty sequence")
    conditions = validate_run_conditions(
        spec["sample_mass_g"],
        spec["vessel_volume_m3"],
        spec["recovery_fraction"],
        spec.get("duration_h"),
    )
    records = []
    seen = set()
    for entry in entries:
        record = determine_compound(entry, conditions)
        if record["compound"] in seen:
            raise ValueError("duplicate compound %r in the entry list" % record["compound"])
        seen.add(record["compound"])
        records.append(record)
    total_ug = sum(r["reported_mass_ug"] for r in records)
    findings = []
    below = [r["compound"] for r in records if r["state"] == STATE_BELOW_QUANTITATION]
    absent = [r["compound"] for r in records if r["state"] == STATE_NON_DETECTED]
    if below:
        findings.append(
            "reported at the quantitation limit: %s" % ", ".join(sorted(below))
        )
    if absent:
        findings.append("not detected above the blank: %s" % ", ".join(sorted(absent)))
    return {
        "conditions": conditions,
        "records": records,
        "total_reported_mass_ug": total_ug,
        "total_ug_per_g": total_ug / conditions["sample_mass_g"],
        "total_mg_per_m3": (total_ug / 1000.0) / conditions["vessel_volume_m3"],
        "quantified_count": sum(1 for r in records if r["state"] == STATE_QUANTIFIED),
        "findings": findings,
    }
