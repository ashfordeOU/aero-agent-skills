"""Onboard software response to a dissipatively failed limiter switch.

Anchor: ECSS-E-ST-20-20C clause 5.2.14.2.1 (the behaviour to be established
when onboard software answers a dissipatively failed current limiter switch
by reducing the load it carries or by commanding that switch off).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
Software is a slow protection, so the argument it supports has two halves and
both have to hold:

* the transient. Detection, voting and command take time, and during that
  time the failed switch is still holding the full dissipation. Each part is
  raised on a first order thermal response -- its coupling sets where it ends
  up, the product of that coupling and its heat capacity sets how fast it
  gets there -- and the temperature reached when the command lands is what
  the part actually has to take. The time at which the part would have
  reached its limit is reported beside it, because a latency budget is only
  meaningful against that number.
* the residual. What the software leaves behind is not always zero. Reducing
  the load leaves the switch dissipating at the reduced current for the rest
  of the mission, so that steady state is assessed as well; commanding the
  switch off leaves nothing, but only if the failed switch answers the off
  command at all.

A switch that has failed dissipatively is a switch that is misbehaving, and
an off command it cannot answer turns the declared response back into no
response. That degeneration is reported explicitly rather than assumed away,
and the parts are then graded against the uncleared dissipation.

The response is adequate only when an effective action is declared, every
part survives the latency, and every part survives what the action leaves
running.
"""

import math

__all__ = [
    "ABSOLUTE_ZERO_C",
    "SURVIVAL_TOLERANCE_K",
    "ONBOARD_ACTIONS",
    "validate_response_case",
    "dissipation_w",
    "thermal_time_constant_s",
    "transient_temperature_c",
    "time_to_limit_s",
    "residual_current_a",
    "part_response",
    "assess_onboard_removal_response",
]

ABSOLUTE_ZERO_C = -273.15

# A part landing exactly on its derated limit survives; the comparison keeps
# this absolute slack so a case built on the bound grades the same way
# wherever the exponential is evaluated.
SURVIVAL_TOLERANCE_K = 1e-9

# reduce-load: software sheds users until the switch leaves limitation.
# switch-off: software commands the failed limiter off outright.
# none: no onboard response is declared, so the failure stays uncleared.
ONBOARD_ACTIONS = ("reduce-load", "switch-off", "none")


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    result = float(value)
    if result != result or result in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return result


def _positive(value, label):
    result = _number(value, label)
    if result <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return result


def _temperature(value, label):
    result = _number(value, label)
    if result <= ABSOLUTE_ZERO_C:
        raise ValueError("%s must be above absolute zero, got %r" % (label, value))
    return result


