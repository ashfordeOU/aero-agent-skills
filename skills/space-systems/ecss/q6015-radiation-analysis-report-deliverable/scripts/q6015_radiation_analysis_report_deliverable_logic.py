"""Content and traceability check for the radiation analysis report.

Anchor: ECSS-Q-ST-60-15C Annex B (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Establish the report's required sections. The deliverable has to
   carry the configuration it analysed, the environment inputs it read
   from, one section per radiation effect analysed, the margins it
   applied, the mitigation decisions it took, the test evidence behind
   them, and the cross-reference back to the parts list.
2. Check every analysis entry is whole. An entry states a margin and
   the margin requirement it was held to; without both it says
   nothing, and the rest of the checks on it cannot run.
3. Tie shortfalls to decisions. Where a margin did not meet its
   requirement, the report has to say what was done about it -- a part
   changed, shielding added, circuit mitigation applied, lot
   acceptance testing imposed, a waiver requested or an operational
   workaround adopted -- not merely that the shortfall exists.
4. Tie everything to evidence. Every entry cites a test reference with
   a date, and a reference that is a placeholder is worse than a
   missing one because it reads as traceability without being it.
   Evidence dated after the report is evidence that did not exist when
   the conclusion was drawn.
5. Cross-check entries against sections. An entry for an effect whose
   section the report does not carry means the analysis exists but is
   not reported.

Stdlib only, offline, deterministic.
"""

import datetime
import math

REQUIRED_SECTIONS = (
    "analysis-scope-and-configuration",
    "environment-inputs-reference",
    "ionising-dose-analysis",
    "displacement-damage-analysis",
    "single-event-analysis",
    "applied-margins-summary",
    "mitigation-decisions",
    "radiation-test-evidence",
    "parts-list-cross-reference",
)

OPTIONAL_SECTIONS = (
    "open-actions",
    "assumptions-and-limitations",
    "shielding-model-description",
)

VALID_SECTIONS = REQUIRED_SECTIONS + OPTIONAL_SECTIONS

RADIATION_EFFECTS = (
    "total-ionising-dose",
    "displacement-damage",
    "single-event",
)

EFFECT_SECTION = {
    "total-ionising-dose": "ionising-dose-analysis",
    "displacement-damage": "displacement-damage-analysis",
    "single-event": "single-event-analysis",
}

MITIGATION_DECISIONS = (
    "part-replaced",
    "shielding-added",
    "circuit-mitigation-applied",
    "lot-acceptance-testing",
    "waiver-requested",
    "operational-workaround",
)

# A reference that is one of these is a placeholder wearing the shape
# of traceability.
PLACEHOLDER_REFERENCES = ("tbd", "tbc", "to-be-determined", "to be determined", "n/a", "none", "-")

# Margins are quotients of measured floats; one sitting exactly on its
# requirement has met it.
MARGIN_RELATIVE_TOLERANCE = 1.0e-9

FINDING_SECTION_MISSING = "required-report-section-missing"
FINDING_ENTRY_NO_MARGIN = "entry-without-an-applied-margin"
FINDING_SHORTFALL_NO_DECISION = "shortfall-without-a-mitigation-decision"
FINDING_NO_EVIDENCE = "entry-without-a-test-evidence-reference"
FINDING_PLACEHOLDER_EVIDENCE = "test-evidence-reference-is-a-placeholder"
FINDING_EVIDENCE_AFTER_REPORT = "test-evidence-dated-after-the-report"
FINDING_ENTRY_WITHOUT_SECTION = "analysis-entry-without-its-report-section"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _iso_date(label, value):
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string" % label)
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO date: %r" % (label, value))


def is_placeholder_reference(reference):
    """True when a reference string carries no traceability."""
    if reference is None:
        return True
    if not isinstance(reference, str):
        raise ValueError("reference must be a string or None")
    return reference.strip().lower() in PLACEHOLDER_REFERENCES


def validate_evidence(evidence, label):
    """Validate an evidence record and return a normalized copy."""
    if evidence is None:
        return None
    if not isinstance(evidence, dict):
        raise ValueError("%s evidence must be a mapping or None" % label)
    reference = evidence.get("reference")
    if reference is not None and not isinstance(reference, str):
        raise ValueError("%s evidence reference must be a string" % label)
    test_date = evidence.get("test_date")
    if test_date is not None:
        test_date = _iso_date("%s evidence test_date" % label, test_date)
    facility = evidence.get("facility")
    if facility is not None and (
        not isinstance(facility, str) or not facility.strip()
    ):
        raise ValueError("%s evidence facility must be a non-empty string" % label)
    return {
        "reference": reference.strip() if isinstance(reference, str) else None,
        "test_date": test_date,
        "facility": facility.strip() if facility else None,
    }


