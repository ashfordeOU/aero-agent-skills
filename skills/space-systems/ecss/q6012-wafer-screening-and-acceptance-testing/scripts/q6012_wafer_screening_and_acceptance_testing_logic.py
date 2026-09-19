"""Wafer level screening and acceptance testing, run as a flow before dicing.

Anchor: ECSS-Q-ST-60-12C clause 10.2 -- the stress and measurement activities
applied to a microwave wafer, arranged as a flow that finishes before the
wafer is diced. Paraphrased into an implementable flow-and-acceptance
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared flow: every activity recognised, none of them an
   activity that can only be performed on separated dies, and no activity
   declared twice.
2. Check the bracketing rule: a stress activity is only interpretable when a
   parametric measurement sits before it and another sits after it, because
   the stress is judged on the change between the two.
3. Compute the relative drift of every monitored parameter at every site
   between the pre-stress and post-stress readings.
4. Group the sites as passing or failing against the per-parameter drift
   limits, absorbing the boundary case with a named tolerance.
5. Compare the failing fraction with the percentage defective allowed and
   return an accepted, rejected or flow-invalid verdict with findings.
"""

import math

__all__ = [
    "DRIFT_TOLERANCE",
    "PRE_DICING_ACTIVITIES",
    "POST_DICING_ONLY_ACTIVITIES",
    "STRESS_ACTIVITIES",
    "MEASUREMENT_ACTIVITIES",
    "normalise_activity",
    "validate_flow",
    "stress_bracketing",
    "parameter_drift",
    "within_drift_limit",
    "site_verdict",
    "grade_sites",
    "failing_fraction",
    "assess_wafer_screening",
]

# A drift landing exactly on its limit is a representation question, not an
# engineering one. Absorb it here rather than by relaxing the limit.
DRIFT_TOLERANCE = 1e-9

PRE_DICING_ACTIVITIES = (
    "wafer_visual_inspection",
    "initial_parametric_measurement",
    "process_control_monitor_measurement",
    "wafer_level_stress_burn_in",
    "high_temperature_storage",
    "final_parametric_measurement",
    "wafer_acceptance_review",
)

# These need separated dies, so a pre-dicing flow cannot contain them.
POST_DICING_ONLY_ACTIVITIES = (
    "die_visual_inspection",
    "die_shear_test",
    "wire_bond_pull_test",
    "die_serialisation",
    "package_seal_test",
)

STRESS_ACTIVITIES = frozenset(
    ("wafer_level_stress_burn_in", "high_temperature_storage")
)

MEASUREMENT_ACTIVITIES = frozenset(
    (
        "initial_parametric_measurement",
        "process_control_monitor_measurement",
        "final_parametric_measurement",
    )
)

_KNOWN = frozenset(PRE_DICING_ACTIVITIES) | frozenset(POST_DICING_ONLY_ACTIVITIES)


def normalise_activity(name):
    """Return the canonical spelling of a declared flow activity."""
    if not isinstance(name, str):
        raise ValueError("activity name must be a string, got %r" % (name,))
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    if not key:
        raise ValueError("activity name must not be blank")
    if key not in _KNOWN:
        raise ValueError("activity %r is not a recognised wafer flow activity" % (name,))
    return key


def validate_flow(activities):
    """Return the canonical flow plus the activities that do not belong in it."""
    if not isinstance(activities, (list, tuple)) or not activities:
        raise ValueError("activities must be a non-empty sequence")
    flow = []
    seen = set()
    for name in activities:
        key = normalise_activity(name)
        if key in seen:
            raise ValueError("activity '%s' is declared twice in the flow" % key)
        seen.add(key)
        flow.append(key)
    misplaced = tuple(key for key in flow if key in POST_DICING_ONLY_ACTIVITIES)
    return {"flow": tuple(flow), "misplaced_activities": misplaced}


def stress_bracketing(flow):
    """Return the stress activities with no measurement before and after them."""
    if not isinstance(flow, (list, tuple)):
        raise ValueError("flow must be a sequence of canonical activities")
    unbracketed = []
    for index, key in enumerate(flow):
        if key not in STRESS_ACTIVITIES:
            continue
        before = any(item in MEASUREMENT_ACTIVITIES for item in flow[:index])
        after = any(item in MEASUREMENT_ACTIVITIES for item in flow[index + 1:])
        if not (before and after):
            unbracketed.append(key)
    return tuple(unbracketed)


