"""Disposition of a minor nonconformance: availability, authority, evidence.

Anchor: ECSS-Q-ST-10-09 clause 5.2.2.4 (disposing of a minor nonconformance --
which disposition the item can actually carry, which board may authorize it,
and what the disposition has to leave written down). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the case: the severity category the departure was given, the
   disposition proposed for it, the properties of the item that decide which
   dispositions are physically available, and the evidence assembled.
2. Work out which dispositions the item can carry at all. Rework needs a
   departure that can be reversed; repair needs an item that can be repaired;
   return needs an item somebody else supplied. A disposition the item cannot
   carry is refused before any authority question is reached.
3. Work out the authority the disposition needs. A minor departure is the
   supplier board's to dispose of, but not unconditionally: a disposition
   leaving a permanent departure against a customer-controlled requirement,
   and the scrapping of customer-furnished property, both rise to the
   customer board however minor the departure was.
4. Compare the authority that actually approved it with the authority needed,
   on an ordered scale, so a higher board approving a lower case is accepted
   and the reverse is not.
5. Check the evidence the chosen disposition owes -- each disposition owes a
   different set, and the sets are what make the disposition auditable.
6. Report the disposition as authorized only when it is available, approved at
   or above the needed authority, and complete in its evidence.
"""

__all__ = [
    "DISPOSITIONS",
    "PERMANENT_DEPARTURE_DISPOSITIONS",
    "REQUIRED_CONDITIONS",
    "AUTHORITY_INTERNAL",
    "AUTHORITY_CUSTOMER",
    "AUTHORITY_RANK",
    "CONTEXT_KEYS",
    "normalize_token",
    "validate_disposition",
    "validate_authority",
    "validate_category",
    "validate_context",
    "eligible_dispositions",
    "required_authority",
    "authority_satisfied",
    "missing_conditions",
    "assess_minor_disposition",
]

AUTHORITY_INTERNAL = "internal-review-board"
AUTHORITY_CUSTOMER = "customer-review-board"

# Ordered: a higher board may take a lower board's decision, never the reverse.
AUTHORITY_RANK = {AUTHORITY_INTERNAL: 1, AUTHORITY_CUSTOMER: 2}

DISPOSITIONS = (
    "rework",
    "repair",
    "use-as-is",
    "return-to-supplier",
    "scrap",
)

# Dispositions that deliver an item still departing from its requirement.
PERMANENT_DEPARTURE_DISPOSITIONS = ("repair", "use-as-is")

# What each disposition has to leave written down. The sets differ because the
# question each disposition has to answer later differs.
REQUIRED_CONDITIONS = {
    "rework": (
        "rework-procedure",
        "re-inspection-record",
        "conformance-restored-statement",
    ),
    "repair": (
        "repair-procedure",
        "repair-design-justification",
        "re-inspection-record",
        "limitation-record",
        "effectivity-list",
    ),
    "use-as-is": (
        "use-as-is-justification",
        "limitation-record",
        "effectivity-list",
    ),
    "return-to-supplier": (
        "supplier-nonconformance-reference",
        "transfer-record",
        "quarantine-record",
    ),
    "scrap": (
        "scrap-authorization",
        "material-removal-record",
        "replacement-plan",
    ),
}

# The item properties that decide which dispositions exist for this case.
CONTEXT_KEYS = (
    "departure_reversible",
    "item_repairable",
    "externally_supplied",
    "customer_furnished",
    "customer_controlled_requirement",
)

_DISPOSITION_SET = frozenset(DISPOSITIONS)


