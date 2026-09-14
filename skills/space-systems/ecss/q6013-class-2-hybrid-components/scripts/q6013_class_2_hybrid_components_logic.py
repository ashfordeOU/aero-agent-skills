"""Hybrid microcircuit procurement at the intermediate assurance class.

Anchor: ECSS-Q-ST-60-13C clause 5.6.3 (a hybrid microcircuit bought for an
intermediate assurance part programme is admissible only against a procurement
specification of its own, and only where the constituent elements were
themselves bought at a class the assembled hybrid can stand behind).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Refuse a hybrid that carries no procurement specification reference. There
   is nothing to buy it against, so no element grading can rescue it.
2. Grade every constituent element -- die, chip resistor, chip capacitor,
   substrate, interconnect, package -- by the procurement class it was itself
   bought at, against the class the hybrid is being offered for.
3. An element at or above the target class is admissible unaided. An element
   one class short is recoverable, but only where an upscreening specification
   is named and lot traceability is declared behind it. An element further
   short than one class, or carrying no specification reference of its own,
   cannot be recovered at all.
4. Cap how much of the assembly may lean on upscreening. Past the declared
   share the hybrid is an upscreened build wearing the target class, and the
   share comparison absorbs the representation error at an exact equality
   rather than loosening the cap.
5. Take the weakest admissible element as the effective class the assembled
   hybrid can claim, and report the unaided share, the recovered elements and
   every refused element behind that verdict.
"""

import math

__all__ = [
    "ELEMENT_KINDS",
    "PROCUREMENT_CLASSES",
    "CLASS_RANK",
    "DEFAULT_TARGET_CLASS",
    "DEFAULT_HYBRID_POLICY",
    "SHARE_TOLERANCE",
    "ADMISSIBLE_UNAIDED",
    "RECOVERABLE_BY_UPSCREENING",
    "ELEMENT_REFUSED",
    "HYBRID_ADMISSIBLE",
    "HYBRID_ADMISSIBLE_AFTER_UPSCREENING",
    "HYBRID_REFUSED",
    "PROCUREMENT_SPECIFICATION_MISSING",
    "class_rank",
    "validate_hybrid_policy",
    "validate_element",
    "validate_elements",
    "upscreening_declared",
    "element_disposition",
    "share_within_cap",
    "effective_hybrid_class",
    "assess_hybrid_procurement",
]

# The constituent elements a hybrid microcircuit is assembled from.
ELEMENT_KINDS = (
    "die",
    "chip-resistor",
    "chip-capacitor",
    "substrate",
    "interconnect",
    "package",
)

# Procurement classes in descending assurance order; rank 1 is the strongest.
PROCUREMENT_CLASSES = ("class-1", "class-2", "class-3", "uncontrolled")
CLASS_RANK = {name: index + 1 for index, name in enumerate(PROCUREMENT_CLASSES)}

DEFAULT_TARGET_CLASS = "class-2"

ADMISSIBLE_UNAIDED = "admissible-unaided"
RECOVERABLE_BY_UPSCREENING = "recoverable-by-upscreening"
ELEMENT_REFUSED = "element-refused"

HYBRID_ADMISSIBLE = "hybrid-admissible"
HYBRID_ADMISSIBLE_AFTER_UPSCREENING = "hybrid-admissible-after-upscreening"
HYBRID_REFUSED = "hybrid-refused"
PROCUREMENT_SPECIFICATION_MISSING = "procurement-specification-missing"

# A share comparison is a ratio of two small counts. An exact equality can land
# a few units in the last place on the wrong side; absorb that here instead of
# softening the cap.
SHARE_TOLERANCE = 1e-9

DEFAULT_HYBRID_POLICY = {
    # Largest share of the elements that may reach the target by upscreening.
    "max_upscreened_share": 0.5,
    # How far short of the target an element may be and still be recoverable.
    "max_recoverable_shortfall": 1,
}


