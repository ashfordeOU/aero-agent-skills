#!/usr/bin/env python3
"""Radiated magnetic susceptibility reporting, ECSS-E-ST-20-07C clause 5.4.10.5.

Paraphrased procedure, no verbatim standard text. The clause asks the record of
a radiated magnetic susceptibility run to carry the tables and diagrams that
show how the radiating loop was verified and what magnetic exposure levels the
run actually reached. This module turns that into a deterministic assessment:

  declared artefacts     -> which required table or diagram is absent
  loop geometry, current -> predicted axial flux density -> dB above one pT
  predicted vs measured  -> loop verification deviation
  reached vs required    -> per-frequency margin -> category
  required frequencies   -> the ones the pack never records

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Magnetic constant, henry per metre. Written out rather than imported so the
# module stays on the standard library of every supported interpreter.
MU0_H_PER_M = 4.0e-7 * math.pi

# Reference for the magnetic decibel scale used on exposure tables: one
# picotesla, so a level in dBpT is 20 log10(B / 1 pT).
PT_REFERENCE_T = 1.0e-12

# Decibel comparison tolerance. A margin is a difference of two float levels,
# so a level sitting exactly on the required one can land a few units in the
# last place either side of zero. This absorbs representation error only.
DB_TOL = 1e-9

# Relative tolerance used when matching a recorded frequency against a
# frequency the test specification requires.
FREQ_REL_TOL = 1e-9

# Deviation allowed between the flux density predicted from the loop geometry
# and the flux density the verification probe reads back, decibels.
DEFAULT_LOOP_AGREEMENT_DB = 3.0

# The three artefacts the clause expects the record to carry.
ARTEFACT_LEVEL_TABLE = "exposure-level-table"
ARTEFACT_SETUP_DIAGRAM = "setup-diagram"
ARTEFACT_LOOP_RECORD = "loop-verification-record"
REQUIRED_ARTEFACTS = (
    ARTEFACT_LEVEL_TABLE,
    ARTEFACT_SETUP_DIAGRAM,
    ARTEFACT_LOOP_RECORD,
)

CATEGORY_AT_LEVEL = "required-level-reached"
CATEGORY_SHORT = "short-of-required-level"
CATEGORY_ABOVE = "above-required-level"
CATEGORIES = (CATEGORY_AT_LEVEL, CATEGORY_SHORT, CATEGORY_ABOVE)

VERDICT_COMPLETE = "reporting-complete"
VERDICT_DEFICIENT = "reporting-deficient"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def at_most_db(value, bound):
    """True when a decibel quantity stays at or under a bound, float error aside."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=0.0, abs_tol=DB_TOL)


def loop_axial_flux_density_t(current_a, turns, radius_m, separation_m):
    """Flux density on the axis of a radiating loop, tesla.

    The loop is the field source of the method: a multi-turn coil of a stated
    radius driven with a stated current, held a stated distance from the face
    of the unit. The axial field it produces is what the exposure table has to
    be traceable to, and it falls off with separation far faster than the
    inverse square a bench operator expects.
    """
    current = _scalar(current_a, "current_a")
    radius = _scalar(radius_m, "radius_m")
    separation = _scalar(separation_m, "separation_m")
    if isinstance(turns, bool) or not isinstance(turns, int):
        raise ValueError("turns must be an integer, got %r" % (turns,))
    if turns < 1:
        raise ValueError("turns must be >= 1, got %d" % turns)
    if current <= 0.0:
        raise ValueError("current_a must be > 0, got %g" % current)
    if radius <= 0.0:
        raise ValueError("radius_m must be > 0, got %g" % radius)
    if separation < 0.0:
        raise ValueError("separation_m must be >= 0, got %g" % separation)
    numerator = MU0_H_PER_M * float(turns) * current * radius * radius
    denominator = 2.0 * math.pow(radius * radius + separation * separation, 1.5)
    return numerator / denominator


