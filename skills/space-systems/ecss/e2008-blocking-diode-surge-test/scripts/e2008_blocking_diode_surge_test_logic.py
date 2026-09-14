#!/usr/bin/env python3
"""Short high-current pulses driven through a planar blocking diode.

Anchor: ECSS-E-ST-20-08C clause 12.6.17. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A surge test drives a small number of SHORT pulses whose PEAK current sits
far above the current the device is rated to carry continuously, and asks
whether the part is still a diode afterwards. Two things have to be decided
and they are not the same question:

    profile     is the pulse train a surge at all, and does it stress the
                part in the window worth testing -- a peak that never clears
                the rated average by a real multiple proves nothing, a pulse
                long enough to be an overload is a different test entirely,
                an action integral far below the device withstand demonstrates
                nothing, one above it destroys parts by design, the junction
                has to keep some margin to its ceiling, and the interval
                between pulses has to let it cool back down first
    specimen    did this individual device survive -- graded on the movement
                between the pre-surge and post-surge readings, on the
                post-surge readings against their own absolute limits, and on
                what the closing inspection could see

The pulse action integral is the quantity that actually does the damage, and
it depends on the waveform shape, not on the peak alone. A rectangular pulse
and a half-sine pulse of the same peak and the same width do not carry the
same energy, so the shape factor is applied before anything is compared.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PULSE_WAVEFORMS = (
    "rectangular",
    "half-sine",
    "triangular",
    "exponential-decay",
)

# Shape factor k in I2t = k * Ipeak^2 * duration, for a pulse of the named
# shape and the stated total width. Declared as exact rationals so the value
# is identical on every platform.
WAVEFORM_ACTION_FACTOR = {
    "rectangular": 1.0,
    "half-sine": 0.5,
    "triangular": 1.0 / 3.0,
    "exponential-decay": 1.0 / 6.0,
}

# Mean current over the pulse as a fraction of the peak, used to turn the
# pulse into dissipated energy at the forward drop.
WAVEFORM_MEAN_FACTOR = {
    "rectangular": 1.0,
    "half-sine": 2.0 / math.pi,
    "triangular": 0.5,
    "exponential-decay": 1.0 / 3.0,
}

GRADED_PARAMETERS = (
    "forward-voltage-drop",
    "reverse-leakage-current",
)

DEGRADATION_SENSE = {
    "forward-voltage-drop": "increase",
    "reverse-leakage-current": "increase",
}

OBSERVABLE_CONDITIONS = (
    "diode-open-circuit",
    "diode-short-circuit",
    "bond-wire-lifted",
    "die-crack",
    "metallisation-melt",
    "package-discolouration",
)

PROFILE_ADEQUATE = "surge-profile-adequate"
PROFILE_INADEQUATE = "surge-profile-inadequate"

SPECIMEN_WITHSTOOD = "blocking-diode-withstood-surge"
SPECIMEN_FAILED = "blocking-diode-failed-surge"
SPECIMEN_NOT_EVALUATED = "blocking-diode-not-evaluated"

SURGE_TEST_PASSED = "surge-test-passed"
SURGE_TEST_FAILED = "surge-test-failed"
SURGE_TEST_NOT_EVALUABLE = "surge-test-not-evaluable"

DEFICIENCY_PEAK_TOO_LOW = "peak-below-rated-average-multiple"
DEFICIENCY_PULSE_TOO_LONG = "pulse-longer-than-surge-duration-limit"
DEFICIENCY_UNDER_STRESSED = "action-integral-below-demonstration-fraction"
DEFICIENCY_OVER_STRESSED = "action-integral-beyond-withstand-allowance"
DEFICIENCY_NO_HEADROOM = "junction-temperature-headroom-exceeded"
DEFICIENCY_NO_RECOVERY = "inter-pulse-recovery-too-short"
DEFICIENCY_NO_READOUT = "no-post-surge-readout-scheduled"

DEFAULT_DEVICE_RATING = {
    "rated_average_current_a": 2.0,
    "i2t_withstand_a2s": 5.0,
    "forward_voltage_drop_v": 0.90,
    "max_junction_temperature_c": 175.0,
    "thermal_capacity_j_per_k": 0.0015,
}

DEFAULT_SURGE_PROFILE = {
    "peak_current_a": 30.0,
    "pulse_duration_s": 0.010,
    "waveform": "half-sine",
    "pulse_count": 3,
    "inter_pulse_interval_s": 90.0,
    "initial_junction_temperature_c": 25.0,
    "post_surge_readout_scheduled": True,
}

DEFAULT_SURGE_CRITERIA = {
    "specification_reference": "planar-blocking-diode-source-control-drawing-issue-c",
    "min_peak_to_rated_multiple": 5.0,
    "max_pulse_duration_s": 0.020,
    "min_demonstrated_withstand_fraction": 0.80,
    "max_withstand_overstress_fraction": 1.00,
    "min_junction_temperature_margin_k": 10.0,
    "min_inter_pulse_interval_s": 60.0,
    "post_surge_readout_required": True,
    "post_surge_drift_allowances": {
        "forward-voltage-drop": 0.10,
        "reverse-leakage-current": 1.00,
    },
    "post_surge_limits": {
        "forward-voltage-drop": 1.10,
        "reverse-leakage-current": 5.0e-6,
    },
    "disqualifying_conditions": (
        "diode-open-circuit",
        "diode-short-circuit",
        "bond-wire-lifted",
        "die-crack",
        "metallisation-melt",
    ),
    "max_failed_fraction": 0.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _within(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_positive(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be a finite positive value, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(
            "%s must be a finite non-negative value, got %r" % (name, value)
        )
    return value


def _require_fraction(name, value):
    value = _require_non_negative(name, value)
    if value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return value


def _require_temperature(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < -273.15:
        raise ValueError("%s must be a finite temperature, got %r" % (name, value))
    return value


def pulse_waveforms():
    """The pulse shapes a surge profile may declare."""
    return tuple(PULSE_WAVEFORMS)


def graded_parameters():
    """The electrical parameters a surged device is graded on."""
    return tuple(GRADED_PARAMETERS)


def observable_conditions():
    """The conditions the post-surge inspection can raise against a device."""
    return tuple(OBSERVABLE_CONDITIONS)


def waveform_action_factor(waveform):
    """Shape factor k such that the pulse action integral is k * Ipk^2 * t."""
    waveform = _require_text("waveform", waveform)
    if waveform not in WAVEFORM_ACTION_FACTOR:
        raise ValueError("unknown pulse waveform %s" % waveform)
    return WAVEFORM_ACTION_FACTOR[waveform]


def waveform_mean_factor(waveform):
    """Mean current over the pulse as a fraction of its peak."""
    waveform = _require_text("waveform", waveform)
    if waveform not in WAVEFORM_MEAN_FACTOR:
        raise ValueError("unknown pulse waveform %s" % waveform)
    return WAVEFORM_MEAN_FACTOR[waveform]


def degradation_sense(parameter):
    """The direction this parameter has to move in before it counts as decay."""
    parameter = _require_text("parameter", parameter)
    if parameter not in DEGRADATION_SENSE:
        raise ValueError("unknown graded parameter %s" % parameter)
    return DEGRADATION_SENSE[parameter]


def surge_ratio(peak_current_a, rated_average_current_a):
    """How many times the rated average current the pulse peak reaches."""
    peak = _require_positive("peak_current_a", peak_current_a)
    rated = _require_positive("rated_average_current_a", rated_average_current_a)
    return peak / rated


def pulse_action_integral(peak_current_a, pulse_duration_s, waveform):
    """The energy-bearing quantity of one pulse, shape taken into account."""
    peak = _require_positive("peak_current_a", peak_current_a)
    duration = _require_positive("pulse_duration_s", pulse_duration_s)
    return waveform_action_factor(waveform) * peak * peak * duration


def train_action_integral(peak_current_a, pulse_duration_s, waveform, pulse_count):
    """The action integral the whole pulse train delivers."""
    count = _require_count("pulse_count", pulse_count)
    return pulse_action_integral(peak_current_a, pulse_duration_s, waveform) * count


def junction_temperature_rise(
    peak_current_a,
    pulse_duration_s,
    waveform,
    forward_voltage_drop_v,
    thermal_capacity_j_per_k,
):
    """Adiabatic junction rise one pulse produces at the forward drop."""
    peak = _require_positive("peak_current_a", peak_current_a)
    duration = _require_positive("pulse_duration_s", pulse_duration_s)
    drop = _require_positive("forward_voltage_drop_v", forward_voltage_drop_v)
    capacity = _require_positive(
        "thermal_capacity_j_per_k", thermal_capacity_j_per_k
    )
    energy = drop * waveform_mean_factor(waveform) * peak * duration
    return energy / capacity


def validate_device_rating(rating):
    """Check a declared device rating can bound anything at all."""
    if not isinstance(rating, dict):
        raise ValueError("rating must be a mapping, got %r" % (rating,))
    _require_positive("rated_average_current_a", rating.get("rated_average_current_a"))
    _require_positive("i2t_withstand_a2s", rating.get("i2t_withstand_a2s"))
    _require_positive("forward_voltage_drop_v", rating.get("forward_voltage_drop_v"))
    _require_temperature(
        "max_junction_temperature_c", rating.get("max_junction_temperature_c")
    )
    _require_positive(
        "thermal_capacity_j_per_k", rating.get("thermal_capacity_j_per_k")
    )
    return rating


def validate_surge_profile(profile):
    """Check a declared pulse train is described well enough to be judged."""
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping, got %r" % (profile,))
    _require_positive("peak_current_a", profile.get("peak_current_a"))
    _require_positive("pulse_duration_s", profile.get("pulse_duration_s"))
    waveform_action_factor(profile.get("waveform"))
    _require_count("pulse_count", profile.get("pulse_count"))
    _require_non_negative(
        "inter_pulse_interval_s", profile.get("inter_pulse_interval_s")
    )
    _require_temperature(
        "initial_junction_temperature_c",
        profile.get("initial_junction_temperature_c"),
    )
    scheduled = profile.get("post_surge_readout_scheduled")
    if not isinstance(scheduled, bool):
        raise ValueError(
            "post_surge_readout_scheduled must be a boolean, got %r" % (scheduled,)
        )
    return profile


def validate_surge_criteria(criteria):
    """Check a declared criteria set can sentence a surge test."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_text("specification_reference", criteria.get("specification_reference"))
    _require_positive(
        "min_peak_to_rated_multiple", criteria.get("min_peak_to_rated_multiple")
    )
    _require_positive("max_pulse_duration_s", criteria.get("max_pulse_duration_s"))
    low = _require_fraction(
        "min_demonstrated_withstand_fraction",
        criteria.get("min_demonstrated_withstand_fraction"),
    )
    high = _require_positive(
        "max_withstand_overstress_fraction",
        criteria.get("max_withstand_overstress_fraction"),
    )
    if low > high:
        raise ValueError(
            "the demonstration floor %r sits above the overstress ceiling %r, "
            "so no pulse train could ever be adequate" % (low, high)
        )
    _require_non_negative(
        "min_junction_temperature_margin_k",
        criteria.get("min_junction_temperature_margin_k"),
    )
    _require_non_negative(
        "min_inter_pulse_interval_s", criteria.get("min_inter_pulse_interval_s")
    )
    if not isinstance(criteria.get("post_surge_readout_required"), bool):
        raise ValueError("post_surge_readout_required must be a boolean")

    allowances = criteria.get("post_surge_drift_allowances")
    if not isinstance(allowances, dict) or not allowances:
        raise ValueError("post_surge_drift_allowances must be a non-empty mapping")
    for name, allowance in allowances.items():
        name = _require_text("post_surge_drift_allowances key", name)
        if name not in GRADED_PARAMETERS:
            raise ValueError("drift allowance names an unknown parameter %s" % name)
        _require_non_negative("drift allowance for %s" % name, allowance)

    limits = criteria.get("post_surge_limits", {})
    if not isinstance(limits, dict):
        raise ValueError("post_surge_limits must be a mapping, got %r" % (limits,))
    for name, limit in limits.items():
        name = _require_text("post_surge_limits key", name)
        if name not in GRADED_PARAMETERS:
            raise ValueError("post_surge_limits names an unknown parameter %s" % name)
        _require_positive("post-surge limit for %s" % name, limit)

    conditions = criteria.get("disqualifying_conditions")
    if not isinstance(conditions, (list, tuple, set, frozenset)) or not conditions:
        raise ValueError("disqualifying_conditions must be a non-empty sequence")
    for condition in conditions:
        condition = _require_text("disqualifying condition", condition)
        if condition not in OBSERVABLE_CONDITIONS:
            raise ValueError("unknown disqualifying condition %s" % condition)

    _require_fraction("max_failed_fraction", criteria.get("max_failed_fraction"))
    return criteria


