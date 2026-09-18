#!/usr/bin/env python3
"""Output impedance gain and phase supplied per protection-device class.

Anchor: ECSS-E-ST-20-20C clause 5.2.17.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

What a protection device presents to the load behind it is not a
resistance but a complex output impedance, and the bus designer needs
BOTH parts of it: the magnitude, because that is what turns a load
current step into a voltage excursion at the load terminals, and the
phase, because that is what decides whether the device and the input
filter of the load behind it form a stable loop or an oscillator. A
magnitude curve alone cannot answer the second question, which is why
the clause asks for gain and phase together rather than either one.

The deliverable is therefore a swept dataset per device class, and a
dataset is reviewable only when it is:

    covering        reaching both edges of the frequency band the
                    project specified, not merely sitting inside it
    resolved        carrying enough points per decade, and no single
                    step between adjacent frequencies wide enough to
                    step straight over a resonance
    ordered         ascending in frequency with no repeated point
    bounded         a phase inside the declared bound and a finite,
                    positive magnitude at every point
    complete        one dataset for every class the project declared,
                    with the missing ones named rather than skipped

Magnitudes travel in two units. Ohms are what the data is measured in;
dB-ohm is what the plots are read in, and the conversion is
20*log10(Z). The peak of the magnitude curve and the frequency carrying
it are reported explicitly, because that pair is what a downstream
stability or transient budget is actually built on.

The resolution floor, the largest permitted step between adjacent
frequencies, the phase bound and the peak advisory ceiling are a
declared project policy, not physical constants; a project substitutes
its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

POINT_FIELDS = ("frequency_hz", "magnitude_ohm", "phase_deg")

VERDICT_COMPLETE = "output-impedance-characterisation-complete"
VERDICT_INCOMPLETE = "output-impedance-characterisation-incomplete"

FINDING_BAND_LOW = "sweep-does-not-reach-the-lower-band-edge"
FINDING_BAND_HIGH = "sweep-does-not-reach-the-upper-band-edge"
FINDING_RESOLUTION = "points-per-decade-below-the-policy-floor"
FINDING_STEP = "adjacent-frequency-step-above-the-policy-limit"
FINDING_PHASE = "reported-phase-outside-the-declared-bound"
FINDING_MISSING_CLASS = "no-dataset-reported-for-the-class"

ADVISORY_PEAK = "peak-output-impedance-above-the-advisory-ceiling"
ADVISORY_UNDECLARED = "dataset-reported-for-an-undeclared-class"

DEFAULT_CHARACTERISATION_POLICY = {
    "points_per_decade_floor": 8.0,
    "max_adjacent_frequency_ratio": 1.6,
    "phase_bound_deg": 180.0,
    "peak_magnitude_advisory_ceiling_ohm": 0.5,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Frequency ratios, points-per-decade figures and dB-ohm conversions
    are built from division and from log10, which is not correctly
    rounded and lands differently on different platforms. A point meant
    to sit exactly on a bound can therefore fall a few units in the last
    place the wrong side of it. The bound is never widened; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, bound):
    """value >= bound, absorbing the same representation error."""
    return value >= bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def ohms_to_db_ohm(magnitude_ohm):
    """Magnitude in dB-ohm: twenty times the base-ten log of the ohms."""
    return 20.0 * math.log10(_require_positive("magnitude_ohm", magnitude_ohm))


def db_ohm_to_ohms(magnitude_db_ohm):
    """Inverse of ohms_to_db_ohm."""
    return 10.0 ** (_require_number("magnitude_db_ohm", magnitude_db_ohm) / 20.0)


def validate_characterisation_policy(policy):
    """Check the resolution, step, phase and advisory figures are usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    floor = _require_positive(
        "points_per_decade_floor", policy.get("points_per_decade_floor")
    )
    if floor < 1.0:
        raise ValueError(
            "points_per_decade_floor must be at least one, got %r" % (floor,)
        )
    ratio = _require_positive(
        "max_adjacent_frequency_ratio", policy.get("max_adjacent_frequency_ratio")
    )
    if ratio <= 1.0:
        raise ValueError(
            "max_adjacent_frequency_ratio must exceed one, got %r" % (ratio,)
        )
    phase = _require_positive("phase_bound_deg", policy.get("phase_bound_deg"))
    if phase > 360.0:
        raise ValueError(
            "phase_bound_deg must not exceed a full turn, got %r" % (phase,)
        )
    _require_positive(
        "peak_magnitude_advisory_ceiling_ohm",
        policy.get("peak_magnitude_advisory_ceiling_ohm"),
    )
    return policy


