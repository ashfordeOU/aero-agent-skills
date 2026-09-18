"""Acceptance and delivery of a product.

Anchor: ECSS-Q-ST-20C clause 5.7.1 (running the acceptance and delivery
process: the acceptance criteria, the mandatory acceptance hold points, and
the verification that the product complies with its requirements before it is
accepted). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Normalise the verification register: every requirement with the method it
   was verified by, the state that verification reached, and the evidence the
   state rests on.
2. Grade each requirement: a verified state needs evidence; a partial or
   absent verification needs an approved deviation or waiver before it can be
   carried into acceptance at all.
3. Grade the open nonconformances by severity: a critical one blocks whatever
   paperwork accompanies it; lesser ones need an approved disposition.
4. Grade the mandatory acceptance hold points: signed, and signed by the party
   that owns them.
5. Compute the compliance fraction and decide: accepted, conditionally
   accepted against named approved concessions, or rejected with the blocking
   items named.
"""

__all__ = [
    "VERIFICATION_METHODS",
    "VERIFICATION_STATES",
    "NONCONFORMANCE_SEVERITIES",
    "DEFAULT_HOLD_POINTS",
    "normalise_identifier",
    "validate_register",
    "validate_concessions",
    "requirement_findings",
    "compliance_fraction",
    "nonconformance_findings",
    "hold_point_findings",
    "assess_acceptance",
]

# How a requirement can have been shown to be met.
VERIFICATION_METHODS = ("test", "analysis", "inspection", "review-of-design")

# How far that verification actually got.
VERIFICATION_STATES = ("verified", "partially-verified", "not-verified")

# Severity drives whether a concession can carry an open nonconformance past
# acceptance at all.
NONCONFORMANCE_SEVERITIES = ("minor", "major", "critical")

# The gates a delivery passes through before the product changes hands.
DEFAULT_HOLD_POINTS = (
    ("physical-configuration-audit", "product-assurance"),
    ("pre-delivery-review", "product-assurance"),
    ("customer-acceptance-review", "customer"),
)


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def validate_register(register):
    """Return the normalised requirement verification register."""
    if not isinstance(register, (list, tuple)) or not register:
        raise ValueError("verification register must be a non-empty sequence")
    entries = {}
    for index, item in enumerate(register):
        if not isinstance(item, dict):
            raise ValueError("register[%d] must be a mapping" % index)
        req = normalise_identifier(item.get("requirement"), "register[%d].requirement" % index)
        if req in entries:
            raise ValueError("duplicate requirement %r in the register" % req)
        method = normalise_identifier(item.get("method"), "register[%d].method" % index)
        if method not in VERIFICATION_METHODS:
            raise ValueError(
                "register[%d].method must be one of %s, got %r"
                % (index, "/".join(VERIFICATION_METHODS), method)
            )
        state = normalise_identifier(item.get("state"), "register[%d].state" % index)
        if state not in VERIFICATION_STATES:
            raise ValueError(
                "register[%d].state must be one of %s, got %r"
                % (index, "/".join(VERIFICATION_STATES), state)
            )
        evidence = item.get("evidence")
        concession = item.get("concession")
        entries[req] = {
            "requirement": req,
            "method": method,
            "state": state,
            "evidence": (
                None if evidence is None
                else normalise_identifier(evidence, "register[%d].evidence" % index)
            ),
            "concession": (
                None if concession is None
                else normalise_identifier(concession, "register[%d].concession" % index)
            ),
        }
    return entries


def validate_concessions(concessions):
    """Return the normalised deviations and waivers raised against the product."""
    if concessions is None:
        concessions = []
    if not isinstance(concessions, (list, tuple)):
        raise ValueError("concessions must be a sequence")
    entries = {}
    for index, item in enumerate(concessions):
        if not isinstance(item, dict):
            raise ValueError("concessions[%d] must be a mapping" % index)
        ref = normalise_identifier(item.get("reference"), "concessions[%d].reference" % index)
        if ref in entries:
            raise ValueError("duplicate concession reference %r" % ref)
        approver = item.get("approved_by")
        entries[ref] = {
            "reference": ref,
            "approved": bool(item.get("approved", False)),
            "approved_by": (
                None if approver is None
                else normalise_identifier(approver, "concessions[%d].approved_by" % index)
            ),
        }
    return entries


