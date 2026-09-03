"""MMEL development logic for transport type designs (pure stdlib).

Develop the Master Minimum Equipment List (MMEL) proposal for a type
design from safety assessment results. Each candidate equipment item is
screened for dispatch relief with the item inoperative, categorized as
MMEL-eligible or forbidden from relief, assigned the operator repair
interval category (A, B, C or D), given the operating (O) and
maintenance (M) flags, and checked against other inoperative items so
that no combination removes a safety function.

Deterministic screening rules only: no randomness, no external data, no
network. Every non-physical input raises ValueError.

The interval days table follows the typical public FAA MMEL interval
policy in summary form (A 3 days, B 10 days, C 120 days, D no
scheduled repair interval); actual approval of any interval is
authority-specific.
"""

SEVERITY_ORDER = {
    "none": 0,
    "minor": 1,
    "major": 2,
    "hazardous": 3,
    "catastrophic": 4,
}
SEVERITIES = tuple(SEVERITY_ORDER)
REDUNDANCY_VALUES = ("single-string", "dual", "multi")
CATEGORIES = ("A", "B", "C", "D")

# Typical public FAA MMEL interval policy, summary form only. D means
# no scheduled repair interval; the operator repairs at the next
# suitable maintenance opportunity.
INTERVAL_DAYS = {"A": 3, "B": 10, "C": 120, "D": None}

# Function groups assigned from item name keywords. Two inoperative
# items in the same group that both back a safety function remove that
# safety function, so that combination is never allowed.
GROUP_KEYWORDS = (
    "yaw",
    "pitch",
    "roll",
    "brake",
    "thrust",
    "pressurization",
    "nav",
    "comms",
    "flight-guidance",
)
GROUP_OF = dict((keyword, keyword) for keyword in GROUP_KEYWORDS)

REQUIRED_KEYS = (
    "item_id",
    "name",
    "function",
    "severity_if_inoperative",
    "redundancy",
    "safety_function",
    "crew_action_available",
    "maintenance_required",
    "placard_required",
)

DOUBLE_RELIEF_MSG = "double-relief removes a safety function"


def _validate_item(item):
    """Validate one item dict; raise ValueError on any non-physical field."""
    if not isinstance(item, dict):
        raise ValueError("each item must be a dict, got %r" % (type(item).__name__,))
    missing = [key for key in REQUIRED_KEYS if key not in item]
    if missing:
        raise ValueError(
            "item %r missing required keys: %s" % (item.get("item_id", "<unknown>"),
                                                   ", ".join(missing)))
    severity = item["severity_if_inoperative"]
    if severity not in SEVERITY_ORDER:
        raise ValueError("unknown severity %r, expected one of %s"
                         % (severity, ", ".join(SEVERITIES)))
    redundancy = item["redundancy"]
    if redundancy not in REDUNDANCY_VALUES:
        raise ValueError("unknown redundancy %r, expected one of %s"
                         % (redundancy, ", ".join(REDUNDANCY_VALUES)))
    if item["item_id"] is None or str(item["item_id"]).strip() == "":
        raise ValueError("item_id must be a non-empty string")


def group_of(name):
    """Return the function group for an item name, or None when the name
    carries no GROUP_OF keyword. Hyphens and spaces are interchangeable."""
    normalized = str(name).lower().replace("-", " ")
    for keyword in GROUP_KEYWORDS:
        token = keyword.replace("-", " ")
        if token in normalized:
            return GROUP_OF[keyword]
    return None


def _flight_relevant(item):
    """True when the item is part of the flight function groups or backs a
    safety function directly."""
    return group_of(item["name"]) is not None or bool(item["safety_function"])


def _redundant(item):
    """True when remaining capability is dual or multi, not single-string."""
    return item["redundancy"] in ("dual", "multi")


