#!/usr/bin/env python3
"""Self-sustained-discharge prevention logic, ECSS-E-ST-20-06C clause 8.2.

Deterministic, offline, stdlib-only implementation of the clause 8.2
demonstration: once an electrostatic-discharge has been triggered somewhere on
the vehicle, no on-board equipment may keep feeding the resulting secondary
arc from its own stored or generated energy for the rest of the mission.

The procedure implemented here is a paraphrase of the engineering intent, not
of the standard text. The clause is cited as an anchor only.
"""

import math

__all__ = [
    "THRESHOLD_REL_TOL",
    "BARRIER_FACTORS",
    "EVIDENCE_METHODS",
    "REGIME_QUENCHED",
    "REGIME_TEMPORARY",
    "REGIME_PERMANENT",
    "categorize_conductor_pair",
    "sustaining_voltage_threshold",
    "sustaining_current_threshold",
    "apply_mitigations",
    "evaluate_arc_regime",
    "transient_arc_energy_j",
    "verify_demonstration_evidence",
    "assess_equipment",
    "summarize_assessment",
]

#: Relative tolerance that absorbs floating-point representation error at an
#: exactly-compliant threshold. It does NOT widen the engineering limit: a
#: value that is mathematically equal to the limit but lands a few ULPs above
#: it after a divide-and-sum round trip still reads as compliant.
THRESHOLD_REL_TOL = 1e-9

# Sustaining-threshold model for a secondary arc bridging two conductors that
# face each other across a dielectric gap. Both thresholds grow with the gap:
# a wider gap needs a higher potential difference to keep the plasma column
# ionized, and a higher current to keep the electrode spots hot.
SUSTAIN_V_INTERCEPT = 22.0       # volts at a vanishing gap
SUSTAIN_V_PER_MM = 58.0          # volts added per millimetre of gap
SUSTAIN_I_INTERCEPT = 0.25       # amperes at a vanishing gap
SUSTAIN_I_PER_MM = 0.35          # amperes added per millimetre of gap

# Barrier material between the two conductors. A bare gap sustains an arc most
# easily; encapsulants and standoffs raise both sustaining thresholds.
BARRIER_FACTORS = {
    "bare-gap": 1.0,
    "conformal-coat": 1.35,
    "polyimide-tape": 1.70,
    "silicone-encapsulant": 2.40,
    "ceramic-standoff": 3.10,
}
UNPROTECTED_BARRIER = "bare-gap"

# Energy a self-extinguishing transient may deposit in the gap before it is
# treated as damaging rather than benign.
TRANSIENT_ENERGY_LIMIT_J = 0.050

REGIME_QUENCHED = "quenched"
REGIME_TEMPORARY = "temporary-sustained-arc"
REGIME_PERMANENT = "permanent-sustained-arc"

_REGIME_RANK = {
    REGIME_QUENCHED: 0,
    REGIME_TEMPORARY: 1,
    REGIME_PERMANENT: 2,
}

EVIDENCE_METHODS = {
    "secondary-arc-test",
    "arc-propagation-analysis",
    "similarity-to-qualified-design",
}

# An escalating pair may not be closed out by paper alone.
_EMPIRICAL_METHODS = {"secondary-arc-test", "similarity-to-qualified-design"}

MITIGATION_TYPES = {
    "current-limiting",
    "string-segmentation",
    "series-blocking-diode",
}


def _require_number(value, label):
    """Return value as float, rejecting non-numeric and non-finite input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(value, label):
    out = _require_number(value, label)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def _require_non_negative(value, label):
    out = _require_number(value, label)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return out


def _not_above(value, limit):
    """True when value is at or below limit, tolerating representation error."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=THRESHOLD_REL_TOL, abs_tol=0.0)


