"""Requirements elicitation helpers for systems engineering.

Deterministic, offline, stdlib-only helpers for capturing system
requirements from stakeholder needs and operational scenarios and for
assessing requirement statement quality: shall clause counting for
atomicity, weasel word detection for unambiguity, measurable bound
checking for verifiability, single-verb structure checking, traceability
field checks, the per-statement quality assessment, and the elicitation
completeness checklist.

Contract exercised by scripts/test_requirements_elicitation.py.
"""

import re

WEASEL_WORDS = (
    "approximately",
    "etc",
    "suitable",
    "and/or",
    "as required",
    "timely",
    "minimize",
    "maximize",
)

VERIFICATION_METHODS = ("test", "analysis", "demonstration", "inspection")

TRACE_FIELDS = ("id", "source")

MODAL_RE = re.compile(r"\b(shall|must|will|should|may)\b")

BOUND_PHRASES = (
    "within",
    "less than",
    "greater than",
    "at least",
    "at most",
    "no more than",
    "no less than",
    "not exceed",
    "exactly",
    "between",
)


def count_shall_clauses(text):
    """Return the number of shall clauses in the requirement statement.

    Atomicity requires exactly one shall clause per statement; two
    shall clauses in one statement are two requirements that must be
    split during elicitation, before the requirements baseline.

    Raises ValueError for a non-string text.
    """
    if not isinstance(text, str):
        raise ValueError("requirement text must be a string, got %r" % (text,))
    return len(re.findall(r"\bshall\b", text.lower()))


def find_weasel_words(text):
    """Return the sorted list of weasel words found in the statement.

    Weasel words such as approximately, etc, suitable, and/or, as
    required, timely, minimize, and maximize carry no measurable
    acceptance bound, so a statement containing one is ambiguous and
    cannot be verified as written.

    Raises ValueError for a non-string text.
    """
    if not isinstance(text, str):
        raise ValueError("requirement text must be a string, got %r" % (text,))
    lowered = text.lower()
    found = []
    for term in WEASEL_WORDS:
        if re.search(r"\b" + re.escape(term) + r"\b", lowered):
            found.append(term)
    return sorted(found)


def has_measurable_bound(text):
    """Return True when the statement states a measurable acceptance bound.

    A measurable bound is a numeric value combined with a bound phrase
    such as within, at least, at most, not exceed, exactly, or between.
    A statement with no numeric value or no bound phrase cannot be
    verified against a measurable acceptance criterion.

    Raises ValueError for a non-string text.
    """
    if not isinstance(text, str):
        raise ValueError("requirement text must be a string, got %r" % (text,))
    lowered = text.lower()
    if not re.search(r"\d", lowered):
        return False
    return any(phrase in lowered for phrase in BOUND_PHRASES)


def check_single_verb(text):
    """Return (ok, extras) for the single-verb structure check.

    A requirement statement uses exactly one modal verb and that verb
    is shall. ok is True only in that case; extras is the sorted list
    of every other modal verb found, plus a shall xN entry when the
    shall count is not exactly one. must, will, should, or may in the
    same statement blur the obligation level.

    Raises ValueError for a non-string text.
    """
    if not isinstance(text, str):
        raise ValueError("requirement text must be a string, got %r" % (text,))
    verbs = MODAL_RE.findall(text.lower())
    extras = []
    shall_count = verbs.count("shall")
    if shall_count != 1:
        extras.append("shall x%d" % shall_count)
    for modal in sorted(set(verbs) - {"shall"}):
        extras.append(modal)
    return not extras, sorted(extras)


def check_traceability(requirement):
    """Return the traceability field verdict for one requirement mapping.

    The required trace fields are id and source; a statement with no
    source cannot be traced to a stakeholder need or operational
    scenario. The optional parent field is recorded when present. The
    verdict dict carries complete and the sorted missing field list.

    Raises ValueError for a non-mapping input.
    """
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    missing = []
    for field in TRACE_FIELDS:
        value = requirement.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return {"complete": not missing, "missing": sorted(missing)}


