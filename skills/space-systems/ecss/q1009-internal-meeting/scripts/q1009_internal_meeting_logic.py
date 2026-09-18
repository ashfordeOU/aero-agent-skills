"""Internal nonconformance review board sitting: quorum, agenda, decision records.

Anchor: ECSS-Q-ST-10-09 clause 5.2.2.1 (internal processing of a
nonconformance -- convening the supplier's own review board, what each agenda
item has to arrive with, and what the sitting has to leave behind).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the board roster: one member per board function, each marked
   present or absent and voting or advisory.
2. Judge the sitting: the mandatory board functions have to be present in
   person, and the attending voting members have to reach the quorum fraction
   of the appointed voting membership. Either shortfall invalidates the
   sitting, and the two shortfalls are reported separately because they are
   repaired differently -- one by a delegate, one by a reconvene.
3. Judge each agenda item: an item may only be heard when its review package
   is complete. A package gap makes the item inadmissible and it is deferred
   rather than decided, so an incomplete item can never absorb board time and
   leave with a decision resting on missing evidence.
4. Judge the minutes: every item actually heard has to carry a decision record
   naming the disposition, its rationale, an accountable owner and a due day.
   An item heard without a complete record is an open minute.
5. Report the sitting as valid only when quorum holds and every item heard
   carries a complete decision record. A deferral does not invalidate a
   properly constituted sitting, so the cleared-agenda verdict is reported
   separately from the sitting verdict and the deferred items are named.
"""

import math

__all__ = [
    "QUORUM_TOLERANCE",
    "DEFAULT_QUORUM_FRACTION",
    "MANDATORY_BOARD_FUNCTIONS",
    "REQUIRED_PACKAGE_ITEMS",
    "REQUIRED_DECISION_FIELDS",
    "normalize_function",
    "validate_member",
    "validate_board",
    "absent_mandatory_functions",
    "voting_counts",
    "quorum_ratio",
    "quorum_status",
    "package_gaps",
    "agenda_admissibility",
    "decision_gaps",
    "minutes_status",
    "assess_internal_meeting",
]

# A quorum test is a ratio against a fraction; an exactly-half board can land a
# few ULPs low. Absorb the representation error here rather than lowering the
# appointed fraction.
QUORUM_TOLERANCE = 1e-9

DEFAULT_QUORUM_FRACTION = 0.5

# Functions that have to sit in person. Quality chairs, engineering owns the
# design intent, production owns the as-built item; without all three the board
# cannot weigh a departure against what the item is for.
MANDATORY_BOARD_FUNCTIONS = (
    "chair",
    "product-assurance",
    "design-engineering",
    "production",
)

# What an agenda item has to arrive with before it may be heard.
REQUIRED_PACKAGE_ITEMS = (
    "nonconformance-report",
    "item-identification",
    "effectivity-list",
    "nonconformance-description",
    "cause-analysis",
    "consequence-assessment",
    "proposed-disposition",
)

# What the minutes have to record for every item that was heard.
REQUIRED_DECISION_FIELDS = (
    "agenda_item",
    "disposition",
    "rationale",
    "owner",
    "due_day",
)


def normalize_function(value):
    """Return a board function or package item name in canonical hyphen form."""
    if not isinstance(value, str):
        raise ValueError("name must be a string, got %r" % (value,))
    text = " ".join(value.strip().lower().split())
    if not text:
        raise ValueError("name must not be empty or whitespace only")
    return text.replace(" ", "-").replace("_", "-")


