#!/usr/bin/env python3
"""Connectors with removable contacts applied at the intermediate class.

Anchor: ECSS-Q-ST-60-13C clause 5.6.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause governs the use of a connector whose contacts can be taken out
of the insert and put back. Removability is the feature that makes the
connector repairable and it is the feature that wears it out: every
insertion works the retention clip that holds the contact in place, and a
clip worked too many times releases under vibration rather than under the
extraction tool.

Four numbers are computed rather than asserted. The insertion count per
contact says which positions have been worked past the limit and must be
replaced rather than reinserted. The consumed durability says how much of
the connector's rated mating life the planned integration, test and
flight matings will spend, because a connector arriving at launch with
its durability already spent has no margin for a late demate. The allowed
contact current is derived, not read: the rated current of a single
contact is derated for the class and derated again for the share of
contacts carrying current at once, since a fully loaded insert heats
itself and every contact in it. The spare provision says whether a repair
that needs a fresh position has one.

Contact loading is the step most often skipped. A connector sized on the
single-contact rating is sized for a connector with one wire in it, and
the same insert with every position energised runs hotter at a lower
current. The loading slope is what carries that, and it is applied to the
fraction of positions energised rather than to their count, so the same
policy works for a nine-way and a sixty-one-way insert.

The evidence list is scored rather than ticked. A subject may be carried
against a heritage connector of the same insert arrangement at this
class, which the class above does not allow, and heritage is credited
below a direct record so that a build documented entirely by what an
earlier programme did cannot read as a documented build.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CRIMP_REMOVABLE_CONTACT = "crimp-removable-contact"
SOLDER_CUP_REMOVABLE_CONTACT = "solder-cup-removable-contact"
PRINTED_BOARD_REMOVABLE_CONTACT = "printed-board-removable-contact"

RECOGNISED_TERMINATIONS = (
    CRIMP_REMOVABLE_CONTACT,
    SOLDER_CUP_REMOVABLE_CONTACT,
    PRINTED_BOARD_REMOVABLE_CONTACT,
)

CONTACT_RETENTION_FORCE_VERIFICATION = "contact-retention-force-verification"
INSERTION_AND_REMOVAL_TOOL_QUALIFICATION = "insertion-and-removal-tool-qualification"
TERMINATION_PROCESS_QUALIFICATION = "termination-process-qualification"
MATING_CYCLE_LOG = "mating-cycle-log"
INSULATION_RESISTANCE_MEASUREMENT = "insulation-resistance-measurement"
CONTACT_ARRANGEMENT_AND_KEYING_RECORD = "contact-arrangement-and-keying-record"

REQUIRED_EVIDENCE = (
    CONTACT_RETENTION_FORCE_VERIFICATION,
    INSERTION_AND_REMOVAL_TOOL_QUALIFICATION,
    TERMINATION_PROCESS_QUALIFICATION,
    MATING_CYCLE_LOG,
    INSULATION_RESISTANCE_MEASUREMENT,
    CONTACT_ARRANGEMENT_AND_KEYING_RECORD,
)

HELD_DIRECTLY = "held-as-a-direct-record"
HELD_AGAINST_HERITAGE = "held-against-a-heritage-connector"
DECLARED_WITHOUT_RECORD = "declared-without-a-record"
ABSENT = "absent"

HELD_STATES = (HELD_DIRECTLY, HELD_AGAINST_HERITAGE)

CONNECTOR_NOT_IDENTIFIED = "connector-not-identified"
CONTACT_INSERTION_LIMIT_EXCEEDED = "removable-contact-insertion-limit-exceeded"
CONNECTOR_CURRENT_DERATING_EXCEEDED = "connector-contact-current-derating-exceeded"
CONNECTOR_DURABILITY_CONSUMED = "connector-mating-cycle-durability-consumed"
CONNECTOR_SPARE_PROVISION_SHORT = "connector-spare-contact-provision-short"
CONNECTOR_EVIDENCE_SHORT = "connector-evidence-short"
CONNECTOR_MEETS_CLASS_TWO_SCOPE = "connector-meets-class-two-scope"

DEFAULT_CONNECTOR_POLICY = {
    "max_contact_insertions": 3,
    "contact_current_derating_factor": 0.5,
    "contact_loading_slope": 0.3,
    "max_mating_cycle_fraction": 0.5,
    "min_spare_contact_share": 0.1,
    "min_evidence_share": 1.0,
    "min_weighted_evidence": 0.6,
    "heritage_credit": 0.7,
    "marginal_current_band": 0.05,
    "require_removal_tool_reference": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_connector_policy(policy):
    """Check the connector policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    insertions = _require_count(
        "max_contact_insertions", policy.get("max_contact_insertions")
    )
    if insertions < 1:
        raise ValueError(
            "max_contact_insertions must allow at least the first insertion, "
            "got %r" % (insertions,)
        )
    derating = _require_fraction(
        "contact_current_derating_factor",
        policy.get("contact_current_derating_factor"),
    )
    if derating <= 0.0:
        raise ValueError(
            "contact_current_derating_factor must be greater than zero, got %r"
            % (derating,)
        )
    slope = _require_fraction(
        "contact_loading_slope", policy.get("contact_loading_slope")
    )
    if slope >= 1.0:
        raise ValueError(
            "contact_loading_slope %g would take the allowed current to zero on "
            "a fully loaded insert" % (slope,)
        )
    cycles = _require_fraction(
        "max_mating_cycle_fraction", policy.get("max_mating_cycle_fraction")
    )
    if cycles <= 0.0:
        raise ValueError(
            "max_mating_cycle_fraction must be greater than zero, got %r" % (cycles,)
        )
    _require_fraction(
        "min_spare_contact_share", policy.get("min_spare_contact_share")
    )
    share = _require_fraction("min_evidence_share", policy.get("min_evidence_share"))
    weighted = _require_fraction(
        "min_weighted_evidence", policy.get("min_weighted_evidence")
    )
    if weighted > share:
        raise ValueError(
            "min_weighted_evidence %g is above min_evidence_share %g; a credited "
            "figure can never exceed the plain one" % (weighted, share)
        )
    credit = _require_fraction("heritage_credit", policy.get("heritage_credit"))
    if credit <= 0.0:
        raise ValueError(
            "heritage_credit must be greater than zero, got %r" % (credit,)
        )
    _require_fraction(
        "marginal_current_band", policy.get("marginal_current_band")
    )
    _require_flag(
        "require_removal_tool_reference",
        policy.get("require_removal_tool_reference"),
    )
    return policy