def assess_surge_profile(
    profile=DEFAULT_SURGE_PROFILE,
    rating=DEFAULT_DEVICE_RATING,
    criteria=DEFAULT_SURGE_CRITERIA,
):
    """Is this pulse train a surge, and does it stress the part usefully."""
    validate_surge_profile(profile)
    validate_device_rating(rating)
    validate_surge_criteria(criteria)

    peak = float(profile["peak_current_a"])
    duration = float(profile["pulse_duration_s"])
    waveform = profile["waveform"].strip()
    count = int(profile["pulse_count"])
    interval = float(profile["inter_pulse_interval_s"])
    start_temperature = float(profile["initial_junction_temperature_c"])

    rated = float(rating["rated_average_current_a"])
    withstand = float(rating["i2t_withstand_a2s"])
    drop = float(rating["forward_voltage_drop_v"])
    ceiling = float(rating["max_junction_temperature_c"])
    capacity = float(rating["thermal_capacity_j_per_k"])

    ratio = surge_ratio(peak, rated)
    per_pulse = pulse_action_integral(peak, duration, waveform)
    train = per_pulse * count
    rise = junction_temperature_rise(peak, duration, waveform, drop, capacity)
    peak_temperature = start_temperature + rise
    margin_k = ceiling - peak_temperature

    demonstrated = per_pulse / withstand
    floor = float(criteria["min_demonstrated_withstand_fraction"])
    cap = float(criteria["max_withstand_overstress_fraction"])
    multiple = float(criteria["min_peak_to_rated_multiple"])
    max_duration = float(criteria["max_pulse_duration_s"])
    min_margin = float(criteria["min_junction_temperature_margin_k"])
    min_interval = float(criteria["min_inter_pulse_interval_s"])

    deficiencies = []
    findings = []

    if not _at_least(ratio, multiple):
        deficiencies.append(DEFICIENCY_PEAK_TOO_LOW)
        findings.append(
            "the pulse peak reaches only %.4g times the rated average current "
            "against a demanded multiple of %.4g, so the device is not being "
            "surged at all" % (ratio, multiple)
        )
    if not _within(duration, max_duration):
        deficiencies.append(DEFICIENCY_PULSE_TOO_LONG)
        findings.append(
            "a pulse of %.6g s runs past the %.6g s that still counts as a "
            "surge, which makes this an overload test instead" % (duration, max_duration)
        )
    if not _at_least(demonstrated, floor):
        deficiencies.append(DEFICIENCY_UNDER_STRESSED)
        findings.append(
            "one pulse delivers %.6g of the declared withstand against a "
            "demonstration floor of %.4g" % (demonstrated, floor)
        )
    if not _within(demonstrated, cap):
        deficiencies.append(DEFICIENCY_OVER_STRESSED)
        findings.append(
            "one pulse delivers %.6g of the declared withstand against an "
            "overstress ceiling of %.4g, so the train destroys parts by design"
            % (demonstrated, cap)
        )
    if not _at_least(margin_k, min_margin):
        deficiencies.append(DEFICIENCY_NO_HEADROOM)
        findings.append(
            "the junction reaches %.5g C against a ceiling of %.5g C, leaving "
            "%.5g K where %.5g K is demanded"
            % (peak_temperature, ceiling, margin_k, min_margin)
        )
    if count > 1 and not _at_least(interval, min_interval):
        deficiencies.append(DEFICIENCY_NO_RECOVERY)
        findings.append(
            "pulses %.6g s apart do not let the junction return to its "
            "reference temperature, %.6g s being demanded" % (interval, min_interval)
        )
    if criteria["post_surge_readout_required"] and not profile[
        "post_surge_readout_scheduled"
    ]:
        deficiencies.append(DEFICIENCY_NO_READOUT)
        findings.append(
            "no electrical readout is scheduled after the last pulse, so the "
            "train cannot sentence anything"
        )

    deficiencies = sorted(set(deficiencies))
    return {
        "verdict": PROFILE_ADEQUATE if not deficiencies else PROFILE_INADEQUATE,
        "adequate": not deficiencies,
        "deficiencies": deficiencies,
        "surge_ratio": ratio,
        "pulse_action_integral": per_pulse,
        "train_action_integral": train,
        "demonstrated_withstand_fraction": demonstrated,
        "junction_temperature_rise_k": rise,
        "peak_junction_temperature_c": peak_temperature,
        "junction_temperature_margin_k": margin_k,
        "findings": findings,
    }


