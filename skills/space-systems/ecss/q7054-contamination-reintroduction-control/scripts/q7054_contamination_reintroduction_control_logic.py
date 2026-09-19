#!/usr/bin/env python3
"""Keeping cleaned hardware clean after the cleaning step.

Anchor: ECSS-Q-ST-70-54C process clause, recontamination control. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

An ultraclean surface starts degrading the moment the process ends. The
state at delivery is the state at the end of cleaning minus everything
the handling, storage and transport put back, and that recontamination
is predictable rather than mysterious:

    particles   fall out of the air at a rate set by the room's class,
                reduced by unidirectional flow, by pointing the surface
                away from the fallout, and above all by a bag. The
                added count is added to the count the surface already
                carried, and the sum inverts to a degraded level.

    molecular   arrives from what touches the hardware — gloves and
                garments on open hardware — and, once bagged, from the
                bag film itself at a far lower rate over a far longer
                time.

Both accumulate with exposure time, so the useful question is never
"is the cleanroom good enough" on its own but "which single control
buys back the shortfall", and that is answered by recomputing the
exposure with one control changed at a time.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Particles above the reference size settling per 0.1 square metre per hour
# on an upward-facing surface with no flow and no bag.
FALLOUT_PER_01M2_PER_HOUR = {
    "iso-5": 30.0,
    "iso-6": 300.0,
    "iso-7": 3000.0,
    "iso-8": 30000.0,
    "uncontrolled": 300000.0,
}

CLEANROOM_CLASSES = tuple(sorted(FALLOUT_PER_01M2_PER_HOUR))

# One step tighter, used when asking what a better room would buy.
CLEANROOM_UPGRADE = {
    "uncontrolled": "iso-8",
    "iso-8": "iso-7",
    "iso-7": "iso-6",
    "iso-6": "iso-5",
    "iso-5": "iso-5",
}

ORIENTATIONS = ("upward-facing", "vertical", "downward-facing")
ORIENTATION_FACTOR = {
    "upward-facing": 1.0,
    "vertical": 0.08,
    "downward-facing": 0.01,
}

UNIDIRECTIONAL_FLOW_FACTOR = 0.20

BAGGING_OPTIONS = ("unbagged", "single-bag", "double-bag")
BAG_FALLOUT_FACTOR = {"unbagged": 1.0, "single-bag": 0.05, "double-bag": 0.01}

# Bag film contributes residue of its own, slowly, for as long as it is on.
BAG_NVR_MG_PER_01M2_PER_HOUR = {
    "unbagged": 0.0,
    "single-bag": 2.0e-5,
    "double-bag": 4.0e-5,
}

GLOVE_REGIMES = (
    "bare-hands",
    "cotton-gloves",
    "powder-free-nitrile",
    "cleanroom-nitrile-double",
)
GLOVE_NVR_MG_PER_01M2_PER_HOUR = {
    "bare-hands": 0.50,
    "cotton-gloves": 0.050,
    "powder-free-nitrile": 0.0050,
    "cleanroom-nitrile-double": 0.00050,
}

REFERENCE_PARTICLE_UM = 5.0
_DISTRIBUTION_SLOPE = 0.926

CONTROLS_ADEQUATE = "controls-adequate"
CONTROLS_INSUFFICIENT = "controls-insufficient"

CONTROL_OPTIONS = (
    "tighten-the-cleanroom-one-class",
    "add-unidirectional-flow",
    "double-bag-the-hardware",
    "upgrade-the-glove-regime",
    "halve-the-exposure-time",
    "turn-the-surface-off-upward-facing",
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(sorted(allowed)), value)
        )
    return value


def _at_most(value, limit):
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def particle_count_at(level_um, size_um=REFERENCE_PARTICLE_UM):
    """Count above size_um permitted by a surface cleanliness level."""
    level = _require_positive("level_um", level_um)
    size = _require_positive("size_um", size_um)
    if size > level:
        raise ValueError(
            "size %g um is above the level %g um" % (size, level)
        )
    return 10.0 ** (
        _DISTRIBUTION_SLOPE * (math.log10(level) ** 2 - math.log10(size) ** 2)
    )


def level_for_count(count_per_01m2, size_um=REFERENCE_PARTICLE_UM):
    """Surface cleanliness level a measured count corresponds to."""
    count = _require_positive("count_per_01m2", count_per_01m2)
    size = _require_positive("size_um", size_um)
    if count < 1.0:
        raise ValueError(
            "a count below one particle per 0.1 m2 cannot be inverted at %g um"
            % size
        )
    squared = math.log10(count) / _DISTRIBUTION_SLOPE + math.log10(size) ** 2
    if squared < 0.0:
        raise ValueError("count %g at %g um is off the ladder" % (count, size))
    return 10.0 ** math.sqrt(squared)


def validate_exposure(period):
    """Check one handling, storage or transport period is fully described."""
    if not isinstance(period, dict):
        raise ValueError("exposure period must be a mapping, got %r" % (period,))
    phase = period.get("phase", "exposure")
    if not isinstance(phase, str) or not phase.strip():
        raise ValueError("exposure phase must be a non-empty string, got %r" % (phase,))
    return {
        "phase": phase,
        "cleanroom_class": _require_choice(
            "cleanroom_class", period.get("cleanroom_class"), CLEANROOM_CLASSES
        ),
        "hours": _require_positive("hours", period.get("hours")),
        "orientation": _require_choice(
            "orientation", period.get("orientation", "upward-facing"), ORIENTATIONS
        ),
        "unidirectional_flow": _require_flag(
            "unidirectional_flow", period.get("unidirectional_flow", False)
        ),
        "bagging": _require_choice(
            "bagging", period.get("bagging", "unbagged"), BAGGING_OPTIONS
        ),
        "gloves": _require_choice(
            "gloves", period.get("gloves", "powder-free-nitrile"), GLOVE_REGIMES
        ),
    }


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def particles_added(period):
    """Particles the period deposits per 0.1 square metre."""
    checked = validate_exposure(period)
    rate = FALLOUT_PER_01M2_PER_HOUR[checked["cleanroom_class"]]
    factor = ORIENTATION_FACTOR[checked["orientation"]]
    if checked["unidirectional_flow"]:
        factor *= UNIDIRECTIONAL_FLOW_FACTOR
    factor *= BAG_FALLOUT_FACTOR[checked["bagging"]]
    return rate * factor * checked["hours"]


def nvr_added(period):
    """Residue the period deposits per 0.1 square metre.

    Gloves reach open hardware only; a bagged item takes residue from the
    bag film instead, at a far lower rate over a far longer time.
    """
    checked = validate_exposure(period)
    if checked["bagging"] == "unbagged":
        rate = GLOVE_NVR_MG_PER_01M2_PER_HOUR[checked["gloves"]]
    else:
        rate = BAG_NVR_MG_PER_01M2_PER_HOUR[checked["bagging"]]
    return rate * checked["hours"]


def validate_case(case):
    """Check the achieved state, the requirement and the exposure profile."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    periods = case.get("exposure")
    if isinstance(periods, dict) or not isinstance(periods, (list, tuple)):
        raise ValueError("exposure must be a list or tuple of periods, got %r" % (periods,))
    if not periods:
        raise ValueError("exposure must not be empty; delivery takes some time")
    return {
        "achieved_particulate_level_um": _require_positive(
            "achieved_particulate_level_um", case.get("achieved_particulate_level_um")
        ),
        "achieved_nvr_mg_per_01m2": _require_non_negative(
            "achieved_nvr_mg_per_01m2", case.get("achieved_nvr_mg_per_01m2")
        ),
        "required_particulate_level_um": _require_positive(
            "required_particulate_level_um", case.get("required_particulate_level_um")
        ),
        "required_nvr_mg_per_01m2": _require_positive(
            "required_nvr_mg_per_01m2", case.get("required_nvr_mg_per_01m2")
        ),
        "exposure": [validate_exposure(period) for period in periods],
    }


