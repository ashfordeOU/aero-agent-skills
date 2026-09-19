"""Magnetic cleanliness, ESD and EMC protection for spacecraft mechanisms.

Anchor: ECSS-E-ST-33-01C clause 4.7.7.8 (a mechanism meets the magnetic
cleanliness budget it is allocated and carries the electrostatic-discharge
and electromagnetic-compatibility protection its installation calls for).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Combine the residual magnetic dipole moments of a mechanism's sources two
   ways -- root-sum-square for orientations that are genuinely independent,
   and a straight sum for the worst-case aligned assumption -- and grade both
   against the allocation.
2. Convert the combined moment into the field it puts at a magnetometer's
   distance, on the dipole axis, and grade that against the sensor's
   cleanliness limit.
3. Grade electrostatic protection: every conductive surface of the mechanism
   needs a bleed path to structure whose resistance sits inside the window
   that drains charge without becoming a fault-current path.
4. Grade electromagnetic compatibility: the switching fundamental of a drive
   and its harmonics are compared with the protected receiver bands, and a
   drive without a declared filter or a terminated screen is a finding.
"""

import math

__all__ = [
    "VACUUM_PERMEABILITY",
    "MOMENT_TOLERANCE_A_M2",
    "FIELD_TOLERANCE_T",
    "RESISTANCE_TOLERANCE_OHM",
    "MIN_BLEED_RESISTANCE_OHM",
    "MAX_BLEED_RESISTANCE_OHM",
    "validate_source",
    "combined_moment_a_m2",
    "axial_dipole_field_t",
    "grade_magnetic_budget",
    "validate_surface",
    "esd_findings",
    "harmonic_frequencies_hz",
    "band_conflicts",
    "emc_findings",
    "assess_magnetic_esd_emc",
]

# Magnetic constant, henries per metre.
VACUUM_PERMEABILITY = 4.0e-7 * math.pi

# Comparisons against a budget can land a few ULPs on the wrong side of an
# exact equality. Absorb the representation error here rather than relaxing
# the engineering limit.
MOMENT_TOLERANCE_A_M2 = 1e-12
FIELD_TOLERANCE_T = 1e-18
RESISTANCE_TOLERANCE_OHM = 1e-6

# Charge-bleed window: below the lower bound the path is a fault-current
# route rather than a bleed; above the upper bound the surface floats long
# enough to build a discharge.
MIN_BLEED_RESISTANCE_OHM = 1.0e5
MAX_BLEED_RESISTANCE_OHM = 1.0e9


def _positive(label, value):
    """Return value as a positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def validate_source(source):
    """Return a normalised magnetic-source record.

    Required keys: id, moment_a_m2. Optional: orientation_known (bool).
    """
    if not isinstance(source, dict):
        raise ValueError("source must be a mapping")
    for key in ("id", "moment_a_m2"):
        if key not in source:
            raise ValueError("source missing required key '%s'" % key)
    identifier = source["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("source id must be a non-empty string")
    return {
        "id": identifier.strip(),
        "moment_a_m2": _non_negative("moment_a_m2", source["moment_a_m2"]),
        "orientation_known": bool(source.get("orientation_known", False)),
    }


def combined_moment_a_m2(sources, aligned=False):
    """Return the combined residual dipole moment of a source set.

    aligned=True sums the moments (the worst case, and the only defensible
    assumption when the orientations are not fixed by the design);
    aligned=False root-sum-squares them.
    """
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ValueError("sources must be a non-empty sequence")
    if not isinstance(aligned, bool):
        raise ValueError("aligned must be a boolean")
    total = 0.0
    square = 0.0
    for source in sources:
        record = validate_source(source)
        total += record["moment_a_m2"]
        square += record["moment_a_m2"] ** 2
    return total if aligned else math.sqrt(square)


def axial_dipole_field_t(moment_a_m2, distance_m):
    """Return the on-axis field of a magnetic dipole at a distance."""
    moment = _non_negative("moment_a_m2", moment_a_m2)
    distance = _positive("distance_m", distance_m)
    return VACUUM_PERMEABILITY * moment / (2.0 * math.pi * distance ** 3)


def grade_magnetic_budget(sources, allocation_a_m2, sensor_distance_m,
                          sensor_limit_t):
    """Return the magnetic-cleanliness grading of a mechanism's sources."""
    allocation = _positive("allocation_a_m2", allocation_a_m2)
    distance = _positive("sensor_distance_m", sensor_distance_m)
    limit = _positive("sensor_limit_t", sensor_limit_t)
    records = [validate_source(s) for s in sources]
    unknown = [r["id"] for r in records if not r["orientation_known"]]
    rss = combined_moment_a_m2(sources, aligned=False)
    aligned = combined_moment_a_m2(sources, aligned=True)
    # Orientations that the design does not fix cannot be assumed
    # independent, so the aligned sum is the number that is graded.
    governing = aligned if unknown else rss
    field = axial_dipole_field_t(governing, distance)
    moment_ok = governing < allocation or math.isclose(
        governing, allocation, rel_tol=0.0, abs_tol=MOMENT_TOLERANCE_A_M2
    )
    field_ok = field < limit or math.isclose(
        field, limit, rel_tol=0.0, abs_tol=FIELD_TOLERANCE_T
    )
    findings = []
    if not moment_ok:
        findings.append(
            "combined dipole moment %.6g A.m2 exceeds the %.6g A.m2 allocation"
            % (governing, allocation)
        )
    if not field_ok:
        findings.append(
            "stray field %.6g T at %.3f m exceeds the %.6g T sensor limit"
            % (field, distance, limit)
        )
    return {
        "rss_moment_a_m2": rss,
        "aligned_moment_a_m2": aligned,
        "governing_moment_a_m2": governing,
        "orientations_unknown": unknown,
        "field_t": field,
        "moment_ok": moment_ok,
        "field_ok": field_ok,
        "compliant": moment_ok and field_ok,
        "findings": findings,
    }


