#!/usr/bin/env python3
"""Power-lead susceptibility test purpose, ECSS-E-ST-20-07C clause 5.4.7.1.

Paraphrased procedure, no verbatim standard text. The clause states what the
conducted susceptibility test on power leads is for: showing that the unit
goes on working while disturbance signals are injected onto the leads that
feed it. A test only demonstrates that aim if the right leads are in scope,
the injection actually reaches every one of them across the declared band at
the declared level, and the monitored functions carry an allowance that makes
"went on working" decidable. This module turns that into an assessment:

  declared leads                 -> supply leads in scope, others out of scope
  injections vs in-scope leads   -> supply leads nothing is injected onto
  injections vs declared band    -> sub-bands never disturbed, per lead
  injected level vs declared     -> injections that under-drive the lead
  monitored functions            -> functions with no decidable allowance
  observed responses             -> tolerant, degraded or malfunction

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Frequencies, levels and deviations are floats
# written by bench software, so two values meant to be equal can differ by
# a few units in the last place. The tolerance absorbs that representation
# error only; it never excuses a real shortfall.
REL_TOL = 1e-12
ABS_TOL = 1e-9

PRIMARY_POWER = "primary-power"
SECONDARY_POWER = "secondary-power"
POWER_RETURN = "power-return"
SIGNAL = "signal"
DATA = "data"

LEAD_KINDS = (PRIMARY_POWER, SECONDARY_POWER, POWER_RETURN, SIGNAL, DATA)
SUPPLY_LEAD_KINDS = (PRIMARY_POWER, SECONDARY_POWER, POWER_RETURN)

WAVEFORMS = ("sinusoidal", "transient", "ripple")

RESPONSE_TOLERANT = "tolerant"
RESPONSE_DEGRADED = "degraded"
RESPONSE_MALFUNCTION = "malfunction"
RESPONSE_CATEGORIES = (
    RESPONSE_TOLERANT,
    RESPONSE_DEGRADED,
    RESPONSE_MALFUNCTION,
)


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _token(record, key, where, allowed=None):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s: field %r must be a non-empty string" % (where, key))
    token = value.strip().lower()
    if allowed is not None and token not in allowed:
        raise ValueError(
            "%s: field %r must be one of %s, got %r" % (where, key, list(allowed), token)
        )
    return token


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def _close(left, right):
    return math.isclose(left, right, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_least(value, bound):
    """True when value meets bound, absorbing float representation error."""
    if value >= bound:
        return True
    return _close(value, bound)


def at_most(value, bound):
    """True when value stays at or under bound, absorbing float error."""
    if value <= bound:
        return True
    return _close(value, bound)


def validate_lead(lead, where="lead"):
    """Validate one declared interface lead of the unit under test."""
    if not isinstance(lead, dict):
        raise ValueError("%s: must be a mapping" % where)
    identifier = _token(lead, "lead_id", where)
    kind = _token(lead, "kind", where, LEAD_KINDS)
    voltage = _number(lead, "nominal_voltage_v", where)
    current = _number(lead, "nominal_current_a", where)
    if voltage < 0.0:
        raise ValueError("%s: nominal_voltage_v must be >= 0, got %g" % (where, voltage))
    if current < 0.0:
        raise ValueError("%s: nominal_current_a must be >= 0, got %g" % (where, current))
    return {
        "lead_id": identifier,
        "kind": kind,
        "nominal_voltage_v": voltage,
        "nominal_current_a": current,
    }


def validate_leads(leads):
    """Validate the declared lead set and return it ordered by identifier."""
    where = "leads"
    if not isinstance(leads, (list, tuple)):
        raise ValueError("%s: must be a list" % where)
    if len(leads) == 0:
        raise ValueError("%s: at least one declared lead is required" % where)
    out = [validate_lead(lead, "%s[%d]" % (where, i)) for i, lead in enumerate(leads)]
    out.sort(key=lambda entry: entry["lead_id"])
    return out


def is_supply_lead(lead):
    """True when a lead carries supply current and so falls under the aim."""
    return validate_lead(lead)["kind"] in SUPPLY_LEAD_KINDS


def supply_leads(leads):
    """Declared leads the clause's aim actually covers."""
    return [lead for lead in validate_leads(leads) if lead["kind"] in SUPPLY_LEAD_KINDS]


def non_supply_leads(leads):
    """Declared leads outside this clause's aim, injected onto or not."""
    return [
        lead for lead in validate_leads(leads) if lead["kind"] not in SUPPLY_LEAD_KINDS
    ]