def validate_point(point):
    """Check one swept point carries a frequency, a magnitude and a phase."""
    if not isinstance(point, dict):
        raise ValueError("point must be a mapping, got %r" % (point,))
    missing = [f for f in POINT_FIELDS if f not in point]
    if missing:
        raise ValueError("point is missing fields: %s" % ", ".join(sorted(missing)))
    return {
        "frequency_hz": _require_positive("frequency_hz", point["frequency_hz"]),
        "magnitude_ohm": _require_positive("magnitude_ohm", point["magnitude_ohm"]),
        "phase_deg": _require_number("phase_deg", point["phase_deg"]),
    }


def validate_sweep(points):
    """Normalise a sweep and require strictly ascending, unique frequencies."""
    if isinstance(points, dict) or not hasattr(points, "__iter__"):
        raise ValueError("sweep must be a sequence of points")
    rows = [validate_point(p) for p in points]
    if len(rows) < 2:
        raise ValueError(
            "a sweep needs at least two points to describe a band, got %d" % len(rows)
        )
    for earlier, later in zip(rows, rows[1:]):
        if later["frequency_hz"] < earlier["frequency_hz"]:
            raise ValueError(
                "sweep is not ascending in frequency: %g Hz then %g Hz"
                % (earlier["frequency_hz"], later["frequency_hz"])
            )
        if math.isclose(
            later["frequency_hz"],
            earlier["frequency_hz"],
            rel_tol=_REL_TOL,
            abs_tol=_ABS_TOL,
        ):
            raise ValueError(
                "sweep repeats the frequency %g Hz" % (earlier["frequency_hz"],)
            )
    return tuple(rows)


def decades_spanned(points):
    """Decades between the first and the last frequency of the sweep."""
    rows = validate_sweep(points)
    return math.log10(rows[-1]["frequency_hz"] / rows[0]["frequency_hz"])


def points_per_decade(points):
    """Steps per decade the sweep actually delivers across its own span."""
    rows = validate_sweep(points)
    span = decades_spanned(rows)
    if span <= 0.0:
        raise ValueError("sweep spans no frequency range; nothing to resolve")
    return (len(rows) - 1) / span


def largest_adjacent_ratio(points):
    """Widest single step between two neighbouring frequencies."""
    rows = validate_sweep(points)
    return max(
        later["frequency_hz"] / earlier["frequency_hz"]
        for earlier, later in zip(rows, rows[1:])
    )


def covers_band(points, band_low_hz, band_high_hz):
    """Whether the sweep reaches both edges of the specified band."""
    rows = validate_sweep(points)
    low = _require_positive("band_low_hz", band_low_hz)
    high = _require_positive("band_high_hz", band_high_hz)
    if high <= low:
        raise ValueError(
            "specified band must ascend, got %g Hz .. %g Hz" % (low, high)
        )
    return (
        _at_most(rows[0]["frequency_hz"], low),
        _at_least(rows[-1]["frequency_hz"], high),
    )


def peak_impedance(points):
    """Largest magnitude in the sweep and the frequency carrying it."""
    rows = validate_sweep(points)
    worst = max(rows, key=lambda r: r["magnitude_ohm"])
    return {
        "frequency_hz": worst["frequency_hz"],
        "magnitude_ohm": worst["magnitude_ohm"],
        "magnitude_db_ohm": ohms_to_db_ohm(worst["magnitude_ohm"]),
        "phase_deg": worst["phase_deg"],
    }


