"""Off-the-shelf item utilisation plan, drafted against the Annex A DRD.

Anchor: ECSS-Q-ST-20-10C clause 5.1.1 (the off-the-shelf plan produced in
accordance with the Annex A document requirements definition: the candidate
items, the schedule of their evaluations, the responsibilities carried and
the interfaces involved). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Grade the DRD section set: a section that is absent and a section that is
   present with nothing in it are both gaps, and they are reported apart
   because they are fixed by different people.
2. Normalise the candidate list, each candidate carrying the day the project
   is committed to procuring it.
3. Normalise the evaluation schedule and require every listed candidate to
   carry at least one evaluation, attributed to somebody who can carry it.
4. Grade each evaluation against the day its result is needed: the
   procurement commitment day less the agreed decision lead, in calendar
   days. An evaluation completing after that date informs nothing.
5. Normalise the interfaces and require each one to name two distinct
   parties and a defined exchange; a candidate with no interface at all is
   raised as an open question rather than a defect.
6. Return the section completeness, the evaluation coverage and the issue
   decision for the plan.
"""

from datetime import date, timedelta

__all__ = [
    "DRD_SECTIONS",
    "RESPONSIBLE_ROLES",
    "EXCHANGE_KINDS",
    "DEFAULT_DECISION_LEAD_DAYS",
    "normalise_identifier",
    "parse_day",
    "need_day",
    "validate_sections",
    "validate_candidates",
    "validate_evaluations",
    "validate_interfaces",
    "section_findings",
    "evaluation_findings",
    "interface_findings",
    "assess_ots_plan",
]

# The sections the Annex A DRD expects the plan to carry, in DRD order.
DRD_SECTIONS = (
    "scope-and-applicability",
    "applicable-documents",
    "ots-candidate-list",
    "evaluation-schedule",
    "responsibilities",
    "interfaces",
)

# Who a plan can attribute an evaluation to.
RESPONSIBLE_ROLES = (
    "design-authority",
    "procurement-officer",
    "product-assurance-manager",
    "project-manager",
    "supplier",
)

# What an interface between two parties actually exchanges.
EXCHANGE_KINDS = ("data", "documentation", "hardware", "software")

# How far ahead of the procurement commitment an evaluation result is needed.
DEFAULT_DECISION_LEAD_DAYS = 30


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_day(value, label):
    """Return an ISO calendar day as a date; raise on anything else."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO calendar day, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO calendar day: %r" % (label, value))


def need_day(commitment_day, lead_days=DEFAULT_DECISION_LEAD_DAYS):
    """Return the day an evaluation result is needed by."""
    if not isinstance(commitment_day, date):
        raise ValueError("commitment_day must be a date")
    if not isinstance(lead_days, int) or isinstance(lead_days, bool):
        raise ValueError("lead_days must be an integer, got %r" % (lead_days,))
    if lead_days < 0:
        raise ValueError("lead_days must not be negative, got %d" % lead_days)
    return commitment_day - timedelta(days=lead_days)


def validate_sections(sections):
    """Return the drafted sections keyed by section, content checked."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a sequence")
    drafted = {}
    for position, item in enumerate(sections):
        if not isinstance(item, dict):
            raise ValueError("sections[%d] must be a mapping" % position)
        name = normalise_identifier(item.get("section"), "sections[%d].section" % position)
        if name not in DRD_SECTIONS:
            raise ValueError(
                "sections[%d] names %r, which is not an Annex A DRD section; the DRD "
                "sections are %s" % (position, name, "/".join(DRD_SECTIONS))
            )
        if name in drafted:
            raise ValueError("section %r is drafted twice" % name)
        content = item.get("content")
        if content is not None and not isinstance(content, str):
            raise ValueError("sections[%d].content must be a string when given" % position)
        drafted[name] = {
            "section": name,
            "content": None if content is None or not content.strip() else content.strip(),
        }
    return drafted


def validate_candidates(candidates):
    """Return the plan's candidate list keyed by candidate."""
    if not isinstance(candidates, (list, tuple)):
        raise ValueError("candidates must be a sequence")
    listed = {}
    for position, item in enumerate(candidates):
        if not isinstance(item, dict):
            raise ValueError("candidates[%d] must be a mapping" % position)
        ref = normalise_identifier(item.get("candidate"), "candidates[%d].candidate" % position)
        if ref in listed:
            raise ValueError("candidate %r is listed twice" % ref)
        listed[ref] = {
            "candidate": ref,
            "node": normalise_identifier(item.get("node"), "candidates[%d].node" % position),
            "commitment_day": parse_day(
                item.get("commitment_day"), "candidates[%d].commitment_day" % position
            ),
        }
    return listed


