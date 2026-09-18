"""Candidate layout trade for a MMIC: area against thermal spreading against loss.

Anchor: ECSS-Q-ST-60-12C clause 7.2.10 (arranging active devices and their
interconnects so die area, heat spreading and electrical performance are
balanced rather than one of them optimised alone). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each candidate arrangement: how many active cells, the pitch they
   are placed on, the die outline they occupy, the power they dissipate and the
   feed length of the combining network.
2. Derive the three competing metrics of the candidate:
     area   - the die outline in square millimetres;
     thermal- the peak channel temperature of the centre cell, which carries its
              own self-heating plus the mutual heating of every neighbour, that
              coupling falling off as the placement pitch opens up;
     loss   - the insertion loss of the combining interconnect, which grows as
              the same pitch opens up. The two pull in opposite directions,
              which is the whole content of the trade.
3. Reject the candidates that break a hard constraint - a channel temperature
   ceiling, a die area budget or an insertion-loss allowance - and keep them in
   the report with the reason, so an arrangement is never dropped silently.
4. Normalise each metric of the feasible candidates against the best value seen
   for that metric, apply the declared weights, and keep the lowest weighted
   score. Ties break on the candidate name so the trade is reproducible.
"""

import math

__all__ = [
    "CONSTRAINT_TOLERANCE",
    "validate_candidate",
    "validate_model",
    "validate_constraints",
    "validate_weights",
    "die_area_mm2",
    "combining_length_um",
    "thermal_spreading_resistance",
    "peak_channel_temperature_c",
    "interconnect_loss_db",
    "evaluate_candidate",
    "feasibility",
    "normalise_metric",
    "weighted_score",
    "optimise_layout",
]

# Constraint comparisons are ratios of floats that an exactly-sized candidate
# lands on. Absorb the representation error here, never by moving the ceiling.
CONSTRAINT_TOLERANCE = 1e-9

_METRICS = ("die_area_mm2", "peak_channel_temperature_c", "insertion_loss_db")


