#!/usr/bin/env python3
"""ECSS-E-ST-10C Annex E technology plan (TP) DRD logic (paraphrase).

Pure stdlib, no network. Unit conventions: this module carries no
physical units; TRL is an integer 1-9 on the E-AS-11 (ISO 16290) scale,
and dates are ISO 8601 strings (YYYY-MM-DD). Unknown/malformed section
names, TRL values outside 1-9, or malformed date strings raise
ValueError.

This module is a deterministic paraphrase of ECSS-E-ST-10C Annex E
practice: a Technology Plan is only complete once it carries every
required DRD content block, and every critical/enabling technology it
tracks must show a target TRL at or above its current TRL with its
assessment due on or before the date the design needs the result.
"""

from datetime import date

REQUIRED_TP_SECTIONS = [
    "purpose-and-scope",
    "applicable-reference-documents",
    "critical-technology-list",
    "trl-assessment-plan",
    "technology-development-schedule",
    "technology-risk-assessment",
    "backup-alternative-solutions",
    "technology-matrix-cross-reference",
]

TRL_MIN = 1
TRL_MAX = 9


def tp_completeness_check(sections_present):
    """Return the completeness verdict for a draft TP's section list.

    sections_present is a list/tuple/set of section-name strings
    present in the draft (case-insensitive). Returns a dict with
    'missing_sections' (the required sections not found, in DRD order)
    and 'status' ('complete' when none are missing, otherwise
    'incomplete-missing-sections'). Non-iterable input raises
    ValueError.
    """
    if not isinstance(sections_present, (list, tuple, set)):
        raise ValueError(
            "sections_present must be a list, tuple, or set of strings, got %r"
            % (sections_present,)
        )
    present = {s.strip().lower() for s in sections_present if isinstance(s, str)}
    missing = [s for s in REQUIRED_TP_SECTIONS if s not in present]
    return {
        "missing_sections": missing,
        "status": "complete" if not missing else "incomplete-missing-sections",
    }


def _validate_trl(value, label):
    if not isinstance(value, int) or isinstance(value, bool) or not (
        TRL_MIN <= value <= TRL_MAX
    ):
        raise ValueError(
            "%s must be an int between %d and %d, got %r"
            % (label, TRL_MIN, TRL_MAX, value)
        )


def trl_assessment_entry(technology, current_trl, target_trl, assessment_due, need_by):
    """Return the TRL/schedule verdict for one critical technology.

    technology is a non-empty name string. current_trl and target_trl
    are ints in 1-9 (E-AS-11/ISO 16290 scale). assessment_due and
    need_by are ISO 8601 date strings (YYYY-MM-DD). Returns a dict with
    'technology', 'current_trl', 'target_trl', 'schedule_ok' (bool),
    and 'status': 'trl-regression' when target_trl < current_trl,
    else 'schedule-risk' when the assessment is due after need_by,
    else 'on-track'. Invalid TRLs or malformed dates raise ValueError.
    """
    if not isinstance(technology, str) or not technology.strip():
        raise ValueError("technology must be a non-empty string, got %r" % (technology,))
    _validate_trl(current_trl, "current_trl")
    _validate_trl(target_trl, "target_trl")
    due = date.fromisoformat(assessment_due)
    need = date.fromisoformat(need_by)
    schedule_ok = due <= need
    if target_trl < current_trl:
        status = "trl-regression"
    elif not schedule_ok:
        status = "schedule-risk"
    else:
        status = "on-track"
    return {
        "technology": technology.strip(),
        "current_trl": current_trl,
        "target_trl": target_trl,
        "schedule_ok": schedule_ok,
        "status": status,
    }


def technology_schedule_verdict(entries):
    """Roll up trl_assessment_entry verdicts for a set of technologies.

    entries is a non-empty list of dicts, each with keys 'technology',
    'current_trl', 'target_trl', 'assessment_due', 'need_by'. Returns
    a dict with 'assessed' (the per-technology verdicts, in input
    order), 'at_risk' (the subset not 'on-track'), and 'status'
    ('schedule-consistent' when every technology is on-track, else
    'schedule-risk-present'). Empty, non-list, or malformed entries
    raise ValueError.
    """
    if not isinstance(entries, list) or not entries:
        raise ValueError(
            "entries must be a non-empty list of technology assessment dicts"
        )
    assessed = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(
                "each entry must be a dict with technology assessment fields, got %r"
                % (entry,)
            )
        try:
            technology = entry["technology"]
            current_trl = entry["current_trl"]
            target_trl = entry["target_trl"]
            assessment_due = entry["assessment_due"]
            need_by = entry["need_by"]
        except KeyError as exc:
            raise ValueError("entry missing required field %s" % (exc,)) from exc
        assessed.append(
            trl_assessment_entry(technology, current_trl, target_trl, assessment_due, need_by)
        )
    at_risk = [a for a in assessed if a["status"] != "on-track"]
    return {
        "assessed": assessed,
        "at_risk": at_risk,
        "status": "schedule-consistent" if not at_risk else "schedule-risk-present",
    }


def tp_status_verdict(sections_present, entries):
    """Build the overall TP status from completeness and schedule verdicts.

    sections_present and entries are passed through to
    tp_completeness_check and technology_schedule_verdict respectively.
    Returns a dict with 'completeness', 'schedule', and 'status'
    ('tp-approved' when the TP is complete and every technology is
    on-track, otherwise 'tp-revision-required').
    """
    completeness = tp_completeness_check(sections_present)
    schedule = technology_schedule_verdict(entries)
    ready = completeness["status"] == "complete" and schedule["status"] == "schedule-consistent"
    return {
        "completeness": completeness,
        "schedule": schedule,
        "status": "tp-approved" if ready else "tp-revision-required",
    }


if __name__ == "__main__":
    import doctest

    doctest.testmod()