def validate_evaluations(evaluations):
    """Return the evaluation schedule keyed by evaluation identifier."""
    if evaluations is None:
        evaluations = []
    if not isinstance(evaluations, (list, tuple)):
        raise ValueError("evaluations must be a sequence")
    scheduled = {}
    for position, item in enumerate(evaluations):
        if not isinstance(item, dict):
            raise ValueError("evaluations[%d] must be a mapping" % position)
        ref = normalise_identifier(
            item.get("evaluation"), "evaluations[%d].evaluation" % position
        )
        if ref in scheduled:
            raise ValueError("evaluation %r is scheduled twice" % ref)
        responsible = item.get("responsible")
        if responsible is not None:
            responsible = normalise_identifier(
                responsible, "evaluations[%d].responsible" % position
            )
            if responsible not in RESPONSIBLE_ROLES:
                raise ValueError(
                    "evaluations[%d].responsible must be one of %s, got %r"
                    % (position, "/".join(RESPONSIBLE_ROLES), responsible)
                )
        scheduled[ref] = {
            "evaluation": ref,
            "candidate": normalise_identifier(
                item.get("candidate"), "evaluations[%d].candidate" % position
            ),
            "completion_day": parse_day(
                item.get("completion_day"), "evaluations[%d].completion_day" % position
            ),
            "responsible": responsible,
        }
    return scheduled


def validate_interfaces(interfaces):
    """Return the declared interfaces keyed by interface identifier."""
    if interfaces is None:
        interfaces = []
    if not isinstance(interfaces, (list, tuple)):
        raise ValueError("interfaces must be a sequence")
    declared = {}
    for position, item in enumerate(interfaces):
        if not isinstance(item, dict):
            raise ValueError("interfaces[%d] must be a mapping" % position)
        ref = normalise_identifier(item.get("interface"), "interfaces[%d].interface" % position)
        if ref in declared:
            raise ValueError("interface %r is declared twice" % ref)
        parties = item.get("parties", [])
        if not isinstance(parties, (list, tuple)):
            raise ValueError("interfaces[%d].parties must be a sequence" % position)
        named = []
        for party in parties:
            name = normalise_identifier(party, "interfaces[%d] party" % position)
            if name not in named:
                named.append(name)
        exchange = normalise_identifier(
            item.get("exchange"), "interfaces[%d].exchange" % position
        )
        if exchange not in EXCHANGE_KINDS:
            raise ValueError(
                "interfaces[%d].exchange must be one of %s, got %r"
                % (position, "/".join(EXCHANGE_KINDS), exchange)
            )
        declared[ref] = {
            "interface": ref,
            "candidate": normalise_identifier(
                item.get("candidate"), "interfaces[%d].candidate" % position
            ),
            "parties": tuple(named),
            "exchange": exchange,
        }
    return declared


def section_findings(drafted):
    """Report DRD sections that are absent or drafted with no content."""
    if not isinstance(drafted, dict):
        raise ValueError("drafted must be the normalised section mapping")
    findings = []
    for section in DRD_SECTIONS:
        entry = drafted.get(section)
        if entry is None:
            findings.append({
                "code": "drd-section-missing",
                "severity": "blocking",
                "subject": section,
                "message": "the plan has no %s section" % section,
            })
        elif entry["content"] is None:
            findings.append({
                "code": "drd-section-empty",
                "severity": "blocking",
                "subject": section,
                "message": "the %s section is present with no content" % section,
            })
    return findings


