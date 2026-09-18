"""System grounding isolation and continuity measurements at assembly.

Anchor: ECSS-E-ST-20-07C clause 5.3.9 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Read the grounding architecture as a set of declared node pairs, each
   with an intent: bonded, in which case a bond category fixes the
   resistance the joint has to come in under, or isolated, in which case
   a floor fixes the resistance it has to stay above at a stated test
   voltage.
2. Take the measurements made at assembly and match them to the declared
   pairs. A declared pair with no measurement is not a pass, and a
   measured pair the architecture never declared is a connection nobody
   designed.
3. Grade each continuity measurement against its category limit, and
   refuse a milliohm bond taken with a two-wire instrument, whose own
   lead resistance is larger than the quantity being measured.
4. Grade each isolation measurement against the floor, separating a
   degraded isolation from a pair that measured as a short, since the
   second is an unintended bond in the architecture rather than a
   leakage path, and check that the test voltage reached the minimum.
5. Check the single-point discipline of the power domains: each domain
   references structure at exactly one place. None leaves the domain
   floating, more than one closes the ground loop the architecture was
   drawn to avoid.

Resistances are in ohms throughout; a milliohm bond and a megohm
isolation therefore sit in the same unit and no conversion is hidden in
a comparison.

Stdlib only, offline, deterministic.
"""

INTENT_BONDED = "bonded"
INTENT_ISOLATED = "isolated"
VALID_INTENTS = (INTENT_BONDED, INTENT_ISOLATED)

METHOD_TWO_WIRE = "two-wire"
METHOD_FOUR_WIRE = "four-wire"
VALID_METHODS = (METHOD_TWO_WIRE, METHOD_FOUR_WIRE)

# Direct-current resistance a bond has to come in under, per category.
BOND_CATEGORY_LIMITS_OHM = {
    "structure-bond": 0.0025,
    "unit-chassis-bond": 0.010,
    "shield-termination-bond": 0.010,
    "signal-reference-bond": 0.050,
    "lightning-path-bond": 0.001,
}

# Isolation floor, the minimum test voltage it is confirmed at, and the
# resistance below which a declared-isolated pair is not degraded but
# simply connected.
ISOLATION_FLOOR_OHM = 1.0e6
MIN_ISOLATION_TEST_VOLTAGE_V = 50.0
CONTINUOUS_PAIR_THRESHOLD_OHM = 1.0

# A two-wire instrument carries its own lead resistance into the reading,
# so it cannot resolve a bond below this value.
TWO_WIRE_RESOLUTION_FLOOR_OHM = 0.010