def _positive(label, value, allow_zero=False):
    """Return value as a float, raising when it is not a usable magnitude."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if number < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, number))
    elif number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _count(label, value, minimum=1):
    """Return value as an integer count of at least `minimum`."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def validate_candidate(candidate):
    """Return a normalised candidate arrangement.

    Keys: name, cells, cell_pitch_um, die_width_um, die_height_um,
    dissipated_power_w, optional feed_length_um and combining_factor.
    """
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping")
    for key in ("name", "cells", "cell_pitch_um", "die_width_um", "die_height_um",
                "dissipated_power_w"):
        if key not in candidate:
            raise ValueError("candidate missing required key '%s'" % key)
    name = candidate["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("candidate['name'] must be a non-empty string")
    cells = _count("candidate['cells']", candidate["cells"])
    pitch = _positive("candidate['cell_pitch_um']", candidate["cell_pitch_um"])
    width = _positive("candidate['die_width_um']", candidate["die_width_um"])
    height = _positive("candidate['die_height_um']", candidate["die_height_um"])
    power = _positive("candidate['dissipated_power_w']",
                      candidate["dissipated_power_w"])
    feed = _positive("candidate['feed_length_um']",
                     candidate.get("feed_length_um", 0.0), allow_zero=True)
    combining = _positive("candidate['combining_factor']",
                          candidate.get("combining_factor", 1.0))
    # The cells have to fit on the die they are placed on; a pitch that walks the
    # last cell off the outline is an input error, not a cheap area saving.
    span = (cells - 1) * pitch
    if span > width * (1.0 + CONSTRAINT_TOLERANCE):
        raise ValueError(
            "candidate '%s' places %d cells on a %g um pitch, spanning %g um "
            "across a %g um die" % (name.strip(), cells, pitch, span, width)
        )
    return {
        "name": name.strip(),
        "cells": cells,
        "cell_pitch_um": pitch,
        "die_width_um": width,
        "die_height_um": height,
        "dissipated_power_w": power,
        "feed_length_um": feed,
        "combining_factor": combining,
    }


def validate_model(model):
    """Return the normalised technology model shared by every candidate.

    Keys: baseplate_temperature_c, cell_thermal_resistance_k_per_w,
    reference_pitch_um, coupling_coefficient, loss_db_per_mm.
    """
    if not isinstance(model, dict):
        raise ValueError("model must be a mapping")
    for key in ("baseplate_temperature_c", "cell_thermal_resistance_k_per_w",
                "reference_pitch_um", "coupling_coefficient", "loss_db_per_mm"):
        if key not in model:
            raise ValueError("model missing required key '%s'" % key)
    base = model["baseplate_temperature_c"]
    if isinstance(base, bool) or not isinstance(base, (int, float)):
        raise ValueError("model['baseplate_temperature_c'] must be a real number")
    if not math.isfinite(float(base)):
        raise ValueError("model['baseplate_temperature_c'] must be finite")
    rth = _positive("model['cell_thermal_resistance_k_per_w']",
                    model["cell_thermal_resistance_k_per_w"])
    reference = _positive("model['reference_pitch_um']", model["reference_pitch_um"])
    coupling = _positive("model['coupling_coefficient']",
                         model["coupling_coefficient"], allow_zero=True)
    if coupling > 1.0:
        raise ValueError(
            "model['coupling_coefficient'] must not exceed 1.0, got %g" % coupling
        )
    loss = _positive("model['loss_db_per_mm']", model["loss_db_per_mm"],
                     allow_zero=True)
    return {
        "baseplate_temperature_c": float(base),
        "cell_thermal_resistance_k_per_w": rth,
        "reference_pitch_um": reference,
        "coupling_coefficient": coupling,
        "loss_db_per_mm": loss,
    }


def validate_constraints(constraints):
    """Return the normalised hard constraints of the trade."""
    if constraints is None:
        constraints = {}
    if not isinstance(constraints, dict):
        raise ValueError("constraints must be a mapping")
    out = {}
    ceiling = constraints.get("max_channel_temperature_c")
    if ceiling is not None:
        if isinstance(ceiling, bool) or not isinstance(ceiling, (int, float)):
            raise ValueError("constraints['max_channel_temperature_c'] must be real")
        if not math.isfinite(float(ceiling)):
            raise ValueError("constraints['max_channel_temperature_c'] must be finite")
        out["max_channel_temperature_c"] = float(ceiling)
    area = constraints.get("max_die_area_mm2")
    if area is not None:
        out["max_die_area_mm2"] = _positive("constraints['max_die_area_mm2']", area)
    loss = constraints.get("max_insertion_loss_db")
    if loss is not None:
        out["max_insertion_loss_db"] = _positive(
            "constraints['max_insertion_loss_db']", loss
        )
    return out


def validate_weights(weights):
    """Return the normalised objective weights; they must be positive and sum to one."""
    if weights is None:
        weights = {"die_area_mm2": 1.0 / 3.0,
                   "peak_channel_temperature_c": 1.0 / 3.0,
                   "insertion_loss_db": 1.0 / 3.0}
    if not isinstance(weights, dict):
        raise ValueError("weights must be a mapping")
    out = {}
    for key in _METRICS:
        if key not in weights:
            raise ValueError("weights missing required metric '%s'" % key)
        out[key] = _positive("weights['%s']" % key, weights[key])
    for key in weights:
        if key not in out:
            raise ValueError("weights carries unknown metric '%s'" % key)
    total = sum(out.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError("weights must sum to 1.0, got %g" % total)
    return out


def die_area_mm2(width_um, height_um):
    """Return the die outline area in square millimetres."""
    width = _positive("width_um", width_um)
    height = _positive("height_um", height_um)
    return (width * height) / 1.0e6


def combining_length_um(cells, cell_pitch_um, combining_factor=1.0,
                        feed_length_um=0.0):
    """Return the interconnect length the combining network has to run."""
    count = _count("cells", cells)
    pitch = _positive("cell_pitch_um", cell_pitch_um)
    factor = _positive("combining_factor", combining_factor)
    feed = _positive("feed_length_um", feed_length_um, allow_zero=True)
    return (count - 1) * pitch * factor + feed


def thermal_spreading_resistance(cell_rth_k_per_w, cells, cell_pitch_um,
                                 reference_pitch_um, coupling_coefficient):
    """Return the effective thermal resistance seen by the hottest cell.

    The centre cell carries its own self-heating plus a share of every
    neighbour's, that share falling off with the placement pitch and with how
    many cells away the neighbour sits.
    """
    rth = _positive("cell_rth_k_per_w", cell_rth_k_per_w)
    count = _count("cells", cells)
    pitch = _positive("cell_pitch_um", cell_pitch_um)
    reference = _positive("reference_pitch_um", reference_pitch_um)
    coupling = _positive("coupling_coefficient", coupling_coefficient,
                         allow_zero=True)
    if coupling > 1.0:
        raise ValueError("coupling_coefficient must not exceed 1.0, got %g" % coupling)
    centre = (count - 1) // 2
    mutual = 0.0
    for index in range(count):
        if index == centre:
            continue
        separation = abs(index - centre)
        mutual += coupling * rth * reference / (pitch * separation)
    return rth + mutual


def peak_channel_temperature_c(baseplate_temperature_c, dissipated_power_w, cells,
                               effective_rth_k_per_w):
    """Return the channel temperature of the hottest cell."""
    if isinstance(baseplate_temperature_c, bool) or not isinstance(
            baseplate_temperature_c, (int, float)):
        raise ValueError("baseplate_temperature_c must be a real number")
    base = float(baseplate_temperature_c)
    if not math.isfinite(base):
        raise ValueError("baseplate_temperature_c must be finite")
    power = _positive("dissipated_power_w", dissipated_power_w)
    count = _count("cells", cells)
    rth = _positive("effective_rth_k_per_w", effective_rth_k_per_w)
    return base + (power / count) * rth


def interconnect_loss_db(length_um, loss_db_per_mm):
    """Return the insertion loss of a run of interconnect."""
    length = _positive("length_um", length_um, allow_zero=True)
    per_mm = _positive("loss_db_per_mm", loss_db_per_mm, allow_zero=True)
    return (length / 1000.0) * per_mm


def evaluate_candidate(candidate, model):
    """Return the three trade metrics of one candidate arrangement."""
    cand = validate_candidate(candidate)
    tech = validate_model(model)
    rth = thermal_spreading_resistance(
        tech["cell_thermal_resistance_k_per_w"],
        cand["cells"],
        cand["cell_pitch_um"],
        tech["reference_pitch_um"],
        tech["coupling_coefficient"],
    )
    length = combining_length_um(
        cand["cells"], cand["cell_pitch_um"], cand["combining_factor"],
        cand["feed_length_um"],
    )
    return {
        "name": cand["name"],
        "cells": cand["cells"],
        "cell_pitch_um": cand["cell_pitch_um"],
        "effective_rth_k_per_w": rth,
        "combining_length_um": length,
        "die_area_mm2": die_area_mm2(cand["die_width_um"], cand["die_height_um"]),
        "peak_channel_temperature_c": peak_channel_temperature_c(
            tech["baseplate_temperature_c"], cand["dissipated_power_w"],
            cand["cells"], rth,
        ),
        "insertion_loss_db": interconnect_loss_db(length, tech["loss_db_per_mm"]),
    }


def feasibility(record, constraints=None):
    """Return (feasible, reasons) for one evaluated candidate."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in _METRICS:
        if key not in record:
            raise ValueError("record missing metric '%s'" % key)
    limits = validate_constraints(constraints)
    reasons = []
    ceiling = limits.get("max_channel_temperature_c")
    if ceiling is not None:
        value = record["peak_channel_temperature_c"]
        if value > ceiling + CONSTRAINT_TOLERANCE * max(1.0, abs(ceiling)):
            reasons.append(
                "peak channel temperature %.4f C exceeds the %.4f C ceiling"
                % (value, ceiling)
            )
    budget = limits.get("max_die_area_mm2")
    if budget is not None:
        value = record["die_area_mm2"]
        if value > budget + CONSTRAINT_TOLERANCE * max(1.0, budget):
            reasons.append(
                "die area %.6f mm2 exceeds the %.6f mm2 budget" % (value, budget)
            )
    allowance = limits.get("max_insertion_loss_db")
    if allowance is not None:
        value = record["insertion_loss_db"]
        if value > allowance + CONSTRAINT_TOLERANCE * max(1.0, allowance):
            reasons.append(
                "insertion loss %.4f dB exceeds the %.4f dB allowance"
                % (value, allowance)
            )
    return (not reasons, reasons)


def normalise_metric(value, best):
    """Return how many times the best value of a metric this candidate costs."""
    current = _positive("value", value)
    reference = _positive("best", best)
    return current / reference


def weighted_score(normalised, weights):
    """Return the weighted objective of one candidate; lower is better."""
    checked = validate_weights(weights)
    if not isinstance(normalised, dict):
        raise ValueError("normalised must be a mapping")
    total = 0.0
    for key, weight in checked.items():
        if key not in normalised:
            raise ValueError("normalised missing metric '%s'" % key)
        total += weight * _positive("normalised['%s']" % key, normalised[key])
    return total


def optimise_layout(candidates, model, constraints=None, weights=None):
    """Run the clause 7.2.10 arrangement trade over a set of candidates."""
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("candidates must be a non-empty sequence")
    checked_weights = validate_weights(weights)
    records = [evaluate_candidate(c, model) for c in candidates]
    seen = set()
    for record in records:
        if record["name"] in seen:
            raise ValueError("candidate '%s' is offered twice" % record["name"])
        seen.add(record["name"])
    feasible = []
    rejected = []
    for record in records:
        ok, reasons = feasibility(record, constraints)
        entry = dict(record)
        entry["reasons"] = reasons
        if ok:
            feasible.append(entry)
        else:
            rejected.append(entry)
    findings = []
    for entry in sorted(rejected, key=lambda r: r["name"]):
        for reason in entry["reasons"]:
            findings.append("%s: %s" % (entry["name"], reason))
    if not feasible:
        findings.append("no candidate arrangement satisfies every constraint")
        return {
            "records": sorted(records, key=lambda r: r["name"]),
            "feasible": [],
            "rejected": sorted(rejected, key=lambda r: r["name"]),
            "ranking": [],
            "selected": None,
            "weights": checked_weights,
            "findings": findings,
        }
    best = {key: min(e[key] for e in feasible) for key in _METRICS}
    for entry in feasible:
        entry["normalised"] = {
            key: normalise_metric(entry[key], best[key]) for key in _METRICS
        }
        entry["score"] = weighted_score(entry["normalised"], checked_weights)
    ranking = sorted(feasible, key=lambda e: (e["score"], e["name"]))
    if len(feasible) == 1:
        findings.append(
            "only one arrangement survived the constraints; the trade has no "
            "alternative to weigh it against"
        )
    return {
        "records": sorted(records, key=lambda r: r["name"]),
        "feasible": feasible,
        "rejected": sorted(rejected, key=lambda r: r["name"]),
        "ranking": ranking,
        "selected": ranking[0],
        "weights": checked_weights,
        "findings": findings,
    }