def assess_surge_specimen(specimen, criteria=DEFAULT_SURGE_CRITERIA):
    """Did this individual device survive the train, with every mode named."""
    validate_surge_criteria(criteria)
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping, got %r" % (specimen,))
    specimen_id = _require_text("specimen_id", specimen.get("specimen_id"))

    before = specimen.get("pre_surge_readings")
    after = specimen.get("post_surge_readings")
    if not isinstance(before, dict) or not before:
        raise ValueError("pre_surge_readings must be a non-empty mapping")
    if not isinstance(after, dict):
        raise ValueError("post_surge_readings must be a mapping, got %r" % (after,))

    allowances = criteria["post_surge_drift_allowances"]
    limits = criteria.get("post_surge_limits", {})
    modes = []
    findings = []
    drifts = {}
    unread = []

    for parameter in sorted(allowances):
        if before.get(parameter) is None:
            unread.append(parameter)
            findings.append(
                "%s has no pre-surge reading for %s, so no movement can be "
                "taken across the train" % (specimen_id, parameter)
            )
            continue
        if after.get(parameter) is None:
            unread.append(parameter)
            findings.append(
                "%s has no post-surge reading for %s, so the device has not "
                "been evaluated on it" % (specimen_id, parameter)
            )
            continue
        start = _require_positive(
            "pre-surge reading for %s" % parameter, before[parameter]
        )
        end = _require_non_negative(
            "post-surge reading for %s" % parameter, after[parameter]
        )
        sense = degradation_sense(parameter)
        signed = end - start
        decay = signed if sense == "increase" else -signed
        relative = decay / start
        allowance = float(allowances[parameter])
        inside = relative <= 0.0 or _within(relative, allowance)
        entry = {
            "parameter": parameter,
            "sense": sense,
            "before": start,
            "after": end,
            "relative_drift": relative,
            "allowance": allowance,
            "margin": allowance - relative,
            "within_allowance": inside,
        }
        drifts[parameter] = entry
        if not inside:
            modes.append("%s-drift-exceeded" % parameter)
            findings.append(
                "%s moved %.4f of its %s across the train against an allowance "
                "of %.4f" % (specimen_id, relative, parameter, allowance)
            )
        if parameter in limits:
            limit = float(limits[parameter])
            respected = _within(end, limit)
            entry["post_surge_limit"] = limit
            entry["post_surge_limit_respected"] = respected
            if not respected:
                modes.append("%s-outside-post-surge-limit" % parameter)
                findings.append(
                    "%s reads %.6g for %s after the train against a limit of "
                    "%.6g" % (specimen_id, end, parameter, limit)
                )

    observed = specimen.get("observed_conditions", ())
    if not isinstance(observed, (list, tuple, set, frozenset)):
        raise ValueError("observed_conditions must be a sequence, got %r" % (observed,))
    declared = set(criteria["disqualifying_conditions"])
    seen = []
    for condition in observed:
        condition = _require_text("observed condition", condition)
        if condition not in OBSERVABLE_CONDITIONS:
            raise ValueError("inspection reports an unknown condition %s" % condition)
        seen.append(condition)
        if condition in declared and condition not in modes:
            modes.append(condition)
            findings.append(
                "%s shows %s after the train, which fails the device on its "
                "own whatever the readings said" % (specimen_id, condition)
            )

    modes = sorted(set(modes))
    if modes:
        verdict = SPECIMEN_FAILED
    elif unread:
        verdict = SPECIMEN_NOT_EVALUATED
    else:
        verdict = SPECIMEN_WITHSTOOD

    margins = {name: entry["margin"] for name, entry in drifts.items()}
    return {
        "specimen_id": specimen_id,
        "verdict": verdict,
        "failed": verdict == SPECIMEN_FAILED,
        "evaluated": not unread,
        "failure_modes": modes,
        "parameter_drifts": drifts,
        "margins": margins,
        "limiting_margin": min(margins.values()) if margins else None,
        "unread_parameters": sorted(set(unread)),
        "observed_conditions": sorted(set(seen)),
        "findings": findings,
    }


