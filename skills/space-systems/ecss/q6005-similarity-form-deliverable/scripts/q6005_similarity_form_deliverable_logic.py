"""Similarity form deliverable: what a likeness claim has to record.

Anchor: ECSS-Q-ST-60-05C Annex C -- the form filed when a hybrid circuit is
offered for a reduced approval programme on documented likeness to a circuit
that already holds an approval, and the entries that form has to record.
Paraphrased into an implementable record-integrity procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Check the reference identity block: the candidate and the reference
   circuit, the reference's approval reference and recorded status, the two
   quality levels, and who filed the claim and when.
2. Confirm a comparison row exists for every attribute the form must cover,
   and refuse the same attribute written twice.
3. Test each declared same-or-differs verdict against the two values written
   beside it, so a row asserting likeness over two different values is caught
   rather than believed.
4. Demand a justification and an impact statement on every divergent row, and
   count the divergences left unsupported.
5. Score the documented evidence the record actually carries against the
   obligations the claim creates, and return a record verdict with findings.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "MANDATED_IDENTITY_FIELDS",
    "MANDATED_ATTRIBUTES",
    "APPROVAL_STATUS_VOCABULARY",
    "CURRENT_APPROVAL_STATUS",
    "normalise_text",
    "validate_identity_block",
    "normalise_row",
    "derived_verdict",
    "normalise_rows",
    "missing_attribute_rows",
    "row_findings",
    "unsupported_divergences",
    "documented_evidence_ratio",
    "assess_similarity_form",
]

# The evidence ratio is a quotient of counts; an exact 1.0 can land a few
# units in the last place low. Absorb that here, not by rounding the ratio.
RATIO_TOLERANCE = 1e-12

MANDATED_IDENTITY_FIELDS = (
    "candidate_designation",
    "reference_designation",
    "reference_approval_reference",
    "reference_approval_status",
    "reference_quality_level",
    "candidate_quality_level",
    "claim_prepared_by",
    "claim_date",
)

# Every one of these owes a comparison row, whether it differs or not.
MANDATED_ATTRIBUTES = (
    "circuit_function",
    "substrate_material",
    "substrate_metallization",
    "die_attach_process",
    "wire_bond_process",
    "package_and_sealing",
    "passive_element_technology",
    "screening_sequence",
    "manufacturing_line",
    "operating_temperature_range",
)

APPROVAL_STATUS_VOCABULARY = (
    "approved",
    "approval_pending",
    "approval_lapsed",
    "approval_withdrawn",
)

CURRENT_APPROVAL_STATUS = "approved"

_VERDICTS = ("same", "differs")


def normalise_text(value, label):
    """Return a recorded entry as stripped text ('' when nothing is written)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        raise ValueError("%s must be recorded as text, not a boolean" % label)
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
        return str(value)
    if isinstance(value, str):
        return value.strip()
    raise ValueError("%s must be recorded as text, got %s" % (label, type(value).__name__))


def _key(value):
    """Return the comparison key of a recorded value."""
    return " ".join(value.lower().replace("-", " ").split())


def validate_identity_block(block):
    """Return the identity block findings: absent entries, blank entries, status."""
    if not isinstance(block, dict):
        raise ValueError("identity block must be a mapping")
    recorded = {}
    for name, value in block.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("identity field names must be non-empty strings")
        key = name.strip().lower().replace("-", "_").replace(" ", "_")
        if key in recorded:
            raise ValueError("identity field '%s' is recorded twice" % key)
        recorded[key] = normalise_text(value, key)
    absent = tuple(name for name in MANDATED_IDENTITY_FIELDS if name not in recorded)
    blank = tuple(
        name
        for name in MANDATED_IDENTITY_FIELDS
        if name in recorded and recorded[name] == ""
    )
    status = _key(recorded.get("reference_approval_status", "")).replace(" ", "_")
    status_known = status in APPROVAL_STATUS_VOCABULARY
    return {
        "recorded": recorded,
        "absent_fields": absent,
        "blank_fields": blank,
        "approval_status": status,
        "approval_status_known": status_known,
        "reference_currently_approved": status == CURRENT_APPROVAL_STATUS,
    }


def normalise_row(row, index=0):
    """Return one comparison row in canonical form, refusing a malformed one."""
    if not isinstance(row, dict):
        raise ValueError("comparison row %d must be a mapping" % index)
    for key in ("attribute", "candidate_value", "reference_value"):
        if key not in row:
            raise ValueError("comparison row %d must carry '%s'" % (index, key))
    attribute = normalise_text(row["attribute"], "row %d attribute" % index)
    attribute = attribute.lower().replace("-", "_").replace(" ", "_")
    if not attribute:
        raise ValueError("comparison row %d has a blank attribute" % index)
    declared = row.get("declared_verdict")
    if declared is None:
        declared = ""
    declared = normalise_text(declared, "row %d declared verdict" % index).lower()
    if declared and declared not in _VERDICTS:
        raise ValueError(
            "comparison row %d declares an unrecognised verdict %r" % (index, declared)
        )
    return {
        "attribute": attribute,
        "candidate_value": normalise_text(row["candidate_value"],
                                          "row %d candidate value" % index),
        "reference_value": normalise_text(row["reference_value"],
                                          "row %d reference value" % index),
        "declared_verdict": declared,
        "justification": normalise_text(row.get("justification"),
                                        "row %d justification" % index),
        "impact_statement": normalise_text(row.get("impact_statement"),
                                           "row %d impact statement" % index),
    }


