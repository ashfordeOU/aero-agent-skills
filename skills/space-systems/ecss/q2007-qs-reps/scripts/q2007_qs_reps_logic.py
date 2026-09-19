"""Quality and safety representative appointments in a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 5.3.4 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Read the appointment register. Each entry names one person, the role
   they hold (quality assurance or safety), how the appointment was made,
   the authorities the appointment carries, the position they report into,
   the chain of intermediaries between them and top management, and the
   test activities their appointment covers.
2. Refuse a register that cannot be read as an appointment: an unknown
   role, an unknown appointment form, an unknown authority token, an
   escalation chain that is not a sequence of positions, or a repeated
   entry identifier.
3. Grade each appointment on three independent properties, none of which
   substitutes for another:
   - Form. An appointment that exists only as a shared understanding is
     not an appointment: the authority has to be recorded so it can be
     pointed at during a test when it is being resisted.
   - Authority. The role fixes the authorities the appointment must
     carry. Both roles must be able to stop a test in progress and must
     be able to reach top management without permission from anyone; the
     quality role must additionally be able to raise a nonconformance.
   - Independence. A representative who reports into the line that runs
     the test is asking that same line to accept the cost of a stop. The
     reporting position is checked against the test-execution line, and
     an escalation chain longer than the direct-access limit is a
     finding even when the reporting position itself is clean.
4. Check coverage. Every test activity in scope needs at least one
   quality representative and at least one safety representative whose
   appointment is sound; an appointment that is itself deficient does not
   count as cover, because the cover it provides is the authority it
   failed to carry.
5. Report the authority-coverage ratio, the per-activity gaps and the
   finding list. The register is sound only when no entry carries a
   finding and no activity is uncovered.

Stdlib only, offline, deterministic.
"""

ROLE_QUALITY = "quality-assurance"
ROLE_SAFETY = "safety"
VALID_ROLES = (ROLE_QUALITY, ROLE_SAFETY)

APPOINTMENT_WRITTEN = "written-appointment"
APPOINTMENT_VERBAL = "verbal-understanding"
APPOINTMENT_NONE = "not-appointed"
VALID_APPOINTMENT_FORMS = (
    APPOINTMENT_WRITTEN,
    APPOINTMENT_VERBAL,
    APPOINTMENT_NONE,
)

AUTHORITY_STOP_TEST = "stop-test"
AUTHORITY_DIRECT_MANAGEMENT_ACCESS = "direct-management-access"
AUTHORITY_NONCONFORMANCE = "nonconformance-raising"
AUTHORITY_RELEASE_SIGNATURE = "test-release-signature"
AUTHORITY_WAIVER_ENDORSEMENT = "waiver-endorsement"
VALID_AUTHORITIES = (
    AUTHORITY_STOP_TEST,
    AUTHORITY_DIRECT_MANAGEMENT_ACCESS,
    AUTHORITY_NONCONFORMANCE,
    AUTHORITY_RELEASE_SIGNATURE,
    AUTHORITY_WAIVER_ENDORSEMENT,
)

# The authorities an appointment must carry, by role. Anything beyond
# these is allowed and is not graded.
REQUIRED_AUTHORITIES = {
    ROLE_QUALITY: (
        AUTHORITY_STOP_TEST,
        AUTHORITY_DIRECT_MANAGEMENT_ACCESS,
        AUTHORITY_NONCONFORMANCE,
    ),
    ROLE_SAFETY: (
        AUTHORITY_STOP_TEST,
        AUTHORITY_DIRECT_MANAGEMENT_ACCESS,
    ),
}

# Positions that own the delivery of the test. A representative reporting
# into one of these has to ask the cost-carrier for permission to stop.
TEST_EXECUTION_LINE = (
    "test-conductor",
    "test-operator",
    "test-campaign-manager",
    "facility-operations-manager",
    "programme-schedule-manager",
)

# "Direct access" means no intermediary stands between the representative
# and top management.
MAX_ESCALATION_HOPS = 0

FINDING_NOT_APPOINTED = "representative-not-appointed"
FINDING_INFORMAL = "appointment-not-recorded-in-writing"
FINDING_INTO_EXECUTION_LINE = "reports-into-the-test-execution-line"
FINDING_INDIRECT = "escalation-chain-not-direct-to-top-management"
FINDING_NO_ACTIVITY = "appointment-covers-no-test-activity"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _sequence(label, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (label, value))
    return list(value)


