"""Equipment radiation control board composition and completeness.

Anchor: ECSS-Q-ST-60-15C clause 5.4 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Constitute the board. The people in the room decide what the board
   can say: the radiation effects engineer who did the work, product
   assurance, the design authority whose design is being examined, the
   component engineer who owns the parts list, and the customer's
   representative. One of them chairs, and the chair is not the design
   authority, because a board chaired by the party whose design is
   under review is not a review.
2. Confirm it can sit. Every mandatory role has to be represented by
   somebody actually present, and enough of the board has to be there
   for the meeting to be a meeting rather than a briefing.
3. Check the dossier is complete before it is judged. Every part on
   the equipment parts list owes an analysis for every radiation
   effect it is exposed to, every analysis owes a margin against a
   stated requirement, and an analysis presented for a part that is
   not on the parts list means the two documents have drifted apart.
4. Turn shortfalls into actions. A margin under its requirement is not
   a finding the board can absorb; it needs an action with an owner
   and a date, and an action already past its date at the board is
   itself reportable.
5. Say one thing at the end. Cleared, cleared subject to actions, or
   not cleared -- and nothing is cleared while the dossier has a hole
   in it.

Stdlib only, offline, deterministic.
"""

import datetime
import math

MANDATORY_ROLES = (
    "radiation-effects-engineer",
    "product-assurance",
    "design-authority",
    "component-engineer",
    "customer-representative",
)

OPTIONAL_ROLES = (
    "system-engineer",
    "thermal-engineer",
    "software-engineer",
)

VALID_ROLES = MANDATORY_ROLES + OPTIONAL_ROLES

# The chair cannot be the party whose design is under review.
ROLE_BARRED_FROM_CHAIR = "design-authority"

# Enough of the board present for the meeting to be a meeting.
MINIMUM_PRESENT_MEMBERS = 5

RADIATION_EFFECTS = (
    "total-ionising-dose",
    "displacement-damage",
    "single-event",
)

ACTION_STATUSES = ("open", "closed")

VERDICT_CLEARED = "cleared"
VERDICT_CLEARED_WITH_ACTIONS = "cleared-with-actions"
VERDICT_NOT_CLEARED = "not-cleared"

# Margins are quotients of measured floats, so one sitting exactly on
# its requirement can land a few units in the last place below it.
MARGIN_RELATIVE_TOLERANCE = 1.0e-9

FINDING_ROLE_MISSING = "mandatory-role-not-represented"
FINDING_NO_CHAIR = "no-chair-appointed"
FINDING_MULTIPLE_CHAIRS = "more-than-one-chair-appointed"
FINDING_CHAIR_NOT_INDEPENDENT = "chair-not-independent-of-design-authority"
FINDING_QUORUM = "quorum-not-met"
FINDING_ANALYSIS_MISSING = "analysis-missing-for-part-effect"
FINDING_ANALYSIS_ORPHAN = "analysis-for-part-not-on-parts-list"
FINDING_ANALYSIS_NO_MARGIN = "analysis-without-a-margin"
FINDING_ANALYSIS_NO_EVIDENCE = "analysis-without-an-evidence-reference"
FINDING_SHORTFALL_NO_ACTION = "margin-shortfall-without-an-action"
FINDING_ACTION_NO_OWNER = "action-without-an-owner"
FINDING_ACTION_OVERDUE = "action-overdue-at-the-board-date"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _iso_date(label, value):
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string" % label)
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO date: %r" % (label, value))


def validate_member(member):
    """Validate one board member record and return a normalized copy."""
    if not isinstance(member, dict):
        raise ValueError("member must be a mapping")
    member_id = _text("member id", member.get("id"))
    role = member.get("role")
    if role not in VALID_ROLES:
        raise ValueError(
            "member %s has unknown role %r (expected one of %s)"
            % (member_id, role, ", ".join(VALID_ROLES))
        )
    present = member.get("present", True)
    if not isinstance(present, bool):
        raise ValueError("member %s present must be a boolean" % member_id)
    chair = member.get("chair", False)
    if not isinstance(chair, bool):
        raise ValueError("member %s chair must be a boolean" % member_id)
    return {"id": member_id, "role": role, "present": present, "chair": chair}


