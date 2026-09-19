"""Mechanism electrical design: connectors, insulation resistance, dielectric strength.

Anchor: ECSS-E-ST-33-01C clauses 4.7.7.1 to 4.7.7.3 and 4.7.7.5 (the electrical
design of a mechanism's circuits). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the connector inventory of the mechanism and detect cross-mating
   hazards: two connectors on one unit that share shell size, insert
   arrangement and keying can be mated to the wrong harness during assembly.
2. Grade contact usage: current per contact against the contact rating after
   the bundle-fill derating that applies at the connector's declared
   occupancy, plus the spare-contact provision.
3. Grade separation of function: power, signal and pyrotechnic-class circuits
   do not share a connector.
4. Grade insulation resistance: the measured value at the declared test
   voltage against the required minimum.
5. Grade dielectric strength: the applied withstand voltage against the
   required test voltage derived from the circuit's operating voltage, and the
   measured leakage current against its limit.
"""

import math

__all__ = [
    "CIRCUIT_CLASSES",
    "RESISTANCE_TOLERANCE",
    "VOLTAGE_TOLERANCE",
    "CURRENT_TOLERANCE",
    "DEFAULT_DIELECTRIC_FACTOR",
    "DEFAULT_DIELECTRIC_OFFSET_V",
    "validate_connector",
    "bundle_derating_factor",
    "contact_current_margin",
    "contact_findings",
    "cross_mating_findings",
    "function_separation_findings",
    "insulation_findings",
    "required_dielectric_voltage",
    "dielectric_findings",
    "assess_electrical_design",
]

# Circuit families that are kept apart at connector level. A class outside
# this set is an input error: its separation rule is not defined here.
CIRCUIT_CLASSES = ("power", "signal", "pyrotechnic", "screen-return")

# Pairs that must never share one connector shell.
_FORBIDDEN_PAIRS = (
    ("power", "signal"),
    ("power", "pyrotechnic"),
    ("signal", "pyrotechnic"),
)

# Comparisons against a limit can land a few ULPs on the wrong side of an
# exact physical equality. Absorb the representation error here rather than
# relaxing the engineering limit.
RESISTANCE_TOLERANCE = 1e-6
VOLTAGE_TOLERANCE = 1e-9
CURRENT_TOLERANCE = 1e-12

# Withstand test voltage derived from the operating voltage of the circuit.
DEFAULT_DIELECTRIC_FACTOR = 2.0
DEFAULT_DIELECTRIC_OFFSET_V = 1000.0

# Minimum spare contacts kept on a flight connector for later growth and for
# a contact that fails continuity at integration.
MIN_SPARE_CONTACTS = 2