def evaluation_findings(listed, scheduled, lead_days=DEFAULT_DECISION_LEAD_DAYS):
    """Grade the evaluation schedule against the candidates and their need days."""
    if not isinstance(listed, dict):
        raise ValueError("listed must be the normalised candidate mapping")
    if not isinstance(scheduled, dict):
        raise ValueError("scheduled must be the normalised evaluation mapping")
    findings = []
    covered = set()
    for ref in sorted(scheduled):
        evaluation = scheduled[ref]
        candidate = evaluation["candidate"]
        if candidate not in listed:
            findings.append({
                "code": "evaluation-for-unlisted-candidate",
                "severity": "blocking",
                "subject": ref,
                "message": "%s evaluates %r, which the candidate list does not carry"
                           % (ref, candidate),
            })
            continue
        covered.add(candidate)
        if evaluation["responsible"] is None:
            findings.append({
                "code": "evaluation-without-responsible",
                "severity": "blocking",
                "subject": ref,
                "message": "%s names nobody responsible for carrying it out" % ref,
            })
        needed = need_day(listed[candidate]["commitment_day"], lead_days)
        if evaluation["completion_day"] > needed:
            findings.append({
                "code": "evaluation-completes-too-late",
                "severity": "blocking",
                "subject": ref,
                "message": "%s completes %s, after the %s its result is needed by"
                           % (ref, evaluation["completion_day"].isoformat(),
                              needed.isoformat()),
            })
    for candidate in sorted(listed):
        if candidate not in covered:
            findings.append({
                "code": "candidate-without-evaluation",
                "severity": "blocking",
                "subject": candidate,
                "message": "%s is listed as a candidate with no evaluation scheduled"
                           % candidate,
            })
    return findings


def interface_findings(listed, declared):
    """Grade the declared interfaces for two-sidedness and candidate coverage."""
    if not isinstance(listed, dict):
        raise ValueError("listed must be the normalised candidate mapping")
    if not isinstance(declared, dict):
        raise ValueError("declared must be the normalised interface mapping")
    findings = []
    covered = set()
    for ref in sorted(declared):
        interface = declared[ref]
        if len(interface["parties"]) < 2:
            findings.append({
                "code": "interface-not-two-sided",
                "severity": "blocking",
                "subject": ref,
                "message": "%s names %d distinct party or parties; an interface needs two"
                           % (ref, len(interface["parties"])),
            })
        if interface["candidate"] not in listed:
            findings.append({
                "code": "interface-for-unlisted-candidate",
                "severity": "blocking",
                "subject": ref,
                "message": "%s declares an interface for %r, which the candidate list does "
                           "not carry" % (ref, interface["candidate"]),
            })
            continue
        covered.add(interface["candidate"])
    for candidate in sorted(listed):
        if candidate not in covered:
            findings.append({
                "code": "candidate-without-declared-interface",
                "severity": "advisory",
                "subject": candidate,
                "message": "%s carries no declared interface" % candidate,
            })
    return findings


def assess_ots_plan(spec):
    """Grade a drafted off-the-shelf plan against the Annex A DRD.

    spec keys: sections, candidates, evaluations, interfaces, and an optional
    lead_days decision lead in calendar days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("sections", "candidates"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    lead = spec.get("lead_days", DEFAULT_DECISION_LEAD_DAYS)
    if not isinstance(lead, int) or isinstance(lead, bool) or lead < 0:
        raise ValueError("lead_days must be a non-negative integer, got %r" % (lead,))
    drafted = validate_sections(spec["sections"])
    listed = validate_candidates(spec["candidates"])
    scheduled = validate_evaluations(spec.get("evaluations"))
    declared = validate_interfaces(spec.get("interfaces"))
    findings = section_findings(drafted)
    findings.extend(evaluation_findings(listed, scheduled, lead))
    findings.extend(interface_findings(listed, declared))
    filled = sum(
        1 for section in DRD_SECTIONS
        if drafted.get(section) is not None and drafted[section]["content"] is not None
    )
    evaluated = {
        e["candidate"] for e in scheduled.values() if e["candidate"] in listed
    }
    blocking = [f for f in findings if f["severity"] == "blocking"]
    advisory = [f for f in findings if f["severity"] == "advisory"]
    if blocking:
        decision = "not-issuable"
    elif advisory:
        decision = "issuable-with-actions"
    else:
        decision = "issuable"
    return {
        "sections": drafted,
        "candidates": listed,
        "evaluations": scheduled,
        "interfaces": declared,
        "decision_lead_days": lead,
        "section_completeness": filled / float(len(DRD_SECTIONS)),
        "evaluation_coverage": (
            len(evaluated) / float(len(listed)) if listed else 0.0
        ),
        "findings": findings,
        "blocking_findings": blocking,
        "decision": decision,
    }
