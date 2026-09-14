#!/usr/bin/env python3
"""Blocking diode survival against a discharge from a charged operator.

Anchor: ECSS-E-ST-20-08C clause 12.6.15. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar array blocking diode is handled: it is inserted, it is bonded,
its interconnectors are welded, and at every one of those moments a
person who has walked across a floor can touch its terminals. The
discharge that follows is short, it is not bounded by anything in the
harness, and the diode has to survive it. The robustness stress fires a
representative discharge network into the device at a rising sequence of
step voltages and asks what level it is still sound after.

The network is the stress. A capacitor charged to the step voltage and
discharged through a series resistance into the device is a model of the
charged person, and four numbers fall straight out of it:

    peak current        the step voltage over the total resistance the
                        discharge sees, which is the series resistance
                        plus the device's own
    decay constant      that same total resistance times the
                        capacitance, which sets how long the current
                        lasts
    transferred charge  the capacitance times the step voltage
    stored energy       half the capacitance times the square of the
                        step voltage, which is what the junction has to
                        absorb

A bench whose capacitance or series resistance has drifted outside its
band is firing a different pulse than the one the record claims, and no
amount of care in reading the diode afterwards repairs that.

What failure looks like on a blocking diode is specific, and it is not
usually a short. The junction takes local damage, and what shows is the
reverse leakage climbing: the diode still blocks, but it blocks worse.
That matters because a blocking diode's whole job is to not conduct
backwards, and the leakage it passes is a parasitic loss the array
carries for the rest of the mission -- once per string, at the worst
reverse bias the string can put across it. So the pass criterion is a
drift criterion against the device's own pre-stress baseline, not an
absolute limit, and the forward drop is read alongside it to catch the
damage that shows the other way.

The ladder is walked from the bottom and both polarities are fired at
each level, because a junction that survives one direction can fail the
other. The withstand level is the highest level the device cleared with
every level below it also clear; a device that failed at one level and
passed at a higher one has an inconsistent record, not a higher
withstand, and the highest unbroken run is what is credited.

The bands and criteria below are a declared project set, not physical
constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT = "accept"
REVIEW = "review"
REJECT = "reject"
ESD_DISPOSITIONS = (ACCEPT, REVIEW, REJECT)

STRESS_INCOMPLETE = "stress-incomplete"

FORWARD = "forward"
REVERSE = "reverse"
REQUIRED_POLARITIES = (FORWARD, REVERSE)

_SEVERITY_ORDER = {ACCEPT: 0, REVIEW: 1, REJECT: 2}

PICO = 1e-12
NANO = 1e-9

DEFAULT_NETWORK_SPEC = {
    "nominal_capacitance_pf": 100.0,
    "capacitance_tolerance_fraction": 0.10,
    "nominal_series_resistance_ohm": 1500.0,
    "resistance_tolerance_fraction": 0.10,
}

DEFAULT_ESD_CRITERIA = {
    "max_leakage_ratio": 2.0,
    "max_forward_drift_v": 0.05,
    "required_withstand_margin": 1.5,
    "max_affected_device_fraction": 0.05,
    "min_sample_fraction": 0.10,
}

# Ascending floors. A withstand voltage is grouped into the highest band
# whose floor it reaches.
DEFAULT_WITHSTAND_BANDS = (
    ("none", 0.0),
    ("band-1", 250.0),
    ("band-2", 500.0),
    ("band-3", 1000.0),
    ("band-4", 2000.0),
)

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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return number


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive integer, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A leakage ratio is a quotient of two measured currents and a ladder
    level is a running product of a declared ratio, so a value that
    should land exactly on its limit can evaluate a few units in the
    last place past it, and it lands differently on different machines.
    The limit is never moved; only the comparison tolerates the
    representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit under the same representation tolerance."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_network_spec(spec):
    """Check the discharge network the bench is meant to present."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    _require_positive(
        "spec nominal_capacitance_pf", spec.get("nominal_capacitance_pf")
    )
    _require_positive(
        "spec nominal_series_resistance_ohm",
        spec.get("nominal_series_resistance_ohm"),
    )
    cap_tol = _require_fraction(
        "spec capacitance_tolerance_fraction",
        spec.get("capacitance_tolerance_fraction"),
    )
    res_tol = _require_fraction(
        "spec resistance_tolerance_fraction",
        spec.get("resistance_tolerance_fraction"),
    )
    if cap_tol >= 1.0 or res_tol >= 1.0:
        raise ValueError(
            "a network tolerance of one or more admits a bench with no "
            "capacitance or no series resistance at all, which is not the "
            "pulse the record claims"
        )
    return spec


