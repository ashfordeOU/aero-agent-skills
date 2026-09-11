"""
Dose-effects margin assessment logic for electronic components.
Implements the margin-factor procedure from ECSS-E-ST-10 §5.5.2 (paraphrased).
No verbatim standard text. Stdlib only.
"""

DEFAULT_RADIATION_DESIGN_MARGIN = 2.0


def apply_dose_margin(predicted_dose_krad, radiation_design_margin=DEFAULT_RADIATION_DESIGN_MARGIN):
    """Return the required component tolerance after applying the margin factor."""
    if predicted_dose_krad < 0:
        raise ValueError("predicted_dose_krad must be non-negative")
    if radiation_design_margin <= 0:
        raise ValueError("radiation_design_margin must be positive and non-zero")
    return predicted_dose_krad * radiation_design_margin


def check_dose_tolerance(predicted_dose_krad, component_tolerance_krad,
                         radiation_design_margin=DEFAULT_RADIATION_DESIGN_MARGIN):
    """
    Determine whether a component's dose tolerance satisfies the margin requirement.

    Returns a dict:
      required_tolerance_krad  — predicted dose × margin factor
      component_tolerance_krad — as supplied
      margin_met               — bool
      achieved_margin_ratio    — component_tolerance / predicted_dose
                                 (inf when predicted dose is zero)
    """
    if predicted_dose_krad < 0:
        raise ValueError("predicted_dose_krad must be non-negative")
    if component_tolerance_krad < 0:
        raise ValueError("component_tolerance_krad must be non-negative")
    if radiation_design_margin <= 0:
        raise ValueError("radiation_design_margin must be positive and non-zero")

    required = apply_dose_margin(predicted_dose_krad, radiation_design_margin)
    if predicted_dose_krad > 0:
        achieved = component_tolerance_krad / predicted_dose_krad
    else:
        achieved = float("inf")

    return {
        "required_tolerance_krad": required,
        "component_tolerance_krad": component_tolerance_krad,
        "margin_met": component_tolerance_krad >= required,
        "achieved_margin_ratio": achieved,
    }


def check_parametric_degradation(parameter_name, nominal_value, degraded_value,
                                  allowable_change_fraction):
    """
    Verify that a single parametric change (gain, leakage current, threshold
    voltage, etc.) stays within the specified allowable fraction of its nominal.

    allowable_change_fraction: e.g. 0.20 permits a 20 % change.

    Returns a dict:
      parameter_name           — as supplied
      nominal_value            — as supplied
      degraded_value           — as supplied
      change_fraction          — |degraded - nominal| / |nominal|
      allowable_change_fraction — as supplied
      within_limit             — bool
    """
    if allowable_change_fraction < 0:
        raise ValueError("allowable_change_fraction must be non-negative")
    if nominal_value == 0:
        raise ValueError(
            "nominal_value cannot be zero; fractional change is undefined"
        )

    change_fraction = abs(degraded_value - nominal_value) / abs(nominal_value)
    return {
        "parameter_name": parameter_name,
        "nominal_value": nominal_value,
        "degraded_value": degraded_value,
        "change_fraction": change_fraction,
        "allowable_change_fraction": allowable_change_fraction,
        "within_limit": change_fraction <= allowable_change_fraction,
    }


def check_functional_degradation(component_id, function_passes_at_dose,
                                  required_tolerance_krad):
    """
    Record whether the component passes its functional test at the
    margin-multiplied required dose.

    Returns a dict:
      component_id             — as supplied
      required_tolerance_krad  — as supplied
      functionally_passes      — bool
    """
    return {
        "component_id": component_id,
        "required_tolerance_krad": required_tolerance_krad,
        "functionally_passes": bool(function_passes_at_dose),
    }


def assess_component(component_id, predicted_dose_krad, component_tolerance_krad,
                     parametric_checks=None, functional_pass=True,
                     radiation_design_margin=DEFAULT_RADIATION_DESIGN_MARGIN):
    """
    Run the full dose-effects margin assessment for one component.

    parametric_checks: list of dicts already produced by
                       check_parametric_degradation (may be None or empty).
    functional_pass:   bool — component still meets its functional spec at the
                       required (margin-multiplied) dose.

    Returns a dict:
      component_id         — as supplied
      dose_check           — result of check_dose_tolerance
      parametric_findings  — list of parametric check dicts that failed
      functional_finding   — result of check_functional_degradation
      compliant            — True only when every check passes
      findings             — human-readable list of violation strings (empty = pass)
    """
    dose_check = check_dose_tolerance(
        predicted_dose_krad, component_tolerance_krad, radiation_design_margin
    )
    required_tolerance = dose_check["required_tolerance_krad"]
    findings = []

    if not dose_check["margin_met"]:
        findings.append(
            f"{component_id}: tolerance {component_tolerance_krad} krad < required "
            f"{required_tolerance:.2f} krad "
            f"(RDM {radiation_design_margin}x predicted {predicted_dose_krad} krad)"
        )

    failed_parametric = []
    for pc in (parametric_checks or []):
        if not pc["within_limit"]:
            failed_parametric.append(pc)
            findings.append(
                f"{component_id}: parametric '{pc['parameter_name']}' degraded "
                f"{pc['change_fraction'] * 100:.1f}% — limit "
                f"{pc['allowable_change_fraction'] * 100:.1f}%"
            )

    functional_finding = check_functional_degradation(
        component_id, functional_pass, required_tolerance
    )
    if not functional_pass:
        findings.append(
            f"{component_id}: fails functional test at {required_tolerance:.2f} krad"
        )

    compliant = dose_check["margin_met"] and not failed_parametric and functional_pass

    return {
        "component_id": component_id,
        "dose_check": dose_check,
        "parametric_findings": failed_parametric,
        "functional_finding": functional_finding,
        "compliant": compliant,
        "findings": findings,
    }