def degraded_state(case):
    """The state the exposure profile leaves, from the state cleaning left."""
    checked = validate_case(case)
    added_particles = sum(particles_added(p) for p in checked["exposure"])
    added_nvr = sum(nvr_added(p) for p in checked["exposure"])
    start_count = particle_count_at(checked["achieved_particulate_level_um"])
    degraded_level = level_for_count(start_count + added_particles)
    degraded_nvr = checked["achieved_nvr_mg_per_01m2"] + added_nvr
    return {
        "added_particles_per_01m2": added_particles,
        "added_nvr_mg_per_01m2": added_nvr,
        "degraded_particulate_level_um": degraded_level,
        "degraded_nvr_mg_per_01m2": degraded_nvr,
        "particulate_requirement_met": _at_most(
            degraded_level, checked["required_particulate_level_um"]
        ),
        "nvr_requirement_met": _at_most(
            degraded_nvr, checked["required_nvr_mg_per_01m2"]
        ),
    }


def _shortfall(state, checked):
    particulate = max(
        0.0,
        state["degraded_particulate_level_um"]
        - checked["required_particulate_level_um"],
    ) / checked["required_particulate_level_um"]
    molecular = max(
        0.0, state["degraded_nvr_mg_per_01m2"] - checked["required_nvr_mg_per_01m2"]
    ) / checked["required_nvr_mg_per_01m2"]
    return particulate + molecular


