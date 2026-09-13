#!/usr/bin/env python3
"""Nominal analysis margins for multicarrier multipactor assessment.

Anchor: ECSS-E-ST-20-01C clause 4.7.2.2 (nominal analysis margins for
multicarrier operation, resolved per margin contribution, per equipment type
and per design heritage). Paraphrased into an implementable procedure; no
verbatim standard text is reproduced.

Stdlib only, offline, deterministic.

Procedure implemented here:

1. build the multicarrier peak-envelope power from the individual carrier
   powers (worst-case in-phase addition of the carrier voltages) and reject a
   carrier set that is not a multicarrier set at all;
2. categorize the unit against the recognized equipment-type list and resolve
   its design-heritage level, giving the nominal analysis margin that the pair
   owes;
3. normalize and accumulate the declared margin contributions, rejecting an
   unrecognized contribution category and flagging a mandatory contribution
   that was never declared or one declared below its credibility floor;
4. compare the accumulated applied margin against the required nominal margin
   and report the shortfall;
5. derive the power level at which the analysis has to demonstrate freedom
   from multipactor (peak envelope raised by the required margin);
6. aggregate the per-case verdicts into a unit-level verdict.

The margin tables below are a documented, project-replaceable engineering
default expressing the clause's ordering (a higher-power chain owes more than
a low-power receive chain, a new design owes more than a recurring one). They
are not a reproduction of any table in the standard.
"""

import math

# A margin landing exactly on its requirement is the design point: the
# comparison absorbs floating-point representation error instead of moving the
# engineering limit.
MARGIN_REL_TOL = 1e-9
MARGIN_ABS_TOL = 1e-9

# Clause 4.7.2.2 is the multicarrier branch; a single carrier belongs to the
# single-carrier clause and is refused here rather than silently assessed.
MIN_MULTICARRIER_CARRIERS = 2

# Nominal analysis margin owed by equipment type, in decibel, before the
# design-heritage increment.
EQUIPMENT_TYPES = {
    "high-power-transmit-chain": 8.0,
    "output-multiplexer": 8.0,
    "waveguide-passive-component": 6.0,
    "coaxial-passive-component": 6.0,
    "antenna-radiating-element": 6.0,
    "low-power-receive-chain": 4.0,
}

# Increment owed by design heritage, in decibel.
HERITAGE_LEVELS = {
    "flight-proven-recurring": 0.0,
    "modified-design": 1.0,
    "new-design": 2.0,
}

# Recognized margin contributions. A mandatory contribution has to appear in
# every multicarrier analysis; the floor is the smallest value that is still a
# credible declaration for that contribution.
CONTRIBUTIONS = {
    "geometry-tolerance": {"floor_db": 0.5, "mandatory": True},
    "secondary-emission-yield-uncertainty": {"floor_db": 1.0, "mandatory": True},
    "field-solver-uncertainty": {"floor_db": 0.5, "mandatory": True},
    "carrier-phasing-uncertainty": {"floor_db": 0.5, "mandatory": True},
    "thermal-drift": {"floor_db": 0.0, "mandatory": False},
    "power-measurement-uncertainty": {"floor_db": 0.0, "mandatory": False},
    "surface-treatment-variability": {"floor_db": 0.0, "mandatory": False},
}

# A single contribution larger than this is a modelling error, not a margin.
MAX_SINGLE_CONTRIBUTION_DB = 10.0


def _as_float(value, label):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _covers(applied, required):
    """True when applied covers required, absorbing representation error."""
    if applied >= required:
        return True
    return math.isclose(
        applied, required, rel_tol=MARGIN_REL_TOL, abs_tol=MARGIN_ABS_TOL
    )


