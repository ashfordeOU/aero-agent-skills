#!/usr/bin/env python3
"""Harness-sample representativeness for an electromagnetic-compatibility
bench setup.

Anchor: ECSS-E-ST-20-07C clause 5.2.6.6.1 (paraphrased into an
implementable procedure; no verbatim standard text).

The clause requires the cable a unit is wired up with on the bench to
be built the way the flight harness is built: the same twisting, the
same shield construction, and the same way of landing the shield. The
harness is the dominant coupling structure in a unit-level run, so a
sample that differs in any of those three properties measures a
different antenna from the one that flies.

Offline, deterministic, python3 standard library only.
"""

import math

SHIELD_CONSTRUCTIONS = (
    "braid",
    "foil",
    "braid-over-foil",
    "unshielded",
)

SHIELD_TERMINATIONS = (
    "circumferential-backshell",
    "pigtail",
    "unterminated",
)

DEFAULT_TWIST_TOLERANCE = 0.10
DEFAULT_COVERAGE_ALLOWANCE_POINTS = 5.0
DEFAULT_PIGTAIL_LENGTH_LIMIT_MM = 25.0
DEFAULT_PIGTAIL_INDUCTANCE_LIMIT_NH = 30.0
MIN_ROUND_WIRE_RATIO = 4.0
REL_TOL = 1e-9


def _mapping(record, label):
    """Return record as a mapping or raise ValueError."""
    if not isinstance(record, dict):
        raise ValueError(
            "%s must be a mapping, got %s" % (label, type(record).__name__)
        )
    return record


def _number(value, label, minimum=None, maximum=None, strict=False):
    """Return value as a finite bounded float or raise ValueError."""
    if value is None:
        raise ValueError("%s is required" % label)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    val = float(value)
    if math.isnan(val) or math.isinf(val):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if strict and val <= minimum:
            raise ValueError("%s must be > %g, got %g" % (label, minimum, val))
        if not strict and val < minimum:
            raise ValueError("%s must be >= %g, got %g" % (label, minimum, val))
    if maximum is not None and val > maximum:
        raise ValueError("%s must be <= %g, got %g" % (label, maximum, val))
    return val


def _at_most(value, ceiling):
    """True when value is under ceiling, absorbing representation error.

    A deviation formed as a difference can land a few ULPs above an
    allowance it physically meets; the comparison absorbs that
    representation error rather than widening the engineering allowance.
    """
    return value <= ceiling or math.isclose(value, ceiling, rel_tol=REL_TOL)


def twists_per_metre(lay_length_mm):
    """Convert a twist lay length in millimetres to twists per metre."""
    lay = _number(lay_length_mm, "lay_length_mm", minimum=0.0, strict=True)
    return 1000.0 / lay


def categorize_shield_construction(record):
    """Categorize a shield build into one of SHIELD_CONSTRUCTIONS.

    record keys: braid_coverage_percent (float 0-100 or None), foil_present
    (bool, default False).
    """
    rec = _mapping(record, "shield construction record")
    raw = rec.get("braid_coverage_percent")
    foil = rec.get("foil_present", False)
    if not isinstance(foil, bool):
        raise ValueError("foil_present must be a boolean, got %r" % (foil,))
    coverage = None
    if raw is not None:
        coverage = _number(raw, "braid_coverage_percent", minimum=0.0,
                           maximum=100.0)
        if coverage == 0.0:
            coverage = None
    if coverage is not None and foil:
        return "braid-over-foil"
    if coverage is not None:
        return "braid"
    if foil:
        return "foil"
    return "unshielded"


def braid_coverage(record):
    """Return the declared braid optical coverage, or None when absent."""
    construction = categorize_shield_construction(record)
    if construction in ("braid", "braid-over-foil"):
        return float(record["braid_coverage_percent"])
    return None


def categorize_shield_termination(record):
    """Categorize a shield termination into one of SHIELD_TERMINATIONS.

    record keys: circumferential_backshell (bool, default False),
    pigtail_length_mm (float > 0 or None).
    """
    rec = _mapping(record, "shield termination record")
    backshell = rec.get("circumferential_backshell", False)
    if not isinstance(backshell, bool):
        raise ValueError(
            "circumferential_backshell must be a boolean, got %r" % (backshell,)
        )
    pigtail = rec.get("pigtail_length_mm")
    if pigtail is not None:
        pigtail = _number(pigtail, "pigtail_length_mm", minimum=0.0,
                          strict=True)
    if backshell and pigtail is not None:
        raise ValueError(
            "termination declares both a circumferential backshell and a "
            "pigtail length"
        )
    if backshell:
        return "circumferential-backshell"
    if pigtail is not None:
        return "pigtail"
    return "unterminated"


