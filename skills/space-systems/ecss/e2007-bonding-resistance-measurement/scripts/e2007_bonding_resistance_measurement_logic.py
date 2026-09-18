"""Four-wire low-resistance measurement of spacecraft bonds.

Anchor: ECSS-E-ST-20-07C clause 5.3.10 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Decide which bonds owe a measurement. Every bond in the bonding
   schedule is measured except a bond whose only role is the control
   of electrostatic charging -- a charge-bleed path is sized by the
   leakage it must carry, not by a milliohm reference target, so the
   low-resistance measurement says nothing about it. A charge-bleed
   path that also carries a second role is measured like any other.
2. Check the measurement setup. The reading has to come from a
   four-wire arrangement: a current-injection pair and a separate
   voltage-sense pair, with the injection current inside the range the
   instrument and the bond can both take. A two-wire reading folds the
   lead and contact resistance of the probe set into the result and is
   not admissible evidence for a milliohm target.
3. Compute the bond resistance from the sensed voltage and the
   injected current, and compare it against the limit its purpose
   carries.
4. Aggregate the schedule: exempt bonds are listed so the exemption is
   visible for review, and the schedule is compliant only when no
   measured bond carries a finding.

Stdlib only, offline, deterministic.
"""

BOND_PURPOSE_CHARGING_CONTROL = "electrostatic-charging-control"
VALID_BOND_PURPOSES = (
    BOND_PURPOSE_CHARGING_CONTROL,
    "structural-reference",
    "power-current-return",
    "radiofrequency-reference",
    "lightning-current-path",
    "shield-termination",
)

METHOD_FOUR_WIRE = "four-wire"
METHOD_TWO_WIRE = "two-wire"
METHOD_NONE = "none"
VALID_METHODS = (METHOD_FOUR_WIRE, METHOD_TWO_WIRE, METHOD_NONE)

# Bond resistance limit by purpose, in ohms. A current-carrying path is
# held tighter than a reference-only path.
BOND_RESISTANCE_LIMIT_OHM = {
    "structural-reference": 2.5e-3,
    "power-current-return": 1.0e-3,
    "radiofrequency-reference": 2.5e-3,
    "lightning-current-path": 1.0e-3,
    "shield-termination": 2.5e-3,
}

# Injection current window: below the floor the sensed voltage sits in
# the instrument noise, above the ceiling the joint is heated by the
# measurement itself.
MIN_INJECTION_CURRENT_A = 0.1
MAX_INJECTION_CURRENT_A = 10.0

# Representative lead-plus-contact resistance a two-wire probe set adds
# to its own reading. Three orders above the milliohm targets, which is
# why a two-wire reading cannot support them.
TYPICAL_LEAD_RESISTANCE_OHM = 20.0e-3

# A resistance is a quotient of two measured floats, so a bond sitting
# exactly on its limit can land a few units in the last place above it.
# A picoohm is far below any bond-tester resolution and absorbs that
# representation error without relaxing the limit itself.
RESISTANCE_TOLERANCE_OHM = 1.0e-12

REQUIRED = "measurement-required"
EXEMPT = "measurement-exempt"


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


def validate_bond(bond):
    """Validate one bond record and return a normalized copy."""
    if not isinstance(bond, dict):
        raise ValueError("bond must be a mapping")
    bond_id = bond.get("id")
    if not isinstance(bond_id, str) or not bond_id.strip():
        raise ValueError("bond needs a non-empty string id")
    purpose = bond.get("purpose")
    if purpose not in VALID_BOND_PURPOSES:
        raise ValueError(
            "bond %s has unknown purpose %r (expected one of %s)"
            % (bond_id, purpose, ", ".join(VALID_BOND_PURPOSES))
        )
    extra = bond.get("additional_purposes", [])
    if not isinstance(extra, (list, tuple)):
        raise ValueError("bond %s additional_purposes must be a sequence" % bond_id)
    for item in extra:
        if item not in VALID_BOND_PURPOSES:
            raise ValueError(
                "bond %s has unknown additional purpose %r" % (bond_id, item)
            )
    method = bond.get("method", METHOD_NONE)
    if method not in VALID_METHODS:
        raise ValueError(
            "bond %s has unknown method %r (expected one of %s)"
            % (bond_id, method, ", ".join(VALID_METHODS))
        )
    injection = bond.get("injection_current_a")
    if injection is not None:
        injection = _numeric("bond %s injection_current_a" % bond_id, injection)
        if injection <= 0:
            raise ValueError("bond %s injection_current_a must be positive" % bond_id)
    sensed = bond.get("sensed_voltage_v")
    if sensed is not None:
        sensed = _numeric("bond %s sensed_voltage_v" % bond_id, sensed, 0.0)
    reported = bond.get("reported_resistance_ohm")
    if reported is not None:
        reported = _numeric("bond %s reported_resistance_ohm" % bond_id, reported, 0.0)
    return {
        "id": bond_id,
        "purpose": purpose,
        "additional_purposes": [str(item) for item in extra],
        "method": method,
        "separate_sense_pair": _boolean(
            "bond %s separate_sense_pair" % bond_id,
            bond.get("separate_sense_pair", method == METHOD_FOUR_WIRE),
        ),
        "injection_current_a": injection,
        "sensed_voltage_v": sensed,
        "reported_resistance_ohm": reported,
    }


