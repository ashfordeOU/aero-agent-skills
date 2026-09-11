#!/usr/bin/env python3
"""ECSS-E-ST-10C §7.2 Technical Specification content-structure check
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system-engineering specification's §7.2 sets out the overall requirements
a Technical Specification document must satisfy to be considered complete
and traceable -- mandatory section organisation (scope, applicable
documents, terms/definitions, requirements, verification in that order),
section-level responsibility assignments linking each section to a named
owner, technical references anchored to their document identifiers,
configuration-management baseline tagging (document number, issue,
revision on the title page), section-numbering format (hierarchical
numeric for body sections, single uppercase letter for annexes),
supplementary information isolated in dedicated lettered annexes, and
any content-distribution restrictions explicitly declared on the title
page. This module implements deterministic, offline checks for each of
the seven §7.2 content-structure dimensions; it does not generate TS
content itself.
"""

import re

MANDATORY_SECTION_KEYS = frozenset({
    "scope",
    "applicable_documents",
    "terms_and_definitions",
    "requirements",
    "verification",
})

# Defines the required relative ordering of mandatory sections.
REQUIRED_SECTION_ORDER = [
    "scope",
    "applicable_documents",
    "terms_and_definitions",
    "requirements",
    "verification",
]

REQUIRED_CM_FIELDS = ("doc_number", "issue", "revision")

_ANNEX_LETTER_RE = re.compile(r"^[A-Z]$")
_SECTION_NUMBER_RE = re.compile(r"^\d+(\.\d+)*$")


def validate_organisation(section_keys):
    """Check that section_keys contains all mandatory keys and that the
    mandatory keys appear in the required relative order.

    section_keys: ordered iterable of string section identifiers.
    Returns a list of violation dicts (empty when compliant). Does not
    mutate section_keys.
    Raises TypeError if section_keys contains a non-string element.
    """
    keys = list(section_keys)
    for k in keys:
        if not isinstance(k, str):
            raise TypeError("section key must be a string, got %r" % (k,))
    violations = []

    for required in MANDATORY_SECTION_KEYS:
        if required not in keys:
            violations.append({
                "issue": "missing_mandatory_section",
                "section": required,
            })

    present_in_order = [k for k in REQUIRED_SECTION_ORDER if k in keys]
    for i, key_a in enumerate(present_in_order):
        for key_b in present_in_order[i + 1:]:
            if keys.index(key_a) > keys.index(key_b):
                violations.append({
                    "issue": "section_order_violation",
                    "section_must_precede": key_a,
                    "found_after": key_b,
                })
    return violations


def check_responsibility(sections):
    """Check that each section carries a non-empty owner assignment.

    sections: iterable of dicts, each with 'key' (str) and 'owner'
    (str or None). A missing or empty owner is flagged.
    Returns a list of violation dicts (empty when compliant). Does not
    mutate sections.
    """
    violations = []
    for section in sections:
        if not section.get("owner"):
            violations.append({
                "issue": "missing_section_owner",
                "section": section["key"],
            })
    return violations


def check_technical_references(references):
    """Check that every technical reference carries a document identifier.

    references: iterable of dicts, each with 'title' (str) and
    optionally 'doc_id' (str). A missing or empty doc_id is flagged.
    Returns a list of violation dicts (empty when compliant). Does not
    mutate references.
    """
    violations = []
    for ref in references:
        if not ref.get("doc_id"):
            violations.append({
                "issue": "missing_reference_doc_id",
                "title": ref.get("title", "<untitled>"),
            })
    return violations


def check_cm_tagging(doc_meta):
    """Check that the document title-page metadata carries all mandatory
    CM fields: doc_number, issue, revision.

    doc_meta: dict with any subset of the required CM fields.
    Returns a list of violation dicts (empty when compliant). Does not
    mutate doc_meta.
    """
    violations = []
    for field in REQUIRED_CM_FIELDS:
        if not doc_meta.get(field):
            violations.append({
                "issue": "missing_cm_field",
                "field": field,
            })
    return violations


