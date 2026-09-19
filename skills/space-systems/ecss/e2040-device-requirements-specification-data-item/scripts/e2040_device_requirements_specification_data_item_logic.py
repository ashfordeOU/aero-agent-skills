#!/usr/bin/env python3
"""Device requirements specification contents (ECSS-E-ST-20-40C Annex A).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The data item fixes what a device requirements document has to contain:
the function the device performs, the performance it has to reach, the
interfaces it presents, and the quality it has to hold. Checking a
submitted document is therefore two passes, and only the second one is
worth much:

* presence -- all four mandatory content areas exist and none is empty.
  An empty heading is the commonest way a document looks complete and
  is not;
* substance -- each statement inside a content area is written so it can
  be answered. Every statement needs an identifier and a verification
  method; a performance statement needs a quantity with a unit, because
  a performance requirement without a number cannot be verified; an
  interface statement needs the counterpart it is an interface TO; and
  a quality statement needs the criterion it is accepted against.

Vague wording is caught in the same pass. "Adequate margin" reads like a
requirement and cannot be verified by any of the four methods, so it is
reported rather than counted as content.
"""

import re

# The four content areas the data item makes mandatory.
FUNCTION = "function"
PERFORMANCE = "performance"
INTERFACE = "interface"
QUALITY = "quality"
MANDATORY_SECTIONS = (FUNCTION, PERFORMANCE, INTERFACE, QUALITY)

# Section heading spellings folded onto the canonical four.
_SECTION_ALIASES = {
    "function": FUNCTION,
    "functions": FUNCTION,
    "functional": FUNCTION,
    "functional requirements": FUNCTION,
    "performance": PERFORMANCE,
    "performances": PERFORMANCE,
    "performance requirements": PERFORMANCE,
    "interface": INTERFACE,
    "interfaces": INTERFACE,
    "interface requirements": INTERFACE,
    "quality": QUALITY,
    "quality requirements": QUALITY,
    "quality assurance requirements": QUALITY,
}

# The four verification methods a statement may nominate.
VERIFICATION_METHODS = ("analysis", "review-of-design", "inspection", "test")
_METHOD_ALIASES = {
    "analysis": "analysis",
    "a": "analysis",
    "review-of-design": "review-of-design",
    "review of design": "review-of-design",
    "rod": "review-of-design",
    "design review": "review-of-design",
    "inspection": "inspection",
    "i": "inspection",
    "test": "test",
    "t": "test",
}

# Wording that reads as a requirement but cannot be answered.
VAGUE_TERMS = (
    "adequate",
    "appropriate",
    "as necessary",
    "as required",
    "if possible",
    "minimal",
    "reasonable",
    "state of the art",
    "sufficient",
    "suitable",
    "user friendly",
    "where practical",
)

_STATEMENT_KEYS = (
    "id",
    "text",
    "verification_method",
    "value",
    "unit",
    "counterpart",
    "acceptance_criterion",
)


def normalize_section(name):
    """Fold a heading onto one of the four content areas, or keep it as extra."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("section name must be a non-empty string, got %r" % (name,))
    key = " ".join(name.strip().lower().replace("_", " ").split())
    return _SECTION_ALIASES.get(key, key)


def normalize_method(value):
    """Fold a verification method onto the four recognised names."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("verification_method must be a non-empty string")
    key = " ".join(value.strip().lower().replace("_", " ").split())
    if key in _METHOD_ALIASES:
        return _METHOD_ALIASES[key]
    raise ValueError(
        "unknown verification method %r; use one of %s"
        % (value, ", ".join(VERIFICATION_METHODS))
    )


def vague_terms_in(text):
    """Unverifiable wording found in a statement, in canonical spelling."""
    if not isinstance(text, str):
        raise ValueError("text must be a string, got %r" % (text,))
    lowered = " ".join(text.lower().replace("-", " ").split())
    found = []
    for term in VAGUE_TERMS:
        pattern = r"(?<![a-z])%s(?![a-z])" % re.escape(term)
        if re.search(pattern, lowered):
            found.append(term)
    return found


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_statement(statement, index=0, section="unknown"):
    """Check the shape of one requirement statement and return it resolved."""
    if not isinstance(statement, dict):
        raise ValueError("%s[%d] must be a mapping" % (section, index))
    unknown = sorted(set(statement) - set(_STATEMENT_KEYS))
    if unknown:
        raise ValueError(
            "%s[%d] has unknown keys: %s" % (section, index, ", ".join(unknown))
        )
    resolved = dict(statement)
    req_id = statement.get("id", "")
    if not isinstance(req_id, str):
        raise ValueError("%s[%d].id must be a string" % (section, index))
    resolved["id"] = req_id.strip()
    text = statement.get("text", "")
    if not isinstance(text, str):
        raise ValueError("%s[%d].text must be a string" % (section, index))
    resolved["text"] = text.strip()
    if "value" in statement and statement["value"] is not None:
        if not _is_number(statement["value"]):
            raise ValueError("%s[%d].value must be a real number" % (section, index))
    return resolved