def assess_surge_test(campaign, criteria=DEFAULT_SURGE_CRITERIA):
    """Full clause 12.6.17 sweep over one blocking diode surge campaign."""
    validate_surge_criteria(criteria)
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping, got %r" % (campaign,))
    campaign_id = _require_text("campaign_id", campaign.get("campaign_id"))

    profile_report = assess_surge_profile(
        campaign.get("profile", DEFAULT_SURGE_PROFILE),
        campaign.get("rating", DEFAULT_DEVICE_RATING),
        criteria,
    )

    specimens = campaign.get("specimens")
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("campaign specimens must be a non-empty sequence of mappings")

    seen = set()
    assessments = []
    for specimen in specimens:
        assessed = assess_surge_specimen(specimen, criteria)
        if assessed["specimen_id"] in seen:
            raise ValueError(
                "campaign declares specimen %s twice" % assessed["specimen_id"]
            )
        seen.add(assessed["specimen_id"])
        assessments.append(assessed)
    assessments.sort(key=lambda entry: entry["specimen_id"])

    failed = [e["specimen_id"] for e in assessments if e["verdict"] == SPECIMEN_FAILED]
    withstood = [
        e["specimen_id"] for e in assessments if e["verdict"] == SPECIMEN_WITHSTOOD
    ]
    unevaluated = [
        e["specimen_id"] for e in assessments if e["verdict"] == SPECIMEN_NOT_EVALUATED
    ]

    total = len(assessments)
    failed_fraction = len(failed) / float(total)
    allowance = float(criteria["max_failed_fraction"])
    share_ok = _within(failed_fraction, allowance)

    mode_tally = {}
    for entry in assessments:
        for mode in entry["failure_modes"]:
            mode_tally.setdefault(mode, []).append(entry["specimen_id"])

    findings = list(profile_report["findings"])
    for entry in assessments:
        findings.extend(entry["findings"])
    if unevaluated:
        findings.append(
            "campaign %s cannot be closed while %s carry no complete reading "
            "pair" % (campaign_id, ", ".join(sorted(unevaluated)))
        )
    if not share_ok:
        findings.append(
            "campaign %s failed %d of %d devices, a share of %.4f against an "
            "allowance of %.4f"
            % (campaign_id, len(failed), total, failed_fraction, allowance)
        )

    if not profile_report["adequate"] or unevaluated:
        verdict = SURGE_TEST_NOT_EVALUABLE
    elif not share_ok:
        verdict = SURGE_TEST_FAILED
    else:
        verdict = SURGE_TEST_PASSED

    return {
        "verdict": verdict,
        "campaign_id": campaign_id,
        "profile_report": profile_report,
        "specimen_assessments": assessments,
        "failed_specimen_ids": sorted(failed),
        "withstood_specimen_ids": sorted(withstood),
        "unevaluated_specimen_ids": sorted(unevaluated),
        "failed_fraction": failed_fraction,
        "allowed_failed_fraction": allowance,
        "failed_share_within_allowance": share_ok,
        "modes_by_specimen": {k: sorted(v) for k, v in mode_tally.items()},
        "findings": findings,
    }
