#!/usr/bin/env python3
"""Inclusive and exclusive category use in tailoring (ECSS-E-ST-20C 8.2).

Deterministic, offline, stdlib-only helpers that:

* normalise the type roles a product carries,
* validate a requirement catalogue whose entries are either exclusive
  (applicable only to the product types they name) or inclusive
  (applicable to every product type they do not except),
* evaluate applicability as the union over the product's roles,
* derive the expected tailoring action and check it against the
  recorded decision, and
* build the pre-tailoring-matrix column with its counts and the
  deleted-weight ratio.

The clause is cited as the anchor only; the procedure below is a
paraphrase, no normative text is reproduced.
"""

import math

# A deleted-weight ratio is a quotient of two sums, so a ratio sitting
# exactly at the agreed ceiling can land marginally high on
# representation alone. The ceiling itself is unchanged.
RATIO_TOLERANCE = 1e-12

CATEGORIES = ("exclusive", "inclusive")

PRODUCT_TYPES = (
    "spacecraft-system",
    "rf-payload",
    "antenna",
    "passive-rf-unit",
    "active-rf-unit",
    "harness",
    "power-conditioning-unit",
    "electrical-ground-support-equipment",
)

DECISIONS = ("keep", "delete")

ACTIONS = ("keep", "delete", "deviation-required")


def _type_list(raw, label):
    """Validate a list of product types: known, non-duplicated, listy."""
    if raw is None:
        return ()
    if not isinstance(raw, (list, tuple)):
        raise ValueError("%s must be a list of product types, got %r" % (label, raw))
    out = []
    for entry in raw:
        if entry not in PRODUCT_TYPES:
            raise ValueError(
                "%s: product type %r unknown; expected one of %s"
                % (label, entry, list(PRODUCT_TYPES))
            )
        if entry in out:
            raise ValueError("%s: duplicate product type %r" % (label, entry))
        out.append(entry)
    return tuple(out)


def normalize_product_roles(roles):
    """Validate the type roles one product carries."""
    out = _type_list(roles, "product roles")
    if not out:
        raise ValueError("a product must declare at least one product-type role")
    return out