def tesla_to_dbpt(flux_density_t):
    """Convert a flux density in tesla to the dB-above-one-picotesla scale."""
    value = _scalar(flux_density_t, "flux_density_t")
    if value <= 0.0:
        raise ValueError("flux_density_t must be > 0, got %g" % value)
    return 20.0 * math.log10(value / PT_REFERENCE_T)


def dbpt_to_tesla(level_dbpt):
    """Convert a dB-above-one-picotesla level back to tesla."""
    level = _scalar(level_dbpt, "level_dbpt")
    return PT_REFERENCE_T * math.pow(10.0, level / 20.0)


def loop_verification_deviation_db(measured_dbpt, predicted_dbpt):
    """Signed deviation of the verification reading from the predicted field."""
    measured = _scalar(measured_dbpt, "measured_dbpt")
    predicted = _scalar(predicted_dbpt, "predicted_dbpt")
    return measured - predicted


def verify_loop(record, allowed_deviation_db=DEFAULT_LOOP_AGREEMENT_DB):
    """Grade one loop verification entry against the field its geometry predicts.

    Required fields: current_a, turns, radius_m, separation_m and
    measured_dbpt. The predicted level comes from the geometry, never from the
    reading, so a probe that has drifted cannot certify itself.
    """
    where = "loop_verification"
    if not isinstance(record, dict):
        raise ValueError("%s: record must be a mapping" % where)
    allowed = _scalar(allowed_deviation_db, "allowed_deviation_db")
    if allowed <= 0.0:
        raise ValueError("allowed_deviation_db must be > 0, got %g" % allowed)
    if "turns" not in record:
        raise ValueError("%s: missing required field 'turns'" % where)
    predicted_t = loop_axial_flux_density_t(
        _number(record, "current_a", where),
        record["turns"],
        _number(record, "radius_m", where),
        _number(record, "separation_m", where),
    )
    predicted_dbpt = tesla_to_dbpt(predicted_t)
    measured_dbpt = _number(record, "measured_dbpt", where)
    deviation = loop_verification_deviation_db(measured_dbpt, predicted_dbpt)
    return {
        "predicted_flux_density_t": predicted_t,
        "predicted_dbpt": predicted_dbpt,
        "measured_dbpt": measured_dbpt,
        "deviation_db": deviation,
        "allowed_deviation_db": allowed,
        "within_tolerance": at_most_db(abs(deviation), allowed),
    }


def exposure_margin_db(level_reached_dbpt, level_required_dbpt):
    """Margin of the exposure level reached over the level the test requires."""
    reached = _scalar(level_reached_dbpt, "level_reached_dbpt")
    required = _scalar(level_required_dbpt, "level_required_dbpt")
    return reached - required


def categorize_exposure(margin_db):
    """Group one exposure frequency by how its reached level sits on the requirement."""
    margin = _scalar(margin_db, "margin_db")
    if math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=DB_TOL):
        return CATEGORY_AT_LEVEL
    if margin < 0.0:
        return CATEGORY_SHORT
    return CATEGORY_ABOVE


def validate_exposure_table(rows):
    """Validate the recorded exposure table and return it normalized.

    Each row needs frequency_hz (positive, strictly increasing down the table),
    level_reached_dbpt and level_required_dbpt.
    """
    where = "exposure_table"
    if not isinstance(rows, (list, tuple)):
        raise ValueError("%s: rows must be a list" % where)
    if len(rows) == 0:
        raise ValueError("%s: at least one recorded row is required" % where)
    out = []
    previous = None
    for index, row in enumerate(rows):
        tag = "%s[%d]" % (where, index)
        if not isinstance(row, dict):
            raise ValueError("%s: row must be a mapping" % tag)
        frequency = _number(row, "frequency_hz", tag)
        if frequency <= 0.0:
            raise ValueError("%s: frequency_hz must be > 0, got %g" % (tag, frequency))
        if previous is not None and frequency <= previous:
            raise ValueError(
                "%s: frequencies must increase strictly (%g Hz after %g Hz)"
                % (tag, frequency, previous)
            )
        previous = frequency
        reached = _number(row, "level_reached_dbpt", tag)
        required = _number(row, "level_required_dbpt", tag)
        margin = exposure_margin_db(reached, required)
        out.append(
            {
                "frequency_hz": frequency,
                "level_reached_dbpt": reached,
                "level_required_dbpt": required,
                "margin_db": margin,
                "category": categorize_exposure(margin),
            }
        )
    return out


