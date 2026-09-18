"""Safety analysis report and the hazard reports it carries.

Anchor: ECSS-Q-ST-40C clause 7.5 with the Annex D data requirement for the
safety analysis report, whose hazard reports integrate the outputs of the
hazard analysis, of the FMEA/FMECA and of the fault tree. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the report section order the data requirement fixes and refuse a
   report that omits a section, invents one, or prints them out of order.
2. Validate each hazard report: a severity, at least one cause, the controls
   that answer the causes, and a verification reference behind each control.
3. Trace every hazard cause back to a failure mode from the FMEA/FMECA or to
   a basic event from the fault tree, and report the causes that rest on
   neither.
4. Check the other direction too: a critical item the FMECA raised and no
   hazard report covers is a gap the report is meant to close.
5. Derive each hazard report's status from its own content, compare it with
   the status declared, and roll the set up into a closure verdict for the
   report as a whole.
"""

__all__ = [
    "REPORT_SECTIONS",
    "HAZARD_FIELDS",
    "CAUSE_FIELDS",
    "HAZARD_STATUSES",
    "SEVERITY_ORDER",
    "STATUS_RANK",
    "validate_severity",
    "validate_status",
    "validate_sections",
    "section_gaps",
    "validate_hazard_report",
    "trace_causes",
    "unverified_controls",
    "derived_status",
    "uncovered_critical_items",
    "assess_hazard_report",
    "assess_safety_analysis_report",
]

# The report sections in the order the data requirement prints them.
REPORT_SECTIONS = (
    "introduction",
    "applicable-and-reference-documents",
    "system-description",
    "safety-analysis-approach",
    "hazard-reports",
    "analysis-results-summary",
    "open-items-and-residual-risk",
    "conclusions",
)

# The hazard report record the assessment accepts.
HAZARD_FIELDS = ("id", "title", "severity", "causes", "controls", "verifications", "status")

# One cause of a hazard, and the analysis output it came from.
CAUSE_FIELDS = ("id", "reference")

# Hazard report statuses, weakest first.
HAZARD_STATUSES = ("open", "controlled", "closed")

# Severity categories, most severe first.
SEVERITY_ORDER = ("catastrophic", "critical", "major", "minor")

# Rank of a status; a declared status above the derived one is a finding.
STATUS_RANK = {name: index for index, name in enumerate(HAZARD_STATUSES)}


def _token(value, label, allowed):
    """Return a trimmed lowercase token drawn from allowed; raise otherwise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if token not in allowed:
        raise ValueError("%s must be one of %s, got %r" % (label, ", ".join(allowed), value))
    return token


def validate_severity(value):
    """Return a known severity category."""
    return _token(value, "severity", SEVERITY_ORDER)


def validate_status(value):
    """Return a known hazard report status."""
    return _token(value, "status", HAZARD_STATUSES)


def _identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower()


def validate_sections(sections):
    """Return the normalised section list of a submitted report."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a sequence of section names")
    result = []
    seen = set()
    for index, section in enumerate(sections):
        name = _token(section, "sections[%d]" % index, REPORT_SECTIONS)
        if name in seen:
            raise ValueError("sections lists %r twice" % name)
        seen.add(name)
        result.append(name)
    return tuple(result)


def section_gaps(sections):
    """Return the missing sections and whether the order was kept."""
    present = validate_sections(sections)
    missing = tuple(name for name in REPORT_SECTIONS if name not in present)
    expected = tuple(name for name in REPORT_SECTIONS if name in present)
    return {"present": present, "missing": missing, "ordered": present == expected}


def _validate_causes(causes, label):
    """Return the normalised cause list of one hazard report."""
    if not isinstance(causes, (list, tuple)) or not causes:
        raise ValueError("%s must be a non-empty sequence of causes" % label)
    result = []
    seen = set()
    for index, cause in enumerate(causes):
        if not isinstance(cause, dict):
            raise ValueError("%s[%d] must be a mapping" % (label, index))
        unknown = sorted(key for key in cause if key not in CAUSE_FIELDS)
        if unknown:
            raise ValueError("%s[%d] carries unknown keys: %s" % (label, index, ", ".join(unknown)))
        identifier = _identifier(cause.get("id"), "%s[%d].id" % (label, index))
        if identifier in seen:
            raise ValueError("%s lists cause %r twice" % (label, identifier))
        seen.add(identifier)
        reference = cause.get("reference")
        if reference is not None:
            reference = _identifier(reference, "%s[%d].reference" % (label, index))
        result.append({"id": identifier, "reference": reference})
    return result


def validate_hazard_report(hazard, position=0):
    """Return one normalised hazard report; raise on a malformed one."""
    if not isinstance(hazard, dict):
        raise ValueError("hazards[%d] must be a mapping" % position)
    unknown = sorted(key for key in hazard if key not in HAZARD_FIELDS)
    if unknown:
        raise ValueError("hazards[%d] carries unknown keys: %s" % (position, ", ".join(unknown)))
    title = hazard.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("hazards[%d].title must be a non-empty string" % position)
    controls = hazard.get("controls", [])
    if not isinstance(controls, (list, tuple)):
        raise ValueError("hazards[%d].controls must be a sequence" % position)
    normalised_controls = []
    for index, control in enumerate(controls):
        name = _identifier(control, "hazards[%d].controls[%d]" % (position, index))
        if name in normalised_controls:
            raise ValueError("hazards[%d] lists control %r twice" % (position, name))
        normalised_controls.append(name)
    verifications = hazard.get("verifications", {})
    if not isinstance(verifications, dict):
        raise ValueError("hazards[%d].verifications must be a mapping" % position)
    normalised_verifications = {}
    for key, value in verifications.items():
        control = _identifier(key, "hazards[%d].verifications key" % position)
        if control not in normalised_controls:
            raise ValueError(
                "hazards[%d] verifies %r, which is not one of its controls" % (position, control)
            )
        normalised_verifications[control] = _identifier(
            value, "hazards[%d].verifications[%r]" % (position, key)
        )
    declared = hazard.get("status")
    return {
        "id": _identifier(hazard.get("id"), "hazards[%d].id" % position),
        "title": title.strip(),
        "severity": validate_severity(hazard.get("severity")),
        "causes": _validate_causes(hazard.get("causes"), "hazards[%d].causes" % position),
        "controls": tuple(normalised_controls),
        "verifications": normalised_verifications,
        "status": None if declared is None else validate_status(declared),
    }