def normalize_requirement(requirement):
    """Validate one catalogue requirement and its category consistency."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    rid = requirement.get("id")
    if not isinstance(rid, str) or not rid.strip():
        raise ValueError("requirement id must be a non-empty string, got %r" % (rid,))
    clause = requirement.get("clause")
    if not isinstance(clause, str) or not clause.strip():
        raise ValueError(
            "requirement %s clause anchor must be a non-empty string, got %r"
            % (rid, clause)
        )
    category = requirement.get("category")
    if category not in CATEGORIES:
        raise ValueError(
            "requirement %s category %r unknown; expected one of %s"
            % (rid, category, list(CATEGORIES))
        )
    named = _type_list(requirement.get("product_types"), "requirement %s product_types" % rid)
    excepted = _type_list(
        requirement.get("excepted_types"), "requirement %s excepted_types" % rid
    )
    if category == "exclusive":
        if not named:
            raise ValueError(
                "requirement %s is exclusive but names no product type" % rid
            )
        if excepted:
            raise ValueError(
                "requirement %s is exclusive but carries an exception list; "
                "category and lists contradict" % rid
            )
    else:
        if named:
            raise ValueError(
                "requirement %s is inclusive but names a product-type list; "
                "category and lists contradict" % rid
            )
    weight = requirement.get("weight", 1.0)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        raise ValueError("requirement %s weight must be a real number, got %r" % (rid, weight))
    weight = float(weight)
    if not math.isfinite(weight) or weight <= 0.0:
        raise ValueError("requirement %s weight must be finite and > 0, got %r" % (rid, weight))
    return {
        "id": rid.strip(),
        "clause": clause.strip(),
        "category": category,
        "product_types": named,
        "excepted_types": excepted,
        "weight": weight,
    }


def validate_catalogue(catalogue):
    """Normalise a whole catalogue and reject duplicate identifiers."""
    if not isinstance(catalogue, (list, tuple)):
        raise ValueError("catalogue must be a list, got %r" % (catalogue,))
    if not catalogue:
        raise ValueError("catalogue must not be empty; nothing to tailor")
    out = []
    seen = set()
    for raw in catalogue:
        entry = normalize_requirement(raw)
        if entry["id"] in seen:
            raise ValueError("duplicate requirement id %r in catalogue" % entry["id"])
        seen.add(entry["id"])
        out.append(entry)
    return out


def applicability(requirement, roles):
    """Applicability of one requirement to a product, as the union over roles."""
    entry = normalize_requirement(requirement)
    product_roles = normalize_product_roles(roles)
    if entry["category"] == "exclusive":
        hit = [r for r in product_roles if r in entry["product_types"]]
        applicable = bool(hit)
        reason = (
            "exclusive category names %s" % ", ".join(hit)
            if applicable
            else "exclusive category names none of the product roles"
        )
    else:
        remaining = [r for r in product_roles if r not in entry["excepted_types"]]
        applicable = bool(remaining)
        reason = (
            "inclusive category, roles %s not excepted" % ", ".join(remaining)
            if applicable
            else "inclusive category excepts every product role"
        )
    return {
        "id": entry["id"],
        "clause": entry["clause"],
        "category": entry["category"],
        "applicable": applicable,
        "reason": reason,
        "weight": entry["weight"],
    }


def tailoring_action(requirement, roles, decision):
    """Expected action for a recorded keep/delete decision."""
    if decision not in DECISIONS:
        raise ValueError(
            "tailoring decision %r unknown; expected one of %s" % (decision, list(DECISIONS))
        )
    verdict = applicability(requirement, roles)
    if verdict["applicable"]:
        return "keep" if decision == "keep" else "deviation-required"
    return "delete" if decision == "delete" else "keep"


def check_tailoring_record(requirement, roles, record):
    """Findings raised by one recorded tailoring decision."""
    if not isinstance(record, dict):
        raise ValueError("tailoring record must be a mapping, got %r" % (record,))
    verdict = applicability(requirement, roles)
    decision = record.get("decision")
    if decision not in DECISIONS:
        raise ValueError(
            "record for %s: decision %r unknown; expected one of %s"
            % (verdict["id"], decision, list(DECISIONS))
        )
    rationale = (record.get("rationale") or "").strip()
    deviation = (record.get("deviation_ref") or "").strip()
    action = tailoring_action(requirement, roles, decision)
    findings = []
    if action == "deviation-required" and not deviation:
        findings.append(
            "%s: applicable requirement deleted without an approved deviation reference"
            % verdict["id"]
        )
    if decision == "delete" and not verdict["applicable"] and not rationale:
        findings.append(
            "%s: deletion recorded without a rationale" % verdict["id"]
        )
    if decision == "keep" and not verdict["applicable"] and not rationale:
        findings.append(
            "%s: requirement kept although not applicable, with no rationale"
            % verdict["id"]
        )
    return {
        "id": verdict["id"],
        "applicable": verdict["applicable"],
        "decision": decision,
        "action": action,
        "findings": findings,
    }


def ratio_within_ceiling(ratio, ceiling):
    """True when a deleted-weight ratio sits at or under the agreed ceiling."""
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
        raise ValueError("ratio must be a real number, got %r" % (ratio,))
    if isinstance(ceiling, bool) or not isinstance(ceiling, (int, float)):
        raise ValueError("ceiling must be a real number, got %r" % (ceiling,))
    ratio = float(ratio)
    ceiling = float(ceiling)
    if not math.isfinite(ratio) or not 0.0 <= ratio <= 1.0:
        raise ValueError("ratio must lie in [0, 1], got %r" % (ratio,))
    if not math.isfinite(ceiling) or not 0.0 <= ceiling <= 1.0:
        raise ValueError("ceiling must lie in [0, 1], got %r" % (ceiling,))
    return ratio <= ceiling + RATIO_TOLERANCE


def build_matrix_column(catalogue, roles):
    """Applicability rows and counts for one product's matrix column."""
    entries = validate_catalogue(catalogue)
    product_roles = normalize_product_roles(roles)
    rows = [applicability(entry, product_roles) for entry in entries]
    applicable = [r for r in rows if r["applicable"]]
    return {
        "roles": product_roles,
        "rows": rows,
        "requirement_count": len(rows),
        "applicable_count": len(applicable),
        "not_applicable_count": len(rows) - len(applicable),
        "applicable_fraction": len(applicable) / float(len(rows)),
    }


def assess_inclusive_and_exclusive_category_use(
    catalogue, roles, records=None, deletion_ceiling=1.0
):
    """Top-level clause 8.2 tailoring assessment for one product."""
    column = build_matrix_column(catalogue, roles)
    entries = validate_catalogue(catalogue)
    by_id = {entry["id"]: entry for entry in entries}
    records = {} if records is None else records
    if not isinstance(records, dict):
        raise ValueError("records must be a mapping of requirement id -> record")
    for rid in records:
        if rid not in by_id:
            raise ValueError("record for unknown requirement id %r" % (rid,))

    findings = []
    decisions = []
    deleted_weight_terms = []
    for entry in entries:
        record = records.get(entry["id"])
        if record is None:
            row = next(r for r in column["rows"] if r["id"] == entry["id"])
            record = {"decision": "keep" if row["applicable"] else "delete"}
            if not row["applicable"]:
                record["rationale"] = row["reason"]
        checked = check_tailoring_record(entry, roles, record)
        decisions.append(checked)
        findings.extend(checked["findings"])
        if checked["decision"] == "delete":
            deleted_weight_terms.append(entry["weight"])

    total_weight = math.fsum(entry["weight"] for entry in entries)
    deleted_weight = math.fsum(deleted_weight_terms)
    ratio = deleted_weight / total_weight
    within = ratio_within_ceiling(ratio, deletion_ceiling)
    if not within:
        findings.append(
            "deleted weight ratio %.6f exceeds the agreed deletion-ceiling %.6f"
            % (ratio, deletion_ceiling)
        )
    return {
        "column": column,
        "decisions": decisions,
        "deleted_count": sum(1 for d in decisions if d["decision"] == "delete"),
        "kept_count": sum(1 for d in decisions if d["decision"] == "keep"),
        "deleted_weight_ratio": ratio,
        "within_deletion_ceiling": within,
        "findings": findings,
        "compliant": not findings,
    }
