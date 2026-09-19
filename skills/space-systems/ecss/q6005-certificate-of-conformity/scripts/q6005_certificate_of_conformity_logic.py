"""The signed declaration that a delivered hybrid lot is what was ordered.

Anchor: ECSS-Q-ST-60-05 clause 13.2.3 (the certificate of conformity issued
with the shipment: a named, authorised person declaring that the units
delivered match the ordered specification and the approved build
configuration, with every departure from it referenced).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* A certificate is a signature on a comparison. The ordered configuration and
  the delivered configuration are compared attribute by attribute, and every
  attribute that differs has to be covered by an approved, referenced waiver
  or the declaration is untrue.
* A waiver covers one attribute, not the certificate. A waiver raised against
  the screening level does not excuse a different drawing issue, and a waiver
  that exists but was never approved covers nothing at all.
* Authority is a property of the signatory, not of the signature. A legible
  name in a role that cannot release product is an unsigned certificate with
  extra ink.
* The declared quantity has to equal the serials listed on the certificate,
  and the certificate cannot cover a unit that is not in the shipment.
* A certificate that declares conformity while an unwaived difference stands
  is refused outright, at any completeness index: the index measures what the
  form carries, not whether the statement on it is true.
* The certificate-completeness index is weighted credit over total weight. It
  ranks what is outstanding once the declaration itself holds.
"""

from __future__ import annotations

import math

# Fields the certificate carries, and the share of the declaration each
# supplies.
CERTIFICATE_FIELDS = {
    "supplier-identity": 1.0,
    "purchase-order-reference": 1.0,
    "part-number": 1.0,
    "specification-reference-and-issue": 1.0,
    "build-standard-reference-and-issue": 1.0,
    "lot-identifier": 1.0,
    "quantity-declared": 1.0,
    "serial-numbers-covered": 1.0,
    "statement-of-conformity": 1.0,
    "deviation-and-waiver-references": 0.9,
    "signatory-name": 0.9,
    "signatory-role": 0.9,
    "date-of-issue": 0.7,
}

# Without these there is no declaration to assess.
MANDATORY_CERTIFICATE_FIELDS = (
    "part-number",
    "specification-reference-and-issue",
    "build-standard-reference-and-issue",
    "lot-identifier",
    "quantity-declared",
    "serial-numbers-covered",
    "statement-of-conformity",
    "signatory-name",
    "signatory-role",
)

FIELD_STATE_CREDIT = {
    "present": 1.0,
    "present-with-observation": 0.7,
    "illegible": 0.2,
    "absent": 0.0,
}

# Roles that may release product on behalf of the manufacturer.
AUTHORISED_SIGNATORY_ROLES = (
    "product-assurance-manager",
    "quality-manager",
    "authorised-quality-representative",
    "delegated-release-officer",
)

# Roles that appear on certificates and cannot release product.
UNAUTHORISED_SIGNATORY_ROLES = (
    "assembly-operator",
    "test-technician",
    "design-engineer",
    "sales-administrator",
    "shipping-clerk",
)

# Configuration attributes compared between what was ordered and what arrived.
CONFIGURATION_ATTRIBUTES = (
    "part_number",
    "specification_issue",
    "build_standard_issue",
    "screening_level",
    "lead_finish",
)

# Certificate-completeness index an acceptable certificate has to reach.
ACCEPTANCE_CERTIFICATE_INDEX = 0.90

# Indices are sums of products; a case meant to sit exactly on a bound can
# land a few units in the last place away from it.
CERTIFICATE_TOLERANCE = 1e-9

VERDICTS = (
    "certificate-accepted",
    "certificate-accepted-with-open-actions",
    "certificate-refused",
    "certificate-assessment-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _count(value, label):
    """Return ``value`` as a non-negative whole count or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def _serials(values, label):
    """Validate a list of unit serials."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (label, type(values).__name__))
    cleaned = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("every %s entry must be a non-empty string, got %r" % (label, value))
        cleaned.append(value.strip())
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("%s contains a repeated serial" % label)
    return cleaned


def signatory_is_authorised(role):
    """True when the role named on the certificate may release product."""
    if not isinstance(role, str) or not role.strip():
        raise ValueError("signatory role must be a non-empty string, got %r" % (role,))
    cleaned = role.strip()
    if cleaned in AUTHORISED_SIGNATORY_ROLES:
        return True
    if cleaned in UNAUTHORISED_SIGNATORY_ROLES:
        return False
    raise ValueError(
        "unknown signatory role %r (known: %s)"
        % (cleaned, ", ".join(sorted(AUTHORISED_SIGNATORY_ROLES + UNAUTHORISED_SIGNATORY_ROLES)))
    )


def signatory_findings(signatory):
    """Findings raised by who put their name on the certificate."""
    if not isinstance(signatory, dict):
        raise ValueError("signatory must be a mapping, got %r" % (type(signatory).__name__,))
    findings = []
    name = signatory.get("name")
    if not isinstance(name, str) or not name.strip():
        findings.append("certificate-signed-by-nobody-named")
    if not signatory_is_authorised(signatory.get("role")):
        findings.append("signatory-role-cannot-release-product")
    if not _flag(signatory, "signature_applied"):
        findings.append("certificate-not-signed")
    return findings


def normalize_configuration(configuration, label):
    """Validate one configuration statement across the compared attributes."""
    if not isinstance(configuration, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, type(configuration).__name__))
    record = {}
    for attribute in CONFIGURATION_ATTRIBUTES:
        value = configuration.get(attribute)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s must state %s as a non-empty string" % (label, attribute))
        record[attribute] = value.strip()
    return record


