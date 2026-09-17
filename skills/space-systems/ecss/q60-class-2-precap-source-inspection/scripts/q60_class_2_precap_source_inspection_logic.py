"""Pre-cap source inspection coverage for Class 2 production lots.

Anchor: ECSS-Q-ST-60C clause 5.3.4 — the inspection witnessed at the
manufacturer's premises before the package is sealed, applied across the
Class 2 production lots of an order. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide applicability from the package. A pre-cap witness point only exists
   where there is a cavity to look into; a moulded or encapsulated lot has no
   seal operation, so the record says not applicable rather than pretending
   an inspection was skipped.
2. For a cavity lot, place the witness point in the manufacturing flow ahead
   of the seal, and report any cavity-affecting operation running between the
   two: whatever it changed went into the package unwitnessed.
3. Judge who held the witness. Class 2 allows the customer to delegate to an
   approved inspection agency, which then owes a delegation reference;
   nobody working for the manufacturer can hold that delegation.
4. Admit a lot with no witness only against an accepted in-line monitoring
   programme carrying an approval reference and a validity that still covers
   the lot date.
5. Group the cavity lots by part type and compute the witnessed coverage each
   part type achieved, comparing it with the minimum coverage the project
   requires within a representation-sized tolerance.
6. Report the per-lot records, the per-part-type coverage and a verdict
   carrying every finding rather than the first.
"""

import datetime

__all__ = [
    "CAVITY_PACKAGE_FAMILIES",
    "SEALLESS_PACKAGE_FAMILIES",
    "CAVITY_AFFECTING_OPERATIONS",
    "DELEGATED_WITNESS_ROLES",
    "MANUFACTURER_ROLES",
    "AGENCY_ROLE",
    "COVERAGE_TOLERANCE",
    "normalize_token",
    "parse_iso_date",
    "precap_applies_to",
    "seal_placement_findings",
    "witness_authority_findings",
    "inline_programme_findings",
    "coverage_findings",
    "assess_precap_lot",
    "assess_precap_inspection",
]

# Package families that close a cavity and therefore carry a witness point.
CAVITY_PACKAGE_FAMILIES = ("hermetic-cavity", "metal-can", "ceramic-flatpack")

# Package families with no cavity and no seal operation to witness.
SEALLESS_PACKAGE_FAMILIES = ("encapsulated-nonhermetic", "moulded-plastic", "passive-chip")

# Operations that change what is inside the package: run after the witness
# has signed, each of them enters the cavity unwitnessed.
CAVITY_AFFECTING_OPERATIONS = (
    "die-attach",
    "wire-bond",
    "die-replacement",
    "internal-clean",
    "desiccant-load",
    "lid-rework",
)

# Roles that may hold the witness on behalf of the customer.
AGENCY_ROLE = "approved-inspection-agency"
DELEGATED_WITNESS_ROLES = ("customer-product-assurance", AGENCY_ROLE)

# Roles that cannot hold it, whatever the paperwork says.
MANUFACTURER_ROLES = ("manufacturer-quality", "manufacturer-production")

