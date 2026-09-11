"""ECSS-E-ST-10-02 clause 5.4.1 verification control and close-out (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): clause 5.4.1
governs how verification is controlled through the verification control
document and how it is finally closed out, including the delivery of the
verification database in electronic form. Close-out is conjunctive: every
requirement closed, every nonconformance dispositioned, every invoked waiver
approved by the authority that can grant it, and the database actually
delivered -- machine-readable, in the agreed format, and covering every row
the control document holds. A database that is delivered but incomplete is
the failure mode this clause exists to prevent: the programme ends and the
evidence trail has holes nobody will ever fill.
"""

ROW_STATUSES = ("open", "in_progress", "closed", "closed_with_waiver")
CLOSED_STATUSES = ("closed", "closed_with_waiver")
NC_STATES = ("open", "dispositioned")


def validate_row_status(status):
    """Return status if it is a recognized control-document row status."""
    if status not in ROW_STATUSES:
        raise ValueError("unknown row status: %r" % (status,))
    return status


def open_rows(rows):
    """Requirement ids whose verification row has not reached a closed
    status, in input order."""
    out = []
    for r in rows:
        rid = r.get("requirement_id")
        if not rid:
            raise ValueError("control document row with no requirement_id")
        if validate_row_status(r.get("status")) not in CLOSED_STATUSES:
            out.append(rid)
    return out


def waiver_violations(rows, approved_waivers):
    """Findings for rows closed against a waiver that is absent or not
    approved. A waiver is an authority's decision, so an unapproved one
    closes nothing -- it only records that somebody wanted to."""
    approved = set(approved_waivers)
    out = []
    for r in rows:
        if r.get("status") != "closed_with_waiver":
            continue
        ref = (r.get("waiver_ref") or "").strip()
        if not ref:
            out.append({"requirement_id": r["requirement_id"],
                        "issue": "closed_with_waiver_without_reference"})
        elif ref not in approved:
            out.append({"requirement_id": r["requirement_id"],
                        "waiver_ref": ref, "issue": "waiver_not_approved"})
    return out


def evidence_violations(rows):
    """Findings for closed rows citing no evidence. Closure without evidence
    is an assertion, and the control document exists to prevent exactly
    that."""
    out = []
    for r in rows:
        if r.get("status") in CLOSED_STATUSES and \
                not (r.get("evidence_ref") or "").strip():
            out.append({"requirement_id": r["requirement_id"],
                        "issue": "closed_without_evidence"})
    return out


def nonconformance_violations(nonconformances):
    """Findings for nonconformances still open at close-out."""
    out = []
    for nc in nonconformances:
        ncid = nc.get("nc_id")
        if not ncid:
            raise ValueError("nonconformance with no nc_id")
        state = nc.get("state", "open")
        if state not in NC_STATES:
            raise ValueError("unknown nonconformance state: %r" % (state,))
        if state == "open":
            out.append({"nc_id": ncid, "issue": "nonconformance_open_at_closeout"})
    return out


def database_violations(delivery, rows, agreed_format):
    """Findings for the verification database delivery required by 5.4.1c.

    delivery: {"delivered": bool, "format": str, "machine_readable": bool,
               "row_ids": [requirement_id, ...]}

    Completeness is checked against the control document's own rows, because
    a delivered-but-partial database is the characteristic failure: the
    programme closes and the evidence trail has holes.
    """
    if not delivery or not delivery.get("delivered"):
        return [{"issue": "verification_database_not_delivered"}]
    out = []
    if delivery.get("format") != agreed_format:
        out.append({"issue": "database_format_not_as_agreed",
                    "delivered": delivery.get("format"),
                    "agreed": agreed_format})
    if not delivery.get("machine_readable"):
        out.append({"issue": "database_not_machine_readable"})
    have = set(delivery.get("row_ids") or [])
    missing = [r["requirement_id"] for r in rows
               if r.get("requirement_id") not in have]
    for rid in missing:
        out.append({"requirement_id": rid, "issue": "row_absent_from_database"})
    return out


def closeout_review(vcd, agreed_format):
    """Full clause 5.4.1 verification control and close-out review.

    vcd: {"rows": [{"requirement_id", "status", "evidence_ref", "waiver_ref"}],
          "nonconformances": [{"nc_id", "state"}],
          "approved_waivers": [str], "database_delivery": {...}}

    Returns {"open_requirements", "findings"}.
    """
    rows = list(vcd.get("rows", []))
    findings = []
    still_open = open_rows(rows)
    for rid in still_open:
        findings.append({"requirement_id": rid, "issue": "requirement_not_closed"})
    findings += waiver_violations(rows, vcd.get("approved_waivers", []))
    findings += evidence_violations(rows)
    findings += nonconformance_violations(vcd.get("nonconformances", []))
    findings += database_violations(vcd.get("database_delivery"), rows,
                                    agreed_format)
    return {"open_requirements": still_open, "findings": findings}


def is_verification_closed_out(review):
    """True when verification may be declared closed out: nothing open and no
    finding standing. The conditions are conjunctive -- a delivered database
    does not offset an open nonconformance, and vice versa."""
    return not (review["open_requirements"] or review["findings"])