def configuration_differences(ordered, delivered):
    """Attributes on which the delivered units depart from what was ordered."""
    left = normalize_configuration(ordered, "ordered configuration")
    right = normalize_configuration(delivered, "delivered configuration")
    return [
        attribute for attribute in CONFIGURATION_ATTRIBUTES if left[attribute] != right[attribute]
    ]


def normalize_waiver(raw):
    """Validate one deviation or waiver record referenced by the certificate."""
    if not isinstance(raw, dict):
        raise ValueError("waiver must be a mapping, got %r" % (type(raw).__name__,))
    reference = raw.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("a waiver must carry a non-empty reference, got %r" % (reference,))
    attribute = raw.get("covers")
    if attribute not in CONFIGURATION_ATTRIBUTES:
        raise ValueError(
            "a waiver must cover one compared attribute (known: %s), got %r"
            % (", ".join(CONFIGURATION_ATTRIBUTES), attribute)
        )
    return {
        "reference": reference.strip(),
        "covers": attribute,
        "approved": _flag(raw, "approved"),
        "referenced_on_certificate": _flag(raw, "referenced_on_certificate"),
    }


def waiver_coverage(differences, waivers):
    """Match each configuration difference to an approved, referenced waiver."""
    if not isinstance(waivers, (list, tuple)):
        raise ValueError("waivers must be a list or tuple, got %r" % (type(waivers).__name__,))
    records = []
    seen = set()
    for raw in waivers:
        record = normalize_waiver(raw)
        if record["reference"] in seen:
            raise ValueError("duplicate waiver reference %r" % (record["reference"],))
        seen.add(record["reference"])
        records.append(record)

    usable = {}
    for record in records:
        if record["approved"] and record["referenced_on_certificate"]:
            usable[record["covers"]] = record["reference"]

    uncovered = [attribute for attribute in differences if attribute not in usable]
    unapproved = [record["reference"] for record in records if not record["approved"]]
    unreferenced = [
        record["reference"]
        for record in records
        if record["approved"] and not record["referenced_on_certificate"]
    ]
    spare = [
        record["reference"]
        for record in records
        if record["covers"] not in differences
    ]
    findings = []
    if uncovered:
        findings.append("configuration-difference-with-no-approved-waiver")
    if unapproved:
        findings.append("waiver-referenced-but-not-approved")
    if unreferenced:
        findings.append("approved-waiver-not-referenced-on-the-certificate")
    if spare:
        findings.append("waiver-raised-against-an-attribute-that-matches")
    return {
        "waivers": records,
        "covered_attributes": sorted(usable),
        "uncovered_differences": uncovered,
        "unapproved_waivers": unapproved,
        "unreferenced_waivers": unreferenced,
        "waivers_without_a_difference": spare,
        "all_differences_covered": len(uncovered) == 0,
        "findings": findings,
    }


def quantity_declaration(declared_quantity, certificate_serials, delivered_serials):
    """Check the quantity and serials the certificate covers against the shipment."""
    declared = _count(declared_quantity, "declared_quantity")
    if declared == 0:
        raise ValueError("a certificate must declare a quantity")
    covered = _serials(certificate_serials, "certificate serials")
    delivered = _serials(delivered_serials, "delivered serials")
    if len(delivered) == 0:
        raise ValueError("a shipment must carry at least one unit serial")
    not_covered = [serial for serial in delivered if serial not in set(covered)]
    not_delivered = [serial for serial in covered if serial not in set(delivered)]
    findings = []
    if declared != len(covered):
        findings.append("declared-quantity-differs-from-the-serials-on-the-certificate")
    if not_covered:
        findings.append("delivered-unit-not-covered-by-the-certificate")
    if not_delivered:
        findings.append("certificate-covers-a-unit-that-was-not-delivered")
    return {
        "declared_quantity": declared,
        "certificate_serial_count": len(covered),
        "delivered_serial_count": len(delivered),
        "units_not_covered": not_covered,
        "units_covered_but_not_delivered": not_delivered,
        "reconciled": len(findings) == 0,
        "findings": findings,
    }


