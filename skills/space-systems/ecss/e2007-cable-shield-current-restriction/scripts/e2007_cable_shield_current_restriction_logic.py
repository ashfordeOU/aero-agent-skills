"""Restriction on intended current in a cable shield.

Anchor: ECSS-E-ST-20-07C clause 4.2.13.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Decide whether a shielded cable qualifies for the narrow exemption
   in which the shield is allowed to be the intended return: a coaxial
   construction used as a radiofrequency-feed, or a coaxial
   construction used as a high-speed-data link at or above the
   exemption data rate. Anything else is barred from using its shield
   as a current path by design.
2. For a barred cable, check the two ways a design puts intended
   current on the shield: declaring the shield as the return, or
   omitting the dedicated return conductor so the return current has
   nowhere else to go.
3. For every cable, bound the incidental current the shield picks up
   when it is bonded at both ends: predict it from the parallel
   division between the shield resistance and the dedicated return
   resistance, prefer a measured bond-strap total when one is on
   record, and compare against a fraction of the circuit current.
4. For an exempt coaxial run, check the constraints that make the
   outer conductor a usable return: a declared characteristic
   impedance, continuity bonded at both ends, and an outer-conductor
   resistance under its limit.

Stdlib only, offline, deterministic.
"""

CONSTRUCTION_COAXIAL = "coaxial"
VALID_CONSTRUCTIONS = (
    CONSTRUCTION_COAXIAL,
    "twisted-shielded-pair",
    "overbraided-bundle",
    "single-shielded-wire",
)

FUNCTION_RADIOFREQUENCY = "radiofrequency-feed"
FUNCTION_HIGH_SPEED_DATA = "high-speed-data"
VALID_FUNCTIONS = (
    FUNCTION_RADIOFREQUENCY,
    FUNCTION_HIGH_SPEED_DATA,
    "low-frequency-signal",
    "discrete-command",
    "analog-sensor",
    "power-distribution",
)

# A data link at or above this rate needs a controlled-impedance
# coaxial return and therefore qualifies for the exemption.
HIGH_SPEED_DATA_RATE_LIMIT_MBPS = 10.0

# Current a both-end-bonded shield may pick up incidentally, as a
# fraction of the circuit current it accompanies.
INCIDENTAL_SHIELD_CURRENT_FRACTION_LIMIT = 0.05

# Outer-conductor resistance limit for an exempt coaxial run.
MAX_COAXIAL_SHIELD_RESISTANCE_OHM = 0.5

# A shield current is a sum of measured bond-strap currents, or a
# product of a divided fraction, so a design sitting exactly on the
# incidental limit can land a few ULPs over. One picoampere is far
# below any harness measurement resolution and absorbs that
# representation error without relaxing the limit itself.
CURRENT_TOLERANCE_A = 1.0e-12

EXEMPT = "exempt"
NOT_EXEMPT = "not-exempt"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_cable(cable):
    """Validate one cable record and return a normalized copy."""
    if not isinstance(cable, dict):
        raise ValueError("cable must be a mapping")
    cable_id = cable.get("id")
    if not isinstance(cable_id, str) or not cable_id.strip():
        raise ValueError("cable needs a non-empty string id")
    function = cable.get("function")
    if function not in VALID_FUNCTIONS:
        raise ValueError(
            "cable %s has unknown function %r (expected one of %s)"
            % (cable_id, function, ", ".join(VALID_FUNCTIONS))
        )
    construction = cable.get("construction")
    if construction not in VALID_CONSTRUCTIONS:
        raise ValueError(
            "cable %s has unknown construction %r (expected one of %s)"
            % (cable_id, construction, ", ".join(VALID_CONSTRUCTIONS))
        )
    straps = cable.get("bond_strap_currents_a")
    if straps is not None:
        if not isinstance(straps, (list, tuple)) or not straps:
            raise ValueError(
                "cable %s bond_strap_currents_a must be a non-empty sequence" % cable_id
            )
        straps = [_numeric("cable %s bond strap current" % cable_id, s, 0.0) for s in straps]
    impedance = cable.get("characteristic_impedance_ohm")
    if impedance is not None:
        impedance = _numeric("cable %s characteristic_impedance_ohm" % cable_id, impedance)
        if impedance <= 0:
            raise ValueError("cable %s characteristic_impedance_ohm must be positive" % cable_id)
    return_resistance = cable.get("return_resistance_ohm")
    if return_resistance is not None:
        return_resistance = _numeric(
            "cable %s return_resistance_ohm" % cable_id, return_resistance
        )
        if return_resistance <= 0:
            raise ValueError("cable %s return_resistance_ohm must be positive" % cable_id)
    shield_resistance = _numeric(
        "cable %s shield_resistance_ohm" % cable_id, cable.get("shield_resistance_ohm", 0.05)
    )
    if shield_resistance <= 0:
        raise ValueError("cable %s shield_resistance_ohm must be positive" % cable_id)
    return {
        "id": cable_id,
        "function": function,
        "construction": construction,
        "shield_is_intended_return": _boolean(
            "cable %s shield_is_intended_return" % cable_id,
            cable.get("shield_is_intended_return", False),
        ),
        "dedicated_return_conductor": _boolean(
            "cable %s dedicated_return_conductor" % cable_id,
            cable.get("dedicated_return_conductor", True),
        ),
        "shield_bonded_both_ends": _boolean(
            "cable %s shield_bonded_both_ends" % cable_id,
            cable.get("shield_bonded_both_ends", True),
        ),
        "data_rate_mbps": _numeric(
            "cable %s data_rate_mbps" % cable_id, cable.get("data_rate_mbps", 0.0), 0.0
        ),
        "circuit_current_a": _numeric(
            "cable %s circuit_current_a" % cable_id, cable.get("circuit_current_a", 0.0), 0.0
        ),
        "shield_resistance_ohm": shield_resistance,
        "return_resistance_ohm": return_resistance,
        "characteristic_impedance_ohm": impedance,
        "bond_strap_currents_a": straps,
    }


