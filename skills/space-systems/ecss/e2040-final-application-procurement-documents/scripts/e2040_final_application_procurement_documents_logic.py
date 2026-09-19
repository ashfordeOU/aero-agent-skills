"""Release check for the final device application and procurement documents.

Anchor: ECSS-E-ST-20-40C clause 5.8.5 (validation, qualification and
acceptance phase -- issuing the closing versions of the documents used to
apply and to procure the device). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve which documents the closing set owes from the procurement route:
   a part going through formal evaluation owes a detail specification, an IP
   core delivered under licence owes a licence and delivery specification
   instead, and neither owes the other's paperwork.
2. Check each owed document is present, at final issue and approved.
3. Compare each revision with the one issued at the previous phase. A
   closing document that reissues the same revision has changed content
   without saying so, which is the defect this step exists to catch.
4. Check every document in the set names the same delivered device
   configuration, since the set is what a user applies and procures one
   article from.
5. Report the application and procurement halves separately and return a
   release decision.
"""

__all__ = [
    "DISPOSITIONS",
    "DOCUMENT_APPLICABILITY",
    "DOCUMENT_ROLE",
    "ISSUE_STATES",
    "ROLES",
    "ROUTES",
    "validate_route",
    "owed_documents",
    "parse_revision",
    "compare_revisions",
    "validate_document",
    "assess_documents",
    "role_completeness",
    "assess_final_application_procurement_documents",
]

ROUTES = ("escc-evaluation", "customer-procurement", "ip-core-licence")

ISSUE_STATES = ("draft", "interim", "final")

ROLES = ("application", "procurement")

# Which closing documents each procurement route owes.
DOCUMENT_APPLICABILITY = {
    "device-data-sheet": ("escc-evaluation", "customer-procurement", "ip-core-licence"),
    "device-user-manual": ("escc-evaluation", "customer-procurement", "ip-core-licence"),
    "declared-limitations-list": (
        "escc-evaluation",
        "customer-procurement",
        "ip-core-licence",
    ),
    "device-database": ("escc-evaluation", "customer-procurement", "ip-core-licence"),
    "escc-detail-specification": ("escc-evaluation",),
    "procurement-specification": ("escc-evaluation", "customer-procurement"),
    "licence-and-delivery-specification": ("ip-core-licence",),
}

# Whether a document is used to apply the device or to procure it.
DOCUMENT_ROLE = {
    "device-data-sheet": "application",
    "device-user-manual": "application",
    "declared-limitations-list": "application",
    "device-database": "application",
    "escc-detail-specification": "procurement",
    "procurement-specification": "procurement",
    "licence-and-delivery-specification": "procurement",
}

DISPOSITIONS = ("released", "release-blocked")


def _text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be empty" % label)
    return stripped


def validate_route(route):
    """Return the normalised procurement route."""
    text = _text(route, "procurement route").lower()
    if text not in ROUTES:
        raise ValueError("procurement route %r is not one of %s" % (route, ", ".join(ROUTES)))
    return text


def owed_documents(route):
    """Return the sorted closing documents this route owes."""
    normalised = validate_route(route)
    return sorted(
        name for name, routes in DOCUMENT_APPLICABILITY.items() if normalised in routes
    )


def parse_revision(revision):
    """Return a dotted numeric revision as a tuple of integers.

    Already-parsed revisions pass through unchanged, so the comparison can be
    handed either the raw field or a normalised record.
    """
    if isinstance(revision, tuple):
        if not revision:
            raise ValueError("revision tuple must not be empty")
        for part in revision:
            if not isinstance(part, int) or isinstance(part, bool) or part < 0:
                raise ValueError(
                    "revision tuple must hold non-negative integers, got %r" % (revision,)
                )
        return revision
    if isinstance(revision, int) and not isinstance(revision, bool):
        if revision < 0:
            raise ValueError("revision must not be negative, got %r" % (revision,))
        return (revision,)
    text = _text(revision, "revision")
    parts = text.split(".")
    if any(part == "" for part in parts):
        raise ValueError("revision %r has an empty segment" % (revision,))
    numbers = []
    for part in parts:
        if not part.isdigit():
            raise ValueError(
                "revision %r has a non-numeric segment %r; dotted numeric revisions only"
                % (revision, part)
            )
        numbers.append(int(part))
    return tuple(numbers)


def compare_revisions(left, right):
    """Return -1, 0 or 1 comparing two dotted numeric revisions."""
    a = parse_revision(left)
    b = parse_revision(right)
    width = max(len(a), len(b))
    a = a + (0,) * (width - len(a))
    b = b + (0,) * (width - len(b))
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def validate_document(record):
    """Return a normalised closing-document record."""
    if not isinstance(record, dict):
        raise ValueError("document record must be a mapping, got %r" % (record,))
    name = _text(record.get("name"), "document name").lower()
    if name not in DOCUMENT_APPLICABILITY:
        raise ValueError(
            "document %r is not a closing application or procurement document; "
            "expected one of %s" % (name, ", ".join(sorted(DOCUMENT_APPLICABILITY)))
        )
    issue = _text(record.get("issue"), "document %s issue" % name).lower()
    if issue not in ISSUE_STATES:
        raise ValueError(
            "document %s issue %r is not one of %s" % (name, issue, ", ".join(ISSUE_STATES))
        )
    revision = parse_revision(record.get("revision"))
    previous = record.get("previous_revision")
    previous_parsed = None if previous is None else parse_revision(previous)
    configuration = _text(record.get("configuration_id"), "document %s configuration_id" % name)
    approved = record.get("approved", False)
    if not isinstance(approved, bool):
        raise ValueError("document %s approved must be a boolean" % name)
    return {
        "name": name,
        "role": DOCUMENT_ROLE[name],
        "issue": issue,
        "revision": revision,
        "previous_revision": previous_parsed,
        "configuration_id": configuration,
        "approved": approved,
    }