def _identifier(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def validate_response_case(spec):
    """Return the case as a normalised mapping, or raise on a bad spec.

    spec keys: switch, voltage_drop_v, failed_current_a, reference_temp_c,
    action, parts, plus response_latency_s for any action other than none,
    reduced_current_a for reduce-load and off_command_effective for
    switch-off.
    """
    if not isinstance(spec, dict):
        raise ValueError("onboard response case must be a mapping")
    for key in (
        "switch",
        "voltage_drop_v",
        "failed_current_a",
        "reference_temp_c",
        "action",
        "parts",
    ):
        if key not in spec:
            raise ValueError("case missing required key '%s'" % key)

    switch = _identifier(spec["switch"], "switch")
    drop_v = _positive(spec["voltage_drop_v"], "voltage_drop_v")
    failed_a = _positive(spec["failed_current_a"], "failed_current_a")
    reference_c = _temperature(spec["reference_temp_c"], "reference_temp_c")

    action = _identifier(spec["action"], "action")
    if action not in ONBOARD_ACTIONS:
        raise ValueError(
            "action %r is not one of %s" % (action, ", ".join(ONBOARD_ACTIONS))
        )

    reduced_a = None
    if action == "reduce-load":
        if "reduced_current_a" not in spec:
            raise ValueError("a reduce-load action needs 'reduced_current_a'")
        reduced_a = _positive(spec["reduced_current_a"], "reduced_current_a")
        if reduced_a >= failed_a:
            raise ValueError(
                "reduced_current_a %r does not reduce the failed current %r"
                % (reduced_a, failed_a)
            )
    elif "reduced_current_a" in spec:
        raise ValueError("'reduced_current_a' belongs to a reduce-load action only")

    off_effective = None
    if action == "switch-off":
        if "off_command_effective" not in spec:
            raise ValueError("a switch-off action needs 'off_command_effective'")
        off_effective = spec["off_command_effective"]
        if not isinstance(off_effective, bool):
            raise ValueError(
                "off_command_effective must be a boolean, got %r" % (off_effective,)
            )
    elif "off_command_effective" in spec:
        raise ValueError("'off_command_effective' belongs to a switch-off action only")

    latency_s = None
    if action == "none":
        if "response_latency_s" in spec:
            raise ValueError("'response_latency_s' has no meaning without an action")
    else:
        if "response_latency_s" not in spec:
            raise ValueError("an onboard action needs 'response_latency_s'")
        latency_s = _positive(spec["response_latency_s"], "response_latency_s")

    raw_parts = spec["parts"]
    if not isinstance(raw_parts, (list, tuple)) or not raw_parts:
        raise ValueError("parts must be a non-empty sequence")
    parts = []
    names = []
    for i, item in enumerate(raw_parts):
        if not isinstance(item, dict):
            raise ValueError("parts[%d] must be a mapping" % i)
        for key in ("name", "coupling_k_per_w", "heat_capacity_j_per_k", "rated_max_c"):
            if key not in item:
                raise ValueError("parts[%d] missing required key '%s'" % (i, key))
        name = _identifier(item["name"], "parts[%d]['name']" % i)
        if name in names:
            raise ValueError("part %r is listed twice" % name)
        names.append(name)
        coupling = _positive(item["coupling_k_per_w"], "part %r coupling_k_per_w" % name)
        capacity = _positive(
            item["heat_capacity_j_per_k"], "part %r heat_capacity_j_per_k" % name
        )
        rated_c = _temperature(item["rated_max_c"], "part %r rated_max_c" % name)
        margin_k = _number(
            item.get("derating_margin_k", 0.0), "part %r derating_margin_k" % name
        )
        if margin_k < 0.0:
            raise ValueError(
                "part %r derating_margin_k must not be negative, got %r" % (name, margin_k)
            )
        limit_c = rated_c - margin_k
        if limit_c <= reference_c:
            raise ValueError(
                "part %r sits at its derated limit before the failure "
                "(limit %.3f C, reference %.3f C)" % (name, limit_c, reference_c)
            )
        parts.append(
            {
                "name": name,
                "coupling_k_per_w": coupling,
                "heat_capacity_j_per_k": capacity,
                "derated_limit_c": limit_c,
                "time_constant_s": thermal_time_constant_s(coupling, capacity),
            }
        )

    return {
        "switch": switch,
        "voltage_drop_v": drop_v,
        "failed_current_a": failed_a,
        "reference_temp_c": reference_c,
        "action": action,
        "reduced_current_a": reduced_a,
        "off_command_effective": off_effective,
        "response_latency_s": latency_s,
        "parts": parts,
    }


def dissipation_w(voltage_drop_v, current_a):
    """Return the dissipation a switch holds at a given current."""
    drop = _positive(voltage_drop_v, "voltage_drop_v")
    current = _number(current_a, "current_a")
    if current < 0.0:
        raise ValueError("current_a must not be negative, got %r" % (current_a,))
    return drop * current


def thermal_time_constant_s(coupling_k_per_w, heat_capacity_j_per_k):
    """Return the first order time constant of a part."""
    return _positive(coupling_k_per_w, "coupling_k_per_w") * _positive(
        heat_capacity_j_per_k, "heat_capacity_j_per_k"
    )


def transient_temperature_c(reference_temp_c, power_w, coupling_k_per_w, time_constant_s, elapsed_s):
    """Return the temperature of a part after elapsed_s of a step in power."""
    reference = _number(reference_temp_c, "reference_temp_c")
    power = _number(power_w, "power_w")
    coupling = _positive(coupling_k_per_w, "coupling_k_per_w")
    tau = _positive(time_constant_s, "time_constant_s")
    elapsed = _number(elapsed_s, "elapsed_s")
    if elapsed < 0.0:
        raise ValueError("elapsed_s must not be negative, got %r" % (elapsed_s,))
    return reference + power * coupling * (1.0 - math.exp(-elapsed / tau))


def time_to_limit_s(reference_temp_c, power_w, coupling_k_per_w, time_constant_s, limit_c):
    """Return when a part reaches its limit, or None when it never does."""
    reference = _number(reference_temp_c, "reference_temp_c")
    power = _number(power_w, "power_w")
    coupling = _positive(coupling_k_per_w, "coupling_k_per_w")
    tau = _positive(time_constant_s, "time_constant_s")
    limit = _number(limit_c, "limit_c")
    available_k = limit - reference
    if available_k <= 0.0:
        return 0.0
    asymptote_k = power * coupling
    if asymptote_k <= available_k + SURVIVAL_TOLERANCE_K:
        return None
    return -tau * math.log(1.0 - available_k / asymptote_k)


def residual_current_a(case):
    """Return the current the failed switch keeps holding after the action."""
    action = case["action"]
    if action == "reduce-load":
        return case["reduced_current_a"]
    if action == "switch-off" and case["off_command_effective"]:
        return 0.0
    return case["failed_current_a"]


def part_response(part, case, pre_power_w, residual_power_w):
    """Return the transient and residual outcome for one part."""
    reference_c = case["reference_temp_c"]
    limit_c = part["derated_limit_c"]
    tau_s = part["time_constant_s"]
    reach_s = time_to_limit_s(
        reference_c, pre_power_w, part["coupling_k_per_w"], tau_s, limit_c
    )
    latency_s = case["response_latency_s"]
    if latency_s is None:
        peak_c = reference_c + pre_power_w * part["coupling_k_per_w"]
    else:
        peak_c = transient_temperature_c(
            reference_c, pre_power_w, part["coupling_k_per_w"], tau_s, latency_s
        )
    residual_c = reference_c + residual_power_w * part["coupling_k_per_w"]
    return {
        "name": part["name"],
        "time_constant_s": tau_s,
        "derated_limit_c": limit_c,
        "time_to_limit_s": reach_s,
        "temperature_at_response_c": peak_c,
        "transient_margin_k": limit_c - peak_c,
        "survives_transient": (limit_c - peak_c) >= -SURVIVAL_TOLERANCE_K,
        "residual_temperature_c": residual_c,
        "residual_margin_k": limit_c - residual_c,
        "survives_residual": (limit_c - residual_c) >= -SURVIVAL_TOLERANCE_K,
    }


def assess_onboard_removal_response(spec):
    """Assess an onboard software response against clause 5.2.14.2.1."""
    case = validate_response_case(spec)
    pre_power_w = dissipation_w(case["voltage_drop_v"], case["failed_current_a"])
    residual_a = residual_current_a(case)
    residual_power_w = dissipation_w(case["voltage_drop_v"], residual_a)

    action = case["action"]
    if action == "none":
        effective_action = "none"
    elif action == "switch-off" and not case["off_command_effective"]:
        effective_action = "none"
    else:
        effective_action = action

    responses = [part_response(part, case, pre_power_w, residual_power_w) for part in case["parts"]]

    findings = []
    notes = []
    if action == "none":
        findings.append(
            "no onboard response is declared, so the failed switch keeps holding "
            "%.2f W and the parts are left with the uncleared case" % pre_power_w
        )
    elif effective_action == "none":
        findings.append(
            "the off command is declared ineffective on the failed switch, so the "
            "declared response removes nothing and %.2f W keeps running" % pre_power_w
        )
    elif action == "reduce-load":
        notes.append(
            "reducing the load leaves the failed switch holding %.2f W for the rest "
            "of the mission; the residual steady state is graded, not the peak alone"
            % residual_power_w
        )

    for item in responses:
        if not item["survives_transient"]:
            reach = item["time_to_limit_s"]
            reach_text = (
                "it reaches that limit %.1f s after the failure"
                % reach
                if reach is not None
                else "it would not have reached that limit on this dissipation"
            )
            findings.append(
                "%s is at %.1f C when the response lands against a derated limit of "
                "%.1f C; %s"
                % (item["name"], item["temperature_at_response_c"], item["derated_limit_c"], reach_text)
            )
        if not item["survives_residual"]:
            findings.append(
                "%s settles at %.1f C on the %.2f W the response leaves running, "
                "against a derated limit of %.1f C"
                % (
                    item["name"],
                    item["residual_temperature_c"],
                    residual_power_w,
                    item["derated_limit_c"],
                )
            )

    transient_casualties = [i["name"] for i in responses if not i["survives_transient"]]
    residual_casualties = [i["name"] for i in responses if not i["survives_residual"]]
    reachable = [i["time_to_limit_s"] for i in responses if i["time_to_limit_s"] is not None]
    latency_budget_s = min(reachable) if reachable else None

    adequate = (
        effective_action != "none"
        and not transient_casualties
        and not residual_casualties
    )
    return {
        "switch": case["switch"],
        "declared_action": action,
        "effective_action": effective_action,
        "pre_response_power_w": pre_power_w,
        "residual_power_w": residual_power_w,
        "response_latency_s": case["response_latency_s"],
        "latency_budget_s": latency_budget_s,
        "part_responses": responses,
        "transient_casualties": transient_casualties,
        "residual_casualties": residual_casualties,
        "response_adequate": adequate,
        "verdict": "compliant" if adequate else "non-compliant",
        "findings": findings,
        "notes": notes,
    }
