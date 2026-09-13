#!/usr/bin/env python3
"""Qualification of radio power handling together with gas discharge behaviour.

Anchor: ECSS-E-ST-20C clause 7.3.4 (paraphrased into an implementable
procedure; no standard text is reproduced).

The clause treats one qualification approach that has to close two different
questions about the same hardware:

* power-handling-capability -- the item carries the overstressed level long
  enough to reach thermal steady state, at the hot case it will really see;
* gas-discharge-behaviour -- the item stays discharge-free at that same level
  while the ambient pressure is swept through the band where onset is lowest.

The two are only one qualification when they close on one hardware standard,
or on two standards joined by a recorded configuration link. A design change
afterwards reopens whichever axis it touches, and that is what turns a change
note into a delta-qualification.

Stdlib only, offline, deterministic.
"""

import math

AXES = ("power-handling-capability", "gas-discharge-behaviour")

# Evidence routes. A route that is not standalone cannot close an axis on its
# own; it needs a recorded correlation or heritage-delta behind it.
QUALIFICATION_EVIDENCE = {
    "dedicated-qualification-model": {"strength": 3, "standalone": True},
    "protoflight-campaign": {"strength": 2, "standalone": True},
    "validated-analysis": {"strength": 1, "standalone": False},
    "heritage-similarity": {"strength": 0, "standalone": False},
}

EVIDENCE_ALIASES = {
    "qualification-model": "dedicated-qualification-model",
    "dedicated-campaign": "dedicated-qualification-model",
    "protoflight": "protoflight-campaign",
    "correlated-analysis": "validated-analysis",
    "heritage": "heritage-similarity",
}

# Which axis each recognized design change reopens.
CHANGE_IMPACT = {
    "discharge-gap-geometry": ("gas-discharge-behaviour",),
    "surface-treatment": ("gas-discharge-behaviour",),
    "venting-path": ("gas-discharge-behaviour",),
    "dielectric-material": ("power-handling-capability", "gas-discharge-behaviour"),
    "operating-power-increase": (
        "power-handling-capability",
        "gas-discharge-behaviour",
    ),
    "connector-interface": (
        "power-handling-capability",
        "gas-discharge-behaviour",
    ),
    "conductor-plating": ("power-handling-capability",),
    "thermal-interface": ("power-handling-capability",),
    "external-marking": (),
    "documentation-only": (),
}

DEFAULT_SETTLING_MULTIPLE = 5.0
DEFAULT_MINIMUM_DWELL_S = 300.0

# Representation tolerance only. It absorbs floating-point round-off on an
# exactly-compliant comparison; it never relaxes an engineering limit.
COMPARISON_TOLERANCE = 1e-9


def _meets(value, limit):
    """True when value is at or above limit, ULP noise absorbed."""
    if value >= limit:
        return True
    return math.isclose(value, limit, rel_tol=1e-12, abs_tol=COMPARISON_TOLERANCE)


def _validate_band(name, band):
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair" % name)
    if band[0] <= 0.0:
        raise ValueError("%s low edge must be > 0" % name)
    if band[1] < band[0]:
        raise ValueError("%s high edge must be >= low edge" % name)
    return float(band[0]), float(band[1])


