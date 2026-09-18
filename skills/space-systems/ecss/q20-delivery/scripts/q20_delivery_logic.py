"""Delivery control, transport monitoring and certificate-of-conformity logic.

Anchor: ECSS-Q-ST-20C clause 5.7.5 (5.7.5.1-5.7.5.2) -- controlling the
delivery itself: the shipping control documentation that travels with the
consignment, transportation carried out against the transport standard of the
Q-ST-20 series, and the conditions under which the certificate of conformity
may be issued. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the consignment and derive the shipping document set it owes from
   its own states: cross-border movement, hazardous contents, a temperature or
   shock limit, an oversize lift.
2. Reconcile the documents actually travelling with the consignment against
   that set and name each gap.
3. Read the transport monitoring record: count the excursions outside each
   declared environmental limit, keep the worst one per parameter, and treat an
   unmonitored stretch of the journey as unknown rather than as compliant.
4. Reconcile the identification on the certificate with the identification on
   the consignment: part number, serial and quantity have to be the same item.
5. Decide whether the certificate of conformity may be issued, and return every
   finding that stands in its way.
"""

import math

__all__ = [
    "BASE_SHIPPING_DOCUMENTS",
    "LIMIT_TOLERANCE",
    "COVERAGE_TOLERANCE",
    "AUTHORISED_SIGNATORY_FUNCTIONS",
    "normalize_token",
    "validate_consignment",
    "required_shipping_documents",
    "document_findings",
    "validate_limits",
    "excursion_report",
    "monitoring_coverage",
    "monitoring_findings",
    "identification_findings",
    "certificate_findings",
    "assess_delivery_control",
]

# Documents every consignment carries whatever is inside it.
BASE_SHIPPING_DOCUMENTS = (
    "packing-list",
    "shipping-control-document",
    "delivery-note",
    "transport-handling-instructions",
)

# Only these functions may put their signature on a certificate of conformity.
AUTHORISED_SIGNATORY_FUNCTIONS = ("quality-assurance", "quality-manager")

# Limit comparisons are made against measured values; a reading that lands on
# the limit is inside it, and the representation error is absorbed here.
LIMIT_TOLERANCE = 1e-9

# Coverage is a ratio of two durations and can land a few ULPs short of unity.
COVERAGE_TOLERANCE = 1e-9


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for a name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v) or v <= 0.0:
        raise ValueError("%s must be positive and finite, got %r" % (label, value))
    return v


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_consignment(consignment):
    """Return the validated consignment record."""
    if not isinstance(consignment, dict):
        raise ValueError("consignment must be a mapping")
    for key in ("part_number", "serial_number", "quantity"):
        if key not in consignment:
            raise ValueError("consignment is missing '%s'" % key)
    quantity = consignment["quantity"]
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise ValueError("consignment quantity must be a positive integer, got %r" % (quantity,))
    return {
        "part_number": normalize_token(consignment["part_number"], "part_number"),
        "serial_number": normalize_token(consignment["serial_number"], "serial_number"),
        "quantity": quantity,
        "cross_border": _flag(consignment.get("cross_border", False), "cross_border"),
        "hazardous": _flag(consignment.get("hazardous", False), "hazardous"),
        "temperature_controlled": _flag(
            consignment.get("temperature_controlled", False), "temperature_controlled"
        ),
        "shock_limited": _flag(consignment.get("shock_limited", False), "shock_limited"),
        "oversize_lift": _flag(consignment.get("oversize_lift", False), "oversize_lift"),
    }


def required_shipping_documents(consignment):
    """Return the shipping documents this consignment's states make mandatory."""
    record = validate_consignment(consignment)
    documents = list(BASE_SHIPPING_DOCUMENTS)
    if record["cross_border"]:
        documents.extend(["customs-declaration", "export-authorisation"])
    if record["hazardous"]:
        documents.append("dangerous-goods-declaration")
    if record["temperature_controlled"] or record["shock_limited"]:
        documents.append("transport-monitoring-record")
    if record["oversize_lift"]:
        documents.append("lifting-and-rigging-plan")
    return documents