def class_rank(name):
    """Return the assurance rank of a declared procurement class."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("procurement class must be a non-empty string")
    key = name.strip().lower()
    if key not in CLASS_RANK:
        raise ValueError(
            "unknown procurement class %r; declare one of %s"
            % (name, ", ".join(PROCUREMENT_CLASSES))
        )
    return CLASS_RANK[key]


def validate_hybrid_policy(policy=None):
    """Return a complete hybrid procurement policy, defaults filled in."""
    if policy is None:
        return dict(DEFAULT_HYBRID_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("hybrid policy must be a mapping")
    merged = dict(DEFAULT_HYBRID_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_HYBRID_POLICY:
            raise ValueError("unknown hybrid policy key %r" % (key,))
        merged[key] = value
    cap = merged["max_upscreened_share"]
    if not isinstance(cap, (int, float)) or isinstance(cap, bool):
        raise ValueError("max_upscreened_share must be a real number")
    cap = float(cap)
    if not math.isfinite(cap) or cap < 0.0 or cap > 1.0:
        raise ValueError("max_upscreened_share must be finite and lie in 0..1")
    merged["max_upscreened_share"] = cap
    shortfall = merged["max_recoverable_shortfall"]
    if not isinstance(shortfall, int) or isinstance(shortfall, bool) or shortfall < 0:
        raise ValueError("max_recoverable_shortfall must be a non-negative integer")
    return merged


def validate_element(record, label):
    """Return a normalised constituent element record."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % label)
    kind = record.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("%s needs a non-empty 'kind'" % label)
    key = kind.strip().lower()
    if key not in ELEMENT_KINDS:
        raise ValueError(
            "%s names unknown element kind %r; declare one of %s"
            % (label, kind, ", ".join(ELEMENT_KINDS))
        )
    reference = record.get("specification_reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError(
            "%s needs a non-empty 'specification_reference'; an element with no "
            "specification of its own cannot be graded" % label
        )
    procurement_class = record.get("procurement_class")
    rank = class_rank(procurement_class)
    upscreening = record.get("upscreening")
    if upscreening is not None and not isinstance(upscreening, dict):
        raise ValueError("%s 'upscreening' must be a mapping when present" % label)
    return {
        "kind": key,
        "specification_reference": reference.strip(),
        "procurement_class": procurement_class.strip().lower(),
        "rank": rank,
        "upscreening": upscreening,
    }


def validate_elements(elements):
    """Return the normalised element list of an offered hybrid."""
    if isinstance(elements, dict) or not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a sequence of element records")
    if not elements:
        raise ValueError("a hybrid needs at least one constituent element")
    normalised = []
    seen = set()
    for index, record in enumerate(elements):
        element = validate_element(record, "element %d" % index)
        marker = (element["kind"], element["specification_reference"])
        if marker in seen:
            raise ValueError(
                "element %d repeats kind %r against the same specification"
                % (index, element["kind"])
            )
        seen.add(marker)
        normalised.append(element)
    return tuple(normalised)


def upscreening_declared(element):
    """Return whether an element carries usable upscreening evidence."""
    if not isinstance(element, dict):
        raise ValueError("element must be a mapping")
    upscreening = element.get("upscreening")
    if not isinstance(upscreening, dict):
        return False
    specification = upscreening.get("specification")
    if not isinstance(specification, str) or not specification.strip():
        return False
    return upscreening.get("lot_traceability") is True


def element_disposition(element, target_class=DEFAULT_TARGET_CLASS, policy=None):
    """Return how one constituent element stands against the target class."""
    settings = validate_hybrid_policy(policy)
    if not isinstance(element, dict):
        raise ValueError("element must be a mapping")
    if "rank" in element and "kind" in element:
        normalised = element
    else:
        normalised = validate_element(element, "element")
    shortfall = normalised["rank"] - class_rank(target_class)
    if shortfall <= 0:
        return ADMISSIBLE_UNAIDED
    if shortfall <= settings["max_recoverable_shortfall"] and upscreening_declared(
        normalised
    ):
        return RECOVERABLE_BY_UPSCREENING
    return ELEMENT_REFUSED