def validate_discharge_network(network, spec=DEFAULT_NETWORK_SPEC):
    """Check the network the bench actually presents sits in its band."""
    validate_network_spec(spec)
    if not isinstance(network, dict):
        raise ValueError("network must be a mapping, got %r" % (network,))
    capacitance = _require_positive(
        "capacitance_pf", network.get("capacitance_pf")
    )
    series = _require_positive(
        "series_resistance_ohm", network.get("series_resistance_ohm")
    )
    device = _require_positive(
        "device_resistance_ohm", network.get("device_resistance_ohm")
    )
    cap_tol = spec["capacitance_tolerance_fraction"]
    res_tol = spec["resistance_tolerance_fraction"]
    cap_low = spec["nominal_capacitance_pf"] * (1.0 - cap_tol)
    cap_high = spec["nominal_capacitance_pf"] * (1.0 + cap_tol)
    res_low = spec["nominal_series_resistance_ohm"] * (1.0 - res_tol)
    res_high = spec["nominal_series_resistance_ohm"] * (1.0 + res_tol)
    findings = []
    if not (_at_least(capacitance, cap_low) and _at_most(capacitance, cap_high)):
        findings.append(
            "the discharge capacitance reads %.2f pF, outside the %.2f to %.2f pF "
            "band; the charge and the energy delivered are not the ones the "
            "record claims" % (capacitance, cap_low, cap_high)
        )
    if not (_at_least(series, res_low) and _at_most(series, res_high)):
        findings.append(
            "the series resistance reads %.1f ohm, outside the %.1f to %.1f ohm "
            "band; the peak current and the decay are not the ones the record "
            "claims" % (series, res_low, res_high)
        )
    return {
        "capacitance_pf": capacitance,
        "series_resistance_ohm": series,
        "device_resistance_ohm": device,
        "total_resistance_ohm": series + device,
        "in_band": not findings,
        "findings": findings,
    }


def discharge_pulse(step_volts, network, spec=DEFAULT_NETWORK_SPEC):
    """The pulse one step voltage produces through the discharge network."""
    state = validate_discharge_network(network, spec)
    volts = _require_positive("step_volts", step_volts)
    farads = state["capacitance_pf"] * PICO
    total = state["total_resistance_ohm"]
    return {
        "step_volts": volts,
        "peak_current_a": volts / total,
        "decay_constant_s": total * farads,
        "transferred_charge_c": farads * volts,
        "stored_energy_j": 0.5 * farads * volts * volts,
        "network_in_band": state["in_band"],
        "network_findings": state["findings"],
    }