def document_findings(carried_documents, required_documents):
    """Return the mandatory shipping documents not travelling with the consignment."""
    if not isinstance(carried_documents, (list, tuple)):
        raise ValueError("carried_documents must be a sequence of document names")
    if not isinstance(required_documents, (list, tuple)):
        raise ValueError("required_documents must be a sequence of document names")
    have = {normalize_token(d, "carried document") for d in carried_documents}
    findings = []
    for document in required_documents:
        token = normalize_token(document, "required document")
        if token not in have:
            findings.append("consignment does not carry %s" % token)
    return findings


def validate_limits(limits):
    """Return the validated transport environmental limits as normalized bounds."""
    if not isinstance(limits, dict) or not limits:
        raise ValueError("limits must be a non-empty mapping of parameter to bounds")
    validated = {}
    for name, bounds in limits.items():
        token = normalize_token(name, "limit parameter")
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("limits[%r] must be a (minimum, maximum) pair" % name)
        low, high = bounds
        low = None if low is None else _real(low, "limits[%r] minimum" % name)
        high = None if high is None else _real(high, "limits[%r] maximum" % name)
        if low is None and high is None:
            raise ValueError("limits[%r] must bound at least one side" % name)
        if low is not None and high is not None and low > high:
            raise ValueError("limits[%r] minimum %g exceeds maximum %g" % (name, low, high))
        validated[token] = (low, high)
    return validated


def excursion_report(readings, limits):
    """Return, per parameter, the excursion count and the worst reading seen."""
    bounds = validate_limits(limits)
    if not isinstance(readings, (list, tuple)):
        raise ValueError("readings must be a sequence of reading records")
    report = {name: {"excursions": 0, "worst_value": None, "side": None} for name in bounds}
    for i, reading in enumerate(readings):
        if not isinstance(reading, dict):
            raise ValueError("readings[%d] must be a mapping" % i)
        for key in ("parameter", "value"):
            if key not in reading:
                raise ValueError("readings[%d] is missing '%s'" % (i, key))
        token = normalize_token(reading["parameter"], "readings[%d]['parameter']" % i)
        if token not in bounds:
            raise ValueError("readings[%d] names %r, which has no declared limit" % (i, token))
        value = _real(reading["value"], "readings[%d]['value']" % i)
        low, high = bounds[token]
        entry = report[token]
        if low is not None and value < low and not math.isclose(
            value, low, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
        ):
            entry["excursions"] += 1
            if entry["worst_value"] is None or value < entry["worst_value"]:
                entry["worst_value"] = value
                entry["side"] = "below"
        elif high is not None and value > high and not math.isclose(
            value, high, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
        ):
            entry["excursions"] += 1
            if entry["worst_value"] is None or value > entry["worst_value"]:
                entry["worst_value"] = value
                entry["side"] = "above"
    return report


def monitoring_coverage(recorded_hours, transit_hours):
    """Return the fraction of the journey the transport monitor actually recorded."""
    recorded = _real(recorded_hours, "recorded_hours")
    transit = _positive(transit_hours, "transit_hours")
    if recorded < 0.0:
        raise ValueError("recorded_hours must not be negative, got %r" % (recorded_hours,))
    if recorded > transit and not math.isclose(
        recorded, transit, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    ):
        raise ValueError(
            "recorded_hours %g exceeds the transit duration %g" % (recorded, transit)
        )
    return recorded / transit


