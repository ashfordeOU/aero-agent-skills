#!/usr/bin/env python3
"""Design, choice, purchase and use of a class 1 microwave monolithic circuit.

Anchor: ECSS-Q-ST-60C clause 4.6.5 (design, selection, procurement and use of
microwave monolithic integrated circuits in class 1 equipment). Paraphrased
into an implementable procedure; no standard text is reproduced.

A microwave monolithic integrated circuit is bought as a component and used as
a circuit. The two halves do not separate: a part that is perfectly procured is
still unusable if the application runs it outside the band it was characterized
over, above the drive level it was rated at, or hotter than the channel
temperature the reliability estimate assumed. This module decides both halves
together -- what the source category and delivery form oblige, and what the
application does to the part once it is fitted.

Procedure implemented here
--------------------------
1. Validate the selection case: the foundry process, the source category, the
   delivery form, the characterized and operating frequency bands, the thermal
   path and the radio-frequency drive.
2. Check the operating band sits inside the band the part was characterized
   over, and report the extent that falls outside.
3. Resolve the channel temperature from the baseplate, the junction-to-case
   thermal resistance and the dissipated power, and compare it with the class 1
   derating limit.
4. Compare the applied drive with the rated drive against the derating limit.
5. Assemble the activities the source category and delivery form oblige, add
   the handling controls the electrostatic sensitivity demands, and return a
   usability verdict with every finding.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "FOUNDRY_PROCESSES",
    "SOURCE_CATEGORIES",
    "DELIVERY_FORMS",
    "BASE_ACTIVITIES_BY_SOURCE",
    "BARE_DIE_ACTIVITIES",
    "ESD_HANDLING_CATEGORIES",
    "DEFAULT_MMIC_POLICY",
    "USABLE_AS_PROCURED",
    "USABLE_WITH_ACTIVITIES",
    "NOT_USABLE",
    "BOLTZMANN_EV_PER_K",
    "validate_mmic_policy",
    "validate_mmic_case",
    "band_coverage_fraction",
    "out_of_band_span_ghz",
    "channel_temperature_c",
    "channel_temperature_margin_c",
    "rf_drive_ratio",
    "thermal_acceleration_factor",
    "esd_handling_category",
    "required_activities",
    "derating_findings",
    "assess_mmic_selection",
]

# The process decides what the die is made of, and with it the radiation
# behaviour, the thermal path and the screening that is meaningful.
FOUNDRY_PROCESSES = ("gaas-phemt", "gan-hemt", "sige-bicmos", "inp-hbt")

# Where the part comes from, best to weakest. The three differ in what has
# already been demonstrated by somebody other than the project.
SOURCE_CATEGORIES = (
    "space-qualified-catalogue",
    "qualified-foundry-custom",
    "commercial-foundry",
)

DELIVERY_FORMS = ("hermetic-packaged", "bare-die")

BASE_ACTIVITIES_BY_SOURCE = {
    "space-qualified-catalogue": ("lot-acceptance-testing",),
    "qualified-foundry-custom": (
        "foundry-process-assessment",
        "evaluation-programme",
        "lot-acceptance-testing",
        "destructive-physical-analysis",
    ),
    "commercial-foundry": (
        "foundry-process-assessment",
        "evaluation-programme",
        "radiation-evaluation",
        "upscreening-programme",
        "lot-acceptance-testing",
        "destructive-physical-analysis",
    ),
}

# A die delivered without its package moves the hermeticity and the handling
# risk onto the equipment builder.
BARE_DIE_ACTIVITIES = (
    "bare-die-visual-inspection",
    "die-handling-and-electrostatic-controls",
    "die-attach-and-interconnect-process-qualification",
)

# Human body model thresholds, in volts, in ascending order; the first band the
# withstand voltage falls below names the handling category.
ESD_HANDLING_CATEGORIES = (
    (125.0, "esd-sensitivity-0a"),
    (250.0, "esd-sensitivity-0b"),
    (500.0, "esd-sensitivity-1a"),
    (1000.0, "esd-sensitivity-1b"),
    (2000.0, "esd-sensitivity-2"),
    (4000.0, "esd-sensitivity-3a"),
    (float("inf"), "esd-sensitivity-3b-or-above"),
)

DEFAULT_MMIC_POLICY = {
    # Channel temperature the class 1 derating rules cap the part at.
    "max_channel_temperature_c": 110.0,
    # Share of the rated drive the application may apply.
    "max_rf_drive_ratio": 0.8,
    # Share of the operating band that must sit inside the characterized band.
    "min_band_coverage": 1.0,
    # Whether a commercial foundry part may be taken to class 1 at all.
    "allow_commercial_foundry": True,
    # Electrostatic withstand below which extra handling controls attach.
    "esd_control_threshold_v": 500.0,
}

# Boltzmann constant expressed in electronvolt per kelvin.
BOLTZMANN_EV_PER_K = 8.617333262e-5
_ABSOLUTE_ZERO_C = -273.15

USABLE_AS_PROCURED = "mmic-usable-as-procured"
USABLE_WITH_ACTIVITIES = "mmic-usable-with-additional-activities"
NOT_USABLE = "mmic-not-usable-at-class-1"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A channel temperature and a drive ratio are both computed, so a case
    sitting exactly on its limit can land a few units in the last place above
    it. The limit is never raised; only the comparison tolerates the
    representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_mmic_policy(policy=None):
    """Return a complete selection policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_MMIC_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("mmic policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_MMIC_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_MMIC_POLICY:
            raise ValueError("unknown mmic policy key %r" % (key,))
        merged[key] = value
    limit = _require_number(
        "max_channel_temperature_c", merged["max_channel_temperature_c"]
    )
    if limit <= _ABSOLUTE_ZERO_C:
        raise ValueError("max_channel_temperature_c must be above absolute zero")
    ratio = _require_positive("max_rf_drive_ratio", merged["max_rf_drive_ratio"])
    if ratio > 1.0:
        raise ValueError("max_rf_drive_ratio must not exceed 1.0, got %r" % (ratio,))
    coverage = _require_positive("min_band_coverage", merged["min_band_coverage"])
    if coverage > 1.0:
        raise ValueError("min_band_coverage must not exceed 1.0, got %r" % (coverage,))
    _require_positive("esd_control_threshold_v", merged["esd_control_threshold_v"])
    if not isinstance(merged["allow_commercial_foundry"], bool):
        raise ValueError("allow_commercial_foundry must be a boolean")
    return merged


def _require_band(name, low, high):
    low = _require_positive("%s_low_ghz" % name, low)
    high = _require_positive("%s_high_ghz" % name, high)
    if high <= low:
        raise ValueError(
            "%s band is inverted or empty: %g GHz to %g GHz" % (name, low, high)
        )
    return low, high


def band_coverage_fraction(
    operating_low_ghz, operating_high_ghz, characterized_low_ghz, characterized_high_ghz
):
    """Share of the operating band that the characterized band covers."""
    op_low, op_high = _require_band("operating", operating_low_ghz, operating_high_ghz)
    ch_low, ch_high = _require_band(
        "characterized", characterized_low_ghz, characterized_high_ghz
    )
    overlap = min(op_high, ch_high) - max(op_low, ch_low)
    if overlap <= 0.0:
        return 0.0
    return overlap / (op_high - op_low)


def out_of_band_span_ghz(
    operating_low_ghz, operating_high_ghz, characterized_low_ghz, characterized_high_ghz
):
    """Width of the operating band that falls outside the characterized band."""
    op_low, op_high = _require_band("operating", operating_low_ghz, operating_high_ghz)
    ch_low, ch_high = _require_band(
        "characterized", characterized_low_ghz, characterized_high_ghz
    )
    overlap = min(op_high, ch_high) - max(op_low, ch_low)
    if overlap <= 0.0:
        return op_high - op_low
    return (op_high - op_low) - overlap


def channel_temperature_c(
    baseplate_temperature_c, thermal_resistance_c_per_w, dissipated_power_w
):
    """Channel temperature reached by the dissipation over the thermal path."""
    base = _require_number("baseplate_temperature_c", baseplate_temperature_c)
    if base <= _ABSOLUTE_ZERO_C:
        raise ValueError("baseplate_temperature_c must be above absolute zero")
    resistance = _require_non_negative(
        "thermal_resistance_c_per_w", thermal_resistance_c_per_w
    )
    power = _require_non_negative("dissipated_power_w", dissipated_power_w)
    return base + resistance * power


def channel_temperature_margin_c(channel_c, limit_c):
    """How far the channel sits below its derating limit; negative is a breach."""
    channel = _require_number("channel_c", channel_c)
    limit = _require_number("limit_c", limit_c)
    return limit - channel


def rf_drive_ratio(applied_drive_w, rated_drive_w):
    """Applied radio-frequency drive as a share of the rated drive."""
    applied = _require_non_negative("applied_drive_w", applied_drive_w)
    rated = _require_positive("rated_drive_w", rated_drive_w)
    return applied / rated


def thermal_acceleration_factor(
    channel_temperature_celsius, reference_temperature_celsius, activation_energy_ev
):
    """Arrhenius acceleration of the degradation rate at the channel temperature.

    Returns exactly one at the reference temperature, which is the only value
    this function asserts against a bound; every other comparison is made
    between values that differ by far more than the representation error.
    """
    channel_k = (
        _require_number("channel_temperature_celsius", channel_temperature_celsius)
        - _ABSOLUTE_ZERO_C
    )
    reference_k = (
        _require_number("reference_temperature_celsius", reference_temperature_celsius)
        - _ABSOLUTE_ZERO_C
    )
    if channel_k <= 0.0 or reference_k <= 0.0:
        raise ValueError("temperatures must be above absolute zero")
    energy = _require_positive("activation_energy_ev", activation_energy_ev)
    exponent = (energy / BOLTZMANN_EV_PER_K) * (1.0 / reference_k - 1.0 / channel_k)
    return math.exp(exponent)


def esd_handling_category(withstand_voltage_v):
    """Handling category named by the human body model withstand voltage."""
    voltage = _require_positive("withstand_voltage_v", withstand_voltage_v)
    for threshold, name in ESD_HANDLING_CATEGORIES:
        if voltage < threshold:
            return name
    return ESD_HANDLING_CATEGORIES[-1][1]


def required_activities(source_category, delivery_form, withstand_voltage_v=None, policy=None):
    """Activities the source, the delivery form and the sensitivity oblige."""
    _require_choice("source_category", source_category, SOURCE_CATEGORIES)
    _require_choice("delivery_form", delivery_form, DELIVERY_FORMS)
    resolved = validate_mmic_policy(policy)
    activities = list(BASE_ACTIVITIES_BY_SOURCE[source_category])
    if delivery_form == "bare-die":
        for activity in BARE_DIE_ACTIVITIES:
            if activity not in activities:
                activities.append(activity)
    if withstand_voltage_v is not None:
        voltage = _require_positive("withstand_voltage_v", withstand_voltage_v)
        if voltage < resolved["esd_control_threshold_v"]:
            activity = "reinforced-electrostatic-discharge-controls"
            if activity not in activities:
                activities.append(activity)
    return tuple(activities)


def derating_findings(case, policy=None):
    """Band, thermal and drive findings the application raises against the part."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    resolved = validate_mmic_policy(policy)
    findings = []

    coverage = band_coverage_fraction(
        case.get("operating_low_ghz"),
        case.get("operating_high_ghz"),
        case.get("characterized_low_ghz"),
        case.get("characterized_high_ghz"),
    )
    outside = out_of_band_span_ghz(
        case.get("operating_low_ghz"),
        case.get("operating_high_ghz"),
        case.get("characterized_low_ghz"),
        case.get("characterized_high_ghz"),
    )
    band_ok = _at_least(coverage, resolved["min_band_coverage"])
    if not band_ok:
        findings.append(
            "the application runs %.3f GHz outside the characterized band" % outside
        )

    channel = channel_temperature_c(
        case.get("baseplate_temperature_c"),
        case.get("thermal_resistance_c_per_w"),
        case.get("dissipated_power_w"),
    )
    margin = channel_temperature_margin_c(
        channel, resolved["max_channel_temperature_c"]
    )
    thermal_ok = _at_most(channel, resolved["max_channel_temperature_c"])
    if not thermal_ok:
        findings.append(
            "the channel reaches %.2f C against a %.2f C derating limit"
            % (channel, resolved["max_channel_temperature_c"])
        )

    ratio = rf_drive_ratio(case.get("applied_drive_w"), case.get("rated_drive_w"))
    drive_ok = _at_most(ratio, resolved["max_rf_drive_ratio"])
    if not drive_ok:
        findings.append(
            "the applied drive is %.3f of rated against a %.3f derating limit"
            % (ratio, resolved["max_rf_drive_ratio"])
        )

    return {
        "band_coverage": coverage,
        "out_of_band_span_ghz": outside,
        "band_ok": band_ok,
        "channel_temperature_c": channel,
        "channel_temperature_margin_c": margin,
        "thermal_ok": thermal_ok,
        "rf_drive_ratio": ratio,
        "drive_ok": drive_ok,
        "findings": findings,
    }


def validate_mmic_case(case):
    """Check a selection case names every field the decision needs."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    _require_choice("foundry_process", case.get("foundry_process"), FOUNDRY_PROCESSES)
    _require_choice("source_category", case.get("source_category"), SOURCE_CATEGORIES)
    _require_choice("delivery_form", case.get("delivery_form"), DELIVERY_FORMS)
    for field in (
        "operating_low_ghz",
        "operating_high_ghz",
        "characterized_low_ghz",
        "characterized_high_ghz",
        "baseplate_temperature_c",
        "thermal_resistance_c_per_w",
        "dissipated_power_w",
        "applied_drive_w",
        "rated_drive_w",
    ):
        if case.get(field) is None:
            raise ValueError("case is missing %s" % field)
    return case


def assess_mmic_selection(case, policy=None):
    """Full clause 4.6.5 selection decision with activities and a verdict."""
    validate_mmic_case(case)
    resolved = validate_mmic_policy(policy)
    derating = derating_findings(case, resolved)
    findings = list(derating["findings"])

    source_category = case["source_category"]
    if source_category == "commercial-foundry" and not resolved[
        "allow_commercial_foundry"
    ]:
        findings.append(
            "the project policy does not admit a commercial foundry part at class 1"
        )
        source_admissible = False
    else:
        source_admissible = True

    withstand = case.get("esd_withstand_voltage_v")
    sensitivity = (
        esd_handling_category(withstand) if withstand is not None else None
    )
    activities = required_activities(
        source_category, case["delivery_form"], withstand, resolved
    )
    extra = tuple(
        activity
        for activity in activities
        if activity not in BASE_ACTIVITIES_BY_SOURCE["space-qualified-catalogue"]
    )

    if not (
        derating["band_ok"]
        and derating["thermal_ok"]
        and derating["drive_ok"]
        and source_admissible
    ):
        verdict = NOT_USABLE
    elif extra:
        verdict = USABLE_WITH_ACTIVITIES
    else:
        verdict = USABLE_AS_PROCURED

    return {
        "verdict": verdict,
        "usable": verdict != NOT_USABLE,
        "foundry_process": case["foundry_process"],
        "source_category": source_category,
        "delivery_form": case["delivery_form"],
        "band_coverage": derating["band_coverage"],
        "out_of_band_span_ghz": derating["out_of_band_span_ghz"],
        "channel_temperature_c": derating["channel_temperature_c"],
        "channel_temperature_margin_c": derating["channel_temperature_margin_c"],
        "rf_drive_ratio": derating["rf_drive_ratio"],
        "esd_handling_category": sensitivity,
        "required_activities": activities,
        "activities_beyond_catalogue": extra,
        "findings": findings,
    }
