#!/usr/bin/env python3
"""Why a photovoltaic assembly is thermally cycled at acceptance.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.7.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Acceptance thermal cycling is not a repeat of qualification. It is
applied to flight hardware that has already passed a qualified design,
and it exists for two reasons only: to stress the assembly hard enough
that an early-life escape declares itself on the ground rather than in
orbit, and to give evidence that the supplier's process produced this
particular article the way it produced the qualified one.

Both reasons put the campaign between two walls. Too little stress --
too few cycles, too shallow a range, dwells too short for the assembly
to reach the extreme -- and nothing is revealed, so the campaign is a
schedule item rather than a screen. Too much stress and the acceptance
run spends the fatigue life the qualification demonstrated, which is
the life the mission was supposed to get.

Where a failure appears in the campaign is the evidence that separates
the two purposes. A failure in the opening cycles is an infant-mortality
escape and speaks about workmanship. A failure that only appears once
most of the campaign has run is a different mechanism and belongs to
design or to wear-out, so it is escalated rather than recorded as a
supplier finding.

Fatigue is scaled with a Coffin-Manson exponent: the cycles a joint
survives fall as the temperature range rises, so acceptance cycles at
one range are converted into qualification-equivalent cycles before the
consumed life fraction means anything.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPTANCE_PURPOSES = (
    "reveal-infant-mortality",
    "confirm-supplier-workmanship",
)

ONSET_CATEGORIES = (
    "infant-mortality",
    "later-life",
)

MIN_ACCEPTANCE_CYCLES = 5
MIN_CYCLE_RANGE_K = 60.0
MIN_SOAK_TIME_CONSTANTS = 3.0
MAX_QUALIFICATION_LIFE_FRACTION = 0.25
EARLY_LIFE_FRACTION = 0.25
DEFAULT_COFFIN_MANSON_EXPONENT = 2.5

WORKMANSHIP_CONFIRMED = "supplier-workmanship-confirmed"
INFANT_MORTALITY_REVEALED = "infant-mortality-revealed"
PURPOSE_NOT_SERVED = "acceptance-purpose-not-served"

PROFILE_FIELDS = (
    "cold_k",
    "cold_dwell_min",
    "cycles",
    "hot_k",
    "hot_dwell_min",
    "ramp_rate_k_per_min",
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


def _require_positive_integer(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A dwell written in minutes and a time constant derived in seconds
    can land a few units in the last place either side of a ratio, so
    the comparison tolerates the representation error while the limit
    itself is never relaxed.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_cycle_profile(name, profile):
    """Normalise a cycling profile, refusing an unusable one."""
    if not isinstance(profile, dict):
        raise ValueError("%s must be a mapping with %s" % (name, ", ".join(PROFILE_FIELDS)))
    absent = tuple(field for field in PROFILE_FIELDS if profile.get(field) is None)
    if absent:
        raise ValueError("%s is missing %s" % (name, ", ".join(absent)))
    hot = _require_positive("%s hot_k" % name, profile["hot_k"])
    cold = _require_positive("%s cold_k" % name, profile["cold_k"])
    if not hot > cold:
        raise ValueError(
            "%s hot_k %g must be above cold_k %g" % (name, hot, cold)
        )
    return {
        "hot_k": hot,
        "cold_k": cold,
        "cycles": _require_positive_integer("%s cycles" % name, profile["cycles"]),
        "ramp_rate_k_per_min": _require_positive(
            "%s ramp_rate_k_per_min" % name, profile["ramp_rate_k_per_min"]
        ),
        "hot_dwell_min": _require_positive(
            "%s hot_dwell_min" % name, profile["hot_dwell_min"]
        ),
        "cold_dwell_min": _require_positive(
            "%s cold_dwell_min" % name, profile["cold_dwell_min"]
        ),
    }


def cycle_temperature_range_k(profile):
    """Depth of one cycle in kelvin."""
    checked = validate_cycle_profile("profile", profile)
    return checked["hot_k"] - checked["cold_k"]


def cycle_duration_min(profile):
    """Wall-clock minutes one complete cycle takes."""
    checked = validate_cycle_profile("profile", profile)
    span = checked["hot_k"] - checked["cold_k"]
    ramp = 2.0 * span / checked["ramp_rate_k_per_min"]
    return ramp + checked["hot_dwell_min"] + checked["cold_dwell_min"]


def campaign_duration_h(profile):
    """Wall-clock hours the whole acceptance campaign takes."""
    checked = validate_cycle_profile("profile", profile)
    return cycle_duration_min(profile) * checked["cycles"] / 60.0


def soak_adequacy(dwell_min, thermal_time_constant_min):
    """Whether a dwell lets the assembly actually reach the extreme.

    A dwell shorter than a few thermal time constants leaves the joints
    cooler than the chamber says, so the stress the article received is
    smaller than the stress on the profile sheet.
    """
    dwell = _require_positive("dwell_min", dwell_min)
    tau = _require_positive("thermal_time_constant_min", thermal_time_constant_min)
    ratio = dwell / tau
    return {
        "soak_time_constants": ratio,
        "adequate": _at_least(ratio, MIN_SOAK_TIME_CONSTANTS),
    }


def fatigue_acceleration(
    applied_range_k, reference_range_k, exponent=DEFAULT_COFFIN_MANSON_EXPONENT
):
    """Damage per cycle at one range relative to a reference range."""
    applied = _require_positive("applied_range_k", applied_range_k)
    reference = _require_positive("reference_range_k", reference_range_k)
    power = _require_positive("exponent", exponent)
    return (applied / reference) ** power


def qualification_life_consumed(
    acceptance_profile,
    qualification_profile,
    exponent=DEFAULT_COFFIN_MANSON_EXPONENT,
):
    """Share of the demonstrated fatigue life the acceptance run spends."""
    acceptance = validate_cycle_profile("acceptance profile", acceptance_profile)
    qualification = validate_cycle_profile(
        "qualification profile", qualification_profile
    )
    acceptance_range = acceptance["hot_k"] - acceptance["cold_k"]
    qualification_range = qualification["hot_k"] - qualification["cold_k"]
    acceleration = fatigue_acceleration(
        acceptance_range, qualification_range, exponent
    )
    equivalent = acceptance["cycles"] * acceleration
    return {
        "acceptance_range_k": acceptance_range,
        "qualification_range_k": qualification_range,
        "fatigue_acceleration": acceleration,
        "equivalent_qualification_cycles": equivalent,
        "consumed_fraction": equivalent / qualification["cycles"],
    }


def early_life_cycle_count(total_cycles):
    """Cycles inside which a failure counts as an early-life escape."""
    total = _require_positive_integer("total_cycles", total_cycles)
    window = int(math.ceil(EARLY_LIFE_FRACTION * total))
    return max(1, window)


def categorize_failure_onset(cycle_index, total_cycles):
    """Group one failure by where in the campaign it appeared."""
    total = _require_positive_integer("total_cycles", total_cycles)
    index = _require_positive_integer("cycle_index", cycle_index)
    if index > total:
        raise ValueError(
            "cycle_index %d is beyond the %d cycles run" % (index, total)
        )
    return (
        "infant-mortality"
        if index <= early_life_cycle_count(total)
        else "later-life"
    )


def group_failures(failure_cycles, total_cycles):
    """Group every recorded failure onset into its onset category."""
    if not isinstance(failure_cycles, (list, tuple)):
        raise ValueError(
            "failure_cycles must be a sequence of cycle indices, got %r"
            % (failure_cycles,)
        )
    grouped = {category: [] for category in ONSET_CATEGORIES}
    for index in failure_cycles:
        grouped[categorize_failure_onset(index, total_cycles)].append(int(index))
    return {category: tuple(sorted(grouped[category])) for category in ONSET_CATEGORIES}


def escape_rate(failure_count, unit_count):
    """Share of the delivered units that failed during acceptance."""
    units = _require_positive_integer("unit_count", unit_count)
    if isinstance(failure_count, bool) or not isinstance(failure_count, int):
        raise ValueError("failure_count must be a whole number, got %r" % (failure_count,))
    if failure_count < 0:
        raise ValueError("failure_count must not be negative, got %r" % (failure_count,))
    if failure_count > units:
        raise ValueError(
            "failure_count %d exceeds the %d units cycled" % (failure_count, units)
        )
    return failure_count / units


def assess_acceptance_purpose(case):
    """Full clause 5.5.3.7.1 judgement of an acceptance cycling campaign."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    acceptance = validate_cycle_profile(
        "acceptance profile", case.get("acceptance_profile")
    )
    life = qualification_life_consumed(
        case.get("acceptance_profile"),
        case.get("qualification_profile"),
        case.get("coffin_manson_exponent", DEFAULT_COFFIN_MANSON_EXPONENT),
    )
    tau = case.get("thermal_time_constant_min")
    hot_soak = soak_adequacy(acceptance["hot_dwell_min"], tau)
    cold_soak = soak_adequacy(acceptance["cold_dwell_min"], tau)
    units = _require_positive_integer("unit_count", case.get("unit_count"))
    failures = case.get("failure_cycles", ())
    grouped = group_failures(failures, acceptance["cycles"])

    findings = []
    if acceptance["cycles"] < MIN_ACCEPTANCE_CYCLES:
        findings.append(
            "%d cycles is below the %d a screen needs to precipitate an early-life escape"
            % (acceptance["cycles"], MIN_ACCEPTANCE_CYCLES)
        )
    if not _at_least(life["acceptance_range_k"], MIN_CYCLE_RANGE_K):
        findings.append(
            "a %.1f K range is too shallow to stress the assembly; the screen reveals nothing at this depth"
            % life["acceptance_range_k"]
        )
    if not hot_soak["adequate"]:
        findings.append(
            "hot dwell covers only %.2f thermal time constants; the assembly never reaches the hot extreme"
            % hot_soak["soak_time_constants"]
        )
    if not cold_soak["adequate"]:
        findings.append(
            "cold dwell covers only %.2f thermal time constants; the assembly never reaches the cold extreme"
            % cold_soak["soak_time_constants"]
        )
    if not _at_most(life["consumed_fraction"], MAX_QUALIFICATION_LIFE_FRACTION):
        findings.append(
            "the campaign spends %.1f%% of the demonstrated fatigue life, above the %.0f%% an acceptance screen may consume"
            % (
                life["consumed_fraction"] * 100.0,
                MAX_QUALIFICATION_LIFE_FRACTION * 100.0,
            )
        )

    capable = not findings

    if grouped["later-life"]:
        findings.append(
            "failures at cycles %s fall outside the early-life window; the onset points at a design or wear-out mechanism and is escalated rather than recorded against the supplier"
            % (", ".join(str(index) for index in grouped["later-life"]))
        )
    if grouped["infant-mortality"]:
        findings.append(
            "failures at cycles %s are early-life escapes; supplier workmanship is not confirmed for this lot"
            % (", ".join(str(index) for index in grouped["infant-mortality"]))
        )

    revealed = bool(grouped["infant-mortality"])
    confirmed = capable and not grouped["infant-mortality"] and not grouped["later-life"]
    if confirmed:
        verdict = WORKMANSHIP_CONFIRMED
    elif capable and revealed and not grouped["later-life"]:
        verdict = INFANT_MORTALITY_REVEALED
    else:
        verdict = PURPOSE_NOT_SERVED

    return {
        "purposes": ACCEPTANCE_PURPOSES,
        "acceptance_cycles": acceptance["cycles"],
        "acceptance_range_k": life["acceptance_range_k"],
        "cycle_duration_min": cycle_duration_min(case.get("acceptance_profile")),
        "campaign_duration_h": campaign_duration_h(case.get("acceptance_profile")),
        "hot_soak": hot_soak,
        "cold_soak": cold_soak,
        "life_consumed": life,
        "early_life_cycle_count": early_life_cycle_count(acceptance["cycles"]),
        "grouped_failures": grouped,
        "escape_rate": escape_rate(len(tuple(failures)), units),
        "screen_capable": capable,
        "infant_mortality_revealed": revealed,
        "workmanship_confirmed": confirmed,
        "verdict": verdict,
        "findings": findings,
    }
