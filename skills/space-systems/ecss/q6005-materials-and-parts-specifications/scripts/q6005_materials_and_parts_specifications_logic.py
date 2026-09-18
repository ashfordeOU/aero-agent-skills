"""Specification content for a material or piece part bought for a hybrid.

Anchor: ECSS-Q-ST-60-05C clause 9.3 (the documentation defining each material
and piece part procured for hybrid microcircuit construction). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the specification record and normalise its declared content keys to
   one canonical form, so punctuation cannot present the same item twice.
2. Build the applicable content set: the core items every procured item owes,
   plus the items the item's own category adds.
3. Test each applicable item for definedness, reading placeholders and empty
   values as undefined rather than declared.
4. Compute the completeness ratio over the applicable set alone, so a surplus
   item cannot raise the score and an inapplicable one cannot lower it.
5. Take the document's approval state: an issue, a dated approval and a named
   approver. An unapproved document defines nothing that binds a supplier.
6. Compare the specification issue with the issue the procurement order cites,
   because an order against a superseded issue buys the old definition.
7. Return released-for-procurement or hold per specification, with the findings
   named, and roll a set of specifications up into one procurement readiness.
"""

import datetime

__all__ = [
    "RATIO_TOLERANCE",
    "PLACEHOLDERS",
    "CORE_CONTENT",
    "CATEGORY_CONTENT",
    "ITEM_CATEGORIES",
    "RELEASED",
    "HOLD",
    "normalise_key",
    "is_defined",
    "required_content",
    "validate_specification",
    "undefined_content",
    "surplus_content",
    "completeness_ratio",
    "approval_state",
    "issue_alignment",
    "assess_specification",
    "assess_specification_set",
]

# Completeness is a quotient of small integers that lands exactly on one for a
# finished document. Comparisons absorb representation error here rather than
# by relaxing the release condition.
RATIO_TOLERANCE = 1e-9

# Text that occupies a field without defining it.
PLACEHOLDERS = (
    "tbd",
    "tbc",
    "tba",
    "to be defined",
    "to be advised",
    "to be confirmed",
    "n/a",
    "na",
    "none",
    "-",
    "--",
    "?",
    "xxx",
)

# Content every procured material or piece part owes, whatever it is.
CORE_CONTENT = (
    "item-designation",
    "manufacturer-and-site",
    "manufacturer-part-reference",
    "traceability-marking",
    "storage-conditions",
    "inspection-and-acceptance-criteria",
    "lot-documentation-required",
)

# Content a category adds on top of the core set.
CATEGORY_CONTENT = {
    "substrate": (
        "substrate-material-and-grade",
        "dimensional-tolerances",
        "metallization-system",
        "surface-finish",
    ),
    "adhesive": (
        "cure-schedule",
        "pot-life",
        "shelf-life",
        "outgassing-data",
        "filler-and-carrier",
    ),
    "bonding-wire": (
        "wire-diameter-and-tolerance",
        "wire-material-and-purity",
        "breaking-load-and-elongation",
        "spool-identification",
    ),
    "preform": (
        "preform-alloy-composition",
        "preform-dimensions-and-tolerance",
        "surface-condition",
    ),
    "package-and-lid": (
        "package-material-and-plating",
        "sealing-surface-condition",
        "lead-finish",
        "hermeticity-provisions",
    ),
    "sealing-material": (
        "cure-schedule",
        "shelf-life",
        "outgassing-data",
        "sealing-temperature-range",
    ),
    "piece-part": (
        "electrical-parameters",
        "dimensional-tolerances",
        "mounting-provisions",
    ),
}

ITEM_CATEGORIES = tuple(sorted(CATEGORY_CONTENT))

RELEASED = "released-for-procurement"
HOLD = "hold"


def _require_text(value, label):
    """Return value as a stripped non-empty string, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be blank" % label)
    return stripped


def normalise_key(key):
    """Return a content key in one canonical hyphenated lower-case form."""
    text = _require_text(key, "content key").lower()
    for character in ("_", " ", "."):
        text = text.replace(character, "-")
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-")


def is_defined(value):
    """Return whether a declared content value actually defines anything.

    A placeholder, an empty string, an empty collection and None alike define
    nothing. A number, including zero, does define something.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False
        return stripped.lower() not in PLACEHOLDERS
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return len(value) > 0
    return True


def required_content(category):
    """Return the applicable content set for a procured item category."""
    text = normalise_key(category)
    if text not in CATEGORY_CONTENT:
        raise ValueError("unrecognised procured item category %r" % (category,))
    return tuple(CORE_CONTENT) + tuple(CATEGORY_CONTENT[text])


def validate_specification(record):
    """Return a normalised specification record.

    The declared content is normalised key by key; two keys that normalise to
    the same item are an input error, because one of them is silently ignored
    otherwise and nobody finds out which.
    """
    if not isinstance(record, dict):
        raise ValueError("specification must be a mapping")
    for key in ("designation", "category", "content"):
        if key not in record:
            raise ValueError("specification missing required key '%s'" % key)
    designation = _require_text(record["designation"], "designation")
    category = normalise_key(record["category"])
    if category not in CATEGORY_CONTENT:
        raise ValueError("unrecognised procured item category %r" % (record["category"],))
    content = record["content"]
    if not isinstance(content, dict):
        raise ValueError("content must be a mapping of content item to value")
    normalised = {}
    for key, value in content.items():
        canonical = normalise_key(key)
        if canonical in normalised:
            raise ValueError("duplicate content item %r after normalisation" % canonical)
        normalised[canonical] = value
    issue = record.get("issue")
    if issue is not None:
        issue = _require_text(issue, "issue").upper()
    return {
        "designation": designation,
        "category": category,
        "content": normalised,
        "issue": issue,
        "approved_by": record.get("approved_by"),
        "approval_date": record.get("approval_date"),
        "order_cites_issue": record.get("order_cites_issue"),
    }


