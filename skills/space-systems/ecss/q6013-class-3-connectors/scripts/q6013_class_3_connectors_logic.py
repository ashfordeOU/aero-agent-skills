#!/usr/bin/env python3
"""Connector selection and contact sourcing at the lowest assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.6.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause covers two decisions that are usually taken by different
people on different days and then never reconciled: which connector
family a harness is built around, and where the contacts that go into it
come from. At the lowest assurance class both decisions are permitted to
rest on lighter standing than the classes above allow, which is exactly
why they have to be written down and scored rather than assumed.

The family decision is arithmetic, not preference. A candidate family is
admissible only where its derated contact current covers the worst
circuit in the wire list, where the insert has positions left over after
every circuit is placed, and where the family has some recognised
standing. The derated current is derived rather than read: the rated
current of a single contact is derated for the class and derated again
for the share of positions carrying current at once, because an insert
with every position loaded heats itself and every contact in it.

The sourcing decision is a supply question with a quality tail. Contacts
bought from the connector manufacturer carry the insert's own retention
and plating basis. Contacts bought from an alternative source may be
used at this class where an interchangeability record exists, and they
are credited below a manufacturer part because the record covers the
dimensions rather than the process. Contacts from an unidentified source
close the assessment on their own: an insert cannot be repaired against
a part nobody can name.

The evidence list is scored rather than ticked. A subject may be carried
by a supplier declaration at this class, which the classes above do not
allow, and a declaration is credited below a project record so that a
selection documented entirely by what a supplier says about itself
cannot read as a documented selection.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CIRCULAR_BAYONET_COUPLING = "circular-bayonet-coupling"
CIRCULAR_THREADED_COUPLING = "circular-threaded-coupling"
RECTANGULAR_MICRO_D = "rectangular-micro-d"
RECTANGULAR_NANO_D = "rectangular-nano-d"
PRINTED_BOARD_EDGE_CONNECTOR = "printed-board-edge-connector"

RECOGNISED_FAMILIES = (
    CIRCULAR_BAYONET_COUPLING,
    CIRCULAR_THREADED_COUPLING,
    RECTANGULAR_MICRO_D,
    RECTANGULAR_NANO_D,
    PRINTED_BOARD_EDGE_CONNECTOR,
)

QUALIFIED_TO_A_RECOGNISED_SPECIFICATION = "qualified-to-a-recognised-specification"
MANUFACTURER_CATALOGUE_ONLY = "manufacturer-catalogue-only"
NO_SPECIFICATION_HELD = "no-specification-held"

RECOGNISED_STANDINGS = (
    QUALIFIED_TO_A_RECOGNISED_SPECIFICATION,
    MANUFACTURER_CATALOGUE_ONLY,
    NO_SPECIFICATION_HELD,
)

STANDING_WEIGHT = {
    QUALIFIED_TO_A_RECOGNISED_SPECIFICATION: 1.0,
    MANUFACTURER_CATALOGUE_ONLY: 0.6,
    NO_SPECIFICATION_HELD: 0.0,
}

CONNECTOR_MANUFACTURER_SOURCE = "connector-manufacturer-source"
INTERCHANGEABLE_ALTERNATIVE_SOURCE = "interchangeable-alternative-source"
UNIDENTIFIED_SOURCE = "unidentified-source"

RECOGNISED_CONTACT_SOURCES = (
    CONNECTOR_MANUFACTURER_SOURCE,
    INTERCHANGEABLE_ALTERNATIVE_SOURCE,
    UNIDENTIFIED_SOURCE,
)

CONNECTOR_SPECIFICATION_REFERENCE = "connector-specification-reference"
CONTACT_PLATING_AND_BASE_METAL_RECORD = "contact-plating-and-base-metal-record"
CONTACT_TERMINATION_TOOL_REFERENCE = "contact-termination-tool-reference"
CONNECTOR_LOT_TRACEABILITY_RECORD = "connector-lot-traceability-record"
CONNECTOR_OUTGASSING_SCREENING_RECORD = "connector-outgassing-screening-record"

REQUIRED_SELECTION_EVIDENCE = (
    CONNECTOR_SPECIFICATION_REFERENCE,
    CONTACT_PLATING_AND_BASE_METAL_RECORD,
    CONTACT_TERMINATION_TOOL_REFERENCE,
    CONNECTOR_LOT_TRACEABILITY_RECORD,
    CONNECTOR_OUTGASSING_SCREENING_RECORD,
)

HELD_AS_A_PROJECT_RECORD = "held-as-a-project-record"
HELD_AS_A_SUPPLIER_DECLARATION = "held-as-a-supplier-declaration"
DECLARED_WITHOUT_A_RECORD = "declared-without-a-record"
ABSENT = "absent"

HELD_STATES = (HELD_AS_A_PROJECT_RECORD, HELD_AS_A_SUPPLIER_DECLARATION)

SELECTION_NOT_DECLARED = "connector-selection-not-declared"
NO_ADMISSIBLE_CANDIDATE = "no-admissible-connector-candidate"
CONTACT_SOURCING_NOT_ESTABLISHED = "contact-sourcing-not-established"
CONTACT_SUPPLY_SHORT = "contact-supply-short"
CONTACT_SOURCING_CREDIT_SHORT = "contact-sourcing-credit-short"
SELECTION_EVIDENCE_SHORT = "connector-selection-evidence-short"
SELECTION_MEETS_CLASS_THREE_SCOPE = "connector-selection-meets-class-three-scope"

DEFAULT_SELECTION_POLICY = {
    "contact_current_derating_factor": 0.6,
    "contact_loading_slope": 0.25,
    "min_spare_position_share": 0.1,
    "min_manufacturer_sourced_share": 0.5,
    "alternative_source_credit": 0.6,
    "min_sourcing_credit": 0.7,
    "supplier_declaration_credit": 0.5,
    "min_evidence_share": 0.8,
    "min_weighted_evidence": 0.6,
    "marginal_headroom_band": 0.1,
    "accept_catalogue_only_family": True,
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


def _require_positive_count(name, value):
    count = _require_count(name, value)
    if count < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return count


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


def validate_selection_policy(policy):
    """Check the connector selection policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
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
    spare = _require_fraction(
        "min_spare_position_share", policy.get("min_spare_position_share")
    )
    if spare >= 1.0:
        raise ValueError(
            "min_spare_position_share %g would leave no position for a circuit"
            % (spare,)
        )
    _require_fraction(
        "min_manufacturer_sourced_share",
        policy.get("min_manufacturer_sourced_share"),
    )
    credit = _require_fraction(
        "alternative_source_credit", policy.get("alternative_source_credit")
    )
    if credit <= 0.0:
        raise ValueError(
            "alternative_source_credit must be greater than zero, got %r" % (credit,)
        )
    if credit >= 1.0:
        raise ValueError(
            "alternative_source_credit %g would make an alternative contact the "
            "equal of a manufacturer contact" % (credit,)
        )
    _require_fraction("min_sourcing_credit", policy.get("min_sourcing_credit"))
    declaration = _require_fraction(
        "supplier_declaration_credit", policy.get("supplier_declaration_credit")
    )
    if declaration <= 0.0:
        raise ValueError(
            "supplier_declaration_credit must be greater than zero, got %r"
            % (declaration,)
        )
    if declaration >= 1.0:
        raise ValueError(
            "supplier_declaration_credit %g would make a declaration the equal of "
            "a project record" % (declaration,)
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
    _require_fraction(
        "marginal_headroom_band", policy.get("marginal_headroom_band")
    )
    _require_flag(
        "accept_catalogue_only_family",
        policy.get("accept_catalogue_only_family"),
    )
    return policy


def validate_circuit_demand(case):
    """Read the harness the connector has to carry."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    reference = _require_label(
        "harness_reference", case.get("harness_reference", "")
    )
    circuits = _require_positive_count("circuit_count", case.get("circuit_count"))
    current = _require_positive(
        "max_circuit_current_a", case.get("max_circuit_current_a")
    )
    return {
        "harness_reference": reference,
        "circuit_count": circuits,
        "max_circuit_current_a": current,
    }


def validate_candidate(entry):
    """Read one candidate connector family offered for the harness."""
    if not isinstance(entry, dict):
        raise ValueError("candidate entry must be a mapping, got %r" % (entry,))
    reference = _require_label("candidate reference", entry.get("reference"))
    if not reference:
        raise ValueError("a candidate connector must be named, got a blank one")
    family = _require_label("family on %s" % reference, entry.get("family"))
    if family not in RECOGNISED_FAMILIES:
        raise ValueError(
            "unrecognised connector family %r on %s; the family names are fixed"
            % (family, reference)
        )
    standing = _require_label("standing on %s" % reference, entry.get("standing"))
    if standing not in RECOGNISED_STANDINGS:
        raise ValueError(
            "unrecognised qualification standing %r on %s; the standing names "
            "are fixed" % (standing, reference)
        )
    positions = _require_positive_count(
        "insert_positions on %s" % reference, entry.get("insert_positions")
    )
    rated = _require_positive(
        "rated_contact_current_a on %s" % reference,
        entry.get("rated_contact_current_a"),
    )
    return {
        "reference": reference,
        "family": family,
        "standing": standing,
        "insert_positions": positions,
        "rated_contact_current_a": rated,
    }


def validate_candidates(candidates):
    """Read every candidate, refusing an empty or repeated set."""
    if not isinstance(candidates, (list, tuple)):
        raise ValueError("candidates must be a sequence of candidate records")
    if not candidates:
        raise ValueError("no candidate connector family is offered")
    checked = []
    seen = set()
    for entry in candidates:
        record = validate_candidate(entry)
        if record["reference"] in seen:
            raise ValueError(
                "candidate connector %r is offered twice" % record["reference"]
            )
        seen.add(record["reference"])
        checked.append(record)
    return tuple(checked)


def position_loading_fraction(candidate, demand):
    """Share of the candidate insert carrying a circuit at once."""
    record = validate_candidate(candidate)
    wanted = validate_circuit_demand(demand)
    return min(
        wanted["circuit_count"] / record["insert_positions"],
        1.0,
    )


def position_loading_factor(candidate, demand, policy=DEFAULT_SELECTION_POLICY):
    """Self-heating factor applied on top of the class derating."""
    validate_selection_policy(policy)
    return 1.0 - float(policy["contact_loading_slope"]) * position_loading_fraction(
        candidate, demand
    )


def allowed_contact_current_a(candidate, demand, policy=DEFAULT_SELECTION_POLICY):
    """Current one contact of the candidate may carry in this harness."""
    validate_selection_policy(policy)
    record = validate_candidate(candidate)
    return (
        record["rated_contact_current_a"]
        * float(policy["contact_current_derating_factor"])
        * position_loading_factor(candidate, demand, policy)
    )


def current_headroom(candidate, demand, policy=DEFAULT_SELECTION_POLICY):
    """Derated contact allowance over the worst circuit in the wire list."""
    wanted = validate_circuit_demand(demand)
    return (
        allowed_contact_current_a(candidate, demand, policy)
        / wanted["max_circuit_current_a"]
    )


def spare_position_share(candidate, demand):
    """Share of the candidate insert left over once every circuit is placed."""
    record = validate_candidate(candidate)
    wanted = validate_circuit_demand(demand)
    spare = record["insert_positions"] - wanted["circuit_count"]
    return spare / record["insert_positions"]


def candidate_findings(candidate, demand, policy=DEFAULT_SELECTION_POLICY):
    """Every reason the candidate cannot carry this harness at this class."""
    validate_selection_policy(policy)
    record = validate_candidate(candidate)
    findings = []
    if record["standing"] == NO_SPECIFICATION_HELD:
        findings.append(
            "%s is offered against no specification at all, so nothing states "
            "what a contact in it is meant to withstand" % record["reference"]
        )
    elif record["standing"] == MANUFACTURER_CATALOGUE_ONLY and not policy[
        "accept_catalogue_only_family"
    ]:
        findings.append(
            "%s is offered on a manufacturer catalogue entry, which this project "
            "has declared insufficient standing" % record["reference"]
        )
    headroom = current_headroom(candidate, demand, policy)
    if not _at_least(headroom, 1.0):
        findings.append(
            "%s allows %.4g A per contact once the class derating and the insert "
            "loading are applied, against a worst circuit of %.4g A"
            % (
                record["reference"],
                allowed_contact_current_a(candidate, demand, policy),
                validate_circuit_demand(demand)["max_circuit_current_a"],
            )
        )
    spare = spare_position_share(candidate, demand)
    if not _at_least(spare, float(policy["min_spare_position_share"])):
        findings.append(
            "%s leaves %.4g of its insert spare against the %.4g the class asks "
            "for, so a late circuit needs a different connector"
            % (
                record["reference"],
                spare,
                float(policy["min_spare_position_share"]),
            )
        )
    return tuple(findings)


def candidate_score(candidate, demand, policy=DEFAULT_SELECTION_POLICY):
    """Rank an admissible candidate on standing, current and spare positions."""
    validate_selection_policy(policy)
    record = validate_candidate(candidate)
    standing = STANDING_WEIGHT[record["standing"]]
    headroom = min(current_headroom(candidate, demand, policy), 2.0) / 2.0
    floor = float(policy["min_spare_position_share"])
    spare = spare_position_share(candidate, demand)
    if floor <= 0.0:
        room = 1.0
    else:
        room = min(max(spare, 0.0) / (2.0 * floor), 1.0)
    return 0.4 * standing + 0.35 * headroom + 0.25 * room


def admissible_candidates(case, policy=DEFAULT_SELECTION_POLICY):
    """Candidates with no finding against them."""
    demand = validate_circuit_demand(case)
    return tuple(
        record
        for record in validate_candidates(case.get("candidates"))
        if not candidate_findings(record, demand, policy)
    )


def rank_candidates(case, policy=DEFAULT_SELECTION_POLICY):
    """Admissible candidates, best first, ties broken on the reference."""
    demand = validate_circuit_demand(case)
    scored = [
        (candidate_score(record, demand, policy), record["reference"], record)
        for record in admissible_candidates(case, policy)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(record for _, _, record in scored)


def selected_candidate(case, policy=DEFAULT_SELECTION_POLICY):
    """The candidate the ranking picks, or None when none is admissible."""
    ranked = rank_candidates(case, policy)
    return ranked[0] if ranked else None


def validate_contact_lot(entry):
    """Read one delivered contact lot and where it came from."""
    if not isinstance(entry, dict):
        raise ValueError("contact lot entry must be a mapping, got %r" % (entry,))
    reference = _require_label("lot reference", entry.get("lot_reference"))
    if not reference:
        raise ValueError("a contact lot must be named, got a blank one")
    source = _require_label("source on %s" % reference, entry.get("source"))
    if source not in RECOGNISED_CONTACT_SOURCES:
        raise ValueError(
            "unrecognised contact source %r on %s; the source names are fixed"
            % (source, reference)
        )
    count = _require_positive_count(
        "contact_count on %s" % reference, entry.get("contact_count")
    )
    record = _require_label(
        "interchangeability_record on %s" % reference,
        entry.get("interchangeability_record", ""),
    )
    if source == CONNECTOR_MANUFACTURER_SOURCE and record:
        raise ValueError(
            "lot %s comes from the connector manufacturer and also cites an "
            "interchangeability record; the manufacturer part is the reference "
            "the record would be written against" % reference
        )
    return {
        "lot_reference": reference,
        "source": source,
        "contact_count": count,
        "interchangeability_record": record,
    }


def validate_contact_lots(lots):
    """Read every contact lot, refusing an empty or repeated set."""
    if not isinstance(lots, (list, tuple)):
        raise ValueError("contact lots must be a sequence of lot records")
    if not lots:
        raise ValueError("no contact lot is declared for the harness")
    checked = []
    seen = set()
    for entry in lots:
        record = validate_contact_lot(entry)
        if record["lot_reference"] in seen:
            raise ValueError(
                "contact lot %r is declared twice" % record["lot_reference"]
            )
        seen.add(record["lot_reference"])
        checked.append(record)
    return tuple(checked)


def sourced_contact_count(lots):
    """Contacts the harness actually has in hand."""
    return sum(record["contact_count"] for record in validate_contact_lots(lots))


def unidentified_source_lots(lots):
    """Lots nobody can name a source for."""
    return tuple(
        record["lot_reference"]
        for record in validate_contact_lots(lots)
        if record["source"] == UNIDENTIFIED_SOURCE
    )


def unsupported_alternative_lots(lots):
    """Alternative-source lots with no interchangeability record behind them."""
    return tuple(
        record["lot_reference"]
        for record in validate_contact_lots(lots)
        if record["source"] == INTERCHANGEABLE_ALTERNATIVE_SOURCE
        and not record["interchangeability_record"]
    )


def manufacturer_sourced_share(lots):
    """Share of the contacts that came from the connector manufacturer."""
    checked = validate_contact_lots(lots)
    total = sum(record["contact_count"] for record in checked)
    manufacturer = sum(
        record["contact_count"]
        for record in checked
        if record["source"] == CONNECTOR_MANUFACTURER_SOURCE
    )
    return manufacturer / total


def sourcing_credit(lots, policy=DEFAULT_SELECTION_POLICY):
    """Credited sourcing standing over every contact in hand."""
    validate_selection_policy(policy)
    checked = validate_contact_lots(lots)
    credit = float(policy["alternative_source_credit"])
    total = 0
    earned = 0.0
    for record in checked:
        total += record["contact_count"]
        if record["source"] == CONNECTOR_MANUFACTURER_SOURCE:
            earned += record["contact_count"]
        elif (
            record["source"] == INTERCHANGEABLE_ALTERNATIVE_SOURCE
            and record["interchangeability_record"]
        ):
            earned += record["contact_count"] * credit
    return earned / total


def validate_evidence_record(entry):
    """Read one declared selection evidence item."""
    if not isinstance(entry, dict):
        raise ValueError("evidence entry must be a mapping, got %r" % (entry,))
    subject = _require_label("subject", entry.get("subject"))
    if subject not in REQUIRED_SELECTION_EVIDENCE:
        raise ValueError(
            "unrecognised evidence subject %r; the subject names are fixed"
            % (subject,)
        )
    declared = _require_flag(
        "held_as_supplier_declaration on %s" % subject,
        entry.get("held_as_supplier_declaration", False),
    )
    record = _require_label(
        "record_reference on %s" % subject, entry.get("record_reference", "")
    )
    supplier = _require_label(
        "supplier_reference on %s" % subject, entry.get("supplier_reference", "")
    )
    if declared and record:
        raise ValueError(
            "%s is declared both as a project record and as a supplier "
            "declaration; it is one or the other" % subject
        )
    return {
        "subject": subject,
        "held_as_supplier_declaration": declared,
        "record_reference": record,
        "supplier_reference": supplier,
    }


def validate_evidence(records):
    """Read every declared evidence item, refusing an empty or repeated set."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("evidence must be a sequence of evidence records")
    if not records:
        raise ValueError("no selection evidence is declared")
    checked = []
    seen = set()
    for entry in records:
        item = validate_evidence_record(entry)
        if item["subject"] in seen:
            raise ValueError("evidence subject %r is declared twice" % item["subject"])
        seen.add(item["subject"])
        checked.append(item)
    return tuple(checked)


def evidence_disposition(records, policy=DEFAULT_SELECTION_POLICY):
    """How each required evidence subject is held, with its credit."""
    validate_selection_policy(policy)
    checked = validate_evidence(records)
    credit = float(policy["supplier_declaration_credit"])
    declared = {item["subject"]: item for item in checked}
    disposition = {}
    for subject in REQUIRED_SELECTION_EVIDENCE:
        item = declared.get(subject)
        if item is None:
            disposition[subject] = {"state": ABSENT, "credit": 0.0}
            continue
        if item["held_as_supplier_declaration"]:
            if item["supplier_reference"]:
                disposition[subject] = {
                    "state": HELD_AS_A_SUPPLIER_DECLARATION,
                    "credit": credit,
                }
            else:
                disposition[subject] = {
                    "state": DECLARED_WITHOUT_A_RECORD,
                    "credit": 0.0,
                }
            continue
        if item["record_reference"]:
            disposition[subject] = {"state": HELD_AS_A_PROJECT_RECORD, "credit": 1.0}
        else:
            disposition[subject] = {"state": DECLARED_WITHOUT_A_RECORD, "credit": 0.0}
    return disposition


def _evidence_in_state(records, states, policy):
    disposition = evidence_disposition(records, policy)
    return tuple(
        subject
        for subject in REQUIRED_SELECTION_EVIDENCE
        if disposition[subject]["state"] in states
    )


def held_evidence(records, policy=DEFAULT_SELECTION_POLICY):
    """Required subjects the selection actually holds."""
    return _evidence_in_state(records, HELD_STATES, policy)


def absent_evidence(records, policy=DEFAULT_SELECTION_POLICY):
    """Required subjects the selection does not declare at all."""
    return _evidence_in_state(records, (ABSENT,), policy)


def unrecorded_evidence(records, policy=DEFAULT_SELECTION_POLICY):
    """Subjects declared with neither a record nor a named supplier."""
    return _evidence_in_state(records, (DECLARED_WITHOUT_A_RECORD,), policy)


def declaration_evidence(records, policy=DEFAULT_SELECTION_POLICY):
    """Subjects carried on a supplier's own declaration."""
    return _evidence_in_state(records, (HELD_AS_A_SUPPLIER_DECLARATION,), policy)


def evidence_share(records, policy=DEFAULT_SELECTION_POLICY):
    """Share of the required subjects the selection holds."""
    return len(held_evidence(records, policy)) / len(REQUIRED_SELECTION_EVIDENCE)


def weighted_evidence(records, policy=DEFAULT_SELECTION_POLICY):
    """Credited evidence over the full required subject list."""
    disposition = evidence_disposition(records, policy)
    total = 0.0
    for subject in REQUIRED_SELECTION_EVIDENCE:
        total += disposition[subject]["credit"]
    return total / len(REQUIRED_SELECTION_EVIDENCE)


def headroom_advisories(case, policy=DEFAULT_SELECTION_POLICY):
    """Name admissible candidates sitting just above the current they must carry.

    These do not move the verdict -- a candidate over the demand is over the
    demand -- but a family with four per cent to spare and one with forty per
    cent carry the same word, and nobody recovers the difference later from
    the word alone.
    """
    validate_selection_policy(policy)
    demand = validate_circuit_demand(case)
    band = 1.0 + float(policy["marginal_headroom_band"])
    advisories = []
    for record in admissible_candidates(case, policy):
        headroom = current_headroom(record, demand, policy)
        if _at_most(headroom, band):
            advisories.append(
                "%s clears the worst circuit by a factor of %.4g, inside the "
                "marginal band; it carries the harness today and is the family a "
                "late current increase would take out first"
                % (record["reference"], headroom)
            )
    return tuple(advisories)


def assess_connector_selection(case, policy=DEFAULT_SELECTION_POLICY):
    """Full clause 6.6.6 selection and sourcing decision for one harness."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_selection_policy(policy)

    findings = []
    advisories = []
    result = {
        "harness_reference": None,
        "selected_connector": None,
        "selected_family": None,
        "allowed_contact_current_a": None,
        "current_headroom": None,
        "spare_position_share": None,
        "rejected_candidates": (),
        "sourced_contact_count": None,
        "manufacturer_sourced_share": None,
        "sourcing_credit": None,
        "unidentified_source_lots": (),
        "unsupported_alternative_lots": (),
        "evidence_share": None,
        "weighted_evidence": None,
        "absent_evidence": (),
        "unrecorded_evidence": (),
        "declaration_evidence": (),
        "findings": findings,
        "advisories": advisories,
    }

    demand = validate_circuit_demand(case)
    result["harness_reference"] = demand["harness_reference"]
    if not demand["harness_reference"]:
        findings.append(
            "the harness carries no reference, so no connector decision taken "
            "here can be traced to the wiring it was taken for"
        )
        result["verdict"] = SELECTION_NOT_DECLARED
        return result

    candidates = case.get("candidates")
    if candidates is None:
        findings.append(
            "no candidate connector family is offered, so there is no selection "
            "to review"
        )
        result["verdict"] = SELECTION_NOT_DECLARED
        return result

    checked = validate_candidates(candidates)
    rejected = []
    for record in checked:
        reasons = candidate_findings(record, demand, policy)
        if reasons:
            rejected.append(record["reference"])
    result["rejected_candidates"] = tuple(rejected)
    advisories.extend(headroom_advisories(case, policy))

    chosen = selected_candidate(case, policy)
    if chosen is None:
        for record in checked:
            for reason in candidate_findings(record, demand, policy):
                findings.append(reason)
        result["verdict"] = NO_ADMISSIBLE_CANDIDATE
        return result

    result["selected_connector"] = chosen["reference"]
    result["selected_family"] = chosen["family"]
    result["allowed_contact_current_a"] = allowed_contact_current_a(
        chosen, demand, policy
    )
    result["current_headroom"] = current_headroom(chosen, demand, policy)
    result["spare_position_share"] = spare_position_share(chosen, demand)

    lots = case.get("contact_lots")
    if lots is None:
        findings.append(
            "no contact lot is declared, so nothing states where the parts going "
            "into the chosen insert came from"
        )
        result["verdict"] = CONTACT_SOURCING_NOT_ESTABLISHED
        return result

    sourced = validate_contact_lots(lots)
    unidentified = unidentified_source_lots(sourced)
    unsupported = unsupported_alternative_lots(sourced)
    result["unidentified_source_lots"] = unidentified
    result["unsupported_alternative_lots"] = unsupported
    result["sourced_contact_count"] = sourced_contact_count(sourced)
    result["manufacturer_sourced_share"] = manufacturer_sourced_share(sourced)
    result["sourcing_credit"] = sourcing_credit(sourced, policy)

    if unidentified or unsupported:
        for reference in unidentified:
            findings.append(
                "lot %s names no source, so a contact from it cannot be traced to "
                "a part anybody can reorder or compare" % reference
            )
        for reference in unsupported:
            findings.append(
                "lot %s comes from an alternative source with no "
                "interchangeability record behind it, so nothing shows it fits "
                "the chosen insert" % reference
            )
        result["verdict"] = CONTACT_SOURCING_NOT_ESTABLISHED
        return result

    if result["sourced_contact_count"] < demand["circuit_count"]:
        findings.append(
            "the declared lots hold %d contacts against %d circuits to place, so "
            "the harness cannot be built from what is in hand"
            % (result["sourced_contact_count"], demand["circuit_count"])
        )
        result["verdict"] = CONTACT_SUPPLY_SHORT
        return result

    share_short = not _at_least(
        result["manufacturer_sourced_share"],
        float(policy["min_manufacturer_sourced_share"]),
    )
    credit_short = not _at_least(
        result["sourcing_credit"], float(policy["min_sourcing_credit"])
    )
    if share_short or credit_short:
        findings.append(
            "the harness draws %.4g of its contacts from the connector "
            "manufacturer against %.4g, at a credited %.4g against %.4g"
            % (
                result["manufacturer_sourced_share"],
                float(policy["min_manufacturer_sourced_share"]),
                result["sourcing_credit"],
                float(policy["min_sourcing_credit"]),
            )
        )
        result["verdict"] = CONTACT_SOURCING_CREDIT_SHORT
        return result

    records = case.get("evidence")
    if records is None:
        findings.append(
            "no selection evidence is declared, so neither the specification the "
            "family was picked against nor the tooling that terminates it is shown"
        )
        result["verdict"] = SELECTION_EVIDENCE_SHORT
        return result

    evidence = validate_evidence(records)
    result["evidence_share"] = evidence_share(evidence, policy)
    result["weighted_evidence"] = weighted_evidence(evidence, policy)
    result["absent_evidence"] = absent_evidence(evidence, policy)
    result["unrecorded_evidence"] = unrecorded_evidence(evidence, policy)
    result["declaration_evidence"] = declaration_evidence(evidence, policy)

    for subject in result["absent_evidence"]:
        findings.append("the selection does not declare %s at all" % subject)
    for subject in result["unrecorded_evidence"]:
        findings.append(
            "%s is declared with neither a record reference nor a named supplier "
            "behind it" % subject
        )

    evidence_short = not _at_least(
        result["evidence_share"], float(policy["min_evidence_share"])
    )
    weighted_short = not _at_least(
        result["weighted_evidence"], float(policy["min_weighted_evidence"])
    )
    if evidence_short or weighted_short:
        findings.append(
            "the selection holds %.4g of the required subjects against %.4g, at a "
            "credited %.4g against %.4g"
            % (
                result["evidence_share"],
                float(policy["min_evidence_share"]),
                result["weighted_evidence"],
                float(policy["min_weighted_evidence"]),
            )
        )
        result["verdict"] = SELECTION_EVIDENCE_SHORT
        return result

    result["verdict"] = SELECTION_MEETS_CLASS_THREE_SCOPE
    return result
