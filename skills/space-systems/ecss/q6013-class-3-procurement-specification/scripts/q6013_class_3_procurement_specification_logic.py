"""Purchase-specification content assessment for lowest-assurance EEE orders.

Anchor: ECSS-Q-ST-60-13C clause 6.3.2 (the purchase specification governing an
order for commercial electrical, electronic and electromechanical parts bought
at the lowest assurance class). Paraphrased into an implementable procedure; no
standard text is reproduced.

At this class the purchase specification is allowed to be thin, and part of
what an order rests on may sit in the manufacturer's published data sheet or in
the order text itself. The question is therefore not how long the specification
is, but whether every item the class still requires is traceable to a carrier
the class permits for that item, at a fixed and citable location.

Procedure implemented here
--------------------------
1. Validate the completeness policy: the floor the content completeness has to
   reach.
2. Validate the specification header where one is declared -- identifier,
   issue and approving authority -- because an unissued document cannot be
   invoked on an order.
3. Validate every content declaration: the item, the carrier it sits in, the
   location inside that carrier, and, for a data-sheet carrier, the citation.
4. Grade each required item against the carriers the class permits for it.
   Three items may never rest on the data sheet alone, because the data sheet
   is a document the project does not control and the manufacturer may reissue.
5. Refuse a data-sheet citation that names no document issue, a specification
   carrier with no identified specification behind it, and a declaration that
   cites no location inside its carrier.
6. Report a declaration naming an item the class does not require.
7. Take the content completeness against the floor under a named tolerance and
   report the share of covered items resting on the data sheet.
8. Close on one verdict carrying every finding.
"""

import math

__all__ = [
    "CARRIERS",
    "PROJECT_CONTROLLED_CARRIERS",
    "REQUIRED_CONTENT",
    "COMPLETENESS_TOLERANCE",
    "validate_completeness_policy",
    "validate_specification_header",
    "permitted_carriers",
    "validate_content_declaration",
    "collect_content",
    "grade_content_item",
    "completeness_figures",
    "assess_class3_specification",
]

# Where a required item may physically sit.
CARRIERS = (
    "purchase-specification",
    "manufacturer-data-sheet",
    "order-text",
)

# The carriers the project itself controls and can freeze at the order date.
PROJECT_CONTROLLED_CARRIERS = (
    "purchase-specification",
    "order-text",
)

# The content an order still has to carry at this class, with the carriers the
# class permits for each item. The items restricted to the project-controlled
# carriers are the ones a reissued data sheet would silently rewrite.
REQUIRED_CONTENT = (
    ("manufacturer-part-number-and-variant", CARRIERS),
    ("electrical-parameter-limits",
     ("purchase-specification", "manufacturer-data-sheet")),
    ("ordered-operating-temperature-range", PROJECT_CONTROLLED_CARRIERS),
    ("acceptance-route-for-the-delivery", PROJECT_CONTROLLED_CARRIERS),
    ("marking-and-lot-traceability-requirement", PROJECT_CONTROLLED_CARRIERS),
    ("packaging-and-esd-protection-requirement", CARRIERS),
    ("storage-condition-or-shelf-life", CARRIERS),
    ("nonconformance-notification-requirement", PROJECT_CONTROLLED_CARRIERS),
)

# Completeness is a ratio of small integers; a figure landing exactly on the
# floor must not fail on representation alone.
COMPLETENESS_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _normalize_token(value, label):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def _optional_text(value, label):
    """Return a stripped optional text field, raising on a non-string."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("%s must be a string or None, got %r" % (label, value))
    return value.strip()


def validate_completeness_policy(policy):
    """Return the validated content-completeness policy for the order."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    if "completeness_floor" not in policy:
        raise ValueError("policy missing required key 'completeness_floor'")
    value = policy["completeness_floor"]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("completeness_floor must be a real number, got %r" % (value,))
    floor = float(value)
    if not math.isfinite(floor):
        raise ValueError("completeness_floor must be finite")
    if floor <= 0.0 or floor > 1.0:
        raise ValueError(
            "completeness_floor must lie in (0, 1]; a floor of nothing accepts "
            "an order documented by nothing at all"
        )
    return {"completeness_floor": floor}