def assess_documents(documents, route, delivered_configuration_id):
    """Return the presence, issue, revision and configuration picture."""
    normalised = validate_route(route)
    delivered = _text(delivered_configuration_id, "delivered_configuration_id")
    if not isinstance(documents, (list, tuple)):
        raise ValueError("documents must be a sequence")
    checked = [validate_document(item) for item in documents]
    names = [d["name"] for d in checked]
    if len(set(names)) != len(names):
        raise ValueError("the same document is issued twice in the closing set")
    present = {d["name"]: d for d in checked}
    owed = owed_documents(normalised)
    missing = sorted(name for name in owed if name not in present)
    not_owed = sorted(name for name in present if name not in owed)
    not_final = sorted(
        name for name in owed if name in present and present[name]["issue"] != "final"
    )
    unapproved = sorted(
        name for name in owed if name in present and not present[name]["approved"]
    )
    unadvanced = []
    regressed = []
    for name in owed:
        record = present.get(name)
        if record is None or record["previous_revision"] is None:
            continue
        order = compare_revisions(record["revision"], record["previous_revision"])
        if order == 0:
            unadvanced.append(name)
        elif order < 0:
            regressed.append(name)
    wrong_article = sorted(
        name
        for name in owed
        if name in present and present[name]["configuration_id"] != delivered
    )
    clean = (
        len(owed)
        - len(set(missing) | set(not_final) | set(unapproved) | set(unadvanced)
              | set(regressed) | set(wrong_article))
    )
    return {
        "route": normalised,
        "owed": owed,
        "present": present,
        "missing": missing,
        "issued_but_not_owed": not_owed,
        "not_at_final_issue": not_final,
        "unapproved": unapproved,
        "revision_not_advanced": sorted(unadvanced),
        "revision_regressed": sorted(regressed),
        "wrong_article": wrong_article,
        "release_fraction": clean / float(len(owed)),
    }


def role_completeness(document_report, role):
    """Return the owed and clean counts for the application or procurement half."""
    if not isinstance(document_report, dict) or "owed" not in document_report:
        raise ValueError("document_report must be the mapping returned by assess_documents")
    name = _text(role, "role").lower()
    if name not in ROLES:
        raise ValueError("role %r is not one of %s" % (role, ", ".join(ROLES)))
    owed = [item for item in document_report["owed"] if DOCUMENT_ROLE[item] == name]
    if not owed:
        return {"role": name, "owed_count": 0, "clean_count": 0, "fraction": 1.0}
    blocked = set()
    for key in (
        "missing",
        "not_at_final_issue",
        "unapproved",
        "revision_not_advanced",
        "revision_regressed",
        "wrong_article",
    ):
        blocked.update(document_report[key])
    clean = [item for item in owed if item not in blocked]
    return {
        "role": name,
        "owed_count": len(owed),
        "clean_count": len(clean),
        "fraction": len(clean) / float(len(owed)),
    }


def assess_final_application_procurement_documents(spec):
    """Run the full clause 5.8.5 closing-document release assessment.

    spec keys: route, documents, delivered_configuration_id.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("route", "documents", "delivered_configuration_id"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    report = assess_documents(
        spec["documents"], spec["route"], spec["delivered_configuration_id"]
    )
    application = role_completeness(report, "application")
    procurement = role_completeness(report, "procurement")

    findings = []
    if report["missing"]:
        findings.append(
            "closing document(s) the %s route owes are absent: %s"
            % (report["route"], ", ".join(report["missing"]))
        )
    if report["issued_but_not_owed"]:
        findings.append(
            "document(s) issued that the %s route does not owe: %s"
            % (report["route"], ", ".join(report["issued_but_not_owed"]))
        )
    if report["not_at_final_issue"]:
        findings.append(
            "document(s) not at final issue: %s" % ", ".join(report["not_at_final_issue"])
        )
    if report["unapproved"]:
        findings.append("document(s) not approved: %s" % ", ".join(report["unapproved"]))
    if report["revision_not_advanced"]:
        findings.append(
            "document(s) reissued on the previous phase revision without advancing it: %s"
            % ", ".join(report["revision_not_advanced"])
        )
    if report["revision_regressed"]:
        findings.append(
            "document(s) carrying a revision below the previous phase: %s"
            % ", ".join(report["revision_regressed"])
        )
    if report["wrong_article"]:
        findings.append(
            "document(s) naming an article other than the delivered configuration %s: %s"
            % (spec["delivered_configuration_id"], ", ".join(report["wrong_article"]))
        )

    return {
        "route": report["route"],
        "owed": report["owed"],
        "release_fraction": report["release_fraction"],
        "application": application,
        "procurement": procurement,
        "missing": report["missing"],
        "not_at_final_issue": report["not_at_final_issue"],
        "revision_not_advanced": report["revision_not_advanced"],
        "wrong_article": report["wrong_article"],
        "disposition": "released" if not findings else "release-blocked",
        "findings": findings,
    }