def trace_causes(record, failure_modes, basic_events):
    """Return the cause identifiers with no analysis output behind them."""
    if not isinstance(record, dict) or "causes" not in record:
        raise ValueError("record must be a normalised hazard report")
    if not isinstance(failure_modes, (list, tuple, set, frozenset)):
        raise ValueError("failure_modes must be a sequence of FMEA/FMECA identifiers")
    if not isinstance(basic_events, (list, tuple, set, frozenset)):
        raise ValueError("basic_events must be a sequence of fault-tree identifiers")
    known = {_identifier(item, "failure_modes item") for item in failure_modes}
    known |= {_identifier(item, "basic_events item") for item in basic_events}
    return tuple(
        cause["id"]
        for cause in record["causes"]
        if cause["reference"] is None or cause["reference"] not in known
    )


def unverified_controls(record):
    """Return the controls of one hazard report that carry no verification."""
    if not isinstance(record, dict) or "controls" not in record:
        raise ValueError("record must be a normalised hazard report")
    return tuple(
        control for control in record["controls"] if control not in record["verifications"]
    )


def derived_status(record):
    """Return the status a hazard report's own content supports."""
    if not record.get("controls"):
        return "open"
    if unverified_controls(record):
        return "controlled"
    return "closed"


def uncovered_critical_items(critical_items, records):
    """Return the FMECA critical items no hazard report names as a cause."""
    if not isinstance(critical_items, (list, tuple, set, frozenset)):
        raise ValueError("critical_items must be a sequence of identifiers")
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of normalised hazard reports")
    referenced = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or "causes" not in record:
            raise ValueError("records[%d] must be a normalised hazard report" % index)
        for cause in record["causes"]:
            if cause["reference"] is not None:
                referenced.add(cause["reference"])
    wanted = []
    for item in critical_items:
        name = _identifier(item, "critical_items item")
        if name not in wanted:
            wanted.append(name)
    return tuple(name for name in wanted if name not in referenced)


def assess_hazard_report(hazard, failure_modes, basic_events, position=0):
    """Grade one hazard report against the data requirement's content rules."""
    record = validate_hazard_report(hazard, position)
    untraced = trace_causes(record, failure_modes, basic_events)
    open_controls = unverified_controls(record)
    derived = derived_status(record)
    findings = []
    for cause in untraced:
        findings.append(
            "%s: cause %s traces to no failure mode and to no basic event"
            % (record["id"], cause)
        )
    for control in open_controls:
        findings.append("%s: control %s carries no verification" % (record["id"], control))
    if record["status"] is not None and STATUS_RANK[record["status"]] > STATUS_RANK[derived]:
        findings.append(
            "%s is declared %s while its content supports only %s"
            % (record["id"], record["status"], derived)
        )
    return {
        "id": record["id"],
        "title": record["title"],
        "severity": record["severity"],
        "cause_count": len(record["causes"]),
        "untraced_causes": untraced,
        "controls": record["controls"],
        "unverified_controls": open_controls,
        "declared_status": record["status"],
        "derived_status": derived,
        "findings": findings,
        "record": record,
    }


def assess_safety_analysis_report(spec):
    """Compile and grade a safety analysis report to the data requirement.

    spec keys: sections, hazards, and optional failure_modes, basic_events and
    critical_items naming the analysis outputs the hazard reports integrate.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("sections", "hazards"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    hazards = spec["hazards"]
    if not isinstance(hazards, (list, tuple)) or not hazards:
        raise ValueError("spec['hazards'] must be a non-empty sequence")
    failure_modes = spec.get("failure_modes", ())
    basic_events = spec.get("basic_events", ())
    critical_items = spec.get("critical_items", ())
    sections = section_gaps(spec["sections"])
    rows = []
    seen = set()
    for position, hazard in enumerate(hazards):
        row = assess_hazard_report(hazard, failure_modes, basic_events, position)
        if row["id"] in seen:
            raise ValueError("hazard report id %r appears twice" % row["id"])
        seen.add(row["id"])
        rows.append(row)
    uncovered = uncovered_critical_items(critical_items, [row["record"] for row in rows])
    findings = []
    for name in sections["missing"]:
        findings.append("the report omits the %s section" % name)
    if not sections["ordered"]:
        findings.append("the report prints its sections out of the required order")
    for row in rows:
        findings.extend(row["findings"])
    for name in uncovered:
        findings.append("critical item %s is covered by no hazard report" % name)
    closable = all(row["derived_status"] == "closed" for row in rows)
    if not closable:
        findings.append("the report cannot be closed while a hazard report is not closed")
    return {
        "sections": sections,
        "hazards": [
            {key: value for key, value in row.items() if key != "record"} for row in rows
        ],
        "hazard_count": len(rows),
        "uncovered_critical_items": uncovered,
        "closable": closable,
        "findings": findings,
        "verdict": "report-complete" if not findings else "report-incomplete",
    }