def peak_envelope_power_w(carrier_powers_w):
    """Worst-case multicarrier peak envelope power, in watt.

    The carriers are assumed to align in phase at some instant, so their
    voltages add; power goes as voltage squared, hence the square of the sum
    of the square roots.
    """
    if isinstance(carrier_powers_w, (str, bytes)) or not isinstance(
        carrier_powers_w, (list, tuple)
    ):
        raise ValueError("carrier_powers_w must be a list or tuple of powers")
    if len(carrier_powers_w) < MIN_MULTICARRIER_CARRIERS:
        raise ValueError(
            "multicarrier assessment needs at least %d carriers, got %d"
            % (MIN_MULTICARRIER_CARRIERS, len(carrier_powers_w))
        )
    total_root = 0.0
    for i, item in enumerate(carrier_powers_w):
        power = _as_float(item, "carrier_powers_w[%d]" % i)
        if power <= 0.0:
            raise ValueError(
                "carrier_powers_w[%d] must be strictly positive, got %r" % (i, item)
            )
        total_root += math.sqrt(power)
    return total_root * total_root


def to_dbw(power_w):
    """Convert a power in watt to decibel-watt."""
    power = _as_float(power_w, "power_w")
    if power <= 0.0:
        raise ValueError("power_w must be strictly positive, got %r" % (power_w,))
    return 10.0 * math.log10(power)


def peak_to_average_ratio_db(carrier_powers_w):
    """Envelope peak over the summed average power of the carrier set, in dB."""
    peak = peak_envelope_power_w(carrier_powers_w)
    average = 0.0
    for i, item in enumerate(carrier_powers_w):
        average += _as_float(item, "carrier_powers_w[%d]" % i)
    return 10.0 * math.log10(peak / average)


def resolve_nominal_margin(equipment_type, heritage):
    """Resolve the nominal analysis margin owed by an equipment/heritage pair."""
    if not isinstance(equipment_type, str):
        raise ValueError("equipment_type must be a string, got %r" % (equipment_type,))
    key = equipment_type.strip().lower()
    if key not in EQUIPMENT_TYPES:
        raise ValueError(
            "unrecognized equipment_type %r; known: %s"
            % (equipment_type, ", ".join(sorted(EQUIPMENT_TYPES)))
        )
    if not isinstance(heritage, str):
        raise ValueError("heritage must be a string, got %r" % (heritage,))
    hkey = heritage.strip().lower()
    if hkey not in HERITAGE_LEVELS:
        raise ValueError(
            "unrecognized heritage %r; known: %s"
            % (heritage, ", ".join(sorted(HERITAGE_LEVELS)))
        )
    base = EQUIPMENT_TYPES[key]
    increment = HERITAGE_LEVELS[hkey]
    return {
        "equipment_type": key,
        "heritage": hkey,
        "base_db": base,
        "heritage_increment_db": increment,
        "required_margin_db": base + increment,
    }


def normalize_contribution(entry):
    """Validate one declared margin contribution and return it normalized."""
    if not isinstance(entry, dict):
        raise ValueError("contribution entry must be a mapping, got %r" % (entry,))
    category = entry.get("category")
    if not isinstance(category, str):
        raise ValueError("contribution 'category' must be a string, got %r" % (category,))
    key = category.strip().lower()
    if key not in CONTRIBUTIONS:
        raise ValueError(
            "unrecognized contribution category %r; known: %s"
            % (category, ", ".join(sorted(CONTRIBUTIONS)))
        )
    if "value_db" not in entry:
        raise ValueError("contribution %r has no 'value_db'" % (category,))
    value = _as_float(entry["value_db"], "contribution %r value_db" % key)
    if value < 0.0:
        raise ValueError(
            "contribution %r value_db must not be negative, got %r" % (key, value)
        )
    if value > MAX_SINGLE_CONTRIBUTION_DB:
        raise ValueError(
            "contribution %r value_db %.3f exceeds the %.1f dB single-contribution "
            "ceiling; that is a modelling error, not a margin"
            % (key, value, MAX_SINGLE_CONTRIBUTION_DB)
        )
    return {"category": key, "value_db": value}


