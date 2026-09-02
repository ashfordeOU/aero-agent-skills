#!/usr/bin/env python3
"""Engineering report logic: structure checks for report deliverables.

The documentation-pack discipline for writing and reviewing engineering
reports: report anatomy (abstract, introduction, method, results,
discussion, conclusion, references), abstract length against the
recommended 150 to 300 word range, completeness of the deliverable,
units and uncertainty statements for every reported value, margin
statements with their basis, traceability of results to requirements,
review gates, and version control. All helpers are deterministic,
offline, stdlib only; invalid inputs raise ValueError.

Section names are matched case-insensitively with surrounding
whitespace stripped. Requirement ids are opaque strings compared
exactly. The recognized-unit set is the common SI and derived set
plus spelled-out forms; a statement passes units_statement_ok only
when it carries at least one number and one recognized unit.
"""

import re

NUMBER_RE = re.compile(r"\d")

REQUIRED_SECTIONS = [
    "abstract",
    "introduction",
    "method",
    "results",
    "discussion",
    "conclusion",
    "references",
]

ABSTRACT_MIN_WORDS = 150
ABSTRACT_MAX_WORDS = 300

# Lowercase word-boundary unit tokens, SI base/derived plus spell-outs.
KNOWN_UNITS = frozenset(
    [
        "n",
        "kn",
        "pa",
        "kpa",
        "mpa",
        "gpa",
        "m",
        "mm",
        "km",
        "cm",
        "g",
        "kg",
        "s",
        "ms",
        "min",
        "h",
        "k",
        "degc",
        "deg",
        "rad",
        "mol",
        "cd",
        "v",
        "w",
        "j",
        "hz",
        "t",
        "newton",
        "newtons",
        "pascal",
        "pascals",
        "meter",
        "meters",
        "metre",
        "metres",
        "kilogram",
        "kilograms",
        "gram",
        "grams",
        "second",
        "seconds",
        "kelvin",
        "hour",
        "hours",
        "minute",
        "minutes",
    ]
)

# Substring markers (lowercase) that signal a stated uncertainty.
UNCERTAINTY_MARKERS = (
    "\u00b1",
    "+/-",
    "+ / -",
    "plus or minus",
    "uncertainty",
    "tolerance",
    "confidence interval",
)


def _require_string_list(value, argname):
    """Raise ValueError unless value is a list of non-empty strings."""
    if not isinstance(value, list):
        raise ValueError("%s must be a list, got %r" % (argname, type(value).__name__))
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("%s entries must be non-empty strings" % argname)


def required_sections_verdict(sections_present):
    """Missing canonical report sections, in canonical order.

    Canonical sections: abstract, introduction, method, results,
    discussion, conclusion, references. Matching is case-insensitive
    with whitespace stripped; extra sections are ignored. Returns the
    list of missing sections (empty list means the report anatomy is
    complete). Raises ValueError when sections_present is not a list
    of non-empty strings.
    """
    _require_string_list(sections_present, "sections_present")
    present = {s.strip().lower() for s in sections_present}
    return [sec for sec in REQUIRED_SECTIONS if sec not in present]


def abstract_length_ok(word_count):
    """True when word_count is within the recommended 150 to 300 range.

    The recommended abstract length for an engineering report is 150
    to 300 words inclusive. Raises ValueError when word_count is not a
    number or is negative.
    """
    if isinstance(word_count, bool) or not isinstance(word_count, (int, float)):
        raise ValueError("word_count must be a number, got %r" % (word_count,))
    if word_count < 0:
        raise ValueError("word_count must be >= 0, got %r" % (word_count,))
    return ABSTRACT_MIN_WORDS <= word_count <= ABSTRACT_MAX_WORDS


def report_completeness_score(present, required):
    """Completeness ratio: required sections present divided by required.

    Ratio = |present intersect required| / |required|, rounded to 3
    decimals, in [0.0, 1.0]. Matching is case-insensitive with
    whitespace stripped; sections present beyond the required set do
    not count. Raises ValueError when either argument is not a list of
    non-empty strings or when required is empty.
    """
    _require_string_list(present, "present")
    _require_string_list(required, "required")
    if not required:
        raise ValueError("required must be a non-empty list")
    p = {s.strip().lower() for s in present}
    r = {s.strip().lower() for s in required}
    return round(len(p & r) / len(r), 3)


def units_statement_ok(statement):
    """True when the statement carries at least one number and one unit.

    A report statement about a measured or computed value must carry
    the unit. The statement passes when it contains a digit and a
    word-boundary token from the recognized unit set (SI base and
    derived symbols plus spelled-out forms). Returns False for empty
    statements or statements without a unit. Raises ValueError when
    statement is not a string.
    """
    if not isinstance(statement, str):
        raise ValueError("statement must be a string, got %r" % (statement,))
    s = statement.strip()
    if not s or not NUMBER_RE.search(s):
        return False
    low = s.lower()
    for unit in KNOWN_UNITS:
        if re.search(r"\b" + re.escape(unit) + r"\b", low):
            return True
    return False


def uncertainty_statement_ok(statement):
    """True when the statement carries a number and an uncertainty marker.

    The statement passes when it contains a digit and one of the
    uncertainty markers (plus/minus sign, "+/-", "plus or minus",
    "uncertainty", "tolerance", "confidence interval"). Returns False
    for statements without a number or without a marker. Raises
    ValueError when statement is not a string.
    """
    if not isinstance(statement, str):
        raise ValueError("statement must be a string, got %r" % (statement,))
    s = statement.strip()
    if not s or not NUMBER_RE.search(s):
        return False
    low = s.lower()
    return any(marker in low for marker in UNCERTAINTY_MARKERS)


def margin_statement_ok(statement):
    """True when the margin statement carries value, basis, and verdict.

    The statement passes when it contains the word "margin", a digit,
    and a basis word ("limit" or "ultimate"). The verdict is implied
    by the sign of the margin; this helper only enforces value plus
    basis. Returns False otherwise. Raises ValueError when statement is
    not a string.
    """
    if not isinstance(statement, str):
        raise ValueError("statement must be a string, got %r" % (statement,))
    s = statement.strip().lower()
    if not s or "margin" not in s or not NUMBER_RE.search(s):
        return False
    return ("limit" in s) or ("ultimate" in s)


def traceability_verdict(traced_ids, required_ids):
    """Missing requirement ids, sorted; [] means traceability is closed.

    traced_ids are the requirement ids with traced evidence in the
    report; required_ids are the ids the report must trace. Missing =
    required minus traced, returned sorted for a deterministic report
    line. Extra traced ids are ignored. Raises ValueError when either
    argument is not a list of non-empty strings.
    """
    _require_string_list(traced_ids, "traced_ids")
    _require_string_list(required_ids, "required_ids")
    return sorted(set(required_ids) - set(traced_ids))