# Coverage is a ratio of small integers compared against a fraction written
# another way; a coverage landing on its minimum must not fail on
# representation alone.
COVERAGE_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_mapping(value, label):
    """Return a mapping, raising on anything else."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def normalize_token(value, label):
    """Return a lower-case hyphenated token from a free-text field."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def parse_iso_date(value, label):
    """Return a date parsed from an ISO calendar string."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar date, got '%s'" % (label, text))


def precap_applies_to(package_family):
    """Return True where the package closes a cavity a witness could inspect."""
    family = normalize_token(package_family, "package family")
    if family in CAVITY_PACKAGE_FAMILIES:
        return True
    if family in SEALLESS_PACKAGE_FAMILIES:
        return False
    raise ValueError(
        "package family '%s' is neither a cavity nor a sealless family" % family
    )


def _flow_tokens(flow):
    """Return the manufacturing flow as an ordered token list."""
    if not isinstance(flow, (list, tuple)) or not flow:
        raise ValueError("flow must be a non-empty sequence of manufacturing steps")
    tokens = []
    for position, value in enumerate(flow):
        token = normalize_token(value, "flow[%d]" % position)
        if token in tokens:
            raise ValueError("step '%s' appears twice in the flow" % token)
        tokens.append(token)
    return tokens


def seal_placement_findings(flow, witness_step, seal_step):
    """Return the findings raised by where the witness point sits in the flow."""
    tokens = _flow_tokens(flow)
    witness = normalize_token(witness_step, "witness step")
    seal = normalize_token(seal_step, "seal step")
    if witness not in tokens:
        raise ValueError("witness step '%s' is not in the flow" % witness)
    if seal not in tokens:
        raise ValueError("seal step '%s' is not in the flow" % seal)

    at = tokens.index(witness)
    closed = tokens.index(seal)
    if at == closed:
        return ["the witness point and the seal are recorded as one step '%s'" % seal]
    if at > closed:
        return [
            "the witness point '%s' is placed after the seal '%s', where the cavity "
            "can no longer be seen" % (witness, seal)
        ]
    findings = []
    for token in tokens[at + 1:closed]:
        if token in CAVITY_AFFECTING_OPERATIONS:
            findings.append(
                "'%s' runs between the witness point and the seal, so what it put in "
                "the cavity was never witnessed" % token
            )
    return findings


def witness_authority_findings(witness):
    """Return the findings raised by who held the witness."""
    _require_mapping(witness, "witness")
    for key in ("name", "role"):
        if key not in witness:
            raise ValueError("witness missing required key '%s'" % key)
    name = _require_text(witness["name"], "witness name")
    role = normalize_token(witness["role"], "witness role")
    known = DELEGATED_WITNESS_ROLES + MANUFACTURER_ROLES
    if role not in known:
        raise ValueError("witness role '%s' is not a recognised role" % role)

    findings = []
    if role in MANUFACTURER_ROLES:
        findings.append(
            "witness '%s' holds the manufacturer role '%s', so the inspection is the "
            "manufacturer's own check" % (name, role)
        )
        return findings
    if role == AGENCY_ROLE:
        delegation = witness.get("delegation_reference")
        if not isinstance(delegation, str) or not delegation.strip():
            findings.append(
                "witness '%s' acts as an inspection agency with no delegation "
                "reference from the customer" % name
            )
    return findings


def inline_programme_findings(programme, lot_date):
    """Return the findings raised by the in-line route offered in place of a witness."""
    on = parse_iso_date(lot_date, "lot_date")
    if programme is None:
        return ["the lot was sealed unwitnessed with no in-line monitoring programme"]
    _require_mapping(programme, "programme")

    findings = []
    reference = programme.get("approval_reference")
    if not isinstance(reference, str) or not reference.strip():
        findings.append("the in-line monitoring programme carries no approval reference")
    if not programme.get("customer_accepted", False):
        findings.append("the in-line monitoring programme was never accepted by the customer")
    valid_until = programme.get("valid_until")
    if valid_until is None:
        findings.append("the in-line monitoring programme carries no validity date")
    else:
        expiry = parse_iso_date(valid_until, "programme valid_until")
        if expiry < on:
            findings.append(
                "the in-line monitoring programme lapsed on %s, before the lot date %s"
                % (expiry.isoformat(), on.isoformat())
            )
    return findings


def coverage_findings(witnessed_lots, cavity_lots, minimum_fraction, part_type):
    """Return the witnessed coverage of one part type and any shortfall."""
    if not isinstance(cavity_lots, int) or isinstance(cavity_lots, bool):
        raise ValueError("cavity_lots must be an integer")
    if cavity_lots < 1:
        raise ValueError("cavity_lots must be at least 1 for part type '%s'" % part_type)
    if not isinstance(witnessed_lots, int) or isinstance(witnessed_lots, bool):
        raise ValueError("witnessed_lots must be an integer")
    if not 0 <= witnessed_lots <= cavity_lots:
        raise ValueError(
            "witnessed_lots %d is outside 0..%d for part type '%s'"
            % (witnessed_lots, cavity_lots, part_type)
        )
    if isinstance(minimum_fraction, bool) or not isinstance(minimum_fraction, (int, float)):
        raise ValueError("minimum_fraction must be a real number")
    minimum = float(minimum_fraction)
    if not 0.0 <= minimum <= 1.0:
        raise ValueError("minimum_fraction must lie in 0..1, got %g" % minimum)

    achieved = witnessed_lots / float(cavity_lots)
    findings = []
    if achieved < minimum - COVERAGE_TOLERANCE:
        findings.append(
            "part type '%s' witnessed %d of %d cavity lots, a coverage of %.4f against "
            "the %.4f required" % (part_type, witnessed_lots, cavity_lots, achieved, minimum)
        )
    return {
        "part_type": part_type,
        "cavity_lots": cavity_lots,
        "witnessed_lots": witnessed_lots,
        "coverage": achieved,
        "minimum_fraction": minimum,
        "findings": findings,
    }


def assess_precap_lot(lot):
    """Return one Class 2 production-lot record carrying its findings."""
    _require_mapping(lot, "lot")
    for key in ("lot_id", "part_type", "package_family", "lot_date"):
        if key not in lot:
            raise ValueError("lot missing required key '%s'" % key)
    lot_id = _require_text(lot["lot_id"], "lot_id")
    part_type = normalize_token(lot["part_type"], "part_type")
    lot_date = parse_iso_date(lot["lot_date"], "lot_date")

    if not precap_applies_to(lot["package_family"]):
        return {
            "lot_id": lot_id,
            "part_type": part_type,
            "applicable": False,
            "witnessed": False,
            "findings": [],
            "acceptable": True,
        }

    if not lot.get("witnessed", False):
        findings = inline_programme_findings(lot.get("inline_programme"), lot_date)
        return {
            "lot_id": lot_id,
            "part_type": part_type,
            "applicable": True,
            "witnessed": False,
            "findings": findings,
            "acceptable": not findings,
        }

    for key in ("flow", "witness_step", "seal_step", "witness"):
        if key not in lot:
            raise ValueError("witnessed lot '%s' missing required key '%s'" % (lot_id, key))

    findings = []
    findings.extend(seal_placement_findings(lot["flow"], lot["witness_step"], lot["seal_step"]))
    findings.extend(witness_authority_findings(lot["witness"]))
    return {
        "lot_id": lot_id,
        "part_type": part_type,
        "applicable": True,
        "witnessed": True,
        "findings": findings,
        "acceptable": not findings,
    }


def assess_precap_inspection(order):
    """Run the full clause 5.3.4 Class 2 pre-cap source inspection assessment.

    order keys: order_reference, minimum_coverage, lots.
    """
    _require_mapping(order, "order")
    for key in ("order_reference", "minimum_coverage", "lots"):
        if key not in order:
            raise ValueError("order missing required key '%s'" % key)
    reference = _require_text(order["order_reference"], "order_reference")
    lots = order["lots"]
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("lots must be a non-empty sequence")

    records = []
    seen = []
    for lot in lots:
        record = assess_precap_lot(lot)
        if record["lot_id"] in seen:
            raise ValueError("production lot '%s' is reported twice" % record["lot_id"])
        seen.append(record["lot_id"])
        records.append(record)

    grouped = {}
    for record in records:
        if not record["applicable"]:
            continue
        bucket = grouped.setdefault(record["part_type"], {"cavity": 0, "witnessed": 0})
        bucket["cavity"] += 1
        if record["witnessed"] and record["acceptable"]:
            bucket["witnessed"] += 1

    coverage = []
    findings = []
    for part_type in sorted(grouped):
        bucket = grouped[part_type]
        entry = coverage_findings(
            bucket["witnessed"], bucket["cavity"], order["minimum_coverage"], part_type
        )
        coverage.append(entry)
        findings.extend(entry["findings"])
    for record in records:
        findings.extend(record["findings"])

    cavity_records = [r for r in records if r["applicable"]]
    witnessed = [r for r in cavity_records if r["witnessed"] and r["acceptable"]]
    return {
        "order_reference": reference,
        "lots": records,
        "coverage_by_part_type": coverage,
        "cavity_lot_count": len(cavity_records),
        "witnessed_fraction": (
            len(witnessed) / float(len(cavity_records)) if cavity_records else 0.0
        ),
        "inspection_complete": not findings,
        "findings": findings,
    }
