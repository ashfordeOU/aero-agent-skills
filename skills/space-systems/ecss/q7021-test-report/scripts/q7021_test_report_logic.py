"""Completeness and self-consistency of a flammability test report.

Anchor: ECSS-Q-ST-70-21C, reporting (the conditions the run was carried out
under, the results obtained, and the observations made while obtaining them).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the report against the section and field list a screening report is
   expected to carry, separating a field whose absence blocks the report from
   one whose absence is an advisory.
2. Cross-check the report against itself. A burn length longer than the
   specimen it was measured on, a result count that disagrees with the specimen
   count, a test run before the conditioning that preceded it and a quoted
   worst case that is not the worst of the results are all internal
   contradictions a field-presence check cannot see.
3. Report completeness as a ratio over the blocking fields only, so an
   advisory omission cannot dilute or inflate the figure that decides whether
   the report is fileable.
4. Return the section order a compliant report follows, so a report that has to
   go back can be rebuilt rather than patched.
"""

import datetime

__all__ = [
    "SECTION_ORDER",
    "BLOCKING_FIELDS",
    "ADVISORY_FIELDS",
    "parse_iso_date",
    "report_skeleton",
    "missing_fields",
    "consistency_findings",
    "completeness_ratio",
    "assess_test_report",
]

SECTION_ORDER = (
    "identification",
    "specimens",
    "conditions",
    "results",
    "observations",
    "deviations",
)

# Fields whose absence stops the report being filed as evidence.
BLOCKING_FIELDS = {
    "identification": ("report_ref", "material", "test_date", "laboratory"),
    "specimens": ("specimen_count", "thickness_mm", "orientation", "batch_ref"),
    "conditions": ("oxygen_concentration_pct", "pressure_kpa",
                   "conditioning_end_date", "ignition_source"),
    "results": ("specimen_results", "worst_case_burn_length_mm"),
    "observations": ("dripping", "self_extinguishing"),
    "deviations": ("deviations_recorded",),
}

# Fields whose absence is worth saying out loud but does not stop the filing.
ADVISORY_FIELDS = {
    "identification": ("operator",),
    "specimens": ("preparation_method",),
    "conditions": ("gas_flow_lpm", "ambient_temperature_c", "conditioning_hours"),
    "observations": ("smoke", "afterglow", "char_appearance"),
}


def parse_iso_date(value, label="date"):
    """Return an ISO-8601 calendar date, refusing anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO-8601 date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO-8601 calendar date: %r" % (label, value))


def report_skeleton():
    """Return the ordered sections and the blocking fields each one carries."""
    return [(section, list(BLOCKING_FIELDS.get(section, ())))
            for section in SECTION_ORDER]


def _validate_report(report):
    """Return the report after checking its outer shape."""
    if not isinstance(report, dict):
        raise ValueError("a test report must be a mapping of section to content")
    unknown = sorted(set(report) - set(SECTION_ORDER))
    if unknown:
        raise ValueError("report carries sections outside the reporting structure: %s"
                         % ", ".join(unknown))
    for section, content in report.items():
        if not isinstance(content, dict):
            raise ValueError("report section %r must be a mapping" % section)
    return report


def _present(content, field):
    """True when a field carries something other than an empty value."""
    if field not in content:
        return False
    value = content[field]
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, tuple, dict)) and len(value) == 0:
        return False
    return True


def missing_fields(report):
    """Return the blocking and advisory omissions, in reporting order."""
    _validate_report(report)
    blocking = []
    advisory = []
    for section in SECTION_ORDER:
        content = report.get(section, {})
        for field in BLOCKING_FIELDS.get(section, ()):
            if not _present(content, field):
                blocking.append("%s.%s" % (section, field))
        for field in ADVISORY_FIELDS.get(section, ()):
            if not _present(content, field):
                advisory.append("%s.%s" % (section, field))
    return {"blocking": blocking, "advisory": advisory}


def _numeric(value):
    """Return value as a float when it is a real number, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def consistency_findings(report):
    """Return the internal contradictions a field-presence check cannot see."""
    _validate_report(report)
    findings = []
    specimens = report.get("specimens", {})
    results = report.get("results", {})
    conditions = report.get("conditions", {})
    identification = report.get("identification", {})

    rows = results.get("specimen_results")
    declared = specimens.get("specimen_count")
    if isinstance(rows, (list, tuple)):
        if isinstance(declared, int) and not isinstance(declared, bool):
            if declared != len(rows):
                findings.append("the specimen section declares %d specimen(s) and the "
                                "results section carries %d row(s)"
                                % (declared, len(rows)))
        burns = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                findings.append("result row %d is not a mapping" % index)
                continue
            burn = _numeric(row.get("burn_length_mm"))
            exposed = _numeric(row.get("specimen_length_mm"))
            if burn is None:
                findings.append("result row %d records no burn length" % index)
                continue
            burns.append(burn)
            if exposed is not None and burn > exposed:
                findings.append("result row %d reports a burn length of %g mm on a "
                                "%g mm specimen" % (index, burn, exposed))
        quoted = _numeric(results.get("worst_case_burn_length_mm"))
        if burns and quoted is not None:
            observed = max(burns)
            if abs(quoted - observed) > 1e-9:
                findings.append("the quoted worst case of %g mm is not the longest "
                                "burn in the results, which is %g mm"
                                % (quoted, observed))
    elif rows is not None:
        findings.append("the results section must carry a list of specimen rows")

    oxygen = _numeric(conditions.get("oxygen_concentration_pct"))
    if oxygen is not None and not 0.0 < oxygen <= 100.0:
        findings.append("the recorded oxygen concentration of %g percent is not a "
                        "physical concentration" % oxygen)
    pressure = _numeric(conditions.get("pressure_kpa"))
    if pressure is not None and pressure <= 0.0:
        findings.append("the recorded pressure of %g kPa is not physical" % pressure)

    test_date = identification.get("test_date")
    conditioning_end = conditions.get("conditioning_end_date")
    if test_date is not None and conditioning_end is not None:
        tested = parse_iso_date(test_date, "identification.test_date")
        conditioned = parse_iso_date(conditioning_end, "conditions.conditioning_end_date")
        if tested < conditioned:
            findings.append("the report is dated %s, before the conditioning it says "
                            "ended on %s" % (tested.isoformat(), conditioned.isoformat()))
    return findings


def completeness_ratio(report):
    """Return the share of blocking fields the report actually carries."""
    missing = missing_fields(report)
    total = sum(len(fields) for fields in BLOCKING_FIELDS.values())
    if total == 0:
        raise ValueError("no blocking fields are defined")
    return (total - len(missing["blocking"])) / float(total)


def assess_test_report(report):
    """Run the full reporting assessment for one flammability test report."""
    _validate_report(report)
    missing = missing_fields(report)
    findings = consistency_findings(report)
    ratio = completeness_ratio(report)
    fileable = not missing["blocking"] and not findings
    if missing["blocking"]:
        verdict = "return-for-completion"
    elif findings:
        verdict = "return-for-correction"
    elif missing["advisory"]:
        verdict = "fileable-with-advisories"
    else:
        verdict = "fileable"
    return {
        "missing_blocking": missing["blocking"],
        "missing_advisory": missing["advisory"],
        "consistency_findings": findings,
        "completeness_ratio": ratio,
        "fileable": fileable,
        "verdict": verdict,
        "skeleton": report_skeleton(),
    }