def validate_board_members(members):
    """Validate the member list and return normalized records."""
    if not isinstance(members, list) or not members:
        raise ValueError("members must be a non-empty list")
    normalized = []
    seen = set()
    for member in members:
        record = validate_member(member)
        if record["id"] in seen:
            raise ValueError("duplicate member id %r" % (record["id"],))
        seen.add(record["id"])
        normalized.append(record)
    return normalized


def board_composition_findings(members):
    """Findings about who is on the board and who is chairing it."""
    records = validate_board_members(members)
    present = [m for m in records if m["present"]]
    present_roles = {m["role"] for m in present}
    findings = []
    for role in MANDATORY_ROLES:
        if role not in present_roles:
            findings.append("%s:%s" % (FINDING_ROLE_MISSING, role))
    chairs = [m for m in present if m["chair"]]
    if not chairs:
        findings.append(FINDING_NO_CHAIR)
    elif len(chairs) > 1:
        findings.append(FINDING_MULTIPLE_CHAIRS)
    elif chairs[0]["role"] == ROLE_BARRED_FROM_CHAIR:
        findings.append(FINDING_CHAIR_NOT_INDEPENDENT)
    if len(present) < MINIMUM_PRESENT_MEMBERS:
        findings.append(FINDING_QUORUM)
    return findings


def board_can_sit(members):
    """True when the board is constituted well enough to sit."""
    return not board_composition_findings(members)


