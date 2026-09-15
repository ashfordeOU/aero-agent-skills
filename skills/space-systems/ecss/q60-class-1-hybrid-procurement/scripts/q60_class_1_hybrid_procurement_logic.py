"""Purchasing a class 1 hybrid microcircuit against its applicable specifications.

Anchor: ECSS-Q-ST-60C clause 4.6.3 (a class 1 hybrid microcircuit is bought
against the specifications the standard lists for it). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Select the generic specification family that belongs to the hybrid's
   construction: thick film, thin film, multichip module or microwave.
2. Check the purchase package cites that family, at an issue that has not been
   superseded, with a detail specification behind it where one is required.
3. Test the supplier against the approval list for that family, and against
   the week its approval lapses relative to the order week.
4. Check every constituent element inside the hybrid - die, chip elements and
   substrate - carries a specification of its own.
5. Return one verdict naming the first thing that stops the order, together
   with the coverage of the constituent elements.
"""

__all__ = [
    "WEEKS_PER_YEAR",
    "SPECIFICATION_CATALOGUE",
    "DEFAULT_PROCUREMENT_POLICY",
    "PROCUREMENT_SPECIFICATION_COMPLETE",
    "SPECIFICATION_FAMILY_MISMATCH",
    "SPECIFICATION_ISSUE_SUPERSEDED",
    "DETAIL_SPECIFICATION_MISSING",
    "SUPPLIER_NOT_APPROVED",
    "ELEMENT_SPECIFICATION_GAP",
    "validate_procurement_policy",
    "parse_week_code",
    "week_index",
    "select_specification_family",
    "validate_package",
    "validate_elements",
    "check_specification_citation",
    "supplier_approval_status",
    "uncovered_elements",
    "element_specification_coverage",
    "assess_hybrid_procurement",
]

WEEKS_PER_YEAR = 52

PROCUREMENT_SPECIFICATION_COMPLETE = "procurement-specification-complete"
SPECIFICATION_FAMILY_MISMATCH = "specification-family-mismatch"
SPECIFICATION_ISSUE_SUPERSEDED = "specification-issue-superseded"
DETAIL_SPECIFICATION_MISSING = "detail-specification-missing"
SUPPLIER_NOT_APPROVED = "supplier-not-approved"
ELEMENT_SPECIFICATION_GAP = "constituent-element-specification-gap"

# The generic specification families the standard lists, keyed by the
# construction of the hybrid. Each carries the lowest issue still admitted and
# the constituent element kinds that must themselves be procured to a
# specification.
SPECIFICATION_CATALOGUE = {
    "thick-film": {
        "generic_family": "hybrid-thick-film-generic",
        "current_issue": 4,
        "detail_specification_required": True,
        "element_kinds": ("die", "chip-resistor", "chip-capacitor", "substrate"),
    },
    "thin-film": {
        "generic_family": "hybrid-thin-film-generic",
        "current_issue": 3,
        "detail_specification_required": True,
        "element_kinds": ("die", "chip-capacitor", "substrate"),
    },
    "multichip-module": {
        "generic_family": "multichip-module-generic",
        "current_issue": 2,
        "detail_specification_required": True,
        "element_kinds": ("die", "substrate"),
    },
    "microwave-hybrid": {
        "generic_family": "microwave-hybrid-generic",
        "current_issue": 2,
        "detail_specification_required": False,
        "element_kinds": ("die", "substrate"),
    },
}