def validate_entry(entry):
    """Validate one analysis entry and return a normalized copy."""
    if not isinstance(entry, dict):
        raise ValueError("analysis entry must be a mapping")
    part_id = _text("entry part_id", entry.get("part_id"))
    effect = entry.get("effect")
    if effect not in RADIATION_EFFECTS:
        raise ValueError(
            "entry for %s has unknown effect %r (expected one of %s)"
            % (part_id, effect, ", ".join(RADIATION_EFFECTS))
        )
    label = "%s/%s" % (part_id, effect)
    margin = entry.get("margin")
    if margin is not None:
        margin = _numeric("%s margin" % label, margin, 0.0)
    requirement = entry.get("margin_requirement")
    if requirement is not None:
        requirement = _numeric("%s margin_requirement" % label, requirement)
        if requirement <= 0.0:
            raise ValueError("%s margin_requirement must be positive" % label)
    decision = entry.get("mitigation_decision")
    if decision is not None and decision not in MITIGATION_DECISIONS:
        raise ValueError(
            "%s mitigation_decision %r unknown (expected one of %s)"
            % (label, decision, ", ".join(MITIGATION_DECISIONS))
        )
    return {
        "part_id": part_id,
        "effect": effect,
        "label": label,
        "margin": margin,
        "margin_requirement": requirement,
        "mitigation_decision": decision,
        "evidence": validate_evidence(entry.get("evidence"), label),
    }


def margin_meets_requirement(margin, requirement):
    """True when a margin meets its requirement at exact equality."""
    margin = _numeric("margin", margin, 0.0)
    requirement = _numeric("requirement", requirement)
    if requirement <= 0.0:
        raise ValueError("requirement must be positive")
    return margin >= requirement * (1.0 - MARGIN_RELATIVE_TOLERANCE)


def validate_report(report):
    """Validate the report deliverable and return a normalized copy."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    report_date = _iso_date("report_date", report.get("report_date"))
    sections = report.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("report sections must be a non-empty list")
    normalized_sections = []
    seen_sections = set()
    for section in sections:
        if section not in VALID_SECTIONS:
            raise ValueError(
                "report section %r unknown (expected one of %s)"
                % (section, ", ".join(VALID_SECTIONS))
            )
        if section in seen_sections:
            raise ValueError("duplicate report section %r" % (section,))
        seen_sections.add(section)
        normalized_sections.append(section)
    entries = report.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("report entries must be a non-empty list")
    normalized_entries = []
    seen_entries = set()
    for entry in entries:
        record = validate_entry(entry)
        if record["label"] in seen_entries:
            raise ValueError("duplicate analysis entry %r" % (record["label"],))
        seen_entries.add(record["label"])
        normalized_entries.append(record)
    return {
        "report_date": report_date,
        "sections": normalized_sections,
        "entries": normalized_entries,
    }


def missing_required_sections(report):
    """Required sections the report does not carry."""
    normalized = validate_report(report)
    present = set(normalized["sections"])
    return [s for s in REQUIRED_SECTIONS if s not in present]


def entry_findings(entry, sections, report_date):
    """Findings about one analysis entry."""
    record = validate_entry(entry)
    held_on = report_date
    if not isinstance(held_on, datetime.date):
        held_on = _iso_date("report_date", held_on)
    if not isinstance(sections, (list, tuple, set)):
        raise ValueError("sections must be a sequence or set")
    present = set(sections)
    findings = []
    if EFFECT_SECTION[record["effect"]] not in present:
        findings.append("%s:%s" % (FINDING_ENTRY_WITHOUT_SECTION, record["label"]))
    if record["margin"] is None or record["margin_requirement"] is None:
        findings.append("%s:%s" % (FINDING_ENTRY_NO_MARGIN, record["label"]))
    elif not margin_meets_requirement(
        record["margin"], record["margin_requirement"]
    ) and not record["mitigation_decision"]:
        findings.append("%s:%s" % (FINDING_SHORTFALL_NO_DECISION, record["label"]))
    evidence = record["evidence"]
    if evidence is None or evidence["reference"] is None:
        findings.append("%s:%s" % (FINDING_NO_EVIDENCE, record["label"]))
    elif is_placeholder_reference(evidence["reference"]):
        findings.append("%s:%s" % (FINDING_PLACEHOLDER_EVIDENCE, record["label"]))
    elif evidence["test_date"] is None:
        findings.append("%s:%s" % (FINDING_NO_EVIDENCE, record["label"]))
    elif evidence["test_date"] > held_on:
        findings.append("%s:%s" % (FINDING_EVIDENCE_AFTER_REPORT, record["label"]))
    return findings


def worst_margin_ratio(entries):
    """Lowest margin-over-requirement ratio across graded entries."""
    records = [validate_entry(e) for e in entries]
    ratios = [
        r["margin"] / r["margin_requirement"]
        for r in records
        if r["margin"] is not None and r["margin_requirement"] is not None
    ]
    if not ratios:
        return None
    return min(ratios)


def assess_radiation_analysis_report(report):
    """Run the Annex B content and traceability check over a report."""
    normalized = validate_report(report)
    missing = missing_required_sections(report)
    findings = ["%s:%s" % (FINDING_SECTION_MISSING, s) for s in missing]
    entry_results = []
    for record in normalized["entries"]:
        own = entry_findings(
            record, normalized["sections"], normalized["report_date"]
        )
        entry_results.append(
            {"label": record["label"], "findings": own, "complete": not own}
        )
        findings.extend(own)
    complete_entries = [r for r in entry_results if r["complete"]]
    return {
        "missing_sections": missing,
        "section_completeness_ratio": (
            len(REQUIRED_SECTIONS) - len(missing)
        ) / float(len(REQUIRED_SECTIONS)),
        "entries": entry_results,
        "entry_completeness_ratio": len(complete_entries)
        / float(len(entry_results)),
        "incomplete_entry_labels": [
            r["label"] for r in entry_results if not r["complete"]
        ],
        "worst_margin_ratio": worst_margin_ratio(normalized["entries"]),
        "findings": findings,
        "compliant": not findings,
    }