def validate_surface(surface):
    """Return a normalised conductive-surface record.

    Required keys: id, area_m2. Optional: bleed_resistance_ohm (absent means
    the surface is isolated).
    """
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping")
    for key in ("id", "area_m2"):
        if key not in surface:
            raise ValueError("surface missing required key '%s'" % key)
    identifier = surface["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("surface id must be a non-empty string")
    record = {
        "id": identifier.strip(),
        "area_m2": _positive("area_m2", surface["area_m2"]),
        "bleed_resistance_ohm": None,
    }
    if surface.get("bleed_resistance_ohm") is not None:
        record["bleed_resistance_ohm"] = _positive(
            "bleed_resistance_ohm", surface["bleed_resistance_ohm"]
        )
    return record


def esd_findings(surfaces, min_ohm=MIN_BLEED_RESISTANCE_OHM,
                 max_ohm=MAX_BLEED_RESISTANCE_OHM):
    """Return the electrostatic-protection findings of a surface set."""
    if not isinstance(surfaces, (list, tuple)) or not surfaces:
        raise ValueError("surfaces must be a non-empty sequence")
    low = _positive("min_ohm", min_ohm)
    high = _positive("max_ohm", max_ohm)
    if low >= high:
        raise ValueError("min_ohm %g must be below max_ohm %g" % (low, high))
    findings = []
    records = []
    for surface in surfaces:
        record = validate_surface(surface)
        resistance = record["bleed_resistance_ohm"]
        if resistance is None:
            findings.append(
                "%s: conductive surface of %.4g m2 has no bleed path to structure"
                % (record["id"], record["area_m2"])
            )
            records.append({"id": record["id"], "bleed_resistance_ohm": None,
                            "compliant": False})
            continue
        too_low = resistance < low and not math.isclose(
            resistance, low, rel_tol=0.0, abs_tol=RESISTANCE_TOLERANCE_OHM
        )
        too_high = resistance > high and not math.isclose(
            resistance, high, rel_tol=0.0, abs_tol=RESISTANCE_TOLERANCE_OHM
        )
        if too_low:
            findings.append(
                "%s: bleed resistance %.4g ohm is below the %.4g ohm floor; the path is a "
                "fault-current route, not a bleed" % (record["id"], resistance, low)
            )
        if too_high:
            findings.append(
                "%s: bleed resistance %.4g ohm is above the %.4g ohm ceiling; the surface "
                "floats long enough to build a discharge"
                % (record["id"], resistance, high)
            )
        records.append({"id": record["id"], "bleed_resistance_ohm": resistance,
                        "compliant": not (too_low or too_high)})
    return {"records": records, "findings": findings}


def harmonic_frequencies_hz(fundamental_hz, count):
    """Return the first `count` harmonics of a switching fundamental."""
    fundamental = _positive("fundamental_hz", fundamental_hz)
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("count must be an integer")
    if count < 1:
        raise ValueError("count must be at least one, got %d" % count)
    return [fundamental * (index + 1) for index in range(count)]


def band_conflicts(frequencies_hz, protected_bands):
    """Return the (frequency, band) pairs falling inside a protected band."""
    if not isinstance(protected_bands, (list, tuple)):
        raise ValueError("protected_bands must be a sequence")
    bands = []
    for index, band in enumerate(protected_bands):
        if not isinstance(band, dict):
            raise ValueError("protected_bands[%d] must be a mapping" % index)
        for key in ("id", "low_hz", "high_hz"):
            if key not in band:
                raise ValueError("protected_bands[%d] missing key '%s'" % (index, key))
        low = _positive("low_hz", band["low_hz"])
        high = _positive("high_hz", band["high_hz"])
        if low >= high:
            raise ValueError(
                "protected band '%s' has low_hz %g at or above high_hz %g"
                % (band["id"], low, high)
            )
        bands.append({"id": str(band["id"]), "low_hz": low, "high_hz": high})
    conflicts = []
    for frequency in frequencies_hz:
        value = _positive("frequency", frequency)
        for band in bands:
            if band["low_hz"] <= value <= band["high_hz"]:
                conflicts.append({"frequency_hz": value, "band": band["id"]})
    return conflicts


def emc_findings(drives, protected_bands, harmonic_count=5):
    """Return the electromagnetic-compatibility findings of a drive set."""
    if not isinstance(drives, (list, tuple)) or not drives:
        raise ValueError("drives must be a non-empty sequence")
    findings = []
    records = []
    for index, drive in enumerate(drives):
        if not isinstance(drive, dict):
            raise ValueError("drives[%d] must be a mapping" % index)
        for key in ("id", "switching_hz"):
            if key not in drive:
                raise ValueError("drives[%d] missing key '%s'" % (index, key))
        identifier = str(drive["id"])
        harmonics = harmonic_frequencies_hz(drive["switching_hz"], harmonic_count)
        conflicts = band_conflicts(harmonics, protected_bands)
        filtered = bool(drive.get("filter_declared", False))
        screened = bool(drive.get("screen_terminated", False))
        for conflict in conflicts:
            findings.append(
                "%s: switching harmonic at %.4g Hz falls inside protected band %s"
                % (identifier, conflict["frequency_hz"], conflict["band"])
            )
        if not filtered:
            findings.append(
                "%s: no conducted-emission filter declared on the drive supply" % identifier
            )
        if not screened:
            findings.append(
                "%s: drive harness screen is not declared terminated to structure at both "
                "ends" % identifier
            )
        records.append({
            "id": identifier,
            "harmonics_hz": harmonics,
            "conflicts": conflicts,
            "filter_declared": filtered,
            "screen_terminated": screened,
            "compliant": not conflicts and filtered and screened,
        })
    return {"records": records, "findings": findings}


def assess_magnetic_esd_emc(spec):
    """Run the full clause 4.7.7.8 magnetic, ESD and EMC assessment.

    spec keys: sources, allocation_a_m2, sensor_distance_m, sensor_limit_t,
    surfaces, drives, protected_bands. Optional: harmonic_count,
    min_bleed_ohm, max_bleed_ohm.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("sources", "allocation_a_m2", "sensor_distance_m", "sensor_limit_t",
                "surfaces", "drives", "protected_bands"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    sources = spec["sources"]
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ValueError("spec['sources'] must be a non-empty sequence")
    magnetic = grade_magnetic_budget(
        sources, spec["allocation_a_m2"], spec["sensor_distance_m"], spec["sensor_limit_t"]
    )
    esd = esd_findings(
        spec["surfaces"],
        spec.get("min_bleed_ohm", MIN_BLEED_RESISTANCE_OHM),
        spec.get("max_bleed_ohm", MAX_BLEED_RESISTANCE_OHM),
    )
    emc = emc_findings(spec["drives"], spec["protected_bands"],
                       spec.get("harmonic_count", 5))
    findings = list(magnetic["findings"]) + list(esd["findings"]) + list(emc["findings"])
    return {
        "magnetic": magnetic,
        "esd": esd["records"],
        "emc": emc["records"],
        "findings": findings,
        "compliant": not findings,
    }
