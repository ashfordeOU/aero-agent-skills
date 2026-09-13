#!/usr/bin/env python3
"""Multicarrier multipactor margin values (ECSS-E-ST-20-01C clause 4.7.1).

Deterministic, offline, stdlib-only implementation of the margin policy that
governs a multicarrier radio-frequency chain: which decibel value the
verification route owes, which reference power that value is applied to, and
what demonstration power the two routes -- analysis and test -- each demand for
the same carrier plan.

The numeric tables below are this leaf's default policy for the clause; a
project working to a different issue of the standard supplies its own table
through the ``policy`` argument instead of editing the procedure. The clause is
the anchor for the procedure, not a reproduction of the standard's text.
"""

import math

# Representation-error absorption only; never a relaxation of the margin.
MARGIN_TOLERANCE_DB = 1e-9

MIN_CARRIERS = 2

ROUTE_ALIASES = {
    "analysis": "analysis",
    "analytical": "analysis",
    "simulation": "analysis",
    "by-analysis": "analysis",
    "test": "test",
    "by-test": "test",
    "measurement": "test",
    "measured": "test",
}

BASIS_ALIASES = {
    "measured": "measured",
    "measurement": "measured",
    "tested": "measured",
    "simulated": "simulated",
    "computed": "simulated",
    "analysed": "simulated",
    "analyzed": "simulated",
}

HERITAGE_ALIASES = {
    "recurrent": "recurrent",
    "recurring": "recurrent",
    "qualified-design": "recurrent",
    "modified": "modified",
    "modified-design": "modified",
    "derivative": "modified",
    "first-of-kind": "first-of-kind",
    "new-design": "first-of-kind",
    "no-heritage": "first-of-kind",
}

# Base decibel value each verification route owes for a multicarrier chain.
ROUTE_BASE_MARGIN_DB = {"analysis": 6.0, "test": 3.0}

# Uplift carried by the maturity of the design being assessed.
HERITAGE_UPLIFT_DB = {"recurrent": 0.0, "modified": 1.0, "first-of-kind": 2.0}

# Uplift carried when the anchoring single-carrier threshold was computed
# rather than measured on representative hardware.
SIMULATED_THRESHOLD_UPLIFT_DB = 1.0


def _check_positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return value


