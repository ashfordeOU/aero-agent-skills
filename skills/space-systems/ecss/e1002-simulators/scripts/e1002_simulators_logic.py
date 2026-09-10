#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.6.4 simulator qualification for
verification (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): a
simulator used to produce verification evidence must be qualified for
the role(s) it plays -- functional behaviour, real-time behaviour,
closed-loop (hardware-in-the-loop) operation -- consistent with the
general verification-tool classification of clause 5.2.6.1. This module
implements the capability-to-evidence mapping and the qualify /
credit / re-qualify decision; it does not cover ground support
equipment (see e1002-gse-tools), software analysis tools (see
e1002-sw-tools), or facility qualification (see e1002-facilities).
"""

CAPABILITIES = ("functional", "real_time", "closed_loop")

EVIDENCE_BY_CAPABILITY = {
    "functional": ("functional_correctness_validation",),
    "real_time": (
        "functional_correctness_validation",
        "timing_performance_validation",
    ),
    "closed_loop": (
        "functional_correctness_validation",
        "interface_representativeness_validation",
        "loop_stability_validation",
    ),
}

REQUALIFICATION_TRIGGERS = (
    "model_changed",
    "environment_interface_changed",
    "unit_under_test_interface_changed",
)


def classify_simulator(is_functional, is_real_time, is_closed_loop):
    """Tuple of capability names asserted for a simulator, in fixed
    CAPABILITIES order. Raises ValueError if none is asserted -- a
    simulator must serve at least one verification role."""
    flags = {
        "functional": is_functional,
        "real_time": is_real_time,
        "closed_loop": is_closed_loop,
    }
    capabilities = tuple(name for name in CAPABILITIES if flags[name])
    if not capabilities:
        raise ValueError("simulator must assert at least one capability")
    return capabilities


def required_evidence(capabilities):
    """Sorted tuple of evidence items required across the given
    capabilities (union, de-duplicated). Raises ValueError for an
    unknown capability."""
    items = set()
    for capability in capabilities:
        if capability not in EVIDENCE_BY_CAPABILITY:
            raise ValueError("unknown simulator capability: %r" % (capability,))
        items.update(EVIDENCE_BY_CAPABILITY[capability])
    return tuple(sorted(items))


def assess_qualification(simulator):
    """Qualification assessment for one simulator dict. Required keys:
    id, is_functional, is_real_time, is_closed_loop; optional key:
    evidence (iterable of evidence-item strings already obtained,
    defaults to none). Returns a new dict with capabilities, required
    evidence, missing evidence, and status ('qualified' if nothing is
    missing else 'not_qualified'). Does not mutate the input. Raises
    ValueError if 'id' is missing."""
    if "id" not in simulator:
        raise ValueError("simulator is missing an id")
    capabilities = classify_simulator(
        simulator["is_functional"],
        simulator["is_real_time"],
        simulator["is_closed_loop"],
    )
    required = required_evidence(capabilities)
    provided = set(simulator.get("evidence", ()))
    missing = tuple(item for item in required if item not in provided)
    status = "qualified" if not missing else "not_qualified"
    return {
        "id": simulator["id"],
        "capabilities": capabilities,
        "required_evidence": required,
        "missing_evidence": missing,
        "status": status,
    }


def build_qualification_register(simulators):
    """List of qualification assessments, one per simulator, in input
    order. Raises ValueError on a duplicate simulator id."""
    register = []
    seen_ids = set()
    for simulator in simulators:
        assessment = assess_qualification(simulator)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate simulator id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        register.append(assessment)
    return register


def can_credit_verification(assessment):
    """True if a simulator's qualification assessment allows crediting a
    verification activity that relied on it (status == 'qualified')."""
    return assessment["status"] == "qualified"


def needs_requalification(assessment, change_flags):
    """True if a simulator must be (re-)qualified before further
    verification credit can be taken. An already not_qualified
    simulator always needs qualification. A qualified simulator needs
    re-qualification only if change_flags marks at least one of
    'model_changed', 'environment_interface_changed', or
    'unit_under_test_interface_changed' as True."""
    if assessment["status"] != "qualified":
        return True
    return any(change_flags.get(trigger, False) for trigger in REQUALIFICATION_TRIGGERS)
