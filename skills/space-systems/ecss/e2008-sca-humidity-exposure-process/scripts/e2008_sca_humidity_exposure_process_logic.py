#!/usr/bin/env python3
"""Subgroup humidity exposure of solar cell assemblies -- chamber hold accounting.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.8.2 -- the samples of a qualification
subgroup are held inside a chamber at ambient pressure for the humidity
exposure period. The procedure below is a paraphrase into implementable steps;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the chamber record: time-ordered samples of chamber pressure that
   bound at least one interval.
2. Validate the ambient pressure band the chamber is required to sit in, and
   reduce the record to the intervals during which the chamber actually held
   that band, merging intervals that touch so a continuous hold reads as one.
3. Validate the subgroup roster: one load time and one unload time per sample,
   unique sample identifiers, no sample unloaded before it was loaded.
4. Credit each sample only with the overlap between its own time inside the
   chamber and the intervals when the chamber held ambient pressure. Time in
   the chamber while the chamber was out of band earns nothing, and time
   outside the logged record earns nothing either because the chamber state
   there was never observed.
5. Compare every sample with the required exposure period, absorbing
   floating-point representation error at the boundary with a named tolerance.
6. Close the subgroup only when it carries enough samples and every one of
   them reached the period; report the shortfall of each one that did not.
"""

import math

__all__ = [
    "AMBIENT_PRESSURE_BAND_KPA",
    "DEFAULT_MIN_SUBGROUP_SIZE",
    "EXPOSURE_TOLERANCE_REL",
    "SAMPLE_EXPOSURE_COMPLETE",
    "SAMPLE_EXPOSURE_SHORT",
    "SUBGROUP_EXPOSED",
    "SUBGROUP_SHORT",
    "SUBGROUP_UNDERSIZED",
    "validate_pressure_band",
    "validate_chamber_record",
    "validate_sample_window",
    "validate_subgroup",
    "pressure_in_band",
    "ambient_hold_intervals",
    "overlap_h",
    "credit_sample_exposure",
    "assess_subgroup_exposure",
]

# The clause holds the chamber at ambient pressure: the exposure is damp heat,
# not an altitude or a vacuum exposure. This is the band a sea-level
# laboratory sits in; a chamber at altitude declares its own.
AMBIENT_PRESSURE_BAND_KPA = (86.0, 106.0)

# A subgroup speaks for a lot only when it carries enough samples.
DEFAULT_MIN_SUBGROUP_SIZE = 4

# Credited exposure is a sum of interval overlaps and the period is read from a
# test specification, so a sample that physically lands exactly on its period
# can sum a few units in the last place either side of it. The comparison
# absorbs that rather than moving the required period.
EXPOSURE_TOLERANCE_REL = 1e-9

SAMPLE_EXPOSURE_COMPLETE = "sample-exposure-complete"
SAMPLE_EXPOSURE_SHORT = "sample-exposure-short"

SUBGROUP_EXPOSED = "subgroup-exposed"
SUBGROUP_SHORT = "subgroup-short"
SUBGROUP_UNDERSIZED = "subgroup-undersized"

_RECORD_KEYS = ("time_h", "pressure_kpa")


def _real(value, label):
    """Return a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    return value


def validate_pressure_band(band):
    """Return a validated (low, high) ambient pressure band in kPa."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("pressure band must be a (low, high) pair")
    low = _real(band[0], "pressure band low edge")
    high = _real(band[1], "pressure band high edge")
    if low <= 0.0:
        raise ValueError("pressure band low edge must be positive")
    if low > high:
        raise ValueError("pressure band is inverted: %g above %g" % (low, high))
    return (low, high)


