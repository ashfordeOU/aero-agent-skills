"""Additional-comments subclause audit for SpaceWire service primitives.

Anchor: ECSS-E-ST-50-53 clause 5.2.2.5 (the additional-comments subclause: the
closing informative note on a service primitive). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the record and resolve the note; absent, null and whitespace-only
   are the same defect.
2. Recognise the declared empty forms, which are compliant and skip the
   content checks.
3. Scan for normative wording, which would create an unnumbered requirement.
4. Extract dotted clause references and resolve them against the clause index.
5. Measure the share of the note's informative tokens already carried by the
   four preceding subclauses of the same primitive, and compare it with the
   ceiling through a named tolerance.
6. Apply the word budget and roll every primitive up into a compliant count.
"""

import re

__all__ = [
    "DUPLICATION_CEILING",
    "DUPLICATION_TOLERANCE",
    "WORD_BUDGET",
    "EMPTY_FORMS",
    "NORMATIVE_MARKERS",
    "UPSTREAM_SUBCLAUSES",
    "STOPWORDS",
    "normalize_note",
    "is_explicit_empty",
    "find_normative_wording",
    "extract_clause_references",
    "unresolved_references",
    "informative_token_set",
    "duplication_share",
    "word_count",
    "assess_additional_comments",
    "assess_comment_set",
]

# Share of the note's informative tokens that may already appear upstream
# before the note is a copy rather than a comment.
DUPLICATION_CEILING = 0.5

# The share is a ratio of integer counts; a note built to sit on the ceiling
# lands there exactly. Absorb the representation error instead of moving the
# ceiling.
DUPLICATION_TOLERANCE = 1e-9

# Normalised word budget for one note.
WORD_BUDGET = 120

# The forms that declare the subclause deliberately empty.
EMPTY_FORMS = ("none", "no additional comments", "not applicable", "nothing further")

NORMATIVE_MARKERS = (
    "shall",
    "must",
    "is required to",
    "are required to",
    "it is mandatory",
    "is prohibited",
)

# The four preceding subclauses the note is compared against.
UPSTREAM_SUBCLAUSES = ("function", "semantics", "when_generated", "effect_on_receipt")