def _as_bool(value, label):
    """Return a strict boolean; anything truthy-but-not-bool is an input error."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_member(member):
    """Return one validated board member record."""
    if not isinstance(member, dict):
        raise ValueError("board member must be a mapping, got %r" % (member,))
    for key in ("function", "present", "voting"):
        if key not in member:
            raise ValueError("board member missing required key '%s'" % key)
    return {
        "function": normalize_function(member["function"]),
        "present": _as_bool(member["present"], "present"),
        "voting": _as_bool(member["voting"], "voting"),
    }


def validate_board(members):
    """Return the validated roster; one appointed member per board function."""
    if not isinstance(members, (list, tuple)) or not members:
        raise ValueError("board roster must be a non-empty sequence of members")
    seen = set()
    roster = []
    for member in members:
        record = validate_member(member)
        if record["function"] in seen:
            raise ValueError(
                "board function '%s' appointed more than once" % record["function"]
            )
        seen.add(record["function"])
        roster.append(record)
    return roster


def absent_mandatory_functions(members):
    """Return the mandatory board functions with no member sitting."""
    roster = validate_board(members)
    present = {r["function"] for r in roster if r["present"]}
    return tuple(f for f in MANDATORY_BOARD_FUNCTIONS if f not in present)


def voting_counts(members):
    """Return (voting members present, voting members appointed)."""
    roster = validate_board(members)
    appointed = [r for r in roster if r["voting"]]
    if not appointed:
        raise ValueError("board roster has no appointed voting members")
    return (sum(1 for r in appointed if r["present"]), len(appointed))


def quorum_ratio(members):
    """Return the attending share of the appointed voting membership."""
    present, appointed = voting_counts(members)
    return present / appointed


def quorum_status(members, fraction=DEFAULT_QUORUM_FRACTION):
    """Return the quorum verdict for a sitting, with both shortfalls separated."""
    if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
        raise ValueError("fraction must be a real number, got %r" % (fraction,))
    frac = float(fraction)
    if not math.isfinite(frac) or frac <= 0.0 or frac > 1.0:
        raise ValueError("fraction must lie in (0, 1], got %r" % (fraction,))
    present, appointed = voting_counts(members)
    ratio = present / appointed
    fraction_met = ratio > frac or math.isclose(
        ratio, frac, rel_tol=0.0, abs_tol=QUORUM_TOLERANCE
    )
    absent = absent_mandatory_functions(members)
    return {
        "voting_present": present,
        "voting_appointed": appointed,
        "ratio": ratio,
        "required_fraction": frac,
        "fraction_met": fraction_met,
        "absent_mandatory_functions": absent,
        "quorum_met": fraction_met and not absent,
    }


def package_gaps(package_items):
    """Return the required review-package items the agenda item did not bring."""
    if isinstance(package_items, dict):
        supplied = {
            normalize_function(k) for k, v in package_items.items() if _as_bool(v, str(k))
        }
    elif isinstance(package_items, (list, tuple, set, frozenset)):
        supplied = {normalize_function(k) for k in package_items}
    else:
        raise ValueError("package must be a mapping or a sequence of item names")
    return tuple(item for item in REQUIRED_PACKAGE_ITEMS if item not in supplied)


def agenda_admissibility(agenda):
    """Return one admissibility record per agenda item, in agenda order."""
    if not isinstance(agenda, (list, tuple)) or not agenda:
        raise ValueError("agenda must be a non-empty sequence of items")
    records = []
    seen = set()
    for entry in agenda:
        if not isinstance(entry, dict):
            raise ValueError("agenda item must be a mapping, got %r" % (entry,))
        for key in ("item", "package"):
            if key not in entry:
                raise ValueError("agenda item missing required key '%s'" % key)
        item = normalize_function(entry["item"])
        if item in seen:
            raise ValueError("agenda item '%s' listed more than once" % item)
        seen.add(item)
        gaps = package_gaps(entry["package"])
        records.append(
            {"item": item, "package_gaps": gaps, "admissible": not gaps}
        )
    return records


def decision_gaps(decision):
    """Return the decision-record fields the minutes did not capture."""
    if not isinstance(decision, dict):
        raise ValueError("decision record must be a mapping, got %r" % (decision,))
    missing = []
    for field in REQUIRED_DECISION_FIELDS:
        value = decision.get(field)
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    return tuple(missing)


def minutes_status(agenda_records, decisions):
    """Match decision records to the items heard and report the open minutes."""
    if not isinstance(agenda_records, (list, tuple)):
        raise ValueError("agenda_records must be a sequence")
    if not isinstance(decisions, (list, tuple)):
        raise ValueError("decisions must be a sequence of decision records")
    by_item = {}
    for decision in decisions:
        gaps = decision_gaps(decision)
        raw = decision.get("agenda_item")
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            # Cannot be attached to an item; surfaced as an unattached record.
            by_item.setdefault(None, []).append({"gaps": gaps})
            continue
        key = normalize_function(raw)
        if key in by_item:
            raise ValueError("more than one decision recorded for item '%s'" % key)
        by_item[key] = {"gaps": gaps}
    heard = [r["item"] for r in agenda_records if r["admissible"]]
    deferred = [r["item"] for r in agenda_records if not r["admissible"]]
    open_minutes = []
    for item in heard:
        record = by_item.get(item)
        if record is None:
            open_minutes.append({"item": item, "reason": "no-decision-recorded"})
        elif record["gaps"]:
            open_minutes.append(
                {"item": item, "reason": "incomplete-record", "missing": record["gaps"]}
            )
    stray = [
        key
        for key in by_item
        if key is not None and key not in set(heard)
    ]
    if None in by_item:
        stray.append(None)
    return {
        "heard": heard,
        "deferred": deferred,
        "open_minutes": open_minutes,
        "unattached_decisions": tuple(sorted(s for s in stray if s is not None))
        + ((None,) if None in by_item else ()),
        "minutes_complete": not open_minutes,
    }


def assess_internal_meeting(spec):
    """Run the full clause 5.2.2.1 internal-board sitting assessment.

    spec keys: board (sequence of members), agenda (sequence of items),
    decisions (sequence of decision records), optional quorum_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("board", "agenda", "decisions"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    quorum = quorum_status(spec["board"], spec.get("quorum_fraction", DEFAULT_QUORUM_FRACTION))
    agenda_records = agenda_admissibility(spec["agenda"])
    minutes = minutes_status(agenda_records, spec["decisions"])
    findings = []
    if not quorum["fraction_met"]:
        findings.append(
            "voting attendance %d of %d is below the %.3f quorum fraction"
            % (quorum["voting_present"], quorum["voting_appointed"], quorum["required_fraction"])
        )
    for function in quorum["absent_mandatory_functions"]:
        findings.append("mandatory board function '%s' not sitting" % function)
    for record in agenda_records:
        if not record["admissible"]:
            findings.append(
                "item '%s' deferred: review package missing %s"
                % (record["item"], ", ".join(record["package_gaps"]))
            )
    for entry in minutes["open_minutes"]:
        if entry["reason"] == "no-decision-recorded":
            findings.append("item '%s' was heard with no decision recorded" % entry["item"])
        else:
            findings.append(
                "decision record for '%s' is missing %s"
                % (entry["item"], ", ".join(entry["missing"]))
            )
    return {
        "quorum": quorum,
        "agenda": agenda_records,
        "minutes": minutes,
        "findings": findings,
        "agenda_cleared": not minutes["deferred"],
        "sitting_valid": quorum["quorum_met"] and minutes["minutes_complete"],
    }