def statement_findings(statement, section, index=0):
    """Everything wrong with one statement, as finding dictionaries."""
    resolved = validate_statement(statement, index, section)
    findings = []
    where = "%s[%d]" % (section, index)
    if not resolved["id"]:
        findings.append(
            {
                "code": "statement-without-identifier",
                "section": section,
                "where": where,
                "detail": "a statement with no identifier cannot be traced or "
                "verified against",
            }
        )
    if not resolved["text"]:
        findings.append(
            {
                "code": "statement-without-text",
                "section": section,
                "where": where,
                "requirement_id": resolved["id"],
                "detail": "the statement carries an identifier and no requirement",
            }
        )
    method = resolved.get("verification_method")
    if method is None or (isinstance(method, str) and not method.strip()):
        findings.append(
            {
                "code": "statement-without-verification-method",
                "section": section,
                "where": where,
                "requirement_id": resolved["id"],
                "detail": "no method nominated from %s"
                % ", ".join(VERIFICATION_METHODS),
            }
        )
    else:
        normalize_method(method)
    vague = vague_terms_in(resolved["text"])
    if vague:
        findings.append(
            {
                "code": "unverifiable-wording",
                "section": section,
                "where": where,
                "requirement_id": resolved["id"],
                "terms": vague,
                "detail": "wording %s cannot be answered by any verification "
                "method" % ", ".join(vague),
            }
        )
    if section == PERFORMANCE:
        value = resolved.get("value")
        unit = resolved.get("unit")
        if not _is_number(value) or not isinstance(unit, str) or not unit.strip():
            findings.append(
                {
                    "code": "performance-without-quantity",
                    "section": section,
                    "where": where,
                    "requirement_id": resolved["id"],
                    "detail": "a performance requirement needs a value and a unit",
                }
            )
    if section == INTERFACE:
        counterpart = resolved.get("counterpart")
        if not isinstance(counterpart, str) or not counterpart.strip():
            findings.append(
                {
                    "code": "interface-without-counterpart",
                    "section": section,
                    "where": where,
                    "requirement_id": resolved["id"],
                    "detail": "an interface requirement has to name what it "
                    "interfaces to",
                }
            )
    if section == QUALITY:
        criterion = resolved.get("acceptance_criterion")
        if not isinstance(criterion, str) or not criterion.strip():
            findings.append(
                {
                    "code": "quality-without-acceptance-criterion",
                    "section": section,
                    "where": where,
                    "requirement_id": resolved["id"],
                    "detail": "a quality requirement has to say what it is accepted "
                    "against",
                }
            )
    return findings


def section_score(statements, section):
    """Fraction of a section's statements that carry no finding."""
    if not isinstance(statements, (list, tuple)):
        raise ValueError("section %s must hold a list of statements" % section)
    if len(statements) == 0:
        return 0.0
    clean = 0
    for index, statement in enumerate(statements):
        if not statement_findings(statement, section, index):
            clean += 1
    return clean / len(statements)


def completeness_score(section_scores):
    """Mean score across the four mandatory content areas."""
    if not isinstance(section_scores, dict):
        raise ValueError("section_scores must be a mapping")
    missing = [name for name in MANDATORY_SECTIONS if name not in section_scores]
    if missing:
        raise ValueError(
            "section_scores missing mandatory areas: %s" % ", ".join(missing)
        )
    total = 0.0
    for name in MANDATORY_SECTIONS:
        value = section_scores[name]
        if not _is_number(value) or not 0.0 <= float(value) <= 1.0:
            raise ValueError("section_scores[%s] must lie in [0, 1]" % name)
        total += float(value)
    return total / len(MANDATORY_SECTIONS)


def evaluate_requirements_specification(document):
    """Full Annex A assessment of one device requirements specification.

    Returns the resolved sections, the per-section and overall scores, the
    findings and the verdict.
    """
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping of section name to statements")
    if len(document) == 0:
        raise ValueError("document must carry at least one section")

    sections = {}
    for name, statements in document.items():
        canonical = normalize_section(name)
        if canonical in sections:
            raise ValueError("section %r declared twice" % canonical)
        if not isinstance(statements, (list, tuple)):
            raise ValueError("section %r must hold a list of statements" % canonical)
        sections[canonical] = list(statements)

    findings = []
    for name in MANDATORY_SECTIONS:
        if name not in sections:
            findings.append(
                {
                    "code": "mandatory-section-absent",
                    "section": name,
                    "detail": "the data item requires a %s content area" % name,
                }
            )
        elif len(sections[name]) == 0:
            findings.append(
                {
                    "code": "mandatory-section-empty",
                    "section": name,
                    "detail": "the %s heading exists and holds no requirement" % name,
                }
            )

    seen = {}
    duplicates = []
    for name in sorted(sections):
        for index, statement in enumerate(sections[name]):
            resolved = validate_statement(statement, index, name)
            req_id = resolved["id"]
            if not req_id:
                continue
            if req_id in seen:
                duplicates.append(req_id)
            else:
                seen[req_id] = name
    if duplicates:
        findings.append(
            {
                "code": "duplicate-requirement-identifier",
                "requirements": sorted(set(duplicates)),
                "detail": "identifiers %s appear more than once, so verification "
                "cannot be traced" % ", ".join(sorted(set(duplicates))),
            }
        )

    scores = {}
    for name in MANDATORY_SECTIONS:
        statements = sections.get(name, [])
        scores[name] = section_score(statements, name)
        for index, statement in enumerate(statements):
            findings.extend(statement_findings(statement, name, index))

    extras = sorted(set(sections) - set(MANDATORY_SECTIONS))

    return {
        "sections_present": sorted(sections),
        "extra_sections": extras,
        "statement_count": sum(len(v) for v in sections.values()),
        "section_scores": scores,
        "completeness_score": completeness_score(scores),
        "findings": findings,
        "compliant": not findings,
    }
