"""Limiter state integrity across main bus start up and zero volt recovery.

Anchor: ECSS-E-ST-20C clause 5.2.7.4.1 (the state a current limiter is
actually in has to be the state it was intended to be in, for the whole of
main bus start up and for the recovery that follows a fall to zero volts).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the recorded start-up profile: one sample per instant, carrying
   the bus voltage, the intended state, the state the limiter output was
   actually in, and the state the unit reported back.
2. Establish the supply window. A limiter's control and status logic only
   holds a defined state once the bus has risen past the supply floor the
   unit declares, so samples below that floor are indeterminate evidence,
   not agreement and not a mismatch.
3. Find every zero volt excursion: a contiguous run of samples at or under
   the declared zero volt threshold. Each one ends a start up and begins a
   recovery.
4. After each excursion, once the supply is valid again and the declared
   settling time has elapsed, require the limiter to be back in the default
   state the design declares for a cold start.
5. Inside the supply window, weigh three things per sample: intended against
   actual (state integrity), reported against actual (status integrity), and
   whether a status was reported at all.
6. Report the per-sample records, the excursions, and every finding. A
   profile that never reached the supply floor is a coverage finding in its
   own right rather than a clean pass.
"""

import math

__all__ = [
    "VOLTAGE_TOLERANCE_V",
    "TIME_TOLERANCE_S",
    "VALID_STATES",
    "normalise_state",
    "validate_sample",
    "validate_profile",
    "supply_valid",
    "supply_window",
    "zero_volt_excursions",
    "evaluate_sample",
    "evaluate_profile",
    "recovery_verdicts",
    "assess_status_integrity",
]

# Bus voltages are differences and products of measured quantities, so a
# sample cut exactly to the supply floor can land a unit in the last place on
# either side of it. Absorb that here rather than by moving the floor.
VOLTAGE_TOLERANCE_V = 1e-9
TIME_TOLERANCE_S = 1e-9

VALID_STATES = ("on", "off")


