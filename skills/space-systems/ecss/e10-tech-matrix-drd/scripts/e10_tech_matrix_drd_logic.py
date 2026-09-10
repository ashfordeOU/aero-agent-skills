#!/usr/bin/env python3
"""ECSS-E-ST-10C Annex F Technology Matrix DRD (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
Technology Matrix is a normative DRD deliverable listing every
technology relevant to the project, one row per technology, against its
current technology readiness level (TRL), the target TRL required for
the mission, and its mission-applicability status. TRL is reported on
the 1-9 integer scale (per E-AS-11 / ISO 16290). A technology's target
TRL should never sit below its already-demonstrated current TRL, and
its mission-applicability status must be resolved ("applicable" or "not
applicable") rather than left open.

This module checks Technology Matrix DRD section presence, per-row
field completeness, TRL validity, TRL progression, and applicability
resolution. It does not run the technology planning and risk-management
activity that produces the matrix's inputs (see the sibling
e10-technology leaf) or check the separate Technology Plan DRD content
(e10-tp-drd).
"""

REQUIRED_DRD_SECTIONS = (
    "purpose and scope",
    "applicable and reference documents",
    "technology matrix",
)

REQUIRED_ROW_FIELDS = (
    "current trl",
    "target trl",
    "mission applicability",
)

VALID_APPLICABILITY = ("applicable", "not applicable")

MIN_TRL = 1
MAX_TRL = 9


def section_gaps(sections_present):
    """Missing required DRD sections, in required-section order.
    sections_present is an iterable of section names present in the
    Technology Matrix document."""
    present = set(sections_present)
    return [s for s in REQUIRED_DRD_SECTIONS if s not in present]


def row_field_gaps(row):
    """Missing required fields for a single technology row, in
    required-field order. row is a mapping of field name -> value."""
    return [f for f in REQUIRED_ROW_FIELDS if f not in row]


def matrix_field_gaps(rows):
    """Technology name -> [missing field, ...] for every row with
    missing required fields. rows is a mapping of technology name ->
    row (field name -> value), in rows insertion order."""
    return {
        name: gaps
        for name, row in rows.items()
        for gaps in [row_field_gaps(row)]
        if gaps
    }


def _is_valid_trl(value):
    return isinstance(value, int) and not isinstance(value, bool) and MIN_TRL <= value <= MAX_TRL


def invalid_trls(rows):
    """(technology_name, field, value) tuples for rows whose current or
    target TRL is missing, non-integer, or outside 1-9. Only rows that
    carry the field are checked here (missing fields are reported by
    matrix_field_gaps); rows insertion order, current TRL before target
    TRL."""
    invalid = []
    for name, row in rows.items():
        for field in ("current trl", "target trl"):
            if field in row and not _is_valid_trl(row[field]):
                invalid.append((name, field, row[field]))
    return invalid


def trl_regressions(rows):
    """Technology names where target TRL is below current TRL. Only
    rows with valid TRL values in both fields are checked; rows
    insertion order."""
    regressed = []
    for name, row in rows.items():
        current = row.get("current trl")
        target = row.get("target trl")
        if _is_valid_trl(current) and _is_valid_trl(target) and target < current:
            regressed.append(name)
    return regressed


def unresolved_applicability(rows):
    """Technology names whose mission-applicability value is missing or
    not one of VALID_APPLICABILITY (e.g. blank or 'TBD'); rows insertion
    order."""
    unresolved = []
    for name, row in rows.items():
        value = row.get("mission applicability")
        if value not in VALID_APPLICABILITY:
            unresolved.append(name)
    return unresolved


def tech_matrix_ready(sections_present, rows):
    """Overall Technology Matrix readiness. Returns (ready, issues)
    where issues is a dict with keys 'missing_sections' (list),
    'missing_fields' (technology name -> [field, ...]),
    'invalid_trls', 'trl_regressions', and 'unresolved_applicability'
    (as returned by the corresponding check functions above). ready is
    True only when every issue list/dict is empty."""
    missing_sections = section_gaps(sections_present)
    missing_fields = matrix_field_gaps(rows)
    bad_trls = invalid_trls(rows)
    regressions = trl_regressions(rows)
    unresolved = unresolved_applicability(rows)
    issues = {
        "missing_sections": missing_sections,
        "missing_fields": missing_fields,
        "invalid_trls": bad_trls,
        "trl_regressions": regressions,
        "unresolved_applicability": unresolved,
    }
    ready = not (missing_sections or missing_fields or bad_trls or regressions or unresolved)
    return (ready, issues)
