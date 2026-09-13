#!/usr/bin/env python3
"""Definition of the nominal multipactor-free input power of an equipment.

Anchor: ECSS-E-ST-20-01C clause 4.3.1.1 (the specified input power at which
the equipment stays free of multipactor discharge). Paraphrased into an
implementable procedure; no verbatim standard text.

Stdlib only, offline, deterministic.

Procedure implemented here:

1. validate the declared per-carrier powers at the equipment input;
2. combine them by the agreed rule -- the in-phase peak envelope for a
   multi-carrier unit, the average sum where that is what the equipment
   sees, a single carrier on its own;
3. report the peak-to-average ratio so a multi-carrier unit specified on
   its average is visible as such;
4. convert freely between watt and decibel-milliwatt;
5. aggregate the input-power budget: signed biases add algebraically,
   uncertainty magnitudes combine either linearly (worst case) or by
   root-sum-square (statistical);
6. derive the worst-case input power the definition has to cover and
   compare the declared multipactor-free power with it, absorbing
   floating-point representation error exactly at equality;
7. apply the route margin to obtain the level the analysis or the
   multipactor test has to reach, and aggregate the findings.

The combining rules, budget methods and default route margins below are
project-replaceable defaults expressing the clause intent, not a
reproduction of any table of the standard.
"""

import math

# A declared power landing exactly on the derived worst case is compliant;
# the comparison absorbs floating-point representation error instead of
# moving the engineering limit.
POWER_REL_TOL = 1e-12
POWER_ABS_TOL = 1e-9

MILLIWATT_PER_WATT = 1000.0

COMBINING_RULES = (
    "coherent-peak",
    "average-sum",
    "single-carrier",
)

BUDGET_METHODS = ("arithmetic-sum", "root-sum-square")

TERM_KINDS = ("bias", "uncertainty")

# Default decibel margin owed above the nominal multipactor-free power,
# per verification route.
DEFAULT_ROUTE_MARGINS_DB = {
    "multipactor-analysis": 6.0,
    "multipactor-test": 3.0,
    "similarity": 6.0,
}

# A multi-carrier unit specified on its average sum understates the field
# by the peak-to-average ratio; beyond this the omission is reported.
PEAK_TO_AVERAGE_REPORTING_DB = 0.0


