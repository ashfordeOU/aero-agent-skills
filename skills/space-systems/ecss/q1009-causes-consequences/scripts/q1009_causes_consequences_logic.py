"""Cause and consequence analysis feeding disposition and corrective action.

Anchor: ECSS-Q-ST-10-09 clause 5.2.2.3 (analysing the cause of a
nonconformance and the consequences it carries, so that the board disposes of
it on evidence and the corrective-action decision rests on something).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the cause chain: an ordered set of levels running from the
   observed departure down to the root, each carrying a statement and a
   declaration of whether it is evidenced. The chain has to reach a minimum
   depth, and its root level has to name a category from the taxonomy and say
   whether the organisation actually controls it.
2. Judge the chain. A root the organisation does not control cannot be acted
   on, and unevidenced levels are named rather than accepted, because a chain
   of assertions is not an analysis.
3. Validate the consequence assessment: an explicit severity for every
   consequence dimension, so that no dimension is quietly left out.
4. Score the departure: the worst dimension severity, the likelihood the cause
   recurs and how hard the departure is to detect combine into one priority
   number that is deliberately integral, so the same inputs give the same
   number on every machine.
5. Propagate: a systemic root makes every unit built under the same condition
   suspect, an item-specific root does not. The suspect population is what the
   disposition has to cover.
6. Decide whether corrective action is owed, and report the inputs the
   disposition step needs.
"""

__all__ = [
    "MIN_CAUSE_DEPTH",
    "MAX_SEVERITY",
    "MAX_PRIORITY_NUMBER",
    "CAPA_PRIORITY_THRESHOLD",
    "CAUSE_CATEGORIES",
    "SYSTEMIC_CATEGORIES",
    "CONSEQUENCE_DIMENSIONS",
    "normalize_token",
    "validate_cause_category",
    "validate_cause_chain",
    "chain_findings",
    "validate_consequences",
    "affected_dimensions",
    "worst_severity",
    "validate_rating",
    "priority_number",
    "priority_ratio",
    "suspect_population",
    "corrective_action_required",
    "assess_causes_consequences",
]

# A chain that stops before this depth has named a mechanism, not a root: the
# departure, the condition that produced it, and the control that let the
# condition exist.
MIN_CAUSE_DEPTH = 3

# Severity, recurrence and detection are all judged on the same integral scale.
MAX_SEVERITY = 4
MAX_RATING = 5
MAX_PRIORITY_NUMBER = MAX_SEVERITY * MAX_RATING * MAX_RATING

# Above this priority the departure earns corrective action on its score alone.
CAPA_PRIORITY_THRESHOLD = 40

# Root-cause taxonomy. "Operator error" is deliberately absent: it names who
# was standing there, not the control that allowed the error to reach the item.
CAUSE_CATEGORIES = (
    "design",
    "material",
    "manufacturing-workmanship",
    "process-control",
    "procedure-or-documentation",
    "equipment-or-tooling",
    "handling-or-transport",
    "supplier",
    "test-or-inspection",
)

# Roots that can reproduce themselves on any unit built under the same
# condition. The rest are specific to the unit in hand.
SYSTEMIC_CATEGORIES = (
    "design",
    "material",
    "process-control",
    "procedure-or-documentation",
    "equipment-or-tooling",
    "supplier",
    "test-or-inspection",
)

CONSEQUENCE_DIMENSIONS = (
    "function-or-performance",
    "safety",
    "interfaces",
    "schedule",
    "cost",
    "qualification-validity",
    "other-units",
)

_CATEGORY_SET = frozenset(CAUSE_CATEGORIES)
_SYSTEMIC_SET = frozenset(SYSTEMIC_CATEGORIES)
_DIMENSION_SET = frozenset(CONSEQUENCE_DIMENSIONS)