def _real_number(value, label):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _non_negative(value, label):
    number = _real_number(value, label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def normalise_state(value, label="state"):
    """Return 'on' or 'off' for a declared limiter state."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower().replace("_", "-")
    aliases = {
        "on": "on",
        "enabled": "on",
        "conducting": "on",
        "closed": "on",
        "off": "off",
        "disabled": "off",
        "tripped": "off",
        "open": "off",
    }
    if text not in aliases:
        raise ValueError(
            "%s must name one of %s, got %r" % (label, VALID_STATES, value)
        )
    return aliases[text]


def validate_sample(sample, index):
    """Return one normalised start-up sample record."""
    if not isinstance(sample, dict):
        raise ValueError("sample[%d] must be a mapping" % index)
    for key in ("time_s", "bus_voltage_v", "intended_state", "actual_state"):
        if key not in sample:
            raise ValueError("sample[%d] missing required key '%s'" % (index, key))
    reported = sample.get("reported_state")
    record = {
        "index": index,
        "time_s": _real_number(sample["time_s"], "sample[%d].time_s" % index),
        "bus_voltage_v": _non_negative(
            sample["bus_voltage_v"], "sample[%d].bus_voltage_v" % index
        ),
        "intended_state": normalise_state(
            sample["intended_state"], "sample[%d].intended_state" % index
        ),
        "actual_state": normalise_state(
            sample["actual_state"], "sample[%d].actual_state" % index
        ),
        "reported_state": (
            None
            if reported is None
            else normalise_state(reported, "sample[%d].reported_state" % index)
        ),
    }
    return record


def validate_profile(samples):
    """Return the validated, time-ordered start-up profile."""
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence of sample mappings")
    records = [validate_sample(s, i) for i, s in enumerate(samples)]
    for i in range(1, len(records)):
        if records[i]["time_s"] <= records[i - 1]["time_s"]:
            raise ValueError(
                "sample times must strictly increase; sample[%d] at %g does not "
                "follow sample[%d] at %g"
                % (i, records[i]["time_s"], i - 1, records[i - 1]["time_s"])
            )
    return records


def supply_valid(bus_voltage_v, logic_supply_floor_v):
    """Return True when the control and status logic has a defined supply."""
    voltage = _non_negative(bus_voltage_v, "bus_voltage_v")
    floor = _non_negative(logic_supply_floor_v, "logic_supply_floor_v")
    return voltage >= floor - VOLTAGE_TOLERANCE_V


def supply_window(records, logic_supply_floor_v):
    """Return the indices of the samples whose supply is valid."""
    floor = _non_negative(logic_supply_floor_v, "logic_supply_floor_v")
    return [r["index"] for r in records if supply_valid(r["bus_voltage_v"], floor)]


def zero_volt_excursions(records, zero_volt_threshold_v):
    """Return the contiguous runs of samples at or under the zero volt threshold."""
    threshold = _non_negative(zero_volt_threshold_v, "zero_volt_threshold_v")
    runs = []
    open_run = None
    for record in records:
        at_zero = record["bus_voltage_v"] <= threshold + VOLTAGE_TOLERANCE_V
        if at_zero and open_run is None:
            open_run = {
                "start_index": record["index"],
                "end_index": record["index"],
                "start_time_s": record["time_s"],
                "end_time_s": record["time_s"],
            }
        elif at_zero:
            open_run["end_index"] = record["index"]
            open_run["end_time_s"] = record["time_s"]
        elif open_run is not None:
            runs.append(open_run)
            open_run = None
    if open_run is not None:
        runs.append(open_run)
    return runs


def evaluate_sample(record, logic_supply_floor_v):
    """Return the state and status verdicts for one sample."""
    if not isinstance(record, dict) or "bus_voltage_v" not in record:
        raise ValueError("record must be a validated sample mapping")
    valid = supply_valid(record["bus_voltage_v"], logic_supply_floor_v)
    if not valid:
        state_verdict = "indeterminate"
        status_verdict = "indeterminate"
    else:
        state_verdict = (
            "match" if record["actual_state"] == record["intended_state"] else "mismatch"
        )
        if record["reported_state"] is None:
            status_verdict = "unreported"
        elif record["reported_state"] == record["actual_state"]:
            status_verdict = "agree"
        else:
            status_verdict = "disagree"
    out = dict(record)
    out["supply_valid"] = valid
    out["state_verdict"] = state_verdict
    out["status_verdict"] = status_verdict
    return out


def evaluate_profile(records, logic_supply_floor_v):
    """Return the per-sample verdict records for the whole profile."""
    return [evaluate_sample(r, logic_supply_floor_v) for r in records]


def recovery_verdicts(evaluated, excursions, default_state, settle_time_s=0.0):
    """Return one verdict per zero volt excursion about the state it came back in."""
    default_state = normalise_state(default_state, "default_state")
    settle = _non_negative(settle_time_s, "settle_time_s")
    verdicts = []
    for excursion in excursions:
        deadline = excursion["end_time_s"] + settle
        observed = None
        for record in evaluated:
            if record["index"] <= excursion["end_index"]:
                continue
            if not record["supply_valid"]:
                continue
            if record["time_s"] < deadline - TIME_TOLERANCE_S:
                continue
            observed = record
            break
        if observed is None:
            verdicts.append(
                {
                    "excursion": excursion,
                    "observed_index": None,
                    "observed_state": None,
                    "verdict": "not-observed",
                }
            )
            continue
        verdicts.append(
            {
                "excursion": excursion,
                "observed_index": observed["index"],
                "observed_state": observed["actual_state"],
                "verdict": (
                    "recovered"
                    if observed["actual_state"] == default_state
                    else "wrong-state"
                ),
            }
        )
    return verdicts


def assess_status_integrity(spec):
    """Run the full clause 5.2.7.4.1 state and status integrity assessment.

    spec keys: samples, logic_supply_floor_v, zero_volt_threshold_v,
    default_state, optional settle_time_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "samples",
        "logic_supply_floor_v",
        "zero_volt_threshold_v",
        "default_state",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    floor = _non_negative(spec["logic_supply_floor_v"], "logic_supply_floor_v")
    threshold = _non_negative(spec["zero_volt_threshold_v"], "zero_volt_threshold_v")
    if threshold >= floor - VOLTAGE_TOLERANCE_V:
        raise ValueError(
            "zero_volt_threshold_v %g must sit below the logic supply floor %g"
            % (threshold, floor)
        )
    records = validate_profile(spec["samples"])
    evaluated = evaluate_profile(records, floor)
    excursions = zero_volt_excursions(records, threshold)
    recoveries = recovery_verdicts(
        evaluated, excursions, spec["default_state"], spec.get("settle_time_s", 0.0)
    )

    findings = []
    mismatches = [r for r in evaluated if r["state_verdict"] == "mismatch"]
    disagreements = [r for r in evaluated if r["status_verdict"] == "disagree"]
    unreported = [r for r in evaluated if r["status_verdict"] == "unreported"]
    valid_indices = [r["index"] for r in evaluated if r["supply_valid"]]

    for record in mismatches:
        findings.append(
            "sample %d at %g s: limiter is %s while the intended state is %s"
            % (
                record["index"],
                record["time_s"],
                record["actual_state"],
                record["intended_state"],
            )
        )
    for record in disagreements:
        findings.append(
            "sample %d at %g s: reported status %s does not describe the actual "
            "state %s" % (record["index"], record["time_s"], record["reported_state"],
                          record["actual_state"])
        )
    for record in unreported:
        findings.append(
            "sample %d at %g s: no status reported while the supply was valid"
            % (record["index"], record["time_s"])
        )
    for verdict in recoveries:
        if verdict["verdict"] == "not-observed":
            findings.append(
                "zero volt excursion ending at %g s: the recovered state was never "
                "observed with a valid supply" % verdict["excursion"]["end_time_s"]
            )
        elif verdict["verdict"] == "wrong-state":
            findings.append(
                "zero volt excursion ending at %g s: recovered in %s rather than the "
                "declared default %s"
                % (
                    verdict["excursion"]["end_time_s"],
                    verdict["observed_state"],
                    normalise_state(spec["default_state"], "default_state"),
                )
            )
    if not valid_indices:
        findings.append(
            "the profile never reached the logic supply floor of %g V, so no sample "
            "carries evidence about the limiter state" % floor
        )

    return {
        "records": evaluated,
        "excursions": excursions,
        "recoveries": recoveries,
        "supply_valid_indices": valid_indices,
        "mismatch_count": len(mismatches),
        "status_disagreement_count": len(disagreements),
        "unreported_count": len(unreported),
        "findings": findings,
        "compliant": not findings,
    }