def validate_connector_identity(case):
    """Read the connector reference, its ratings and the removal tool."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    reference = _require_label(
        "connector_reference", case.get("connector_reference", "")
    )
    arrangement = _require_label(
        "insert_arrangement", case.get("insert_arrangement", "")
    )
    rated_current = _require_positive(
        "rated_contact_current_a", case.get("rated_contact_current_a")
    )
    rated_cycles = _require_positive(
        "rated_mating_cycles", case.get("rated_mating_cycles")
    )
    planned_cycles = _require_non_negative(
        "planned_mating_cycles", case.get("planned_mating_cycles")
    )
    tool = _require_label(
        "removal_tool_reference", case.get("removal_tool_reference", "")
    )
    return {
        "connector_reference": reference,
        "insert_arrangement": arrangement,
        "rated_contact_current_a": rated_current,
        "rated_mating_cycles": rated_cycles,
        "planned_mating_cycles": planned_cycles,
        "removal_tool_reference": tool,
    }


def validate_contact_record(entry):
    """Read one removable contact position and what it carries."""
    if not isinstance(entry, dict):
        raise ValueError("contact entry must be a mapping, got %r" % (entry,))
    position = _require_label("position", entry.get("position"))
    if not position:
        raise ValueError("a contact position must be named, got a blank one")
    termination = _require_label("termination on %s" % position, entry.get("termination"))
    if termination not in RECOGNISED_TERMINATIONS:
        raise ValueError(
            "unrecognised termination %r on position %s; the termination names "
            "are fixed" % (termination, position)
        )
    energised = _require_flag(
        "energised on %s" % position, entry.get("energised", False)
    )
    current = _require_non_negative(
        "current_a on %s" % position, entry.get("current_a", 0.0)
    )
    insertions = _require_count(
        "insertion_count on %s" % position, entry.get("insertion_count")
    )
    spare = _require_flag("spare on %s" % position, entry.get("spare", False))
    if spare and energised:
        raise ValueError(
            "position %s is declared both spare and energised; a spare position "
            "carries nothing" % position
        )
    if energised and current <= 0.0:
        raise ValueError(
            "position %s is energised but carries no current; declare the "
            "current it carries or declare it unenergised" % position
        )
    return {
        "position": position,
        "termination": termination,
        "energised": energised,
        "current_a": current if energised else 0.0,
        "insertion_count": insertions,
        "spare": spare,
    }


def validate_contacts(contacts):
    """Read every declared contact, refusing an empty or repeated set."""
    if not isinstance(contacts, (list, tuple)):
        raise ValueError("contacts must be a sequence of contact records")
    if not contacts:
        raise ValueError("the connector declares no contact position")
    checked = []
    seen = set()
    for entry in contacts:
        record = validate_contact_record(entry)
        if record["position"] in seen:
            raise ValueError(
                "contact position %r is declared twice" % record["position"]
            )
        seen.add(record["position"])
        checked.append(record)
    return tuple(checked)


def energised_positions(contacts):
    """Positions carrying current."""
    return tuple(r["position"] for r in validate_contacts(contacts) if r["energised"])


def spare_positions(contacts):
    """Positions held unused for a later repair."""
    return tuple(r["position"] for r in validate_contacts(contacts) if r["spare"])


def contact_loading_fraction(contacts):
    """Share of the insert's positions carrying current at once."""
    checked = validate_contacts(contacts)
    return len([r for r in checked if r["energised"]]) / len(checked)