def monitoring_findings(readings, limits, recorded_hours, transit_hours):
    """Return the findings from the transport monitoring record."""
    report = excursion_report(readings, limits)
    coverage = monitoring_coverage(recorded_hours, transit_hours)
    findings = []
    for name in sorted(report):
        entry = report[name]
        if entry["excursions"]:
            findings.append(
                "%s left its transport limit %d time(s), worst reading %g %s the bound"
                % (name, entry["excursions"], entry["worst_value"], entry["side"])
            )
    if coverage < 1.0 and not math.isclose(
        coverage, 1.0, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    ):
        findings.append(
            "transport monitor covered %.1f%% of the journey; the remainder is unknown, "
            "not compliant" % (coverage * 100.0)
        )
    return {"report": report, "coverage": coverage, "findings": findings}


def identification_findings(consignment, certificate):
    """Return the mismatches between the certificate and the consignment it covers."""
    record = validate_consignment(consignment)
    if not isinstance(certificate, dict):
        raise ValueError("certificate must be a mapping")
    for key in ("part_number", "serial_number", "quantity"):
        if key not in certificate:
            raise ValueError("certificate is missing '%s'" % key)
    findings = []
    for key in ("part_number", "serial_number"):
        stated = normalize_token(certificate[key], "certificate[%r]" % key)
        if stated != record[key]:
            findings.append(
                "certificate %s %s does not match the consignment %s"
                % (key.replace("_", "-"), stated, record[key])
            )
    quantity = certificate["quantity"]
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise ValueError("certificate quantity must be a positive integer, got %r" % (quantity,))
    if quantity != record["quantity"]:
        findings.append(
            "certificate quantity %d does not match the consignment quantity %d"
            % (quantity, record["quantity"])
        )
    return findings


def certificate_findings(certificate, board_decision):
    """Return the findings about the certificate's own authority to be issued."""
    if not isinstance(certificate, dict):
        raise ValueError("certificate must be a mapping")
    decision = normalize_token(board_decision, "board_decision")
    if decision not in ("deliver", "deliver-with-reservation", "hold"):
        raise ValueError("board_decision %r is not a delivery review outcome" % decision)
    findings = []
    if decision == "hold":
        findings.append("delivery review board held the delivery; no certificate may be issued")
    signatory = certificate.get("signatory_function")
    if signatory is None:
        findings.append("certificate has no signatory function")
    else:
        token = normalize_token(signatory, "certificate['signatory_function']")
        if token not in AUTHORISED_SIGNATORY_FUNCTIONS:
            findings.append("%s is not authorised to sign a certificate of conformity" % token)
    if not _flag(certificate.get("reservations_listed", False), "certificate['reservations_listed']"):
        if decision == "deliver-with-reservation":
            findings.append(
                "delivery carries reservations that the certificate does not list"
            )
    return findings


def assess_delivery_control(spec):
    """Run the full clause 5.7.5 delivery control assessment.

    spec keys: consignment, carried_documents, transport (limits, readings,
    recorded_hours, transit_hours), certificate, board_decision.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("consignment", "carried_documents", "transport", "certificate", "board_decision"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    transport = spec["transport"]
    if not isinstance(transport, dict):
        raise ValueError("spec['transport'] must be a mapping")
    for key in ("limits", "readings", "recorded_hours", "transit_hours"):
        if key not in transport:
            raise ValueError("spec['transport'] is missing '%s'" % key)
    consignment = validate_consignment(spec["consignment"])
    required = required_shipping_documents(spec["consignment"])
    documents = document_findings(spec["carried_documents"], required)
    monitoring = monitoring_findings(
        transport["readings"],
        transport["limits"],
        transport["recorded_hours"],
        transport["transit_hours"],
    )
    identification = identification_findings(spec["consignment"], spec["certificate"])
    authority = certificate_findings(spec["certificate"], spec["board_decision"])
    findings = list(documents) + list(monitoring["findings"]) + list(identification) + list(authority)
    return {
        "consignment": consignment,
        "required_documents": required,
        "document_findings": documents,
        "monitoring": monitoring,
        "identification_findings": identification,
        "certificate_findings": authority,
        "findings": findings,
        "certificate_issuable": not findings,
    }