def validate_part(part):
    """Validate one parts-list entry and return a normalized copy."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    part_id = _text("part id", part.get("id"))
    effects = part.get("effects", RADIATION_EFFECTS)
    if not isinstance(effects, (list, tuple)) or not effects:
        raise ValueError("part %s needs a non-empty effects sequence" % part_id)
    for effect in effects:
        if effect not in RADIATION_EFFECTS:
            raise ValueError("part %s has unknown effect %r" % (part_id, effect))
    return {"id": part_id, "effects": tuple(effects)}


def validate_analysis(analysis):
    """Validate one analysis record and return a normalized copy."""
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be a mapping")
    part_id = _text("analysis part_id", analysis.get("part_id"))
    effect = analysis.get("effect")
    if effect not in RADIATION_EFFECTS:
        raise ValueError(
            "analysis for %s has unknown effect %r" % (part_id, effect)
        )
    margin = analysis.get("margin")
    if margin is not None:
        margin = _numeric("analysis %s/%s margin" % (part_id, effect), margin, 0.0)
    required = analysis.get("required_margin")
    if required is not None:
        required = _numeric(
            "analysis %s/%s required_margin" % (part_id, effect), required
        )
        if required <= 0.0:
            raise ValueError(
                "analysis %s/%s required_margin must be positive" % (part_id, effect)
            )
    reference = analysis.get("evidence_reference")
    if reference is not None and (
        not isinstance(reference, str) or not reference.strip()
    ):
        raise ValueError(
            "analysis %s/%s evidence_reference must be a non-empty string"
            % (part_id, effect)
        )
    return {
        "part_id": part_id,
        "effect": effect,
        "margin": margin,
        "required_margin": required,
        "evidence_reference": reference.strip() if reference else None,
    }


def validate_action(action):
    """Validate one board action and return a normalized copy."""
    if not isinstance(action, dict):
        raise ValueError("action must be a mapping")
    action_id = _text("action id", action.get("id"))
    subject = _text("action %s subject" % action_id, action.get("subject"))
    status = action.get("status")
    if status not in ACTION_STATUSES:
        raise ValueError(
            "action %s has unknown status %r (expected one of %s)"
            % (action_id, status, ", ".join(ACTION_STATUSES))
        )
    owner = action.get("owner")
    if owner is not None and (not isinstance(owner, str) or not owner.strip()):
        raise ValueError("action %s owner must be a non-empty string" % action_id)
    due = _iso_date("action %s due_date" % action_id, action.get("due_date"))
    return {
        "id": action_id,
        "subject": subject,
        "status": status,
        "owner": owner.strip() if owner else None,
        "due_date": due,
    }


def margin_meets_requirement(margin, required):
    """True when a margin meets its requirement at exact equality."""
    margin = _numeric("margin", margin, 0.0)
    required = _numeric("required", required)
    if required <= 0.0:
        raise ValueError("required margin must be positive")
    return margin >= required * (1.0 - MARGIN_RELATIVE_TOLERANCE)


def coverage_findings(parts, analyses):
    """Findings about parts-list against analysis coverage."""
    part_records = [validate_part(p) for p in parts]
    if not part_records:
        raise ValueError("parts must be a non-empty list")
    analysis_records = [validate_analysis(a) for a in analyses]
    covered = {(a["part_id"], a["effect"]) for a in analysis_records}
    listed = {p["id"] for p in part_records}
    findings = []
    for part in part_records:
        for effect in part["effects"]:
            if (part["id"], effect) not in covered:
                findings.append(
                    "%s:%s/%s" % (FINDING_ANALYSIS_MISSING, part["id"], effect)
                )
    for analysis in analysis_records:
        if analysis["part_id"] not in listed:
            findings.append(
                "%s:%s" % (FINDING_ANALYSIS_ORPHAN, analysis["part_id"])
            )
    return findings


def analysis_findings(analyses, actions):
    """Findings about margins, evidence and the actions covering them."""
    analysis_records = [validate_analysis(a) for a in analyses]
    action_records = [validate_action(a) for a in actions]
    subjects = {a["subject"] for a in action_records}
    findings = []
    for analysis in analysis_records:
        tag = "%s/%s" % (analysis["part_id"], analysis["effect"])
        if analysis["margin"] is None or analysis["required_margin"] is None:
            findings.append("%s:%s" % (FINDING_ANALYSIS_NO_MARGIN, tag))
            continue
        if not analysis["evidence_reference"]:
            findings.append("%s:%s" % (FINDING_ANALYSIS_NO_EVIDENCE, tag))
        if not margin_meets_requirement(
            analysis["margin"], analysis["required_margin"]
        ):
            if tag not in subjects:
                findings.append("%s:%s" % (FINDING_SHORTFALL_NO_ACTION, tag))
    return findings


def action_findings(actions, board_date):
    """Findings about the actions the board is carrying."""
    action_records = [validate_action(a) for a in actions]
    held_on = _iso_date("board_date", board_date)
    findings = []
    for action in action_records:
        if not action["owner"]:
            findings.append("%s:%s" % (FINDING_ACTION_NO_OWNER, action["id"]))
        if action["status"] == "open" and action["due_date"] < held_on:
            findings.append("%s:%s" % (FINDING_ACTION_OVERDUE, action["id"]))
    return findings


def review_radiation_control_board(board):
    """Run the clause 5.4 board review over one equipment dossier."""
    if not isinstance(board, dict):
        raise ValueError("board must be a mapping")
    board_date = board.get("board_date")
    _iso_date("board_date", board_date)
    members = board.get("members")
    parts = board.get("parts")
    analyses = board.get("analyses", [])
    actions = board.get("actions", [])
    if not isinstance(parts, list) or not parts:
        raise ValueError("board parts must be a non-empty list")
    if not isinstance(analyses, list):
        raise ValueError("board analyses must be a list")
    if not isinstance(actions, list):
        raise ValueError("board actions must be a list")
    composition = board_composition_findings(members)
    coverage = coverage_findings(parts, analyses)
    dossier = analysis_findings(analyses, actions)
    action_items = action_findings(actions, board_date)
    findings = composition + coverage + dossier + action_items
    open_actions = [
        a["id"] for a in (validate_action(a) for a in actions) if a["status"] == "open"
    ]
    if findings:
        verdict = VERDICT_NOT_CLEARED
    elif open_actions:
        verdict = VERDICT_CLEARED_WITH_ACTIONS
    else:
        verdict = VERDICT_CLEARED
    return {
        "board_date": board_date,
        "composition_findings": composition,
        "coverage_findings": coverage,
        "analysis_findings": dossier,
        "action_findings": action_items,
        "findings": findings,
        "open_action_ids": sorted(open_actions),
        "verdict": verdict,
        "cleared": verdict != VERDICT_NOT_CLEARED,
    }