def _normalize(value, aliases, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    if key not in aliases:
        raise ValueError(
            "unrecognized %s %r (known: %s)"
            % (label, value, ", ".join(sorted(set(aliases.values()))))
        )
    return aliases[key]


def normalize_route(value):
    """Map a free-form verification route onto 'analysis' or 'test'."""
    return _normalize(value, ROUTE_ALIASES, "verification route")


def normalize_threshold_basis(value):
    """Map the basis of the anchoring threshold onto 'measured' or 'simulated'."""
    return _normalize(value, BASIS_ALIASES, "threshold basis")


def normalize_heritage(value):
    """Map a free-form heritage statement onto a canonical heritage category."""
    return _normalize(value, HERITAGE_ALIASES, "heritage")


def validate_carrier_powers(carrier_powers):
    """Return the carrier plan as a tuple of positive watt values."""
    if not isinstance(carrier_powers, (list, tuple)):
        raise ValueError("carrier_powers must be a list of watt values")
    if len(carrier_powers) < MIN_CARRIERS:
        raise ValueError(
            "a multicarrier assessment needs at least %d carriers, got %d"
            % (MIN_CARRIERS, len(carrier_powers))
        )
    return tuple(
        _check_positive(p, "carrier power [%d]" % i) for i, p in enumerate(carrier_powers)
    )


def average_power_w(carrier_powers):
    """Return the summed (average) power of the carrier plan in watts."""
    return float(sum(validate_carrier_powers(carrier_powers)))


def peak_envelope_power_w(carrier_powers):
    """Return the coherent peak envelope power: all carriers adding in phase."""
    powers = validate_carrier_powers(carrier_powers)
    amplitude = sum(math.sqrt(p) for p in powers)
    return amplitude * amplitude


def crest_factor_db(carrier_powers):
    """Return the peak-to-average ratio of the carrier plan in decibels."""
    peak = peak_envelope_power_w(carrier_powers)
    mean = average_power_w(carrier_powers)
    return 10.0 * math.log10(peak / mean)


def required_multicarrier_margin_db(
    route, heritage="recurrent", threshold_basis="measured", policy=None
):
    """Return the decibel margin the route owes for this design maturity."""
    rt = normalize_route(route)
    her = normalize_heritage(heritage)
    basis = normalize_threshold_basis(threshold_basis)
    if rt == "test" and basis == "simulated":
        raise ValueError(
            "a test-based route cannot rest on a simulated threshold; the test "
            "measures it"
        )
    table = ROUTE_BASE_MARGIN_DB if policy is None else policy
    if not isinstance(table, dict):
        raise ValueError("policy must be a mapping of route to base decibels")
    if rt not in table:
        raise ValueError("policy carries no base margin for route %r" % rt)
    base = table[rt]
    if isinstance(base, bool) or not isinstance(base, (int, float)):
        raise ValueError("policy base margin for %r must be a number" % rt)
    base = float(base)
    if not math.isfinite(base) or base < 0.0:
        raise ValueError("policy base margin for %r must be finite and >= 0" % rt)
    margin = base + HERITAGE_UPLIFT_DB[her]
    if basis == "simulated":
        margin += SIMULATED_THRESHOLD_UPLIFT_DB
    return margin


def reference_power_w(route, carrier_powers=None, applied_test_power_w=None):
    """Return the power the margin is applied to for the given route."""
    rt = normalize_route(route)
    if rt == "analysis":
        if carrier_powers is None:
            raise ValueError("the analysis route needs the carrier plan")
        return peak_envelope_power_w(carrier_powers)
    if applied_test_power_w is None:
        raise ValueError("the test route needs the applied multicarrier test power")
    return _check_positive(applied_test_power_w, "applied_test_power_w")


def demonstration_power_w(reference_w, margin_value_db):
    """Return the power level the route must demonstrate above the reference."""
    ref = _check_positive(reference_w, "reference_w")
    if isinstance(margin_value_db, bool) or not isinstance(margin_value_db, (int, float)):
        raise ValueError("margin_value_db must be a number, got %r" % (margin_value_db,))
    margin = float(margin_value_db)
    if not math.isfinite(margin):
        raise ValueError("margin_value_db must be finite, got %r" % (margin_value_db,))
    if margin < 0.0:
        raise ValueError("margin_value_db must not be negative, got %r" % (margin_value_db,))
    return ref * (10.0 ** (margin / 10.0))


def achieved_margin_db(threshold_w, reference_w):
    """Return the margin a threshold delivers over the reference power."""
    num = _check_positive(threshold_w, "threshold_w")
    den = _check_positive(reference_w, "reference_w")
    return 10.0 * math.log10(num / den)


def margin_is_met(achieved_db, required_db):
    """True when the achieved margin reaches the required one."""
    for label, value in (("achieved_db", achieved_db), ("required_db", required_db)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a number, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite, got %r" % (label, value))
    return float(achieved_db) >= float(required_db) - MARGIN_TOLERANCE_DB


def evaluate_margin_case(case):
    """Evaluate one multicarrier margin case end to end."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    for key in ("id", "route"):
        if key not in case:
            raise ValueError("case missing required key %r" % (key,))
    identifier = case["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("case id must be a non-empty string, got %r" % (identifier,))
    rt = normalize_route(case["route"])
    required = required_multicarrier_margin_db(
        rt,
        heritage=case.get("heritage", "recurrent"),
        threshold_basis=case.get("threshold_basis", "measured"),
        policy=case.get("policy"),
    )
    reference = reference_power_w(
        rt,
        carrier_powers=case.get("carrier_powers"),
        applied_test_power_w=case.get("applied_test_power_w"),
    )
    demanded = demonstration_power_w(reference, required)
    findings = []
    threshold = case.get("multipactor_threshold_w")
    if threshold is None:
        findings.append("no multipactor threshold on record for this route")
        achieved = None
        compliant = False
    else:
        achieved = achieved_margin_db(threshold, reference)
        compliant = margin_is_met(achieved, required)
        if not compliant:
            findings.append(
                "achieved margin %.3f dB is below the required %.3f dB"
                % (achieved, required)
            )
    return {
        "id": identifier.strip(),
        "route": rt,
        "required_margin_db": required,
        "reference_power_w": reference,
        "demonstration_power_w": demanded,
        "achieved_margin_db": achieved,
        "deficit_db": None if achieved is None else max(0.0, required - achieved),
        "compliant": compliant,
        "findings": findings,
    }


def route_overview(carrier_powers, heritage="recurrent", threshold_basis="measured"):
    """Return the analysis and test demands for one carrier plan side by side.

    Both routes are priced against the same coherent peak envelope power so the
    two demonstration powers are directly comparable; a test campaign that
    applies a different multicarrier level is evaluated through
    :func:`evaluate_margin_case` with that level supplied explicitly.
    """
    powers = validate_carrier_powers(carrier_powers)
    peak = peak_envelope_power_w(powers)
    analysis_margin = required_multicarrier_margin_db(
        "analysis", heritage=heritage, threshold_basis=threshold_basis
    )
    test_margin = required_multicarrier_margin_db("test", heritage=heritage)
    return {
        "carriers": len(powers),
        "average_power_w": average_power_w(powers),
        "peak_envelope_power_w": peak,
        "crest_factor_db": crest_factor_db(powers),
        "analysis": {
            "required_margin_db": analysis_margin,
            "reference_power_w": peak,
            "demonstration_power_w": demonstration_power_w(peak, analysis_margin),
        },
        "test": {
            "required_margin_db": test_margin,
            "reference_power_w": peak,
            "demonstration_power_w": demonstration_power_w(peak, test_margin),
        },
    }


def summarize_cases(cases):
    """Aggregate evaluated cases into one margin-overview verdict."""
    if not isinstance(cases, (list, tuple)) or len(cases) == 0:
        raise ValueError("cases must be a non-empty list")
    results = []
    seen = set()
    for case in cases:
        result = evaluate_margin_case(case)
        if result["id"] in seen:
            raise ValueError("duplicate case id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    open_ids = [r["id"] for r in results if not r["compliant"]]
    deficits = [r["deficit_db"] for r in results if r["deficit_db"] is not None]
    return {
        "cases": len(results),
        "results": results,
        "open_ids": open_ids,
        "worst_deficit_db": max(deficits) if deficits else 0.0,
        "all_routes_compliant": not open_ids,
    }
