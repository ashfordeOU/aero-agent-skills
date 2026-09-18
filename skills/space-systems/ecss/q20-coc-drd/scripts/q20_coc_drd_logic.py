"""Certificate of conformity document requirements description.

Anchor: ECSS-Q-ST-20C Annex D (normative), the document requirements
description for the certificate of conformity: the statement that the item
delivered is the item that was ordered, the references to the evidence
behind that statement, and the signature and authority that make it binding.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the certificate fields the DRD names, refusing a blank one.
2. Decide whether the conformity statement the certificate carries agrees
   with the deviations it enumerates.
3. Resolve every evidence reference against the evidence register supplied
   with the delivery, and report the coverage.
4. Check the signature block: a named signatory, a quality authority
   independent of the organisation that built the item, and a signature date
   that does not precede the evidence it certifies.
5. Return the coverage fraction, the findings and the certificate verdict.
"""

from datetime import date

__all__ = [
    "REQUIRED_FIELDS",
    "EVIDENCE_KINDS",
    "STATEMENTS",
    "INDEPENDENT_AUTHORITIES",
    "normalise_identifier",
    "parse_day",
    "normalise_register",
    "validate_certificate",
    "field_findings",
    "statement_findings",
    "evidence_findings",
    "evidence_coverage",
    "signature_findings",
    "assess_certificate",
]

# The identification and content the certificate carries.
REQUIRED_FIELDS = (
    "item_designation",
    "part_number",
    "serial_number",
    "quantity",
    "order_reference",
    "specification_reference",
    "specification_issue",
    "statement",
    "signatory",
    "signatory_function",
    "signature_date",
)

# The evidence a certificate points at; each must resolve in the register.
EVIDENCE_KINDS = (
    "as-built-configuration-list",
    "acceptance-test-report",
    "inspection-record",
    "material-certificate",
)

# The two statements the DRD admits, and what each one implies.
STATEMENTS = ("conforms-fully", "conforms-with-listed-deviations")