def eligibility(item):
    """Return (eligible, reason) for dispatch relief with the item
    inoperative.

    Severity major or lower is eligible. A hazardous or catastrophic
    single-string item is never eligible. A hazardous or catastrophic
    item is eligible only with dual or multi redundancy and only when it
    is not itself the mitigation (safety_function False): the remaining
    channels alone then meet the safety objective.
    """
    _validate_item(item)
    severity = item["severity_if_inoperative"]
    if severity in ("hazardous", "catastrophic"):
        if not _redundant(item):
            return (False, "single-string item backs a %s failure "
                    "condition, no dispatch relief" % severity)
        if item["safety_function"]:
            return (False, "item is itself the mitigation for a %s "
                    "failure condition, relief removes the safety function"
                    % severity)
        return (True, "%s with dual or multi redundancy, remaining "
                "channels meet the safety objective with the item "
                "inoperative" % severity)
    if severity == "major":
        return (True, "major severity stays within dispatch relief limits")
    if severity == "minor":
        return (True, "minor severity stays within dispatch relief limits")
    return (True, "no safety effect when inoperative, relief permitted")


def interval_category(item):
    """Return (category, reason) for an eligible item.

    Category A 3 days, B 10 days, C 120 days, D no scheduled repair
    interval (INTERVAL_DAYS). Hazards escalate the interval:
    catastrophic with redundancy -> A, hazardous with redundancy -> B.
    Severity major single-string without crew action -> A. Minor and
    none severity single-string items are C when flight-relevant
    (function group or safety function) and D otherwise, so passenger
    convenience items such as cabin entertainment carry no scheduled
    repair interval. Raises ValueError when the item is not MMEL
    eligible, since no interval category exists for it.
    """
    _validate_item(item)
    eligible, reason = eligibility(item)
    if not eligible:
        raise ValueError("item %s is not MMEL-eligible (%s); no interval "
                         "category exists" % (item["item_id"], reason))
    severity = item["severity_if_inoperative"]
    crew = bool(item["crew_action_available"])
    redundant = _redundant(item)
    if severity == "catastrophic":
        return ("A", "catastrophic backed by redundant channels, "
                "repair within 3 days")
    if severity == "hazardous":
        return ("B", "hazardous backed by redundant channels, "
                "repair within 10 days")
    if severity == "major":
        if redundant:
            return ("C", "major severity with redundancy, "
                    "repair within 120 days")
        if crew:
            return ("B", "major severity single string with crew action, "
                    "repair within 10 days")
        return ("A", "major severity single string without crew action, "
                "repair within 3 days")
    if severity == "minor":
        if crew or redundant:
            return ("D", "minor severity with crew action or redundancy, "
                    "no scheduled repair interval")
        if _flight_relevant(item):
            return ("C", "minor severity single string, flight-relevant, "
                    "repair within 120 days")
        return ("D", "minor severity passenger convenience item outside "
                "the flight function groups, no scheduled repair interval")
    # severity none
    if not redundant and _flight_relevant(item):
        return ("C", "no-effect single string flight-relevant item, "
                "repair within 120 days")
    return ("D", "no safety effect when inoperative, no scheduled "
            "repair interval")


def o_m_flags(item, category):
    """Return (o_flag, m_flag, placard) for an eligible item.

    The (O) operating procedure flag is set when the crew can detect and
    compensate (crew_action_available), the interval category is A or B,
    or the item backs a safety function. The (M) maintenance flag is set
    when a maintenance task restores the item or function, the category
    is A, or the item is hazardous/catastrophic with redundancy. A
    placard is required when placard_required is set or the category is
    A or B.
    """
    _validate_item(item)
    if category not in CATEGORIES:
        raise ValueError("unknown interval category %r, expected one of %s"
                         % (category, ", ".join(CATEGORIES)))
    severity = item["severity_if_inoperative"]
    o_flag = (bool(item["crew_action_available"])
              or category in ("A", "B")
              or bool(item["safety_function"]))
    m_flag = (bool(item["maintenance_required"])
              or category == "A"
              or (severity in ("hazardous", "catastrophic")
                  and _redundant(item)))
    placard = (bool(item["placard_required"]) or category in ("A", "B"))
    return (o_flag, m_flag, placard)


