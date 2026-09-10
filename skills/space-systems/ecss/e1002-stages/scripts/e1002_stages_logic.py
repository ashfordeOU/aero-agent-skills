#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.4.1 verification stages (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): a
verification programme runs through a fixed sequence of stages --
qualification, acceptance, pre-launch, in-orbit (including
commissioning), post-landing -- each with a distinct objective and each
applicable only to products with the matching life profile (whether the
product is launched, whether it is recovered). This module implements
stage ordering, per-product applicability, and stage-plan/schedule
checks. It does not select verification methods or levels (see the
sibling e10-req-verif-methods leaf) and does not run the qualification
or acceptance stages themselves (see the sibling e1002-qualification and
e1002-acceptance leaves).
"""

STAGES = ("qualification", "acceptance", "pre_launch", "in_orbit", "post_landing")

STAGE_OBJECTIVES = {
    "qualification": (
        "Demonstrate that the design, with adequate margin, meets its "
        "requirements before any article is accepted for delivery."
    ),
    "acceptance": (
        "Demonstrate that the specific deliverable article is free of "
        "manufacturing and workmanship defects and complies with its "
        "requirements, without consuming the design margin qualified above."
    ),
    "pre_launch": (
        "Confirm the integrated flight configuration is still compliant "
        "after transport, storage, and launch-site processing, up to the "
        "point of launch."
    ),
    "in_orbit": (
        "Confirm the system performs as required in its operational "
        "environment, including commissioning of functions before routine "
        "operations begin."
    ),
    "post_landing": (
        "Confirm the condition and performance of recovered or returned "
        "hardware after landing."
    ),
}

_STAGE_INDEX = {stage: index for index, stage in enumerate(STAGES)}


def stage_objective(stage):
    """Objective text for one stage. Raises ValueError for an unknown stage."""
    if stage not in STAGE_OBJECTIVES:
        raise ValueError("unknown verification stage: %r" % (stage,))
    return STAGE_OBJECTIVES[stage]


def determine_applicable_stages(launched, recovered):
    """Ordered subset of STAGES applicable to a product with the given life
    profile. qualification and acceptance always apply; pre_launch and
    in_orbit apply only if the product is launched; post_landing applies
    only if the product is recovered. Raises ValueError if recovered is
    True while launched is False (a product cannot be recovered without
    having been launched)."""
    if recovered and not launched:
        raise ValueError("a product cannot be recovered without being launched")
    applicable = ["qualification", "acceptance"]
    if launched:
        applicable.append("pre_launch")
        applicable.append("in_orbit")
    if recovered:
        applicable.append("post_landing")
    return applicable


def build_stage_plan(product):
    """Ordered list of {stage, objective} dicts for the stages applicable to
    a product dict. Required keys: id, launched, recovered. Raises
    ValueError if 'id' is missing."""
    if "id" not in product:
        raise ValueError("product is missing an id")
    stages = determine_applicable_stages(product["launched"], product["recovered"])
    return [{"stage": stage, "objective": stage_objective(stage)} for stage in stages]


def check_stage_order(stage_sequence):
    """Stage names in stage_sequence that appear out of the canonical STAGES
    order relative to the stage immediately before them, in
    stage_sequence order. An empty result means the sequence is
    monotonically non-decreasing in canonical order (repeats of the same
    stage are allowed). Raises ValueError for an unknown stage name."""
    violations = []
    previous_index = -1
    for stage in stage_sequence:
        if stage not in _STAGE_INDEX:
            raise ValueError("unknown verification stage: %r" % (stage,))
        index = _STAGE_INDEX[stage]
        if index < previous_index:
            violations.append(stage)
        else:
            previous_index = index
    return violations


def missing_stages(applicable_stages, completed_stages):
    """Stages present in applicable_stages but absent from completed_stages,
    in applicable_stages order -- the check that every stage a product's
    life profile calls for has actually been planned or executed."""
    completed = set(completed_stages)
    return [stage for stage in applicable_stages if stage not in completed]