def validate_injection(injection, where="injection"):
    """Validate one planned disturbance injection onto a named lead."""
    if not isinstance(injection, dict):
        raise ValueError("%s: must be a mapping" % where)
    lead_id = _token(injection, "lead_id", where)
    waveform = _token(injection, "waveform", where, WAVEFORMS)
    start = _number(injection, "start_hz", where)
    stop = _number(injection, "stop_hz", where)
    level = _number(injection, "level_dbuv", where)
    if start <= 0.0:
        raise ValueError("%s: start_hz must be > 0, got %g" % (where, start))
    if stop <= start or _close(stop, start):
        raise ValueError(
            "%s: stop_hz (%g) must exceed start_hz (%g)" % (where, stop, start)
        )
    return {
        "lead_id": lead_id,
        "waveform": waveform,
        "start_hz": start,
        "stop_hz": stop,
        "level_dbuv": level,
    }


def validate_injections(injections):
    """Validate the injection plan and return it ordered."""
    where = "injections"
    if not isinstance(injections, (list, tuple)):
        raise ValueError("%s: must be a list" % where)
    if len(injections) == 0:
        raise ValueError("%s: at least one planned injection is required" % where)
    out = [
        validate_injection(item, "%s[%d]" % (where, i))
        for i, item in enumerate(injections)
    ]
    out.sort(key=lambda entry: (entry["lead_id"], entry["start_hz"], entry["stop_hz"]))
    return out


def leads_without_injection(leads, injections):
    """Supply leads the aim covers that the plan never injects onto."""
    planned = {item["lead_id"] for item in validate_injections(injections)}
    return [lead["lead_id"] for lead in supply_leads(leads) if lead["lead_id"] not in planned]


def injections_on_non_supply_leads(leads, injections):
    """Planned injections aimed at leads this clause's purpose does not cover."""
    outside = {lead["lead_id"] for lead in non_supply_leads(leads)}
    return [item for item in validate_injections(injections) if item["lead_id"] in outside]


def undeclared_injection_targets(leads, injections):
    """Injections naming a lead that the declared lead set never listed."""
    declared = {lead["lead_id"] for lead in validate_leads(leads)}
    return sorted(
        {
            item["lead_id"]
            for item in validate_injections(injections)
            if item["lead_id"] not in declared
        }
    )


def _merge(spans):
    merged = []
    for start, stop in sorted(spans):
        if merged and (start <= merged[-1][1] or _close(start, merged[-1][1])):
            if stop > merged[-1][1]:
                merged[-1][1] = stop
        else:
            merged.append([start, stop])
    return merged


def undisturbed_sub_bands(injections, lead_id, band_start_hz, band_stop_hz):
    """Sub-bands of the declared band no injection ever drove onto a lead."""
    start = _scalar(band_start_hz, "band_start_hz")
    stop = _scalar(band_stop_hz, "band_stop_hz")
    if start <= 0.0:
        raise ValueError("band_start_hz must be > 0, got %g" % start)
    if stop <= start or _close(stop, start):
        raise ValueError(
            "band_stop_hz (%g) must exceed band_start_hz (%g)" % (stop, start)
        )
    name = _token({"lead_id": lead_id}, "lead_id", "lead_id")
    spans = [
        (item["start_hz"], item["stop_hz"])
        for item in validate_injections(injections)
        if item["lead_id"] == name
    ]
    if not spans:
        return [{"start_hz": start, "stop_hz": stop, "span_hz": stop - start}]
    gaps = []
    cursor = start
    for lower, upper in _merge(spans):
        if upper <= cursor or lower >= stop:
            continue
        edge = min(lower, stop)
        if edge > cursor and not _close(edge, cursor):
            gaps.append({"start_hz": cursor, "stop_hz": edge, "span_hz": edge - cursor})
        cursor = max(cursor, min(upper, stop))
    if stop > cursor and not _close(stop, cursor):
        gaps.append({"start_hz": cursor, "stop_hz": stop, "span_hz": stop - cursor})
    return gaps


def under_driven_injections(injections, declared_level_dbuv):
    """Injections planned below the level the unit is required to tolerate."""
    level = _scalar(declared_level_dbuv, "declared_level_dbuv")
    return [
        item
        for item in validate_injections(injections)
        if not at_least(item["level_dbuv"], level)
    ]


def validate_observation(observation, where="observation"):
    """Validate one monitored-function response to an injection."""
    if not isinstance(observation, dict):
        raise ValueError("%s: must be a mapping" % where)
    function_id = _token(observation, "function_id", where)
    lead_id = _token(observation, "lead_id", where)
    deviation = _number(observation, "deviation", where)
    allowed = _number(observation, "allowed_deviation", where)
    recovering = _flag(observation, "self_recovering", where)
    if deviation < 0.0:
        raise ValueError("%s: deviation must be >= 0, got %g" % (where, deviation))
    if allowed <= 0.0:
        raise ValueError(
            "%s: allowed_deviation must be > 0 for the aim to be decidable, got %g"
            % (where, allowed)
        )
    return {
        "function_id": function_id,
        "lead_id": lead_id,
        "deviation": deviation,
        "allowed_deviation": allowed,
        "self_recovering": recovering,
    }


