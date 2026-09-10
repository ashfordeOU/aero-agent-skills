#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.6.2 ground support equipment (GSE)
qualification for verification tooling (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): GSE
used during verification (handling, transport, test stimulation,
checkout) is itself subject to qualification before it may interface
with flight hardware, consistent with the general tool-qualification
regime of clause 5.2.6.1. GSE is categorized as mechanical (MGSE --
handling, lifting, transport, alignment, protective equipment) or
electrical (EGSE -- stimulation, simulation, power, signal, checkout,
harnesses). This module implements the classification and required-
qualification-action logic for one piece of GSE and for a GSE
register; it does not replace the general tool category A/B/C/D
scheme (see the sibling e1002-tools-general leaf) or facility
qualification (see e1002-facilities).
"""

GSE_CLASSES = ("mgse", "egse")

MGSE_FUNCTIONS = (
    "handling",
    "lifting",
    "transport",
    "alignment_fixture",
    "protective_cover",
)

EGSE_FUNCTIONS = (
    "stimulation",
    "simulation",
    "power_supply",
    "signal_checkout",
    "harness",
)


def classify_gse(primary_function):
    """"mgse" or "egse" for a GSE item's primary_function. Raises
    ValueError for a function outside the known MGSE/EGSE vocabulary."""
    if primary_function in MGSE_FUNCTIONS:
        return "mgse"
    if primary_function in EGSE_FUNCTIONS:
        return "egse"
    raise ValueError("unknown GSE primary function: %r" % (primary_function,))


def required_qualification_actions(gse):
    """Sorted tuple of required qualification actions for one GSE item.
    Required keys: id, primary_function; optional keys:
    contacts_flight_item (default False), used_for_formal_verification_measurement
    (default False). Rules: any GSE that contacts/interfaces the flight
    item needs an interface control document; MGSE that contacts the
    flight item additionally needs a proof test before first use and
    periodic re-proof; EGSE that interfaces the flight item additionally
    needs an interface safety verification (no out-of-spec stimulus to
    the flight item); any GSE acting as the measurement or stimulus of
    record for a formal verification result needs calibration with
    traceability, regardless of class. Raises ValueError if 'id' is
    missing or primary_function is unknown."""
    if "id" not in gse:
        raise ValueError("gse item is missing an id")
    gse_class = classify_gse(gse["primary_function"])
    actions = set()
    if gse.get("contacts_flight_item", False):
        actions.add("interface_control_document")
        if gse_class == "mgse":
            actions.add("proof_test_before_first_use")
            actions.add("periodic_re_proof")
        else:
            actions.add("interface_safety_verification")
    if gse.get("used_for_formal_verification_measurement", False):
        actions.add("calibration_with_traceability")
    return tuple(sorted(actions))


def build_qualification_record(gse):
    """{"id", "class", "required_actions"} for one GSE item. Does not
    mutate the input. Raises ValueError via classify_gse /
    required_qualification_actions for missing id or unknown function."""
    return {
        "id": gse["id"],
        "class": classify_gse(gse["primary_function"]),
        "required_actions": required_qualification_actions(gse),
    }


def build_gse_register(gse_items):
    """One qualification record per GSE item, in input order. Raises
    ValueError on a duplicate GSE id."""
    register = []
    seen_ids = set()
    for gse in gse_items:
        record = build_qualification_record(gse)
        if record["id"] in seen_ids:
            raise ValueError("duplicate gse id: %r" % (record["id"],))
        seen_ids.add(record["id"])
        register.append(record)
    return register


def find_unqualified_gse(register, completed_actions_by_id):
    """GSE ids (register order) whose required_actions are not fully
    covered by completed_actions_by_id (dict id -> iterable of
    completed action strings). An id absent from
    completed_actions_by_id is treated as having no actions complete."""
    gaps = []
    for record in register:
        completed = set(completed_actions_by_id.get(record["id"], ()))
        if not set(record["required_actions"]).issubset(completed):
            gaps.append(record["id"])
    return gaps


def measurement_chain_gse_ids(register):
    """GSE ids (register order) that are the measurement or stimulus of
    record for a formal verification result -- the subset requiring
    calibration_with_traceability, which ties this leaf's output to the
    tightened tool-qualification tier of the sibling e1002-tools-general
    leaf."""
    return [
        record["id"]
        for record in register
        if "calibration_with_traceability" in record["required_actions"]
    ]


def reproof_due(reproof_status):
    """True if an MGSE item's periodic re-proof is due: it has been
    modified since its last proof, or its usage count since the last
    proof has reached/exceeded the allowed maximum. Required keys:
    modified_since_last_proof, uses_since_last_proof,
    max_uses_between_proofs."""
    if reproof_status["modified_since_last_proof"]:
        return True
    return reproof_status["uses_since_last_proof"] >= reproof_status["max_uses_between_proofs"]


def find_gse_due_for_reproof(register, reproof_status_by_id):
    """GSE ids (register order) that require periodic_re_proof and are
    currently due for it. An id requiring periodic_re_proof with no
    entry in reproof_status_by_id is treated as due (fail-safe: an
    untracked proof-test history cannot be presumed current)."""
    due = []
    for record in register:
        if "periodic_re_proof" not in record["required_actions"]:
            continue
        status = reproof_status_by_id.get(record["id"])
        if status is None or reproof_due(status):
            due.append(record["id"])
    return due