def validate_representative(record):
    """Validate one appointment-register entry and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("representative record must be a mapping")
    entry_id = _text("representative id", record.get("id"))
    role = record.get("role")
    if role not in VALID_ROLES:
        raise ValueError(
            "representative %s has unknown role %r (expected one of %s)"
            % (entry_id, role, ", ".join(VALID_ROLES))
        )
    form = record.get("appointment_form", APPOINTMENT_NONE)
    if form not in VALID_APPOINTMENT_FORMS:
        raise ValueError(
            "representative %s has unknown appointment_form %r (expected one of %s)"
            % (entry_id, form, ", ".join(VALID_APPOINTMENT_FORMS))
        )
    authorities = _sequence(
        "representative %s authorities" % entry_id, record.get("authorities", [])
    )
    for token in authorities:
        if token not in VALID_AUTHORITIES:
            raise ValueError(
                "representative %s has unknown authority %r (expected one of %s)"
                % (entry_id, token, ", ".join(VALID_AUTHORITIES))
            )
    chain = _sequence(
        "representative %s escalation_chain" % entry_id,
        record.get("escalation_chain", []),
    )
    for position in chain:
        _text("representative %s escalation_chain entry" % entry_id, position)
    activities = _sequence(
        "representative %s activities" % entry_id, record.get("activities", [])
    )
    for activity in activities:
        _text("representative %s activity" % entry_id, activity)
    reports_to = record.get("reports_to")
    if reports_to is not None:
        reports_to = _text("representative %s reports_to" % entry_id, reports_to)
    return {
        "id": entry_id,
        "role": role,
        "appointment_form": form,
        "authorities": sorted(set(str(a) for a in authorities)),
        "reports_to": reports_to,
        "escalation_chain": [str(p).strip() for p in chain],
        "activities": sorted(set(str(a).strip() for a in activities)),
    }


def required_authorities(role):
    """The authorities an appointment in this role has to carry."""
    if role not in VALID_ROLES:
        raise ValueError("unknown role %r" % (role,))
    return tuple(REQUIRED_AUTHORITIES[role])


def missing_authorities(record):
    """Required authorities this appointment does not carry, in order."""
    norm = validate_representative(record)
    held = set(norm["authorities"])
    return tuple(a for a in required_authorities(norm["role"]) if a not in held)


def can_stop_test(record):
    """True when this appointment can halt a test already running."""
    norm = validate_representative(record)
    return (
        norm["appointment_form"] == APPOINTMENT_WRITTEN
        and AUTHORITY_STOP_TEST in norm["authorities"]
    )


def escalation_hops(record):
    """Intermediaries standing between the representative and top management."""
    norm = validate_representative(record)
    return len(norm["escalation_chain"])


def has_direct_management_access(record):
    """True when the chain is short enough and the authority is granted."""
    norm = validate_representative(record)
    return (
        escalation_hops(norm) <= MAX_ESCALATION_HOPS
        and AUTHORITY_DIRECT_MANAGEMENT_ACCESS in norm["authorities"]
    )


def is_independent_of_test_execution(record):
    """True when the reporting position is outside the test-execution line."""
    norm = validate_representative(record)
    if norm["reports_to"] is None:
        return True
    return norm["reports_to"] not in TEST_EXECUTION_LINE


def assess_representative(record):
    """Assess one appointment against clause 5.3.4."""
    norm = validate_representative(record)
    findings = []
    if norm["appointment_form"] == APPOINTMENT_NONE:
        findings.append(FINDING_NOT_APPOINTED)
    elif norm["appointment_form"] == APPOINTMENT_VERBAL:
        findings.append(FINDING_INFORMAL)
    for token in missing_authorities(norm):
        findings.append("missing-authority-%s" % token)
    if not is_independent_of_test_execution(norm):
        findings.append(FINDING_INTO_EXECUTION_LINE)
    if escalation_hops(norm) > MAX_ESCALATION_HOPS:
        findings.append(FINDING_INDIRECT)
    if not norm["activities"]:
        findings.append(FINDING_NO_ACTIVITY)
    return {
        "id": norm["id"],
        "role": norm["role"],
        "appointment_form": norm["appointment_form"],
        "authorities": norm["authorities"],
        "missing_authorities": list(missing_authorities(norm)),
        "escalation_hops": escalation_hops(norm),
        "independent": is_independent_of_test_execution(norm),
        "can_stop_test": can_stop_test(norm),
        "activities": norm["activities"],
        "findings": findings,
        "sound": not findings,
    }


def authority_coverage_ratio(records):
    """Fraction of all required authorities the register actually carries."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    required = 0
    held = 0
    for record in records:
        norm = validate_representative(record)
        wanted = required_authorities(norm["role"])
        required += len(wanted)
        held += sum(1 for a in wanted if a in norm["authorities"])
    if required == 0:
        raise ValueError("no role in the register carries a required authority")
    return held / required


def coverage_gaps(records, activities):
    """Activities lacking a sound quality or safety representative."""
    wanted = _sequence("activities", activities)
    if not wanted:
        raise ValueError("activities must be a non-empty list")
    names = []
    for activity in wanted:
        names.append(_text("activity", activity))
    if len(set(names)) != len(names):
        raise ValueError("duplicate activity in the scope list")
    assessed = [assess_representative(r) for r in records]
    known = set(names)
    for result in assessed:
        for activity in result["activities"]:
            if activity not in known:
                raise ValueError(
                    "representative %s covers unknown activity %r"
                    % (result["id"], activity)
                )
    gaps = {}
    for activity in names:
        missing = []
        for role in VALID_ROLES:
            covered = any(
                result["sound"]
                and result["role"] == role
                and activity in result["activities"]
                for result in assessed
            )
            if not covered:
                missing.append(role)
        if missing:
            gaps[activity] = missing
    return gaps


def assess_appointment_register(records, activities):
    """Run the full clause 5.3.4 assessment over an appointment register."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_representative(record)
        if result["id"] in seen:
            raise ValueError("duplicate representative id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    gaps = coverage_gaps(records, activities)
    deficient = [r["id"] for r in results if not r["sound"]]
    return {
        "representatives": results,
        "deficient_ids": deficient,
        "stop_test_capable_ids": [r["id"] for r in results if r["can_stop_test"]],
        "authority_coverage_ratio": authority_coverage_ratio(records),
        "coverage_gaps": gaps,
        "sound": not deficient and not gaps,
    }