def exemption_status(cable):
    """Return (status, reason) for the coaxial/high-speed-data exemption."""
    norm = validate_cable(cable)
    if norm["construction"] != CONSTRUCTION_COAXIAL:
        return NOT_EXEMPT, "construction-is-not-coaxial"
    if norm["function"] == FUNCTION_RADIOFREQUENCY:
        return EXEMPT, "coaxial-radiofrequency-feed"
    if norm["function"] == FUNCTION_HIGH_SPEED_DATA:
        if norm["data_rate_mbps"] >= HIGH_SPEED_DATA_RATE_LIMIT_MBPS:
            return EXEMPT, "coaxial-high-speed-data-link"
        return NOT_EXEMPT, "data-rate-below-exemption-threshold"
    return NOT_EXEMPT, "function-outside-the-exemption"


def shield_current_share(shield_resistance_ohm, return_resistance_ohm):
    """Fraction of return current diverted onto a both-end-bonded shield."""
    shield = _numeric("shield_resistance_ohm", shield_resistance_ohm)
    ret = _numeric("return_resistance_ohm", return_resistance_ohm)
    if shield <= 0 or ret <= 0:
        raise ValueError("both resistances must be positive")
    return ret / (shield + ret)


def measured_shield_current_a(cable):
    """Total measured bond-strap current, or None when none is on record."""
    norm = validate_cable(cable)
    straps = norm["bond_strap_currents_a"]
    if straps is None:
        return None
    total = 0.0
    for value in straps:
        total += value
    return total


def predicted_shield_current_a(cable):
    """Shield current the topology produces, in amperes."""
    norm = validate_cable(cable)
    if not norm["dedicated_return_conductor"]:
        return norm["circuit_current_a"]
    if not norm["shield_bonded_both_ends"]:
        return 0.0
    if norm["return_resistance_ohm"] is None:
        raise ValueError(
            "cable %s declares a dedicated return conductor but no "
            "return_resistance_ohm" % norm["id"]
        )
    share = shield_current_share(norm["shield_resistance_ohm"], norm["return_resistance_ohm"])
    return norm["circuit_current_a"] * share


def incidental_current_limit_a(cable):
    """Incidental shield current allowed for one cable, in amperes."""
    norm = validate_cable(cable)
    return INCIDENTAL_SHIELD_CURRENT_FRACTION_LIMIT * norm["circuit_current_a"]


def check_intended_current_use(cable):
    """Findings for a cable whose shield carries intended current."""
    norm = validate_cable(cable)
    status, reason = exemption_status(norm)
    findings = []
    if status == EXEMPT:
        return findings
    if norm["shield_is_intended_return"]:
        findings.append("shield-declared-as-intended-return-without-exemption")
    if not norm["dedicated_return_conductor"]:
        findings.append("no-dedicated-return-conductor-forces-current-onto-shield")
    if (
        reason == "data-rate-below-exemption-threshold"
        and norm["shield_is_intended_return"]
    ):
        findings.append("data-rate-below-exemption-threshold")
    return findings


def check_incidental_current(cable):
    """Findings for incidental shield current beyond the allowed fraction."""
    norm = validate_cable(cable)
    status, _ = exemption_status(norm)
    if status == EXEMPT:
        return [], None
    if not norm["dedicated_return_conductor"]:
        return [], None
    measured = measured_shield_current_a(norm)
    current = measured if measured is not None else predicted_shield_current_a(norm)
    limit = incidental_current_limit_a(norm)
    findings = []
    if current > limit + CURRENT_TOLERANCE_A:
        findings.append("incidental-shield-current-above-limit")
    return findings, current


def check_exempt_coaxial_constraints(cable):
    """Findings for an exempt coaxial run whose outer conductor is the return."""
    norm = validate_cable(cable)
    status, _ = exemption_status(norm)
    findings = []
    if status != EXEMPT:
        return findings
    if norm["characteristic_impedance_ohm"] is None:
        findings.append("exempt-coaxial-characteristic-impedance-not-declared")
    if not norm["shield_bonded_both_ends"]:
        findings.append("exempt-coaxial-outer-conductor-not-bonded-both-ends")
    if norm["shield_resistance_ohm"] > MAX_COAXIAL_SHIELD_RESISTANCE_OHM:
        findings.append("exempt-coaxial-shield-resistance-above-limit")
    return findings


def assess_cable(cable):
    """Assess one cable against clause 4.2.13.2."""
    norm = validate_cable(cable)
    status, reason = exemption_status(norm)
    findings = list(check_intended_current_use(norm))
    incidental_findings, current = check_incidental_current(norm)
    findings.extend(incidental_findings)
    findings.extend(check_exempt_coaxial_constraints(norm))
    return {
        "id": norm["id"],
        "exemption": status,
        "exemption_reason": reason,
        "shield_current_a": current,
        "incidental_limit_a": incidental_current_limit_a(norm),
        "findings": findings,
        "compliant": not findings,
    }


def assess_shield_current_restriction(cables):
    """Run the full clause 4.2.13.2 assessment over a cable list."""
    if not isinstance(cables, list) or not cables:
        raise ValueError("cables must be a non-empty list")
    results = []
    seen = set()
    for cable in cables:
        result = assess_cable(cable)
        if result["id"] in seen:
            raise ValueError("duplicate cable id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    return {
        "cables": results,
        "exempt_ids": [r["id"] for r in results if r["exemption"] == EXEMPT],
        "non_compliant_ids": non_compliant,
        "compliant": not non_compliant,
    }
