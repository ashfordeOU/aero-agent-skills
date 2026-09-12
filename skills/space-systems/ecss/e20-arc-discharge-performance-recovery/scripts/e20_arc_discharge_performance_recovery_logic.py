#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.4.3 arc discharge performance recovery
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard tolerates a short interruption of a
spacecraft function while an electrostatic discharge is occurring, on
the condition that the function comes back to the performance level its
specification states once the event has passed. This module implements
the checkable part of that clause: categorization of an arc event as a
primary discharge or a sustained secondary arc, derivation of the
outage from arc onset to restored service against the allowance the
function holds, comparison of every post-arc performance parameter
against its specified level in the correct direction of merit,
quantification of the residual degradation that never comes back, and
rejection of a recovery that leans on a ground action slower than the
outage the function is allowed. It does not size an arc suppression
network, does not model the discharge current waveform, and does not
set the allowance itself.
"""

import math

PRIMARY_ARC_KINDS = frozenset(
    {
        "surface_dielectric_primary_discharge",
        "triple_junction_primary_discharge",
        "internal_dielectric_breakdown",
        "harness_insulation_flashover",
    }
)
SUSTAINED_ARC_KINDS = frozenset(
    {
        "solar_array_sustained_secondary_arc",
        "bus_driven_sustained_arc",
        "permanent_short_sustained_arc",
    }
)

SENSE_HIGHER_IS_BETTER = "higher_is_better"
SENSE_LOWER_IS_BETTER = "lower_is_better"
PERFORMANCE_SENSES = frozenset(
    {SENSE_HIGHER_IS_BETTER, SENSE_LOWER_IS_BETTER}
)

RECOVERY_MODES = frozenset({"autonomous", "ground_commanded"})

DEFAULT_RESIDUAL_ALLOWANCE_PERCENT = 0.0
RECOVERY_REL_TOL = 1e-9
RECOVERY_ABS_TOL = 1e-12


def categorize_arc_event(event_kind):
    """Arc family for an event kind: "primary_discharge" for the
    self-extinguishing blowoff event the clause tolerates, or
    "sustained_secondary_arc" for an event fed by the power system that
    does not stop on its own. Raises ValueError for a kind that is not
    a clause 6.3.4.3 arc event."""
    if event_kind in PRIMARY_ARC_KINDS:
        return "primary_discharge"
    if event_kind in SUSTAINED_ARC_KINDS:
        return "sustained_secondary_arc"
    raise ValueError(
        "unrecognized arc event kind %r under "
        "E-ST-20C clause 6.3.4.3" % (event_kind,)
    )


def arc_family_findings(function_id, event_kind):
    """Findings (empty for a primary discharge) for the arc family. A
    sustained secondary arc is outside the brief-outage allowance
    altogether: it keeps drawing power after the discharge and is a
    design finding, not a recoverable interruption. Raises ValueError
    through categorize_arc_event."""
    if categorize_arc_event(event_kind) == "sustained_secondary_arc":
        return [
            {
                "issue": "sustained_secondary_arc_not_a_brief_outage",
                "function": function_id,
                "event_kind": event_kind,
            }
        ]
    return []


def outage_duration_s(arc_onset_s, service_restored_s):
    """Outage length in seconds: restored-service time less arc-onset
    time, both on the same mission clock. Raises ValueError for a
    negative onset or for a restoration that precedes the onset."""
    if arc_onset_s < 0:
        raise ValueError("arc_onset_s must be >= 0")
    if service_restored_s < arc_onset_s:
        raise ValueError(
            "service_restored_s must be >= arc_onset_s "
            "(service cannot return before the arc starts)"
        )
    return service_restored_s - arc_onset_s


def outage_findings(function_id, duration_s, allowance_s):
    """Findings (empty when the interruption is brief enough) for the
    outage against the allowance the function holds. An outage equal to
    the allowance within representation error is permitted -- the
    duration is a difference of two clock values and can land a few
    units on the wrong side of an allowance it physically meets. Raises
    ValueError for a negative duration or a non-positive allowance."""
    if duration_s < 0:
        raise ValueError("duration_s must be >= 0")
    if allowance_s <= 0:
        raise ValueError("allowance_s must be > 0")
    if duration_s > allowance_s and not math.isclose(
        duration_s, allowance_s, rel_tol=RECOVERY_REL_TOL,
        abs_tol=RECOVERY_ABS_TOL,
    ):
        return [
            {
                "issue": "arc_outage_exceeds_allowance",
                "function": function_id,
                "duration_s": duration_s,
                "allowance_s": allowance_s,
            }
        ]
    return []


def recovery_ratio(post_arc_value, specified_value, sense):
    """Ratio of achieved to required performance after the arc, always
    oriented so that a value of one or more means the specification is
    met. For a higher-is-better parameter the ratio is achieved over
    required; for a lower-is-better parameter it is required over
    achieved. Raises ValueError for an unrecognized sense, a
    non-positive specified value, a negative achieved value, or a zero
    achieved value on a lower-is-better parameter."""
    if sense not in PERFORMANCE_SENSES:
        raise ValueError("unrecognized performance sense %r" % (sense,))
    if specified_value <= 0:
        raise ValueError("specified_value must be > 0")
    if post_arc_value < 0:
        raise ValueError("post_arc_value must be >= 0")
    if sense == SENSE_HIGHER_IS_BETTER:
        return post_arc_value / specified_value
    if post_arc_value == 0:
        raise ValueError(
            "post_arc_value must be > 0 for a lower_is_better parameter"
        )
    return specified_value / post_arc_value


def performance_recovered(post_arc_value, specified_value, sense):
    """True when the post-arc value meets its specified level. A ratio
    equal to one within representation error counts as recovered.
    Raises ValueError through recovery_ratio."""
    ratio = recovery_ratio(post_arc_value, specified_value, sense)
    if ratio >= 1.0:
        return True
    return math.isclose(
        ratio, 1.0, rel_tol=RECOVERY_REL_TOL, abs_tol=RECOVERY_ABS_TOL
    )


def residual_degradation_percent(post_arc_value, specified_value, sense):
    """Shortfall against the specified level as a percentage, zero when
    the parameter is fully recovered or better. Raises ValueError
    through recovery_ratio."""
    ratio = recovery_ratio(post_arc_value, specified_value, sense)
    if ratio >= 1.0:
        return 0.0
    return (1.0 - ratio) * 100.0


def performance_findings(
    function_id,
    parameters,
    residual_allowance_percent=DEFAULT_RESIDUAL_ALLOWANCE_PERCENT,
):
    """Findings (empty when every parameter comes back) for the post-arc
    performance set.

    parameters: list of {"name", "post_arc_value", "specified_value",
    "sense"}. A parameter whose shortfall exceeds the residual
    allowance is reported with the shortfall it carries. Raises
    ValueError for an empty parameter list, a negative residual
    allowance, or through recovery_ratio for a bad parameter."""
    if not parameters:
        raise ValueError("parameters must carry at least one entry")
    if residual_allowance_percent < 0:
        raise ValueError("residual_allowance_percent must be >= 0")
    findings = []
    for parameter in parameters:
        shortfall = residual_degradation_percent(
            parameter["post_arc_value"],
            parameter["specified_value"],
            parameter["sense"],
        )
        if shortfall > residual_allowance_percent and not math.isclose(
            shortfall, residual_allowance_percent,
            rel_tol=RECOVERY_REL_TOL, abs_tol=RECOVERY_ABS_TOL,
        ):
            findings.append(
                {
                    "issue": "post_arc_performance_not_restored",
                    "function": function_id,
                    "parameter": parameter["name"],
                    "shortfall_percent": shortfall,
                    "allowance_percent": residual_allowance_percent,
                }
            )
    return findings


def recovery_autonomy_findings(
    function_id, recovery_mode, ground_response_latency_s, allowance_s
):
    """Findings (empty when the recovery fits the allowance) for how the
    function gets its service back. An autonomous recovery is self
    contained. A ground-commanded recovery only works if the ground
    loop closes inside the outage the function is allowed, so a latency
    longer than the allowance is a finding against the recovery
    concept. Raises ValueError for an unrecognized mode, a negative
    latency or a non-positive allowance."""
    if recovery_mode not in RECOVERY_MODES:
        raise ValueError("unrecognized recovery mode %r" % (recovery_mode,))
    if ground_response_latency_s < 0:
        raise ValueError("ground_response_latency_s must be >= 0")
    if allowance_s <= 0:
        raise ValueError("allowance_s must be > 0")
    if recovery_mode == "autonomous":
        return []
    if ground_response_latency_s > allowance_s and not math.isclose(
        ground_response_latency_s, allowance_s,
        rel_tol=RECOVERY_REL_TOL, abs_tol=RECOVERY_ABS_TOL,
    ):
        return [
            {
                "issue": "ground_recovery_slower_than_outage_allowance",
                "function": function_id,
                "latency_s": ground_response_latency_s,
                "allowance_s": allowance_s,
            }
        ]
    return []


def arc_event_review(event):
    """Full clause 6.3.4.3 review for one arc event on one function.

    event: {"function_id": str, "event_kind": str, "arc_onset_s": float,
    "service_restored_s": float, "outage_allowance_s": float,
    "parameters": [{"name", "post_arc_value", "specified_value",
    "sense"}], "recovery_mode": str, "ground_response_latency_s": float
    (optional, defaults to zero), "residual_allowance_percent": float
    (optional)}.

    Returns {"arc_family": [...], "outage": [...], "performance": [...],
    "autonomy": [...]}. Raises ValueError through the helpers for an
    unrecognized event kind, sense or recovery mode, or for an
    inconsistent clock or performance input. Does not mutate event."""
    function_id = event["function_id"]
    allowance_s = event["outage_allowance_s"]
    duration_s = outage_duration_s(
        event["arc_onset_s"], event["service_restored_s"]
    )
    return {
        "arc_family": arc_family_findings(function_id, event["event_kind"]),
        "outage": outage_findings(function_id, duration_s, allowance_s),
        "performance": performance_findings(
            function_id,
            event["parameters"],
            event.get(
                "residual_allowance_percent",
                DEFAULT_RESIDUAL_ALLOWANCE_PERCENT,
            ),
        ),
        "autonomy": recovery_autonomy_findings(
            function_id,
            event["recovery_mode"],
            event.get("ground_response_latency_s", 0.0),
            allowance_s,
        ),
    }


def is_recovery_acceptable(review):
    """True when every finding list in an arc_event_review result is
    empty -- the interruption was brief, self-extinguishing, fully
    recovered, and did not depend on a ground loop slower than the
    allowance."""
    return all(len(findings) == 0 for findings in review.values())
