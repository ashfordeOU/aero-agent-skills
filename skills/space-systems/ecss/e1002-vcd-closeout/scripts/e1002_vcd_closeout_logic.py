#!/usr/bin/env python3
"""ECSS-E-ST-10C §5.4.4.1 VCD closeout — compliance-status determination
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
verification engineering standard's VCD closeout clause requires that every
row in the Verification Control Document be settled with one of three
statuses before a formal review gate can be passed — compliant when all
linked verification records are closed with passed results (or documented
as not applicable), not compliant when one or more records remain open or
carry a failed result without an accepted waiver, and waived when an approved
deviation document reference is on file for the requirement. A row with no
verification records at all is treated as not compliant: absence of evidence
is not evidence of compliance. This module implements row-level status
determination, VCD-level aggregation across all rows, a blocking-findings
extractor, and a compliance summary; it does not validate waiver approval
chains or the adequacy of not-applicable rationales.
"""

COMPLIANT = "compliant"
NOT_COMPLIANT = "not_compliant"
WAIVED = "waived"

VALID_OUTCOMES = frozenset({"passed", "failed", "open", "not_applicable"})


def determine_row_status(req_id, records, waiver_ref=None):
    """Determine VCD closeout status for one requirement row.

    req_id: requirement identifier string.
    records: list of dicts, each with keys "record_id" (str) and
        "outcome" (str — one of VALID_OUTCOMES).
    waiver_ref: str or None. A non-empty string indicates an approved
        waiver document is on file; the row is waived regardless of
        record outcomes.

    Returns a dict:
        {"req_id": str, "status": str, "findings": list}
    where status is one of COMPLIANT, NOT_COMPLIANT, WAIVED and
    findings is a list of finding dicts (empty when status is
    COMPLIANT or WAIVED).

    Raises ValueError for any record carrying an unrecognized outcome.
    Does not mutate records.
    """
    for rec in records:
        if rec["outcome"] not in VALID_OUTCOMES:
            raise ValueError(
                "unrecognized outcome %r for record %r in req %r under "
                "ECSS-E-ST-10C §5.4.4.1" % (rec["outcome"], rec["record_id"], req_id)
            )

    if waiver_ref:
        return {"req_id": req_id, "status": WAIVED, "findings": []}

    if not records:
        return {
            "req_id": req_id,
            "status": NOT_COMPLIANT,
            "findings": [{"issue": "no_verification_records", "req_id": req_id}],
        }

    open_ids = [r["record_id"] for r in records if r["outcome"] == "open"]
    failed_ids = [r["record_id"] for r in records if r["outcome"] == "failed"]

    findings = []
    if open_ids:
        findings.append(
            {
                "issue": "open_records_blocking_closeout",
                "req_id": req_id,
                "record_ids": open_ids,
            }
        )
    if failed_ids:
        findings.append(
            {
                "issue": "failed_records_without_waiver",
                "req_id": req_id,
                "record_ids": failed_ids,
            }
        )

    if findings:
        return {"req_id": req_id, "status": NOT_COMPLIANT, "findings": findings}

    return {"req_id": req_id, "status": COMPLIANT, "findings": []}


def vcd_closeout(vcd_rows):
    """Produce closeout results for all VCD rows.

    vcd_rows: iterable of dicts with keys:
        "req_id"    : str
        "records"   : list of {"record_id": str, "outcome": str}
        "waiver_ref": str or None  (optional key; defaults to None)

    Returns a list of result dicts from determine_row_status, one per row.
    Raises ValueError for any unrecognized record outcome encountered.
    Does not mutate input dicts.
    """
    return [
        determine_row_status(
            row["req_id"],
            row.get("records", []),
            row.get("waiver_ref"),
        )
        for row in vcd_rows
    ]


def compliance_summary(closeout_results):
    """Count requirements by status from vcd_closeout results.

    Returns a dict:
        {
            "compliant":     int,
            "not_compliant": int,
            "waived":        int,
            "total":         int,
            "all_closed":    bool,
        }
    all_closed is True only when not_compliant is zero.
    Does not mutate closeout_results.
    """
    counts = {COMPLIANT: 0, NOT_COMPLIANT: 0, WAIVED: 0}
    for result in closeout_results:
        counts[result["status"]] += 1
    total = sum(counts.values())
    return {
        "compliant": counts[COMPLIANT],
        "not_compliant": counts[NOT_COMPLIANT],
        "waived": counts[WAIVED],
        "total": total,
        "all_closed": counts[NOT_COMPLIANT] == 0,
    }


def blocking_findings(closeout_results):
    """Flatten all per-row findings from vcd_closeout into one list.

    Returns a list of finding dicts. An empty list means no blocking
    findings — the VCD can proceed to gate closure.
    Does not mutate closeout_results.
    """
    findings = []
    for result in closeout_results:
        findings.extend(result["findings"])
    return findings