def build_step_ladder(plan):
    """The rising sequence of step voltages the stress is walked up.

    The levels are built by repeated multiplication rather than by
    raising the ratio to a power, so every level is a product of exactly
    rounded multiplications and the ladder is the same sequence on every
    machine.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    start = _require_positive("start_volts", plan.get("start_volts"))
    ratio = _require_number("step_ratio", plan.get("step_ratio"))
    if ratio <= 1.0:
        raise ValueError(
            "step_ratio must be greater than one so the ladder rises, got %r"
            % (ratio,)
        )
    levels = _require_count("level_count", plan.get("level_count"))
    _require_count("pulses_per_level", plan.get("pulses_per_level"))
    polarities = plan.get("polarities", REQUIRED_POLARITIES)
    if not isinstance(polarities, (list, tuple)) or not polarities:
        raise ValueError("polarities must be a non-empty list, got %r" % (polarities,))
    for polarity in polarities:
        if polarity not in REQUIRED_POLARITIES:
            raise ValueError(
                "polarity must be one of %s, got %r"
                % (", ".join(REQUIRED_POLARITIES), polarity)
            )
    if len(set(polarities)) != len(polarities):
        raise ValueError("polarities must not repeat, got %r" % (polarities,))
    ladder = []
    level = start
    for _ in range(levels):
        ladder.append(level)
        level = level * ratio
    return ladder


def post_stress_parasitic_loss_w(leakage_na, reverse_bias_v, string_count):
    """What the leakage after the stress costs the array, per orbit-second.

    A blocking diode that still blocks but blocks worse is not a benign
    outcome: the leakage flows once per string at the worst reverse bias
    the string can present, for the rest of the mission.
    """
    leakage = _require_non_negative("leakage_na", leakage_na)
    bias = _require_non_negative("reverse_bias_v", reverse_bias_v)
    strings = _require_count("string_count", string_count)
    return leakage * NANO * bias * strings


def evaluate_step_observation(observation, baseline, criteria=DEFAULT_ESD_CRITERIA):
    """Read one post-pulse measurement against the device's own baseline."""
    validate_esd_criteria(criteria)
    if not isinstance(observation, dict):
        raise ValueError("observation must be a mapping, got %r" % (observation,))
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be a mapping, got %r" % (baseline,))
    polarity = observation.get("polarity")
    if polarity not in REQUIRED_POLARITIES:
        raise ValueError(
            "observation polarity must be one of %s, got %r"
            % (", ".join(REQUIRED_POLARITIES), polarity)
        )
    base_leakage = _require_positive(
        "baseline reverse_leakage_na", baseline.get("reverse_leakage_na")
    )
    base_forward = _require_positive(
        "baseline forward_voltage_v", baseline.get("forward_voltage_v")
    )
    leakage = _require_non_negative(
        "reverse_leakage_na", observation.get("reverse_leakage_na")
    )
    forward = _require_non_negative(
        "forward_voltage_v", observation.get("forward_voltage_v")
    )
    catastrophic = bool(observation.get("catastrophic_failure", False))

    ratio = leakage / base_leakage
    drift = abs(forward - base_forward)
    findings = []
    if catastrophic:
        findings.append(
            "the device went short or open on the %s pulse" % polarity
        )
    if not _at_most(ratio, criteria["max_leakage_ratio"]):
        findings.append(
            "the reverse leakage after the %s pulse is %.3f times its own "
            "pre-stress value, past the %.3f the criteria allow"
            % (polarity, ratio, criteria["max_leakage_ratio"])
        )
    if not _at_most(drift, criteria["max_forward_drift_v"]):
        findings.append(
            "the forward drop after the %s pulse moved %.4f V from its own "
            "pre-stress value, past the %.4f V the criteria allow"
            % (polarity, drift, criteria["max_forward_drift_v"])
        )
    return {
        "polarity": polarity,
        "passed": not findings,
        "leakage_ratio": ratio,
        "forward_drift_v": drift,
        "reverse_leakage_na": leakage,
        "catastrophic_failure": catastrophic,
        "findings": findings,
    }