def derived_verdict(candidate_value, reference_value):
    """Return the verdict the two recorded values actually support."""
    if not isinstance(candidate_value, str) or not isinstance(reference_value, str):
        raise ValueError("recorded values must be strings")
    if not candidate_value.strip() or not reference_value.strip():
        raise ValueError("a verdict cannot be derived from a blank value")
    return "same" if _key(candidate_value) == _key(reference_value) else "differs"


def normalise_rows(rows):
    """Return the comparison rows in canonical form, refusing a repeated attribute."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("rows must be a sequence of comparison rows")
    result = []
    seen = set()
    for index, row in enumerate(rows):
        record = normalise_row(row, index)
        if record["attribute"] in seen:
            raise ValueError("attribute '%s' has two comparison rows" % record["attribute"])
        seen.add(record["attribute"])
        result.append(record)
    return result


def missing_attribute_rows(rows):
    """Return the mandated attributes with no comparison row."""
    present = {record["attribute"] for record in rows}
    return tuple(name for name in MANDATED_ATTRIBUTES if name not in present)


def row_findings(record):
    """Return the findings one canonical comparison row raises."""
    findings = []
    blank_value = not record["candidate_value"] or not record["reference_value"]
    if blank_value:
        findings.append(
            "row '%s' leaves a compared value blank, so no verdict is supportable"
            % record["attribute"]
        )
        effective = record["declared_verdict"] or "differs"
    else:
        supported = derived_verdict(record["candidate_value"], record["reference_value"])
        effective = record["declared_verdict"] or supported
        if record["declared_verdict"] and record["declared_verdict"] != supported:
            findings.append(
                "row '%s' declares '%s' but the recorded values support '%s'"
                % (record["attribute"], record["declared_verdict"], supported)
            )
        if not record["declared_verdict"]:
            findings.append(
                "row '%s' records no verdict; the values were read as '%s'"
                % (record["attribute"], supported)
            )
    if effective == "differs":
        if not record["justification"]:
            findings.append("divergent row '%s' carries no justification"
                            % record["attribute"])
        if not record["impact_statement"]:
            findings.append("divergent row '%s' carries no impact statement"
                            % record["attribute"])
    return {"effective_verdict": effective, "findings": findings}


def unsupported_divergences(rows):
    """Return the divergent attributes lacking a justification or an impact statement."""
    unsupported = []
    for record in rows:
        outcome = row_findings(record)
        if outcome["effective_verdict"] != "differs":
            continue
        if not record["justification"] or not record["impact_statement"]:
            unsupported.append(record["attribute"])
    return tuple(unsupported)


def documented_evidence_ratio(rows):
    """Return the fraction of the record obligations the claim actually meets."""
    total = len(MANDATED_ATTRIBUTES)
    met = 0
    by_attribute = {record["attribute"]: record for record in rows}
    for name in MANDATED_ATTRIBUTES:
        if name in by_attribute:
            met += 1
    for name in MANDATED_ATTRIBUTES:
        record = by_attribute.get(name)
        if record is None:
            continue
        total += 1
        outcome = row_findings(record)
        blank_value = not record["candidate_value"] or not record["reference_value"]
        consistent = (
            not blank_value
            and record["declared_verdict"]
            and record["declared_verdict"]
            == derived_verdict(record["candidate_value"], record["reference_value"])
        )
        if consistent:
            met += 1
        if outcome["effective_verdict"] == "differs":
            total += 2
            if record["justification"]:
                met += 1
            if record["impact_statement"]:
                met += 1
    if total == 0:
        return 1.0
    return met / total


def assess_similarity_form(form):
    """Judge a filed similarity form against what Annex C requires it to record.

    form keys: identity (mapping), rows (sequence of comparison rows).
    """
    if not isinstance(form, dict):
        raise ValueError("form must be a mapping")
    for key in ("identity", "rows"):
        if key not in form:
            raise ValueError("form missing required key '%s'" % key)
    identity = validate_identity_block(form["identity"])
    rows = normalise_rows(form["rows"])
    absent_rows = missing_attribute_rows(rows)
    known = set(MANDATED_ATTRIBUTES)
    extra_rows = tuple(
        sorted(record["attribute"] for record in rows if record["attribute"] not in known)
    )
    ratio = documented_evidence_ratio(rows)
    complete = math.isclose(ratio, 1.0, rel_tol=0.0, abs_tol=RATIO_TOLERANCE)

    findings = []
    for name in identity["absent_fields"]:
        findings.append("identity entry '%s' is absent from the form" % name)
    for name in identity["blank_fields"]:
        findings.append("identity entry '%s' is recorded blank" % name)
    if identity["recorded"].get("reference_approval_status") and not identity[
        "approval_status_known"
    ]:
        findings.append(
            "reference approval status '%s' is outside the recognised vocabulary"
            % identity["approval_status"]
        )
    elif identity["approval_status_known"] and not identity["reference_currently_approved"]:
        findings.append(
            "reference approval status is recorded as '%s', so the record cannot "
            "carry a likeness claim as filed" % identity["approval_status"]
        )
    for name in absent_rows:
        findings.append("no comparison row is written for attribute '%s'" % name)
    for record in rows:
        findings.extend(row_findings(record)["findings"])

    unsupported = unsupported_divergences(rows)
    if findings:
        verdict = "record-incomplete"
    elif extra_rows:
        verdict = "record-complete-with-remarks"
    else:
        verdict = "record-complete"

    return {
        "identity": identity,
        "rows": rows,
        "missing_rows": absent_rows,
        "extra_rows": extra_rows,
        "unsupported_divergences": unsupported,
        "documented_evidence_ratio": ratio,
        "record_complete": complete,
        "findings": findings,
        "verdict": verdict,
    }