def validate_observations(observations):
    """Validate the monitored-function responses and return them ordered."""
    where = "observations"
    if not isinstance(observations, (list, tuple)):
        raise ValueError("%s: must be a list" % where)
    if len(observations) == 0:
        raise ValueError("%s: at least one monitored function is required" % where)
    out = [
        validate_observation(item, "%s[%d]" % (where, i))
        for i, item in enumerate(observations)
    ]
    out.sort(key=lambda entry: (entry["function_id"], entry["lead_id"]))
    return out


def deviation_ratio(observation):
    """Observed deviation expressed in units of the allowance for it."""
    record = validate_observation(observation)
    return record["deviation"] / record["allowed_deviation"]


def categorize_response(observation):
    """Group a monitored response as tolerant, degraded or malfunction."""
    record = validate_observation(observation)
    if at_most(record["deviation"], record["allowed_deviation"]):
        return RESPONSE_TOLERANT
    if record["self_recovering"]:
        return RESPONSE_DEGRADED
    return RESPONSE_MALFUNCTION


def functions_without_coverage(observations, leads, injections):
    """Monitored functions watched only on leads nothing is injected onto."""
    driven = {item["lead_id"] for item in validate_injections(injections)}
    supply = {lead["lead_id"] for lead in supply_leads(leads)}
    watched = {}
    for record in validate_observations(observations):
        watched.setdefault(record["function_id"], set()).add(record["lead_id"])
    return sorted(
        name
        for name, seen in watched.items()
        if not (seen & driven & supply)
    )


def assess_power_lead_susceptibility_purpose(
    leads,
    injections,
    observations,
    band_start_hz,
    band_stop_hz,
    declared_level_dbuv,
):
    """Full clause 5.4.7.1 assessment of whether a test can meet its aim."""
    declared = validate_leads(leads)
    planned = validate_injections(injections)
    watched = validate_observations(observations)
    in_scope = supply_leads(declared)
    unplanned = leads_without_injection(declared, planned)
    stray = injections_on_non_supply_leads(declared, planned)
    undeclared = undeclared_injection_targets(declared, planned)
    weak = under_driven_injections(planned, declared_level_dbuv)
    blind = functions_without_coverage(watched, declared, planned)

    gaps = []
    for lead in in_scope:
        for gap in undisturbed_sub_bands(
            planned, lead["lead_id"], band_start_hz, band_stop_hz
        ):
            gaps.append(dict(gap, lead_id=lead["lead_id"]))

    responses = []
    for record in watched:
        responses.append(
            dict(
                record,
                ratio=deviation_ratio(record),
                category=categorize_response(record),
            )
        )

    findings = []
    for lead_id in unplanned:
        findings.append(
            "supply lead %s carries the unit but no disturbance is injected onto it"
            % lead_id
        )
    for gap in gaps:
        if gap["lead_id"] in unplanned:
            continue
        findings.append(
            "lead %s is never disturbed between %g Hz and %g Hz (%g Hz wide)"
            % (gap["lead_id"], gap["start_hz"], gap["stop_hz"], gap["span_hz"])
        )
    for item in weak:
        findings.append(
            "injection onto %s is planned at %g dBuV, under the %g dBuV the unit "
            "must tolerate" % (item["lead_id"], item["level_dbuv"], declared_level_dbuv)
        )
    for name in blind:
        findings.append(
            "function %s is monitored only on leads nothing is injected onto"
            % name
        )
    for lead_id in undeclared:
        findings.append(
            "injection names lead %s, which the declared lead set never listed"
            % lead_id
        )
    for response in responses:
        if response["category"] == RESPONSE_MALFUNCTION:
            findings.append(
                "function %s deviates %g against a %g allowance on lead %s and does "
                "not recover"
                % (
                    response["function_id"],
                    response["deviation"],
                    response["allowed_deviation"],
                    response["lead_id"],
                )
            )

    limitations = []
    for item in stray:
        limitations.append(
            "injection onto %s targets a %s lead, outside the aim of this clause"
            % (
                item["lead_id"],
                next(
                    lead["kind"]
                    for lead in declared
                    if lead["lead_id"] == item["lead_id"]
                ),
            )
        )
    for response in responses:
        if response["category"] == RESPONSE_DEGRADED:
            limitations.append(
                "function %s degrades past its allowance on lead %s but recovers"
                % (response["function_id"], response["lead_id"])
            )

    return {
        "leads": declared,
        "in_scope_leads": [lead["lead_id"] for lead in in_scope],
        "out_of_scope_leads": [lead["lead_id"] for lead in non_supply_leads(declared)],
        "injections": planned,
        "leads_without_injection": unplanned,
        "undisturbed": gaps,
        "under_driven": weak,
        "stray_injections": stray,
        "undeclared_targets": undeclared,
        "unwatched_functions": blind,
        "responses": responses,
        "findings": findings,
        "limitations": limitations,
        "verdict": "aim-demonstrable" if not findings else "aim-not-demonstrable",
    }
