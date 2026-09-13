#!/usr/bin/env python3
"""Receiver and transducer overload precautions for the measurement chain of
ECSS-E-ST-20-07C clause 5.2.5.3.

Paraphrased, implementable procedure (no verbatim standard text):

* Every electromagnetic measurement chain that carries a transducer output
  (antenna, current probe, coupling network, voltage probe) to an EMI
  receiver has a linear operating window. A stage driven above its
  compression point reports a level that is both low and non-reproducible,
  so the measurement is invalid rather than conservative.
* The chain is walked stage by stage from the transducer output to the
  receiver input, accumulating gain and loss in dB, so the level presented
  to the input of every stage is known before the run starts.
* Each stage carries a compression point (top of its linear window) and a
  damage threshold (the level above which the stage is harmed). A stage
  above its damage threshold is a stop-work condition, not a margin issue.
* Where a stage sits above its compression point, input attenuation is
  added in whole attenuator steps until the whole chain is linear again,
  and the resulting receiver level is re-checked against the noise floor so
  the emission limit is still measurable with the required headroom.
* Attenuation added behind the transducer cannot rescue a transducer that
  is itself saturated: that case is resolved by reducing the coupling
  (greater separation, a lower-factor transducer) instead.
* The precaution is demonstrated on the bench by inserting a known pad and
  confirming the indicated level falls by the same number of dB within a
  stated tolerance.

Stdlib only, offline, deterministic.
"""

import math

# Named tolerance that absorbs binary floating-point representation error in
# sums and differences of dB quantities. It is NOT an engineering allowance:
# the limits themselves are never widened.
DB_EPS = 1e-9

TRANSDUCER = "transducer"
RECEIVER = "receiver"
PREAMPLIFIER = "preamplifier"

PASSIVE_LOSS_KINDS = ("cable", "attenuator", "filter")
STAGE_KINDS = (TRANSDUCER, RECEIVER, PREAMPLIFIER) + PASSIVE_LOSS_KINDS
# Stages that carry an active or detector linear window and must declare it.
ACTIVE_WINDOW_KINDS = (TRANSDUCER, PREAMPLIFIER, RECEIVER)

# 50 ohm conversion offset: dBm = dBuV - 90 - 10*log10(R)
_DBUV_TO_DBM_BASE = 90.0