STOPWORDS = frozenset(
    """a an and are as at be by for from has have in into is it its of on or that the this
    to with which while when whose not no than then there these those such""".split()
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_CLAUSE_RE = re.compile(r"\b\d+(?:\.\d+)+\b")


def _text_or_none(value, label):
    """Return a str or None, raising when the value is neither."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("%s must be text or null, got %r" % (label, type(value).__name__))
    return value


def normalize_note(text):
    """Return the note with collapsed whitespace and no surrounding space."""
    if not isinstance(text, str):
        raise ValueError("note must be a string, got %r" % type(text).__name__)
    return " ".join(text.split())


def is_explicit_empty(text):
    """True when the note declares the subclause deliberately empty."""
    stripped = normalize_note(text).strip(" .").lower()
    return stripped in EMPTY_FORMS


def find_normative_wording(text):
    """Return the normative markers present in an informative note."""
    low = normalize_note(text).lower()
    return tuple(marker for marker in NORMATIVE_MARKERS if marker in low)


def extract_clause_references(text):
    """Return the dotted clause numbers the note cites, in order of appearance."""
    out = []
    for match in _CLAUSE_RE.findall(normalize_note(text)):
        if match not in out:
            out.append(match)
    return tuple(out)


def unresolved_references(references, clause_index):
    """Return the cited clause numbers that the clause index does not declare."""
    if not isinstance(clause_index, (list, tuple, set, frozenset, dict)):
        raise ValueError("clause index must be a collection of clause numbers")
    known = {str(item).strip() for item in clause_index}
    return tuple(ref for ref in references if ref not in known)


def informative_token_set(text):
    """Return the lowercase non-stopword token set of a piece of text."""
    if not isinstance(text, str):
        raise ValueError("text must be a string, got %r" % type(text).__name__)
    return frozenset(
        token for token in _TOKEN_RE.findall(text.lower()) if token not in STOPWORDS
    )


def duplication_share(note, upstream_texts):
    """Return the share of the note's informative tokens already used upstream."""
    if not isinstance(upstream_texts, (list, tuple)):
        raise ValueError("upstream texts must be a sequence")
    note_tokens = informative_token_set(note)
    if not note_tokens:
        return 0.0
    upstream = set()
    for index, text in enumerate(upstream_texts):
        if text is None:
            continue
        if not isinstance(text, str):
            raise ValueError("upstream text %d must be text or null" % index)
        upstream |= informative_token_set(text)
    return len(note_tokens & upstream) / float(len(note_tokens))


def word_count(text):
    """Return the normalised word count of a note."""
    normalised = normalize_note(text)
    return len(normalised.split()) if normalised else 0


def assess_additional_comments(record, clause_index=(), index=0):
    """Assess the clause 5.2.2.5 note of one primitive."""
    if not isinstance(record, dict):
        raise ValueError("primitive record %d must be a mapping" % index)
    name = _text_or_none(record.get("primitive"), "primitive record %d name" % index)
    if name is None or not name.strip():
        raise ValueError("primitive record %d has no primitive name" % index)
    name = name.strip()
    raw = _text_or_none(record.get("additional_comments"), "note of %s" % name)
    result = {
        "primitive": name,
        "note": None,
        "present": False,
        "explicit_empty": False,
        "normative_wording": (),
        "references": (),
        "unresolved_references": (),
        "duplication_share": 0.0,
        "word_count": 0,
        "findings": [],
        "compliant": False,
    }
    note = normalize_note(raw) if isinstance(raw, str) else ""
    if not note:
        result["findings"].append(
            "%s has no additional-comments subclause; state it as empty if there is "
            "nothing to add" % name
        )
        return result
    result["note"] = note
    result["present"] = True
    result["word_count"] = word_count(note)
    if is_explicit_empty(note):
        result["explicit_empty"] = True
        result["compliant"] = True
        return result
    result["normative_wording"] = find_normative_wording(note)
    result["references"] = extract_clause_references(note)
    result["unresolved_references"] = unresolved_references(result["references"], clause_index)
    upstream = [record.get(key) for key in UPSTREAM_SUBCLAUSES]
    result["duplication_share"] = duplication_share(note, upstream)
    if result["normative_wording"]:
        result["findings"].append(
            "%s note uses normative wording (%s); an informative subclause cannot carry "
            "a requirement" % (name, ", ".join(result["normative_wording"]))
        )
    if result["unresolved_references"]:
        result["findings"].append(
            "%s note cites clause %s, which the clause index does not declare"
            % (name, ", ".join(result["unresolved_references"]))
        )
    if result["duplication_share"] > DUPLICATION_CEILING + DUPLICATION_TOLERANCE:
        result["findings"].append(
            "%s note repeats %.1f%% of its informative tokens from the preceding "
            "subclauses, ceiling %.1f%%"
            % (name, 100.0 * result["duplication_share"], 100.0 * DUPLICATION_CEILING)
        )
    if result["word_count"] > WORD_BUDGET:
        result["findings"].append(
            "%s note runs to %d words, budget %d" % (name, result["word_count"], WORD_BUDGET)
        )
    result["compliant"] = not result["findings"]
    return result


def assess_comment_set(records, clause_index=()):
    """Audit the clause 5.2.2.5 subclause across a whole service definition."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of primitive records")
    results = []
    seen = set()
    for index, record in enumerate(records):
        result = assess_additional_comments(record, clause_index, index)
        key = result["primitive"].lower()
        if key in seen:
            raise ValueError(
                "primitive %s is declared twice in the service definition" % result["primitive"]
            )
        seen.add(key)
        results.append(result)
    findings = []
    for result in results:
        findings.extend(result["findings"])
    compliant_count = sum(1 for r in results if r["compliant"])
    return {
        "primitives": results,
        "findings": findings,
        "explicit_empty_count": sum(1 for r in results if r["explicit_empty"]),
        "compliant_count": compliant_count,
        "total": len(results),
        "compliant": compliant_count == len(results),
    }
