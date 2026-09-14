"""Rated temperature range versus equipment operating envelope, Class 1 parts.

Anchor: ECSS-Q-ST-60-13C clause 4.2.2.6 (matching the rated temperature limits
of a commercial part to the operating envelope of the equipment it sits in,
for the highest assurance class).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The envelope the equipment is qualified to is not the temperature the part
  sees. Two corrections separate them. The first is self-heating: the part
  dissipates power across the thermal resistance between its mounting
  reference and the point its rating is quoted at, so the hot end of the part
  requirement sits above the hot end of the equipment envelope. The cold end
  carries no such rise -- dissipation only helps there -- so the cold
  requirement is taken with the part unpowered, which is the conservative
  case.
* The second is the uncertainty of the thermal prediction itself. A margin is
  added at both ends, and how large it is depends on how the temperature was
  established: a measured thermal balance earns the smallest margin, a
  correlated model more, an uncorrelated model more again, and a bare
  engineering estimate the most.
* The part then has to cover the corrected requirement at both ends. Headroom
  is reported separately per end, because the two ends fail for different
  reasons and are fixed by different actions.
* A part whose rating falls short is not automatically excluded, but the only
  route that keeps it is a substantiated extension of the rated range. A
  shortfall with no extension evidence on file is a finding, and a shortfall
  with an extension claim is a finding of a different kind -- it stays open
  until the evidence behind the claim is reviewed.
"""

from __future__ import annotations

import math

# Rated ranges implied by the commonly quoted commercial part grades, in
# degrees Celsius. An explicit rated range on the part always wins over the
# grade; the grade is only a fallback for a part whose datasheet limits were
# not transcribed.
GRADE_RATED_RANGES_C = {
    "commercial-grade": (0.0, 70.0),
    "industrial-grade": (-40.0, 85.0),
    "extended-industrial-grade": (-40.0, 105.0),
    "automotive-grade": (-40.0, 125.0),
    "military-temperature-grade": (-55.0, 125.0),
}

# Uncertainty margin added at BOTH ends of the envelope, keyed on how the
# equipment temperature was established.
THERMAL_KNOWLEDGE_MARGIN_K = {
    "measured-thermal-balance-test": 5.0,
    "correlated-thermal-model": 10.0,
    "uncorrelated-thermal-model": 15.0,
    "engineering-estimate": 20.0,
}

VERDICTS = (
    "temperature-range-covered",
    "hot-end-shortfall",
    "cold-end-shortfall",
    "both-ends-shortfall",
)

# A part whose rating lands exactly on the corrected requirement passes. The
# requirement is a sum of Celsius terms and can differ from a transcribed
# datasheet limit by a few units in the last place; the policy itself is never
# relaxed by this tolerance.
TEMPERATURE_TOLERANCE_K = 1e-9


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def rated_range_for_grade(grade):
    """Rated range in degrees Celsius implied by a commercial part grade."""
    if grade not in GRADE_RATED_RANGES_C:
        raise ValueError(
            "unknown part grade %r (known: %s)"
            % (grade, ", ".join(sorted(GRADE_RATED_RANGES_C)))
        )
    return GRADE_RATED_RANGES_C[grade]


def thermal_margin_k(knowledge_state):
    """Uncertainty margin earned by the state of the thermal prediction."""
    if knowledge_state not in THERMAL_KNOWLEDGE_MARGIN_K:
        raise ValueError(
            "unknown thermal knowledge state %r (known: %s)"
            % (knowledge_state, ", ".join(sorted(THERMAL_KNOWLEDGE_MARGIN_K)))
        )
    return THERMAL_KNOWLEDGE_MARGIN_K[knowledge_state]


def self_heating_rise_k(dissipation_w, thermal_resistance_k_per_w):
    """Temperature rise from the mounting reference to the rated point."""
    power = _real(dissipation_w, "dissipation_w")
    resistance = _real(thermal_resistance_k_per_w, "thermal_resistance_k_per_w")
    if power < 0.0:
        raise ValueError("dissipation_w must not be negative, got %r" % (dissipation_w,))
    if resistance < 0.0:
        raise ValueError(
            "thermal_resistance_k_per_w must not be negative, got %r"
            % (thermal_resistance_k_per_w,)
        )
    return power * resistance


def normalize_envelope(raw):
    """Validate the equipment operating envelope declaration."""
    if not isinstance(raw, dict):
        raise ValueError("envelope must be a mapping, got %r" % (type(raw).__name__,))
    low = _real(raw.get("min_c"), "envelope min_c")
    high = _real(raw.get("max_c"), "envelope max_c")
    if not low < high:
        raise ValueError(
            "envelope min_c %r must be below max_c %r" % (raw.get("min_c"), raw.get("max_c"))
        )
    knowledge = raw.get("thermal_knowledge", "engineering-estimate")
    thermal_margin_k(knowledge)  # validation only
    return {"min_c": low, "max_c": high, "thermal_knowledge": knowledge}


def required_part_range_c(envelope, rise_k):
    """Corrected range the part rating has to cover, in degrees Celsius."""
    checked = normalize_envelope(envelope)
    rise = _real(rise_k, "rise_k")
    if rise < 0.0:
        raise ValueError("rise_k must not be negative, got %r" % (rise_k,))
    margin = thermal_margin_k(checked["thermal_knowledge"])
    return (checked["min_c"] - margin, checked["max_c"] + rise + margin)


