#!/usr/bin/env python3
"""ECSS-E-ST-20-01C clause 9.5.1 -- emission-yield measurement-procedure
documentation audit.

Deterministic, offline, stdlib-only implementation of the clause 9.5.1
floor on a secondary-electron-emission yield measurement procedure: the
minimum set of recorded items, from the normative references at the front
of the document through to the sample description that identifies the
specimen actually placed in front of the beam.

The module categorizes declared procedure entries, checks that each
present item carries enough recorded detail to be repeatable, validates
the reference list and the sample description structurally, and scores
procedure completeness against the mandatory set.

Paraphrase only -- no ECSS text is reproduced. Clause anchor:
ECSS-E-ST-20-01C 9.5.1.
"""

import math

# Mandatory recorded items -> minimum recorded-detail word floor. The floor
# separates a populated item from a bare heading; it is a documentation
# threshold, not an engineering limit.
MANDATORY_ITEMS = {
    "normative-references": 8,
    "measurement-facility-description": 12,
    "electron-gun-parameters": 12,
    "sample-description": 12,
    "sample-preparation": 10,
    "measurement-method": 12,
    "data-reduction": 10,
    "uncertainty-budget": 10,
    "environmental-conditions": 8,
    "record-identification": 6,
}

# Recognized but not required. Present here so their absence never counts
# against completeness and their presence never inflates it.
OPTIONAL_ITEMS = {
    "surface-analysis-record": 6,
    "beam-alignment-record": 6,
    "witness-specimen-record": 6,
}

# Every mandatory item must be present and sufficient.
REQUIRED_COMPLETENESS = 1.0

# Absorbs the representation residue of a ratio of small integers so an
# exactly complete record is never rejected. Not an engineering allowance.
SCORE_TOLERANCE = 1e-9

MANDATORY = "mandatory"
OPTIONAL = "optional"
UNCATEGORIZED = "uncategorized"

SUFFICIENT = "sufficient"
PRESENT_BUT_THIN = "present-but-thin"


def normalize_item_key(raw):
    """Fold a declared item key onto the canonical hyphenated form."""
    if not isinstance(raw, str):
        raise ValueError("procedure item key must be a string, got %r" % (raw,))
    key = raw.strip().lower().replace("_", "-")
    key = "-".join(part for part in key.split() if part)
    while "--" in key:
        key = key.replace("--", "-")
    key = key.strip("-")
    if not key:
        raise ValueError("procedure item key is empty after normalization")
    return key


def categorize_procedure_item(raw):
    """Return (category, canonical_key) for one declared procedure entry."""
    key = normalize_item_key(raw)
    if key in MANDATORY_ITEMS:
        return (MANDATORY, key)
    if key in OPTIONAL_ITEMS:
        return (OPTIONAL, key)
    return (UNCATEGORIZED, key)


def detail_floor(key):
    """Minimum recorded-detail word count for a recognized item key."""
    canonical = normalize_item_key(key)
    if canonical in MANDATORY_ITEMS:
        return MANDATORY_ITEMS[canonical]
    if canonical in OPTIONAL_ITEMS:
        return OPTIONAL_ITEMS[canonical]
    raise ValueError("no detail floor for uncategorized item %r" % (canonical,))


def assess_item_detail(key, detail):
    """Mark a present item sufficient or present-but-thin against its floor."""
    if not isinstance(detail, str):
        raise ValueError(
            "recorded detail for %r must be a string, got %r" % (key, detail)
        )
    floor = detail_floor(key)
    words = len(detail.split())
    if words == 0:
        raise ValueError("recorded detail for %r is blank" % (key,))
    return SUFFICIENT if words >= floor else PRESENT_BUT_THIN


def check_reference_list(references):
    """Validate the normative-reference list; return the findings list."""
    if not isinstance(references, (list, tuple)):
        raise ValueError("references must be a list, got %r" % (references,))
    if len(references) == 0:
        raise ValueError("normative-reference list is empty")
    findings = []
    seen = set()
    for index, entry in enumerate(references):
        if not isinstance(entry, dict):
            raise ValueError("reference[%d] must be a mapping" % index)
        ident = entry.get("id")
        issue = entry.get("issue")
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError("reference[%d] has no identifier" % index)
        ident = ident.strip()
        if issue is None or (isinstance(issue, str) and not issue.strip()):
            findings.append("reference %s carries no issue or date" % ident)
        if ident in seen:
            findings.append("reference %s is listed more than once" % ident)
        seen.add(ident)
    return findings