def certificate_field_weight(name):
    """Weight of one certificate field; unknown names are rejected."""
    if name not in CERTIFICATE_FIELDS:
        raise ValueError(
            "unknown certificate field %r (known: %s)"
            % (name, ", ".join(sorted(CERTIFICATE_FIELDS)))
        )
    return CERTIFICATE_FIELDS[name]


def field_state_credit(state):
    """Credit a certificate field state earns."""
    if state not in FIELD_STATE_CREDIT:
        raise ValueError(
            "unknown field state %r (known: %s)" % (state, ", ".join(sorted(FIELD_STATE_CREDIT)))
        )
    return FIELD_STATE_CREDIT[state]


def normalize_field(raw):
    """Validate one certificate field record and fill its default state."""
    if not isinstance(raw, dict):
        raise ValueError("field must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("field")
    certificate_field_weight(name)  # validation only
    state = raw.get("state", "absent")
    field_state_credit(state)  # validation only
    return {"field": name, "state": state}


def assess_field(raw):
    """Grade one certificate field into a credit and its findings."""
    record = normalize_field(raw)
    name = record["field"]
    state = record["state"]
    weight = certificate_field_weight(name)
    credit = field_state_credit(state)
    findings = []
    if state == "present-with-observation":
        findings.append("certificate-field-observation-open")
    elif state == "illegible":
        findings.append("certificate-field-illegible")
    elif state == "absent":
        findings.append("certificate-field-absent")
    mandatory = name in MANDATORY_CERTIFICATE_FIELDS
    return {
        "field": name,
        "state": state,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory": mandatory,
        "mandatory_missing": mandatory and state == "absent",
        "mandatory_illegible": mandatory and state == "illegible",
        "findings": findings,
    }


def certificate_completeness_index(records):
    """Weighted credit of a set of graded fields over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a certificate must carry at least one field")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total certificate field weight must be positive")
    return earned / total_weight


def assess_certificate_of_conformity(
    lot_id, ordered, delivered, waivers, signatory, declaration, delivered_serials, fields
):
    """Grade a whole certificate of conformity and name one verdict."""
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("lot_id must be a non-empty string, got %r" % (lot_id,))
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping, got %r" % (type(declaration).__name__,))
    if not isinstance(fields, (list, tuple)):
        raise ValueError("fields must be a list or tuple, got %r" % (type(fields).__name__,))

    differences = configuration_differences(ordered, delivered)
    coverage = waiver_coverage(differences, waivers)
    signature = signatory_findings(signatory)
    quantity = quantity_declaration(
        declaration.get("declared_quantity"),
        declaration.get("certificate_serials"),
        delivered_serials,
    )

    declared = {}
    for raw in fields:
        record = normalize_field(raw)
        if record["field"] in declared:
            raise ValueError("duplicate certificate field %r" % (record["field"],))
        declared[record["field"]] = record
    graded = []
    for name in sorted(CERTIFICATE_FIELDS):
        graded.append(assess_field(declared.get(name, {"field": name})))
    index = certificate_completeness_index(graded)

    findings = []
    for attribute in coverage["uncovered_differences"]:
        findings.append(
            {
                "item": attribute,
                "finding": "configuration-difference-with-no-approved-waiver",
                "detail": lot_id,
            }
        )
    for finding in coverage["findings"]:
        if finding == "configuration-difference-with-no-approved-waiver":
            continue
        findings.append({"item": "waivers", "finding": finding, "detail": lot_id})
    for finding in signature:
        findings.append({"item": "signatory", "finding": finding, "detail": lot_id})
    for finding in quantity["findings"]:
        findings.append({"item": "quantity-declared", "finding": finding, "detail": lot_id})
    for record in graded:
        for finding in record["findings"]:
            findings.append(
                {"item": record["field"], "finding": finding, "detail": record["state"]}
            )

    incomplete = any(record["mandatory_missing"] for record in graded)
    refused = (
        not coverage["all_differences_covered"]
        or bool(coverage["unapproved_waivers"])
        or bool(signature)
        or not quantity["reconciled"]
        or any(record["mandatory_illegible"] for record in graded)
        or index < ACCEPTANCE_CERTIFICATE_INDEX - CERTIFICATE_TOLERANCE
    )
    if incomplete:
        verdict = "certificate-assessment-incomplete"
    elif refused:
        verdict = "certificate-refused"
    elif findings:
        verdict = "certificate-accepted-with-open-actions"
    else:
        verdict = "certificate-accepted"
    return {
        "lot_id": lot_id,
        "configuration_differences": differences,
        "waiver_coverage": coverage,
        "signatory_findings": signature,
        "quantity": quantity,
        "fields": graded,
        "certificate_completeness_index": index,
        "findings": findings,
        "verdict": verdict,
        "certificate_accepted": verdict
        in ("certificate-accepted", "certificate-accepted-with-open-actions"),
    }