def _finite(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be a finite number" % label)
    return value


def watt_to_dbm(power_w):
    """Convert a strictly positive power in watt to decibel-milliwatt."""
    value = _finite(power_w, "power in watt")
    if value <= 0.0:
        raise ValueError("power in watt must be strictly positive, got %r" % (power_w,))
    return 10.0 * math.log10(value * MILLIWATT_PER_WATT)


def dbm_to_watt(power_dbm):
    """Convert a level in decibel-milliwatt to power in watt."""
    value = _finite(power_dbm, "power in decibel-milliwatt")
    return (10.0 ** (value / 10.0)) / MILLIWATT_PER_WATT


def validate_carrier_powers(carrier_watts):
    """Every carrier at the equipment input carries a positive power."""
    if not isinstance(carrier_watts, (list, tuple)):
        raise ValueError("carrier powers must be a list")
    if not carrier_watts:
        raise ValueError("at least one carrier power is required")
    validated = []
    for index, power in enumerate(carrier_watts):
        value = _finite(power, "carrier[%d] power" % index)
        if value <= 0.0:
            raise ValueError("carrier[%d] power must be strictly positive" % index)
        validated.append(value)
    return validated


def combine_carrier_powers(carrier_watts, rule):
    """Combine the carriers into the power the equipment input sees."""
    if not isinstance(rule, str):
        raise ValueError("combining rule must be a string, got %r" % (rule,))
    key = rule.strip().lower()
    if key not in COMBINING_RULES:
        raise ValueError(
            "unrecognized combining rule %r; known: %s" % (rule, ", ".join(COMBINING_RULES))
        )
    powers = validate_carrier_powers(carrier_watts)
    if key == "single-carrier":
        if len(powers) != 1:
            raise ValueError(
                "single-carrier rule needs exactly one carrier, got %d" % len(powers)
            )
        return powers[0]
    if key == "average-sum":
        return math.fsum(powers)
    amplitude = math.fsum(math.sqrt(power) for power in powers)
    return amplitude * amplitude


def peak_to_average_ratio_db(carrier_watts):
    """Decibel gap between the in-phase envelope and the average sum."""
    powers = validate_carrier_powers(carrier_watts)
    peak = combine_carrier_powers(powers, "coherent-peak")
    average = combine_carrier_powers(powers, "average-sum")
    return 10.0 * math.log10(peak / average)


def aggregate_uncertainty_db(terms, method="arithmetic-sum"):
    """Aggregate the input-power budget: signed biases plus uncertainties."""
    if not isinstance(terms, (list, tuple)):
        raise ValueError("budget terms must be a list")
    if not isinstance(method, str):
        raise ValueError("budget method must be a string, got %r" % (method,))
    key = method.strip().lower()
    if key not in BUDGET_METHODS:
        raise ValueError(
            "unrecognized budget method %r; known: %s" % (method, ", ".join(BUDGET_METHODS))
        )
    bias_db = 0.0
    magnitudes = []
    named = []
    for index, term in enumerate(terms):
        if not isinstance(term, dict):
            raise ValueError("budget term[%d] must be a mapping" % index)
        name = term.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("budget term[%d] has no name" % index)
        kind = term.get("kind", "uncertainty")
        if not isinstance(kind, str) or kind.strip().lower() not in TERM_KINDS:
            raise ValueError(
                "budget term %r has an unrecognized kind %r; known: %s"
                % (name, kind, ", ".join(TERM_KINDS))
            )
        kind = kind.strip().lower()
        value = _finite(term.get("db"), "budget term %r" % name)
        if kind == "uncertainty":
            if value < 0.0:
                raise ValueError(
                    "uncertainty term %r must carry a non-negative magnitude" % name
                )
            magnitudes.append(value)
        else:
            bias_db += value
        named.append({"name": name.strip(), "kind": kind, "db": value})
    if key == "arithmetic-sum":
        uncertainty_db = math.fsum(magnitudes)
    else:
        uncertainty_db = math.sqrt(math.fsum(value * value for value in magnitudes))
    return {
        "method": key,
        "terms": named,
        "bias_db": bias_db,
        "uncertainty_db": uncertainty_db,
        "total_db": bias_db + uncertainty_db,
    }


def derive_nominal_multipactor_free_power(carrier_watts, combining_rule="coherent-peak",
                                          budget_terms=(), budget_method="arithmetic-sum"):
    """Worst-case input power the multipactor-free definition has to cover."""
    powers = validate_carrier_powers(carrier_watts)
    combined_w = combine_carrier_powers(powers, combining_rule)
    combined_dbm = watt_to_dbm(combined_w)
    budget = aggregate_uncertainty_db(budget_terms, budget_method)
    worst_case_dbm = combined_dbm + budget["total_db"]
    return {
        "carrier_count": len(powers),
        "combining_rule": combining_rule.strip().lower(),
        "combined_w": combined_w,
        "combined_dbm": combined_dbm,
        "budget": budget,
        "worst_case_dbm": worst_case_dbm,
        "worst_case_w": dbm_to_watt(worst_case_dbm),
    }


def verify_declared_power(declared_dbm, required_dbm):
    """The declared multipactor-free power has to cover the worst case."""
    declared = _finite(declared_dbm, "declared power")
    required = _finite(required_dbm, "required power")
    shortfall_db = required - declared
    covers = declared >= required or math.isclose(
        declared, required, rel_tol=POWER_REL_TOL, abs_tol=POWER_ABS_TOL
    )
    return {
        "declared_dbm": declared,
        "required_dbm": required,
        "shortfall_db": max(0.0, shortfall_db) if not covers else 0.0,
        "headroom_db": declared - required,
        "covers_worst_case": covers,
    }


def route_margin_db(route, overrides=None):
    """Decibel margin owed above the nominal power, per verification route."""
    if not isinstance(route, str):
        raise ValueError("verification route must be a string, got %r" % (route,))
    key = route.strip().lower()
    table = dict(DEFAULT_ROUTE_MARGINS_DB)
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise ValueError("route margin overrides must be a mapping")
        for name, value in overrides.items():
            table[str(name).strip().lower()] = _finite(value, "margin for %r" % name)
    if key not in table:
        raise ValueError(
            "unrecognized verification route %r; known: %s" % (route, ", ".join(sorted(table)))
        )
    margin = table[key]
    if margin < 0.0:
        raise ValueError("route margin must not be negative, got %r" % (margin,))
    return margin


def apply_power_margin(power_dbm, margin_db):
    """Raise a level by a non-negative decibel margin."""
    level = _finite(power_dbm, "power level")
    margin = _finite(margin_db, "margin")
    if margin < 0.0:
        raise ValueError("margin must not be negative, got %r" % (margin_db,))
    return level + margin


def assess_nominal_power_definition(spec):
    """Aggregate verdict on the clause 4.3.1.1 power definition."""
    if not isinstance(spec, dict):
        raise ValueError("specification must be a mapping")
    carriers = spec.get("carrier_watts")
    rule = spec.get("combining_rule", "coherent-peak")
    derivation = derive_nominal_multipactor_free_power(
        carriers,
        rule,
        spec.get("budget_terms", ()),
        spec.get("budget_method", "arithmetic-sum"),
    )
    declared = spec.get("declared_nominal_dbm")
    if declared is None:
        declared_w = spec.get("declared_nominal_w")
        if declared_w is None:
            raise ValueError(
                "the specification declares no nominal multipactor-free power"
            )
        declared = watt_to_dbm(declared_w)
    check = verify_declared_power(declared, derivation["worst_case_dbm"])
    route = spec.get("verification_route", "multipactor-test")
    margin = route_margin_db(route, spec.get("route_margins"))
    demonstration_dbm = apply_power_margin(check["declared_dbm"], margin)
    findings = []
    if not check["covers_worst_case"]:
        findings.append(
            "declared multipactor-free power is %.3f dB below the worst-case input"
            % check["shortfall_db"]
        )
    ratio_db = peak_to_average_ratio_db(carriers)
    if derivation["carrier_count"] > 1 and derivation["combining_rule"] == "average-sum":
        if ratio_db > PEAK_TO_AVERAGE_REPORTING_DB:
            findings.append(
                "multi-carrier unit specified on its average sum; the in-phase "
                "envelope is %.2f dB higher" % ratio_db
            )
    if derivation["carrier_count"] == 1 and derivation["combining_rule"] == "coherent-peak":
        findings.append(
            "single carrier combined with the coherent-peak rule; state the rule "
            "as single-carrier so the definition is unambiguous"
        )
    if derivation["budget"]["uncertainty_db"] == 0.0 and derivation["budget"]["bias_db"] == 0.0:
        findings.append(
            "no uncertainty or bias term is carried; the declared power then "
            "rests on the nominal drive level alone"
        )
    return {
        "derivation": derivation,
        "declaration": check,
        "verification_route": route.strip().lower(),
        "route_margin_db": margin,
        "demonstration_level_dbm": demonstration_dbm,
        "demonstration_level_w": dbm_to_watt(demonstration_dbm),
        "peak_to_average_db": ratio_db,
        "findings": findings,
        "compliant": check["covers_worst_case"] and not findings,
    }