def normalize_token(value, label="token"):
    """Return a taxonomy token in canonical hyphen form."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = " ".join(value.strip().lower().split())
    if not text:
        raise ValueError("%s must not be empty or whitespace only" % label)
    return text.replace(" ", "-").replace("_", "-")


def validate_cause_category(value):
    """Return a root-cause category from the taxonomy."""
    name = normalize_token(value, "cause category")
    if name not in _CATEGORY_SET:
        raise ValueError(
            "unknown root-cause category '%s'; name the control that allowed the "
            "departure, not the person present" % name
        )
    return name


def validate_cause_chain(chain):
    """Return the validated cause chain, symptom first and root last."""
    if not isinstance(chain, (list, tuple)):
        raise ValueError("cause chain must be a sequence of levels")
    if len(chain) < MIN_CAUSE_DEPTH:
        raise ValueError(
            "cause chain has %d level(s); at least %d are needed to reach a root"
            % (len(chain), MIN_CAUSE_DEPTH)
        )
    levels = []
    for index, level in enumerate(chain):
        if not isinstance(level, dict):
            raise ValueError("cause level %d must be a mapping" % index)
        for key in ("statement", "evidenced"):
            if key not in level:
                raise ValueError("cause level %d missing required key '%s'" % (index, key))
        statement = level["statement"]
        if not isinstance(statement, str) or not statement.strip():
            raise ValueError("cause level %d needs a non-empty statement" % index)
        if not isinstance(level["evidenced"], bool):
            raise ValueError("cause level %d 'evidenced' must be a boolean" % index)
        levels.append(
            {
                "index": index,
                "statement": statement.strip(),
                "evidenced": level["evidenced"],
            }
        )
    root = chain[-1]
    for key in ("category", "controllable"):
        if key not in root:
            raise ValueError("root cause level missing required key '%s'" % key)
    if not isinstance(root["controllable"], bool):
        raise ValueError("root cause 'controllable' must be a boolean")
    category = validate_cause_category(root["category"])
    levels[-1]["category"] = category
    levels[-1]["controllable"] = root["controllable"]
    levels[-1]["systemic"] = category in _SYSTEMIC_SET
    return levels


def chain_findings(levels):
    """Return the findings a cause chain carries, in reporting order."""
    if not isinstance(levels, (list, tuple)) or not levels:
        raise ValueError("levels must be a non-empty validated cause chain")
    findings = []
    root = levels[-1]
    if "controllable" not in root:
        raise ValueError("levels must come from validate_cause_chain")
    if not root["controllable"]:
        findings.append("root-cause-not-controllable")
    unevidenced = [level["index"] for level in levels if not level["evidenced"]]
    if unevidenced:
        findings.append(
            "unevidenced-cause-levels:%s" % ",".join(str(i) for i in unevidenced)
        )
    return tuple(findings)


def validate_rating(value, label, maximum=MAX_RATING):
    """Return an integral rating on the 1..maximum scale."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 1 or value > maximum:
        raise ValueError("%s must lie in 1..%d, got %d" % (label, maximum, value))
    return value


def validate_consequences(assessment):
    """Return the validated severity of every consequence dimension."""
    if not isinstance(assessment, dict):
        raise ValueError("consequence assessment must be a mapping")
    severities = {}
    for raw_name, raw_value in assessment.items():
        name = normalize_token(raw_name, "consequence dimension")
        if name not in _DIMENSION_SET:
            raise ValueError("unknown consequence dimension '%s'" % name)
        if name in severities:
            raise ValueError("consequence dimension '%s' assessed more than once" % name)
        if not isinstance(raw_value, int) or isinstance(raw_value, bool):
            raise ValueError(
                "severity for '%s' must be an integer, got %r" % (name, raw_value)
            )
        if raw_value < 0 or raw_value > MAX_SEVERITY:
            raise ValueError(
                "severity for '%s' must lie in 0..%d, got %d" % (name, MAX_SEVERITY, raw_value)
            )
        severities[name] = raw_value
    missing = [d for d in CONSEQUENCE_DIMENSIONS if d not in severities]
    if missing:
        raise ValueError("consequence dimensions left unassessed: %s" % ", ".join(missing))
    return severities


def affected_dimensions(severities):
    """Return the consequence dimensions carrying a non-zero severity."""
    validated = validate_consequences(severities)
    return tuple(d for d in CONSEQUENCE_DIMENSIONS if validated[d] > 0)


def worst_severity(severities):
    """Return the highest severity across the consequence dimensions."""
    validated = validate_consequences(severities)
    return max(validated[d] for d in CONSEQUENCE_DIMENSIONS)