def share_within_cap(share, cap):
    """Return whether a share sits within its cap, an exact equality included."""
    for label, value in (("share", share), ("cap", cap)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    have = float(share)
    limit = float(cap)
    return have < limit or math.isclose(
        have, limit, rel_tol=SHARE_TOLERANCE, abs_tol=SHARE_TOLERANCE
    )


def effective_hybrid_class(elements, target_class=DEFAULT_TARGET_CLASS, policy=None):
    """Return the weakest class the admissible elements let the hybrid claim."""
    normalised = validate_elements(elements)
    target_rank = class_rank(target_class)
    worst = 1
    for element in normalised:
        disposition = element_disposition(element, target_class, policy)
        if disposition == ELEMENT_REFUSED:
            rank = element["rank"]
        elif disposition == RECOVERABLE_BY_UPSCREENING:
            rank = target_rank
        else:
            rank = element["rank"]
        worst = max(worst, rank)
    for name, rank in CLASS_RANK.items():
        if rank == worst:
            return name
    raise ValueError("no procurement class carries rank %d" % worst)


def assess_hybrid_procurement(case):
    """Run the clause 5.6.3 intermediate-class hybrid procurement assessment.

    case keys: hybrid (mapping carrying procurement_specification), elements
    (sequence of element records), optional target_class, optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "hybrid" not in case:
        raise ValueError("case missing required key 'hybrid'")
    if "elements" not in case:
        raise ValueError("case missing required key 'elements'")
    settings = validate_hybrid_policy(case.get("policy"))
    target_class = case.get("target_class", DEFAULT_TARGET_CLASS)
    target_rank = class_rank(target_class)

    hybrid = case["hybrid"]
    if not isinstance(hybrid, dict):
        raise ValueError("hybrid must be a mapping")
    specification = hybrid.get("procurement_specification")
    if not isinstance(specification, str) or not specification.strip():
        return {
            "verdict": PROCUREMENT_SPECIFICATION_MISSING,
            "effective_class": None,
            "unaided_share": 0.0,
            "upscreened_share": 0.0,
            "recovered_elements": (),
            "refused_elements": (),
            "findings": [
                "the hybrid carries no procurement specification reference; no "
                "element grading can make it admissible at %s" % target_class
            ],
        }

    elements = validate_elements(case["elements"])
    unaided = []
    recovered = []
    refused = []
    for element in elements:
        disposition = element_disposition(element, target_class, settings)
        if disposition == ADMISSIBLE_UNAIDED:
            unaided.append(element)
        elif disposition == RECOVERABLE_BY_UPSCREENING:
            recovered.append(element)
        else:
            refused.append(element)

    total = float(len(elements))
    unaided_share = len(unaided) / total
    upscreened_share = len(recovered) / total
    cap_ok = share_within_cap(upscreened_share, settings["max_upscreened_share"])

    findings = []
    for element in refused:
        findings.append(
            "%s bought at %s is short of %s by more than the recoverable "
            "shortfall, or carries no upscreening evidence"
            % (element["kind"], element["procurement_class"], target_class)
        )
    for element in recovered:
        findings.append(
            "%s bought at %s reaches %s only through the declared upscreening "
            "specification" % (element["kind"], element["procurement_class"], target_class)
        )
    if not cap_ok:
        findings.append(
            "%.4f of the elements lean on upscreening against a cap of %.4f"
            % (upscreened_share, settings["max_upscreened_share"])
        )

    effective = effective_hybrid_class(elements, target_class, settings)

    if refused or not cap_ok:
        verdict = HYBRID_REFUSED
    elif recovered:
        verdict = HYBRID_ADMISSIBLE_AFTER_UPSCREENING
    else:
        verdict = HYBRID_ADMISSIBLE

    return {
        "verdict": verdict,
        "target_class": target_class,
        "effective_class": effective,
        "effective_rank": class_rank(effective),
        "target_rank": target_rank,
        "unaided_share": unaided_share,
        "upscreened_share": upscreened_share,
        "upscreened_share_cap": settings["max_upscreened_share"],
        "recovered_elements": tuple(element["kind"] for element in recovered),
        "refused_elements": tuple(element["kind"] for element in refused),
        "findings": findings,
    }
