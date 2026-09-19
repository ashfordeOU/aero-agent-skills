"""Flowing a programme cleanliness requirement into procurement and AIT paper.

Anchor: the contamination and cleanliness control practice of
ECSS-Q-ST-70-01C, at programme level (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. A cleanliness requirement only exists where it binds somebody. A limit
   written in a programme contamination control plan and nowhere else
   binds no supplier and no integration team, so the flowdown is graded
   on the documents that actually carry it: the purchase orders that buy
   the item and the AIT procedures that handle it.
2. A carried limit is compared with its parent, not merely counted. A
   child document may be stricter than the programme asked for, and that
   is the supplier's business. A child document that is looser has
   relaxed a programme requirement, and a relaxation stands only with a
   waiver reference beside it.
3. Limits here are upper bounds in which a smaller number is cleaner --
   particles per unit area, residue mass per unit area, the largest
   permitted particle size. Comparing two limits of different kinds is
   refused rather than guessed at.
4. A document carrying a requirement identifier that no parent defines
   is a finding in its own right. It is usually a requirement that was
   renumbered upstream, and the supplier is building to the old one.
5. A carried requirement with no verification method named is carried in
   name only: nobody at goods receipt or at the AIT bench knows what to
   measure, so it cannot be shown to have been met.

Stdlib only, offline, deterministic.
"""

# Requirement kinds. Each is an upper bound where smaller is cleaner.
KIND_PARTICULATE_COUNT = "particulate-count-per-0p1m2"
KIND_PARTICULATE_SIZE = "largest-particle-um"
KIND_OBSCURATION = "obscuration-pct"
KIND_MOLECULAR = "residue-mg-per-0p1m2"
REQUIREMENT_KINDS = (
    KIND_PARTICULATE_COUNT,
    KIND_PARTICULATE_SIZE,
    KIND_OBSCURATION,
    KIND_MOLECULAR,
)

# The two document families a programme requirement has to reach.
ROLE_PROCUREMENT = "procurement"
ROLE_AIT = "ait"
DOCUMENT_ROLES = (ROLE_PROCUREMENT, ROLE_AIT)

# Limits are compared as floats, so a child repeating its parent exactly
# can land a unit in the last place either side. This tolerance absorbs
# that representation error only; a real relaxation is never tolerated.
RELATIVE_TOLERANCE = 1.0e-12
ABSOLUTE_TOLERANCE = 1.0e-15


def _text(label, value):
    """Return value as a squeezed non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _optional_text(label, value):
    if value is None:
        return None
    text = _text(label, value)
    return text


def _positive(label, value):
    """Return value as a strictly positive float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return float(value)


