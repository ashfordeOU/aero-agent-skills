"""Survival of the surrounding parts when a limiter switch fails dissipatively.

Anchor: ECSS-E-ST-20-20C clause 5.2.14.1.1 (the components around a current
limiter switch survive a dissipative failure of that switch when no other
means removes it). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
A switch that fails dissipatively does not open and does not short. It sits
in its limitation region, holding the limited current while the whole bus
drop appears across it, and it keeps doing so for as long as the bus is up.
The case the clause asks about is the uncleared one, so the assessment is a
steady state, not an energy pulse:

* the dissipation is the drop across the failed switch times the current it
  is holding;
* every part named as surrounding the switch is raised above the reference
  temperature by that dissipation through its own thermal coupling, expressed
  as the kelvin it rises per watt dissipated in the switch;
* each part is compared against its derated limit, the rated maximum less the
  margin the parts programme withholds;
* the dissipation each part could have taken is derived back from its limit,
  so a report says by how much the design misses and not merely that it does.

A clearing device may be declared. It does not change the arithmetic: the
clause's case is the one where nothing else removes the failure, so a
declared clearing path is reported as being outside that case while the
uncleared steady state is still graded. Survival is reported per part; the
switch is conformant only when every named part stays at or under its own
derated limit.
"""

__all__ = [
    "ABSOLUTE_ZERO_C",
    "SURVIVAL_TOLERANCE_K",
    "validate_case",
    "dissipated_power_w",
    "derated_limit_c",
    "part_temperature_c",
    "allowable_power_w",
    "part_outcome",
    "assess_dissipative_failure_survival",
]

ABSOLUTE_ZERO_C = -273.15

# A part landing exactly on its derated limit survives. The comparison is
# made with this absolute slack so that a case built to sit on the bound
# grades the same way wherever the arithmetic runs.
SURVIVAL_TOLERANCE_K = 1e-9