def validate_chamber_record(record):
    """Return the validated, strictly time-ordered chamber pressure record."""
    if not isinstance(record, (list, tuple)) or len(record) < 2:
        raise ValueError("chamber record needs at least two samples to bound an interval")
    rows = []
    for index, entry in enumerate(record):
        if not isinstance(entry, dict):
            raise ValueError("chamber record entry %d must be a mapping" % index)
        for key in _RECORD_KEYS:
            if key not in entry:
                raise ValueError("chamber record entry %d is missing '%s'" % (index, key))
        time_h = _real(entry["time_h"], "chamber record entry %d time_h" % index)
        pressure = _real(entry["pressure_kpa"], "chamber record entry %d pressure_kpa" % index)
        if time_h < 0.0:
            raise ValueError("chamber record entry %d has a negative time stamp" % index)
        if pressure <= 0.0:
            raise ValueError("chamber record entry %d pressure must be positive" % index)
        rows.append({"time_h": time_h, "pressure_kpa": pressure, "index": index})
    for i in range(1, len(rows)):
        if rows[i]["time_h"] <= rows[i - 1]["time_h"]:
            raise ValueError(
                "chamber record time stamps must strictly increase (entry %d at %g h "
                "follows %g h)" % (i, rows[i]["time_h"], rows[i - 1]["time_h"])
            )
    return rows


def validate_sample_window(sample, index):
    """Return one validated subgroup sample window."""
    if not isinstance(sample, dict):
        raise ValueError("subgroup sample %d must be a mapping" % index)
    for key in ("sample_id", "loaded_h", "unloaded_h"):
        if key not in sample:
            raise ValueError("subgroup sample %d is missing '%s'" % (index, key))
    sample_id = sample["sample_id"]
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError("subgroup sample %d needs a non-empty sample_id" % index)
    loaded = _real(sample["loaded_h"], "subgroup sample %d loaded_h" % index)
    unloaded = _real(sample["unloaded_h"], "subgroup sample %d unloaded_h" % index)
    if loaded < 0.0:
        raise ValueError("subgroup sample %d was loaded at a negative time" % index)
    if unloaded <= loaded:
        raise ValueError(
            "subgroup sample %s was unloaded at %g h, not after its load at %g h"
            % (sample_id, unloaded, loaded)
        )
    return {"sample_id": sample_id.strip(), "loaded_h": loaded, "unloaded_h": unloaded}


def validate_subgroup(samples):
    """Return the validated subgroup roster with unique sample identifiers."""
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("the subgroup needs at least one sample")
    roster = [validate_sample_window(s, i) for i, s in enumerate(samples)]
    seen = set()
    for entry in roster:
        if entry["sample_id"] in seen:
            raise ValueError("duplicate sample_id in the subgroup: %s" % entry["sample_id"])
        seen.add(entry["sample_id"])
    return roster


def pressure_in_band(pressure_kpa, band=AMBIENT_PRESSURE_BAND_KPA):
    """Return True when a chamber pressure sits inside the band, edges included."""
    low, high = validate_pressure_band(band)
    pressure = _real(pressure_kpa, "pressure")
    if math.isclose(pressure, low, rel_tol=EXPOSURE_TOLERANCE_REL, abs_tol=0.0):
        return True
    if math.isclose(pressure, high, rel_tol=EXPOSURE_TOLERANCE_REL, abs_tol=0.0):
        return True
    return low < pressure < high


def ambient_hold_intervals(record, band=AMBIENT_PRESSURE_BAND_KPA):
    """Return the merged intervals during which the chamber held ambient pressure.

    An interval is credited only when both of its endpoints sit inside the
    band: between two logged entries the chamber state is not observed, so a
    single out-of-band entry voids the interval before it and the interval
    after it.
    """
    rows = validate_chamber_record(record)
    band = validate_pressure_band(band)
    intervals = []
    for i in range(1, len(rows)):
        start, end = rows[i - 1], rows[i]
        if pressure_in_band(start["pressure_kpa"], band) and pressure_in_band(
            end["pressure_kpa"], band
        ):
            if intervals and math.isclose(
                intervals[-1][1], start["time_h"], rel_tol=EXPOSURE_TOLERANCE_REL, abs_tol=0.0
            ):
                intervals[-1] = (intervals[-1][0], end["time_h"])
            else:
                intervals.append((start["time_h"], end["time_h"]))
    return [tuple(pair) for pair in intervals]


