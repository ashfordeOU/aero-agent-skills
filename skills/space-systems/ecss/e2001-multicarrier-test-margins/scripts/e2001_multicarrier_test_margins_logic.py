#!/usr/bin/env python3
"""Multicarrier multipactor test margins and the level a campaign must reach.

Anchor: ECSS-E-ST-20-01C clause 4.7.3.1 (test margins for multicarrier
operation, set from the equipment or component type under test and from the
design heritage of that item). Paraphrased into an implementable procedure;
no verbatim standard text is reproduced.

Stdlib only, offline, deterministic.

Procedure implemented here:

1. categorize the article under test against the recognized equipment-type
   and component-type list, which fixes the base test margin and the test
   level (equipment or component) the campaign sits at;
2. add the design-heritage increment and the model-philosophy adder for the
   article actually on the bench, then subtract the sample-count relief
   earned by testing more than one article, never dropping below the floor;
3. build the multicarrier peak-envelope power from the carrier set by
   in-phase voltage addition;
4. raise that envelope by the resolved test margin to obtain the level the
   campaign has to reach;
5. compare the required level against the facility capability and report the
   headroom;
6. aggregate the per-article verdicts into a campaign verdict.

The margin tables below are a documented, project-replaceable engineering
default expressing the clause's ordering (a high-power chain owes more than a
receive chain, a new design owes more than a recurring one, a dedicated
qualification article earns no penalty). They are not a reproduction of any
table in the standard.
"""

import math

# A level landing exactly on its requirement is the design point: the
# comparison absorbs floating-point representation error instead of moving the
# engineering limit.
LEVEL_REL_TOL = 1e-9
LEVEL_ABS_TOL = 1e-9

# Clause 4.7.3.1 is the multicarrier branch; a single carrier belongs to the
# single-carrier clause and is refused here rather than silently assessed.
MIN_MULTICARRIER_CARRIERS = 2

TEST_LEVEL_EQUIPMENT = "equipment"
TEST_LEVEL_COMPONENT = "component"

# Base multicarrier test margin, in decibel, by article type.
ITEM_TYPES = {
    "high-power-transmit-chain": {
        "test_level": TEST_LEVEL_EQUIPMENT,
        "base_test_margin_db": 6.0,
    },
    "output-multiplexer": {
        "test_level": TEST_LEVEL_EQUIPMENT,
        "base_test_margin_db": 6.0,
    },
    "low-power-receive-chain": {
        "test_level": TEST_LEVEL_EQUIPMENT,
        "base_test_margin_db": 3.0,
    },
    "waveguide-filter-component": {
        "test_level": TEST_LEVEL_COMPONENT,
        "base_test_margin_db": 4.0,
    },
    "coaxial-connector-component": {
        "test_level": TEST_LEVEL_COMPONENT,
        "base_test_margin_db": 4.0,
    },
    "antenna-radiating-element": {
        "test_level": TEST_LEVEL_COMPONENT,
        "base_test_margin_db": 4.0,
    },
    "dielectric-loaded-component": {
        "test_level": TEST_LEVEL_COMPONENT,
        "base_test_margin_db": 5.0,
    },
}

# Increment owed by design heritage, in decibel.
HERITAGE_LEVELS = {
    "flight-proven-recurring": 0.0,
    "modified-design": 1.0,
    "new-design": 2.0,
}

# Adder owed by the build standard of the article actually on the bench.
# An article that cannot close the verification at all is marked closing:False
# and produces a finding rather than a silent pass.
MODEL_PHILOSOPHIES = {
    "dedicated-qualification-model": {"adder_db": 0.0, "closing": True},
    "protoflight-model": {"adder_db": 0.5, "closing": True},
    "engineering-model": {"adder_db": 1.5, "closing": True},
    "breadboard": {"adder_db": 2.5, "closing": False},
}

# Relief earned per additional tested article, and its cap, in decibel.
SAMPLE_RELIEF_PER_EXTRA_DB = 0.5
MAX_SAMPLE_RELIEF_DB = 1.0

# No combination of relief may drive the test margin below this floor.
MIN_TEST_MARGIN_DB = 2.5


def _as_float(value, label):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _at_least(value, limit):
    """True when value reaches limit, absorbing representation error."""
    if value >= limit:
        return True
    return math.isclose(value, limit, rel_tol=LEVEL_REL_TOL, abs_tol=LEVEL_ABS_TOL)


def _lookup(table, key, label):
    """Resolve a normalized key in a table or raise ValueError."""
    if not isinstance(key, str):
        raise ValueError("%s must be a string, got %r" % (label, key))
    normalized = key.strip().lower()
    if normalized not in table:
        raise ValueError(
            "unrecognized %s %r; known: %s" % (label, key, ", ".join(sorted(table)))
        )
    return normalized


