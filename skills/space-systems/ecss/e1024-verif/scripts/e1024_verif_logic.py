"""
ECSS-E-ST-10-24C §5.6 — Interface Verification and Validation Logic.
Deterministic, offline, stdlib-only.
"""

VALID_METHODS = frozenset({"test", "analysis", "inspection", "review", "similarity"})

VALID_STATUSES = frozenset({
    "open", "in-progress", "complete", "waived", "not-applicable"
})

VALID_INTERFACE_TYPES = frozenset({
    "mechanical", "electrical", "thermal", "data",
    "rf", "optical", "fluid", "software"
})

ICD_REQUIRED_FIELDS = frozenset({
    "id", "source_subsystem", "destination_subsystem", "interface_type", "description"
})

VCD_REQUIRED_FIELDS = frozenset({"id", "icd_ref", "method", "status"})


def validate_icd_record(record):
    """
    Validate a single ICD record dict for completeness and consistency.
    Returns (is_valid: bool, findings: list[str]).
    """
    findings = []

    for field in sorted(ICD_REQUIRED_FIELDS):
        if field not in record or not str(record[field]).strip():
            findings.append(f"ICD record missing or empty field: '{field}'")

    if "interface_type" in record and str(record["interface_type"]).strip():
        itype = record["interface_type"].strip().lower()
        if itype not in VALID_INTERFACE_TYPES:
            findings.append(
                f"ICD record '{record.get('id', '<no-id>')}' has unrecognized "
                f"interface_type: '{record['interface_type']}'; "
                f"expected one of {sorted(VALID_INTERFACE_TYPES)}"
            )

    src = str(record.get("source_subsystem", "")).strip().lower()
    dst = str(record.get("destination_subsystem", "")).strip().lower()
    if src and dst and src == dst:
        findings.append(
            f"ICD record '{record.get('id', '<no-id>')}' has identical "
            "source and destination subsystem; interface cannot be verified"
        )

    return (len(findings) == 0, findings)


def validate_vcd_entry(entry):
    """
    Validate a single VCD entry dict for required fields and recognized values.
    Returns (is_valid: bool, findings: list[str]).
    """
    findings = []

    for field in sorted(VCD_REQUIRED_FIELDS):
        if field not in entry or not str(entry[field]).strip():
            findings.append(f"VCD entry missing or empty field: '{field}'")

    if "method" in entry and str(entry["method"]).strip():
        method = entry["method"].strip().lower()
        if method not in VALID_METHODS:
            findings.append(
                f"VCD entry '{entry.get('id', '<no-id>')}' has unrecognized "
                f"method: '{entry['method']}'; "
                f"expected one of {sorted(VALID_METHODS)}"
            )

    if "status" in entry and str(entry["status"]).strip():
        status = entry["status"].strip().lower()
        if status not in VALID_STATUSES:
            findings.append(
                f"VCD entry '{entry.get('id', '<no-id>')}' has unrecognized "
                f"status: '{entry['status']}'; "
                f"expected one of {sorted(VALID_STATUSES)}"
            )

    return (len(findings) == 0, findings)


def trace_icd_to_vcd(icd_records, vcd_entries):
    """
    Trace each ICD record to VCD entries via icd_ref matching.
    Returns dict:
      'covered'        — sorted list of ICD ids with at least one VCD entry
      'gaps'           — sorted list of ICD ids with no VCD entry
      'coverage_ratio' — float in [0.0, 1.0]; 0.0 when no ICD records
    """
    icd_ids = {str(r["id"]) for r in icd_records if "id" in r and r["id"]}
    vcd_refs = {str(e["icd_ref"]) for e in vcd_entries if "icd_ref" in e and e["icd_ref"]}

    covered_ids = icd_ids & vcd_refs
    gap_ids = icd_ids - vcd_refs

    total = len(icd_ids)
    ratio = len(covered_ids) / total if total > 0 else 0.0

    return {
        "covered": sorted(covered_ids),
        "gaps": sorted(gap_ids),
        "coverage_ratio": ratio,
    }


def compute_coverage_status(icd_records, vcd_entries):
    """
    Trace ICD to VCD and append a pass/fail status string.
    Returns trace dict extended with 'status': 'pass' | 'fail'.
    """
    result = trace_icd_to_vcd(icd_records, vcd_entries)
    result["status"] = "pass" if not result["gaps"] else "fail"
    return result


def assess_interface_verification(icd_records, vcd_entries):
    """
    Full ECSS-E-ST-10-24C §5.6 assessment.

    Validates all ICD records, validates all VCD entries, traces coverage,
    and returns a consolidated result dict:
      'icd_findings' — {icd_id: [finding_str, ...]} for each invalid record
      'vcd_findings' — {vcd_id: [finding_str, ...]} for each invalid entry
      'trace'        — coverage trace dict (covered, gaps, coverage_ratio, status)
      'compliant'    — True only when icd_findings, vcd_findings, and gaps are all empty
    """
    icd_findings = {}
    for record in icd_records:
        rid = str(record.get("id", "<no-id>"))
        valid, flist = validate_icd_record(record)
        if not valid:
            icd_findings[rid] = flist

    vcd_findings = {}
    for entry in vcd_entries:
        eid = str(entry.get("id", "<no-id>"))
        valid, flist = validate_vcd_entry(entry)
        if not valid:
            vcd_findings[eid] = flist

    trace = compute_coverage_status(icd_records, vcd_entries)

    compliant = (
        not icd_findings
        and not vcd_findings
        and trace["status"] == "pass"
    )

    return {
        "icd_findings": icd_findings,
        "vcd_findings": vcd_findings,
        "trace": trace,
        "compliant": compliant,
    }