def validate_section_numbering(numbers):
    """Check that each body section number follows hierarchical numeric
    format: one or more digit groups separated by dots (e.g. "1", "2.3",
    "4.1.2"). Annex identifiers (letters) must not be included here;
    use check_supplementary_info for annexes.

    numbers: iterable of section number strings.
    Returns a list of violation dicts for non-conforming entries.
    Raises ValueError for a non-string element.
    """
    violations = []
    for number in numbers:
        if not isinstance(number, str):
            raise ValueError(
                "section number must be a string, got %r" % (number,)
            )
        if not _SECTION_NUMBER_RE.match(number):
            violations.append({
                "issue": "invalid_section_number_format",
                "number": number,
                "detail": "expected hierarchical numeric e.g. '1', '1.2', '1.2.3'",
            })
    return violations


def check_supplementary_info(annex_entries):
    """Check that each supplementary-information annex carries a single
    uppercase-letter identifier (A, B, C, ...).

    annex_entries: iterable of dicts with 'key' (str) and 'letter'
    (str or None). A missing, empty, or non-uppercase-letter identifier
    is flagged.
    Returns a list of violation dicts (empty when compliant). Does not
    mutate annex_entries.
    """
    violations = []
    for entry in annex_entries:
        letter = entry.get("letter") or ""
        if not _ANNEX_LETTER_RE.match(letter):
            violations.append({
                "issue": "invalid_annex_letter",
                "key": entry["key"],
                "letter": letter,
                "detail": "annex identifier must be a single uppercase letter A-Z",
            })
    return violations


def check_restrictions(doc_meta):
    """Check that any content-distribution restriction is explicitly
    declared via a restriction_statement in the document metadata.

    doc_meta: dict with 'has_restriction' (bool) and optionally
    'restriction_statement' (str). A document that sets has_restriction
    True without a non-empty restriction_statement is flagged.
    Returns a list of violation dicts (empty when compliant). Does not
    mutate doc_meta.
    """
    violations = []
    if doc_meta.get("has_restriction") and not doc_meta.get("restriction_statement"):
        violations.append({
            "issue": "undeclared_restriction",
            "detail": "document has_restriction is True but restriction_statement is absent",
        })
    return violations


def full_ts_structure_review(ts_doc):
    """Aggregate ECSS-E-ST-10C §7.2 content-structure review for one TS.

    ts_doc: {
        "section_keys": [...],              # ordered list of str section keys
        "sections": [{key, owner}, ...],    # for responsibility check
        "technical_references": [...],      # list of {title, doc_id?}
        "doc_meta": {                       # title-page metadata
            "doc_number", "issue", "revision",
            "has_restriction", "restriction_statement", ...
        },
        "section_numbers": [...],           # body section number strings
        "annexes": [{key, letter}, ...],    # supplementary-info annex entries
    }
    Returns a dict keyed by dimension name, each value a list of
    violation dicts. Does not mutate ts_doc.
    """
    return {
        "organisation": validate_organisation(ts_doc.get("section_keys", [])),
        "responsibility": check_responsibility(ts_doc.get("sections", [])),
        "technical_references": check_technical_references(
            ts_doc.get("technical_references", [])
        ),
        "cm_tagging": check_cm_tagging(ts_doc.get("doc_meta", {})),
        "format": validate_section_numbering(ts_doc.get("section_numbers", [])),
        "supplementary_info": check_supplementary_info(ts_doc.get("annexes", [])),
        "restrictions": check_restrictions(ts_doc.get("doc_meta", {})),
    }


def is_ts_structure_compliant(review):
    """True when every dimension in a full_ts_structure_review result
    has an empty violation list -- the TS satisfies all §7.2 dimensions."""
    return all(len(v) == 0 for v in review.values())