def validate_specification_header(header):
    """Return the validated specification header, or None when none is declared.

    A specification with no issue cannot be invoked on an order, because nobody
    can later say which text the delivery was bought under.
    """
    if header is None:
        return None
    if not isinstance(header, dict):
        raise ValueError("specification header must be a mapping or None")
    identifier = _optional_text(header.get("identifier"), "identifier")
    issue = _optional_text(header.get("issue"), "issue")
    authority = _optional_text(header.get("approving_authority"), "approving_authority")
    missing = [
        label
        for label, field in (
            ("identifier", identifier),
            ("issue", issue),
            ("approving_authority", authority),
        )
        if not field
    ]
    return {
        "identifier": identifier,
        "issue": issue,
        "approving_authority": authority,
        "missing": missing,
        "identified": not missing,
    }


def permitted_carriers(item):
    """Return the carriers the class permits for one required content item."""
    token = _normalize_token(item, "content item")
    for name, carriers in REQUIRED_CONTENT:
        if name == token:
            return tuple(carriers)
    raise ValueError("content item '%s' is not a required item at this class" % token)


def validate_content_declaration(declaration):
    """Return one validated declaration of where a required item is carried."""
    if not isinstance(declaration, dict):
        raise ValueError("each declaration must be a mapping")
    for key in ("item", "carrier"):
        if key not in declaration:
            raise ValueError("declaration missing required key '%s'" % key)
    item = _normalize_token(declaration["item"], "item")
    carrier = _normalize_token(declaration["carrier"], "carrier")
    if carrier not in CARRIERS:
        raise ValueError(
            "carrier '%s' is not recognized; expected one of %s"
            % (carrier, ", ".join(CARRIERS))
        )
    location = _optional_text(declaration.get("location"), "location")
    citation = declaration.get("citation")
    if citation is None:
        cited = {"document": "", "issue": ""}
    elif isinstance(citation, dict):
        cited = {
            "document": _optional_text(citation.get("document"), "citation document"),
            "issue": _optional_text(citation.get("issue"), "citation issue"),
        }
    else:
        raise ValueError(
            "citation for item '%s' must be a mapping or None" % item
        )
    return {
        "item": item,
        "carrier": carrier,
        "location": location,
        "citation": cited,
        "citation_locked": bool(cited["document"] and cited["issue"]),
    }


def collect_content(declarations):
    """Return the validated declarations keyed by item, rejecting a repeat."""
    if not isinstance(declarations, (list, tuple)):
        raise ValueError("declarations must be a sequence")
    collected = {}
    for declaration in declarations:
        record = validate_content_declaration(declaration)
        if record["item"] in collected:
            raise ValueError("content item '%s' is declared twice" % record["item"])
        collected[record["item"]] = record
    return collected


def grade_content_item(item, declaration, header):
    """Return the graded state of one required content item."""
    name = _normalize_token(item, "content item")
    allowed = permitted_carriers(name)
    if declaration is None:
        return {
            "item": name,
            "carrier": None,
            "state": "absent",
            "reason": "no carrier declared for a required item",
            "covered": False,
        }
    if not isinstance(declaration, dict) or "carrier" not in declaration:
        raise ValueError("declaration for '%s' must be a validated mapping" % name)
    carrier = declaration["carrier"]
    if carrier not in allowed:
        return {
            "item": name,
            "carrier": carrier,
            "state": "carrier-not-permitted",
            "reason": "'%s' may not rest on the %s at this class" % (name, carrier),
            "covered": False,
        }
    if carrier == "manufacturer-data-sheet" and not declaration["citation_locked"]:
        return {
            "item": name,
            "carrier": carrier,
            "state": "citation-not-locked",
            "reason": "the data-sheet citation names no document and issue",
            "covered": False,
        }
    if carrier == "purchase-specification" and (header is None or not header["identified"]):
        missing = "no specification declared" if header is None else \
            "specification missing %s" % ", ".join(header["missing"])
        return {
            "item": name,
            "carrier": carrier,
            "state": "carrier-not-identified",
            "reason": missing,
            "covered": False,
        }
    if not declaration["location"]:
        return {
            "item": name,
            "carrier": carrier,
            "state": "location-not-cited",
            "reason": "no location cited inside the %s" % carrier,
            "covered": False,
        }
    return {
        "item": name,
        "carrier": carrier,
        "state": "covered",
        "reason": None,
        "covered": True,
    }