def check_sample_description(sample):
    """Validate the sample description structurally; return the findings."""
    if not isinstance(sample, dict):
        raise ValueError("sample description must be a mapping, got %r" % (sample,))
    for field in ("material", "batch_identifier", "surface_finish"):
        value = sample.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("sample description field %r is absent or blank" % field)
    thickness = sample.get("thickness_mm")
    if not isinstance(thickness, (int, float)) or isinstance(thickness, bool):
        raise ValueError("sample thickness_mm must be numeric, got %r" % (thickness,))
    if thickness <= 0.0:
        raise ValueError("sample thickness_mm must be positive, got %r" % (thickness,))
    findings = []
    area = sample.get("exposed_area_cm2")
    if area is not None:
        if not isinstance(area, (int, float)) or isinstance(area, bool):
            raise ValueError("exposed_area_cm2 must be numeric, got %r" % (area,))
        if area <= 0.0:
            raise ValueError("exposed_area_cm2 must be positive, got %r" % (area,))
        if area < 0.25:
            findings.append(
                "exposed area %.3f cm2 is below the beam-footprint floor" % area
            )
    return findings


def audit_procedure_record(record):
    """Categorize and depth-check every declared entry in one procedure."""
    if not isinstance(record, dict):
        raise ValueError("procedure record must be a mapping, got %r" % (record,))
    if not record:
        raise ValueError("procedure record declares no items")
    present_mandatory = {}
    present_optional = {}
    thin = []
    uncategorized = []
    for raw_key, detail in record.items():
        category, key = categorize_procedure_item(raw_key)
        if category == UNCATEGORIZED:
            uncategorized.append(key)
            continue
        status = assess_item_detail(key, detail)
        if status == PRESENT_BUT_THIN:
            thin.append(key)
        if category == MANDATORY:
            present_mandatory[key] = status
        else:
            present_optional[key] = status
    missing = sorted(set(MANDATORY_ITEMS) - set(present_mandatory))
    return {
        "present_mandatory": present_mandatory,
        "present_optional": present_optional,
        "missing_mandatory": missing,
        "thin_items": sorted(thin),
        "uncategorized_items": sorted(uncategorized),
    }


def completeness_score(audit):
    """Fraction of mandatory items both present and sufficient."""
    if not isinstance(audit, dict) or "present_mandatory" not in audit:
        raise ValueError("audit mapping is not a procedure audit result")
    satisfied = sum(
        1
        for key, status in audit["present_mandatory"].items()
        if status == SUFFICIENT and key in MANDATORY_ITEMS
    )
    return satisfied / float(len(MANDATORY_ITEMS))


def meets_completeness(score, required=REQUIRED_COMPLETENESS):
    """Compare a completeness score against the floor, absorbing ULP residue."""
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise ValueError("completeness score must be numeric, got %r" % (score,))
    if not 0.0 <= score <= 1.0:
        raise ValueError("completeness score out of range: %r" % (score,))
    if score >= required:
        return True
    return math.isclose(score, required, rel_tol=0.0, abs_tol=SCORE_TOLERANCE)


def evaluate_procedure(record, references, sample):
    """Run the full clause 9.5.1 audit and return the disposition."""
    audit = audit_procedure_record(record)
    reference_findings = check_reference_list(references)
    sample_findings = check_sample_description(sample)
    score = completeness_score(audit)
    findings = []
    for key in audit["missing_mandatory"]:
        findings.append("mandatory item %s is absent from the procedure" % key)
    for key in audit["thin_items"]:
        findings.append("item %s is present but below its recorded-detail floor" % key)
    findings.extend(reference_findings)
    findings.extend(sample_findings)
    compliant = not findings and meets_completeness(score)
    return {
        "completeness_score": score,
        "compliant": compliant,
        "findings": findings,
        "uncategorized_items": audit["uncategorized_items"],
        "audit": audit,
    }