def normalize_token(value, label="token"):
    """Return a token in canonical hyphen form."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = " ".join(value.strip().lower().split())
    if not text:
        raise ValueError("%s must not be empty or whitespace only" % label)
    return text.replace(" ", "-").replace("_", "-")


def validate_disposition(value):
    """Return a disposition from the permitted set."""
    name = normalize_token(value, "disposition")
    if name not in _DISPOSITION_SET:
        raise ValueError("unknown disposition '%s'" % name)
    return name


def validate_authority(value):
    """Return an authority from the ordered scale."""
    name = normalize_token(value, "authority")
    if name not in AUTHORITY_RANK:
        raise ValueError("unknown authority '%s'" % name)
    return name


def validate_category(value):
    """Return the severity category the departure was given."""
    name = normalize_token(value, "category")
    if name not in ("minor", "major"):
        raise ValueError("category must be 'minor' or 'major', got '%s'" % name)
    return name


def validate_context(context):
    """Return the validated item properties, every key answered explicitly."""
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping of item properties")
    validated = {}
    for raw_key, raw_value in context.items():
        key = normalize_token(raw_key, "context key").replace("-", "_")
        if key not in CONTEXT_KEYS:
            raise ValueError("unknown context key '%s'" % key)
        if key in validated:
            raise ValueError("context key '%s' answered more than once" % key)
        if not isinstance(raw_value, bool):
            raise ValueError("context key '%s' must be a boolean, got %r" % (key, raw_value))
        validated[key] = raw_value
    missing = [k for k in CONTEXT_KEYS if k not in validated]
    if missing:
        raise ValueError("context keys left unanswered: %s" % ", ".join(missing))
    return validated


def eligible_dispositions(context):
    """Return the dispositions this item can actually carry, in canonical order."""
    props = validate_context(context)
    available = []
    for disposition in DISPOSITIONS:
        if disposition == "rework" and not props["departure_reversible"]:
            continue
        if disposition == "repair" and not props["item_repairable"]:
            continue
        if disposition == "return-to-supplier" and not props["externally_supplied"]:
            continue
        available.append(disposition)
    return tuple(available)


def required_authority(category, disposition, context):
    """Return the authority the case needs and the reasons it rises."""
    cat = validate_category(category)
    name = validate_disposition(disposition)
    props = validate_context(context)
    reasons = []
    if cat == "major":
        reasons.append("major-departure")
    if (
        name in PERMANENT_DEPARTURE_DISPOSITIONS
        and props["customer_controlled_requirement"]
    ):
        reasons.append("permanent-departure-against-customer-controlled-requirement")
    if name == "scrap" and props["customer_furnished"]:
        reasons.append("scrapping-customer-furnished-property")
    authority = AUTHORITY_CUSTOMER if reasons else AUTHORITY_INTERNAL
    return {"authority": authority, "reasons": tuple(reasons)}


def authority_satisfied(approved_by, needed):
    """Return whether the approving authority reaches the authority needed."""
    have = validate_authority(approved_by)
    want = validate_authority(needed)
    return AUTHORITY_RANK[have] >= AUTHORITY_RANK[want]


def missing_conditions(disposition, evidence):
    """Return the documented conditions this disposition owes and did not get."""
    name = validate_disposition(disposition)
    if isinstance(evidence, dict):
        supplied = set()
        for raw_key, raw_value in evidence.items():
            key = normalize_token(raw_key, "evidence item")
            if not isinstance(raw_value, bool):
                raise ValueError(
                    "evidence item '%s' must be a boolean, got %r" % (key, raw_value)
                )
            if raw_value:
                supplied.add(key)
    elif isinstance(evidence, (list, tuple, set, frozenset)):
        supplied = {normalize_token(k, "evidence item") for k in evidence}
    else:
        raise ValueError("evidence must be a mapping or a sequence of item names")
    return tuple(item for item in REQUIRED_CONDITIONS[name] if item not in supplied)


def assess_minor_disposition(spec):
    """Run the full clause 5.2.2.4 disposition assessment.

    spec keys: category, disposition, context, evidence, approved_by.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("category", "disposition", "context", "evidence", "approved_by"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    category = validate_category(spec["category"])
    disposition = validate_disposition(spec["disposition"])
    props = validate_context(spec["context"])
    available = eligible_dispositions(props)
    needed = required_authority(category, disposition, props)
    approved_by = validate_authority(spec["approved_by"])
    satisfied = authority_satisfied(approved_by, needed["authority"])
    gaps = missing_conditions(disposition, spec["evidence"])
    findings = []
    if disposition not in available:
        findings.append(
            "disposition '%s' is not available for this item; available: %s"
            % (disposition, ", ".join(available))
        )
    if not satisfied:
        findings.append(
            "approved by %s but the case needs %s (%s)"
            % (approved_by, needed["authority"], ", ".join(needed["reasons"]))
        )
    if gaps:
        findings.append(
            "disposition '%s' is missing %s" % (disposition, ", ".join(gaps))
        )
    return {
        "category": category,
        "disposition": disposition,
        "available_dispositions": available,
        "required_authority": needed["authority"],
        "escalation_reasons": needed["reasons"],
        "approved_by": approved_by,
        "authority_satisfied": satisfied,
        "missing_conditions": gaps,
        "leaves_permanent_departure": disposition in PERMANENT_DEPARTURE_DISPOSITIONS,
        "findings": findings,
        "authorized": (disposition in available) and satisfied and not gaps,
    }
