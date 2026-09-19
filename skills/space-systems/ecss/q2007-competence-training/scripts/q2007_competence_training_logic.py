"""Personnel competence and training control in a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 5.4 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Fix the competence need per test role, not per person. A role is a set
   of named competences each held to a minimum level on a 0-4 scale, where
   0 is no exposure and 4 is able to set the practice for others. The need
   belongs to the role because the role is what the test schedule assigns;
   a person is then measured against the role they are about to fill.
2. Read the personnel record. Each person declares the role they are
   proposed for and, per competence, the level assessed, the day that
   assessment was made, the day any certificate expires, and whether a
   training event is on record behind the level.
3. Refuse a record that cannot be read: an unknown role, an unknown
   competence name, a level outside the scale, a non-integer day, or a
   repeated person identifier.
4. Derive the gap per competence. A competence can fail in four separate
   ways and the remedy differs for each, so they are never merged:
   - absent: the person holds no assessment for it at all;
   - under-level: assessed below the level the role needs;
   - certificate-expired: the level is there but the certificate behind it
     has lapsed as of the evaluation day;
   - untrained: the level is asserted with no training event behind it.
5. Clear a person for the role only when no competence carries a gap. A
   near miss is not a clearance: the level the role asks for is the level
   at which the person can be left alone with the test article.
6. Order the remaining work into a training plan, worst shortfall first
   and alphabetically within an equal shortfall, so the plan is stable
   across runs and can be diffed between reviews.
7. Roll the centre up: who is cleared, who is blocked, the per-role
   clearance ratio and the plan. Records are retained for a fixed window
   and a record older than that window no longer supports a clearance.

Stdlib only, offline, deterministic. The evaluation day is always passed
in, never read from the clock, so a run is reproducible.
"""

MIN_LEVEL = 0
MAX_LEVEL = 4

# Competence need per test role: competence name -> minimum level.
ROLE_COMPETENCE_REQUIREMENTS = {
    "test-conductor": {
        "test-facility-operation": 3,
        "test-centre-safety-rules": 3,
        "test-procedure-authoring": 2,
        "nonconformance-handling": 2,
    },
    "test-operator": {
        "test-facility-operation": 2,
        "test-centre-safety-rules": 2,
    },
    "quality-inspector": {
        "inspection-technique": 3,
        "test-centre-safety-rules": 2,
        "nonconformance-handling": 3,
    },
    "safety-officer": {
        "test-centre-safety-rules": 4,
        "hazard-analysis": 3,
    },
    "facility-maintainer": {
        "test-facility-operation": 3,
        "facility-maintenance-practice": 3,
        "test-centre-safety-rules": 2,
    },
}

VALID_ROLES = tuple(sorted(ROLE_COMPETENCE_REQUIREMENTS))
VALID_COMPETENCES = tuple(
    sorted({c for needs in ROLE_COMPETENCE_REQUIREMENTS.values() for c in needs})
)

# A certificate is good for two years from issue; an assessment record is
# kept for ten and stops supporting a clearance once it falls out.
CERTIFICATE_VALIDITY_DAYS = 730
RECORD_RETENTION_DAYS = 3650

GAP_ABSENT = "competence-absent"
GAP_UNDER_LEVEL = "competence-below-required-level"
GAP_EXPIRED = "certificate-expired"
GAP_UNTRAINED = "level-asserted-without-training-record"
GAP_RECORD_STALE = "assessment-record-outside-retention-window"


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def required_competences(role):
    """The competence need of one test role: name -> minimum level."""
    if role not in ROLE_COMPETENCE_REQUIREMENTS:
        raise ValueError(
            "unknown role %r (expected one of %s)" % (role, ", ".join(VALID_ROLES))
        )
    return dict(ROLE_COMPETENCE_REQUIREMENTS[role])


def validate_competence_entry(person_id, name, entry):
    """Validate one held-competence entry and return a normalized copy."""
    if name not in VALID_COMPETENCES:
        raise ValueError(
            "person %s holds unknown competence %r (expected one of %s)"
            % (person_id, name, ", ".join(VALID_COMPETENCES))
        )
    if not isinstance(entry, dict):
        raise ValueError(
            "person %s competence %s must be a mapping" % (person_id, name)
        )
    level = _integer("person %s competence %s level" % (person_id, name),
                     entry.get("level", 0), MIN_LEVEL)
    if level > MAX_LEVEL:
        raise ValueError(
            "person %s competence %s level %d is above the %d-point scale"
            % (person_id, name, level, MAX_LEVEL)
        )
    assessed = entry.get("assessed_on_day")
    if assessed is not None:
        assessed = _integer(
            "person %s competence %s assessed_on_day" % (person_id, name), assessed
        )
    expires = entry.get("certificate_expires_on_day")
    if expires is not None:
        expires = _integer(
            "person %s competence %s certificate_expires_on_day"
            % (person_id, name),
            expires,
        )
    return {
        "name": name,
        "level": level,
        "assessed_on_day": assessed,
        "certificate_expires_on_day": expires,
        "trained": _boolean(
            "person %s competence %s trained" % (person_id, name),
            entry.get("trained", False),
        ),
    }