def interaction_check(items, allowed_combination_max=1):
    """Return the interaction issue list for candidate inoperative items.

    Every pair of items in the same function group (GROUP_OF keywords)
    that both back a safety function raises the double-relief issue,
    because dispatching both inoperative removes that safety function.
    More than allowed_combination_max inoperative items in one function
    group is also issued. An empty candidate list has no issues.
    """
    issues = []
    candidates = list(items)
    for item in candidates:
        _validate_item(item)
    indexed = []
    for item in candidates:
        group = group_of(item["name"])
        if group is not None:
            indexed.append((group, item))
    for i in range(len(indexed)):
        group_a, item_a = indexed[i]
        for j in range(i + 1, len(indexed)):
            group_b, item_b = indexed[j]
            if group_a != group_b:
                continue
            if item_a["safety_function"] and item_b["safety_function"]:
                issues.append("%s: %s and %s share function group %s"
                              % (DOUBLE_RELIEF_MSG, item_a["item_id"],
                                 item_b["item_id"], group_a))
    per_group = {}
    for group, _item in indexed:
        per_group[group] = per_group.get(group, 0) + 1
    for group in sorted(per_group):
        count = per_group[group]
        if count > allowed_combination_max:
            issues.append("%d inoperative items share function group %s "
                          "(max %d)" % (count, group, allowed_combination_max))
    return issues


def build_mmel_proposal(items):
    """Return {rows, forbidden, issues} for the item list.

    rows: per-item MMEL proposal rows {item_id, category, o_flag,
    m_flag, placard, eligible} for every relief-eligible item.
    forbidden: {item_id, reason} entries for items refused relief.
    issues: interaction issues between the eligible inoperative items.
    Raises ValueError on an empty or malformed item list.
    """
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list of item dicts")
    rows = []
    forbidden = []
    eligible_items = []
    for item in items:
        _validate_item(item)
        ok, reason = eligibility(item)
        if not ok:
            forbidden.append({"item_id": item["item_id"], "reason": reason})
            continue
        category, _reason = interval_category(item)
        o_flag, m_flag, placard = o_m_flags(item, category)
        rows.append({"item_id": item["item_id"], "category": category,
                     "o_flag": o_flag, "m_flag": m_flag,
                     "placard": placard, "eligible": True})
        eligible_items.append(item)
    issues = interaction_check(eligible_items)
    return {"rows": rows, "forbidden": forbidden, "issues": issues}


def proposal_verdict(proposal):
    """Return (PASS/FAIL, reasons) for a built MMEL proposal.

    FAIL when a catastrophic or hazardous single-string item sits in the
    rows (a row may carry optional severity_if_inoperative and
    redundancy keys), when any interaction issue exists, or when any
    category A or B row lacks the (O) operating procedure flag. An empty
    reasons list accompanies PASS.
    """
    reasons = []
    for row in proposal.get("rows", []):
        item_id = row["item_id"]
        if (row.get("severity_if_inoperative") in ("hazardous", "catastrophic")
                and row.get("redundancy") == "single-string"):
            reasons.append("%s: hazardous or catastrophic single-string "
                           "item must not appear in the MMEL rows" % item_id)
        if row["category"] in ("A", "B") and not row["o_flag"]:
            reasons.append("%s: missing (O) operating procedure flag for "
                           "interval category %s" % (item_id, row["category"]))
    for issue in proposal.get("issues", []):
        reasons.append(str(issue))
    if reasons:
        return ("FAIL", reasons)
    return ("PASS", [])


def interval_days(category):
    """Return the interval days for a category letter, None for D."""
    if category not in INTERVAL_DAYS:
        raise ValueError("unknown interval category %r, expected one of %s"
                         % (category, ", ".join(CATEGORIES)))
    return INTERVAL_DAYS[category]
