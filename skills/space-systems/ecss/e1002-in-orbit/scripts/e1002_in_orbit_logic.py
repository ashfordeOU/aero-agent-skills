#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.4.5 in-orbit verification (paraphrase, not
copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
in-orbit verification stage confirms performance of a flight item that
cannot be fully confirmed on the ground -- typically because compliance
depends on the operational orbital environment (deployment, thermal or
vacuum operation in flight, RF link performance, microgravity
behaviour). Clause 5.2.4.5 ties this stage to the post-launch
commissioning activities that generate the evidence used to close it
out, and requires that an in-orbit anomaly affecting a previously closed
requirement reopen that requirement for re-verification until the
corrective action is itself verified. This module implements that
closure and re-verification logic; it does not plan the commissioning
campaign itself (owned by mission operations) or run the anomaly
investigation (owned by the anomaly/non-conformance process, see the
sibling e10-changes-nc leaf).
"""

STATUSES = ("not_applicable", "open", "verified", "failed",
            "reverification_required", "reverified")
EVIDENCE_RESULTS = ("pass", "fail", "not_run")


def requires_in_orbit_stage(requirement):
    """True when a requirement's compliance can only be confirmed under
    the actual operational orbital environment (clause 5.2.4.5 scope),
    i.e. it cannot be closed by an earlier ground stage regardless of
    that stage's outcome. Required key: onorbit_environment_dependent."""
    return bool(requirement["onorbit_environment_dependent"])


def evidence_for_requirement(requirement_id, commissioning_records):
    """Results (in record order) of the commissioning records whose
    requirement_ids list includes requirement_id."""
    return [
        record["result"]
        for record in commissioning_records
        if requirement_id in record["requirement_ids"]
    ]


def commissioning_outcome(requirement_id, commissioning_records):
    """Aggregate outcome of the commissioning evidence for one
    requirement: 'fail' if any covering record failed, else 'not_run' if
    any covering record has not run yet, else 'pass' if all covering
    records passed, else 'no_commissioning_evidence' if no record covers
    it. Raises ValueError for an unknown result value."""
    results = evidence_for_requirement(requirement_id, commissioning_records)
    for result in results:
        if result not in EVIDENCE_RESULTS:
            raise ValueError("unknown commissioning result: %r" % (result,))
    if not results:
        return "no_commissioning_evidence"
    if "fail" in results:
        return "fail"
    if "not_run" in results:
        return "not_run"
    return "pass"


_OUTCOME_TO_STATUS = {
    "pass": "verified",
    "fail": "failed",
    "not_run": "open",
    "no_commissioning_evidence": "open",
}


def close_in_orbit_verification(requirement, commissioning_records):
    """In-orbit verification status for one requirement: 'not_applicable'
    if the requirement does not require the in-orbit stage; otherwise
    the commissioning-outcome-derived status (verified / failed / open).
    Required key: id (plus the keys requires_in_orbit_stage needs).
    Raises ValueError if 'id' is missing."""
    if "id" not in requirement:
        raise ValueError("requirement is missing an id")
    if not requires_in_orbit_stage(requirement):
        return {"id": requirement["id"], "status": "not_applicable"}
    outcome = commissioning_outcome(requirement["id"], commissioning_records)
    return {"id": requirement["id"], "status": _OUTCOME_TO_STATUS[outcome]}


def build_in_orbit_matrix(requirements, commissioning_records):
    """In-orbit verification status for each requirement, in input
    order. Raises ValueError on a duplicate requirement id."""
    matrix = []
    seen_ids = set()
    for requirement in requirements:
        entry = close_in_orbit_verification(requirement, commissioning_records)
        if entry["id"] in seen_ids:
            raise ValueError("duplicate requirement id: %r" % (entry["id"],))
        seen_ids.add(entry["id"])
        matrix.append(entry)
    return matrix


def apply_anomaly_reverification(matrix, anomaly):
    """New matrix reflecting an in-orbit anomaly: entries whose id is in
    anomaly['affected_ids'] and are currently 'verified' move to
    'reverified' when anomaly['corrective_action_verified'] is True, or
    to 'reverification_required' otherwise; entries not currently
    verified, and entries not affected, are copied unchanged. Does not
    mutate the input matrix. Raises ValueError if an affected id is not
    present in the matrix."""
    matrix_ids = {entry["id"] for entry in matrix}
    for affected_id in anomaly["affected_ids"]:
        if affected_id not in matrix_ids:
            raise ValueError("anomaly affects unknown requirement id: %r" % (affected_id,))
    affected = set(anomaly["affected_ids"])
    new_status = "reverified" if anomaly["corrective_action_verified"] else "reverification_required"
    return [
        dict(entry, status=new_status)
        if entry["id"] in affected and entry["status"] == "verified"
        else dict(entry)
        for entry in matrix
    ]


def open_in_orbit_items(matrix):
    """Requirement ids in the matrix not yet closed (status one of open,
    failed, reverification_required), in matrix order -- the items that
    must be resolved before the in-orbit verification record, and by
    extension the commissioning result review, can be declared
    complete."""
    open_statuses = ("open", "failed", "reverification_required")
    return [entry["id"] for entry in matrix if entry["status"] in open_statuses]