def spare_contact_share(contacts):
    """Share of the insert's positions held spare."""
    checked = validate_contacts(contacts)
    return len([r for r in checked if r["spare"]]) / len(checked)


def contact_loading_factor(contacts, policy=DEFAULT_CONNECTOR_POLICY):
    """The self-heating factor applied on top of the class derating."""
    validate_connector_policy(policy)
    return 1.0 - float(policy["contact_loading_slope"]) * contact_loading_fraction(
        contacts
    )


def allowed_contact_current_a(case, policy=DEFAULT_CONNECTOR_POLICY):
    """Current one contact may carry, derated for the class and the loading."""
    validate_connector_policy(policy)
    identity = validate_connector_identity(case)
    contacts = case.get("contacts")
    return (
        identity["rated_contact_current_a"]
        * float(policy["contact_current_derating_factor"])
        * contact_loading_factor(contacts, policy)
    )


def overloaded_positions(case, policy=DEFAULT_CONNECTOR_POLICY):
    """Positions carrying more than the derated allowance."""
    allowed = allowed_contact_current_a(case, policy)
    return tuple(
        record["position"]
        for record in validate_contacts(case.get("contacts"))
        if not _at_most(record["current_a"], allowed)
    )


def over_inserted_positions(case, policy=DEFAULT_CONNECTOR_POLICY):
    """Positions worked past the insertion limit, which need a fresh contact."""
    validate_connector_policy(policy)
    limit = int(policy["max_contact_insertions"])
    return tuple(
        record["position"]
        for record in validate_contacts(case.get("contacts"))
        if record["insertion_count"] > limit
    )


def mating_cycle_fraction(case):
    """Share of the rated mating life the planned matings will spend."""
    identity = validate_connector_identity(case)
    return identity["planned_mating_cycles"] / identity["rated_mating_cycles"]


def validate_evidence_record(entry):
    """Read one declared connector evidence item."""
    if not isinstance(entry, dict):
        raise ValueError("evidence entry must be a mapping, got %r" % (entry,))
    subject = _require_label("subject", entry.get("subject"))
    if subject not in REQUIRED_EVIDENCE:
        raise ValueError(
            "unrecognised evidence subject %r; the subject names are fixed"
            % (subject,)
        )
    by_heritage = _require_flag(
        "held_against_heritage on %s" % subject,
        entry.get("held_against_heritage", False),
    )
    record = _require_label(
        "record_reference on %s" % subject, entry.get("record_reference", "")
    )
    heritage = _require_label(
        "heritage_connector_reference on %s" % subject,
        entry.get("heritage_connector_reference", ""),
    )
    if by_heritage and record:
        raise ValueError(
            "%s is declared both as a direct record and as a heritage claim; it "
            "is one or the other" % subject
        )
    return {
        "subject": subject,
        "held_against_heritage": by_heritage,
        "record_reference": record,
        "heritage_connector_reference": heritage,
    }