def assess_requirement_statement(requirement):
    """Return the structured quality assessment for one statement.

    The mapping carries id, text, source, and method, with optional
    parent; only text is required to exist, while a missing or blank
    id, source, or method is a quality failure that flags in the
    assessment rather than raising. The assessment scores atomicity
    (one shall clause), verifiability (measurable bound plus a method
    in test, analysis, demonstration, or inspection), unambiguity (no
    weasel words), single-verb structure, and traceability fields, and
    returns the issues list and the ready or fix verdict.

    Raises ValueError for a missing text key or a non-string text.
    """
    if "text" not in requirement:
        raise ValueError("requirement missing key 'text'")
    if not isinstance(requirement["text"], str):
        raise ValueError("requirement text must be a string")
    text = requirement["text"]

    shall_count = count_shall_clauses(text)
    weasel = find_weasel_words(text)
    single_verb_ok, verb_extras = check_single_verb(text)
    trace = check_traceability(requirement)
    method = requirement.get("method")
    method_ok = method in VERIFICATION_METHODS
    verifiable = has_measurable_bound(text) and method_ok

    atomicity = shall_count == 1
    unambiguity = not weasel

    issues = []
    if not atomicity:
        issues.append("atomicity: %d shall clauses, expected 1" % shall_count)
    if not verifiable:
        if not has_measurable_bound(text):
            issues.append("verifiability: no measurable acceptance bound")
        if method is None or (isinstance(method, str) and not method.strip()):
            issues.append("verifiability: no method assigned")
        elif not method_ok:
            issues.append(
                "verifiability: method %r not in %s"
                % (method, ", ".join(VERIFICATION_METHODS))
            )
    if not unambiguity:
        issues.append("unambiguity: weasel words %s" % ", ".join(weasel))
    if not single_verb_ok:
        issues.append("single-verb: extra modals %s" % ", ".join(verb_extras))
    if not trace["complete"]:
        issues.append("traceability: missing %s" % ", ".join(trace["missing"]))

    return {
        "id": requirement["id"],
        "text": text,
        "shall_clauses": shall_count,
        "weasel_words": weasel,
        "single_verb": single_verb_ok,
        "verb_extras": verb_extras,
        "traceability": trace,
        "quality_checks": {
            "atomicity": atomicity,
            "verifiability": verifiable,
            "unambiguity": unambiguity,
            "single_verb": single_verb_ok,
            "traceability": trace["complete"],
        },
        "issues": sorted(issues),
        "verdict": "ready" if not issues else "fix",
    }


def elicitation_completeness_check(needs, scenarios, log_entries):
    """Return the elicitation completeness checklist verdict.

    needs is the list of stakeholder needs, scenarios the list of
    operational scenarios, and log_entries the list of requirements
    elicitation log entries, each a mapping with need and scenario keys
    naming the source covered by the entry. A need or scenario with no
    covering log entry is a gap. The verdict dict carries the covered
    fractions, the sorted missing lists, and the complete or gaps
    verdict. Empty needs and scenarios lists return complete.

    Raises ValueError for a non-list input.
    """
    if not isinstance(needs, list) or not isinstance(scenarios, list):
        raise ValueError("needs and scenarios must be lists")
    if not isinstance(log_entries, list):
        raise ValueError("log entries must be a list, got %r" % (log_entries,))

    covered_needs = {entry.get("need") for entry in log_entries}
    covered_scenarios = {entry.get("scenario") for entry in log_entries}

    missing_needs = sorted(set(needs) - covered_needs)
    missing_scenarios = sorted(set(scenarios) - covered_scenarios)

    needs_covered = (
        len(set(needs) & covered_needs) / float(len(needs)) if needs else 1.0
    )
    scenarios_covered = (
        len(set(scenarios) & covered_scenarios) / float(len(scenarios))
        if scenarios
        else 1.0
    )

    complete = not missing_needs and not missing_scenarios
    return {
        "needs_covered": needs_covered,
        "scenarios_covered": scenarios_covered,
        "missing_needs": missing_needs,
        "missing_scenarios": missing_scenarios,
        "complete": complete,
        "verdict": "complete" if complete else "gaps",
    }
