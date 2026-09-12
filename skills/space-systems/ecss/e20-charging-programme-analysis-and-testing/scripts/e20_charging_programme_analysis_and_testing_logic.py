#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.4.2 charging protection programme analysis
and test planning (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires a spacecraft charging
protection programme to keep a planned set of analysis activities and a
planned set of test activities, sized to the charging environment the
item actually sees, and requires the planned test conditions to remain
consistent with what the analysis predicts. This module implements the
checkable part of that clause: categorization of a programme activity
as an analysis task or a test task, derivation of the mandatory task
set from the charging regime, detection of a required task that is
absent or left unplanned, the steady-state electric field a trapped
electron flux drives into a dielectric against its breakdown strength,
the charge bleed-off time constant of a surface against the permitted
limit, the differential potential between a surface and structure
against a discharge-onset threshold, and an envelope check of every
planned test severity parameter against the analysis worst case. It
does not design a grounding scheme, does not model a plasma sheath,
and does not write the test procedure.
"""

import math

VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12

ANALYSIS_TASK_KINDS = frozenset(
    {
        "absolute_potential_analysis",
        "differential_potential_analysis",
        "deep_dielectric_field_analysis",
        "discharge_energy_analysis",
        "bleed_off_path_analysis",
    }
)
TEST_TASK_KINDS = frozenset(
    {
        "electron_beam_surface_charging_test",
        "discharge_susceptibility_test",
        "bleed_off_resistance_measurement",
        "dielectric_breakdown_screening",
        "harness_injection_transient_test",
    }
)

CHARGING_REGIME_TASKS = {
    "geo_surface_charging": frozenset(
        {
            "absolute_potential_analysis",
            "differential_potential_analysis",
            "bleed_off_path_analysis",
            "electron_beam_surface_charging_test",
            "discharge_susceptibility_test",
        }
    ),
    "leo_auroral_charging": frozenset(
        {
            "absolute_potential_analysis",
            "bleed_off_path_analysis",
            "electron_beam_surface_charging_test",
        }
    ),
    "internal_dielectric_charging": frozenset(
        {
            "deep_dielectric_field_analysis",
            "discharge_energy_analysis",
            "dielectric_breakdown_screening",
            "harness_injection_transient_test",
        }
    ),
    "solar_array_triple_junction": frozenset(
        {
            "differential_potential_analysis",
            "discharge_energy_analysis",
            "discharge_susceptibility_test",
            "bleed_off_resistance_measurement",
        }
    ),
}

PLANNED_STATUSES = frozenset({"planned", "in_work", "complete"})
OPEN_STATUSES = frozenset({"not_planned"})

DEFAULT_FIELD_SAFETY_FACTOR = 2.0
ENVELOPE_REL_TOL = 1e-9
ENVELOPE_ABS_TOL = 1e-12


def categorize_charging_task(task_kind):
    """Programme family for an activity: "analysis" for a predictive
    charging task, "test" for a hardware demonstration. Raises
    ValueError for a kind that is not a clause 6.3.4.2 programme
    activity."""
    if task_kind in ANALYSIS_TASK_KINDS:
        return "analysis"
    if task_kind in TEST_TASK_KINDS:
        return "test"
    raise ValueError(
        "unrecognized charging programme task %r under "
        "E-ST-20C clause 6.3.4.2" % (task_kind,)
    )


def required_programme_tasks(charging_regime):
    """Mandatory task set for a charging regime. Every regime pulls at
    least one analysis task and one test task, so a programme can never
    satisfy the clause with prediction alone. Raises ValueError for an
    unrecognized regime."""
    try:
        return CHARGING_REGIME_TASKS[charging_regime]
    except KeyError:
        raise ValueError(
            "unrecognized charging regime %r under "
            "E-ST-20C clause 6.3.4.2" % (charging_regime,)
        )


def missing_programme_tasks(planned_tasks, charging_regime):
    """Sorted list of mandatory tasks the programme does not carry.

    planned_tasks: mapping of task kind to status. A required task is
    missing when it is absent, carries a status of None, or sits at
    "not_planned". Raises ValueError for a task kind that is not a
    programme activity, or for a status outside the recognized set."""
    required = required_programme_tasks(charging_regime)
    for task_kind, status in planned_tasks.items():
        categorize_charging_task(task_kind)
        if status is None:
            continue
        if status not in PLANNED_STATUSES and status not in OPEN_STATUSES:
            raise ValueError(
                "unrecognized programme status %r for task %r"
                % (status, task_kind)
            )
    missing = []
    for task_kind in required:
        status = planned_tasks.get(task_kind)
        if status is None or status in OPEN_STATUSES:
            missing.append(task_kind)
    return sorted(missing)


def planning_findings(item_id, planned_tasks, charging_regime):
    """Findings (empty when the programme is complete) for every
    mandatory task the item does not plan, each tagged with the family
    the task belongs to."""
    return [
        {
            "issue": "charging_programme_task_not_planned",
            "item": item_id,
            "task": task_kind,
            "family": categorize_charging_task(task_kind),
            "regime": charging_regime,
        }
        for task_kind in missing_programme_tasks(planned_tasks, charging_regime)
    ]


def dielectric_steady_state_field_v_per_m(
    current_density_a_per_m2, bulk_resistivity_ohm_m
):
    """Steady-state electric field inside a dielectric driven by a
    penetrating electron flux: current density times bulk resistivity.
    Raises ValueError for a negative current density or a non-positive
    resistivity (a conductor has no internal charging field to
    compute)."""
    if current_density_a_per_m2 < 0:
        raise ValueError("current_density_a_per_m2 must be >= 0")
    if bulk_resistivity_ohm_m <= 0:
        raise ValueError("bulk_resistivity_ohm_m must be > 0")
    return current_density_a_per_m2 * bulk_resistivity_ohm_m


def dielectric_field_findings(
    item_id,
    field_v_per_m,
    breakdown_strength_v_per_m,
    safety_factor=DEFAULT_FIELD_SAFETY_FACTOR,
):
    """Findings (empty when the dielectric holds off) for the internal
    field against the derated breakdown strength. The allowable is the
    breakdown strength divided by the safety factor; a field equal to
    that allowable within representation error is compliant. Raises
    ValueError for a negative field, a non-positive breakdown strength
    or a safety factor below one."""
    if field_v_per_m < 0:
        raise ValueError("field_v_per_m must be >= 0")
    if breakdown_strength_v_per_m <= 0:
        raise ValueError("breakdown_strength_v_per_m must be > 0")
    if safety_factor < 1.0:
        raise ValueError("safety_factor must be >= 1.0")
    allowable = breakdown_strength_v_per_m / safety_factor
    if field_v_per_m > allowable and not math.isclose(
        field_v_per_m, allowable, rel_tol=ENVELOPE_REL_TOL,
        abs_tol=ENVELOPE_ABS_TOL,
    ):
        return [
            {
                "issue": "internal_dielectric_field_exceeds_allowable",
                "item": item_id,
                "field_v_per_m": field_v_per_m,
                "allowable_v_per_m": allowable,
            }
        ]
    return []


def bleed_off_time_constant_s(relative_permittivity, bulk_resistivity_ohm_m):
    """Charge bleed-off time constant of a dielectric: vacuum
    permittivity times relative permittivity times bulk resistivity.
    Raises ValueError for a relative permittivity below one or a
    non-positive resistivity."""
    if relative_permittivity < 1.0:
        raise ValueError("relative_permittivity must be >= 1.0")
    if bulk_resistivity_ohm_m <= 0:
        raise ValueError("bulk_resistivity_ohm_m must be > 0")
    return (
        VACUUM_PERMITTIVITY_F_PER_M
        * relative_permittivity
        * bulk_resistivity_ohm_m
    )


def bleed_off_findings(item_id, time_constant_s, maximum_allowed_s):
    """Findings (empty when charge drains fast enough) for the bleed-off
    time constant against the limit the protection programme sets. A
    time constant equal to the limit within representation error is
    compliant. Raises ValueError for a negative time constant or a
    non-positive limit."""
    if time_constant_s < 0:
        raise ValueError("time_constant_s must be >= 0")
    if maximum_allowed_s <= 0:
        raise ValueError("maximum_allowed_s must be > 0")
    if time_constant_s > maximum_allowed_s and not math.isclose(
        time_constant_s, maximum_allowed_s, rel_tol=ENVELOPE_REL_TOL,
        abs_tol=ENVELOPE_ABS_TOL,
    ):
        return [
            {
                "issue": "bleed_off_time_constant_too_long",
                "item": item_id,
                "time_constant_s": time_constant_s,
                "maximum_allowed_s": maximum_allowed_s,
            }
        ]
    return []


def differential_potential_v(surface_potential_v, structure_potential_v):
    """Magnitude of the potential difference between a surface and the
    structure it sits on. Charging potentials are normally negative;
    only the magnitude drives a discharge, so the sign is dropped.
    Raises ValueError for a value that is not finite."""
    for name, value in (
        ("surface_potential_v", surface_potential_v),
        ("structure_potential_v", structure_potential_v),
    ):
        if not math.isfinite(value):
            raise ValueError("%s must be a finite value" % (name,))
    return abs(surface_potential_v - structure_potential_v)


def differential_potential_findings(
    item_id, differential_v, onset_threshold_v
):
    """Findings (empty when below onset) for the differential potential
    against the discharge-onset threshold for the surface pair. A
    differential equal to the threshold within representation error is
    treated as compliant. Raises ValueError for a negative differential
    or a non-positive threshold."""
    if differential_v < 0:
        raise ValueError("differential_v must be >= 0")
    if onset_threshold_v <= 0:
        raise ValueError("onset_threshold_v must be > 0")
    if differential_v > onset_threshold_v and not math.isclose(
        differential_v, onset_threshold_v, rel_tol=ENVELOPE_REL_TOL,
        abs_tol=ENVELOPE_ABS_TOL,
    ):
        return [
            {
                "issue": "differential_potential_above_discharge_onset",
                "item": item_id,
                "differential_v": differential_v,
                "onset_threshold_v": onset_threshold_v,
            }
        ]
    return []


def test_envelope_findings(item_id, analysis_case, test_case):
    """Findings (empty when the test bounds the prediction) for every
    severity parameter the analysis predicts. Each parameter planned for
    test must be at least as severe as the analysis worst case; a
    parameter the test plan does not carry at all is reported
    separately. Equality within representation error passes. Raises
    ValueError for an empty analysis case or a negative severity."""
    if not analysis_case:
        raise ValueError("analysis_case must carry at least one parameter")
    findings = []
    for parameter in sorted(analysis_case):
        predicted = analysis_case[parameter]
        if predicted < 0:
            raise ValueError(
                "analysis severity %r must be >= 0" % (parameter,)
            )
        if parameter not in test_case or test_case[parameter] is None:
            findings.append(
                {
                    "issue": "test_parameter_not_planned",
                    "item": item_id,
                    "parameter": parameter,
                    "predicted": predicted,
                }
            )
            continue
        planned = test_case[parameter]
        if planned < 0:
            raise ValueError("test severity %r must be >= 0" % (parameter,))
        if planned < predicted and not math.isclose(
            planned, predicted, rel_tol=ENVELOPE_REL_TOL,
            abs_tol=ENVELOPE_ABS_TOL,
        ):
            findings.append(
                {
                    "issue": "test_severity_below_analysis_prediction",
                    "item": item_id,
                    "parameter": parameter,
                    "predicted": predicted,
                    "planned": planned,
                }
            )
    return findings


def programme_review(item):
    """Full clause 6.3.4.2 review for one charging-protection item.

    item: {"item_id": str, "charging_regime": str, "planned_tasks":
    {task: status}, "electron_current_density_a_per_m2": float,
    "bulk_resistivity_ohm_m": float, "breakdown_strength_v_per_m":
    float, "relative_permittivity": float, "maximum_bleed_off_s":
    float, "surface_potential_v": float, "structure_potential_v":
    float, "discharge_onset_v": float, "analysis_case": {param: value},
    "test_case": {param: value}, "field_safety_factor": float
    (optional)}.

    Returns {"planning": [...], "dielectric": [...], "bleed_off":
    [...], "differential": [...], "test_envelope": [...]}. Raises
    ValueError through the helpers for an unrecognized regime, task or
    status, or for an invalid physical input. Does not mutate item."""
    item_id = item["item_id"]
    field_v_per_m = dielectric_steady_state_field_v_per_m(
        item["electron_current_density_a_per_m2"],
        item["bulk_resistivity_ohm_m"],
    )
    time_constant_s = bleed_off_time_constant_s(
        item["relative_permittivity"], item["bulk_resistivity_ohm_m"]
    )
    differential_v = differential_potential_v(
        item["surface_potential_v"], item["structure_potential_v"]
    )
    return {
        "planning": planning_findings(
            item_id, item.get("planned_tasks", {}), item["charging_regime"]
        ),
        "dielectric": dielectric_field_findings(
            item_id,
            field_v_per_m,
            item["breakdown_strength_v_per_m"],
            item.get("field_safety_factor", DEFAULT_FIELD_SAFETY_FACTOR),
        ),
        "bleed_off": bleed_off_findings(
            item_id, time_constant_s, item["maximum_bleed_off_s"]
        ),
        "differential": differential_potential_findings(
            item_id, differential_v, item["discharge_onset_v"]
        ),
        "test_envelope": test_envelope_findings(
            item_id, item["analysis_case"], item.get("test_case", {})
        ),
    }


def is_programme_compliant(review):
    """True when every finding list in a programme_review result is
    empty -- the charging protection programme plans the analysis and
    test work the regime demands, and the hardware holds off."""
    return all(len(findings) == 0 for findings in review.values())