def overlap_h(window, interval):
    """Return the overlap in hours between a sample window and one interval."""
    for pair, label in ((window, "window"), (interval, "interval")):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("%s must be a (start, end) pair" % label)
    start = max(_real(window[0], "window start"), _real(interval[0], "interval start"))
    end = min(_real(window[1], "window end"), _real(interval[1], "interval end"))
    if end <= start:
        return 0.0
    return end - start


def credit_sample_exposure(sample, record, band=AMBIENT_PRESSURE_BAND_KPA):
    """Return the exposure accounting of one subgroup sample."""
    window = validate_sample_window(sample, 0)
    rows = validate_chamber_record(record)
    intervals = ambient_hold_intervals(rows, band)
    span = (window["loaded_h"], window["unloaded_h"])
    credited = math.fsum(overlap_h(span, interval) for interval in intervals)
    in_chamber = window["unloaded_h"] - window["loaded_h"]
    logged = overlap_h(span, (rows[0]["time_h"], rows[-1]["time_h"]))
    return {
        "sample_id": window["sample_id"],
        "loaded_h": window["loaded_h"],
        "unloaded_h": window["unloaded_h"],
        "in_chamber_h": in_chamber,
        "credited_exposure_h": credited,
        "uncredited_h": in_chamber - credited,
        "unlogged_h": in_chamber - logged,
        "ambient_hold_count": len(intervals),
        "longest_ambient_hold_h": max(
            (end - start for start, end in intervals), default=0.0
        ),
    }


def assess_subgroup_exposure(spec):
    """Run the full clause 6.4.3.8.2 subgroup humidity exposure assessment.

    spec keys: samples, chamber_record, required_exposure_h; optional
    pressure_band and min_subgroup_size.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("samples", "chamber_record", "required_exposure_h"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required = _real(spec["required_exposure_h"], "required_exposure_h")
    if required <= 0.0:
        raise ValueError("required_exposure_h must be positive")
    minimum = spec.get("min_subgroup_size", DEFAULT_MIN_SUBGROUP_SIZE)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        raise ValueError("min_subgroup_size must be a positive integer")

    band = validate_pressure_band(spec.get("pressure_band", AMBIENT_PRESSURE_BAND_KPA))
    rows = validate_chamber_record(spec["chamber_record"])
    roster = validate_subgroup(spec["samples"])

    results = []
    findings = []
    for entry in roster:
        accounting = credit_sample_exposure(entry, rows, band)
        reached = accounting["credited_exposure_h"] > required or math.isclose(
            accounting["credited_exposure_h"], required,
            rel_tol=EXPOSURE_TOLERANCE_REL, abs_tol=0.0,
        )
        accounting["shortfall_h"] = 0.0 if reached else required - accounting["credited_exposure_h"]
        accounting["verdict"] = SAMPLE_EXPOSURE_COMPLETE if reached else SAMPLE_EXPOSURE_SHORT
        if not reached:
            findings.append(
                "sample %s holds %.3f h of ambient-pressure exposure against a required "
                "%.3f h" % (accounting["sample_id"], accounting["credited_exposure_h"], required)
            )
        if accounting["unlogged_h"] > 0.0:
            findings.append(
                "sample %s spent %.3f h in the chamber outside the logged record, which "
                "cannot be credited" % (accounting["sample_id"], accounting["unlogged_h"])
            )
        results.append(accounting)

    if len(roster) < minimum:
        verdict = SUBGROUP_UNDERSIZED
        findings.insert(
            0,
            "the subgroup carries %d samples against a floor of %d" % (len(roster), minimum),
        )
    elif any(r["verdict"] == SAMPLE_EXPOSURE_SHORT for r in results):
        verdict = SUBGROUP_SHORT
    else:
        verdict = SUBGROUP_EXPOSED

    return {
        "verdict": verdict,
        "required_exposure_h": required,
        "min_subgroup_size": minimum,
        "pressure_band_kpa": band,
        "sample_count": len(roster),
        "record_span_h": rows[-1]["time_h"] - rows[0]["time_h"],
        "ambient_hold_h": math.fsum(
            end - start for start, end in ambient_hold_intervals(rows, band)
        ),
        "samples": results,
        "findings": findings,
    }