def validate_requirement(requirement):
    """Validate one parent cleanliness requirement, returning a normalized copy."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    rid = _text("requirement id", requirement.get("id"))
    kind = _text("requirement %s kind" % rid, requirement.get("kind"))
    if kind not in REQUIREMENT_KINDS:
        raise ValueError(
            "requirement %s declares kind %r, which is not one of %r"
            % (rid, kind, list(REQUIREMENT_KINDS))
        )
    limit = _positive("requirement %s limit" % rid, requirement.get("limit"))
    surface = _text("requirement %s surface" % rid, requirement.get("surface"))
    roles = requirement.get("required_roles", DOCUMENT_ROLES)
    if not isinstance(roles, (list, tuple)) or not roles:
        raise ValueError("requirement %s required_roles must be a non-empty list" % rid)
    normalized_roles = []
    for role in roles:
        role = _text("requirement %s required role" % rid, role)
        if role not in DOCUMENT_ROLES:
            raise ValueError(
                "requirement %s names role %r, which is not one of %r"
                % (rid, role, list(DOCUMENT_ROLES))
            )
        if role not in normalized_roles:
            normalized_roles.append(role)
    return {
        "id": rid,
        "kind": kind,
        "limit": limit,
        "surface": surface,
        "required_roles": tuple(normalized_roles),
    }


def validate_carried_clause(clause):
    """Validate one clause a receiving document carries."""
    if not isinstance(clause, dict):
        raise ValueError("carried clause must be a mapping")
    rid = _text("carried clause requirement_id", clause.get("requirement_id"))
    kind = _text("carried clause %s kind" % rid, clause.get("kind"))
    if kind not in REQUIREMENT_KINDS:
        raise ValueError(
            "carried clause %s declares kind %r, which is not one of %r"
            % (rid, kind, list(REQUIREMENT_KINDS))
        )
    limit = _positive("carried clause %s limit" % rid, clause.get("limit"))
    method = _optional_text(
        "carried clause %s verification_method" % rid, clause.get("verification_method")
    )
    waiver = _optional_text(
        "carried clause %s waiver_reference" % rid, clause.get("waiver_reference")
    )
    return {
        "requirement_id": rid,
        "kind": kind,
        "limit": limit,
        "verification_method": method,
        "waiver_reference": waiver,
    }


def validate_document(document):
    """Validate one receiving document and its carried clauses."""
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping")
    did = _text("document id", document.get("id"))
    role = _text("document %s role" % did, document.get("role"))
    if role not in DOCUMENT_ROLES:
        raise ValueError(
            "document %s declares role %r, which is not one of %r"
            % (did, role, list(DOCUMENT_ROLES))
        )
    clauses = document.get("clauses")
    if not isinstance(clauses, list) or not clauses:
        raise ValueError("document %s must carry a non-empty clause list" % did)
    normalized = [validate_carried_clause(clause) for clause in clauses]
    seen = set()
    for clause in normalized:
        if clause["requirement_id"] in seen:
            raise ValueError(
                "document %s carries requirement %s twice"
                % (did, clause["requirement_id"])
            )
        seen.add(clause["requirement_id"])
    return {"id": did, "role": role, "clauses": normalized}


def is_at_least_as_strict(carried_limit, parent_limit):
    """True when the carried limit binds at least as tightly as its parent."""
    carried = _positive("carried_limit", carried_limit)
    parent = _positive("parent_limit", parent_limit)
    slack = abs(parent) * RELATIVE_TOLERANCE + ABSOLUTE_TOLERANCE
    return carried <= parent + slack


def strictness_ratio(carried_limit, parent_limit):
    """Carried limit over parent limit: below one is stricter than asked."""
    carried = _positive("carried_limit", carried_limit)
    parent = _positive("parent_limit", parent_limit)
    return carried / parent


def assess_flowdown(requirements, documents):
    """Grade a cleanliness requirement flowdown into procurement and AIT paper."""
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("requirements must be a non-empty list")
    if not isinstance(documents, list) or not documents:
        raise ValueError("documents must be a non-empty list")

    parents = {}
    for requirement in requirements:
        norm = validate_requirement(requirement)
        if norm["id"] in parents:
            raise ValueError("duplicate requirement id %r" % (norm["id"],))
        parents[norm["id"]] = norm

    carriers = []
    for document in documents:
        norm = validate_document(document)
        if any(existing["id"] == norm["id"] for existing in carriers):
            raise ValueError("duplicate document id %r" % (norm["id"],))
        carriers.append(norm)

    findings = []
    rows = {}
    for rid, parent in parents.items():
        rows[rid] = {
            "requirement_id": rid,
            "kind": parent["kind"],
            "parent_limit": parent["limit"],
            "surface": parent["surface"],
            "required_roles": list(parent["required_roles"]),
            "carried_by": [],
            "roles_covered": [],
            "tightest_carried_limit": None,
            "findings": [],
        }

    for document in carriers:
        for clause in document["clauses"]:
            rid = clause["requirement_id"]
            if rid not in parents:
                findings.append("document-carries-a-requirement-no-parent-defines")
                continue
            parent = parents[rid]
            row = rows[rid]
            if clause["kind"] != parent["kind"]:
                row["findings"].append("carried-clause-changes-the-requirement-kind")
                findings.append("carried-clause-changes-the-requirement-kind")
                continue
            row["carried_by"].append(document["id"])
            if document["role"] not in row["roles_covered"]:
                row["roles_covered"].append(document["role"])
            current = row["tightest_carried_limit"]
            if current is None or clause["limit"] < current:
                row["tightest_carried_limit"] = clause["limit"]
            if not is_at_least_as_strict(clause["limit"], parent["limit"]):
                row["findings"].append("carried-limit-looser-than-the-parent")
                findings.append("carried-limit-looser-than-the-parent")
                if clause["waiver_reference"] is None:
                    row["findings"].append("relaxation-carried-without-a-waiver")
                    findings.append("relaxation-carried-without-a-waiver")
            if clause["verification_method"] is None:
                row["findings"].append("carried-clause-names-no-verification-method")
                findings.append("carried-clause-names-no-verification-method")

    complete = 0
    for rid in sorted(rows):
        row = rows[rid]
        if not row["carried_by"]:
            row["findings"].append("requirement-reaches-no-document")
            findings.append("requirement-reaches-no-document")
        missing = [
            role for role in row["required_roles"] if role not in row["roles_covered"]
        ]
        row["missing_roles"] = missing
        for role in missing:
            row["findings"].append("requirement-missing-a-%s-document" % role)
            findings.append("requirement-missing-a-%s-document" % role)
        row["flowed"] = not row["findings"]
        if row["flowed"]:
            complete += 1

    ordered = [rows[rid] for rid in sorted(rows)]
    gaps = [row["requirement_id"] for row in ordered if not row["flowed"]]
    coverage = complete / float(len(ordered))
    return {
        "requirement_count": len(ordered),
        "document_count": len(carriers),
        "requirements": ordered,
        "fully_flowed_count": complete,
        "coverage_fraction": coverage,
        "gap_requirement_ids": gaps,
        "findings": findings,
        "verdict": "flowdown-complete" if not gaps else "flowdown-incomplete",
        "clear": not findings,
    }