def _apply_control(periods, control):
    """Exposure profile with one control changed, or None if already in force."""
    changed = False
    out = []
    for period in periods:
        updated = dict(period)
        if control == "tighten-the-cleanroom-one-class":
            better = CLEANROOM_UPGRADE[period["cleanroom_class"]]
            if better != period["cleanroom_class"]:
                updated["cleanroom_class"] = better
                changed = True
        elif control == "add-unidirectional-flow":
            if not period["unidirectional_flow"]:
                updated["unidirectional_flow"] = True
                changed = True
        elif control == "double-bag-the-hardware":
            if period["bagging"] != "double-bag":
                updated["bagging"] = "double-bag"
                changed = True
        elif control == "upgrade-the-glove-regime":
            if period["gloves"] != "cleanroom-nitrile-double":
                updated["gloves"] = "cleanroom-nitrile-double"
                changed = True
        elif control == "halve-the-exposure-time":
            updated["hours"] = period["hours"] / 2.0
            changed = True
        elif control == "turn-the-surface-off-upward-facing":
            if period["orientation"] == "upward-facing":
                updated["orientation"] = "vertical"
                changed = True
        else:
            raise ValueError("unknown control %r" % (control,))
        out.append(updated)
    return out if changed else None


def control_options(case):
    """Each single control, what it leaves, ranked by remaining shortfall."""
    checked = validate_case(case)
    options = []
    for control in CONTROL_OPTIONS:
        periods = _apply_control(checked["exposure"], control)
        if periods is None:
            continue
        variant = dict(checked)
        variant["exposure"] = periods
        state = degraded_state(variant)
        options.append(
            {
                "control": control,
                "degraded_particulate_level_um": state[
                    "degraded_particulate_level_um"
                ],
                "degraded_nvr_mg_per_01m2": state["degraded_nvr_mg_per_01m2"],
                "requirement_met": state["particulate_requirement_met"]
                and state["nvr_requirement_met"],
                "remaining_shortfall": _shortfall(state, checked),
            }
        )
    options.sort(key=lambda entry: (entry["remaining_shortfall"], entry["control"]))
    return options


def assess_recontamination_controls(case):
    """Full recontamination decision with the control that buys back most."""
    checked = validate_case(case)
    state = degraded_state(checked)
    adequate = state["particulate_requirement_met"] and state["nvr_requirement_met"]
    findings = []
    open_hours = sum(
        p["hours"] for p in checked["exposure"] if p["bagging"] == "unbagged"
    )
    if any(
        p["bagging"] == "unbagged" and p["gloves"] in ("bare-hands", "cotton-gloves")
        for p in checked["exposure"]
    ):
        findings.append(
            "open hardware is handled in a glove regime that sheds residue; the "
            "molecular budget is spent by the handler, not by the process"
        )
    if any(
        p["bagging"] == "unbagged"
        and p["orientation"] == "upward-facing"
        and not p["unidirectional_flow"]
        and p["cleanroom_class"] in ("iso-7", "iso-8", "uncontrolled")
        for p in checked["exposure"]
    ):
        findings.append(
            "an upward-facing surface sits open in a room with no unidirectional "
            "flow; fallout is the dominant term and no later step removes it"
        )
    if not state["particulate_requirement_met"]:
        findings.append(
            "particulate level degrades from %.4g um to %.4g um against a "
            "requirement of %.4g um"
            % (
                checked["achieved_particulate_level_um"],
                state["degraded_particulate_level_um"],
                checked["required_particulate_level_um"],
            )
        )
    if not state["nvr_requirement_met"]:
        findings.append(
            "residue rises from %.4g to %.4g mg per 0.1 m2 against an allowance "
            "of %.4g"
            % (
                checked["achieved_nvr_mg_per_01m2"],
                state["degraded_nvr_mg_per_01m2"],
                checked["required_nvr_mg_per_01m2"],
            )
        )
    options = control_options(checked)
    result = dict(state)
    result.update(
        {
            "achieved_particulate_level_um": checked["achieved_particulate_level_um"],
            "achieved_nvr_mg_per_01m2": checked["achieved_nvr_mg_per_01m2"],
            "open_exposure_hours": open_hours,
            "verdict": CONTROLS_ADEQUATE if adequate else CONTROLS_INSUFFICIENT,
            "control_options": options,
            "best_control": None if adequate or not options else options[0],
            "findings": findings,
        }
    )
    return result
