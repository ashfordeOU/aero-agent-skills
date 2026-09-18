"""Procurement category boundary for hybrid microcircuit manufacturers.

Anchor: ECSS-Q-ST-60-05 clause 5.2 (the two procurement categories: a maker
whose production line already carries an approval, and a maker whose line does
not). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Describe the build the hybrid will actually go through: the site, the
   production line inside that site, and the process technology of the part.
2. Validate every approval the maker offers, each of which names the site and
   line it was granted for, the technologies it covers, its issue and expiry
   dates and its standing.
3. Test each approval against the build on every dimension at once, and keep
   the reasons an approval fails rather than only the verdict, so an approval
   that misses on one dimension can be told apart from one that misses on
   several.
4. A maker is put in the approved-line category only when at least one
   approval covers this site, this line and this technology and is in force
   on the decision date. Anything less puts it in the other category.
5. Report the near misses, because an approval that covers the line but not
   the technology, or the technology but not the line, is the usual way a
   maker is put in the wrong category.
"""

import datetime

__all__ = [
    "CATEGORY_APPROVED_LINE",
    "CATEGORY_NO_APPROVED_LINE",
    "CATEGORIES",
    "CATEGORY_LABELS",
    "TECHNOLOGIES",
    "EXCLUSION_REASONS",
    "normalize_technology",
    "normalize_identifier",
    "normalize_standing",
    "parse_date",
    "validate_build",
    "validate_approval",
    "approval_covers_site",
    "approval_covers_line",
    "approval_covers_technology",
    "approval_in_force",
    "approval_exclusions",
    "matching_approvals",
    "near_miss_approvals",
    "category_label",
    "categorize_manufacturer",
]

CATEGORY_APPROVED_LINE = "approved-line"
CATEGORY_NO_APPROVED_LINE = "no-approved-line"
CATEGORIES = (CATEGORY_APPROVED_LINE, CATEGORY_NO_APPROVED_LINE)

CATEGORY_LABELS = {
    CATEGORY_APPROVED_LINE: "maker whose production line already carries an approval",
    CATEGORY_NO_APPROVED_LINE: "maker whose production line carries no approval",
}

# Process technologies a hybrid line is approved for. An approval is granted
# per technology; a line approved for one is not thereby approved for another.
TECHNOLOGIES = (
    "thick-film",
    "thin-film",
    "multi-chip-module",
    "chip-on-board",
    "microwave-hybrid",
)

_TECHNOLOGY_ALIASES = {
    "thick film": "thick-film",
    "thickfilm": "thick-film",
    "thin film": "thin-film",
    "thinfilm": "thin-film",
    "mcm": "multi-chip-module",
    "multi chip module": "multi-chip-module",
    "cob": "chip-on-board",
    "chip on board": "chip-on-board",
    "mmic-hybrid": "microwave-hybrid",
    "microwave hybrid": "microwave-hybrid",
}

EXCLUSION_REASONS = (
    "different-site",
    "different-line",
    "technology-not-covered",
    "lapsed",
    "suspended",
    "withdrawn",
    "not-yet-in-force",
)

_STANDINGS = ("valid", "suspended", "withdrawn")


def normalize_technology(technology):
    """Return the canonical process technology name."""
    if not isinstance(technology, str):
        raise ValueError("technology must be a string, got %r" % (technology,))
    key = technology.strip().lower()
    key = _TECHNOLOGY_ALIASES.get(key, key.replace("_", "-").replace(" ", "-"))
    if key not in TECHNOLOGIES:
        raise ValueError("unknown hybrid process technology %r" % (technology,))
    return key


def normalize_identifier(value, label):
    """Return a canonical site or line identifier."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def normalize_standing(standing):
    """Return the canonical standing an approval carries."""
    if not isinstance(standing, str):
        raise ValueError("standing must be a string, got %r" % (standing,))
    key = standing.strip().lower()
    if key not in _STANDINGS:
        raise ValueError("unknown approval standing %r" % (standing,))
    return key


def parse_date(value):
    """Return a date from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("date must be an ISO string or a date, got %r" % (value,))
    parts = value.strip().split("-")
    if len(parts) != 3 or len(parts[0]) != 4:
        raise ValueError("date %r must be formatted yyyy-mm-dd" % (value,))
    try:
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except ValueError:
        raise ValueError("date %r is not a real calendar date" % (value,))


def validate_build(build):
    """Return the canonical description of the build the hybrid will go through."""
    if not isinstance(build, dict):
        raise ValueError("build must be a mapping")
    for key in ("site", "line", "technology"):
        if key not in build:
            raise ValueError("build missing required key '%s'" % key)
    return {
        "site": normalize_identifier(build["site"], "site"),
        "line": normalize_identifier(build["line"], "line"),
        "technology": normalize_technology(build["technology"]),
    }