def completeness_figures(graded):
    """Return the content completeness and the data-sheet share of it."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("graded must be a non-empty sequence of graded items")
    total = len(graded)
    covered = 0
    on_data_sheet = 0
    for entry in graded:
        if not isinstance(entry, dict) or "state" not in entry:
            raise ValueError("each graded item must be a mapping with a state")
        if entry["covered"]:
            covered += 1
            if entry["carrier"] == "manufacturer-data-sheet":
                on_data_sheet += 1
    return {
        "required_items": total,
        "covered_items": covered,
        "completeness": covered / total,
        "data_sheet_items": on_data_sheet,
        "data_sheet_share": (on_data_sheet / covered) if covered else 0.0,
    }


def assess_class3_specification(case):
    """Run the full clause 6.3.2 content assessment for a class 3 order.

    case keys: policy, specification, content.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("policy", "specification", "content"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)

    policy = validate_completeness_policy(case["policy"])
    header = validate_specification_header(case["specification"])
    collected = collect_content(case["content"])

    required_names = [name for name, _ in REQUIRED_CONTENT]
    graded = [
        grade_content_item(name, collected.get(name), header) for name in required_names
    ]
    figures = completeness_figures(graded)

    not_permitted = [e for e in graded if e["state"] == "carrier-not-permitted"]
    absent = [e for e in graded if e["state"] == "absent"]
    untraceable = [
        e
        for e in graded
        if e["state"] in ("citation-not-locked", "carrier-not-identified",
                          "location-not-cited")
    ]

    findings = []
    for entry in not_permitted:
        findings.append("content item '%s' is misplaced: %s" % (entry["item"], entry["reason"]))
    for entry in absent:
        findings.append("content item '%s' is absent: %s" % (entry["item"], entry["reason"]))
    for entry in untraceable:
        findings.append(
            "content item '%s' is not traceable: %s" % (entry["item"], entry["reason"])
        )

    extraneous = [name for name in collected if name not in required_names]
    for name in sorted(extraneous):
        findings.append(
            "declaration names item '%s', which is not required content at this class"
            % name
        )

    short = figures["completeness"] < policy["completeness_floor"] and not math.isclose(
        figures["completeness"],
        policy["completeness_floor"],
        rel_tol=0.0,
        abs_tol=COMPLETENESS_TOLERANCE,
    )
    if short:
        findings.append(
            "content completeness %.3f is below the declared floor %.3f"
            % (figures["completeness"], policy["completeness_floor"])
        )

    if not collected:
        verdict = "order documentation not declared"
    elif not_permitted:
        verdict = "required content carried where the class does not permit it"
    elif absent:
        verdict = "required content absent"
    elif untraceable:
        verdict = "required content not traceable to an identified carrier"
    elif short:
        verdict = "content completeness below the declared floor"
    else:
        verdict = "order documentation meets class 3 expectations"

    return {
        "policy": policy,
        "specification": header,
        "graded": graded,
        "misplaced_items": [e["item"] for e in not_permitted],
        "absent_items": [e["item"] for e in absent],
        "untraceable_items": [e["item"] for e in untraceable],
        "extraneous_declarations": sorted(extraneous),
        "figures": figures,
        "verdict": verdict,
        "acceptable": verdict == "order documentation meets class 3 expectations",
        "findings": findings,
    }