def _number(value, label):
    """Return value as a float, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    result = float(value)
    if result != result or result in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return result


def _positive(value, label):
    """Return value as a strictly positive float."""
    result = _number(value, label)
    if result <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return result


def _temperature(value, label):
    """Return value as a physically possible celsius temperature."""
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


def validate_case(spec):
    """Return the case as (switch, drop, current, reference, parts, clearing).

    spec keys: switch, voltage_drop_v, limited_current_a, reference_temp_c,
    parts (sequence of mappings with name, coupling_k_per_w, rated_max_c and
    an optional derating_margin_k) and an optional external_clearing mapping.
    """
    if not isinstance(spec, dict):
        raise ValueError("dissipative failure case must be a mapping")
    for key in ("switch", "voltage_drop_v", "limited_current_a", "reference_temp_c", "parts"):
        if key not in spec:
            raise ValueError("case missing required key '%s'" % key)

    switch = _identifier(spec["switch"], "switch")
    drop_v = _positive(spec["voltage_drop_v"], "voltage_drop_v")
    current_a = _positive(spec["limited_current_a"], "limited_current_a")
    reference_c = _temperature(spec["reference_temp_c"], "reference_temp_c")

    raw_parts = spec["parts"]
    if not isinstance(raw_parts, (list, tuple)) or not raw_parts:
        raise ValueError("parts must be a non-empty sequence")
    parts = []
    names = []
    for i, item in enumerate(raw_parts):
        if not isinstance(item, dict):
            raise ValueError("parts[%d] must be a mapping" % i)
        for key in ("name", "coupling_k_per_w", "rated_max_c"):
            if key not in item:
                raise ValueError("parts[%d] missing required key '%s'" % (i, key))
        name = _identifier(item["name"], "parts[%d]['name']" % i)
        if name in names:
            raise ValueError("part %r is listed twice" % name)
        names.append(name)
        coupling = _positive(item["coupling_k_per_w"], "part %r coupling_k_per_w" % name)
        rated_c = _temperature(item["rated_max_c"], "part %r rated_max_c" % name)
        margin_k = _number(item.get("derating_margin_k", 0.0), "part %r derating_margin_k" % name)
        if margin_k < 0.0:
            raise ValueError(
                "part %r derating_margin_k must not be negative, got %r" % (name, margin_k)
            )
        limit_c = derated_limit_c(rated_c, margin_k)
        if limit_c <= reference_c:
            raise ValueError(
                "part %r sits at its derated limit before the failure "
                "(limit %.3f C, reference %.3f C)" % (name, limit_c, reference_c)
            )
        parts.append(
            {
                "name": name,
                "coupling_k_per_w": coupling,
                "rated_max_c": rated_c,
                "derating_margin_k": margin_k,
                "derated_limit_c": limit_c,
            }
        )

    raw_clearing = spec.get("external_clearing")
    clearing = None
    if raw_clearing is not None:
        if not isinstance(raw_clearing, dict):
            raise ValueError("external_clearing must be a mapping or absent")
        for key in ("name", "clears_after_s"):
            if key not in raw_clearing:
                raise ValueError("external_clearing missing required key '%s'" % key)
        clearing = {
            "name": _identifier(raw_clearing["name"], "external_clearing['name']"),
            "clears_after_s": _positive(
                raw_clearing["clears_after_s"], "external_clearing['clears_after_s']"
            ),
        }
    return (switch, drop_v, current_a, reference_c, parts, clearing)


def dissipated_power_w(voltage_drop_v, limited_current_a):
    """Return the steady dissipation of a switch stuck in limitation."""
    return _positive(voltage_drop_v, "voltage_drop_v") * _positive(
        limited_current_a, "limited_current_a"
    )


def derated_limit_c(rated_max_c, derating_margin_k=0.0):
    """Return the temperature a part is allowed to reach."""
    return _number(rated_max_c, "rated_max_c") - _number(derating_margin_k, "derating_margin_k")


def part_temperature_c(reference_temp_c, power_w, coupling_k_per_w):
    """Return the steady temperature a part reaches under the dissipation."""
    return _number(reference_temp_c, "reference_temp_c") + _number(
        power_w, "power_w"
    ) * _positive(coupling_k_per_w, "coupling_k_per_w")


def allowable_power_w(part, reference_temp_c):
    """Return the dissipation that would take a part to its derated limit."""
    return (part["derated_limit_c"] - _number(reference_temp_c, "reference_temp_c")) / part[
        "coupling_k_per_w"
    ]


def part_outcome(part, reference_temp_c, power_w):
    """Return the temperature, margin, allowable power and survival of a part."""
    temperature_c = part_temperature_c(reference_temp_c, power_w, part["coupling_k_per_w"])
    margin_k = part["derated_limit_c"] - temperature_c
    allowable_w = allowable_power_w(part, reference_temp_c)
    return {
        "name": part["name"],
        "temperature_c": temperature_c,
        "derated_limit_c": part["derated_limit_c"],
        "margin_k": margin_k,
        "allowable_power_w": allowable_w,
        "survives": margin_k >= -SURVIVAL_TOLERANCE_K,
    }


def assess_dissipative_failure_survival(spec):
    """Assess an uncleared dissipative switch failure against clause 5.2.14.1.1."""
    switch, drop_v, current_a, reference_c, parts, clearing = validate_case(spec)
    power_w = drop_v * current_a

    outcomes = [part_outcome(part, reference_c, power_w) for part in parts]
    survivors = [item["name"] for item in outcomes if item["survives"]]
    exceeded = [item for item in outcomes if not item["survives"]]

    findings = []
    notes = []
    for item in exceeded:
        findings.append(
            "%s reaches %.1f C against a derated limit of %.1f C, over by %.1f K; "
            "it could take %.2f W and the failed switch holds %.2f W"
            % (
                item["name"],
                item["temperature_c"],
                item["derated_limit_c"],
                -item["margin_k"],
                item["allowable_power_w"],
                power_w,
            )
        )
    if clearing is not None:
        notes.append(
            "%s is declared to clear the failure after %.3f s; the clause addresses "
            "the case where nothing else removes it, so the uncleared steady state "
            "is graded and the clearing path is reported for information"
            % (clearing["name"], clearing["clears_after_s"])
        )

    worst = min(outcomes, key=lambda item: item["margin_k"])
    limiting_power_w = min(item["allowable_power_w"] for item in outcomes)
    return {
        "switch": switch,
        "dissipated_power_w": power_w,
        "reference_temp_c": reference_c,
        "part_outcomes": outcomes,
        "surviving_parts": survivors,
        "exceeded_parts": [item["name"] for item in exceeded],
        "worst_part": worst["name"],
        "worst_margin_k": worst["margin_k"],
        "limiting_allowable_power_w": limiting_power_w,
        "power_headroom_ratio": limiting_power_w / power_w,
        "externally_cleared": clearing is not None,
        "survives_uncleared_failure": not exceeded,
        "verdict": "compliant" if not exceeded else "non-compliant",
        "findings": findings,
        "notes": notes,
    }