def validate_evidence(records):
    """Read every declared evidence item, refusing an empty or repeated set."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("evidence must be a sequence of evidence records")
    if not records:
        raise ValueError("no connector evidence is declared")
    checked = []
    seen = set()
    for entry in records:
        item = validate_evidence_record(entry)
        if item["subject"] in seen:
            raise ValueError("evidence subject %r is declared twice" % item["subject"])
        seen.add(item["subject"])
        checked.append(item)
    return tuple(checked)


def evidence_disposition(records, policy=DEFAULT_CONNECTOR_POLICY):
    """How each required evidence subject is held, with its credit."""
    validate_connector_policy(policy)
    checked = validate_evidence(records)
    credit = float(policy["heritage_credit"])
    declared = {item["subject"]: item for item in checked}
    disposition = {}
    for subject in REQUIRED_EVIDENCE:
        item = declared.get(subject)
        if item is None:
            disposition[subject] = {"state": ABSENT, "credit": 0.0}
            continue
        if item["held_against_heritage"]:
            if item["heritage_connector_reference"]:
                disposition[subject] = {"state": HELD_AGAINST_HERITAGE, "credit": credit}
            else:
                disposition[subject] = {"state": DECLARED_WITHOUT_RECORD, "credit": 0.0}
            continue
        if item["record_reference"]:
            disposition[subject] = {"state": HELD_DIRECTLY, "credit": 1.0}
        else:
            disposition[subject] = {"state": DECLARED_WITHOUT_RECORD, "credit": 0.0}
    return disposition


def _evidence_in_state(records, states, policy):
    disposition = evidence_disposition(records, policy)
    return tuple(
        subject
        for subject in REQUIRED_EVIDENCE
        if disposition[subject]["state"] in states
    )


def held_evidence(records, policy=DEFAULT_CONNECTOR_POLICY):
    """Required subjects the build actually holds."""
    return _evidence_in_state(records, HELD_STATES, policy)


def absent_evidence(records, policy=DEFAULT_CONNECTOR_POLICY):
    """Required subjects the build does not declare at all."""
    return _evidence_in_state(records, (ABSENT,), policy)


def unrecorded_evidence(records, policy=DEFAULT_CONNECTOR_POLICY):
    """Subjects declared with neither a record nor a named heritage connector."""
    return _evidence_in_state(records, (DECLARED_WITHOUT_RECORD,), policy)


def heritage_evidence(records, policy=DEFAULT_CONNECTOR_POLICY):
    """Subjects carried against an earlier connector of the same arrangement."""
    return _evidence_in_state(records, (HELD_AGAINST_HERITAGE,), policy)


def evidence_share(records, policy=DEFAULT_CONNECTOR_POLICY):
    """Share of the required subjects the build holds."""
    return len(held_evidence(records, policy)) / len(REQUIRED_EVIDENCE)


def weighted_evidence(records, policy=DEFAULT_CONNECTOR_POLICY):
    """Credited evidence over the full required subject list."""
    disposition = evidence_disposition(records, policy)
    total = 0.0
    for subject in REQUIRED_EVIDENCE:
        total += disposition[subject]["credit"]
    return total / len(REQUIRED_EVIDENCE)


def current_advisories(case, policy=DEFAULT_CONNECTOR_POLICY):
    """Name positions sitting inside the marginal band under the allowance.

    These do not move the verdict -- a position under the allowance is
    within the allowance -- but a contact a hair under and one at half the
    allowance carry the same word, and nobody recovers the difference later
    from the word alone.
    """
    allowed = allowed_contact_current_a(case, policy)
    band = float(policy["marginal_current_band"]) * allowed
    advisories = []
    for record in validate_contacts(case.get("contacts")):
        if not record["energised"]:
            continue
        if not _at_most(record["current_a"], allowed):
            continue
        if _at_most(allowed - record["current_a"], band):
            advisories.append(
                "position %s carries %.4g A against a %.4g A allowance, inside "
                "the marginal band; it is within the allowance today and is the "
                "position a late harness change would take out first"
                % (record["position"], record["current_a"], allowed)
            )
    return tuple(advisories)


def assess_connector_application(case, policy=DEFAULT_CONNECTOR_POLICY):
    """Full clause 5.6.6 application decision for one connector."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_connector_policy(policy)

    findings = []
    advisories = []
    result = {
        "connector_reference": None,
        "insert_arrangement": None,
        "contact_loading_fraction": None,
        "allowed_contact_current_a": None,
        "overloaded_positions": (),
        "over_inserted_positions": (),
        "mating_cycle_fraction": None,
        "spare_contact_share": None,
        "evidence_share": None,
        "weighted_evidence": None,
        "absent_evidence": (),
        "unrecorded_evidence": (),
        "heritage_evidence": (),
        "findings": findings,
        "advisories": advisories,
    }

    identity = validate_connector_identity(case)
    result["connector_reference"] = identity["connector_reference"]
    result["insert_arrangement"] = identity["insert_arrangement"]
    missing_tool = (
        policy["require_removal_tool_reference"]
        and not identity["removal_tool_reference"]
    )
    if (
        not identity["connector_reference"]
        or not identity["insert_arrangement"]
        or missing_tool
    ):
        findings.append(
            "the connector carries no reference, no insert arrangement or no "
            "removal tool reference, so no contact in it can be taken out "
            "against a known procedure"
        )
        result["verdict"] = CONNECTOR_NOT_IDENTIFIED
        return result

    contacts = case.get("contacts")
    if contacts is None:
        findings.append(
            "no contact positions are declared, so nothing is known about what "
            "the insert carries or how often it has been worked"
        )
        result["verdict"] = CONNECTOR_NOT_IDENTIFIED
        return result

    checked = validate_contacts(contacts)
    loading = contact_loading_fraction(checked)
    allowed = allowed_contact_current_a(case, policy)
    overloaded = overloaded_positions(case, policy)
    over_inserted = over_inserted_positions(case, policy)
    cycles = mating_cycle_fraction(case)
    spares = spare_contact_share(checked)
    result["contact_loading_fraction"] = loading
    result["allowed_contact_current_a"] = allowed
    result["overloaded_positions"] = overloaded
    result["over_inserted_positions"] = over_inserted
    result["mating_cycle_fraction"] = cycles
    result["spare_contact_share"] = spares
    advisories.extend(current_advisories(case, policy))

    if over_inserted:
        for position in over_inserted:
            findings.append(
                "position %s has been worked past the %d insertion limit; the "
                "retention clip no longer holds the contact against vibration "
                "and the contact has to be replaced rather than reinserted"
                % (position, int(policy["max_contact_insertions"]))
            )
        result["verdict"] = CONTACT_INSERTION_LIMIT_EXCEEDED
        return result

    if overloaded:
        for position in overloaded:
            findings.append(
                "position %s carries more than the %.4g A allowed once the class "
                "derating and the %.4g insert loading are applied"
                % (position, allowed, loading)
            )
        result["verdict"] = CONNECTOR_CURRENT_DERATING_EXCEEDED
        return result

    if not _at_most(cycles, float(policy["max_mating_cycle_fraction"])):
        findings.append(
            "the planned matings spend %.4g of the rated mating life against the "
            "%.4g the class reserves, so the connector reaches launch with no "
            "margin for a late demate"
            % (cycles, float(policy["max_mating_cycle_fraction"]))
        )
        result["verdict"] = CONNECTOR_DURABILITY_CONSUMED
        return result

    if not _at_least(spares, float(policy["min_spare_contact_share"])):
        findings.append(
            "the insert holds %.4g of its positions spare against the %.4g the "
            "class asks for, so a repair needing a fresh position has none"
            % (spares, float(policy["min_spare_contact_share"]))
        )
        result["verdict"] = CONNECTOR_SPARE_PROVISION_SHORT
        return result

    records = case.get("evidence")
    if records is None:
        findings.append(
            "no connector evidence is declared, so neither the retention of the "
            "contacts nor the process that terminated them has been shown"
        )
        result["verdict"] = CONNECTOR_EVIDENCE_SHORT
        return result

    evidence = validate_evidence(records)
    share = evidence_share(evidence, policy)
    weighted = weighted_evidence(evidence, policy)
    absent = absent_evidence(evidence, policy)
    unrecorded = unrecorded_evidence(evidence, policy)
    heritage = heritage_evidence(evidence, policy)
    result["evidence_share"] = share
    result["weighted_evidence"] = weighted
    result["absent_evidence"] = absent
    result["unrecorded_evidence"] = unrecorded
    result["heritage_evidence"] = heritage

    for subject in absent:
        findings.append("the build does not declare %s at all" % subject)
    for subject in unrecorded:
        findings.append(
            "%s is declared with neither a record reference nor a named heritage "
            "connector behind it" % subject
        )

    share_short = not _at_least(share, float(policy["min_evidence_share"]))
    weighted_short = not _at_least(weighted, float(policy["min_weighted_evidence"]))
    if share_short or weighted_short:
        findings.append(
            "the build holds %.4g of the required subjects against %.4g, at a "
            "credited %.4g against %.4g"
            % (
                share,
                float(policy["min_evidence_share"]),
                weighted,
                float(policy["min_weighted_evidence"]),
            )
        )
        result["verdict"] = CONNECTOR_EVIDENCE_SHORT
        return result

    result["verdict"] = CONNECTOR_MEETS_CLASS_TWO_SCOPE
    return result