def parameter_drift(pre_value, post_value):
    """Return the relative drift of one monitored parameter across a stress."""
    for label, value in (("pre_value", pre_value), ("post_value", post_value)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    pre = float(pre_value)
    post = float(post_value)
    if pre == 0.0:
        raise ValueError("a relative drift needs a non-zero pre-stress reading")
    return (post - pre) / pre


def within_drift_limit(drift, limit):
    """Return whether a drift sits inside its symmetric limit."""
    if not isinstance(drift, (int, float)) or isinstance(drift, bool):
        raise ValueError("drift must be a real number")
    if not isinstance(limit, (int, float)) or isinstance(limit, bool):
        raise ValueError("limit must be a real number")
    if not math.isfinite(float(drift)) or not math.isfinite(float(limit)):
        raise ValueError("drift and limit must be finite")
    if float(limit) < 0.0:
        raise ValueError("a drift limit must not be negative, got %r" % (limit,))
    return abs(float(drift)) <= float(limit) + DRIFT_TOLERANCE


def site_verdict(site, limits):
    """Return the per-parameter drift record and the verdict for one site."""
    if not isinstance(site, dict):
        raise ValueError("site must be a mapping")
    for key in ("site_id", "pre", "post"):
        if key not in site:
            raise ValueError("site must carry '%s'" % key)
    if not isinstance(limits, dict) or not limits:
        raise ValueError("limits must be a non-empty mapping of parameter to limit")
    pre = site["pre"]
    post = site["post"]
    for label, block in (("pre", pre), ("post", post)):
        if not isinstance(block, dict):
            raise ValueError("site '%s' %s readings must be a mapping"
                             % (site["site_id"], label))
    drifts = {}
    breaches = []
    unmeasured = []
    for parameter, limit in sorted(limits.items()):
        if parameter not in pre or parameter not in post:
            unmeasured.append(parameter)
            continue
        drift = parameter_drift(pre[parameter], post[parameter])
        drifts[parameter] = drift
        if not within_drift_limit(drift, limit):
            breaches.append(parameter)
    passing = not breaches and not unmeasured
    return {
        "site_id": site["site_id"],
        "drifts": drifts,
        "breached_parameters": tuple(breaches),
        "unmeasured_parameters": tuple(unmeasured),
        "passing": passing,
    }


def grade_sites(sites, limits):
    """Return the per-site verdicts, grouped into passing and failing sites."""
    if not isinstance(sites, (list, tuple)) or not sites:
        raise ValueError("sites must be a non-empty sequence")
    verdicts = []
    seen = set()
    for site in sites:
        record = site_verdict(site, limits)
        if record["site_id"] in seen:
            raise ValueError("site '%s' is measured twice" % record["site_id"])
        seen.add(record["site_id"])
        verdicts.append(record)
    passing = tuple(r["site_id"] for r in verdicts if r["passing"])
    failing = tuple(r["site_id"] for r in verdicts if not r["passing"])
    return {"verdicts": verdicts, "passing_sites": passing, "failing_sites": failing}


def failing_fraction(failing, total):
    """Return the fraction of measured sites that failed."""
    for label, value in (("failing", failing), ("total", total)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer" % label)
        if value < 0:
            raise ValueError("%s must not be negative" % label)
    if total == 0:
        raise ValueError("a failing fraction needs at least one measured site")
    if failing > total:
        raise ValueError("failing sites cannot exceed the measured sites")
    return failing / total


def assess_wafer_screening(case):
    """Grade a pre-dicing wafer screening and acceptance flow.

    case keys: activities (sequence of flow activities), sites (sequence of
    {site_id, pre, post}), drift_limits (parameter -> symmetric limit),
    percent_defective_allowed (fraction of sites allowed to fail).
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("activities", "sites", "drift_limits", "percent_defective_allowed"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    pda = case["percent_defective_allowed"]
    if not isinstance(pda, (int, float)) or isinstance(pda, bool):
        raise ValueError("percent_defective_allowed must be a real number")
    pda = float(pda)
    if not math.isfinite(pda) or pda < 0.0 or pda > 1.0:
        raise ValueError("percent_defective_allowed must be a fraction between zero and one")

    flow = validate_flow(case["activities"])
    unbracketed = stress_bracketing(flow["flow"])
    grading = grade_sites(case["sites"], case["drift_limits"])
    total = len(grading["verdicts"])
    failing = len(grading["failing_sites"])
    fraction = failing_fraction(failing, total)
    within_pda = fraction <= pda + DRIFT_TOLERANCE

    findings = []
    for key in flow["misplaced_activities"]:
        findings.append(
            "activity '%s' needs separated dies and cannot sit in a pre-dicing flow"
            % key
        )
    for key in unbracketed:
        findings.append(
            "stress activity '%s' is not bracketed by a parametric measurement "
            "before and after it" % key
        )
    if not any(key in STRESS_ACTIVITIES for key in flow["flow"]):
        findings.append("the flow declares no wafer level stress activity")
    for record in grading["verdicts"]:
        for parameter in record["unmeasured_parameters"]:
            findings.append(
                "site '%s' has no reading pair for monitored parameter '%s'"
                % (record["site_id"], parameter)
            )
        for parameter in record["breached_parameters"]:
            findings.append(
                "site '%s' drifts past the limit on '%s' (%.6f)"
                % (record["site_id"], parameter, record["drifts"][parameter])
            )
    if not within_pda:
        findings.append(
            "failing site fraction %.6f exceeds the allowed %.6f" % (fraction, pda)
        )

    flow_invalid = bool(flow["misplaced_activities"]) or bool(unbracketed)
    if flow_invalid:
        verdict = "flow-invalid"
    elif within_pda:
        verdict = "accepted"
    else:
        verdict = "rejected"

    return {
        "flow": flow,
        "unbracketed_stress": unbracketed,
        "grading": grading,
        "measured_sites": total,
        "failing_site_count": failing,
        "failing_fraction": fraction,
        "percent_defective_allowed": pda,
        "within_percent_defective_allowed": within_pda,
        "findings": findings,
        "verdict": verdict,
    }