def priority_number(severity, recurrence, detection):
    """Return the integral priority number of the departure."""
    if not isinstance(severity, int) or isinstance(severity, bool):
        raise ValueError("severity must be an integer, got %r" % (severity,))
    if severity < 0 or severity > MAX_SEVERITY:
        raise ValueError("severity must lie in 0..%d, got %d" % (MAX_SEVERITY, severity))
    rec = validate_rating(recurrence, "recurrence")
    det = validate_rating(detection, "detection")
    return severity * rec * det


def priority_ratio(priority):
    """Return the priority number as a share of the worst attainable one."""
    if not isinstance(priority, int) or isinstance(priority, bool):
        raise ValueError("priority must be an integer, got %r" % (priority,))
    if priority < 0 or priority > MAX_PRIORITY_NUMBER:
        raise ValueError(
            "priority must lie in 0..%d, got %d" % (MAX_PRIORITY_NUMBER, priority)
        )
    return priority / MAX_PRIORITY_NUMBER


def suspect_population(units, systemic):
    """Return the units the departure puts in question, given the root's reach."""
    if not isinstance(systemic, bool):
        raise ValueError("systemic must be a boolean, got %r" % (systemic,))
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("units must be a non-empty sequence")
    suspect = []
    raising = None
    seen = set()
    for unit in units:
        if not isinstance(unit, dict):
            raise ValueError("unit must be a mapping, got %r" % (unit,))
        for key in ("id", "shares_root_condition", "raising"):
            if key not in unit:
                raise ValueError("unit missing required key '%s'" % key)
        ident = normalize_token(unit["id"], "unit id")
        if ident in seen:
            raise ValueError("unit '%s' listed more than once" % ident)
        seen.add(ident)
        for key in ("shares_root_condition", "raising"):
            if not isinstance(unit[key], bool):
                raise ValueError("unit '%s' key '%s' must be a boolean" % (ident, key))
        if unit["raising"]:
            if raising is not None:
                raise ValueError("more than one unit marked as raising the departure")
            raising = ident
        if systemic and unit["shares_root_condition"]:
            suspect.append(ident)
        elif unit["raising"]:
            suspect.append(ident)
    if raising is None:
        raise ValueError("no unit marked as raising the departure")
    if raising not in suspect:
        suspect.append(raising)
    return tuple(sorted(suspect))


def corrective_action_required(priority, severities, systemic):
    """Return whether corrective action is owed, and the reasons for it."""
    validated = validate_consequences(severities)
    if not isinstance(systemic, bool):
        raise ValueError("systemic must be a boolean, got %r" % (systemic,))
    if not isinstance(priority, int) or isinstance(priority, bool):
        raise ValueError("priority must be an integer, got %r" % (priority,))
    reasons = []
    if validated["safety"] > 0:
        reasons.append("safety-consequence")
    if priority >= CAPA_PRIORITY_THRESHOLD:
        reasons.append("priority-at-or-above-threshold")
    if systemic and validated["other-units"] > 0:
        reasons.append("systemic-root-reaching-other-units")
    return {"required": bool(reasons), "reasons": tuple(reasons)}


def assess_causes_consequences(spec):
    """Run the full clause 5.2.2.3 cause and consequence analysis.

    spec keys: cause_chain, consequences, recurrence, detection, units.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("cause_chain", "consequences", "recurrence", "detection", "units"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    levels = validate_cause_chain(spec["cause_chain"])
    root = levels[-1]
    findings = list(chain_findings(levels))
    severities = validate_consequences(spec["consequences"])
    severity = worst_severity(severities)
    priority = priority_number(severity, spec["recurrence"], spec["detection"])
    suspect = suspect_population(spec["units"], root["systemic"])
    capa = corrective_action_required(priority, severities, root["systemic"])
    if len(suspect) > 1:
        findings.append("suspect-population-beyond-the-raising-unit:%d" % len(suspect))
    return {
        "cause_chain": levels,
        "root_category": root["category"],
        "root_systemic": root["systemic"],
        "chain_findings": tuple(findings),
        "consequences": severities,
        "affected_dimensions": affected_dimensions(severities),
        "worst_severity": severity,
        "priority_number": priority,
        "priority_ratio": priority_ratio(priority),
        "suspect_units": suspect,
        "corrective_action": capa,
        "analysis_complete": root["controllable"]
        and all(level["evidenced"] for level in levels),
    }