# Functions whose signature carries the independence the certificate needs.
INDEPENDENT_AUTHORITIES = ("quality-assurance", "product-assurance", "quality-manager")


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_day(value, label):
    """Return an ISO date; raise on anything that is not one."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def validate_certificate(certificate):
    """Return the normalised certificate; raise on a malformed submission."""
    if not isinstance(certificate, dict):
        raise ValueError("certificate must be a mapping")
    result = {}
    for field in REQUIRED_FIELDS:
        if field not in certificate:
            result[field] = None
            continue
        value = certificate[field]
        if field == "quantity":
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(
                    "certificate['quantity'] must be an integer of at least 1, got %r" % value
                )
            result[field] = value
        elif field == "signature_date":
            result[field] = parse_day(value, "certificate['signature_date']")
        elif field == "specification_issue":
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(
                    "certificate['specification_issue'] must be an integer of at least 1, got %r"
                    % value
                )
            result[field] = value
        else:
            result[field] = normalise_identifier(value, "certificate[%r]" % field)
    raw_dev = certificate.get("deviations", ())
    if not isinstance(raw_dev, (list, tuple)):
        raise ValueError("certificate['deviations'] must be a sequence")
    result["deviations"] = tuple(
        normalise_identifier(value, "certificate['deviations'] entry") for value in raw_dev
    )
    raw_ev = certificate.get("evidence", {})
    if not isinstance(raw_ev, dict):
        raise ValueError("certificate['evidence'] must be a mapping")
    evidence = {}
    for key, value in raw_ev.items():
        kind = normalise_identifier(key, "certificate['evidence'] key")
        evidence[kind] = normalise_identifier(value, "certificate['evidence'] value")
    result["evidence"] = evidence
    if result.get("statement") is not None and result["statement"] not in STATEMENTS:
        raise ValueError(
            "certificate['statement'] must be one of %s, got %r"
            % ("/".join(STATEMENTS), result["statement"])
        )
    return result


def field_findings(normalised):
    """Return findings for the DRD fields the certificate leaves blank."""
    if not isinstance(normalised, dict):
        raise ValueError("normalised must be the mapping returned by validate_certificate")
    absent = [field for field in REQUIRED_FIELDS if normalised.get(field) is None]
    if not absent:
        return []
    return ["the certificate states no %s" % ", ".join(absent)]


def statement_findings(normalised):
    """Return findings where the statement disagrees with the deviations."""
    statement = normalised.get("statement")
    deviations = normalised.get("deviations", ())
    if statement is None:
        return []
    findings = []
    if statement == "conforms-fully" and deviations:
        findings.append(
            "the certificate asserts full conformity while listing %d deviation(s): %s"
            % (len(deviations), ", ".join(deviations))
        )
    if statement == "conforms-with-listed-deviations" and not deviations:
        findings.append(
            "the certificate qualifies its conformity but enumerates no deviation"
        )
    return findings


def evidence_findings(normalised, register):
    """Return findings where a cited evidence reference does not resolve."""
    resolved = set(normalise_register(register))
    evidence = normalised.get("evidence", {})
    findings = []
    absent_kinds = [kind for kind in EVIDENCE_KINDS if kind not in evidence]
    if absent_kinds:
        findings.append(
            "the certificate points at no %s" % ", ".join(absent_kinds)
        )
    dangling = sorted(
        reference for reference in evidence.values() if reference not in resolved
    )
    if dangling:
        findings.append(
            "evidence cited by the certificate and absent from the register: %s"
            % ", ".join(dangling)
        )
    return findings


def evidence_coverage(normalised, register):
    """Return the fraction of the evidence kinds cited and resolvable."""
    resolved = set(normalise_register(register))
    evidence = normalised.get("evidence", {})
    covered = 0
    for kind in EVIDENCE_KINDS:
        reference = evidence.get(kind)
        if reference is not None and reference in resolved:
            covered += 1
    return covered / float(len(EVIDENCE_KINDS))


def normalise_register(register):
    """Return the evidence register keyed by normalised reference."""
    if not isinstance(register, dict):
        raise ValueError("register must be a mapping of reference to its issue date")
    return {
        normalise_identifier(key, "register key"): parse_day(value, "register[%r]" % key)
        for key, value in register.items()
    }


def signature_findings(normalised, register):
    """Return findings on the signatory, the authority and the date."""
    issued_on = normalise_register(register)
    findings = []
    function = normalised.get("signatory_function")
    if function is not None and function not in INDEPENDENT_AUTHORITIES:
        findings.append(
            "the certificate is signed by %s, which does not hold the independent "
            "quality authority the certificate needs" % function
        )
    signed = normalised.get("signature_date")
    if signed is None:
        return findings
    latest = None
    latest_reference = None
    evidence = normalised.get("evidence", {})
    for reference in sorted(evidence.values()):
        issued = issued_on.get(reference)
        if issued is None:
            continue
        if latest is None or issued > latest:
            latest = issued
            latest_reference = reference
    if latest is not None and signed < latest:
        findings.append(
            "the certificate is signed on %s, before %s was issued on %s"
            % (signed.isoformat(), latest_reference, latest.isoformat())
        )
    return findings


def assess_certificate(certificate, register):
    """Grade a certificate of conformity against the Annex D DRD."""
    normalised = validate_certificate(certificate)
    findings = []
    findings.extend(field_findings(normalised))
    findings.extend(statement_findings(normalised))
    findings.extend(evidence_findings(normalised, register))
    findings.extend(signature_findings(normalised, register))
    return {
        "serial_number": normalised.get("serial_number"),
        "statement": normalised.get("statement"),
        "deviation_count": len(normalised.get("deviations", ())),
        "evidence_coverage": evidence_coverage(normalised, register),
        "findings": findings,
        "verdict": "certificate-valid" if not findings else "certificate-invalid",
    }
