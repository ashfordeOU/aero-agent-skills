#!/usr/bin/env python3
"""Summary design sheet review item for a microwave die design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.14. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The summary design sheet is the one page a reader meets before any of
the detail: the die, its key characteristics and the numbers everyone
downstream will quote. It is a derived document, so reviewing it is not
reviewing a design - it is reviewing a copy against what it was copied
from, and against the form it has to keep.

Content
    The sheet has to carry the characteristics the programme requires
    of a die. A characteristic the sheet leaves out is not summarised
    elsewhere; it is simply absent from the page everyone reads.

Agreement
    Every summarised value was copied from a detail source and rounded
    on the way. A difference inside the stated rounding tolerance is
    the sheet doing its job; a difference beyond it means the page and
    the detail disagree, and the page is the one that gets quoted.

Form
    One page is a requirement, not a preference. A sheet whose rendered
    content exceeds the page budget is no longer a summary, and a sheet
    issued before the detail it summarises may be quoting numbers the
    detail has already moved away from.

An item closes only when the required characteristics are present, each
agrees with its source, and the page still fits and is not behind the
detail.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ENTRY_FIELDS = (
    "characteristic",
    "summary_value",
    "source_value",
    "unit",
    "source_reference",
    "rendered_lines",
)

REQUIRED_CHARACTERISTICS = (
    "die-outline-dimensions",
    "die-thickness",
    "operating-frequency-band",
    "rated-output-power",
    "maximum-junction-temperature",
    "bias-supply-voltage",
    "backside-metallization",
    "bond-pad-layout-reference",
)

COVERAGE_COMPLETE = "summary-sheet-carries-every-characteristic"
COVERAGE_INCOMPLETE = "summary-sheet-missing-characteristics"

AGREEMENT_HELD = "summary-agrees-with-the-detail-source"
AGREEMENT_BROKEN = "summary-contradicts-the-detail-source"

ANNOTATION_COMPLETE = "summary-entries-fully-annotated"
ANNOTATION_INCOMPLETE = "summary-entries-missing-annotation"

PAGE_FITS = "summary-sheet-fits-one-page"
PAGE_NEARLY_FULL = "summary-sheet-page-nearly-full"
PAGE_OVER = "summary-sheet-over-one-page"

ISSUE_CURRENT = "summary-sheet-issue-current"
ISSUE_BEHIND = "summary-sheet-behind-the-detail-issue"

VERDICT_CLOSED = "summary-design-sheet-item-closed"
VERDICT_ACTIONED = "summary-design-sheet-item-open-with-actions"
VERDICT_REJECTED = "summary-design-sheet-item-rejected"

# Relative difference a summarised value may carry against its detail
# source before the page and the detail are taken to disagree.
DEFAULT_ROUNDING_TOLERANCE = 0.005

# Rendered lines a single sheet page holds, and the share of that budget
# above which the page is carried as a finding while still fitting.
DEFAULT_PAGE_LINE_BUDGET = 56
DEFAULT_PAGE_CAUTION_FRACTION = 0.95
DEFAULT_HEADER_LINES = 6

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_positive_integer(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("%s must be an integer of one or more, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or (number > 1.0 and not _close(number, 1.0)):
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (name, value))
    return list(value)


def _reject_unknown_fields(name, record, allowed):
    unknown = sorted(set(record) - set(allowed))
    if unknown:
        raise ValueError("%s carries unknown fields: %s" % (name, ", ".join(unknown)))


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _below(value, limit):
    """value < limit, with a value sitting on the limit counted as on it."""
    return value < limit and not _close(value, limit)


def canonical_text(raw_value):
    """One spelling for a textual characteristic quoted on the sheet."""
    text = _require_identifier("textual value", raw_value)
    return " ".join(text.split()).casefold()


def relative_difference(summary_value, source_value):
    """How far a summarised number sits from the detail it was copied from.

    Scaled on the source magnitude so a tolerance can be stated once for
    the whole sheet, with a unit denominator floor so a source value of
    zero does not divide the review.
    """
    summary = _require_number("summary_value", summary_value)
    source = _require_number("source_value", source_value)
    denominator = abs(source)
    if denominator < 1.0:
        denominator = 1.0
    return abs(summary - source) / denominator


def values_agree(summary_value, source_value, tolerance=None):
    """Whether a summarised number is inside the rounding tolerance."""
    limit = (
        DEFAULT_ROUNDING_TOLERANCE
        if tolerance is None
        else _require_fraction("tolerance", tolerance)
    )
    return _at_most(relative_difference(summary_value, source_value), limit)


def normalize_entries(records, allowed_characteristics=None):
    """Canonical, duplicate-free rows of the summary design sheet."""
    rows = _require_sequence("records", records)
    if not rows:
        raise ValueError("records must contain at least one sheet entry")
    allowed = (
        REQUIRED_CHARACTERISTICS
        if allowed_characteristics is None
        else tuple(_require_sequence("allowed_characteristics", allowed_characteristics))
    )
    normalized = {}
    for position, record in enumerate(rows):
        label = "entry %d" % position
        row = _require_mapping(label, record)
        _reject_unknown_fields(label, row, ENTRY_FIELDS)
        characteristic = _require_identifier(
            "%s characteristic" % label, row.get("characteristic")
        )
        if characteristic not in allowed:
            raise ValueError(
                "the sheet carries %s, which the programme does not define as a "
                "die characteristic" % characteristic
            )
        if characteristic in normalized:
            raise ValueError("characteristic %s is stated twice" % characteristic)
        summary_value = row.get("summary_value")
        source_value = row.get("source_value")
        if _is_finite_number(summary_value) and _is_finite_number(source_value):
            kind = "numeric"
            summary_value = float(summary_value)
            source_value = float(source_value)
        elif isinstance(summary_value, str) and isinstance(source_value, str):
            kind = "text"
            summary_value = _require_identifier("%s summary_value" % label, summary_value)
            source_value = _require_identifier("%s source_value" % label, source_value)
        else:
            raise ValueError(
                "%s must quote a summary and a source of the same kind, got %r "
                "against %r" % (label, summary_value, source_value)
            )
        unit = row.get("unit")
        if unit is not None:
            unit = _require_identifier("%s unit" % label, unit)
        source_reference = row.get("source_reference")
        if source_reference is not None:
            source_reference = _require_identifier(
                "%s source_reference" % label, source_reference
            )
        rendered_lines = _require_positive_integer(
            "%s rendered_lines" % label, row.get("rendered_lines", 1)
        )
        normalized[characteristic] = {
            "characteristic": characteristic,
            "kind": kind,
            "summary_value": summary_value,
            "source_value": source_value,
            "unit": unit,
            "source_reference": source_reference,
            "rendered_lines": rendered_lines,
        }
    return tuple(normalized[key] for key in sorted(normalized))


def assess_coverage(entries, required_characteristics=None):
    """Decide whether the page carries every required characteristic."""
    required = (
        REQUIRED_CHARACTERISTICS
        if required_characteristics is None
        else tuple(
            _require_sequence("required_characteristics", required_characteristics)
        )
    )
    if not required:
        raise ValueError("required_characteristics must name at least one entry")
    present = {entry["characteristic"] for entry in entries}
    absent = tuple(sorted(set(required) - present))
    share = float(len(required) - len(absent)) / float(len(required))
    findings = []
    if absent:
        status = COVERAGE_INCOMPLETE
        findings.append(
            "the sheet leaves out %d required characteristic(s): %s"
            % (len(absent), ", ".join(absent))
        )
    else:
        status = COVERAGE_COMPLETE
    return {
        "status": status,
        "absent": absent,
        "coverage_share": share,
        "findings": findings,
    }


def assess_agreement(entries, tolerance=None):
    """Decide whether every summarised value matches its detail source."""
    limit = (
        DEFAULT_ROUNDING_TOLERANCE
        if tolerance is None
        else _require_fraction("tolerance", tolerance)
    )
    disagreements = []
    rounded = []
    findings = []
    for entry in entries:
        if entry["kind"] == "numeric":
            difference = relative_difference(
                entry["summary_value"], entry["source_value"]
            )
            if not _at_most(difference, limit):
                disagreements.append(entry["characteristic"])
                findings.append(
                    "%s is summarised as %g against a detail value of %g, a "
                    "relative difference of %.4f beyond the %.4f rounding "
                    "tolerance"
                    % (
                        entry["characteristic"],
                        entry["summary_value"],
                        entry["source_value"],
                        difference,
                        limit,
                    )
                )
            elif not _close(difference, 0.0):
                rounded.append(entry["characteristic"])
        else:
            if canonical_text(entry["summary_value"]) != canonical_text(
                entry["source_value"]
            ):
                disagreements.append(entry["characteristic"])
                findings.append(
                    "%s is summarised as %r against a detail value of %r"
                    % (
                        entry["characteristic"],
                        entry["summary_value"],
                        entry["source_value"],
                    )
                )
    status = AGREEMENT_BROKEN if disagreements else AGREEMENT_HELD
    return {
        "status": status,
        "disagreements": tuple(disagreements),
        "rounded_within_tolerance": tuple(rounded),
        "tolerance": limit,
        "findings": findings,
    }


def assess_annotation(entries):
    """Decide whether each entry declares its unit and its detail source."""
    without_unit = []
    without_source = []
    findings = []
    for entry in entries:
        if entry["kind"] == "numeric" and entry["unit"] is None:
            without_unit.append(entry["characteristic"])
            findings.append(
                "%s is quoted as a bare number with no unit on the page"
                % entry["characteristic"]
            )
        if entry["source_reference"] is None:
            without_source.append(entry["characteristic"])
            findings.append(
                "%s names no detail document the value was taken from"
                % entry["characteristic"]
            )
    status = (
        ANNOTATION_INCOMPLETE if (without_unit or without_source)
        else ANNOTATION_COMPLETE
    )
    return {
        "status": status,
        "without_unit": tuple(without_unit),
        "without_source_reference": tuple(without_source),
        "findings": findings,
    }


def sheet_line_count(entries, header_lines=None):
    """Rendered lines the sheet occupies, header included."""
    header = (
        DEFAULT_HEADER_LINES
        if header_lines is None
        else _require_positive_integer("header_lines", header_lines)
    )
    return header + sum(entry["rendered_lines"] for entry in entries)


def assess_page_budget(
    entries, header_lines=None, page_line_budget=None, caution_fraction=None
):
    """Decide whether the condensed overview still occupies one page."""
    budget = (
        DEFAULT_PAGE_LINE_BUDGET
        if page_line_budget is None
        else _require_positive_integer("page_line_budget", page_line_budget)
    )
    caution = (
        DEFAULT_PAGE_CAUTION_FRACTION
        if caution_fraction is None
        else _require_fraction("caution_fraction", caution_fraction)
    )
    used = sheet_line_count(entries, header_lines)
    fill = float(used) / float(budget)
    findings = []
    if used > budget:
        status = PAGE_OVER
        findings.append(
            "the sheet renders %d lines against a one page budget of %d"
            % (used, budget)
        )
    elif not _at_most(fill, caution):
        status = PAGE_NEARLY_FULL
        findings.append(
            "the sheet already fills %.1f%% of the page, leaving no room for the "
            "next revision" % (100.0 * fill)
        )
    else:
        status = PAGE_FITS
    return {
        "status": status,
        "rendered_lines": used,
        "page_line_budget": budget,
        "fill_share": fill,
        "findings": findings,
    }


def assess_issue_currency(sheet_issued_day, latest_detail_issued_day):
    """Decide whether the sheet is at least as recent as its detail."""
    sheet_day = _require_non_negative("sheet_issued_day", sheet_issued_day)
    detail_day = _require_non_negative(
        "latest_detail_issued_day", latest_detail_issued_day
    )
    lag = detail_day - sheet_day
    findings = []
    if _below(sheet_day, detail_day):
        status = ISSUE_BEHIND
        findings.append(
            "the sheet was issued on day %.2f while the detail it summarises "
            "moved on day %.2f" % (sheet_day, detail_day)
        )
    else:
        status = ISSUE_CURRENT
    return {
        "status": status,
        "sheet_issued_day": sheet_day,
        "latest_detail_issued_day": detail_day,
        "lag_days": lag,
        "findings": findings,
    }


def review_summary_design_sheet_item(case):
    """Full clause 7.3.14 summary design sheet review item with a verdict."""
    row = _require_mapping("case", case)
    required = row.get("required_characteristics")
    entries = normalize_entries(row.get("entries"), required)
    coverage = assess_coverage(entries, required)
    agreement = assess_agreement(entries, row.get("rounding_tolerance"))
    annotation = assess_annotation(entries)
    page = assess_page_budget(
        entries,
        row.get("header_lines"),
        row.get("page_line_budget"),
        row.get("caution_fraction"),
    )
    currency = assess_issue_currency(
        row.get("sheet_issued_day"), row.get("latest_detail_issued_day")
    )
    findings = (
        list(coverage["findings"])
        + list(agreement["findings"])
        + list(annotation["findings"])
        + list(page["findings"])
        + list(currency["findings"])
    )
    actions = []
    blocking = (
        coverage["status"] == COVERAGE_INCOMPLETE
        or agreement["status"] == AGREEMENT_BROKEN
        or page["status"] == PAGE_OVER
    )
    if annotation["without_unit"]:
        actions.append("declare a unit against every numeric characteristic")
    if annotation["without_source_reference"]:
        actions.append("reference the detail document behind every summarised value")
    if page["status"] == PAGE_NEARLY_FULL:
        actions.append("recover page room before the next sheet revision")
    if currency["status"] == ISSUE_BEHIND:
        actions.append("reissue the sheet against the current detail documents")
    if blocking:
        verdict = VERDICT_REJECTED
    elif actions:
        verdict = VERDICT_ACTIONED
    else:
        verdict = VERDICT_CLOSED
    return {
        "verdict": verdict,
        "entries": entries,
        "coverage": coverage,
        "agreement": agreement,
        "annotation": annotation,
        "page": page,
        "currency": currency,
        "actions": actions,
        "findings": findings,
    }
