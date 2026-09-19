#!/usr/bin/env python3
"""Qualification organization for two-phase heat transport equipment.

Anchor: ECSS-E-ST-31-02 clauses 4.2 to 4.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two questions are settled before any hardware is built. Who is the
customer and who is the supplier for each duty the standard embeds, and
which of those embedded generic requirements actually bite for the
product category and procurement route in hand. A duty nobody owns and a
duty the supplier quietly dropped are the two failure modes this module
exists to find.

Product categories
    new-development     a design with no qualified predecessor
    modified-design     a qualified design changed for this application
    off-the-shelf       a catalogue item already qualified elsewhere

Procurement routes
    full-development-contract   the supplier develops against a customer TS
    recurring-build             a repeat build of an already-qualified item
    catalogue-purchase          the item is bought as offered

Ownership of a duty marked joint is not a free choice: it follows the
route. On a catalogue purchase the supplier has no development visibility
to offer, so the customer carries it; on a development contract the
supplier is the only party holding the design data, so the supplier
carries it; on a recurring build the two parties keep it jointly.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

PRODUCT_CATEGORIES = ("new-development", "modified-design", "off-the-shelf")
PROCUREMENT_ROUTES = (
    "full-development-contract",
    "recurring-build",
    "catalogue-purchase",
)
ROLES = ("customer", "supplier", "joint")

ORGANIZATION_AGREED = "organization-agreed"
ORGANIZATION_OPEN = "organization-open"

# Embedded generic duties of clauses 4.2 to 4.3, paraphrased to a subject
# line each. base_role is the party the standard points at before the
# route is considered; disapplicable says whether the duty may be dropped
# at all, and then only against a recorded tailoring agreement.
DEFAULT_REQUIREMENT_REGISTRY = (
    {
        "id": "qualification-status-declaration",
        "subject": "state the qualification status claimed for the equipment",
        "categories": PRODUCT_CATEGORIES,
        "routes": PROCUREMENT_ROUTES,
        "base_role": "supplier",
        "disapplicable": False,
    },
    {
        "id": "qualification-programme-approval",
        "subject": "agree the qualification programme before it is run",
        "categories": ("new-development", "modified-design"),
        "routes": ("full-development-contract", "recurring-build"),
        "base_role": "customer",
        "disapplicable": False,
    },
    {
        "id": "heritage-evidence-submission",
        "subject": "submit the heritage evidence the reuse claim rests on",
        "categories": ("modified-design", "off-the-shelf"),
        "routes": PROCUREMENT_ROUTES,
        "base_role": "supplier",
        "disapplicable": False,
    },
    {
        "id": "verification-matrix-maintenance",
        "subject": "keep the verification matrix current against the TS",
        "categories": PRODUCT_CATEGORIES,
        "routes": PROCUREMENT_ROUTES,
        "base_role": "joint",
        "disapplicable": False,
    },
    {
        "id": "working-fluid-compatibility-declaration",
        "subject": "declare the fluid and envelope material compatibility basis",
        "categories": PRODUCT_CATEGORIES,
        "routes": PROCUREMENT_ROUTES,
        "base_role": "supplier",
        "disapplicable": False,
    },
    {
        "id": "nonconformance-disposition-authority",
        "subject": "hold disposition authority over a major non-conformance",
        "categories": PRODUCT_CATEGORIES,
        "routes": PROCUREMENT_ROUTES,
        "base_role": "customer",
        "disapplicable": False,
    },
    {
        "id": "acceptance-data-package-delivery",
        "subject": "deliver the acceptance data package with the hardware",
        "categories": PRODUCT_CATEGORIES,
        "routes": PROCUREMENT_ROUTES,
        "base_role": "supplier",
        "disapplicable": False,
    },
    {
        "id": "development-test-reporting",
        "subject": "report the development tests that fed the design",
        "categories": ("new-development",),
        "routes": ("full-development-contract",),
        "base_role": "supplier",
        "disapplicable": True,
    },
    {
        "id": "qualification-unit-retention",
        "subject": "retain the qualification unit for later reference",
        "categories": ("new-development", "modified-design"),
        "routes": ("full-development-contract", "recurring-build"),
        "base_role": "joint",
        "disapplicable": True,
    },
    {
        "id": "obsolescence-notification",
        "subject": "notify a change of part, material or process source",
        "categories": PRODUCT_CATEGORIES,
        "routes": ("recurring-build", "catalogue-purchase"),
        "base_role": "supplier",
        "disapplicable": True,
    },
)

_JOINT_RESOLUTION = {
    "full-development-contract": "supplier",
    "catalogue-purchase": "customer",
    "recurring-build": "joint",
}


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (name, value))
    return tuple(value)


def validate_requirement(record):
    """Check one embedded generic requirement record is usable."""
    if not isinstance(record, dict):
        raise ValueError("requirement must be a mapping, got %r" % (record,))
    _require_text("requirement id", record.get("id"))
    _require_text("requirement subject", record.get("subject"))
    _require_choice("base_role", record.get("base_role"), ROLES)
    categories = _require_sequence("requirement categories", record.get("categories"))
    if not categories:
        raise ValueError("requirement %s applies to no category" % record["id"])
    for category in categories:
        _require_choice("requirement category", category, PRODUCT_CATEGORIES)
    routes = _require_sequence("requirement routes", record.get("routes"))
    if not routes:
        raise ValueError("requirement %s applies to no route" % record["id"])
    for route in routes:
        _require_choice("requirement route", route, PROCUREMENT_ROUTES)
    if not isinstance(record.get("disapplicable"), bool):
        raise ValueError("requirement %s needs a boolean disapplicable" % record["id"])
    return record


def validate_registry(registry):
    """Check a whole registry: every record usable, no duplicate id."""
    records = _require_sequence("registry", registry)
    if not records:
        raise ValueError("registry is empty; there is nothing to organize")
    seen = set()
    for record in records:
        validate_requirement(record)
        if record["id"] in seen:
            raise ValueError("duplicate requirement id %r in registry" % record["id"])
        seen.add(record["id"])
    return records


def requirement_applies(record, product_category, procurement_route):
    """Say whether one embedded generic requirement bites in this context."""
    validate_requirement(record)
    _require_choice("product_category", product_category, PRODUCT_CATEGORIES)
    _require_choice("procurement_route", procurement_route, PROCUREMENT_ROUTES)
    return (
        product_category in tuple(record["categories"])
        and procurement_route in tuple(record["routes"])
    )


def resolve_role(record, procurement_route):
    """Owner of the duty once the procurement route is taken into account."""
    validate_requirement(record)
    _require_choice("procurement_route", procurement_route, PROCUREMENT_ROUTES)
    if record["base_role"] != "joint":
        return record["base_role"]
    return _JOINT_RESOLUTION[procurement_route]


def applicable_requirements(
    product_category, procurement_route, registry=DEFAULT_REQUIREMENT_REGISTRY
):
    """Every embedded generic requirement that survives the context, owned."""
    records = validate_registry(registry)
    _require_choice("product_category", product_category, PRODUCT_CATEGORIES)
    _require_choice("procurement_route", procurement_route, PROCUREMENT_ROUTES)
    resolved = []
    for record in records:
        if not requirement_applies(record, product_category, procurement_route):
            continue
        resolved.append(
            {
                "id": record["id"],
                "subject": record["subject"],
                "owner": resolve_role(record, procurement_route),
                "disapplicable": record["disapplicable"],
            }
        )
    return resolved


def group_by_owner(resolved):
    """Group the surviving duties by the party that carries them."""
    grouped = {role: [] for role in ROLES}
    for item in _require_sequence("resolved requirements", resolved):
        if not isinstance(item, dict):
            raise ValueError("resolved requirement must be a mapping, got %r" % (item,))
        owner = _require_choice("owner", item.get("owner"), ROLES)
        grouped[owner].append(_require_text("id", item.get("id")))
    return grouped


def audit_disapplications(resolved, disapplied, tailoring_agreement=None):
    """Grade every duty the parties propose to drop.

    A duty may be dropped only when the registry marks it disapplicable
    AND a tailoring agreement reference is on record. Anything else is a
    finding, including a dropped duty that never applied in the first
    place, because that says the parties are working from a different
    applicability picture.
    """
    index = {}
    for item in _require_sequence("resolved requirements", resolved):
        index[_require_text("id", item.get("id"))] = item
    findings = []
    accepted = []
    for raw in _require_sequence("disapplied", disapplied):
        req_id = _require_text("disapplied id", raw)
        item = index.get(req_id)
        if item is None:
            findings.append(
                "%s is listed as dropped but does not apply to this context"
                % req_id
            )
            continue
        if not item["disapplicable"]:
            findings.append("%s may not be dropped by agreement" % req_id)
            continue
        if tailoring_agreement is None:
            findings.append(
                "%s was dropped with no tailoring agreement on record" % req_id
            )
            continue
        _require_text("tailoring_agreement", tailoring_agreement)
        accepted.append(req_id)
    return {"accepted": accepted, "findings": findings}


def audit_assignments(resolved, declared_assignments):
    """Compare the parties' own role assignment against the resolved one."""
    if not isinstance(declared_assignments, dict):
        raise ValueError(
            "declared_assignments must be a mapping, got %r" % (declared_assignments,)
        )
    findings = []
    unowned = []
    resolved_ids = set()
    for item in _require_sequence("resolved requirements", resolved):
        req_id = _require_text("id", item.get("id"))
        resolved_ids.add(req_id)
        if req_id not in declared_assignments:
            unowned.append(req_id)
            findings.append("%s has been left with no owner" % req_id)
            continue
        declared = _require_choice(
            "declared owner for %s" % req_id, declared_assignments[req_id], ROLES
        )
        if declared != item["owner"]:
            findings.append(
                "%s is owned by the %s on this route, not the %s"
                % (req_id, item["owner"], declared)
            )
    for req_id in sorted(set(declared_assignments) - resolved_ids):
        findings.append(
            "%s carries an owner but does not apply to this context" % req_id
        )
    return {"unowned": unowned, "findings": findings}


