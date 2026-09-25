"""Supplier selection, flow-down and control of procured software.

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025), clause 5.4 (selecting
suppliers, the assurance requirements passed to them, monitoring them, and
the criticality and security results they must be given), clause 5.5
(procurement documents, the procured component list, per-item procurement
data, identification, receiving inspection, exportability) and clause 7.4
(ground equipment and services for the operational system). Software
furnished by the customer is existing software and is handled the same
way. Paraphrased into checks; no requirement text is reproduced.

Procedure implemented here
--------------------------
1. Grade a supplier selection record.
2. Build the flow-down a lower-level supplier must receive for its role,
   category and sensitivity, and grade a package against it.
3. Grade the monitoring record of a lower-level supplier.
4. Grade each procured or customer-furnished software item for its
   procurement data, configuration registration and exportability.
5. Run a receiving inspection: compare what arrived with what was ordered,
   including an integrity hash computed from the delivered bytes.
6. Grade the selection justification for operational ground equipment and
   support services.
"""

import hashlib

__all__ = [
    "PROCUREMENT_DATA",
    "GROUND_SELECTION_CRITERIA",
    "grade_supplier_selection",
    "build_flowdown",
    "check_flowdown_package",
    "check_supplier_monitoring",
    "check_procured_item",
    "receiving_inspection",
    "check_ground_selection",
]

_CATEGORIES = ("A", "B", "C", "D")

# Data owed for each procured software item (clause 5.5.3), in own words.
PROCUREMENT_DATA = (
    "ordering_criteria",
    "receiving_inspection_criteria",
    "backup_solution",
    "contract_for_development_maintenance_upgrades",
)

# Aspects on which operational ground computers and services are selected.
GROUND_SELECTION_CRITERIA = (
    "performance", "maintenance", "durability-and-consistency",
    "criticality-assessment", "security-sensitivity-assessment",
    "regulatory-compliance", "support-documentation", "acceptance-and-warranty",
    "installation-and-training", "evolution-possibilities", "copyright",
    "availability", "compatibility", "site-constraints",
)


def _cat(value):
    c = str(value).strip().upper()
    if c not in _CATEGORIES:
        raise ValueError("unknown software criticality category %r" % (value,))
    return c


def grade_supplier_selection(record):
    """Grade the selection of one software supplier.

    record: dict with name, pre_award_assessment (bool), source_recorded
        (bool), supplies_existing_software (bool) and reuse_file (bool, the
        reuse analysis outputs made available for existing software,
        including software inside off-the-shelf units).
    Returns a list of findings.
    """
    found = []
    if not record.get("pre_award_assessment"):
        found.append("no pre-award audit or assessment result")
    if not record.get("source_recorded"):
        found.append("procurement source not recorded")
    if record.get("supplies_existing_software") and not record.get("reuse_file"):
        found.append("existing software offered without its reuse file")
    return found


def build_flowdown(category, sensitive, role="development"):
    """Build the list of items a lower-level supplier must receive.

    role: 'development', 'maintenance' or 'cots-provider'. A provider of
    off-the-shelf software is not asked for its own assurance plan; the
    buyer covers it through the reuse file and receiving inspection.
    Returns a list of (key, text).
    """
    cat = _cat(category)
    if role not in ("development", "maintenance", "cots-provider"):
        raise ValueError("unknown supplier role %r" % (role,))
    items = []
    if role != "cots-provider":
        items.append(("spa-requirements", "assurance requirements tailored to the supplier's role"))
        items.append(("spap-required", "obligation to write a software product assurance plan"))
        items.append(("customer-acceptance", "requirements submitted to the customer for acceptance"))
    items.append(("criticality", "category %s of the product to be developed" % cat))
    if cat != "D":
        items.append(("higher-level-failures", "failures the product can cause at higher level"))
    items.append(("sensitivity", "security sensitivity of the product to be developed"))
    if sensitive:
        items.append(("attack-scenarios", "failures, attacks and their higher-level security impact"))
    return items


def check_flowdown_package(package, category, sensitive, role="development"):
    """Grade a flow-down package against build_flowdown.

    package: mapping key -> bool (item present).
    Returns the list of missing keys.
    """
    return [k for k, _ in build_flowdown(category, sensitive, role) if not package.get(k)]