def _positive(label, value):
    """Return value as a positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def _count(label, value):
    """Return value as a non-negative integer count or raise ValueError."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count" % label)
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def validate_connector(connector):
    """Return a normalised connector record.

    Required keys: id, shell, insert, keying, total_contacts, circuits.
    Each circuit is a mapping with keys: id, circuit_class, current_a,
    contact_rating_a, operating_v.
    """
    if not isinstance(connector, dict):
        raise ValueError("connector must be a mapping")
    for key in ("id", "shell", "insert", "keying", "total_contacts", "circuits"):
        if key not in connector:
            raise ValueError("connector missing required key '%s'" % key)
    identifier = connector["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("connector id must be a non-empty string")
    for key in ("shell", "insert", "keying"):
        if not isinstance(connector[key], str) or not connector[key].strip():
            raise ValueError("connector %s must be a non-empty string" % key)
    total = _count("total_contacts", connector["total_contacts"])
    if total < 1:
        raise ValueError("total_contacts must be at least one")
    circuits = connector["circuits"]
    if not isinstance(circuits, (list, tuple)) or not circuits:
        raise ValueError("connector '%s' carries no circuits" % identifier)
    normalised = []
    for index, circuit in enumerate(circuits):
        if not isinstance(circuit, dict):
            raise ValueError("circuits[%d] must be a mapping" % index)
        for key in ("id", "circuit_class", "current_a", "contact_rating_a", "operating_v"):
            if key not in circuit:
                raise ValueError("circuits[%d] missing key '%s'" % (index, key))
        circuit_class = circuit["circuit_class"]
        if not isinstance(circuit_class, str):
            raise ValueError("circuits[%d] circuit_class must be a string" % index)
        circuit_class = circuit_class.strip().lower()
        if circuit_class not in CIRCUIT_CLASSES:
            raise ValueError(
                "circuit class %r is not one of %s"
                % (circuit["circuit_class"], ", ".join(CIRCUIT_CLASSES))
            )
        contacts_used = _count("contacts_used", circuit.get("contacts_used", 1))
        if contacts_used < 1:
            raise ValueError("circuits[%d] must occupy at least one contact" % index)
        normalised.append({
            "id": str(circuit["id"]),
            "circuit_class": circuit_class,
            "current_a": _non_negative("current_a", circuit["current_a"]),
            "contact_rating_a": _positive("contact_rating_a", circuit["contact_rating_a"]),
            "operating_v": _non_negative("operating_v", circuit["operating_v"]),
            "contacts_used": contacts_used,
        })
    used = sum(c["contacts_used"] for c in normalised)
    if used > total:
        raise ValueError(
            "connector '%s' allocates %d contacts out of %d" % (identifier, used, total)
        )
    return {
        "id": identifier.strip(),
        "shell": connector["shell"].strip().lower(),
        "insert": connector["insert"].strip().lower(),
        "keying": connector["keying"].strip().lower(),
        "total_contacts": total,
        "contacts_used": used,
        "circuits": normalised,
    }


def bundle_derating_factor(contacts_used, total_contacts):
    """Return the current derating factor a connector's occupancy imposes.

    An empty shell runs a contact at its full rating; a fully populated shell
    cannot shed the heat of every contact at rating, so the usable fraction
    falls linearly with occupancy down to a floor.
    """
    total = _count("total_contacts", total_contacts)
    used = _count("contacts_used", contacts_used)
    if total < 1:
        raise ValueError("total_contacts must be at least one")
    if used > total:
        raise ValueError("contacts_used %d exceeds total_contacts %d" % (used, total))
    occupancy = used / total
    return 1.0 - 0.5 * occupancy


def contact_current_margin(current_a, contact_rating_a, derating_factor):
    """Return the fractional margin of a derated contact rating over the load."""
    current = _non_negative("current_a", current_a)
    rating = _positive("contact_rating_a", contact_rating_a)
    factor = _positive("derating_factor", derating_factor)
    if factor > 1.0:
        raise ValueError("derating_factor must not exceed unity, got %r" % (derating_factor,))
    allowed = rating * factor
    if current == 0.0:
        return math.inf
    return allowed / current - 1.0


def contact_findings(connector, required_current_margin):
    """Return the per-circuit contact-current findings of one connector."""
    record = validate_connector(connector)
    required = _non_negative("required_current_margin", required_current_margin)
    factor = bundle_derating_factor(record["contacts_used"], record["total_contacts"])
    findings = []
    records = []
    for circuit in record["circuits"]:
        margin = contact_current_margin(
            circuit["current_a"], circuit["contact_rating_a"], factor
        )
        compliant = margin > required or math.isclose(
            margin, required, rel_tol=0.0, abs_tol=CURRENT_TOLERANCE
        )
        records.append({
            "connector": record["id"],
            "circuit": circuit["id"],
            "derating_factor": factor,
            "margin": margin,
            "compliant": compliant,
        })
        if not compliant:
            findings.append(
                "%s/%s: contact current margin %.4f is below the required %.4f "
                "after the %.3f occupancy derating"
                % (record["id"], circuit["id"], margin, required, factor)
            )
    spare = record["total_contacts"] - record["contacts_used"]
    if spare < MIN_SPARE_CONTACTS:
        findings.append(
            "%s: %d spare contact(s); at least %d are kept for growth and for a "
            "contact that fails continuity at integration"
            % (record["id"], spare, MIN_SPARE_CONTACTS)
        )
    return {"records": records, "spare_contacts": spare, "findings": findings}


def cross_mating_findings(connectors):
    """Return the findings for connector pairs that can be mated to each other."""
    if not isinstance(connectors, (list, tuple)) or not connectors:
        raise ValueError("connectors must be a non-empty sequence")
    records = [validate_connector(c) for c in connectors]
    seen = set()
    for record in records:
        if record["id"] in seen:
            raise ValueError("duplicate connector id '%s'" % record["id"])
        seen.add(record["id"])
    findings = []
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            a, b = records[i], records[j]
            if (a["shell"], a["insert"], a["keying"]) == (b["shell"], b["insert"], b["keying"]):
                findings.append(
                    "%s and %s share shell, insert arrangement and keying; either can be "
                    "mated to the other's harness" % (a["id"], b["id"])
                )
    return findings


def function_separation_findings(connectors):
    """Return the findings for connectors mixing circuit families in one shell."""
    if not isinstance(connectors, (list, tuple)) or not connectors:
        raise ValueError("connectors must be a non-empty sequence")
    findings = []
    for connector in connectors:
        record = validate_connector(connector)
        present = {c["circuit_class"] for c in record["circuits"]}
        for first, second in _FORBIDDEN_PAIRS:
            if first in present and second in present:
                findings.append(
                    "%s: %s and %s circuits share one connector shell"
                    % (record["id"], first, second)
                )
    return findings


def insulation_findings(measurements, required_ohm):
    """Return the insulation-resistance findings of a measurement set."""
    if not isinstance(measurements, (list, tuple)) or not measurements:
        raise ValueError("measurements must be a non-empty sequence")
    required = _positive("required_ohm", required_ohm)
    findings = []
    records = []
    for index, measurement in enumerate(measurements):
        if not isinstance(measurement, dict):
            raise ValueError("measurements[%d] must be a mapping" % index)
        for key in ("id", "measured_ohm", "test_voltage_v"):
            if key not in measurement:
                raise ValueError("measurements[%d] missing key '%s'" % (index, key))
        measured = _positive("measured_ohm", measurement["measured_ohm"])
        test_v = _positive("test_voltage_v", measurement["test_voltage_v"])
        required_test_v = _positive(
            "required_test_voltage_v", measurement.get("required_test_voltage_v", test_v)
        )
        ratio = measured / required
        compliant = ratio > 1.0 or math.isclose(ratio, 1.0, rel_tol=0.0, abs_tol=RESISTANCE_TOLERANCE)
        records.append({
            "id": str(measurement["id"]),
            "measured_ohm": measured,
            "required_ohm": required,
            "ratio": ratio,
            "test_voltage_v": test_v,
            "compliant": compliant,
        })
        if not compliant:
            findings.append(
                "%s: insulation resistance %.4g ohm is below the required %.4g ohm"
                % (measurement["id"], measured, required)
            )
        if test_v < required_test_v - VOLTAGE_TOLERANCE:
            findings.append(
                "%s: measured at %.1f V, below the %.1f V the requirement is written at; "
                "a lower stress reads a higher resistance"
                % (measurement["id"], test_v, required_test_v)
            )
    return {"records": records, "findings": findings}


def required_dielectric_voltage(operating_v, factor=DEFAULT_DIELECTRIC_FACTOR,
                                offset_v=DEFAULT_DIELECTRIC_OFFSET_V):
    """Return the withstand test voltage a circuit's operating voltage calls for."""
    operating = _non_negative("operating_v", operating_v)
    scale = _positive("factor", factor)
    offset = _non_negative("offset_v", offset_v)
    return scale * operating + offset


def dielectric_findings(tests, leakage_limit_a, factor=DEFAULT_DIELECTRIC_FACTOR,
                        offset_v=DEFAULT_DIELECTRIC_OFFSET_V):
    """Return the dielectric-strength findings of a withstand test set."""
    if not isinstance(tests, (list, tuple)) or not tests:
        raise ValueError("tests must be a non-empty sequence")
    limit = _positive("leakage_limit_a", leakage_limit_a)
    findings = []
    records = []
    for index, test in enumerate(tests):
        if not isinstance(test, dict):
            raise ValueError("tests[%d] must be a mapping" % index)
        for key in ("id", "operating_v", "applied_v", "leakage_a"):
            if key not in test:
                raise ValueError("tests[%d] missing key '%s'" % (index, key))
        operating = _non_negative("operating_v", test["operating_v"])
        applied = _positive("applied_v", test["applied_v"])
        leakage = _non_negative("leakage_a", test["leakage_a"])
        required_v = required_dielectric_voltage(operating, factor, offset_v)
        voltage_ok = applied > required_v or math.isclose(
            applied, required_v, rel_tol=0.0, abs_tol=VOLTAGE_TOLERANCE
        )
        leakage_ok = leakage < limit or math.isclose(
            leakage, limit, rel_tol=0.0, abs_tol=CURRENT_TOLERANCE
        )
        records.append({
            "id": str(test["id"]),
            "required_v": required_v,
            "applied_v": applied,
            "leakage_a": leakage,
            "voltage_ok": voltage_ok,
            "leakage_ok": leakage_ok,
            "compliant": voltage_ok and leakage_ok,
        })
        if not voltage_ok:
            findings.append(
                "%s: withstand applied at %.1f V, below the %.1f V the %.1f V circuit calls for"
                % (test["id"], applied, required_v, operating)
            )
        if not leakage_ok:
            findings.append(
                "%s: leakage %.4g A exceeds the %.4g A limit" % (test["id"], leakage, limit)
            )
    return {"records": records, "findings": findings}


def assess_electrical_design(spec):
    """Run the full clause 4.7.7.1-4.7.7.3 / 4.7.7.5 electrical assessment.

    spec keys: connectors, insulation_measurements, insulation_required_ohm,
    dielectric_tests, leakage_limit_a, required_current_margin. Optional:
    dielectric_factor, dielectric_offset_v.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("connectors", "insulation_measurements", "insulation_required_ohm",
                "dielectric_tests", "leakage_limit_a", "required_current_margin"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    connectors = spec["connectors"]
    findings = []
    connector_records = []
    for connector in connectors:
        contacts = contact_findings(connector, spec["required_current_margin"])
        connector_records.append({
            "id": validate_connector(connector)["id"],
            "contact_records": contacts["records"],
            "spare_contacts": contacts["spare_contacts"],
            "findings": contacts["findings"],
        })
        findings.extend(contacts["findings"])
    findings.extend(cross_mating_findings(connectors))
    findings.extend(function_separation_findings(connectors))
    insulation = insulation_findings(
        spec["insulation_measurements"], spec["insulation_required_ohm"]
    )
    findings.extend(insulation["findings"])
    dielectric = dielectric_findings(
        spec["dielectric_tests"],
        spec["leakage_limit_a"],
        spec.get("dielectric_factor", DEFAULT_DIELECTRIC_FACTOR),
        spec.get("dielectric_offset_v", DEFAULT_DIELECTRIC_OFFSET_V),
    )
    findings.extend(dielectric["findings"])
    return {
        "connectors": connector_records,
        "insulation": insulation["records"],
        "dielectric": dielectric["records"],
        "findings": findings,
        "compliant": not findings,
    }