DEFAULT_PROCUREMENT_POLICY = {
    # Whether an issue below the current one may still be ordered against.
    "allow_superseded_issue": False,
    # Whether a supplier whose approval lapses in the order week is still
    # approved for that week.
    "approval_valid_through_expiry_week": True,
    # Whether every constituent element kind must be covered by a
    # specification of its own.
    "require_element_specifications": True,
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_procurement_policy(policy=None):
    """Return a complete procurement policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_PROCUREMENT_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("procurement policy must be a mapping")
    merged = dict(DEFAULT_PROCUREMENT_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_PROCUREMENT_POLICY:
            raise ValueError("unknown procurement policy key %r" % (key,))
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean" % key)
        merged[key] = value
    return merged


def parse_week_code(code):
    """Return the (year, week) pair a four-digit YYWW code carries."""
    if not isinstance(code, str):
        raise ValueError("week code must be a four-digit string, got %r" % (code,))
    text = code.strip()
    if len(text) != 4 or not text.isdigit():
        raise ValueError("week code must read YYWW, got %r" % (code,))
    year = int(text[:2])
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("week code week must lie in 01..53, got %r" % (code,))
    return (year, week)


def week_index(code):
    """Return a monotone integer week index for a YYWW code."""
    year, week = parse_week_code(code)
    return year * WEEKS_PER_YEAR + (week - 1)


def _ordered_week_pair(first, second):
    """Return two week indices, refusing a pair that straddles a century."""
    left_year = parse_week_code(first)[0]
    right_year = parse_week_code(second)[0]
    if (left_year >= 90 and right_year <= 9) or (right_year >= 90 and left_year <= 9):
        raise ValueError(
            "week codes straddle a century rollover; they cannot be ordered "
            "from two-digit years alone"
        )
    return week_index(first), week_index(second)


def select_specification_family(hybrid_type):
    """Return the catalogue entry that governs this hybrid construction."""
    if not isinstance(hybrid_type, str) or not hybrid_type.strip():
        raise ValueError("hybrid_type must be a non-empty string")
    key = hybrid_type.strip().lower()
    if key not in SPECIFICATION_CATALOGUE:
        raise ValueError(
            "no listed specification family for hybrid construction %r; the "
            "applicable specification cannot be selected" % (hybrid_type,)
        )
    entry = dict(SPECIFICATION_CATALOGUE[key])
    entry["hybrid_type"] = key
    return entry


def validate_package(package):
    """Return a normalised purchase package record."""
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    family = package.get("cited_family")
    if not isinstance(family, str) or not family.strip():
        raise ValueError("the purchase package cites no specification family")
    issue = package.get("cited_issue")
    if not _is_int(issue) or issue <= 0:
        raise ValueError("cited_issue must be a positive integer, got %r" % (issue,))
    supplier = package.get("supplier")
    if not isinstance(supplier, str) or not supplier.strip():
        raise ValueError("the purchase package names no supplier")
    detail = package.get("detail_specification")
    if detail is not None:
        if not isinstance(detail, str) or not detail.strip():
            raise ValueError("detail_specification must be a non-empty reference or absent")
        detail = detail.strip()
    order_week = package.get("order_week")
    week_index(order_week)
    return {
        "cited_family": family.strip(),
        "cited_issue": issue,
        "detail_specification": detail,
        "supplier": supplier.strip(),
        "order_week": order_week.strip(),
    }


def validate_elements(elements):
    """Return the normalised constituent element records of the hybrid."""
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a sequence of element records")
    records = []
    for element in elements:
        if not isinstance(element, dict):
            raise ValueError("each element must be a mapping")
        kind = element.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("each constituent element needs a non-empty 'kind'")
        specification = element.get("specification")
        if specification is not None:
            if not isinstance(specification, str) or not specification.strip():
                raise ValueError(
                    "element %r carries a blank specification reference" % (kind.strip(),)
                )
            specification = specification.strip()
        records.append({"kind": kind.strip().lower(), "specification": specification})
    return records


def check_specification_citation(entry, package):
    """Return the citation findings for a package against its catalogue entry."""
    if not isinstance(entry, dict) or "generic_family" not in entry:
        raise ValueError("entry must be a catalogue entry")
    record = package if "cited_family" in package else validate_package(package)
    findings = []
    mismatch = record["cited_family"] != entry["generic_family"]
    if mismatch:
        findings.append(
            "the order cites %s where a %s hybrid is bought against %s"
            % (record["cited_family"], entry["hybrid_type"], entry["generic_family"])
        )
    superseded = record["cited_issue"] < entry["current_issue"]
    if superseded:
        findings.append(
            "issue %d of %s is superseded by issue %d"
            % (record["cited_issue"], entry["generic_family"], entry["current_issue"])
        )
    detail_missing = (
        entry["detail_specification_required"] and record["detail_specification"] is None
    )
    if detail_missing:
        findings.append(
            "%s is a generic family; the part itself needs a detail specification"
            % entry["generic_family"]
        )
    return {
        "family_mismatch": mismatch,
        "issue_superseded": superseded,
        "detail_specification_missing": detail_missing,
        "findings": findings,
    }


def supplier_approval_status(approvals, supplier, generic_family, order_week, policy=None):
    """Return whether the supplier is approved for this family at the order week."""
    settings = validate_procurement_policy(policy)
    if not isinstance(approvals, dict):
        raise ValueError("approvals must be a mapping of supplier to approval record")
    if not isinstance(supplier, str) or not supplier.strip():
        raise ValueError("supplier must be a non-empty string")
    name = supplier.strip()
    record = approvals.get(name)
    if record is None:
        return {"approved": False, "reason": "supplier-not-on-approval-list",
                "weeks_remaining": None}
    if not isinstance(record, dict):
        raise ValueError("the approval record for %r must be a mapping" % (name,))
    families = record.get("families")
    if not isinstance(families, (list, tuple)) or not families:
        raise ValueError("the approval record for %r lists no families" % (name,))
    if generic_family not in families:
        return {"approved": False, "reason": "family-outside-supplier-approval",
                "weeks_remaining": None}
    expiry = record.get("approval_expiry_week")
    ordered, expires = _ordered_week_pair(order_week, expiry)
    remaining = expires - ordered
    if remaining > 0:
        return {"approved": True, "reason": "approved", "weeks_remaining": remaining}
    if remaining == 0 and settings["approval_valid_through_expiry_week"]:
        return {"approved": True, "reason": "approved-through-expiry-week",
                "weeks_remaining": 0}
    return {"approved": False, "reason": "supplier-approval-lapsed",
            "weeks_remaining": remaining}


def uncovered_elements(entry, records):
    """Return the element kinds the hybrid needs but has no specification for."""
    if not isinstance(entry, dict) or "element_kinds" not in entry:
        raise ValueError("entry must be a catalogue entry")
    present = {}
    for record in records:
        kind = record["kind"]
        covered = record["specification"] is not None
        present[kind] = present.get(kind, True) and covered
    gaps = []
    for kind in entry["element_kinds"]:
        if kind not in present:
            gaps.append(kind)
        elif not present[kind]:
            gaps.append(kind)
    return gaps


def element_specification_coverage(entry, records):
    """Return the share of the required element kinds that carry a specification."""
    if not isinstance(entry, dict) or "element_kinds" not in entry:
        raise ValueError("entry must be a catalogue entry")
    required = entry["element_kinds"]
    if not required:
        raise ValueError("the catalogue entry lists no constituent element kinds")
    gaps = uncovered_elements(entry, records)
    return float(len(required) - len(gaps)) / float(len(required))


def assess_hybrid_procurement(case):
    """Run the clause 4.6.3 procurement check over a hybrid purchase.

    case keys: hybrid_type, package (purchase package record), optional
    elements, optional approvals, optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("hybrid_type", "package"):
        if key not in case:
            raise ValueError("case missing required key %r" % (key,))
    settings = validate_procurement_policy(case.get("policy"))
    entry = select_specification_family(case["hybrid_type"])
    package = validate_package(case["package"])
    records = validate_elements(case.get("elements") or [])
    citation = check_specification_citation(entry, package)
    approval = supplier_approval_status(
        case.get("approvals") or {},
        package["supplier"],
        entry["generic_family"],
        package["order_week"],
        settings,
    )
    gaps = uncovered_elements(entry, records) if settings["require_element_specifications"] else []
    coverage = element_specification_coverage(entry, records)

    findings = list(citation["findings"])
    if not approval["approved"]:
        findings.append(
            "supplier %s: %s" % (package["supplier"], approval["reason"].replace("-", " "))
        )
    for kind in gaps:
        findings.append(
            "constituent %s carries no specification of its own" % kind
        )

    if citation["family_mismatch"]:
        verdict = SPECIFICATION_FAMILY_MISMATCH
    elif citation["issue_superseded"] and not settings["allow_superseded_issue"]:
        verdict = SPECIFICATION_ISSUE_SUPERSEDED
    elif citation["detail_specification_missing"]:
        verdict = DETAIL_SPECIFICATION_MISSING
    elif not approval["approved"]:
        verdict = SUPPLIER_NOT_APPROVED
    elif gaps:
        verdict = ELEMENT_SPECIFICATION_GAP
    else:
        verdict = PROCUREMENT_SPECIFICATION_COMPLETE

    return {
        "verdict": verdict,
        "hybrid_type": entry["hybrid_type"],
        "applicable_generic_family": entry["generic_family"],
        "current_issue": entry["current_issue"],
        "cited_family": package["cited_family"],
        "cited_issue": package["cited_issue"],
        "detail_specification": package["detail_specification"],
        "supplier": package["supplier"],
        "supplier_approved": approval["approved"],
        "supplier_approval_reason": approval["reason"],
        "approval_weeks_remaining": approval["weeks_remaining"],
        "uncovered_element_kinds": gaps,
        "element_specification_coverage": coverage,
        "orderable": verdict == PROCUREMENT_SPECIFICATION_COMPLETE,
        "findings": findings,
    }