def normalize_part(raw):
    """Validate one part declaration and fill in the values it left out."""
    if not isinstance(raw, dict):
        raise ValueError("part must be a mapping, got %r" % (type(raw).__name__,))
    part_id = raw.get("id")
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part needs a non-empty string id, got %r" % (part_id,))
    grade = raw.get("grade")
    rated_min = raw.get("rated_min_c")
    rated_max = raw.get("rated_max_c")
    if rated_min is None or rated_max is None:
        if grade is None:
            raise ValueError(
                "part %r needs either an explicit rated range or a grade" % (part_id,)
            )
        rated_min, rated_max = rated_range_for_grade(grade)
    else:
        if grade is not None:
            rated_range_for_grade(grade)  # validation only
    rated_min = _real(rated_min, "rated_min_c of %r" % (part_id,))
    rated_max = _real(rated_max, "rated_max_c of %r" % (part_id,))
    if not rated_min < rated_max:
        raise ValueError(
            "rated_min_c of %r must be below rated_max_c" % (part_id,)
        )
    dissipation = _real(raw.get("dissipation_w", 0.0), "dissipation_w of %r" % (part_id,))
    resistance = _real(
        raw.get("thermal_resistance_k_per_w", 0.0),
        "thermal_resistance_k_per_w of %r" % (part_id,),
    )
    if dissipation < 0.0:
        raise ValueError("dissipation_w of %r must not be negative" % (part_id,))
    if resistance < 0.0:
        raise ValueError(
            "thermal_resistance_k_per_w of %r must not be negative" % (part_id,)
        )
    extension = raw.get("extension_evidence", False)
    if not isinstance(extension, bool):
        raise ValueError(
            "extension_evidence of %r must be a boolean, got %r" % (part_id, extension)
        )
    declared = raw.get("declared_verdict")
    if declared is not None and declared not in VERDICTS:
        raise ValueError(
            "declared_verdict of %r is not a known verdict, got %r" % (part_id, declared)
        )
    return {
        "id": part_id,
        "grade": grade,
        "rated_min_c": rated_min,
        "rated_max_c": rated_max,
        "dissipation_w": dissipation,
        "thermal_resistance_k_per_w": resistance,
        "extension_evidence": extension,
        "declared_verdict": declared,
    }


def coverage_verdict(hot_headroom_k, cold_headroom_k):
    """Verdict name for a pair of end headrooms, in kelvin."""
    hot = _real(hot_headroom_k, "hot_headroom_k")
    cold = _real(cold_headroom_k, "cold_headroom_k")
    hot_ok = hot >= -TEMPERATURE_TOLERANCE_K
    cold_ok = cold >= -TEMPERATURE_TOLERANCE_K
    if hot_ok and cold_ok:
        return "temperature-range-covered"
    if hot_ok:
        return "cold-end-shortfall"
    if cold_ok:
        return "hot-end-shortfall"
    return "both-ends-shortfall"


def assess_part(raw, envelope):
    """Grade one part rating against the corrected equipment requirement."""
    part = normalize_part(raw)
    checked = normalize_envelope(envelope)
    rise = self_heating_rise_k(
        part["dissipation_w"], part["thermal_resistance_k_per_w"]
    )
    required_min, required_max = required_part_range_c(checked, rise)
    hot_headroom = part["rated_max_c"] - required_max
    cold_headroom = required_min - part["rated_min_c"]
    verdict = coverage_verdict(hot_headroom, cold_headroom)
    findings = []
    if verdict != "temperature-range-covered":
        if part["extension_evidence"]:
            findings.append("rated-range-extension-claim-open")
        else:
            findings.append("rated-range-extension-evidence-missing")
    elif part["extension_evidence"]:
        findings.append("rated-range-extension-claim-not-needed")
    declared = part["declared_verdict"]
    if declared is not None and declared != verdict:
        if declared == "temperature-range-covered":
            findings.append("declared-coverage-overstated")
        else:
            findings.append("declared-coverage-mismatched")
    record = dict(part)
    record.update(
        {
            "self_heating_rise_k": rise,
            "thermal_margin_k": thermal_margin_k(checked["thermal_knowledge"]),
            "required_min_c": required_min,
            "required_max_c": required_max,
            "hot_headroom_k": hot_headroom,
            "cold_headroom_k": cold_headroom,
            "verdict": verdict,
            "findings": findings,
        }
    )
    return record


def assess_equipment(parts, envelope):
    """Grade a whole part population against one equipment envelope.

    Returns the per-part records, a count per verdict, the flat finding list,
    the part with the least hot-end and the least cold-end headroom, and a
    single boolean saying whether every part covers the requirement with no
    open finding.
    """
    if not isinstance(parts, (list, tuple)):
        raise ValueError("parts must be a list or tuple, got %r" % (type(parts).__name__,))
    if len(parts) == 0:
        raise ValueError("part population must contain at least one part")
    checked = normalize_envelope(envelope)
    records = []
    seen = set()
    for raw in parts:
        record = assess_part(raw, checked)
        if record["id"] in seen:
            raise ValueError("duplicate part id %r" % (record["id"],))
        seen.add(record["id"])
        records.append(record)
    counts = {}
    findings = []
    for record in records:
        counts[record["verdict"]] = counts.get(record["verdict"], 0) + 1
        for finding in record["findings"]:
            findings.append({"id": record["id"], "finding": finding})
    hot_critical = min(records, key=lambda r: (r["hot_headroom_k"], r["id"]))
    cold_critical = min(records, key=lambda r: (r["cold_headroom_k"], r["id"]))
    covered = counts.get("temperature-range-covered", 0)
    return {
        "records": records,
        "verdict_counts": counts,
        "findings": findings,
        "hot_critical_part_id": hot_critical["id"],
        "hot_critical_headroom_k": hot_critical["hot_headroom_k"],
        "cold_critical_part_id": cold_critical["id"],
        "cold_critical_headroom_k": cold_critical["cold_headroom_k"],
        "covered_part_count": covered,
        "population_size": len(records),
        "consistent": len(findings) == 0 and covered == len(records),
    }