def pigtail_inductance_nh(length_mm, diameter_mm):
    """Self-inductance of a round pigtail wire, in nanohenry.

    Round-wire relation: L = 0.2 * l * (ln(4 * l / d) - 0.75), with l and d
    in millimetres and L in nanohenry.
    """
    length = _number(length_mm, "length_mm", minimum=0.0, strict=True)
    diameter = _number(diameter_mm, "diameter_mm", minimum=0.0, strict=True)
    ratio = 4.0 * length / diameter
    if ratio <= MIN_ROUND_WIRE_RATIO:
        raise ValueError(
            "round-wire relation needs a length well above the diameter; "
            "4*length/diameter is %g" % ratio
        )
    return 0.2 * length * (math.log(ratio) - 0.75)


def compare_twisting(flight_lay_mm, sample_lay_mm,
                     tolerance_fraction=DEFAULT_TWIST_TOLERANCE):
    """Compare sample twisting against the flight run, in twists per metre."""
    fraction = _number(tolerance_fraction, "tolerance_fraction", minimum=0.0,
                       maximum=1.0, strict=True)
    flight_tpm = twists_per_metre(flight_lay_mm)
    sample_tpm = twists_per_metre(sample_lay_mm)
    allowed = flight_tpm * fraction
    deviation = abs(sample_tpm - flight_tpm)
    within = _at_most(deviation, allowed)
    findings = []
    if not within:
        findings.append(
            "twist-lay-length-deviation: sample %.3f twists-per-metre against "
            "flight %.3f, allowance %.3f" % (sample_tpm, flight_tpm, allowed)
        )
    return {
        "flight_twists_per_metre": flight_tpm,
        "sample_twists_per_metre": sample_tpm,
        "deviation": deviation,
        "allowed": allowed,
        "within_tolerance": within,
        "findings": findings,
    }


def compare_shielding(flight, sample,
                      coverage_allowance_points=DEFAULT_COVERAGE_ALLOWANCE_POINTS):
    """Compare sample shield construction against the flight construction."""
    allowance = _number(coverage_allowance_points, "coverage_allowance_points",
                        minimum=0.0)
    flight_construction = categorize_shield_construction(flight)
    sample_construction = categorize_shield_construction(sample)
    findings = []
    result = {
        "flight_construction": flight_construction,
        "sample_construction": sample_construction,
        "findings": findings,
    }
    if flight_construction != sample_construction:
        findings.append(
            "shield-construction-mismatch: flight %s against sample %s"
            % (flight_construction, sample_construction)
        )
        return result
    flight_coverage = braid_coverage(flight)
    sample_coverage = braid_coverage(sample)
    if flight_coverage is not None and sample_coverage is not None:
        deviation = abs(sample_coverage - flight_coverage)
        result["coverage_deviation_points"] = deviation
        if not _at_most(deviation, allowance):
            findings.append(
                "braid-optical-coverage-deviation: sample %.2f percent against "
                "flight %.2f percent, allowance %.2f points"
                % (sample_coverage, flight_coverage, allowance)
            )
    return result


def compare_termination(flight, sample,
                        pigtail_length_limit_mm=DEFAULT_PIGTAIL_LENGTH_LIMIT_MM,
                        pigtail_inductance_limit_nh=DEFAULT_PIGTAIL_INDUCTANCE_LIMIT_NH):
    """Compare sample shield termination against the flight termination."""
    length_limit = _number(pigtail_length_limit_mm, "pigtail_length_limit_mm",
                           minimum=0.0, strict=True)
    inductance_limit = _number(pigtail_inductance_limit_nh,
                               "pigtail_inductance_limit_nh", minimum=0.0,
                               strict=True)
    flight_termination = categorize_shield_termination(flight)
    sample_termination = categorize_shield_termination(sample)
    findings = []
    result = {
        "flight_termination": flight_termination,
        "sample_termination": sample_termination,
        "sample_pigtail_inductance_nh": None,
        "findings": findings,
    }
    if sample_termination == "unterminated" and flight_termination != "unterminated":
        findings.append(
            "sample-shield-unterminated: flight lands the shield as %s"
            % flight_termination
        )
        return result
    if flight_termination != sample_termination:
        findings.append(
            "shield-termination-mismatch: flight %s against sample %s"
            % (flight_termination, sample_termination)
        )
        return result
    if sample_termination == "pigtail":
        length = float(sample["pigtail_length_mm"])
        diameter = _number(sample.get("pigtail_diameter_mm"),
                           "pigtail_diameter_mm", minimum=0.0, strict=True)
        inductance = pigtail_inductance_nh(length, diameter)
        result["sample_pigtail_inductance_nh"] = inductance
        if not _at_most(length, length_limit):
            findings.append(
                "pigtail-length-exceeded: %.2f mm against %.2f mm"
                % (length, length_limit)
            )
        if not _at_most(inductance, inductance_limit):
            findings.append(
                "pigtail-inductance-exceeded: %.2f nH against %.2f nH"
                % (inductance, inductance_limit)
            )
    return result


