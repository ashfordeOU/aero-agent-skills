#!/usr/bin/env python3
"""Finish quality presented by the contact surfaces of a bare solar cell.

Anchor: ECSS-E-ST-20-08C clause 7.5.11. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The qualification examination behind this clause looks at the surface a
contact presents -- the face an interconnect is welded or soldered to,
and the face a bond has to wet. Two unrelated kinds of evidence arrive
under that one heading and neither substitutes for the other:

    a profile trace, reducing the texture to roughness parameters
    an examination of the surface, returning discrete anomalies

A contact can be beautifully smooth and carry a void at the weld site,
and it can be visibly clean and far too rough to wet. So the two are
carried separately, judged separately, and only then combined.

Anomalies are not equal. A stain and a flake off the metallisation are
both anomalies, and only one of them removes contact area. They are
therefore weighted by severity into a demerit score, in addition to the
area they occupy and the size of the largest one, because those three
catch three different failures: many small faults, one large fault, and
a population of severe faults that is small in area.

The trace itself is checked before it is believed. A peak-to-valley
height barely above the mean deviation is not a smooth surface; it is a
trace too short, too filtered or taken on the wrong feature.

Lengths are in millimetres, areas in square millimetres and roughness
in micrometres. Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ANOMALY_SEVERITY_WEIGHTS = {
    "discoloration": 1,
    "staining": 1,
    "scratch": 2,
    "nodule": 3,
    "pit": 3,
    "void": 4,
    "flaking": 5,
}

ANOMALY_KINDS = tuple(sorted(ANOMALY_SEVERITY_WEIGHTS))

DEFAULT_FINISH_POLICY = {
    "maximum_roughness_ra_um": 1.2,
    "maximum_roughness_rz_um": 8.0,
    "minimum_rz_to_ra_ratio": 3.0,
    "minimum_trace_length_mm": 4.0,
    "maximum_single_anomaly_mm2": 0.05,
    "maximum_anomaly_area_fraction": 0.01,
    "maximum_demerit_score": 10.0,
    "marginal_band_fraction": 0.80,
}

GRADE_COMPLIANT = "compliant"
GRADE_MARGINAL = "marginal"
GRADE_NON_COMPLIANT = "non-compliant"

FINISH_GRADES = (GRADE_COMPLIANT, GRADE_MARGINAL, GRADE_NON_COMPLIANT)

FINISH_ACCEPTED = "contact-finish-accepted"
FINISH_REJECTED = "contact-finish-rejected"
EXAMINATION_INADEQUATE = "finish-examination-inadequate"

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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number <= 0.0 or number > 1.0:
        raise ValueError(
            "%s must sit above zero and at most one, got %r" % (name, value)
        )
    return number


def _require_count(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A ratio of two measured lengths, or an area divided by an area, can
    land a few units in the last place either side of a written limit.
    The limit is never relaxed; only the comparison tolerates the
    representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_finish_policy(policy=None):
    """Normalise the declared finish limits, rejecting an unusable set."""
    if policy is None:
        policy = DEFAULT_FINISH_POLICY
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_FINISH_POLICY)
    for key in policy:
        if key not in DEFAULT_FINISH_POLICY:
            raise ValueError("unknown policy key %r" % (key,))
        merged[key] = policy[key]
    ra_limit = _require_positive(
        "maximum_roughness_ra_um", merged["maximum_roughness_ra_um"]
    )
    rz_limit = _require_positive(
        "maximum_roughness_rz_um", merged["maximum_roughness_rz_um"]
    )
    if not rz_limit > ra_limit:
        raise ValueError(
            "maximum_roughness_rz_um %g must sit above maximum_roughness_ra_um %g"
            % (rz_limit, ra_limit)
        )
    ratio_floor = _require_number(
        "minimum_rz_to_ra_ratio", merged["minimum_rz_to_ra_ratio"]
    )
    if ratio_floor < 1.0:
        raise ValueError(
            "minimum_rz_to_ra_ratio must be at least one, got %r" % (ratio_floor,)
        )
    merged["maximum_roughness_ra_um"] = ra_limit
    merged["maximum_roughness_rz_um"] = rz_limit
    merged["minimum_rz_to_ra_ratio"] = ratio_floor
    merged["minimum_trace_length_mm"] = _require_positive(
        "minimum_trace_length_mm", merged["minimum_trace_length_mm"]
    )
    merged["maximum_single_anomaly_mm2"] = _require_positive(
        "maximum_single_anomaly_mm2", merged["maximum_single_anomaly_mm2"]
    )
    merged["maximum_anomaly_area_fraction"] = _require_fraction(
        "maximum_anomaly_area_fraction", merged["maximum_anomaly_area_fraction"]
    )
    merged["maximum_demerit_score"] = _require_positive(
        "maximum_demerit_score", merged["maximum_demerit_score"]
    )
    merged["marginal_band_fraction"] = _require_fraction(
        "marginal_band_fraction", merged["marginal_band_fraction"]
    )
    return merged


def anomaly_severity_weight(kind):
    """Demerit weight carried by one anomaly of this kind."""
    if kind not in ANOMALY_SEVERITY_WEIGHTS:
        raise ValueError(
            "unknown anomaly kind %r; known kinds are %s"
            % (kind, ", ".join(ANOMALY_KINDS))
        )
    return ANOMALY_SEVERITY_WEIGHTS[kind]


def normalise_anomalies(records):
    """Validate the examined anomaly population and return it normalised.

    An anomaly record is a kind, how many of them were seen, and the
    area one of them occupies. A record with no count is an observation
    that was made and found nothing, which is kept rather than dropped
    so the examination shows what it looked for.
    """
    if records is None:
        return ()
    if isinstance(records, dict) or isinstance(records, (str, bytes)):
        raise ValueError("anomalies must be a sequence of anomaly records")
    try:
        items = list(records)
    except TypeError:
        raise ValueError("anomalies must be a sequence of anomaly records")
    normalised = []
    seen = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("anomaly %d must be a mapping, got %r" % (index, item))
        kind = item.get("kind")
        anomaly_severity_weight(kind)
        if kind in seen:
            raise ValueError(
                "anomaly kind %s is recorded twice; combine the counts" % (kind,)
            )
        seen.add(kind)
        count = _require_count("%s count" % kind, item.get("count", 0), 0)
        if count == 0:
            area = _require_number(
                "%s single_area_mm2" % kind, item.get("single_area_mm2", 0.0)
            )
            if area < 0.0:
                raise ValueError("%s single_area_mm2 must not be negative" % (kind,))
        else:
            area = _require_positive(
                "%s single_area_mm2" % kind, item.get("single_area_mm2")
            )
        normalised.append(
            {
                "kind": kind,
                "count": count,
                "single_area_mm2": area,
                "severity_weight": anomaly_severity_weight(kind),
            }
        )
    normalised.sort(key=lambda record: record["kind"])
    return tuple(normalised)


def total_anomaly_area_mm2(anomalies):
    """Contact area taken up by every anomaly found."""
    return sum(
        record["count"] * record["single_area_mm2"]
        for record in normalise_anomalies(anomalies)
    )


def largest_single_anomaly_mm2(anomalies):
    """Area of the single largest anomaly found, zero if none were."""
    present = [
        record["single_area_mm2"]
        for record in normalise_anomalies(anomalies)
        if record["count"] > 0
    ]
    return max(present) if present else 0.0


def anomaly_area_fraction(anomalies, inspected_area_mm2):
    """Share of the examined contact surface the anomalies occupy."""
    area = _require_positive("inspected_area_mm2", inspected_area_mm2)
    total = total_anomaly_area_mm2(anomalies)
    if total > area and not math.isclose(
        total, area, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "anomaly area %g mm2 exceeds the inspected area %g mm2" % (total, area)
        )
    return total / area


def demerit_score(anomalies):
    """Severity-weighted count of the anomaly population.

    Area alone misses a population of small severe faults, and a count
    alone treats a stain as a flake. The weighted sum catches the case
    that neither does.
    """
    return float(
        sum(
            record["count"] * record["severity_weight"]
            for record in normalise_anomalies(anomalies)
        )
    )


def roughness_consistency(ra_um, rz_um):
    """Whether the profile trace is self-consistent before it is believed.

    The mean deviation cannot exceed the peak-to-valley height, and a
    peak-to-valley height only just above it describes a trace that is
    too short, too heavily filtered, or taken somewhere other than the
    contact.
    """
    ra = _require_positive("ra_um", ra_um)
    rz = _require_positive("rz_um", rz_um)
    if rz < ra and not math.isclose(rz, ra, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        raise ValueError(
            "rz_um %g cannot sit below ra_um %g on one trace" % (rz, ra)
        )
    return {"ra_um": ra, "rz_um": rz, "rz_to_ra_ratio": rz / ra}


def trace_adequacy(trace_length_mm, ra_um, rz_um, policy=None):
    """Whether the profile trace can carry a roughness judgement at all."""
    limits = validate_finish_policy(policy)
    length = _require_positive("trace_length_mm", trace_length_mm)
    profile = roughness_consistency(ra_um, rz_um)
    findings = []
    long_enough = _at_least(length, limits["minimum_trace_length_mm"])
    if not long_enough:
        findings.append(
            "profile trace is %.2f mm, %.2f mm needed to carry a roughness figure"
            % (length, limits["minimum_trace_length_mm"])
        )
    consistent = _at_least(
        profile["rz_to_ra_ratio"], limits["minimum_rz_to_ra_ratio"]
    )
    if not consistent:
        findings.append(
            "peak-to-valley height is only %.2f times the mean deviation;"
            " the trace is not describing a real contact surface"
            % (profile["rz_to_ra_ratio"],)
        )
    return {
        "trace_length_mm": length,
        "rz_to_ra_ratio": profile["rz_to_ra_ratio"],
        "adequate": long_enough and consistent,
        "findings": findings,
    }


def _utilisation(value, limit):
    return value / limit


def finish_grade(utilisations, policy=None):
    """Name the finish grade from how much of each limit is used up."""
    limits = validate_finish_policy(policy)
    if not isinstance(utilisations, dict) or not utilisations:
        raise ValueError("utilisations must be a non-empty mapping")
    values = []
    for name in sorted(utilisations):
        values.append(_require_number(name, utilisations[name]))
    if any(not _at_most(value, 1.0) for value in values):
        return GRADE_NON_COMPLIANT
    if any(
        _at_least(value, limits["marginal_band_fraction"]) for value in values
    ):
        return GRADE_MARGINAL
    return GRADE_COMPLIANT


def assess_contact_surface_finish(case, policy=None):
    """Full clause 7.5.11 examination of one bare cell contact surface."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    limits = validate_finish_policy(
        policy if policy is not None else case.get("policy")
    )
    inspected = _require_positive(
        "inspected_area_mm2", case.get("inspected_area_mm2")
    )
    trace = trace_adequacy(
        case.get("trace_length_mm"),
        case.get("roughness_ra_um"),
        case.get("roughness_rz_um"),
        limits,
    )
    anomalies = normalise_anomalies(case.get("anomalies"))
    ra = _require_positive("roughness_ra_um", case.get("roughness_ra_um"))
    rz = _require_positive("roughness_rz_um", case.get("roughness_rz_um"))
    area_fraction = anomaly_area_fraction(anomalies, inspected)
    largest = largest_single_anomaly_mm2(anomalies)
    demerits = demerit_score(anomalies)
    utilisations = {
        "roughness_ra": _utilisation(ra, limits["maximum_roughness_ra_um"]),
        "roughness_rz": _utilisation(rz, limits["maximum_roughness_rz_um"]),
        "largest_anomaly": _utilisation(
            largest, limits["maximum_single_anomaly_mm2"]
        ),
        "anomaly_area_fraction": _utilisation(
            area_fraction, limits["maximum_anomaly_area_fraction"]
        ),
        "demerit_score": _utilisation(demerits, limits["maximum_demerit_score"]),
    }
    grade = finish_grade(utilisations, limits)
    findings = list(trace["findings"])
    if not _at_most(ra, limits["maximum_roughness_ra_um"]):
        findings.append(
            "mean deviation %.2f um exceeds the %.2f um limit"
            % (ra, limits["maximum_roughness_ra_um"])
        )
    if not _at_most(rz, limits["maximum_roughness_rz_um"]):
        findings.append(
            "peak-to-valley height %.2f um exceeds the %.2f um limit"
            % (rz, limits["maximum_roughness_rz_um"])
        )
    if not _at_most(largest, limits["maximum_single_anomaly_mm2"]):
        findings.append(
            "largest anomaly is %.3f mm2, limit %.3f mm2"
            % (largest, limits["maximum_single_anomaly_mm2"])
        )
    if not _at_most(area_fraction, limits["maximum_anomaly_area_fraction"]):
        findings.append(
            "anomalies cover %.2f%% of the contact, limit %.2f%%"
            % (
                area_fraction * 100.0,
                limits["maximum_anomaly_area_fraction"] * 100.0,
            )
        )
    if not _at_most(demerits, limits["maximum_demerit_score"]):
        findings.append(
            "severity-weighted demerit score %.1f exceeds the limit of %.1f"
            % (demerits, limits["maximum_demerit_score"])
        )
    if grade == GRADE_MARGINAL:
        findings.append(
            "finish sits inside every limit with little room; grade is marginal"
        )
    if not trace["adequate"]:
        verdict = EXAMINATION_INADEQUATE
    elif grade == GRADE_NON_COMPLIANT:
        verdict = FINISH_REJECTED
    else:
        verdict = FINISH_ACCEPTED
    return {
        "contact_identifier": case.get("contact_identifier"),
        "trace": trace,
        "roughness_ra_um": ra,
        "roughness_rz_um": rz,
        "anomalies": anomalies,
        "anomaly_kinds_found": tuple(
            record["kind"] for record in anomalies if record["count"] > 0
        ),
        "total_anomaly_area_mm2": total_anomaly_area_mm2(anomalies),
        "largest_single_anomaly_mm2": largest,
        "anomaly_area_fraction": area_fraction,
        "demerit_score": demerits,
        "limit_utilisation": utilisations,
        "finish_grade": grade,
        "accepted": verdict == FINISH_ACCEPTED,
        "verdict": verdict,
        "findings": findings,
    }