def organize_qualification(case, registry=DEFAULT_REQUIREMENT_REGISTRY):
    """Full clauses 4.2 to 4.3 organization with an agreement verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    category = _require_choice(
        "product_category", case.get("product_category"), PRODUCT_CATEGORIES
    )
    route = _require_choice(
        "procurement_route", case.get("procurement_route"), PROCUREMENT_ROUTES
    )
    _require_text("customer", case.get("customer"))
    _require_text("supplier", case.get("supplier"))
    resolved = applicable_requirements(category, route, registry)
    if not resolved:
        raise ValueError(
            "no embedded generic requirement applies to a %s on a %s; the "
            "context is outside the registry" % (category, route)
        )
    assignment_audit = audit_assignments(resolved, case.get("declared_assignments", {}))
    disapplication_audit = audit_disapplications(
        resolved,
        case.get("disapplied", ()),
        case.get("tailoring_agreement"),
    )
    findings = list(assignment_audit["findings"]) + list(
        disapplication_audit["findings"]
    )
    dropped = set(disapplication_audit["accepted"])
    active = [item for item in resolved if item["id"] not in dropped]
    return {
        "product_category": category,
        "procurement_route": route,
        "applicable": [item["id"] for item in resolved],
        "active": [item["id"] for item in active],
        "dropped": sorted(dropped),
        "owners": group_by_owner(active),
        "unowned": assignment_audit["unowned"],
        "findings": findings,
        "verdict": ORGANIZATION_AGREED if not findings else ORGANIZATION_OPEN,
    }
