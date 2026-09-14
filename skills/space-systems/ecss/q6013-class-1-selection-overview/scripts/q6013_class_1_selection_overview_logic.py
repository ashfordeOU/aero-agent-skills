#!/usr/bin/env python3
"""Selection duties framing a Class 1 commercial EEE component choice.

Anchor: ECSS-Q-ST-60-13C clause 4.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Class 1 is the highest assurance category a project can put a
commercial part into, and the clause that opens the selection subject
is a framing clause: before any single rule is applied to any single
part, it fixes what the selection OWES and who owes it. Two mistakes
follow from ignoring that framing.

The first is treating every duty as a per-part duty. The usage
justification, the procurement route, the radiation suitability, the
lifetime assessment and the evaluation plan really are owed once per
candidate component -- each part earns its own. The customer agreement
and the obsolescence continuity plan are owed once per programme. A
tool that re-owes a programme duty on every part reports a hundred
open duties where one decision was outstanding, and a project reading
that list cannot find the one that mattered.

The second is collapsing "no record" into "failed". The two are
dispositioned by different people through different paperwork. A duty
recorded as open has an owner working it; a duty recorded as rejected
has an owner who has answered and the answer was no; a duty with no
record at all has nobody, and nobody can say whether it was skipped,
lost or never scheduled. Absence is the worst of the three and is kept
separate so it can be chased.

    per-component   commercial-usage-justification
                    franchised-procurement-route
                    radiation-suitability-assessment
                    reliability-and-lifetime-assessment
                    component-evaluation-plan
    per-programme   customer-agreement-record
                    obsolescence-continuity-plan

The duty set, the owner roles, the class-to-duty mapping and the
coverage minimum below are declared project policy, not physical
constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ASSURANCE_CLASSES = ("class-1", "class-2", "class-3")

PER_COMPONENT_DUTIES = (
    "commercial-usage-justification",
    "franchised-procurement-route",
    "radiation-suitability-assessment",
    "reliability-and-lifetime-assessment",
    "component-evaluation-plan",
)

PROGRAMME_DUTIES = (
    "customer-agreement-record",
    "obsolescence-continuity-plan",
)

SELECTION_DUTIES = PER_COMPONENT_DUTIES + PROGRAMME_DUTIES

DUTY_OWNERS = {
    "commercial-usage-justification": "design-authority",
    "franchised-procurement-route": "procurement-authority",
    "radiation-suitability-assessment": "product-assurance",
    "reliability-and-lifetime-assessment": "product-assurance",
    "component-evaluation-plan": "product-assurance",
    "customer-agreement-record": "customer",
    "obsolescence-continuity-plan": "procurement-authority",
}

# Class 1 owes the whole set. Lower categories owe a declared subset;
# the duties dropped are the ones a lower category buys its relief with.
DUTIES_BY_CLASS = {
    "class-1": SELECTION_DUTIES,
    "class-2": tuple(d for d in SELECTION_DUTIES if d != "component-evaluation-plan"),
    "class-3": (
        "commercial-usage-justification",
        "franchised-procurement-route",
        "customer-agreement-record",
    ),
}

RECORD_HELD = "held"
RECORD_OPEN = "open"
RECORD_REJECTED = "rejected"
RECORD_STATES = (RECORD_HELD, RECORD_OPEN, RECORD_REJECTED)

DUTY_HELD = "duty-held"
DUTY_OPEN = "duty-open"
DUTY_REJECTED = "duty-rejected"
DUTY_NO_RECORD = "duty-not-recorded"

DUTY_RANK = {
    DUTY_NO_RECORD: 0,
    DUTY_REJECTED: 1,
    DUTY_OPEN: 2,
    DUTY_HELD: 3,
}

COMPONENT_READY = "component-selection-ready"
COMPONENT_NOT_READY = "component-selection-not-ready"

SELECTION_READY = "selection-ready"
SELECTION_NOT_READY = "selection-not-ready"

DEFAULT_SELECTION_POLICY = {
    "min_duty_coverage": 1.0,
    "carry_dispositioned_open": False,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if not 0.0 < value <= 1.0:
        raise ValueError(
            "%s must sit above zero and at or below one, got %r" % (name, value)
        )
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A coverage share is a quotient of two duty counts, so a selection
    that holds exactly the declared share can evaluate a unit in the
    last place below it. The comparison absorbs that; the declared
    minimum is untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_SELECTION_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_fraction("min_duty_coverage", settings.get("min_duty_coverage"))
    _require_flag(
        "carry_dispositioned_open", settings.get("carry_dispositioned_open")
    )
    return settings


def duty_owner(duty):
    """Name the role that owes a selection duty."""
    name = _require_choice("duty", duty, SELECTION_DUTIES)
    return DUTY_OWNERS[name]


def duties_owed(assurance_class, scope="per-component"):
    """List the duties an assurance category owes at one scope."""
    category = _require_choice("assurance_class", assurance_class, ASSURANCE_CLASSES)
    if scope not in ("per-component", "per-programme"):
        raise ValueError(
            "scope must be per-component or per-programme, got %r" % (scope,)
        )
    owed = DUTIES_BY_CLASS[category]
    pool = PER_COMPONENT_DUTIES if scope == "per-component" else PROGRAMME_DUTIES
    return tuple(d for d in pool if d in owed)


def _grade_records(owed, records, prefix):
    """Grade one owed duty list against a record mapping."""
    missing = [d for d in owed if d not in records]
    open_duties = [d for d in owed if records.get(d) == RECORD_OPEN]
    rejected = [d for d in owed if records.get(d) == RECORD_REJECTED]
    held = [d for d in owed if records.get(d) == RECORD_HELD]

    findings = []
    for duty in missing:
        findings.append(
            "%s: no record at all for %s, owed by the %s; nobody can tell "
            "whether the duty was skipped, lost or never scheduled"
            % (prefix, duty, DUTY_OWNERS[duty])
        )
    for duty in rejected:
        findings.append(
            "%s: %s was answered and rejected by the %s"
            % (prefix, duty, DUTY_OWNERS[duty])
        )
    for duty in open_duties:
        findings.append(
            "%s: %s is open with the %s" % (prefix, duty, DUTY_OWNERS[duty])
        )
    return {
        "owed": list(owed),
        "missing": missing,
        "open": open_duties,
        "rejected": rejected,
        "held": held,
        "findings": findings,
    }


def validate_component(component):
    """Check one component entry names a category and only known duties."""
    _require_mapping("component", component)
    component_id = _require_label("component_id", component.get("component_id"))
    category = _require_choice(
        "assurance_class", component.get("assurance_class"), ASSURANCE_CLASSES
    )
    records = component.get("duty_records") or {}
    _require_mapping("duty_records", records)
    cleaned = {}
    for duty, state in records.items():
        name = _require_choice("selection duty", duty, SELECTION_DUTIES)
        cleaned[name] = _require_choice("state for %s" % name, state, RECORD_STATES)
    return {
        "component_id": component_id,
        "assurance_class": category,
        "duty_records": cleaned,
    }


def assess_component_duties(component, policy=None):
    """Grade one component against the duties it owes in its own right.

    Programme duties are deliberately not owed here. Re-owing them on
    every part reports one outstanding decision as a hundred open
    duties and buries the parts that genuinely carry nothing.
    """
    settings = resolve_policy(policy)
    record = validate_component(component)
    owed = duties_owed(record["assurance_class"], "per-component")
    graded = _grade_records(owed, record["duty_records"], record["component_id"])

    findings = list(graded["findings"])
    misfiled = [d for d in PROGRAMME_DUTIES if d in record["duty_records"]]
    for duty in misfiled:
        findings.append(
            "%s: %s is recorded against the part but is owed once per "
            "programme by the %s" % (record["component_id"], duty, DUTY_OWNERS[duty])
        )

    if graded["missing"]:
        verdict = DUTY_NO_RECORD
    elif graded["rejected"]:
        verdict = DUTY_REJECTED
    elif graded["open"]:
        verdict = DUTY_OPEN
    else:
        verdict = DUTY_HELD

    ready = verdict == DUTY_HELD or (
        verdict == DUTY_OPEN and settings["carry_dispositioned_open"]
    )
    coverage = len(graded["held"]) / len(owed) if owed else 1.0
    return {
        "component_id": record["component_id"],
        "assurance_class": record["assurance_class"],
        "owed": graded["owed"],
        "missing": graded["missing"],
        "open": graded["open"],
        "rejected": graded["rejected"],
        "held": graded["held"],
        "misfiled_programme_duties": misfiled,
        "duty_coverage": coverage,
        "verdict": verdict,
        "readiness": COMPONENT_READY if ready else COMPONENT_NOT_READY,
        "findings": findings,
    }


def assess_programme_duties(programme_records, assurance_class, policy=None):
    """Grade the duties the programme owes once, not once per part."""
    resolve_policy(policy)
    records = _require_mapping("programme_records", programme_records or {})
    cleaned = {}
    for duty, state in records.items():
        name = _require_choice("programme duty", duty, PROGRAMME_DUTIES)
        cleaned[name] = _require_choice("state for %s" % name, state, RECORD_STATES)
    owed = duties_owed(assurance_class, "per-programme")
    graded = _grade_records(owed, cleaned, "programme")
    if graded["missing"]:
        verdict = DUTY_NO_RECORD
    elif graded["rejected"]:
        verdict = DUTY_REJECTED
    elif graded["open"]:
        verdict = DUTY_OPEN
    else:
        verdict = DUTY_HELD
    coverage = len(graded["held"]) / len(owed) if owed else 1.0
    graded.update(
        {
            "assurance_class": assurance_class,
            "duty_coverage": coverage,
            "verdict": verdict,
        }
    )
    return graded


def assess_selection_readiness(case):
    """Full clause 4.2.1 roll-up over a Class 1 selection."""
    _require_mapping("case", case)
    selection_id = _require_label("selection_id", case.get("selection_id"))
    components = case.get("components")
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError("case must carry a non-empty components sequence")
    settings = resolve_policy(case.get("policy"))

    seen = set()
    for component in components:
        component_id = validate_component(component)["component_id"]
        if component_id in seen:
            raise ValueError("component %r appears twice in one selection" % component_id)
        seen.add(component_id)

    categories = {validate_component(c)["assurance_class"] for c in components}
    programme_class = "class-1" if "class-1" in categories else sorted(categories)[0]
    programme = assess_programme_duties(
        case.get("programme_records") or {}, programme_class, settings
    )

    assessments = [assess_component_duties(c, settings) for c in components]
    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])
    findings.extend(programme["findings"])

    held = sum(len(a["held"]) for a in assessments) + len(programme["held"])
    owed = sum(len(a["owed"]) for a in assessments) + len(programme["owed"])
    coverage = held / owed if owed else 1.0
    meets_coverage = _at_least(coverage, settings["min_duty_coverage"])
    if not meets_coverage:
        findings.append(
            "the selection holds %.4g of the duties it owes against a declared "
            "%.4g minimum" % (coverage, settings["min_duty_coverage"])
        )

    grouped = {}
    for assessment in assessments:
        grouped.setdefault(assessment["verdict"], []).append(
            assessment["component_id"]
        )
    for names in grouped.values():
        names.sort()

    blocking = set(grouped) - {DUTY_HELD}
    if settings["carry_dispositioned_open"]:
        blocking -= {DUTY_OPEN}
    programme_blocking = programme["verdict"] != DUTY_HELD and not (
        settings["carry_dispositioned_open"] and programme["verdict"] == DUTY_OPEN
    )

    weakest = min(
        assessments, key=lambda a: (DUTY_RANK[a["verdict"]], a["component_id"])
    )
    verdict = (
        SELECTION_READY
        if not blocking and not programme_blocking and meets_coverage
        else SELECTION_NOT_READY
    )
    return {
        "selection_id": selection_id,
        "programme_class": programme_class,
        "components": assessments,
        "programme": programme,
        "grouped_components": grouped,
        "duty_coverage": coverage,
        "meets_duty_coverage": meets_coverage,
        "weakest_component": weakest["component_id"],
        "verdict": verdict,
        "findings": findings,
    }