def _not_above(value, limit):
    """True when value does not exceed limit, absorbing dB representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=DB_EPS)


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def dbuv_to_dbm(level_dbuv, impedance_ohm=50.0):
    """Convert a level in dB microvolt to dBm across a resistive impedance."""
    level_dbuv = _require_number(level_dbuv, "level_dbuv")
    impedance_ohm = _require_number(impedance_ohm, "impedance_ohm")
    if impedance_ohm <= 0.0:
        raise ValueError("impedance_ohm must be positive, got %r" % (impedance_ohm,))
    return level_dbuv - _DBUV_TO_DBM_BASE - 10.0 * math.log10(impedance_ohm)


def dbm_to_dbuv(level_dbm, impedance_ohm=50.0):
    """Convert a level in dBm to dB microvolt across a resistive impedance."""
    level_dbm = _require_number(level_dbm, "level_dbm")
    impedance_ohm = _require_number(impedance_ohm, "impedance_ohm")
    if impedance_ohm <= 0.0:
        raise ValueError("impedance_ohm must be positive, got %r" % (impedance_ohm,))
    return level_dbm + _DBUV_TO_DBM_BASE + 10.0 * math.log10(impedance_ohm)


def transducer_output_dbuv(quantity_level, transducer_factor_db):
    """Terminal level produced by a transducer for a given field or current.

    The transducer factor is the additive correction that maps the terminal
    level back to the measured quantity, so the terminal level is the
    quantity level minus the factor.
    """
    quantity_level = _require_number(quantity_level, "quantity_level")
    transducer_factor_db = _require_number(transducer_factor_db, "transducer_factor_db")
    return quantity_level - transducer_factor_db


def stage_gain_db(stage):
    """Signed dB contribution of one chain stage (positive = gain)."""
    _validate_stage(stage)
    kind = stage["kind"]
    if kind == PREAMPLIFIER:
        return float(stage["gain_db"])
    if kind in PASSIVE_LOSS_KINDS:
        return -float(stage["loss_db"])
    return 0.0


def _validate_stage(stage):
    if not isinstance(stage, dict):
        raise ValueError("each chain stage must be a mapping, got %r" % (stage,))
    name = stage.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("chain stage needs a non-empty 'name', got %r" % (name,))
    kind = stage.get("kind")
    if kind not in STAGE_KINDS:
        raise ValueError(
            "stage %r has unrecognized kind %r (expected one of %s)"
            % (name, kind, ", ".join(sorted(STAGE_KINDS)))
        )
    if kind == PREAMPLIFIER:
        gain = _require_number(stage.get("gain_db"), "stage %r gain_db" % name)
        if gain <= 0.0:
            raise ValueError("stage %r gain_db must be positive, got %r" % (name, gain))
    if kind in PASSIVE_LOSS_KINDS:
        loss = _require_number(stage.get("loss_db"), "stage %r loss_db" % name)
        if loss < 0.0:
            raise ValueError(
                "stage %r loss_db must not be negative, got %r" % (name, loss)
            )
    compression = stage.get("compression_point_dbm")
    damage = stage.get("damage_threshold_dbm")
    if compression is not None:
        compression = _require_number(compression, "stage %r compression_point_dbm" % name)
    if damage is not None:
        damage = _require_number(damage, "stage %r damage_threshold_dbm" % name)
    if compression is not None and damage is not None and damage < compression:
        raise ValueError(
            "stage %r damage_threshold_dbm (%r) is below its compression_point_dbm (%r)"
            % (name, damage, compression)
        )
    return stage


def chain_levels_dbm(source_level_dbm, chain):
    """Propagate a transducer terminal level through the ordered chain.

    Returns one record per stage with the level presented to that stage's
    input and the level leaving it, both in dBm.
    """
    source_level_dbm = _require_number(source_level_dbm, "source_level_dbm")
    if not isinstance(chain, (list, tuple)) or not chain:
        raise ValueError("chain must be a non-empty ordered sequence of stages")
    names = []
    for stage in chain:
        _validate_stage(stage)
        names.append(stage["name"])
    if len(set(names)) != len(names):
        raise ValueError("chain stage names must be unique, got %r" % (names,))
    if chain[0]["kind"] != TRANSDUCER:
        raise ValueError("chain must start at the transducer, starts at %r" % (chain[0]["kind"],))
    if chain[-1]["kind"] != RECEIVER:
        raise ValueError("chain must end at the receiver, ends at %r" % (chain[-1]["kind"],))
    for stage in chain[1:-1]:
        if stage["kind"] in (TRANSDUCER, RECEIVER):
            raise ValueError(
                "stage %r of kind %r may only appear at a chain end"
                % (stage["name"], stage["kind"])
            )
    records = []
    level = source_level_dbm
    for stage in chain:
        gain = stage_gain_db(stage)
        record = {
            "name": stage["name"],
            "kind": stage["kind"],
            "input_dbm": level,
            "gain_db": gain,
            "output_dbm": level + gain,
        }
        records.append(record)
        level = record["output_dbm"]
    return records


def evaluate_stage_overload(stage, input_dbm):
    """Categorize one stage as linear, overloaded or at damage risk."""
    _validate_stage(stage)
    input_dbm = _require_number(input_dbm, "input_dbm")
    kind = stage["kind"]
    compression = stage.get("compression_point_dbm")
    damage = stage.get("damage_threshold_dbm")
    status = "linear"
    if damage is not None and not _not_above(input_dbm, float(damage)):
        status = "damage-risk"
    elif compression is not None and not _not_above(input_dbm, float(compression)):
        status = "overload"
    elif compression is None and damage is None and kind in ACTIVE_WINDOW_KINDS:
        # Only the stages that can compress are expected to declare a linear
        # window; a purely passive loss element has none to declare.
        status = "uncategorized"
    return {
        "name": stage["name"],
        "kind": stage["kind"],
        "input_dbm": input_dbm,
        "status": status,
        "compression_margin_db": (
            None if compression is None else float(compression) - input_dbm
        ),
        "damage_margin_db": (None if damage is None else float(damage) - input_dbm),
    }


def assess_chain(source_level_dbm, chain):
    """Evaluate every stage of the chain against its own linear window."""
    records = chain_levels_dbm(source_level_dbm, chain)
    evaluations = []
    for stage, record in zip(chain, records):
        evaluation = evaluate_stage_overload(stage, record["input_dbm"])
        evaluation["output_dbm"] = record["output_dbm"]
        evaluations.append(evaluation)
    return evaluations


def worst_overload_excess_db(evaluations):
    """Largest amount by which any stage sits above its compression point."""
    if not isinstance(evaluations, (list, tuple)) or not evaluations:
        raise ValueError("evaluations must be a non-empty sequence")
    excess = 0.0
    for evaluation in evaluations:
        margin = evaluation.get("compression_margin_db")
        if margin is None:
            continue
        if -float(margin) > excess:
            excess = -float(margin)
    return excess


def required_input_attenuation_db(evaluations, step_db, available_attenuation_db):
    """Whole attenuator steps needed behind the transducer to restore linearity.

    Attenuation inserted behind the transducer shifts every downstream stage
    by the same amount, so the needed value is the worst compression excess
    rounded up to the attenuator step size. A saturated transducer is called
    out separately because downstream attenuation cannot resolve it.
    """
    step_db = _require_number(step_db, "step_db")
    available_attenuation_db = _require_number(
        available_attenuation_db, "available_attenuation_db"
    )
    if step_db <= 0.0:
        raise ValueError("step_db must be positive, got %r" % (step_db,))
    if available_attenuation_db < 0.0:
        raise ValueError(
            "available_attenuation_db must not be negative, got %r"
            % (available_attenuation_db,)
        )
    transducer_saturated = any(
        e.get("kind") == TRANSDUCER and e.get("status") in ("overload", "damage-risk")
        for e in evaluations
    )
    excess = worst_overload_excess_db(evaluations)
    if excess <= DB_EPS:
        steps = 0
    else:
        steps = int(math.ceil((excess - DB_EPS) / step_db))
        if steps < 1:
            steps = 1
    required = steps * step_db
    feasible = _not_above(required, available_attenuation_db) and not transducer_saturated
    return {
        "excess_db": excess,
        "steps": steps,
        "required_attenuation_db": required,
        "available_attenuation_db": available_attenuation_db,
        "transducer_saturated": transducer_saturated,
        "feasible": feasible,
    }


def recommend_precautions(evaluations, attenuation_plan):
    """Ordered precaution tokens for the observed overload pattern."""
    if not isinstance(attenuation_plan, dict):
        raise ValueError("attenuation_plan must be the mapping from required_input_attenuation_db")
    actions = []
    if any(e.get("status") == "damage-risk" for e in evaluations):
        actions.append("stop-and-protect-receiver-input")
    if attenuation_plan.get("transducer_saturated"):
        actions.append("reduce-transducer-coupling")
    elif attenuation_plan.get("required_attenuation_db", 0.0) > 0.0:
        if attenuation_plan.get("feasible"):
            actions.append("insert-input-attenuation")
        else:
            actions.append("extend-attenuator-range")
        if any(
            e.get("kind") == PREAMPLIFIER and e.get("status") in ("overload", "damage-risk")
            for e in evaluations
        ):
            actions.append("bypass-preamplifier")
        if any(
            e.get("kind") == RECEIVER and e.get("status") in ("overload", "damage-risk")
            for e in evaluations
        ):
            actions.append("engage-preselector-filter")
    if not actions:
        actions.append("proceed-with-measurement")
    return actions


def measurement_headroom_db(
    limit_referred_dbm, noise_floor_dbm, min_headroom_db, added_attenuation_db=0.0
):
    """Check the emission limit stays measurable after adding attenuation."""
    limit_referred_dbm = _require_number(limit_referred_dbm, "limit_referred_dbm")
    noise_floor_dbm = _require_number(noise_floor_dbm, "noise_floor_dbm")
    min_headroom_db = _require_number(min_headroom_db, "min_headroom_db")
    added_attenuation_db = _require_number(added_attenuation_db, "added_attenuation_db")
    if min_headroom_db < 0.0:
        raise ValueError("min_headroom_db must not be negative, got %r" % (min_headroom_db,))
    if added_attenuation_db < 0.0:
        raise ValueError(
            "added_attenuation_db must not be negative, got %r" % (added_attenuation_db,)
        )
    headroom = (limit_referred_dbm - added_attenuation_db) - noise_floor_dbm
    sufficient = _not_above(min_headroom_db, headroom)
    return {
        "headroom_db": headroom,
        "required_headroom_db": min_headroom_db,
        "sufficient": sufficient,
    }


def attenuation_insertion_check(
    indicated_before_dbuv, indicated_after_dbuv, inserted_attenuation_db, tolerance_db
):
    """Bench demonstration that the chain is operating linearly.

    Inserting a known pad must move the indicated level by the same number
    of dB; a smaller change means a stage was compressed before the pad
    went in.
    """
    indicated_before_dbuv = _require_number(indicated_before_dbuv, "indicated_before_dbuv")
    indicated_after_dbuv = _require_number(indicated_after_dbuv, "indicated_after_dbuv")
    inserted_attenuation_db = _require_number(
        inserted_attenuation_db, "inserted_attenuation_db"
    )
    tolerance_db = _require_number(tolerance_db, "tolerance_db")
    if inserted_attenuation_db <= 0.0:
        raise ValueError(
            "inserted_attenuation_db must be positive, got %r" % (inserted_attenuation_db,)
        )
    if tolerance_db <= 0.0:
        raise ValueError("tolerance_db must be positive, got %r" % (tolerance_db,))
    observed = indicated_before_dbuv - indicated_after_dbuv
    deviation = observed - inserted_attenuation_db
    linear = _not_above(abs(deviation), tolerance_db)
    return {
        "observed_change_db": observed,
        "expected_change_db": inserted_attenuation_db,
        "deviation_db": deviation,
        "linear": linear,
        "verdict": "linear" if linear else "compressed-before-insertion",
    }


def assess_overload_precautions(config):
    """End-to-end clause 5.2.5.3 assessment for one measurement chain."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    for key in ("quantity_level_dbuv", "transducer_factor_db", "chain"):
        if key not in config:
            raise ValueError("config missing required key %r" % (key,))
    terminal_dbuv = transducer_output_dbuv(
        config["quantity_level_dbuv"], config["transducer_factor_db"]
    )
    impedance = config.get("impedance_ohm", 50.0)
    source_dbm = dbuv_to_dbm(terminal_dbuv, impedance)
    evaluations = assess_chain(source_dbm, config["chain"])
    plan = required_input_attenuation_db(
        evaluations,
        config.get("attenuator_step_db", 10.0),
        config.get("available_attenuation_db", 40.0),
    )
    headroom = measurement_headroom_db(
        config.get("limit_referred_dbm", source_dbm),
        config.get("noise_floor_dbm", source_dbm - 40.0),
        config.get("min_headroom_db", 6.0),
        plan["required_attenuation_db"] if plan["feasible"] else 0.0,
    )
    actions = recommend_precautions(evaluations, plan)
    findings = []
    for evaluation in evaluations:
        if evaluation["status"] == "damage-risk":
            findings.append("stage %s above damage threshold" % evaluation["name"])
        elif evaluation["status"] == "overload":
            findings.append("stage %s above compression point" % evaluation["name"])
        elif evaluation["status"] == "uncategorized":
            findings.append("stage %s has no declared linear window" % evaluation["name"])
    if not plan["feasible"] and plan["required_attenuation_db"] > 0.0:
        findings.append("chain cannot be made linear with the attenuation on hand")
    if not headroom["sufficient"]:
        findings.append("limit no longer measurable above the noise floor")
    check = config.get("insertion_check")
    if check is not None:
        result = attenuation_insertion_check(
            check["indicated_before_dbuv"],
            check["indicated_after_dbuv"],
            check["inserted_attenuation_db"],
            check.get("tolerance_db", 1.0),
        )
        if not result["linear"]:
            findings.append("attenuation insertion check did not reproduce the pad value")
    else:
        result = None
        findings.append("no attenuation insertion check on record")
    return {
        "terminal_level_dbuv": terminal_dbuv,
        "source_level_dbm": source_dbm,
        "evaluations": evaluations,
        "attenuation_plan": plan,
        "headroom": headroom,
        "insertion_check": result,
        "actions": actions,
        "findings": findings,
        "compliant": not findings,
    }