def categorize_conductor_pair(pair):
    """Validate one adjacent-conductor pair and categorize its barrier.

    A pair carries: pair_id, gap_mm, potential_v (the steady difference the
    two conductors hold across the gap), available_current_a (what the source
    behind them can deliver into a short) and barrier (a key of
    BARRIER_FACTORS).

    Returns a normalized record with a "category" of either
    "unprotected-pair" or "barrier-protected-pair".
    """
    if not isinstance(pair, dict):
        raise ValueError("conductor pair must be a mapping, got %r" % (pair,))
    pair_id = pair.get("pair_id")
    if not isinstance(pair_id, str) or not pair_id.strip():
        raise ValueError("conductor pair needs a non-empty pair_id")
    barrier = pair.get("barrier")
    if barrier not in BARRIER_FACTORS:
        raise ValueError(
            "pair %s has uncategorized barrier %r; known: %s"
            % (pair_id, barrier, ", ".join(sorted(BARRIER_FACTORS)))
        )
    gap_mm = _require_positive(pair.get("gap_mm"), "gap_mm of pair %s" % pair_id)
    potential_v = _require_non_negative(
        pair.get("potential_v"), "potential_v of pair %s" % pair_id
    )
    current_a = _require_non_negative(
        pair.get("available_current_a"), "available_current_a of pair %s" % pair_id
    )
    category = (
        "unprotected-pair" if barrier == UNPROTECTED_BARRIER else "barrier-protected-pair"
    )
    return {
        "pair_id": pair_id,
        "gap_mm": gap_mm,
        "potential_v": potential_v,
        "available_current_a": current_a,
        "barrier": barrier,
        "category": category,
    }


def sustaining_voltage_threshold(gap_mm, barrier):
    """Potential difference below which a secondary arc cannot stay ionized."""
    if barrier not in BARRIER_FACTORS:
        raise ValueError("uncategorized barrier %r" % (barrier,))
    gap = _require_positive(gap_mm, "gap_mm")
    return (SUSTAIN_V_INTERCEPT + SUSTAIN_V_PER_MM * gap) * BARRIER_FACTORS[barrier]


def sustaining_current_threshold(gap_mm, barrier):
    """Current below which arc electrode spots cool and the column collapses."""
    if barrier not in BARRIER_FACTORS:
        raise ValueError("uncategorized barrier %r" % (barrier,))
    gap = _require_positive(gap_mm, "gap_mm")
    return (SUSTAIN_I_INTERCEPT + SUSTAIN_I_PER_MM * gap) * BARRIER_FACTORS[barrier]


def apply_mitigations(pair, mitigations=None):
    """Reduce the driving potential and current by the credited mitigations.

    Only a mitigation that is physically present on the equipment may be
    credited. Each entry is a mapping with a "type" from MITIGATION_TYPES and
    its own parameter. Returns (effective_v, effective_a, credited_types).
    """
    record = categorize_conductor_pair(pair)
    effective_v = record["potential_v"]
    effective_a = record["available_current_a"]
    credited = []
    if mitigations is None:
        return effective_v, effective_a, credited
    if not isinstance(mitigations, (list, tuple)):
        raise ValueError("mitigations must be a list, got %r" % (mitigations,))
    for item in mitigations:
        if not isinstance(item, dict):
            raise ValueError("mitigation must be a mapping, got %r" % (item,))
        kind = item.get("type")
        if kind not in MITIGATION_TYPES:
            raise ValueError(
                "uncategorized mitigation %r; known: %s"
                % (kind, ", ".join(sorted(MITIGATION_TYPES)))
            )
        if kind == "current-limiting":
            limit = _require_positive(item.get("limit_a"), "limit_a")
            effective_a = min(effective_a, limit)
        elif kind == "string-segmentation":
            segments = item.get("segments")
            if not isinstance(segments, int) or isinstance(segments, bool):
                raise ValueError("segments must be an integer, got %r" % (segments,))
            if segments < 2:
                raise ValueError("segments must be >= 2 to reduce the gap potential")
            effective_v = effective_v / float(segments)
        elif kind == "series-blocking-diode":
            share = _require_number(item.get("bypass_fraction"), "bypass_fraction")
            if not 0.0 <= share < 1.0:
                raise ValueError(
                    "bypass_fraction must be in [0, 1), got %r" % (item.get("bypass_fraction"),)
                )
            effective_a = effective_a * (1.0 - share)
        credited.append(kind)
    return effective_v, effective_a, credited


def evaluate_arc_regime(pair, mitigations=None):
    """Decide whether a triggered pair quenches, flickers, or latches on.

    A sustained column needs the gap potential to stay above the sustaining
    voltage; without it the arc cannot re-ionize whatever the current is. With
    the voltage present, the current decides whether the arc self-extinguishes
    (temporary) or latches for the rest of the mission (permanent).
    """
    record = categorize_conductor_pair(pair)
    effective_v, effective_a, credited = apply_mitigations(pair, mitigations)
    v_threshold = sustaining_voltage_threshold(record["gap_mm"], record["barrier"])
    i_threshold = sustaining_current_threshold(record["gap_mm"], record["barrier"])
    if _not_above(effective_v, v_threshold):
        regime = REGIME_QUENCHED
    elif _not_above(effective_a, i_threshold):
        regime = REGIME_TEMPORARY
    else:
        regime = REGIME_PERMANENT
    return {
        "pair_id": record["pair_id"],
        "category": record["category"],
        "barrier": record["barrier"],
        "effective_v": effective_v,
        "effective_a": effective_a,
        "voltage_threshold_v": v_threshold,
        "current_threshold_a": i_threshold,
        "voltage_margin_v": v_threshold - effective_v,
        "current_margin_a": i_threshold - effective_a,
        "credited_mitigations": credited,
        "regime": regime,
    }