def assess_class_sweep(
    class_name,
    points,
    band_low_hz,
    band_high_hz,
    policy=DEFAULT_CHARACTERISATION_POLICY,
):
    """Assess one class dataset for coverage, resolution and bounds."""
    validate_characterisation_policy(policy)
    if not isinstance(class_name, str) or not class_name.strip():
        raise ValueError("class name must be a non-empty string, got %r" % (class_name,))
    rows = validate_sweep(points)
    reaches_low, reaches_high = covers_band(rows, band_low_hz, band_high_hz)
    density = points_per_decade(rows)
    widest = largest_adjacent_ratio(rows)
    peak = peak_impedance(rows)

    floor = float(policy["points_per_decade_floor"])
    step_limit = float(policy["max_adjacent_frequency_ratio"])
    phase_bound = float(policy["phase_bound_deg"])

    resolved = _at_least(density, floor)
    stepped = _at_most(widest, step_limit)
    out_of_bound = [
        r for r in rows if not _at_most(abs(r["phase_deg"]), phase_bound)
    ]

    findings = []
    if not reaches_low:
        findings.append(
            "%s: %s starts at %.6g Hz, above the lower edge %.6g Hz"
            % (FINDING_BAND_LOW, class_name, rows[0]["frequency_hz"], band_low_hz)
        )
    if not reaches_high:
        findings.append(
            "%s: %s stops at %.6g Hz, below the upper edge %.6g Hz"
            % (FINDING_BAND_HIGH, class_name, rows[-1]["frequency_hz"], band_high_hz)
        )
    if not resolved:
        findings.append(
            "%s: %s delivers %.3f points per decade against a floor of %.3f"
            % (FINDING_RESOLUTION, class_name, density, floor)
        )
    if not stepped:
        findings.append(
            "%s: %s steps by a factor %.4f between adjacent frequencies, "
            "against a limit of %.4f" % (FINDING_STEP, class_name, widest, step_limit)
        )
    for r in out_of_bound:
        findings.append(
            "%s: %s reports %.3f deg at %.6g Hz, outside the bound of %.3f deg"
            % (
                FINDING_PHASE,
                class_name,
                r["phase_deg"],
                r["frequency_hz"],
                phase_bound,
            )
        )

    advisories = []
    ceiling = float(policy["peak_magnitude_advisory_ceiling_ohm"])
    if not _at_most(peak["magnitude_ohm"], ceiling):
        advisories.append(
            "%s: %s peaks at %.6g ohm (%.3f dB-ohm) at %.6g Hz, above the "
            "advisory ceiling of %.6g ohm"
            % (
                ADVISORY_PEAK,
                class_name,
                peak["magnitude_ohm"],
                peak["magnitude_db_ohm"],
                peak["frequency_hz"],
                ceiling,
            )
        )

    return {
        "class_name": class_name,
        "point_count": len(rows),
        "first_frequency_hz": rows[0]["frequency_hz"],
        "last_frequency_hz": rows[-1]["frequency_hz"],
        "points_per_decade": density,
        "largest_adjacent_ratio": widest,
        "peak": peak,
        "reaches_lower_edge": reaches_low,
        "reaches_upper_edge": reaches_high,
        "resolution_met": resolved,
        "step_limit_met": stepped,
        "phase_within_bound": not out_of_bound,
        "complete": not findings,
        "findings": findings,
        "advisories": advisories,
    }


def characterise_output_impedance(
    sweeps_by_class,
    declared_classes,
    band_low_hz,
    band_high_hz,
    policy=DEFAULT_CHARACTERISATION_POLICY,
):
    """Full clause 5.2.17.1.1 characterisation with a delivery verdict.

    Every declared class has to arrive with its own gain-and-phase sweep;
    a class with no dataset is a finding in its own right rather than an
    absence the reader is expected to notice.
    """
    validate_characterisation_policy(policy)
    if not isinstance(sweeps_by_class, dict):
        raise ValueError(
            "sweeps must be a mapping of class name to sweep, got %r"
            % (sweeps_by_class,)
        )
    if isinstance(declared_classes, (str, bytes)) or not hasattr(
        declared_classes, "__iter__"
    ):
        raise ValueError("declared_classes must be a sequence of class names")
    declared = [c for c in declared_classes]
    if not declared:
        raise ValueError("no class was declared; there is nothing to characterise")
    for name in declared:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("declared class name must be a non-empty string")
    if len(set(declared)) != len(declared):
        raise ValueError("declared_classes repeats a class name")

    assessments = []
    findings = []
    advisories = []
    for name in declared:
        if name not in sweeps_by_class:
            findings.append(
                "%s: %s was declared but no gain-and-phase sweep arrived"
                % (FINDING_MISSING_CLASS, name)
            )
            continue
        assessment = assess_class_sweep(
            name, sweeps_by_class[name], band_low_hz, band_high_hz, policy
        )
        assessments.append(assessment)
        findings.extend(assessment["findings"])
        advisories.extend(assessment["advisories"])

    for name in sorted(sweeps_by_class):
        if name not in declared:
            advisories.append(
                "%s: a sweep arrived for %s, which is not in the declared "
                "class list" % (ADVISORY_UNDECLARED, name)
            )

    return {
        "verdict": VERDICT_COMPLETE if not findings else VERDICT_INCOMPLETE,
        "assessments": assessments,
        "complete_classes": [a["class_name"] for a in assessments if a["complete"]],
        "missing_classes": [c for c in declared if c not in sweeps_by_class],
        "findings": findings,
        "advisories": advisories,
    }