def validate_approval(approval):
    """Return a canonical production-line approval record."""
    if not isinstance(approval, dict):
        raise ValueError("approval must be a mapping")
    for key in ("id", "site", "line", "technologies", "issued", "valid_until"):
        if key not in approval:
            raise ValueError("approval missing required key '%s'" % key)
    technologies = approval["technologies"]
    if not isinstance(technologies, (list, tuple)) or not technologies:
        raise ValueError("approval must cover at least one technology")
    covered = []
    for item in technologies:
        name = normalize_technology(item)
        if name not in covered:
            covered.append(name)
    issued = parse_date(approval["issued"])
    valid_until = parse_date(approval["valid_until"])
    if valid_until < issued:
        raise ValueError("approval expires before it was issued")
    return {
        "id": normalize_identifier(approval["id"], "approval id"),
        "site": normalize_identifier(approval["site"], "site"),
        "line": normalize_identifier(approval["line"], "line"),
        "technologies": tuple(covered),
        "issued": issued,
        "valid_until": valid_until,
        "standing": normalize_standing(approval.get("standing", "valid")),
    }


def approval_covers_site(approval, build):
    """Return True when the approval was granted for the build's site."""
    return validate_approval(approval)["site"] == validate_build(build)["site"]


def approval_covers_line(approval, build):
    """Return True when the approval names the build's site and line."""
    canonical = validate_approval(approval)
    target = validate_build(build)
    return canonical["site"] == target["site"] and canonical["line"] == target["line"]


def approval_covers_technology(approval, build):
    """Return True when the approval covers the build's process technology."""
    canonical = validate_approval(approval)
    return validate_build(build)["technology"] in canonical["technologies"]


def approval_in_force(approval, on_date):
    """Return True when the approval is in force on the given date."""
    canonical = validate_approval(approval)
    when = parse_date(on_date)
    if canonical["standing"] != "valid":
        return False
    return canonical["issued"] <= when <= canonical["valid_until"]


def approval_exclusions(approval, build, on_date):
    """Return every reason the approval fails to cover the build, in order."""
    canonical = validate_approval(approval)
    target = validate_build(build)
    when = parse_date(on_date)
    reasons = []
    if canonical["site"] != target["site"]:
        reasons.append("different-site")
    if canonical["site"] == target["site"] and canonical["line"] != target["line"]:
        reasons.append("different-line")
    if target["technology"] not in canonical["technologies"]:
        reasons.append("technology-not-covered")
    if canonical["standing"] == "suspended":
        reasons.append("suspended")
    elif canonical["standing"] == "withdrawn":
        reasons.append("withdrawn")
    elif when > canonical["valid_until"]:
        reasons.append("lapsed")
    elif when < canonical["issued"]:
        reasons.append("not-yet-in-force")
    return tuple(reasons)


def matching_approvals(approvals, build, on_date):
    """Return the ids of approvals that cover the build on every dimension."""
    if not isinstance(approvals, (list, tuple)):
        raise ValueError("approvals must be a list or tuple of records")
    matched = []
    for approval in approvals:
        if not approval_exclusions(approval, build, on_date):
            matched.append(validate_approval(approval)["id"])
    return tuple(matched)


def near_miss_approvals(approvals, build, on_date):
    """Return (id, reason) pairs for approvals that fail on exactly one count."""
    if not isinstance(approvals, (list, tuple)):
        raise ValueError("approvals must be a list or tuple of records")
    near = []
    for approval in approvals:
        reasons = approval_exclusions(approval, build, on_date)
        if len(reasons) == 1:
            near.append((validate_approval(approval)["id"], reasons[0]))
    return tuple(near)


def category_label(category):
    """Return the readable description of a procurement category."""
    if not isinstance(category, str):
        raise ValueError("category must be a string, got %r" % (category,))
    key = category.strip().lower()
    if key not in CATEGORY_LABELS:
        raise ValueError("unknown procurement category %r" % (category,))
    return CATEGORY_LABELS[key]


def categorize_manufacturer(spec):
    """Place a hybrid maker in one of the two procurement categories.

    spec keys: build (site, line, technology), approvals (list of records),
    decision_date. The maker is put in the approved-line category only when an
    approval covers this site, this line and this technology and is in force.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("build", "approvals", "decision_date"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    build = validate_build(spec["build"])
    when = parse_date(spec["decision_date"])
    approvals = spec["approvals"]
    if not isinstance(approvals, (list, tuple)):
        raise ValueError("approvals must be a list or tuple of records")
    seen = []
    exclusions = {}
    for approval in approvals:
        canonical = validate_approval(approval)
        if canonical["id"] in seen:
            raise ValueError("approval id %s is recorded more than once" % canonical["id"])
        seen.append(canonical["id"])
        reasons = approval_exclusions(approval, build, when)
        if reasons:
            exclusions[canonical["id"]] = reasons
    matched = matching_approvals(approvals, build, when)
    near = near_miss_approvals(approvals, build, when)
    category = CATEGORY_APPROVED_LINE if matched else CATEGORY_NO_APPROVED_LINE
    findings = []
    if not matched:
        for approval_id, reason in near:
            findings.append(
                "approval %s misses only on %s; it does not move the maker into "
                "the approved-line category" % (approval_id, reason)
            )
        if not approvals:
            findings.append("no production-line approval was offered for this build")
    return {
        "category": category,
        "category_label": category_label(category),
        "build": build,
        "decision_date": when,
        "matching_approvals": matched,
        "near_misses": near,
        "exclusions": exclusions,
        "approval_count": len(seen),
        "findings": findings,
    }
