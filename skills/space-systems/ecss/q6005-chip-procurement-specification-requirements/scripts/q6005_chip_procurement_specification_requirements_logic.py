"""Content a purchase specification for bare chips has to define.

Anchor: ECSS-Q-ST-60-05C clause 8.1.3 (what the purchasing documents for bare
semiconductor and passive chips define before an order is placed). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Build the applicable content set for this order: the items every bare-chip
   purchase defines, plus the conditional items that become applicable only
   when the project declares the context that calls for them (a radiation
   requirement, additional screening, a single-wafer-lot constraint,
   serialization).
2. Read the declared specification, treating a placeholder value -- an empty
   string, a dash, "TBD", "to be advised" -- as undefined rather than declared.
   A field that exists but says nothing has not defined anything.
3. Report the undefined applicable items, the items declared outside the
   applicable set, and the completeness ratio computed over the applicable set
   only, so adding an inapplicable item cannot inflate it.
4. Refuse release-to-order while any applicable item is undefined.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "MANDATORY_ITEMS",
    "CONDITIONAL_ITEMS",
    "PLACEHOLDER_VALUES",
    "normalize_item_key",
    "is_defined",
    "validate_context",
    "applicable_items",
    "declared_items",
    "undefined_items",
    "surplus_items",
    "completeness_ratio",
    "assess_procurement_specification",
]

# A completeness ratio is a quotient of small integers, but a caller may pass a
# required ratio as a decimal fraction. Comparisons absorb the representation
# error here rather than by lowering the required completeness.
RATIO_TOLERANCE = 1e-9

# Content every bare-chip purchase defines, whatever the project context.
MANDATORY_ITEMS = (
    "chip-type-identification",
    "die-revision-and-mask-set",
    "wafer-lot-traceability",
    "electrical-parameters-at-probe",
    "visual-inspection-criteria",
    "die-dimensions-and-tolerances",
    "bond-pad-metallization",
    "backside-finish",
    "passivation",
    "packaging-and-storage",
    "esd-sensitivity-category",
    "certificate-of-conformity-content",
    "delivery-documentation",
)

# Content that becomes applicable only when the project declares its context.
# Maps the item key to the context flag that switches it on.
CONDITIONAL_ITEMS = {
    "radiation-hardness-level": "radiation_requirement",
    "additional-screening-plan": "screening_required",
    "single-wafer-lot-quantity": "single_wafer_lot_required",
    "serialization-and-container-marking": "serialization_required",
}

# A field carrying one of these has not defined anything.
PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "-",
        "--",
        "?",
        "tbd",
        "tba",
        "n/a",
        "na",
        "none",
        "not defined",
        "to be defined",
        "to be advised",
        "see later",
    }
)


def normalize_item_key(key):
    """Return a specification item key in the canonical hyphenated lower form."""
    if not isinstance(key, str):
        raise ValueError("specification item key must be a string, got %r" % (key,))
    cleaned = key.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    cleaned = cleaned.strip("-")
    if not cleaned:
        raise ValueError("specification item key must not be blank")
    return cleaned


def is_defined(value):
    """Return True when a declared value actually defines something."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in PLACEHOLDER_VALUES
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    raise ValueError("unsupported declared value type: %r" % (type(value).__name__,))


def validate_context(context):
    """Return the validated project context switching the conditional items on."""
    if context is None:
        context = {}
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping of flag name to boolean")
    known = set(CONDITIONAL_ITEMS.values())
    validated = {}
    for flag, value in context.items():
        if not isinstance(flag, str) or not flag.strip():
            raise ValueError("context flag names must be non-empty strings")
        if flag not in known:
            raise ValueError(
                "unknown context flag '%s'; known flags: %s"
                % (flag, ", ".join(sorted(known)))
            )
        if not isinstance(value, bool):
            raise ValueError("context flag '%s' must be a boolean, got %r" % (flag, value))
        validated[flag] = value
    for flag in known:
        validated.setdefault(flag, False)
    return validated


def applicable_items(context=None):
    """Return the ordered content set this particular order has to define."""
    flags = validate_context(context)
    items = list(MANDATORY_ITEMS)
    for item, flag in sorted(CONDITIONAL_ITEMS.items()):
        if flags[flag]:
            items.append(item)
    return tuple(items)


def declared_items(specification):
    """Return the declared specification with canonical keys, refusing duplicates."""
    if not isinstance(specification, dict):
        raise ValueError("specification must be a mapping of item key to value")
    canonical = {}
    for key, value in specification.items():
        item = normalize_item_key(key)
        if item in canonical:
            raise ValueError("item '%s' is declared more than once" % item)
        canonical[item] = value
    return canonical


def undefined_items(specification, context=None):
    """Return the applicable items this specification leaves undefined."""
    canonical = declared_items(specification)
    missing = []
    for item in applicable_items(context):
        if item not in canonical or not is_defined(canonical[item]):
            missing.append(item)
    return missing


def surplus_items(specification, context=None):
    """Return declared items that sit outside the applicable set for this order."""
    canonical = declared_items(specification)
    applicable = set(applicable_items(context))
    return sorted(item for item in canonical if item not in applicable)


def completeness_ratio(specification, context=None):
    """Return the fraction of the applicable set that is actually defined."""
    applicable = applicable_items(context)
    if not applicable:
        raise ValueError("applicable content set is empty; nothing to measure")
    missing = undefined_items(specification, context)
    return (len(applicable) - len(missing)) / float(len(applicable))


def assess_procurement_specification(spec):
    """Run the full clause 8.1.3 purchase-specification assessment.

    spec keys: specification (the declared item mapping), optional context
    (the conditional-item flags) and optional required_ratio used to report a
    partial-readiness view; release-to-order still needs every applicable item.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "specification" not in spec:
        raise ValueError("spec missing required key 'specification'")
    context = validate_context(spec.get("context"))
    applicable = applicable_items(context)
    missing = undefined_items(spec["specification"], context)
    surplus = surplus_items(spec["specification"], context)
    ratio = completeness_ratio(spec["specification"], context)
    required = spec.get("required_ratio", 1.0)
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_ratio must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_ratio must lie in [0, 1], got %r" % (required,))
    meets_ratio = ratio > required or math.isclose(
        ratio, required, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    findings = []
    if missing:
        findings.append(
            "%d applicable item(s) undefined: %s" % (len(missing), ", ".join(missing))
        )
    if surplus:
        findings.append(
            "%d declared item(s) outside the applicable set: %s"
            % (len(surplus), ", ".join(surplus))
        )
    conditional_on = sorted(
        item for item, flag in CONDITIONAL_ITEMS.items() if context[flag]
    )
    return {
        "applicable_count": len(applicable),
        "conditional_items_applicable": conditional_on,
        "undefined_items": missing,
        "surplus_items": surplus,
        "completeness_ratio": ratio,
        "required_ratio": required,
        "meets_required_ratio": meets_ratio,
        "ready_to_order": not missing,
        "findings": findings,
    }