def check_supplier_monitoring(record, milestone):
    """Grade the monitoring of one lower-level supplier.

    record: dict with spap_reviewed, spap_approved, spap_sent_to_customer
        (bools), process_checks (list of dates or ids of audits and
        inspections of process and product), final_validation_witnessed
        (bool).
    milestone: 'srr', 'pdr', 'cdr', 'qr' or 'ar'. The supplier plan is
    owed approved and passed to the customer by PDR; continuous checks are
    expected from PDR on; final validation is monitored by QR.
    Returns a list of findings.
    """
    order = ("srr", "pdr", "cdr", "qr", "ar")
    ms = str(milestone).lower()
    if ms not in order:
        raise ValueError("unknown milestone %r" % (milestone,))
    now = order.index(ms)
    found = []
    if now >= 1:
        if not record.get("spap_reviewed"):
            found.append("supplier assurance plan not reviewed")
        elif not record.get("spap_approved"):
            found.append("supplier assurance plan not approved")
        if not record.get("spap_sent_to_customer"):
            found.append("supplier assurance plan not passed to the customer")
    if now >= 2 and not record.get("process_checks"):
        found.append("no process or product verification of the supplier on record")
    if now >= 3 and not record.get("final_validation_witnessed"):
        found.append("final validation of the supplier product not monitored")
    return found


def check_procured_item(item, customer_requires_origin=False):
    """Grade one procured or customer-furnished software item.

    item: dict with name, origin ('procured' or 'customer-furnished'),
        the PROCUREMENT_DATA keys (text), country_of_origin, cm_id (the
        configuration identifier it is registered under),
        export_constraints_identified (bool), inspection_report (id or
        empty), reuse_file (bool, needed for customer-furnished items).
    Returns a list of findings.
    """
    found = []
    origin = item.get("origin", "procured")
    if origin not in ("procured", "customer-furnished"):
        raise ValueError("unknown origin %r" % (origin,))
    if origin == "procured":
        for key in PROCUREMENT_DATA:
            if not str(item.get(key) or "").strip():
                found.append("missing procurement data: %s" % key.replace("_", " "))
        if customer_requires_origin and not str(item.get("country_of_origin") or "").strip():
            found.append("country of origin required by the customer and not given")
    elif not item.get("reuse_file"):
        found.append("customer-furnished software without a reuse assessment")
    if not str(item.get("cm_id") or "").strip():
        found.append("not registered under configuration management")
    if not item.get("export_constraints_identified"):
        found.append("exportability constraints not identified")
    if not str(item.get("inspection_report") or "").strip():
        found.append("no receiving inspection report")
    return found


def receiving_inspection(ordered, delivered, payload=None):
    """Compare a delivered software item with the order.

    ordered: dict with version, options (list), sha256 (expected digest,
        optional), licences (count, optional).
    delivered: dict with version, options (list), documentation (bool),
        licences (count, optional).
    payload: bytes of the delivered image; when given its SHA-256 is
        computed and compared with the expected digest.

    Returns dict(verdict, findings, digest). verdict is 'accept',
    'accept-with-reservation' (documentation missing only) or
    'reject-return-to-supplier'.
    """
    findings, hard = [], False
    if str(ordered.get("version")) != str(delivered.get("version")):
        findings.append("version %s delivered, %s ordered" % (delivered.get("version"), ordered.get("version")))
        hard = True
    missing_opts = sorted(set(ordered.get("options") or []) - set(delivered.get("options") or []))
    if missing_opts:
        findings.append("options missing: %s" % ", ".join(missing_opts))
        hard = True
    if ordered.get("licences") is not None and \
            int(delivered.get("licences") or 0) < int(ordered["licences"]):
        findings.append("fewer licences delivered than ordered")
        hard = True
    digest = None
    if payload is not None:
        digest = hashlib.sha256(payload).hexdigest()
        expected = str(ordered.get("sha256") or "").lower()
        if expected and digest != expected:
            findings.append("integrity digest does not match the order")
            hard = True
        elif not expected:
            findings.append("no expected digest in the order; record %s as received" % digest)
    soft = not delivered.get("documentation")
    if soft:
        findings.append("support documentation not delivered")
    if hard:
        verdict = "reject-return-to-supplier"
    elif soft:
        verdict = "accept-with-reservation"
    else:
        verdict = "accept"
    return {"verdict": verdict, "findings": findings, "digest": digest}


def check_ground_selection(justification, service=None):
    """Grade the selection of operational ground equipment and services.

    justification: mapping criterion (GROUND_SELECTION_CRITERIA) -> text.
    service: optional dict for procured support services with sla,
        quality_of_service, escalation (bools) and lifetime_support (bool:
        the provider can maintain it for the specified life).
    Returns dict(missing_criteria, service_gaps, covered).
    """
    missing = [c for c in GROUND_SELECTION_CRITERIA
               if not str((justification or {}).get(c) or "").strip()]
    gaps = []
    if service is not None:
        for key, text in (("sla", "service level agreement"),
                          ("quality_of_service", "quality of service"),
                          ("escalation", "escalation procedure"),
                          ("lifetime_support", "maintenance over the specified life")):
            if not service.get(key):
                gaps.append(text)
    covered = len(GROUND_SELECTION_CRITERIA) - len(missing)
    return {"missing_criteria": missing, "service_gaps": gaps,
            "covered": "%d/%d" % (covered, len(GROUND_SELECTION_CRITERIA))}
