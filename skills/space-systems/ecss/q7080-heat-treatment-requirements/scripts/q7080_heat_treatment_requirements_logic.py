#!/usr/bin/env python3
"""Post-build heat-treatment verification for additively manufactured parts.

Anchor: ECSS-Q-ST-70-80 post-process clause on heat treatment of parts made
by additive manufacturing. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

What the clause actually decides
--------------------------------
An as-built part carries the residual stress of the deposition process and a
microstructure that is not the one the design allowables were taken on. The
furnace route converts one into the other, so it is graded on five things
that fail for different reasons:

soak band     the part is at temperature only when the COLDEST load
              thermocouple is inside the band. A set-point trace proves the
              furnace was hot, not that the part was.
dwell         the qualifying dwell is the longest contiguous run inside the
              band. An excursion above the band interrupts the soak as surely
              as one below it, because it is a different treatment.
ramp          a ramp faster than the declared limit reintroduces the thermal
              gradient the treatment exists to remove.
atmosphere    a reactive alloy held in air gains an oxygen-enriched surface
              layer that no later machining allowance was sized for.
sequence      stress relief belongs before the part leaves the build plate,
              ageing after solution treatment, and a quench inside its
              transfer window. A correct set of steps in the wrong order is
              not a correct treatment.

The verdict is the worst of the graded steps plus the sequence and the
furnace qualification, and the driving step is always named.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STEP_TYPES = (
    "stress-relief",
    "solution",
    "quench",
    "ageing",
    "hot-isostatic-pressing",
)

# A quench is graded on its transfer window and its immersion, not on an
# approach ramp or a soak overshoot it never has.
SOAK_STEP_TYPES = (
    "stress-relief",
    "solution",
    "ageing",
    "hot-isostatic-pressing",
)

ATMOSPHERES = ("vacuum", "argon", "nitrogen", "air")

VERDICT_ACCEPT = "accept"
VERDICT_REVIEW = "review"
VERDICT_REJECT = "reject"

_VERDICT_RANK = {VERDICT_ACCEPT: 0, VERDICT_REVIEW: 1, VERDICT_REJECT: 2}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

# A survey inside this fraction of its interval is still valid but is called
# out, so a long furnace route is not started on a survey about to lapse.
SURVEY_WARNING_FRACTION = 0.9


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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(verdicts):
    worst = VERDICT_ACCEPT
    for verdict in verdicts:
        if _VERDICT_RANK[verdict] > _VERDICT_RANK[worst]:
            worst = verdict
    return worst


def validate_traces(traces):
    """Return load-thermocouple traces as lists of (minute, celsius) pairs.

    Every trace has to sit on the same time base: the coldest-point envelope
    is taken sample by sample, and traces on different time bases cannot be
    compared sample by sample without inventing values between them.
    """
    if not isinstance(traces, (list, tuple)) or not traces:
        raise ValueError("traces must be a non-empty sequence of thermocouple traces")
    cleaned = []
    for t_index, trace in enumerate(traces):
        if not isinstance(trace, (list, tuple)) or len(trace) < 2:
            raise ValueError(
                "trace %d needs at least two (minute, celsius) samples" % t_index
            )
        points = []
        for s_index, sample in enumerate(trace):
            if not isinstance(sample, (list, tuple)) or len(sample) != 2:
                raise ValueError(
                    "trace %d sample %d must be a (minute, celsius) pair"
                    % (t_index, s_index)
                )
            minute = _require_non_negative(
                "trace %d sample %d minute" % (t_index, s_index), sample[0]
            )
            celsius = _require_number(
                "trace %d sample %d celsius" % (t_index, s_index), sample[1]
            )
            if points and minute <= points[-1][0]:
                raise ValueError(
                    "trace %d time base must strictly increase at sample %d"
                    % (t_index, s_index)
                )
            points.append((minute, celsius))
        cleaned.append(points)
    base = [minute for minute, _ in cleaned[0]]
    for t_index, points in enumerate(cleaned[1:], start=1):
        if len(points) != len(base):
            raise ValueError(
                "trace %d has %d samples against %d on trace 0; one time base only"
                % (t_index, len(points), len(base))
            )
        for s_index, (minute, _) in enumerate(points):
            if not math.isclose(minute, base[s_index], rel_tol=_REL_TOL, abs_tol=1e-9):
                raise ValueError(
                    "trace %d sample %d sits at %g min against %g min on trace 0"
                    % (t_index, s_index, minute, base[s_index])
                )
    return cleaned


def coldest_envelope(traces):
    """Return the sample-by-sample coldest load-thermocouple envelope."""
    cleaned = validate_traces(traces)
    envelope = []
    for s_index in range(len(cleaned[0])):
        minute = cleaned[0][s_index][0]
        coldest = min(points[s_index][1] for points in cleaned)
        envelope.append((minute, coldest))
    return envelope


def soak_dwell_minutes(envelope, target_c, band_c):
    """Longest contiguous run the envelope spends inside the soak band.

    Both sides of the band break the soak. A part that overshot is not
    partway through the same treatment, it is partway through another one.
    """
    if not isinstance(envelope, (list, tuple)) or len(envelope) < 2:
        raise ValueError("envelope needs at least two (minute, celsius) samples")
    target = _require_number("target_c", target_c)
    band = _require_positive("band_c", band_c)
    low = target - band
    high = target + band
    best = 0.0
    run_start = None
    previous_minute = None
    for sample in envelope:
        if not isinstance(sample, (list, tuple)) or len(sample) != 2:
            raise ValueError("envelope sample must be a (minute, celsius) pair")
        minute = _require_non_negative("envelope minute", sample[0])
        celsius = _require_number("envelope celsius", sample[1])
        if previous_minute is not None and minute <= previous_minute:
            raise ValueError("envelope time base must strictly increase")
        previous_minute = minute
        inside = _at_least(celsius, low) and _at_most(celsius, high)
        if inside:
            if run_start is None:
                run_start = minute
            best = max(best, minute - run_start)
        else:
            run_start = None
    return best


def peak_temperature(envelope):
    """Highest temperature the coldest-point envelope reached."""
    if not isinstance(envelope, (list, tuple)) or not envelope:
        raise ValueError("envelope must be a non-empty sequence")
    return max(_require_number("envelope celsius", sample[1]) for sample in envelope)


def max_ramp_rate(envelope, target_c, band_c):
    """Fastest heating rate on the approach, in celsius per minute.

    Only the approach counts: the rate inside the band is furnace control,
    not the ramp the treatment specifies.
    """
    target = _require_number("target_c", target_c)
    band = _require_positive("band_c", band_c)
    low = target - band
    if not isinstance(envelope, (list, tuple)) or len(envelope) < 2:
        raise ValueError("envelope needs at least two samples to form a rate")
    fastest = 0.0
    for index in range(1, len(envelope)):
        minute_0, celsius_0 = envelope[index - 1]
        minute_1, celsius_1 = envelope[index]
        if _at_least(celsius_0, low):
            break
        span = float(minute_1) - float(minute_0)
        if span <= 0.0:
            raise ValueError("envelope time base must strictly increase")
        rate = (float(celsius_1) - float(celsius_0)) / span
        fastest = max(fastest, rate)
    return fastest


def grade_step(step, requirement):
    """Grade one furnace step against its declared material requirement."""
    if not isinstance(step, dict):
        raise ValueError("step must be a mapping, got %r" % (step,))
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    step_type = _require_choice("step type", step.get("type"), STEP_TYPES)
    atmosphere = _require_choice(
        "atmosphere", step.get("atmosphere", "air"), ATMOSPHERES
    )
    target = _require_positive("requirement target_c", requirement.get("target_c"))
    band = _require_positive("requirement band_c", requirement.get("band_c"))
    min_dwell = _require_positive(
        "requirement min_dwell_min", requirement.get("min_dwell_min")
    )
    is_soak = step_type in SOAK_STEP_TYPES
    max_ramp = None
    if is_soak:
        max_ramp = _require_positive(
            "requirement max_ramp_c_per_min", requirement.get("max_ramp_c_per_min")
        )
    allowed_atmospheres = requirement.get("atmospheres", ATMOSPHERES)
    if not isinstance(allowed_atmospheres, (list, tuple)) or not allowed_atmospheres:
        raise ValueError("requirement atmospheres must be a non-empty sequence")

    envelope = coldest_envelope(step.get("traces"))
    dwell = soak_dwell_minutes(envelope, target, band)
    peak = peak_temperature(envelope)
    ramp = max_ramp_rate(envelope, target, band) if is_soak else 0.0

    findings = []
    verdicts = []

    if _at_least(dwell, min_dwell):
        verdicts.append(VERDICT_ACCEPT)
    else:
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%s dwell %.1f min on the coldest load thermocouple is short of the "
            "%.1f min required inside %.0f +/- %.0f C"
            % (step_type, dwell, min_dwell, target, band)
        )

    if is_soak:
        if _at_most(peak, target + band):
            verdicts.append(VERDICT_ACCEPT)
        else:
            verdicts.append(VERDICT_REJECT)
            findings.append(
                "%s overshot to %.1f C, above the %.1f C band ceiling"
                % (step_type, peak, target + band)
            )
        if _at_most(ramp, max_ramp):
            verdicts.append(VERDICT_ACCEPT)
        else:
            verdicts.append(VERDICT_REJECT)
            findings.append(
                "%s approach ramp %.2f C/min exceeds the %.2f C/min limit"
                % (step_type, ramp, max_ramp)
            )

    if atmosphere in allowed_atmospheres:
        verdicts.append(VERDICT_ACCEPT)
    else:
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%s ran under %s; the declared protection is %s"
            % (step_type, atmosphere, "/".join(allowed_atmospheres))
        )

    transfer_limit = requirement.get("max_quench_transfer_s")
    transfer = step.get("quench_transfer_s")
    if transfer_limit is not None:
        limit = _require_positive("requirement max_quench_transfer_s", transfer_limit)
        if transfer is None:
            raise ValueError(
                "step %s owes a quench_transfer_s against its declared window"
                % step_type
            )
        measured = _require_non_negative("quench_transfer_s", transfer)
        if _at_most(measured, limit):
            verdicts.append(VERDICT_ACCEPT)
        else:
            verdicts.append(VERDICT_REJECT)
            findings.append(
                "quench transfer %.1f s exceeds the %.1f s window, so the part "
                "cooled out of the furnace before it reached the quenchant"
                % (measured, limit)
            )

    return {
        "type": step_type,
        "graded_as_soak": is_soak,
        "dwell_min": dwell,
        "peak_c": peak,
        "ramp_c_per_min": ramp,
        "atmosphere": atmosphere,
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def check_sequence(step_types, plate_removal_index=None):
    """Grade the order of the furnace route and where plate removal sits.

    plate_removal_index is the number of steps completed before the part was
    cut from the build plate; None means it was still attached throughout.
    """
    if not isinstance(step_types, (list, tuple)) or not step_types:
        raise ValueError("step_types must be a non-empty sequence")
    types = [_require_choice("step type", value, STEP_TYPES) for value in step_types]
    if plate_removal_index is not None:
        if not isinstance(plate_removal_index, int) or isinstance(
            plate_removal_index, bool
        ):
            raise ValueError("plate_removal_index must be an integer or None")
        if plate_removal_index < 0 or plate_removal_index > len(types):
            raise ValueError(
                "plate_removal_index %d is outside the %d-step route"
                % (plate_removal_index, len(types))
            )
    findings = []
    verdicts = [VERDICT_ACCEPT]

    if "stress-relief" not in types:
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "no stress-relief step in the route; the as-built residual stress "
            "is still in the part when it is cut free"
        )
    else:
        relief_at = types.index("stress-relief")
        if plate_removal_index is not None and relief_at >= plate_removal_index:
            verdicts.append(VERDICT_REJECT)
            findings.append(
                "stress relief sits at step %d but the part came off the plate "
                "after step %d, so it distorted on release"
                % (relief_at + 1, plate_removal_index)
            )

    if "solution" in types:
        if types.count("solution") > 1:
            verdicts.append(VERDICT_REVIEW)
            findings.append(
                "%d solution steps in one route; the later one resets the "
                "condition the earlier one produced" % types.count("solution")
            )
        solution_at = types.index("solution")
        if "quench" in types:
            quench_at = types.index("quench")
            if quench_at != solution_at + 1:
                verdicts.append(VERDICT_REJECT)
                findings.append(
                    "quench is step %d and solution is step %d; the quench has "
                    "to follow the solution soak directly"
                    % (quench_at + 1, solution_at + 1)
                )
        else:
            verdicts.append(VERDICT_REJECT)
            findings.append(
                "solution treatment with no quench step; the part cooled in "
                "the furnace and the solution is not retained"
            )
        if "ageing" in types and types.index("ageing") < solution_at:
            verdicts.append(VERDICT_REJECT)
            findings.append(
                "ageing at step %d precedes solution at step %d; the solution "
                "soak dissolves what the ageing produced"
                % (types.index("ageing") + 1, solution_at + 1)
            )
    elif "quench" in types:
        verdicts.append(VERDICT_REVIEW)
        findings.append(
            "quench step with no solution soak before it; confirm which "
            "condition the route is meant to leave the part in"
        )

    if "hot-isostatic-pressing" in types:
        hip_at = types.index("hot-isostatic-pressing")
        if "ageing" in types and types.index("ageing") < hip_at:
            verdicts.append(VERDICT_REVIEW)
            findings.append(
                "ageing at step %d runs before the hot isostatic pressing at "
                "step %d, whose cycle re-solutionises the part"
                % (types.index("ageing") + 1, hip_at + 1)
            )

    return {
        "steps": list(types),
        "plate_removal_index": plate_removal_index,
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def furnace_survey_status(
    days_since_survey, max_interval_days, load_thermocouples, required_thermocouples
):
    """Grade the furnace temperature-uniformity survey and its load couples."""
    age = _require_non_negative("days_since_survey", days_since_survey)
    interval = _require_positive("max_interval_days", max_interval_days)
    for name, value in (
        ("load_thermocouples", load_thermocouples),
        ("required_thermocouples", required_thermocouples),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (name, value))
        if value < 0:
            raise ValueError("%s must not be negative, got %d" % (name, value))
    findings = []
    verdicts = [VERDICT_ACCEPT]
    if not _at_most(age, interval):
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "uniformity survey is %.0f days old against a %.0f day interval"
            % (age, interval)
        )
    elif _at_least(age, interval * SURVEY_WARNING_FRACTION):
        verdicts.append(VERDICT_REVIEW)
        findings.append(
            "uniformity survey at %.0f of %.0f days lapses inside the route"
            % (age, interval)
        )
    if load_thermocouples < required_thermocouples:
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%d load thermocouples against the %d required, so the coldest "
            "point of the load is unmeasured"
            % (load_thermocouples, required_thermocouples)
        )
    return {
        "days_since_survey": age,
        "max_interval_days": interval,
        "load_thermocouples": load_thermocouples,
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def assess_heat_treatment(case):
    """Full post-build heat-treatment verdict for one part or furnace load."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    steps = case.get("steps")
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("case['steps'] must be a non-empty sequence of steps")
    requirements = case.get("requirements")
    if not isinstance(requirements, dict) or not requirements:
        raise ValueError("case['requirements'] must map a step type to its recipe")
    graded = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("each step must be a mapping, got %r" % (step,))
        step_type = step.get("type")
        if step_type not in requirements:
            raise ValueError(
                "no declared requirement for step type %r; the recipe of the "
                "material has to name every step it authorises" % (step_type,)
            )
        graded.append(grade_step(step, requirements[step_type]))
    sequence = check_sequence(
        [record["type"] for record in graded], case.get("plate_removal_index")
    )
    furnace = furnace_survey_status(
        case.get("days_since_survey", 0.0),
        case.get("max_interval_days", 365.0),
        case.get("load_thermocouples", 0),
        case.get("required_thermocouples", 0),
    )
    verdict = _worst(
        [record["verdict"] for record in graded]
        + [sequence["verdict"], furnace["verdict"]]
    )
    driving = []
    if verdict != VERDICT_ACCEPT:
        driving = [
            record["type"]
            for record in graded
            if _VERDICT_RANK[record["verdict"]] == _VERDICT_RANK[verdict]
        ]
        if _VERDICT_RANK[sequence["verdict"]] == _VERDICT_RANK[verdict]:
            driving.append("sequence")
        if _VERDICT_RANK[furnace["verdict"]] == _VERDICT_RANK[verdict]:
            driving.append("furnace")
    findings = []
    for record in graded:
        findings.extend("%s: %s" % (record["type"], text) for text in record["findings"])
    findings.extend("sequence: %s" % text for text in sequence["findings"])
    findings.extend("furnace: %s" % text for text in furnace["findings"])
    return {
        "verdict": verdict,
        "driving_steps": driving,
        "steps": graded,
        "sequence": sequence,
        "furnace": furnace,
        "findings": findings,
    }