def accumulate_contributions(entries):
    """Sum the declared contributions and report credibility findings."""
    if isinstance(entries, (str, bytes)) or not isinstance(entries, (list, tuple)):
        raise ValueError("contributions must be a list or tuple")
    if not entries:
        raise ValueError("contributions must not be empty")
    breakdown = {}
    findings = []
    total = 0.0
    for entry in entries:
        item = normalize_contribution(entry)
        key = item["category"]
        if key in breakdown:
            raise ValueError("contribution category %r declared twice" % key)
        breakdown[key] = item["value_db"]
        total += item["value_db"]
    for key in sorted(CONTRIBUTIONS):
        spec = CONTRIBUTIONS[key]
        if key not in breakdown:
            if spec["mandatory"]:
                findings.append(
                    "mandatory contribution %r not declared for the multicarrier "
                    "analysis" % key
                )
            continue
        floor = spec["floor_db"]
        if floor > 0.0 and breakdown[key] < floor and not math.isclose(
            breakdown[key], floor, rel_tol=MARGIN_REL_TOL, abs_tol=MARGIN_ABS_TOL
        ):
            findings.append(
                "contribution %r declared at %.3f dB is below its %.3f dB "
                "credibility floor" % (key, breakdown[key], floor)
            )
    return {"total_db": total, "breakdown": breakdown, "findings": findings}


def assess_analysis_case(case):
    """Assess one multicarrier analysis case against its nominal margin."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case 'case_id' must be a non-empty string, got %r" % (case_id,))
    resolved = resolve_nominal_margin(case.get("equipment_type"), case.get("heritage"))
    carriers = case.get("carrier_powers_w")
    peak_w = peak_envelope_power_w(carriers)
    accumulated = accumulate_contributions(case.get("contributions"))
    required = resolved["required_margin_db"]
    applied = accumulated["total_db"]
    covers = _covers(applied, required)
    deficit = 0.0 if covers else required - applied
    findings = list(accumulated["findings"])
    if not covers:
        findings.append(
            "applied analysis margin %.3f dB does not cover the required "
            "%.3f dB (shortfall %.3f dB)" % (applied, required, deficit)
        )
    peak_dbw = to_dbw(peak_w)
    return {
        "case_id": case_id.strip(),
        "equipment_type": resolved["equipment_type"],
        "heritage": resolved["heritage"],
        "carrier_count": len(carriers),
        "peak_envelope_power_w": peak_w,
        "peak_envelope_power_dbw": peak_dbw,
        "peak_to_average_ratio_db": peak_to_average_ratio_db(carriers),
        "required_margin_db": required,
        "applied_margin_db": applied,
        "margin_breakdown_db": accumulated["breakdown"],
        "deficit_db": deficit,
        "analysis_power_level_dbw": peak_dbw + required,
        "findings": findings,
        "compliant": covers and not findings,
    }


def assess_unit(cases):
    """Aggregate the per-case verdicts into a unit-level verdict."""
    if isinstance(cases, (str, bytes)) or not isinstance(cases, (list, tuple)):
        raise ValueError("cases must be a list or tuple")
    if not cases:
        raise ValueError("cases must not be empty")
    seen = set()
    assessed = []
    for case in cases:
        result = assess_analysis_case(case)
        if result["case_id"] in seen:
            raise ValueError("duplicate case_id %r" % result["case_id"])
        seen.add(result["case_id"])
        assessed.append(result)
    failing = [r["case_id"] for r in assessed if not r["compliant"]]
    worst = 0.0
    for r in assessed:
        if r["deficit_db"] > worst:
            worst = r["deficit_db"]
    findings = []
    for r in assessed:
        for f in r["findings"]:
            findings.append("%s: %s" % (r["case_id"], f))
    return {
        "case_count": len(assessed),
        "cases": assessed,
        "non_compliant_cases": failing,
        "worst_deficit_db": worst,
        "findings": findings,
        "compliant": not failing,
    }