def undefined_content(record):
    """Return the applicable content items this specification leaves undefined."""
    normalised = validate_specification(record)
    applicable = required_content(normalised["category"])
    return [
        item
        for item in applicable
        if not is_defined(normalised["content"].get(item))
    ]


def surplus_content(record):
    """Return the declared content items that sit outside the applicable set."""
    normalised = validate_specification(record)
    applicable = set(required_content(normalised["category"]))
    return sorted(key for key in normalised["content"] if key not in applicable)


def completeness_ratio(record):
    """Return the defined fraction of the applicable content set."""
    normalised = validate_specification(record)
    applicable = required_content(normalised["category"])
    defined = sum(1 for item in applicable if is_defined(normalised["content"].get(item)))
    return defined / float(len(applicable))


def approval_state(record):
    """Return the approval standing of the specification document.

    A document is approved only with an issue, a named approver and a real
    calendar approval date; each absence is reported by name.
    """
    normalised = validate_specification(record)
    findings = []
    if normalised["issue"] is None or not is_defined(normalised["issue"]):
        findings.append("specification carries no issue identifier")
    approver = normalised["approved_by"]
    if approver is not None and not isinstance(approver, str):
        raise ValueError("approved_by must be a string or None")
    if not is_defined(approver):
        findings.append("specification carries no named approver")
    date_text = normalised["approval_date"]
    approval_date = None
    if is_defined(date_text):
        if not isinstance(date_text, str):
            raise ValueError("approval_date must be an ISO date string or None")
        try:
            approval_date = datetime.date.fromisoformat(date_text.strip())
        except ValueError:
            raise ValueError("approval_date %r is not an ISO calendar date" % (date_text,))
    else:
        findings.append("specification carries no approval date")
    return {
        "issue": normalised["issue"],
        "approved_by": approver if is_defined(approver) else None,
        "approval_date": approval_date.isoformat() if approval_date else None,
        "approved": not findings,
        "findings": findings,
    }


def issue_alignment(record):
    """Return whether the order cites the issue this specification carries.

    An order citing nothing is a reservation: it will be filled against
    whichever issue the supplier holds. An order citing an earlier issue buys
    the superseded definition, which is a harder finding.
    """
    normalised = validate_specification(record)
    cited = normalised["order_cites_issue"]
    if cited is not None and not isinstance(cited, str):
        raise ValueError("order_cites_issue must be a string or None")
    issue = normalised["issue"]
    if not is_defined(cited):
        return {"cited_issue": None, "aligned": False, "finding": "the procurement order cites no specification issue"}
    cited_text = cited.strip().upper()
    if issue is None:
        return {
            "cited_issue": cited_text,
            "aligned": False,
            "finding": "the order cites issue %s but the specification carries none" % cited_text,
        }
    if cited_text != issue:
        return {
            "cited_issue": cited_text,
            "aligned": False,
            "finding": "the order cites issue %s against specification issue %s"
            % (cited_text, issue),
        }
    return {"cited_issue": cited_text, "aligned": True, "finding": None}


def assess_specification(record):
    """Run the full clause 9.3 assessment of one procurement specification.

    record keys: designation, category, content, optional issue, approved_by,
    approval_date and order_cites_issue.
    """
    normalised = validate_specification(record)
    applicable = required_content(normalised["category"])
    undefined = undefined_content(record)
    surplus = surplus_content(record)
    ratio = completeness_ratio(record)
    approval = approval_state(record)
    alignment = issue_alignment(record)

    findings = []
    if undefined:
        findings.append(
            "%d applicable content item(s) undefined: %s"
            % (len(undefined), ", ".join(undefined))
        )
    findings.extend(approval["findings"])
    if alignment["finding"] is not None:
        findings.append(alignment["finding"])
    complete = not undefined
    status = RELEASED if complete and approval["approved"] and alignment["aligned"] else HOLD
    return {
        "designation": normalised["designation"],
        "category": normalised["category"],
        "applicable_count": len(applicable),
        "undefined_content": undefined,
        "surplus_content": surplus,
        "completeness_ratio": ratio,
        "content_complete": complete,
        "approved": approval["approved"],
        "issue": normalised["issue"],
        "cited_issue": alignment["cited_issue"],
        "issue_aligned": alignment["aligned"],
        "status": status,
        "findings": findings,
    }


def assess_specification_set(records):
    """Roll a set of procurement specifications up into one readiness view."""
    if isinstance(records, dict) or not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of specification records")
    if not records:
        raise ValueError("specification set is empty")
    verdicts = [assess_specification(record) for record in records]
    seen = set()
    for verdict in verdicts:
        key = verdict["designation"].lower()
        if key in seen:
            raise ValueError("duplicate specification designation %r" % verdict["designation"])
        seen.add(key)
    held = [v["designation"] for v in verdicts if v["status"] == HOLD]
    mean_ratio = sum(v["completeness_ratio"] for v in verdicts) / float(len(verdicts))
    return {
        "specification_count": len(verdicts),
        "specifications": verdicts,
        "held": held,
        "released": [v["designation"] for v in verdicts if v["status"] == RELEASED],
        "mean_completeness_ratio": mean_ratio,
        "ready_to_procure": not held,
    }