def check_exposed_run_length(sample_length_m, required_length_m):
    """Check the exposed harness run against the length the geometry needs."""
    sample = _number(sample_length_m, "sample_length_m", minimum=0.0,
                     strict=True)
    required = _number(required_length_m, "required_length_m", minimum=0.0,
                       strict=True)
    adequate = sample >= required or math.isclose(sample, required,
                                                  rel_tol=REL_TOL)
    findings = []
    if not adequate:
        findings.append(
            "exposed-run-length-short: %.3f m against %.3f m required"
            % (sample, required)
        )
    return {
        "sample_length_m": sample,
        "required_length_m": required,
        "adequate": adequate,
        "findings": findings,
    }


def assess_harness_run(run, tolerance_fraction=DEFAULT_TWIST_TOLERANCE,
                       coverage_allowance_points=DEFAULT_COVERAGE_ALLOWANCE_POINTS):
    """Assess one harness run: twisting, shielding, termination, run length."""
    rec = _mapping(run, "harness run")
    run_id = rec.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("harness run requires a non-empty run_id")
    flight = _mapping(rec.get("flight_build"), "flight_build")
    sample = _mapping(rec.get("sample_build"), "sample_build")
    findings = []
    twist = compare_twisting(flight.get("lay_length_mm"),
                             sample.get("lay_length_mm"), tolerance_fraction)
    findings.extend(twist["findings"])
    shielding = compare_shielding(flight, sample, coverage_allowance_points)
    findings.extend(shielding["findings"])
    termination = compare_termination(
        flight, sample,
        rec.get("pigtail_length_limit_mm", DEFAULT_PIGTAIL_LENGTH_LIMIT_MM),
        rec.get("pigtail_inductance_limit_nh",
                DEFAULT_PIGTAIL_INDUCTANCE_LIMIT_NH),
    )
    findings.extend(termination["findings"])
    length = check_exposed_run_length(sample.get("exposed_length_m"),
                                      rec.get("required_length_m"))
    findings.extend(length["findings"])
    return {
        "run_id": run_id,
        "twisting": twist,
        "shielding": shielding,
        "termination": termination,
        "run_length": length,
        "findings": findings,
        "representative": not findings,
    }


def assess_cable_representativeness(setup):
    """Full clause 5.2.6.6.1 assessment across every harness run in a setup."""
    rec = _mapping(setup, "setup")
    unit_id = rec.get("unit_id")
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("setup requires a non-empty unit_id")
    runs = rec.get("harness_runs")
    if isinstance(runs, dict) or not isinstance(runs, (list, tuple)):
        raise ValueError("harness_runs must be a list of harness runs")
    if not runs:
        raise ValueError("setup must declare at least one harness run")
    tolerance = rec.get("tolerance_fraction", DEFAULT_TWIST_TOLERANCE)
    allowance = rec.get("coverage_allowance_points",
                        DEFAULT_COVERAGE_ALLOWANCE_POINTS)
    results = []
    seen = []
    findings = []
    for run in runs:
        assessed = assess_harness_run(run, tolerance, allowance)
        if assessed["run_id"] in seen:
            raise ValueError(
                "harness_runs repeats run_id %r" % assessed["run_id"]
            )
        seen.append(assessed["run_id"])
        results.append(assessed)
        for finding in assessed["findings"]:
            findings.append("%s: %s" % (assessed["run_id"], finding))
    return {
        "unit_id": unit_id,
        "runs": results,
        "run_count": len(results),
        "findings": findings,
        "representative": not findings,
    }
