#!/usr/bin/env python3
"""Receiving inspection of a delivered lot of threaded fasteners.

Anchor: ECSS-Q-ST-70-46 inspection clause on threaded fasteners. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

Goods-in is the last cheap place to stop a wrong or unverifiable
fastener. Four things are judged and they fail differently:

documents   a missing certificate is a recoverable hold. The lot is
            quarantined and released when the document arrives.
marking     a head mark whose property class disagrees with the order
            is not recoverable; the wrong product was shipped.
dimensions  every toleranced feature is measured on the sample. A
            feature with no reading is a coverage gap, not a pass.
re-test     a sample mechanical re-test is owed when the lot is
            fracture-critical, when a required document is missing, or
            when the marking could not be read. It buys evidence that
            did not arrive.

The sample comes from the lot size and the inspection level together.
The level says how much the source is trusted; the lot size sets the
sample. The defective allowance is taken from the sample drawn, and it
is zero on a fracture-critical lot.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

#: Relative slack on a comparison whose two sides are both computed.
DIMENSION_REL_TOL = 1e-9

CRITICALITIES = ("fracture-critical", "structural", "non-structural")

LEVEL_REDUCED = "reduced"
LEVEL_NORMAL = "normal"
LEVEL_TIGHTENED = "tightened"
INSPECTION_LEVELS = (LEVEL_REDUCED, LEVEL_NORMAL, LEVEL_TIGHTENED)

DOC_CONFORMITY = "certificate-of-conformity"
DOC_DIMENSIONAL = "dimensional-inspection-report"
DOC_MATERIAL = "material-certificate"
DOC_HEAT_TREATMENT = "heat-treatment-record"
DOC_MECHANICAL = "mechanical-test-report"
DOC_TRACEABILITY = "lot-traceability-record"
DOC_COATING = "coating-process-record"

DISPOSITION_ACCEPT = "lot-released-to-stores"
DISPOSITION_QUARANTINE = "quarantine-pending-documentation"
DISPOSITION_RETEST = "sample-mechanical-retest-owed"
DISPOSITION_REJECT = "lot-rejected"

#: Sample size by lot-size band and inspection level. Bands are
#: inclusive upper bounds; the last band catches everything above.
_SAMPLE_TABLE = (
    (8, {LEVEL_REDUCED: 2, LEVEL_NORMAL: 3, LEVEL_TIGHTENED: 5}),
    (25, {LEVEL_REDUCED: 3, LEVEL_NORMAL: 5, LEVEL_TIGHTENED: 8}),
    (90, {LEVEL_REDUCED: 5, LEVEL_NORMAL: 8, LEVEL_TIGHTENED: 13}),
    (280, {LEVEL_REDUCED: 8, LEVEL_NORMAL: 13, LEVEL_TIGHTENED: 20}),
    (1200, {LEVEL_REDUCED: 13, LEVEL_NORMAL: 20, LEVEL_TIGHTENED: 32}),
    (10000, {LEVEL_REDUCED: 20, LEVEL_NORMAL: 32, LEVEL_TIGHTENED: 50}),
    (None, {LEVEL_REDUCED: 32, LEVEL_NORMAL: 50, LEVEL_TIGHTENED: 80}),
)

_DOCUMENTS_BY_CRITICALITY = {
    "non-structural": (DOC_CONFORMITY, DOC_DIMENSIONAL),
    "structural": (
        DOC_CONFORMITY,
        DOC_DIMENSIONAL,
        DOC_MATERIAL,
        DOC_HEAT_TREATMENT,
        DOC_MECHANICAL,
    ),
    "fracture-critical": (
        DOC_CONFORMITY,
        DOC_DIMENSIONAL,
        DOC_MATERIAL,
        DOC_HEAT_TREATMENT,
        DOC_MECHANICAL,
        DOC_TRACEABILITY,
        DOC_COATING,
    ),
}

#: Defectives tolerated per hundred sampled, by criticality.
_ALLOWANCE_PER_HUNDRED = {
    "fracture-critical": 0,
    "structural": 5,
    "non-structural": 15,
}


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return float(value)


def _at_least(value, bound, rel_tol=DIMENSION_REL_TOL):
    return value >= bound - abs(bound) * rel_tol


def _at_most(value, bound, rel_tol=DIMENSION_REL_TOL):
    return value <= bound + abs(bound) * rel_tol


def sample_size(lot_size, inspection_level=LEVEL_NORMAL):
    """Parts drawn from the lot, from its size and the trust level."""
    lot = _require_count("lot_size", lot_size, minimum=1)
    level = _require_choice("inspection_level", inspection_level, INSPECTION_LEVELS)
    for upper, row in _SAMPLE_TABLE:
        if upper is None or lot <= upper:
            return min(lot, row[level])
    raise ValueError("lot_size %d could not be placed in the sample table" % lot)


def acceptance_number(lot_size, criticality, inspection_level=LEVEL_NORMAL):
    """Non-conforming parts the sample may carry and still be released."""
    _require_choice("criticality", criticality, CRITICALITIES)
    sample = sample_size(lot_size, inspection_level)
    return (sample * _ALLOWANCE_PER_HUNDRED[criticality]) // 100


def required_documents(criticality):
    """Certificates and records the delivery has to carry."""
    _require_choice("criticality", criticality, CRITICALITIES)
    return list(_DOCUMENTS_BY_CRITICALITY[criticality])


def document_findings(criticality, documents_present):
    """Documents the criticality demands that the delivery did not carry."""
    if isinstance(documents_present, (str, dict)) or not isinstance(
        documents_present, (list, tuple, set)
    ):
        raise ValueError(
            "documents_present must be a sequence of document names, got %r"
            % (documents_present,)
        )
    required = required_documents(criticality)
    present = set(documents_present)
    missing = [doc for doc in required if doc not in present]
    findings = []
    if missing:
        findings.append(
            "%d required document(s) did not arrive with the lot: %s"
            % (len(missing), ", ".join(missing))
        )
    return {
        "required": required,
        "missing": missing,
        "complete": not missing,
        "findings": findings,
    }


def marking_verdict(marking, ordered_class, criticality):
    """Read the head marking against the order and the traceability need."""
    _require_choice("criticality", criticality, CRITICALITIES)
    if not isinstance(ordered_class, str) or not ordered_class:
        raise ValueError(
            "ordered_class must be a non-empty property class, got %r"
            % (ordered_class,)
        )
    if marking is None:
        return {
            "readable": False,
            "class_agrees": False,
            "conforming": False,
            "findings": ["the head marking could not be read"],
        }
    if not isinstance(marking, dict):
        raise ValueError("marking must be a mapping or None, got %r" % (marking,))
    marked_class = marking.get("property_class")
    manufacturer = marking.get("manufacturer_id")
    lot_code = marking.get("lot_code")
    findings = []
    class_agrees = marked_class == ordered_class
    if not class_agrees:
        findings.append(
            "the head is marked %r but %r was ordered; the box holds a "
            "different product" % (marked_class, ordered_class)
        )
    if not manufacturer:
        findings.append("no manufacturer identifier is marked on the head")
    if criticality == "fracture-critical" and not lot_code:
        findings.append(
            "a fracture-critical lot must carry its lot code on the part"
        )
    return {
        "readable": True,
        "class_agrees": class_agrees,
        "conforming": not findings,
        "findings": findings,
    }


def dimensional_verdict(measurements, tolerances):
    """Judge each measured feature and name the ones never measured."""
    if not isinstance(tolerances, dict) or not tolerances:
        raise ValueError(
            "tolerances must be a non-empty mapping of feature to band, got %r"
            % (tolerances,)
        )
    if not isinstance(measurements, dict):
        raise ValueError(
            "measurements must be a mapping of feature to value, got %r"
            % (measurements,)
        )
    out_of_tolerance = []
    unmeasured = []
    findings = []
    for feature in sorted(tolerances):
        band = tolerances[feature]
        if (
            not isinstance(band, (list, tuple))
            or len(band) != 3
        ):
            raise ValueError(
                "tolerance for %s must be (nominal, minus, plus), got %r"
                % (feature, band)
            )
        nominal = _require_number("%s nominal" % feature, band[0])
        minus = _require_number("%s minus" % feature, band[1])
        plus = _require_number("%s plus" % feature, band[2])
        if minus < 0.0 or plus < 0.0:
            raise ValueError(
                "tolerance limits for %s are magnitudes and cannot be "
                "negative, got %r" % (feature, band)
            )
        if feature not in measurements:
            unmeasured.append(feature)
            continue
        value = _require_number(feature, measurements[feature])
        low = nominal - minus
        high = nominal + plus
        if not (_at_least(value, low) and _at_most(value, high)):
            out_of_tolerance.append(feature)
            findings.append(
                "%s measured %.4f, outside %.4f..%.4f" % (feature, value, low, high)
            )
    extra = sorted(set(measurements) - set(tolerances))
    if unmeasured:
        findings.append(
            "%d toleranced feature(s) were never measured on the sample: %s"
            % (len(unmeasured), ", ".join(unmeasured))
        )
    if extra:
        findings.append(
            "readings recorded for feature(s) the drawing does not tolerance: "
            "%s" % ", ".join(extra)
        )
    return {
        "out_of_tolerance": out_of_tolerance,
        "unmeasured": unmeasured,
        "unexpected_features": extra,
        "conforming": not out_of_tolerance and not unmeasured,
        "findings": findings,
    }


def retest_required(criticality, documents_missing, marking_readable):
    """Whether a sample mechanical re-test is owed, and why."""
    _require_choice("criticality", criticality, CRITICALITIES)
    reasons = []
    if criticality == "fracture-critical":
        reasons.append("the lot is fracture-critical")
    if documents_missing:
        reasons.append("a required document did not arrive")
    if not marking_readable:
        reasons.append("the head marking could not be read")
    return {"required": bool(reasons), "reasons": reasons}


def assess_receiving(case):
    """One disposition for a delivered lot, in order of severity."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    criticality = _require_choice(
        "criticality", case.get("criticality"), CRITICALITIES
    )
    lot = _require_count("lot_size", case.get("lot_size"), minimum=1)
    level = _require_choice(
        "inspection_level", case.get("inspection_level", LEVEL_NORMAL),
        INSPECTION_LEVELS,
    )
    sample = sample_size(lot, level)
    allowance = acceptance_number(lot, criticality, level)

    documents = document_findings(criticality, case.get("documents_present", ()))
    marking = marking_verdict(
        case.get("marking"), case.get("ordered_class"), criticality
    )
    dimensions = dimensional_verdict(
        case.get("measurements", {}), case.get("tolerances")
    )

    non_conforming = _require_count(
        "non_conforming_parts", case.get("non_conforming_parts", 0)
    )
    if non_conforming > sample:
        raise ValueError(
            "non_conforming_parts %d exceeds the sample of %d parts"
            % (non_conforming, sample)
        )

    retest = retest_required(
        criticality, bool(documents["missing"]), marking["readable"]
    )
    retest_done = bool(case.get("retest_performed", False))

    findings = []
    findings.extend(documents["findings"])
    findings.extend(marking["findings"])
    findings.extend(dimensions["findings"])
    if non_conforming > allowance:
        findings.append(
            "%d non-conforming part(s) in a sample of %d exceeds the "
            "allowance of %d for a %s lot"
            % (non_conforming, sample, allowance, criticality)
        )
    if retest["required"] and not retest_done:
        findings.append(
            "a sample mechanical re-test is owed because %s"
            % "; ".join(retest["reasons"])
        )

    # A marking that was read and disagrees with the order means a
    # different product arrived. A marking that could not be read is a
    # missing-evidence case and is answered by the re-test, not a reject.
    wrong_product = marking["readable"] and not marking["class_agrees"]
    if wrong_product or non_conforming > allowance or dimensions["out_of_tolerance"]:
        disposition = DISPOSITION_REJECT
    elif documents["missing"]:
        disposition = DISPOSITION_QUARANTINE
    elif retest["required"] and not retest_done:
        disposition = DISPOSITION_RETEST
    elif (
        marking["readable"] and not marking["conforming"]
    ) or not dimensions["conforming"]:
        # A mark that was read but is incomplete, or a sample that left a
        # toleranced feature unmeasured, is a recoverable hold. An
        # unreadable mark is not judged here: the re-test above answers it.
        disposition = DISPOSITION_QUARANTINE
    else:
        disposition = DISPOSITION_ACCEPT

    return {
        "criticality": criticality,
        "lot_size": lot,
        "inspection_level": level,
        "sample_size": sample,
        "acceptance_number": allowance,
        "non_conforming_parts": non_conforming,
        "documents": documents,
        "marking": marking,
        "dimensions": dimensions,
        "retest": retest,
        "retest_performed": retest_done,
        "findings": findings,
        "disposition": disposition,
    }