def requirement_findings(entries, concessions):
    """Return the per-requirement findings and the carried concessions."""
    findings = []
    carried = []
    for req in sorted(entries):
        entry = entries[req]
        if entry["state"] == "verified":
            if entry["evidence"] is None:
                findings.append("requirement %s is called verified with no evidence" % req)
            continue
        if entry["concession"] is None:
            findings.append(
                "requirement %s is %s with no deviation or waiver raised" % (req, entry["state"])
            )
            continue
        concession = concessions.get(entry["concession"])
        if concession is None:
            findings.append(
                "requirement %s cites concession %s, which is not in the register"
                % (req, entry["concession"])
            )
            continue
        if not concession["approved"]:
            findings.append(
                "requirement %s rests on unapproved concession %s" % (req, entry["concession"])
            )
            continue
        if concession["approved_by"] is None:
            findings.append(
                "concession %s is marked approved with no approver named" % entry["concession"]
            )
            continue
        carried.append(entry["concession"])
    return {"findings": findings, "carried_concessions": sorted(set(carried))}


def compliance_fraction(entries):
    """Return the fraction of registered requirements reaching full verification."""
    verified = sum(1 for entry in entries.values() if entry["state"] == "verified")
    return verified / float(len(entries))


def nonconformance_findings(nonconformances):
    """Return the findings of the nonconformances still open at acceptance."""
    if nonconformances is None:
        nonconformances = []
    if not isinstance(nonconformances, (list, tuple)):
        raise ValueError("nonconformances must be a sequence")
    findings = []
    seen = set()
    for index, item in enumerate(nonconformances):
        if not isinstance(item, dict):
            raise ValueError("nonconformances[%d] must be a mapping" % index)
        ncr = normalise_identifier(item.get("id"), "nonconformances[%d].id" % index)
        if ncr in seen:
            raise ValueError("duplicate nonconformance id %r" % ncr)
        seen.add(ncr)
        severity = normalise_identifier(
            item.get("severity"), "nonconformances[%d].severity" % index
        )
        if severity not in NONCONFORMANCE_SEVERITIES:
            raise ValueError(
                "nonconformances[%d].severity must be one of %s, got %r"
                % (index, "/".join(NONCONFORMANCE_SEVERITIES), severity)
            )
        if bool(item.get("closed", False)):
            continue
        if severity == "critical":
            findings.append("critical nonconformance %s is open at acceptance" % ncr)
            continue
        disposition = item.get("disposition")
        if disposition is None:
            findings.append("open %s nonconformance %s has no disposition" % (severity, ncr))
            continue
        normalise_identifier(disposition, "nonconformances[%d].disposition" % index)
        if not bool(item.get("disposition_approved", False)):
            findings.append(
                "disposition of %s nonconformance %s is not approved" % (severity, ncr)
            )
    return findings


def hold_point_findings(signatures, hold_points=DEFAULT_HOLD_POINTS):
    """Return the findings of the mandatory acceptance hold points."""
    if signatures is None:
        signatures = []
    if not isinstance(signatures, (list, tuple)):
        raise ValueError("signatures must be a sequence")
    signed = {}
    for index, item in enumerate(signatures):
        if not isinstance(item, dict):
            raise ValueError("signatures[%d] must be a mapping" % index)
        gate = normalise_identifier(item.get("hold_point"), "signatures[%d].hold_point" % index)
        if gate in signed:
            raise ValueError("duplicate signature for hold point %r" % gate)
        signed[gate] = normalise_identifier(item.get("signed_by"), "signatures[%d].signed_by" % index)
    findings = []
    for gate, owner in hold_points:
        if gate not in signed:
            findings.append("acceptance hold point %s is not signed" % gate)
        elif signed[gate] != owner:
            findings.append(
                "acceptance hold point %s was signed by %s, not by the %s that owns it"
                % (gate, signed[gate], owner)
            )
    return findings


def assess_acceptance(package, hold_points=DEFAULT_HOLD_POINTS):
    """Run the whole clause 5.7.1 acceptance assessment for one delivery."""
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    entries = validate_register(package.get("register"))
    concessions = validate_concessions(package.get("concessions"))
    requirements = requirement_findings(entries, concessions)
    blocking = []
    blocking.extend(requirements["findings"])
    blocking.extend(nonconformance_findings(package.get("nonconformances")))
    blocking.extend(hold_point_findings(package.get("signatures"), hold_points))
    fraction = compliance_fraction(entries)
    if blocking:
        verdict = "rejected"
    elif requirements["carried_concessions"]:
        verdict = "conditionally-accepted"
    else:
        verdict = "accepted"
    return {
        "requirement_count": len(entries),
        "compliance_fraction": fraction,
        "carried_concessions": requirements["carried_concessions"],
        "findings": blocking,
        "verdict": verdict,
    }