def validate_esd_criteria(criteria):
    """Check the drift criteria and the margin the stress is read against."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    ratio = _require_number("criteria max_leakage_ratio", criteria.get("max_leakage_ratio"))
    if ratio < 1.0:
        raise ValueError(
            "criteria max_leakage_ratio must be at least one; a ceiling below "
            "the device's own baseline fails every sound device, got %r" % (ratio,)
        )
    _require_positive(
        "criteria max_forward_drift_v", criteria.get("max_forward_drift_v")
    )
    margin = _require_number(
        "criteria required_withstand_margin", criteria.get("required_withstand_margin")
    )
    if margin < 1.0:
        raise ValueError(
            "criteria required_withstand_margin must be at least one; a margin "
            "below one asks the diode to survive less than the handling "
            "environment it will meet, got %r" % (margin,)
        )
    _require_fraction(
        "criteria max_affected_device_fraction",
        criteria.get("max_affected_device_fraction"),
    )
    sample = _require_fraction(
        "criteria min_sample_fraction", criteria.get("min_sample_fraction")
    )
    if sample <= 0.0:
        raise ValueError(
            "criteria min_sample_fraction must be above zero; a lot cannot be "
            "sentenced from no devices at all"
        )
    return criteria


def validate_withstand_bands(bands):
    """Check the withstand bands rise and start at zero."""
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("bands must be a non-empty sequence, got %r" % (bands,))
    previous = None
    for index, entry in enumerate(bands):
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError(
                "band %d must be a (name, floor_volts) pair, got %r" % (index, entry)
            )
        _require_text("band %d name" % index, entry[0])
        floor = _require_non_negative("band %d floor_volts" % index, entry[1])
        if previous is not None and floor <= previous:
            raise ValueError(
                "band floors must rise; band %d floor %r is not above the one "
                "before it (%r)" % (index, floor, previous)
            )
        previous = floor
    if bands[0][1] != 0.0:
        raise ValueError(
            "the lowest band must start at zero volts so a device that "
            "survived nothing still lands somewhere, got %r" % (bands[0][1],)
        )
    return bands


def esd_withstand_band(withstand_volts, bands=DEFAULT_WITHSTAND_BANDS):
    """Group a withstand voltage into the highest band whose floor it reaches."""
    validate_withstand_bands(bands)
    volts = _require_non_negative("withstand_volts", withstand_volts)
    grouped = bands[0][0]
    for name, floor in bands:
        if _at_least(volts, floor):
            grouped = name
    return grouped


def assess_blocking_diode_esd(
    device,
    plan,
    network,
    spec=DEFAULT_NETWORK_SPEC,
    criteria=DEFAULT_ESD_CRITERIA,
    bands=DEFAULT_WITHSTAND_BANDS,
):
    """Walk one blocking diode up the ladder and find its withstand level."""
    validate_esd_criteria(criteria)
    validate_withstand_bands(bands)
    ladder = build_step_ladder(plan)
    pulses_per_level = plan["pulses_per_level"]
    polarities = list(plan.get("polarities", REQUIRED_POLARITIES))
    network_state = validate_discharge_network(network, spec)
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    device_id = _require_text("device_id", device.get("device_id"))
    baseline = device.get("baseline")
    results = device.get("levels")
    if not isinstance(results, (list, tuple)):
        raise ValueError(
            "%s must carry a levels list, got %r" % (device_id, results)
        )

    findings = list(network_state["findings"])
    by_volts = {}
    for entry in results:
        if not isinstance(entry, dict):
            raise ValueError(
                "%s carries a level record that is not a mapping: %r"
                % (device_id, entry)
            )
        volts = _require_positive("step_volts on %s" % device_id, entry.get("step_volts"))
        key = "%.6f" % volts
        if key in by_volts:
            raise ValueError(
                "%s carries two records for the %.1f V level" % (device_id, volts)
            )
        by_volts[key] = entry

    walked = []
    withstand = 0.0
    run_broken = False
    inconsistent = False
    incomplete_levels = []
    worst_leakage_ratio = 0.0
    for volts in ladder:
        key = "%.6f" % volts
        entry = by_volts.get(key)
        if entry is None:
            incomplete_levels.append(volts)
            run_broken = True
            walked.append(
                {"step_volts": volts, "recorded": False, "passed": None,
                 "observations": [], "findings": []}
            )
            continue
        pulse = discharge_pulse(volts, network, spec)
        observations = entry.get("observations")
        if not isinstance(observations, (list, tuple)):
            raise ValueError(
                "%s level %.1f V must carry an observations list, got %r"
                % (device_id, volts, observations)
            )
        graded = [
            evaluate_step_observation(observation, baseline, criteria)
            for observation in observations
        ]
        level_findings = []
        counts = dict((polarity, 0) for polarity in polarities)
        for result in graded:
            if result["polarity"] in counts:
                counts[result["polarity"]] += 1
            worst_leakage_ratio = max(worst_leakage_ratio, result["leakage_ratio"])
            for finding in result["findings"]:
                level_findings.append("%s at %.1f V %s" % (device_id, volts, finding))
        short = [p for p in polarities if counts[p] < pulses_per_level]
        level_complete = not short
        if short:
            incomplete_levels.append(volts)
            level_findings.append(
                "%s at %.1f V was fired fewer than the %d pulses planned on its "
                "%s side, so the level is not credited"
                % (device_id, volts, pulses_per_level, " and ".join(short))
            )
        passed = level_complete and all(result["passed"] for result in graded)
        walked.append(
            {
                "step_volts": volts,
                "recorded": True,
                "complete": level_complete,
                "passed": passed,
                "pulse": pulse,
                "observations": graded,
                "findings": level_findings,
            }
        )
        findings.extend(level_findings)
        if passed and not run_broken:
            withstand = volts
        elif passed and run_broken:
            inconsistent = True
        elif not passed:
            run_broken = True

    if inconsistent:
        findings.append(
            "%s passed a level above one it had already failed; the highest "
            "unbroken run is credited rather than the higher level" % device_id
        )

    handling = _require_non_negative(
        "handling_environment_v", device.get("handling_environment_v", 0.0)
    )
    required = handling * criteria["required_withstand_margin"]
    dispositions = [ACCEPT]
    if withstand <= 0.0:
        dispositions.append(REJECT)
        findings.append(
            "%s did not clear the lowest level on the ladder" % device_id
        )
    elif handling > 0.0 and not _at_least(withstand, required):
        if _at_least(withstand, handling):
            dispositions.append(REVIEW)
            findings.append(
                "%s withstood %.1f V against a handling environment of %.1f V; it "
                "clears the environment but not the %.2f margin asked of it"
                % (device_id, withstand, handling, criteria["required_withstand_margin"])
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%s withstood %.1f V, under the %.1f V handling environment it "
                "will actually meet" % (device_id, withstand, handling)
            )
    if not network_state["in_band"]:
        dispositions.append(REVIEW)

    complete = not incomplete_levels and network_state["in_band"]
    if incomplete_levels:
        findings.append(
            "%s has %d ladder levels with no complete record; a withstand read "
            "off a ladder with holes in it is read off the wrong ladder"
            % (device_id, len(incomplete_levels))
        )
    verdict = _worst(dispositions) if complete else STRESS_INCOMPLETE
    return {
        "device_id": device_id,
        "verdict": verdict,
        "complete": complete,
        "withstand_volts": withstand,
        "withstand_band": esd_withstand_band(withstand, bands),
        "handling_environment_v": handling,
        "required_withstand_v": required,
        "worst_leakage_ratio": worst_leakage_ratio,
        "inconsistent_ladder": inconsistent,
        "incomplete_level_count": len(incomplete_levels),
        "levels": walked,
        "network": network_state,
        "findings": findings,
    }


def screen_blocking_diode_esd(
    lot,
    plan,
    network,
    spec=DEFAULT_NETWORK_SPEC,
    criteria=DEFAULT_ESD_CRITERIA,
    bands=DEFAULT_WITHSTAND_BANDS,
):
    """Clause 12.6.15 human-contact ESD robustness screen over one lot."""
    validate_esd_criteria(criteria)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    lot_id = _require_text("lot_id", lot.get("lot_id"))
    population = _require_count(
        "lot_population", lot.get("lot_population")
    )
    records = lot.get("devices")
    if not isinstance(records, (list, tuple)):
        raise ValueError("devices must be a list, got %r" % (records,))
    if len(records) > population:
        raise ValueError(
            "%d stressed devices against a lot population of %d on lot %s"
            % (len(records), population, lot_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = assess_blocking_diode_esd(
            record, plan, network, spec, criteria, bands
        )
        if result["device_id"] in seen:
            raise ValueError(
                "duplicate device id %r on lot %s" % (result["device_id"], lot_id)
            )
        seen.add(result["device_id"])
        screened.append(result)

    stressed = len(screened)
    counts = dict((state, 0) for state in ESD_DISPOSITIONS)
    counts[STRESS_INCOMPLETE] = 0
    findings = []
    dispositions = [ACCEPT]
    affected = 0
    open_devices = []
    lowest = None
    for result in screened:
        counts[result["verdict"]] += 1
        if result["complete"]:
            dispositions.append(result["verdict"])
        else:
            open_devices.append(result["device_id"])
        if result["findings"]:
            affected += 1
        lowest = (
            result["withstand_volts"]
            if lowest is None
            else min(lowest, result["withstand_volts"])
        )
        for finding in result["findings"]:
            findings.append(finding)

    share = stressed / float(population)
    if not _at_least(share, criteria["min_sample_fraction"]):
        findings.append(
            "%d of %d devices were stressed, a share of %.3f against the %.3f "
            "the criteria ask for; a lot cannot be sentenced from a sample too "
            "thin to represent it"
            % (stressed, population, share, criteria["min_sample_fraction"])
        )
        dispositions.append(REVIEW)

    allowed = criteria["max_affected_device_fraction"] * stressed
    if stressed and not _at_most(affected, allowed):
        dispositions.append(REVIEW)
        findings.append(
            "%d of %d stressed devices carry a robustness finding, past the "
            "%.2f the lot allowance permits" % (affected, stressed, allowed)
        )

    if open_devices:
        findings.append(
            "%d devices are left open on an incomplete stress" % len(open_devices)
        )
    complete = not open_devices and stressed > 0
    verdict = _worst(dispositions) if complete else STRESS_INCOMPLETE
    return {
        "lot_id": lot_id,
        "verdict": verdict,
        "complete": complete,
        "lot_population": population,
        "stressed_count": stressed,
        "sample_fraction": share,
        "affected_count": affected,
        "lowest_withstand_volts": lowest if lowest is not None else 0.0,
        "lot_withstand_band": esd_withstand_band(
            lowest if lowest is not None else 0.0, bands
        ),
        "counts": counts,
        "open_device_ids": open_devices,
        "devices": screened,
        "findings": findings,
    }