def peak_envelope_power_w(carrier_powers_w):
    """Worst-case multicarrier peak envelope power, in watt.

    The carriers are assumed to align in phase at some instant, so their
    voltages add and the power goes as the square of the summed root-powers.
    """
    if isinstance(carrier_powers_w, (str, bytes)) or not isinstance(
        carrier_powers_w, (list, tuple)
    ):
        raise ValueError("carrier_powers_w must be a list or tuple of powers")
    if len(carrier_powers_w) < MIN_MULTICARRIER_CARRIERS:
        raise ValueError(
            "multicarrier test needs at least %d carriers, got %d"
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


def from_dbw(level_dbw):
    """Convert a level in decibel-watt back to watt."""
    return 10.0 ** (_as_float(level_dbw, "level_dbw") / 10.0)


def sample_count_relief_db(sample_count):
    """Relief earned by testing more than one article, in decibel."""
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise ValueError("sample_count must be an integer, got %r" % (sample_count,))
    if sample_count < 1:
        raise ValueError("sample_count must be at least 1, got %d" % sample_count)
    relief = SAMPLE_RELIEF_PER_EXTRA_DB * (sample_count - 1)
    if relief > MAX_SAMPLE_RELIEF_DB:
        relief = MAX_SAMPLE_RELIEF_DB
    return relief


def resolve_test_margin(item_type, heritage, model_philosophy, sample_count=1):
    """Resolve the multicarrier test margin owed by one tested article."""
    item_key = _lookup(ITEM_TYPES, item_type, "item_type")
    heritage_key = _lookup(HERITAGE_LEVELS, heritage, "heritage")
    model_key = _lookup(MODEL_PHILOSOPHIES, model_philosophy, "model_philosophy")
    spec = ITEM_TYPES[item_key]
    model = MODEL_PHILOSOPHIES[model_key]
    relief = sample_count_relief_db(sample_count)
    raw = (
        spec["base_test_margin_db"]
        + HERITAGE_LEVELS[heritage_key]
        + model["adder_db"]
        - relief
    )
    notes = []
    applied = raw
    if not _at_least(raw, MIN_TEST_MARGIN_DB):
        applied = MIN_TEST_MARGIN_DB
        notes.append(
            "relief capped: computed %.3f dB is below the %.3f dB test-margin floor"
            % (raw, MIN_TEST_MARGIN_DB)
        )
    findings = []
    if not model["closing"]:
        findings.append(
            "model philosophy %r cannot close the multicarrier test-margin "
            "requirement; the build standard is not representative of flight"
            % model_key
        )
    return {
        "item_type": item_key,
        "test_level": spec["test_level"],
        "heritage": heritage_key,
        "model_philosophy": model_key,
        "base_test_margin_db": spec["base_test_margin_db"],
        "heritage_increment_db": HERITAGE_LEVELS[heritage_key],
        "model_adder_db": model["adder_db"],
        "sample_relief_db": relief,
        "computed_margin_db": raw,
        "test_margin_db": applied,
        "notes": notes,
        "findings": findings,
    }


def required_test_level_dbw(peak_envelope_dbw, test_margin_db):
    """Level the campaign has to reach: envelope peak raised by the margin."""
    envelope = _as_float(peak_envelope_dbw, "peak_envelope_dbw")
    margin = _as_float(test_margin_db, "test_margin_db")
    if margin < 0.0:
        raise ValueError("test_margin_db must not be negative, got %r" % (test_margin_db,))
    return envelope + margin


def check_facility_headroom(required_dbw, facility_max_dbw):
    """Compare the required level against what the facility can deliver."""
    required = _as_float(required_dbw, "required_dbw")
    capability = _as_float(facility_max_dbw, "facility_max_dbw")
    sufficient = _at_least(capability, required)
    headroom = capability - required
    if sufficient and headroom < 0.0:
        headroom = 0.0
    return {
        "required_dbw": required,
        "facility_max_dbw": capability,
        "headroom_db": headroom,
        "sufficient": sufficient,
    }


def assess_test_case(case):
    """Assess one tested article against its multicarrier test margin."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    article_id = case.get("article_id")
    if not isinstance(article_id, str) or not article_id.strip():
        raise ValueError(
            "case 'article_id' must be a non-empty string, got %r" % (article_id,)
        )
    resolved = resolve_test_margin(
        case.get("item_type"),
        case.get("heritage"),
        case.get("model_philosophy"),
        case.get("sample_count", 1),
    )
    carriers = case.get("carrier_powers_w")
    peak_w = peak_envelope_power_w(carriers)
    peak_dbw = to_dbw(peak_w)
    required = required_test_level_dbw(peak_dbw, resolved["test_margin_db"])
    facility = check_facility_headroom(required, case.get("facility_max_dbw"))
    findings = list(resolved["findings"])
    if not facility["sufficient"]:
        findings.append(
            "facility ceiling %.3f dBW cannot reach the required %.3f dBW "
            "(short by %.3f dB)"
            % (facility["facility_max_dbw"], required, required - facility["facility_max_dbw"])
        )
    result = dict(resolved)
    result.update(
        {
            "article_id": article_id.strip(),
            "carrier_count": len(carriers),
            "peak_envelope_power_w": peak_w,
            "peak_envelope_power_dbw": peak_dbw,
            "required_test_level_dbw": required,
            "required_test_level_w": from_dbw(required),
            "facility_headroom_db": facility["headroom_db"],
            "facility_sufficient": facility["sufficient"],
            "findings": findings,
            "testable": not findings,
        }
    )
    return result


def assess_campaign(cases):
    """Aggregate the per-article verdicts into a campaign verdict."""
    if isinstance(cases, (str, bytes)) or not isinstance(cases, (list, tuple)):
        raise ValueError("cases must be a list or tuple")
    if not cases:
        raise ValueError("cases must not be empty")
    seen = set()
    assessed = []
    for case in cases:
        result = assess_test_case(case)
        if result["article_id"] in seen:
            raise ValueError("duplicate article_id %r" % result["article_id"])
        seen.add(result["article_id"])
        assessed.append(result)
    blocked = [r["article_id"] for r in assessed if not r["testable"]]
    highest = max(r["required_test_level_dbw"] for r in assessed)
    findings = []
    for r in assessed:
        for f in r["findings"]:
            findings.append("%s: %s" % (r["article_id"], f))
    return {
        "article_count": len(assessed),
        "articles": assessed,
        "blocked_articles": blocked,
        "highest_required_level_dbw": highest,
        "findings": findings,
        "testable": not blocked,
    }