def transient_arc_energy_j(effective_v, effective_a, duration_s):
    """Energy a self-extinguishing transient deposits in the gap."""
    volts = _require_non_negative(effective_v, "effective_v")
    amps = _require_non_negative(effective_a, "effective_a")
    seconds = _require_non_negative(duration_s, "duration_s")
    return volts * amps * seconds


def verify_demonstration_evidence(evidence, regime):
    """Check that the closure evidence matches what the regime demands."""
    if regime not in _REGIME_RANK:
        raise ValueError("uncategorized regime %r" % (regime,))
    findings = []
    if evidence is None:
        findings.append("no demonstration evidence on record for clause 8.2")
        return findings
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping or None, got %r" % (evidence,))
    method = evidence.get("method")
    if method not in EVIDENCE_METHODS:
        raise ValueError(
            "uncategorized evidence method %r; known: %s"
            % (method, ", ".join(sorted(EVIDENCE_METHODS)))
        )
    reference = evidence.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        findings.append("evidence method %s carries no report reference" % method)
    if regime == REGIME_TEMPORARY and method not in _EMPIRICAL_METHODS:
        findings.append(
            "a temporary-sustained-arc pair needs empirical evidence, not %s" % method
        )
    return findings


def assess_equipment(item):
    """Run the full clause 8.2 demonstration for one equipment item."""
    if not isinstance(item, dict):
        raise ValueError("equipment item must be a mapping, got %r" % (item,))
    equipment_id = item.get("equipment_id")
    if not isinstance(equipment_id, str) or not equipment_id.strip():
        raise ValueError("equipment item needs a non-empty equipment_id")
    pairs = item.get("pairs")
    if not isinstance(pairs, (list, tuple)) or not pairs:
        raise ValueError(
            "equipment %s must declare at least one adjacent-conductor pair" % equipment_id
        )
    duration_s = _require_non_negative(
        item.get("transient_duration_s", 0.0), "transient_duration_s"
    )
    mitigations = item.get("mitigations")
    results = []
    findings = []
    worst = REGIME_QUENCHED
    for pair in pairs:
        outcome = evaluate_arc_regime(pair, mitigations)
        energy = transient_arc_energy_j(
            outcome["effective_v"], outcome["effective_a"], duration_s
        )
        outcome["transient_energy_j"] = energy
        if outcome["regime"] == REGIME_PERMANENT:
            findings.append(
                "pair %s latches a permanent-sustained-arc; clause 8.2 is not met"
                % outcome["pair_id"]
            )
        elif outcome["regime"] == REGIME_TEMPORARY and not _not_above(
            energy, TRANSIENT_ENERGY_LIMIT_J
        ):
            findings.append(
                "pair %s deposits %.4f J per transient, above the %.3f J limit"
                % (outcome["pair_id"], energy, TRANSIENT_ENERGY_LIMIT_J)
            )
        if _REGIME_RANK[outcome["regime"]] > _REGIME_RANK[worst]:
            worst = outcome["regime"]
        results.append(outcome)
    findings.extend(verify_demonstration_evidence(item.get("evidence"), worst))
    return {
        "equipment_id": equipment_id,
        "pair_results": results,
        "worst_regime": worst,
        "findings": findings,
        "compliant": not findings,
    }


def summarize_assessment(items):
    """Aggregate per-equipment verdicts into one clause 8.2 roll-up."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("summarize_assessment needs a non-empty list of equipment")
    assessments = [assess_equipment(item) for item in items]
    non_compliant = [a["equipment_id"] for a in assessments if not a["compliant"]]
    latching = [
        a["equipment_id"] for a in assessments if a["worst_regime"] == REGIME_PERMANENT
    ]
    return {
        "assessed": len(assessments),
        "assessments": assessments,
        "non_compliant": non_compliant,
        "latching_equipment": latching,
        "clause_8_2_met": not non_compliant,
    }