def measurement_required(bond):
    """Return (status, reason) for the charging-control exemption."""
    norm = validate_bond(bond)
    if norm["purpose"] != BOND_PURPOSE_CHARGING_CONTROL:
        return REQUIRED, "purpose-carries-a-resistance-target"
    if norm["additional_purposes"]:
        return REQUIRED, "charge-bleed-path-with-a-second-role"
    return EXEMPT, "serves-charging-control-only"


def bond_resistance_limit_ohm(bond):
    """Resistance limit for a bond that owes a measurement, in ohms."""
    norm = validate_bond(bond)
    status, _ = measurement_required(norm)
    if status == EXEMPT:
        raise ValueError(
            "bond %s serves charging control only and carries no "
            "resistance limit" % norm["id"]
        )
    candidates = [norm["purpose"]] + norm["additional_purposes"]
    limits = [
        BOND_RESISTANCE_LIMIT_OHM[p] for p in candidates if p in BOND_RESISTANCE_LIMIT_OHM
    ]
    if not limits:
        raise ValueError("bond %s has no purpose carrying a limit" % norm["id"])
    return min(limits)


def resistance_from_four_wire(sensed_voltage_v, injection_current_a):
    """Bond resistance from the sensed voltage and the injected current."""
    voltage = _numeric("sensed_voltage_v", sensed_voltage_v, 0.0)
    current = _numeric("injection_current_a", injection_current_a)
    if current <= 0:
        raise ValueError("injection_current_a must be positive")
    return voltage / current


def two_wire_reading_error_ohm():
    """Resistance a two-wire probe set adds to its own reading, in ohms."""
    return TYPICAL_LEAD_RESISTANCE_OHM


def check_setup(bond):
    """Findings about the measurement arrangement of one bond."""
    norm = validate_bond(bond)
    status, _ = measurement_required(norm)
    findings = []
    if status == EXEMPT:
        return findings
    if norm["method"] == METHOD_NONE:
        findings.append("no-resistance-measurement-on-record")
        return findings
    if norm["method"] == METHOD_TWO_WIRE:
        findings.append("two-wire-reading-includes-lead-and-contact-resistance")
        return findings
    if not norm["separate_sense_pair"]:
        findings.append("sense-pair-not-separated-from-injection-pair")
    if norm["injection_current_a"] is None:
        findings.append("injection-current-not-on-record")
    elif norm["injection_current_a"] < MIN_INJECTION_CURRENT_A:
        findings.append("injection-current-below-window")
    elif norm["injection_current_a"] > MAX_INJECTION_CURRENT_A:
        findings.append("injection-current-above-window")
    if norm["sensed_voltage_v"] is None:
        findings.append("sensed-voltage-not-on-record")
    return findings


def measured_resistance_ohm(bond):
    """Four-wire bond resistance in ohms, or None when none is usable."""
    norm = validate_bond(bond)
    if norm["method"] != METHOD_FOUR_WIRE:
        return None
    if norm["injection_current_a"] is None or norm["sensed_voltage_v"] is None:
        return None
    return resistance_from_four_wire(
        norm["sensed_voltage_v"], norm["injection_current_a"]
    )


def check_resistance_limit(bond):
    """Findings about the measured value of one bond, plus that value."""
    norm = validate_bond(bond)
    status, _ = measurement_required(norm)
    if status == EXEMPT:
        return [], None
    resistance = measured_resistance_ohm(norm)
    if resistance is None:
        return [], None
    limit = bond_resistance_limit_ohm(norm)
    findings = []
    if resistance > limit + RESISTANCE_TOLERANCE_OHM:
        findings.append("bond-resistance-above-purpose-limit")
    return findings, resistance


def assess_bond(bond):
    """Assess one bond against clause 5.3.10."""
    norm = validate_bond(bond)
    status, reason = measurement_required(norm)
    findings = list(check_setup(norm))
    limit_findings, resistance = check_resistance_limit(norm)
    findings.extend(limit_findings)
    limit = None
    if status == REQUIRED:
        limit = bond_resistance_limit_ohm(norm)
    return {
        "id": norm["id"],
        "status": status,
        "status_reason": reason,
        "method": norm["method"],
        "resistance_ohm": resistance,
        "limit_ohm": limit,
        "findings": findings,
        "compliant": not findings,
    }


def assess_bonding_resistance_measurement(bonds):
    """Run the full clause 5.3.10 assessment over a bonding schedule."""
    if not isinstance(bonds, list) or not bonds:
        raise ValueError("bonds must be a non-empty list")
    results = []
    seen = set()
    for bond in bonds:
        result = assess_bond(bond)
        if result["id"] in seen:
            raise ValueError("duplicate bond id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    return {
        "bonds": results,
        "exempt_ids": [r["id"] for r in results if r["status"] == EXEMPT],
        "measured_ids": [
            r["id"] for r in results if r["resistance_ohm"] is not None
        ],
        "non_compliant_ids": non_compliant,
        "compliant": not non_compliant,
    }