def categorize_qualification_evidence(kind):
    """Resolve a declared evidence route to its canonical category."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("evidence kind must be a non-empty string")
    key = kind.strip().lower()
    key = EVIDENCE_ALIASES.get(key, key)
    if key not in QUALIFICATION_EVIDENCE:
        raise ValueError("unrecognized qualification evidence %r" % (kind,))
    return key


def evidence_profile(kind):
    """Return a copy of the profile attached to an evidence route."""
    return dict(QUALIFICATION_EVIDENCE[categorize_qualification_evidence(kind)])


def qualification_power_level_w(max_operating_power_w, overstress_db):
    """Level the qualification has to reach above maximum operating power."""
    if max_operating_power_w <= 0.0:
        raise ValueError("max_operating_power_w must be > 0")
    if overstress_db < 0.0:
        raise ValueError("overstress_db must be >= 0")
    return max_operating_power_w * 10.0 ** (overstress_db / 10.0)


def qualified_operating_envelope_w(demonstrated_level_w, overstress_db):
    """Maximum operating power a demonstrated level actually supports."""
    if demonstrated_level_w <= 0.0:
        raise ValueError("demonstrated_level_w must be > 0")
    if overstress_db < 0.0:
        raise ValueError("overstress_db must be >= 0")
    return demonstrated_level_w / 10.0 ** (overstress_db / 10.0)


def required_dwell_s(
    thermal_time_constant_s,
    settling_multiple=DEFAULT_SETTLING_MULTIPLE,
    minimum_dwell_s=DEFAULT_MINIMUM_DWELL_S,
):
    """Dwell needed to reach thermal steady state, floored by a minimum."""
    if thermal_time_constant_s <= 0.0:
        raise ValueError("thermal_time_constant_s must be > 0")
    if settling_multiple <= 0.0:
        raise ValueError("settling_multiple must be > 0")
    if minimum_dwell_s < 0.0:
        raise ValueError("minimum_dwell_s must be >= 0")
    return max(thermal_time_constant_s * settling_multiple, minimum_dwell_s)


def _evidence_findings(axis, record):
    """Shared evidence check: route resolves, and a weak route is supported."""
    category = categorize_qualification_evidence(record["evidence"])
    profile = QUALIFICATION_EVIDENCE[category]
    findings = []
    if not profile["standalone"] and not record.get("supporting_reference"):
        findings.append(
            "%s: route %s cannot close the axis alone and carries no supporting evidence"
            % (axis, category)
        )
    return category, profile, findings


def evaluate_power_handling_axis(record, required_level_w):
    """Close the power-handling-capability axis, or say why it stays open."""
    axis = "power-handling-capability"
    for key in ("evidence", "hardware_standard", "demonstrated_level_w", "dwell_s"):
        if key not in record:
            raise ValueError("%s record missing required key %r" % (axis, key))
    if record["demonstrated_level_w"] <= 0.0:
        raise ValueError("demonstrated_level_w must be > 0")
    if record["dwell_s"] <= 0.0:
        raise ValueError("dwell_s must be > 0")
    category, profile, findings = _evidence_findings(axis, record)

    if not _meets(record["demonstrated_level_w"], required_level_w):
        findings.append(
            "%s: demonstrated %.1f W is below the required qualification level %.1f W"
            % (axis, record["demonstrated_level_w"], required_level_w)
        )
    floor_dwell = record.get("minimum_dwell_s", DEFAULT_MINIMUM_DWELL_S)
    if "thermal_time_constant_s" in record:
        needed_dwell = required_dwell_s(
            record["thermal_time_constant_s"],
            record.get("settling_multiple", DEFAULT_SETTLING_MULTIPLE),
            floor_dwell,
        )
    else:
        if floor_dwell < 0.0:
            raise ValueError("minimum_dwell_s must be >= 0")
        needed_dwell = floor_dwell
        findings.append(
            "%s: no thermal time constant on record; only the floor dwell could be checked"
            % axis
        )
    if not _meets(record["dwell_s"], needed_dwell):
        findings.append(
            "%s: dwell of %.0f s stops short of the %.0f s needed for thermal steady state"
            % (axis, record["dwell_s"], needed_dwell)
        )
    hot_case = record.get("hot_case_temperature_c")
    required_hot_case = record.get("required_hot_case_temperature_c")
    if required_hot_case is not None:
        if hot_case is None:
            findings.append("%s: no hot-case temperature on record" % axis)
        elif not _meets(hot_case, required_hot_case):
            findings.append(
                "%s: run at %.1f C, below the %.1f C hot case the item will see"
                % (axis, hot_case, required_hot_case)
            )
    return {
        "axis": axis,
        "evidence": category,
        "evidence_strength": profile["strength"],
        "hardware_standard": record["hardware_standard"],
        "required_level_w": required_level_w,
        "demonstrated_level_w": record["demonstrated_level_w"],
        "required_dwell_s": needed_dwell,
        "findings": findings,
        "closed": not findings,
    }


def evaluate_gas_discharge_axis(record, required_level_w):
    """Close the gas-discharge-behaviour axis, or say why it stays open."""
    axis = "gas-discharge-behaviour"
    for key in (
        "evidence",
        "hardware_standard",
        "demonstrated_level_w",
        "swept_band_pa",
        "critical_band_pa",
    ):
        if key not in record:
            raise ValueError("%s record missing required key %r" % (axis, key))
    if record["demonstrated_level_w"] <= 0.0:
        raise ValueError("demonstrated_level_w must be > 0")
    category, profile, findings = _evidence_findings(axis, record)

    if not _meets(record["demonstrated_level_w"], required_level_w):
        findings.append(
            "%s: demonstrated %.1f W is below the required qualification level %.1f W"
            % (axis, record["demonstrated_level_w"], required_level_w)
        )
    swept_low, swept_high = _validate_band("swept_band_pa", record["swept_band_pa"])
    critical_low, critical_high = _validate_band(
        "critical_band_pa", record["critical_band_pa"]
    )
    uncovered = []
    if swept_low > critical_low:
        uncovered.append((critical_low, min(swept_low, critical_high)))
    if swept_high < critical_high:
        uncovered.append((max(swept_high, critical_low), critical_high))
    if uncovered:
        findings.append(
            "%s: pressure sweep leaves %d critical sub-band(s) unexercised"
            % (axis, len(uncovered))
        )
    step_dwell = record.get("dwell_per_step_s")
    minimum_step_dwell = record.get("minimum_step_dwell_s")
    if minimum_step_dwell is not None:
        if step_dwell is None:
            findings.append("%s: no dwell per pressure step on record" % axis)
        elif not _meets(step_dwell, minimum_step_dwell):
            findings.append(
                "%s: %.0f s per pressure step is under the %.0f s needed to let onset develop"
                % (axis, step_dwell, minimum_step_dwell)
            )
    return {
        "axis": axis,
        "evidence": category,
        "evidence_strength": profile["strength"],
        "hardware_standard": record["hardware_standard"],
        "required_level_w": required_level_w,
        "demonstrated_level_w": record["demonstrated_level_w"],
        "uncovered_bands": uncovered,
        "findings": findings,
        "closed": not findings,
    }


def cross_axis_configuration_check(power_result, discharge_result, configuration_link=None):
    """Confirm the two axes closed on one hardware standard, or a linked pair."""
    findings = []
    same = power_result["hardware_standard"] == discharge_result["hardware_standard"]
    if not same and not configuration_link:
        findings.append(
            "axes closed on different hardware standards (%s and %s) with no configuration link on record"
            % (power_result["hardware_standard"], discharge_result["hardware_standard"])
        )
    return {"single_standard": same, "findings": findings}


def delta_qualification_required(changes):
    """Decide which axes a set of design changes reopens."""
    if not isinstance(changes, (list, tuple)):
        raise ValueError("changes must be a sequence")
    reopened = []
    reasons = []
    for change in changes:
        if not isinstance(change, str) or not change.strip():
            raise ValueError("each change must be a non-empty string")
        key = change.strip().lower()
        if key not in CHANGE_IMPACT:
            raise ValueError("unrecognized design change %r" % (change,))
        for axis in CHANGE_IMPACT[key]:
            if axis not in reopened:
                reopened.append(axis)
            reasons.append("%s reopens %s" % (key, axis))
    return {
        "required": bool(reopened),
        "axes": [axis for axis in AXES if axis in reopened],
        "reasons": reasons,
    }


def assess_qualification_programme(programme):
    """Full clause 7.3.4 verdict for one qualification approach."""
    for key in ("max_operating_power_w", "overstress_db", "axes"):
        if key not in programme:
            raise ValueError("programme missing required key %r" % (key,))
    axes = programme["axes"]
    if not isinstance(axes, dict):
        raise ValueError("programme axes must be a mapping")
    for name in axes:
        if name not in AXES:
            raise ValueError("unrecognized qualification axis %r" % (name,))

    required_level = qualification_power_level_w(
        programme["max_operating_power_w"], programme["overstress_db"]
    )
    findings = []
    results = {}
    for axis in AXES:
        if axis not in axes:
            findings.append("%s: axis not addressed by the qualification approach" % axis)
    if "power-handling-capability" in axes:
        results["power-handling-capability"] = evaluate_power_handling_axis(
            axes["power-handling-capability"], required_level
        )
    if "gas-discharge-behaviour" in axes:
        results["gas-discharge-behaviour"] = evaluate_gas_discharge_axis(
            axes["gas-discharge-behaviour"], required_level
        )
    for result in results.values():
        findings.extend(result["findings"])

    configuration = None
    if len(results) == len(AXES):
        configuration = cross_axis_configuration_check(
            results["power-handling-capability"],
            results["gas-discharge-behaviour"],
            programme.get("configuration_link"),
        )
        findings.extend(configuration["findings"])

    delta = delta_qualification_required(programme.get("changes", []))
    for reason in delta["reasons"]:
        findings.append("delta-qualification: %s" % reason)

    envelope = min(
        (
            qualified_operating_envelope_w(
                result["demonstrated_level_w"], programme["overstress_db"]
            )
            for result in results.values()
        ),
        default=0.0,
    )
    return {
        "id": programme.get("id", "unnamed-programme"),
        "required_level_w": required_level,
        "qualified_operating_envelope_w": envelope,
        "axes": results,
        "configuration": configuration,
        "delta": delta,
        "findings": findings,
        "qualified": not findings,
    }