# A resistance is a ratio of two measured quantities, so a joint sitting
# exactly on its limit can land a few units in the last place either
# side. This tolerance is far below any bonding-meter resolution and
# absorbs that representation error without relaxing the limit itself.
RESISTANCE_TOLERANCE_OHM = 1.0e-12


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def _node(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value


def bond_limit_ohm(category):
    """Resistance limit for one bond category, in ohms."""
    if category not in BOND_CATEGORY_LIMITS_OHM:
        raise ValueError(
            "unknown bond category %r (expected one of %s)"
            % (category, ", ".join(sorted(BOND_CATEGORY_LIMITS_OHM)))
        )
    return BOND_CATEGORY_LIMITS_OHM[category]


def pair_key(node_a, node_b):
    """Order-independent key for a node pair."""
    a = _node("node_a", node_a)
    b = _node("node_b", node_b)
    if a == b:
        raise ValueError("a pair must join two different nodes, got %r twice" % (a,))
    return (a, b) if a <= b else (b, a)


def validate_declaration(declaration):
    """Validate one declared architecture pair and return a normalized copy."""
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping")
    intent = declaration.get("intent")
    if intent not in VALID_INTENTS:
        raise ValueError(
            "declaration has unknown intent %r (expected one of %s)"
            % (intent, ", ".join(VALID_INTENTS))
        )
    key = pair_key(declaration.get("node_a"), declaration.get("node_b"))
    category = declaration.get("bond_category")
    if intent == INTENT_BONDED:
        if category is None:
            raise ValueError("bonded pair %s/%s needs a bond_category" % key)
        bond_limit_ohm(category)
    elif category is not None:
        raise ValueError("isolated pair %s/%s must not carry a bond_category" % key)
    domain = declaration.get("power_domain")
    if domain is not None:
        domain = _node("power_domain", domain)
    return {
        "key": key,
        "node_a": key[0],
        "node_b": key[1],
        "intent": intent,
        "bond_category": category,
        "power_domain": domain,
    }


def validate_measurement(measurement):
    """Validate one assembly measurement and return a normalized copy."""
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping")
    key = pair_key(measurement.get("node_a"), measurement.get("node_b"))
    resistance = _numeric("measurement %s/%s resistance_ohm" % key,
                          measurement.get("resistance_ohm"), 0.0)
    method = measurement.get("method", METHOD_FOUR_WIRE)
    if method not in VALID_METHODS:
        raise ValueError(
            "measurement %s/%s has unknown method %r (expected one of %s)"
            % (key + (method, ", ".join(VALID_METHODS)))
        )
    voltage = measurement.get("test_voltage_v")
    if voltage is not None:
        voltage = _numeric("measurement %s/%s test_voltage_v" % key, voltage, 0.0)
    return {
        "key": key,
        "node_a": key[0],
        "node_b": key[1],
        "resistance_ohm": resistance,
        "method": method,
        "test_voltage_v": voltage,
    }


def index_measurements(measurements):
    """Index the measurements by pair, refusing a repeated pair."""
    if not isinstance(measurements, list):
        raise ValueError("measurements must be a list")
    indexed = {}
    for measurement in measurements:
        norm = validate_measurement(measurement)
        if norm["key"] in indexed:
            raise ValueError("duplicate measurement for pair %s/%s" % norm["key"])
        indexed[norm["key"]] = norm
    return indexed


def check_continuity(declaration, measurement):
    """Findings for a bonded pair measured at assembly."""
    declared = validate_declaration(declaration)
    if declared["intent"] != INTENT_BONDED:
        raise ValueError("check_continuity needs a bonded declaration")
    norm = validate_measurement(measurement)
    limit = bond_limit_ohm(declared["bond_category"])
    findings = []
    if norm["resistance_ohm"] > limit + RESISTANCE_TOLERANCE_OHM:
        findings.append("bond-resistance-above-the-category-limit")
    if (
        norm["method"] == METHOD_TWO_WIRE
        and limit < TWO_WIRE_RESOLUTION_FLOOR_OHM - RESISTANCE_TOLERANCE_OHM
    ):
        findings.append("bond-measured-below-the-two-wire-resolution-floor")
    return findings


def check_isolation(declaration, measurement):
    """Findings for an isolated pair measured at assembly."""
    declared = validate_declaration(declaration)
    if declared["intent"] != INTENT_ISOLATED:
        raise ValueError("check_isolation needs an isolated declaration")
    norm = validate_measurement(measurement)
    findings = []
    if norm["resistance_ohm"] < CONTINUOUS_PAIR_THRESHOLD_OHM:
        findings.append("isolated-pair-measured-as-continuous")
    elif norm["resistance_ohm"] < ISOLATION_FLOOR_OHM - RESISTANCE_TOLERANCE_OHM:
        findings.append("isolation-resistance-below-the-floor")
    if norm["test_voltage_v"] is None:
        findings.append("isolation-test-voltage-not-recorded")
    elif norm["test_voltage_v"] < MIN_ISOLATION_TEST_VOLTAGE_V:
        findings.append("isolation-test-voltage-below-the-minimum")
    return findings


def check_pair(declaration, measurement):
    """Findings for one declared pair, measured or not."""
    declared = validate_declaration(declaration)
    if measurement is None:
        if declared["intent"] == INTENT_BONDED:
            return ["declared-bond-not-measured"]
        return ["declared-isolation-not-measured"]
    if declared["intent"] == INTENT_BONDED:
        return check_continuity(declared, measurement)
    return check_isolation(declared, measurement)


def check_measurement_coverage(declarations, measurements):
    """Findings for pairs the architecture and the measurements disagree on."""
    if not isinstance(declarations, list) or not declarations:
        raise ValueError("declarations must be a non-empty list")
    declared_keys = set()
    for declaration in declarations:
        norm = validate_declaration(declaration)
        if norm["key"] in declared_keys:
            raise ValueError("duplicate declaration for pair %s/%s" % norm["key"])
        declared_keys.add(norm["key"])
    indexed = index_measurements(measurements)
    findings = []
    for key in sorted(declared_keys - set(indexed)):
        findings.append("declared-pair-not-measured:%s/%s" % key)
    for key in sorted(set(indexed) - declared_keys):
        findings.append("measured-pair-absent-from-the-architecture:%s/%s" % key)
    return findings


def structure_reference_findings(declarations):
    """Findings on the single-point structure reference of each power domain."""
    if not isinstance(declarations, list) or not declarations:
        raise ValueError("declarations must be a non-empty list")
    grouped = {}
    for declaration in declarations:
        norm = validate_declaration(declaration)
        domain = norm["power_domain"]
        if domain is None:
            continue
        grouped.setdefault(domain, []).append(norm)
    findings = []
    for domain in sorted(grouped):
        references = [
            entry for entry in grouped[domain] if entry["intent"] == INTENT_BONDED
        ]
        if not references:
            findings.append("power-domain-without-a-structure-reference:%s" % domain)
        elif len(references) > 1:
            findings.append("power-domain-with-multiple-structure-references:%s" % domain)
    return findings


def assess_grounding_isolation(architecture):
    """Assess one grounding architecture against clause 5.3.9."""
    if not isinstance(architecture, dict):
        raise ValueError("architecture must be a mapping")
    declarations = architecture.get("declarations")
    measurements = architecture.get("measurements", [])
    findings = list(check_measurement_coverage(declarations, measurements))
    findings.extend(structure_reference_findings(declarations))
    indexed = index_measurements(measurements)
    pairs = []
    for declaration in declarations:
        declared = validate_declaration(declaration)
        measurement = indexed.get(declared["key"])
        pair_findings = []
        if measurement is not None:
            pair_findings = check_pair(declared, measurement)
        pairs.append(
            {
                "node_a": declared["node_a"],
                "node_b": declared["node_b"],
                "intent": declared["intent"],
                "bond_category": declared["bond_category"],
                "power_domain": declared["power_domain"],
                "resistance_ohm": (
                    measurement["resistance_ohm"] if measurement else None
                ),
                "method": measurement["method"] if measurement else None,
                "findings": pair_findings,
                "compliant": not pair_findings,
            }
        )
        for finding in pair_findings:
            findings.append(
                "%s:%s/%s" % (finding, declared["node_a"], declared["node_b"])
            )
    return {
        "pairs": pairs,
        "non_compliant_pairs": [
            "%s/%s" % (p["node_a"], p["node_b"]) for p in pairs if not p["compliant"]
        ],
        "findings": findings,
        "compliant": not findings,
    }