def missing_required_frequencies(rows, required_frequencies_hz):
    """Frequencies the specification calls for that the table never records."""
    if not isinstance(required_frequencies_hz, (list, tuple)):
        raise ValueError("required_frequencies_hz must be a list")
    recorded = [row["frequency_hz"] for row in rows]
    out = []
    for index, wanted in enumerate(required_frequencies_hz):
        value = _scalar(wanted, "required_frequencies_hz[%d]" % index)
        if value <= 0.0:
            raise ValueError(
                "required_frequencies_hz[%d] must be > 0, got %g" % (index, value)
            )
        hit = False
        for frequency in recorded:
            if math.isclose(frequency, value, rel_tol=FREQ_REL_TOL, abs_tol=0.0):
                hit = True
                break
        if not hit:
            out.append(value)
    return out


def missing_artefacts(declared):
    """Required tables and diagrams the reporting pack does not declare."""
    where = "artefacts"
    if not isinstance(declared, dict):
        raise ValueError("%s: declaration must be a mapping" % where)
    out = []
    for artefact in REQUIRED_ARTEFACTS:
        if not _flag(declared, artefact, where):
            out.append(artefact)
    return out


def assess_radiated_magnetic_susceptibility_reporting(
    pack, allowed_deviation_db=DEFAULT_LOOP_AGREEMENT_DB
):
    """Full clause 5.4.10.5 assessment of a magnetic susceptibility report pack.

    Required keys: artefacts (a mapping of the three artefact flags),
    loop_verification (a mapping) and exposure_table (a list of rows).
    Optional: required_frequencies_hz.
    """
    where = "reporting_pack"
    if not isinstance(pack, dict):
        raise ValueError("%s: pack must be a mapping" % where)
    for key in ("artefacts", "loop_verification", "exposure_table"):
        if key not in pack:
            raise ValueError("%s: missing required field %r" % (where, key))

    absent = missing_artefacts(pack["artefacts"])
    loop = verify_loop(pack["loop_verification"], allowed_deviation_db)
    table = validate_exposure_table(pack["exposure_table"])
    uncovered = missing_required_frequencies(
        table, pack.get("required_frequencies_hz", [])
    )

    shortfalls = [row for row in table if row["category"] == CATEGORY_SHORT]
    overdriven = [row for row in table if row["category"] == CATEGORY_ABOVE]

    findings = []
    for artefact in absent:
        findings.append(
            "the pack does not carry the %s the clause requires" % artefact
        )
    if not loop["within_tolerance"]:
        findings.append(
            "loop verification reads %g dBpT against a predicted %g dBpT, a %g dB "
            "deviation past the %g dB allowed"
            % (
                loop["measured_dbpt"],
                loop["predicted_dbpt"],
                loop["deviation_db"],
                loop["allowed_deviation_db"],
            )
        )
    for row in shortfalls:
        findings.append(
            "at %g Hz the run reached %g dBpT, %g dB short of the required %g dBpT"
            % (
                row["frequency_hz"],
                row["level_reached_dbpt"],
                -row["margin_db"],
                row["level_required_dbpt"],
            )
        )
    for frequency in uncovered:
        findings.append(
            "the required frequency %g Hz appears nowhere in the exposure table"
            % frequency
        )

    limitations = []
    for row in overdriven:
        limitations.append(
            "at %g Hz the run reached %g dB above the required level, so the unit "
            "was exposed harder than the specification asks"
            % (row["frequency_hz"], row["margin_db"])
        )

    return {
        "missing_artefacts": absent,
        "loop_verification": loop,
        "exposure_table": table,
        "uncovered_frequencies_hz": uncovered,
        "shortfall_count": len(shortfalls),
        "overdriven_count": len(overdriven),
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_COMPLETE if not findings else VERDICT_DEFICIENT,
    }
