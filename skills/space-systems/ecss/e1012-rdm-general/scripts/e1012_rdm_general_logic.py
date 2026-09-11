#!/usr/bin/env python3
"""ECSS-E-ST-10-12 §5.1.2/§5.2 radiation design margin — general case
(dose-effects, margin approach). Paraphrase, not verbatim copy.

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
radiation hardness assurance standard's margin approach for dose effects
defines the radiation design margin (RDM) as the ratio of the component's
lot-qualified failure dose to the design dose; the design dose is the
shielded mission total ionizing dose (TID) multiplied by an uncertainty
factor (1.0 in the general case, where the RDM requirement itself absorbs
all analysis uncertainties); and the minimum required RDM for the general
case is 2.0 — a component is compliant only when its measured failure dose
is at least that multiple of its design dose. This module implements design-
dose derivation, RDM computation, per-component compliance checking, and
multi-component assessment aggregation; it does not implement the radiation
environment model or the shielding analysis that produce the mission dose.
"""

DEFAULT_RDM_MIN = 2.0


def compute_design_dose(mission_dose_gy, uncertainty_factor=1.0):
    """Design dose for one component: mission_dose_gy × uncertainty_factor.

    In the general-case margin approach the uncertainty factor is 1.0 (the
    required RDM absorbs all uncertainties). A value > 1.0 may be applied
    when elevated analysis uncertainty has been separately justified.

    Raises ValueError for a non-positive mission dose or a factor < 1.0.
    """
    if mission_dose_gy <= 0:
        raise ValueError(
            "mission_dose_gy must be > 0, got %r" % (mission_dose_gy,)
        )
    if uncertainty_factor < 1.0:
        raise ValueError(
            "uncertainty_factor must be >= 1.0, got %r" % (uncertainty_factor,)
        )
    return mission_dose_gy * uncertainty_factor


def compute_rdm(qualified_failure_dose_gy, design_dose_gy):
    """RDM = qualified_failure_dose_gy / design_dose_gy.

    Both values must be strictly positive (a zero or negative failure dose or
    design dose is an invalid input, not a margin-of-zero result).

    Raises ValueError for a non-positive argument.
    """
    if qualified_failure_dose_gy <= 0:
        raise ValueError(
            "qualified_failure_dose_gy must be > 0, got %r"
            % (qualified_failure_dose_gy,)
        )
    if design_dose_gy <= 0:
        raise ValueError(
            "design_dose_gy must be > 0, got %r" % (design_dose_gy,)
        )
    return qualified_failure_dose_gy / design_dose_gy


def check_rdm_compliance(component_id, rdm, required_rdm_min):
    """Compliance result for one component's computed RDM.

    Returns a dict with keys:
      component        — the supplied component_id
      rdm              — the computed RDM value
      required_rdm_min — the minimum acceptable RDM
      compliant        — True when rdm >= required_rdm_min
      finding          — None if compliant; violation dict otherwise

    Raises ValueError for a non-positive rdm or required_rdm_min.
    """
    if rdm <= 0:
        raise ValueError("rdm must be > 0, got %r" % (rdm,))
    if required_rdm_min <= 0:
        raise ValueError(
            "required_rdm_min must be > 0, got %r" % (required_rdm_min,)
        )
    compliant = rdm >= required_rdm_min
    finding = (
        None
        if compliant
        else {
            "issue": "rdm_below_minimum",
            "component": component_id,
            "rdm": rdm,
            "required_rdm_min": required_rdm_min,
        }
    )
    return {
        "component": component_id,
        "rdm": rdm,
        "required_rdm_min": required_rdm_min,
        "compliant": compliant,
        "finding": finding,
    }


def assess_component(
    component_id,
    mission_dose_gy,
    qualified_failure_dose_gy,
    uncertainty_factor=1.0,
    required_rdm_min=DEFAULT_RDM_MIN,
):
    """Full RDM assessment for one component under the general case.

    Steps:
      1. Derive design_dose = mission_dose_gy × uncertainty_factor.
      2. Compute RDM = qualified_failure_dose_gy / design_dose.
      3. Check RDM >= required_rdm_min.

    Returns a dict with all intermediate values, the computed RDM, and the
    compliance result. Does not mutate any input. Raises ValueError for any
    invalid input.
    """
    design_dose = compute_design_dose(mission_dose_gy, uncertainty_factor)
    rdm = compute_rdm(qualified_failure_dose_gy, design_dose)
    compliance = check_rdm_compliance(component_id, rdm, required_rdm_min)
    return {
        "component": component_id,
        "mission_dose_gy": mission_dose_gy,
        "uncertainty_factor": uncertainty_factor,
        "design_dose_gy": design_dose,
        "qualified_failure_dose_gy": qualified_failure_dose_gy,
        "rdm": rdm,
        "required_rdm_min": required_rdm_min,
        "compliant": compliance["compliant"],
        "finding": compliance["finding"],
    }


def assess_all(components):
    """Assess a list of component specification dicts.

    Each dict must carry:
      component_id             — string identifier
      mission_dose_gy          — shielded mission TID in Gy(Si)
      qualified_failure_dose_gy — lot-tested failure dose in Gy(Si)
    Optional keys (defaults apply when absent):
      uncertainty_factor       — float >= 1.0 (default 1.0)
      required_rdm_min         — float > 0 (default DEFAULT_RDM_MIN)

    Returns a list of assessment dicts in the same order as the input.
    Does not mutate the input list or any of its dicts.
    """
    results = []
    for comp in components:
        result = assess_component(
            comp["component_id"],
            comp["mission_dose_gy"],
            comp["qualified_failure_dose_gy"],
            comp.get("uncertainty_factor", 1.0),
            comp.get("required_rdm_min", DEFAULT_RDM_MIN),
        )
        results.append(result)
    return results


def rdm_findings(assessment_results):
    """Non-compliant findings from an assess_all result list.

    Returns a list of finding dicts for every component that did not meet
    its required RDM. An empty list means all components pass.
    """
    return [r["finding"] for r in assessment_results if not r["compliant"]]