def validate_person(record):
    """Validate one personnel record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("person record must be a mapping")
    person_id = _text("person id", record.get("id"))
    role = record.get("role")
    if role not in ROLE_COMPETENCE_REQUIREMENTS:
        raise ValueError(
            "person %s has unknown role %r (expected one of %s)"
            % (person_id, role, ", ".join(VALID_ROLES))
        )
    held = record.get("competences", {})
    if not isinstance(held, dict):
        raise ValueError("person %s competences must be a mapping" % person_id)
    normalized = {}
    for name in sorted(held):
        normalized[name] = validate_competence_entry(person_id, name, held[name])
    return {"id": person_id, "role": role, "competences": normalized}


def certificate_state(person, competence, as_of_day):
    """State of the certificate behind one competence on the evaluation day."""
    norm = validate_person(person)
    day = _integer("as_of_day", as_of_day)
    entry = norm["competences"].get(competence)
    if entry is None:
        return "absent"
    if entry["certificate_expires_on_day"] is None:
        return "uncertificated"
    if entry["certificate_expires_on_day"] < day:
        return "expired"
    return "valid"


def days_to_certificate_expiry(person, competence, as_of_day):
    """Whole days left on a certificate; negative once it has lapsed."""
    norm = validate_person(person)
    day = _integer("as_of_day", as_of_day)
    entry = norm["competences"].get(competence)
    if entry is None or entry["certificate_expires_on_day"] is None:
        raise ValueError(
            "person %s holds no certificate for %r" % (norm["id"], competence)
        )
    return entry["certificate_expires_on_day"] - day


def record_is_within_retention(person, competence, as_of_day):
    """True when the assessment record still sits inside the retention window."""
    norm = validate_person(person)
    day = _integer("as_of_day", as_of_day)
    entry = norm["competences"].get(competence)
    if entry is None or entry["assessed_on_day"] is None:
        return False
    return day - entry["assessed_on_day"] <= RECORD_RETENTION_DAYS


def competence_gaps(person, as_of_day):
    """Every way this person falls short of the role, one entry per reason."""
    norm = validate_person(person)
    day = _integer("as_of_day", as_of_day)
    needs = required_competences(norm["role"])
    gaps = []
    for name in sorted(needs):
        wanted = needs[name]
        entry = norm["competences"].get(name)
        if entry is None:
            gaps.append(
                {
                    "competence": name,
                    "reason": GAP_ABSENT,
                    "required_level": wanted,
                    "held_level": 0,
                    "shortfall": wanted,
                }
            )
            continue
        shortfall = max(0, wanted - entry["level"])
        if shortfall > 0:
            gaps.append(
                {
                    "competence": name,
                    "reason": GAP_UNDER_LEVEL,
                    "required_level": wanted,
                    "held_level": entry["level"],
                    "shortfall": shortfall,
                }
            )
        if certificate_state(norm, name, day) == "expired":
            gaps.append(
                {
                    "competence": name,
                    "reason": GAP_EXPIRED,
                    "required_level": wanted,
                    "held_level": entry["level"],
                    "shortfall": shortfall,
                }
            )
        if not entry["trained"]:
            gaps.append(
                {
                    "competence": name,
                    "reason": GAP_UNTRAINED,
                    "required_level": wanted,
                    "held_level": entry["level"],
                    "shortfall": shortfall,
                }
            )
        if entry["assessed_on_day"] is not None and not record_is_within_retention(
            norm, name, day
        ):
            gaps.append(
                {
                    "competence": name,
                    "reason": GAP_RECORD_STALE,
                    "required_level": wanted,
                    "held_level": entry["level"],
                    "shortfall": shortfall,
                }
            )
    return gaps


def is_cleared_for_role(person, as_of_day):
    """True only when the person carries no gap against the role."""
    return not competence_gaps(person, as_of_day)


def training_plan(person, as_of_day):
    """Competences to train, worst shortfall first then alphabetical."""
    gaps = competence_gaps(person, as_of_day)
    merged = {}
    for gap in gaps:
        name = gap["competence"]
        current = merged.get(name)
        if current is None or gap["shortfall"] > current["shortfall"]:
            merged[name] = {
                "competence": name,
                "shortfall": gap["shortfall"],
                "reasons": [],
            }
    for gap in gaps:
        merged[gap["competence"]]["reasons"].append(gap["reason"])
    plan = list(merged.values())
    for item in plan:
        item["reasons"] = sorted(set(item["reasons"]))
    plan.sort(key=lambda item: (-item["shortfall"], item["competence"]))
    return plan


def assess_person(person, as_of_day):
    """Assess one person against the competence need of their role."""
    norm = validate_person(person)
    gaps = competence_gaps(norm, as_of_day)
    return {
        "id": norm["id"],
        "role": norm["role"],
        "gaps": gaps,
        "training_plan": training_plan(norm, as_of_day),
        "cleared": not gaps,
    }


def role_clearance_ratio(people, role, as_of_day):
    """Fraction of the people proposed for one role who are cleared for it."""
    if role not in ROLE_COMPETENCE_REQUIREMENTS:
        raise ValueError("unknown role %r" % (role,))
    in_role = [p for p in people if validate_person(p)["role"] == role]
    if not in_role:
        raise ValueError("no person in the register is proposed for role %r" % (role,))
    cleared = sum(1 for p in in_role if is_cleared_for_role(p, as_of_day))
    return cleared / len(in_role)


def assess_personnel(people, as_of_day):
    """Run the full clause 5.4 assessment over a test-centre register."""
    if not isinstance(people, list) or not people:
        raise ValueError("people must be a non-empty list")
    day = _integer("as_of_day", as_of_day)
    results = []
    seen = set()
    for person in people:
        result = assess_person(person, day)
        if result["id"] in seen:
            raise ValueError("duplicate person id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    blocked = [r["id"] for r in results if not r["cleared"]]
    roles = sorted({r["role"] for r in results})
    return {
        "people": results,
        "cleared_ids": [r["id"] for r in results if r["cleared"]],
        "blocked_ids": blocked,
        "role_clearance_ratio": {
            role: role_clearance_ratio(people, role, day) for role in roles
        },
        "compliant": not blocked,
    }
