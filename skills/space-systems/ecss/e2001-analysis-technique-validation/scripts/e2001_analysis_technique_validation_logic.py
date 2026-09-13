#!/usr/bin/env python3
"""Validation of a multipaction analysis technique and its software.

Anchor: ECSS-E-ST-20-01C clause 5.3.2.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An analysis technique -- the theory plus the software that implements it
-- may only substantiate a multipaction result once it has been shown to
be trustworthy over the region it is applied in. Two routes are open:

demonstrable-heritage
    the same tool build has already predicted a comparable configuration
    whose hardware was afterwards verified by a multipaction-test, so
    the prediction has been confronted with reality at least once;

measured-correlation
    the tool is run against a set of configurations whose breakdown
    levels were measured, and every predicted level agrees with the
    measured level inside a declared agreement criterion.

Either route validates the technique only over the region its evidence
actually spans. The evidence therefore defines a validated applicability
envelope -- a frequency-gap-product range plus the geometry families and
electrode materials it touched -- and an analysis case outside that
envelope is not covered by the validation.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

HERITAGE = "demonstrable-heritage"
MEASURED_CORRELATION = "measured-correlation"
EVIDENCE_ROUTES = (HERITAGE, MEASURED_CORRELATION)

THEORY_BASES = (
    "parallel-plate-two-surface",
    "single-surface-resonant",
    "particle-in-cell",
    "statistical-electron-tracking",
)

MIN_COMPARISON_POINTS = 3
DEFAULT_AGREEMENT_CRITERION_DB = 1.0

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A deviation in decibel is a difference of logarithms, so a point that
    sits exactly on the agreement criterion can land a few units in the
    last place above it. The criterion itself is never widened; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def prediction_deviation_db(predicted_power_w, measured_power_w):
    """Signed deviation of a predicted breakdown level from the measured one."""
    predicted = _require_positive("predicted_power_w", predicted_power_w)
    measured = _require_positive("measured_power_w", measured_power_w)
    return 10.0 * math.log10(predicted / measured)


def frequency_gap_product_ghz_mm(frequency_hz, gap_m):
    """Frequency-gap-product in GHz.mm, the scaling coordinate of the envelope."""
    frequency = _require_positive("frequency_hz", frequency_hz)
    gap = _require_positive("gap_m", gap_m)
    return (frequency / 1.0e9) * (gap * 1.0e3)


def categorize_evidence(record):
    """Return the validation route an evidence record belongs to."""
    if not isinstance(record, dict):
        raise ValueError("evidence record must be a mapping, got %r" % (record,))
    route = record.get("route")
    if route not in EVIDENCE_ROUTES:
        raise ValueError(
            "evidence route must be one of %s, got %r"
            % (", ".join(EVIDENCE_ROUTES), route)
        )
    return route


def tool_build_is_covered(tool_version, technique):
    """True when an evidence build is the technique build or a declared ancestor."""
    version = _require_text("tool_version", tool_version)
    if not isinstance(technique, dict):
        raise ValueError("technique must be a mapping, got %r" % (technique,))
    current = _require_text("technique version", technique.get("version"))
    if version == current:
        return True
    lineage = technique.get("version_lineage", ())
    if not isinstance(lineage, (list, tuple)):
        raise ValueError("technique version_lineage must be a list or tuple")
    return version in [str(item) for item in lineage]


def assess_heritage_evidence(record, technique):
    """Check one heritage record: same build, comparable case, verified by test."""
    if categorize_evidence(record) != HERITAGE:
        raise ValueError("record is not a %s record" % HERITAGE)
    findings = []
    prior = record.get("prior_application")
    if not isinstance(prior, str) or not prior.strip():
        findings.append("heritage record names no prior application")
    if not tool_build_is_covered(record.get("tool_version"), technique):
        findings.append(
            "heritage build %r is neither the technique build nor a declared ancestor"
            % (record.get("tool_version"),)
        )
    if record.get("verified_by_test") is not True:
        findings.append(
            "heritage case was never confronted with a multipaction-test result"
        )
    geometry = record.get("geometry_family")
    if not isinstance(geometry, str) or not geometry.strip():
        findings.append("heritage record names no geometry family")
    material = record.get("electrode_material")
    if not isinstance(material, str) or not material.strip():
        findings.append("heritage record names no electrode material")
    product = frequency_gap_product_ghz_mm(
        record.get("frequency_hz"), record.get("gap_m")
    )
    return {
        "route": HERITAGE,
        "accepted": not findings,
        "findings": findings,
        "frequency_gap_products": (product,),
        "geometry_family": geometry if isinstance(geometry, str) else None,
        "electrode_material": material if isinstance(material, str) else None,
        "worst_deviation_db": None,
    }


def assess_correlation_evidence(record, criterion_db=DEFAULT_AGREEMENT_CRITERION_DB):
    """Check one measured-correlation record against the agreement criterion."""
    if categorize_evidence(record) != MEASURED_CORRELATION:
        raise ValueError("record is not a %s record" % MEASURED_CORRELATION)
    criterion = _require_positive("criterion_db", criterion_db)
    points = record.get("comparison_points")
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("correlation record needs a non-empty comparison_points list")
    findings = []
    products = []
    deviations = []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError("comparison point %d must be a mapping" % index)
        missing = {
            "frequency_hz",
            "gap_m",
            "predicted_breakdown_w",
            "measured_breakdown_w",
        } - set(point)
        if missing:
            raise ValueError(
                "comparison point %d missing key(s): %s"
                % (index, ", ".join(sorted(missing)))
            )
        products.append(
            frequency_gap_product_ghz_mm(point["frequency_hz"], point["gap_m"])
        )
        deviation = prediction_deviation_db(
            point["predicted_breakdown_w"], point["measured_breakdown_w"]
        )
        deviations.append(deviation)
        if not _at_most(abs(deviation), criterion):
            findings.append(
                "comparison point %d deviates %.3f dB, outside the %.3f dB criterion"
                % (index, deviation, criterion)
            )
    if len(points) < MIN_COMPARISON_POINTS:
        findings.append(
            "correlation rests on %d comparison point(s), fewer than the %d required"
            % (len(points), MIN_COMPARISON_POINTS)
        )
    geometry = record.get("geometry_family")
    material = record.get("electrode_material")
    if not isinstance(geometry, str) or not geometry.strip():
        findings.append("correlation record names no geometry family")
    if not isinstance(material, str) or not material.strip():
        findings.append("correlation record names no electrode material")
    worst = max(deviations, key=abs)
    return {
        "route": MEASURED_CORRELATION,
        "accepted": not findings,
        "findings": findings,
        "frequency_gap_products": tuple(products),
        "geometry_family": geometry if isinstance(geometry, str) else None,
        "electrode_material": material if isinstance(material, str) else None,
        "worst_deviation_db": worst,
        "mean_deviation_db": sum(deviations) / len(deviations),
    }


def validated_envelope(assessments):
    """Applicability envelope spanned by the accepted evidence."""
    if not isinstance(assessments, (list, tuple)):
        raise ValueError("assessments must be a list or tuple")
    accepted = [a for a in assessments if a.get("accepted")]
    if not accepted:
        return None
    products = []
    families = set()
    materials = set()
    for item in accepted:
        products.extend(item["frequency_gap_products"])
        if item.get("geometry_family"):
            families.add(item["geometry_family"])
        if item.get("electrode_material"):
            materials.add(item["electrode_material"])
    return {
        "frequency_gap_product_min": min(products),
        "frequency_gap_product_max": max(products),
        "geometry_families": tuple(sorted(families)),
        "electrode_materials": tuple(sorted(materials)),
        "routes": tuple(sorted({item["route"] for item in accepted})),
    }


def covers_analysis_case(envelope, case):
    """Decide whether one analysis case falls inside the validated envelope."""
    if envelope is None:
        return {"covered": False, "reasons": ["technique carries no accepted evidence"]}
    if not isinstance(case, dict):
        raise ValueError("analysis case must be a mapping, got %r" % (case,))
    product = frequency_gap_product_ghz_mm(case.get("frequency_hz"), case.get("gap_m"))
    reasons = []
    if not _at_least(product, envelope["frequency_gap_product_min"]):
        reasons.append(
            "frequency-gap-product %.4f GHz.mm is below the validated %.4f GHz.mm"
            % (product, envelope["frequency_gap_product_min"])
        )
    if not _at_most(product, envelope["frequency_gap_product_max"]):
        reasons.append(
            "frequency-gap-product %.4f GHz.mm is above the validated %.4f GHz.mm"
            % (product, envelope["frequency_gap_product_max"])
        )
    family = _require_text("case geometry_family", case.get("geometry_family"))
    if family not in envelope["geometry_families"]:
        reasons.append("geometry family %r is outside the validated evidence" % family)
    material = _require_text("case electrode_material", case.get("electrode_material"))
    if material not in envelope["electrode_materials"]:
        reasons.append("electrode material %r is outside the validated evidence" % material)
    return {
        "covered": not reasons,
        "frequency_gap_product_ghz_mm": product,
        "reasons": reasons,
    }


def validate_analysis_technique(
    technique,
    evidence,
    analysis_cases=(),
    criterion_db=DEFAULT_AGREEMENT_CRITERION_DB,
):
    """Run the full clause 5.3.2.4 validation and return a verdict."""
    if not isinstance(technique, dict):
        raise ValueError("technique must be a mapping, got %r" % (technique,))
    _require_text("technique name", technique.get("name"))
    _require_text("technique version", technique.get("version"))
    basis = technique.get("theory_basis")
    if basis not in THEORY_BASES:
        raise ValueError(
            "theory_basis must be one of %s, got %r" % (", ".join(THEORY_BASES), basis)
        )
    if not isinstance(evidence, (list, tuple)) or not evidence:
        raise ValueError("evidence must be a non-empty list of records")
    if not isinstance(analysis_cases, (list, tuple)):
        raise ValueError("analysis_cases must be a list or tuple")
    assessments = []
    for record in evidence:
        if categorize_evidence(record) == HERITAGE:
            assessments.append(assess_heritage_evidence(record, technique))
        else:
            assessments.append(assess_correlation_evidence(record, criterion_db))
    envelope = validated_envelope(assessments)
    findings = []
    for index, item in enumerate(assessments):
        for reason in item["findings"]:
            findings.append("evidence %d (%s): %s" % (index, item["route"], reason))
    coverage = []
    for case in analysis_cases:
        result = covers_analysis_case(envelope, case)
        coverage.append(result)
        for reason in result["reasons"]:
            findings.append("analysis case outside the validated envelope: %s" % reason)
    if envelope is None:
        verdict = "not-validated"
    elif any(not item["covered"] for item in coverage):
        verdict = "validated-restricted-envelope"
    else:
        verdict = "validated"
    return {
        "technique": technique.get("name"),
        "version": technique.get("version"),
        "theory_basis": basis,
        "assessments": assessments,
        "accepted_routes": envelope["routes"] if envelope else (),
        "envelope": envelope,
        "coverage": coverage,
        "verdict": verdict,
        "usable_for_substantiation": verdict == "validated",
        "findings": findings,
    }
