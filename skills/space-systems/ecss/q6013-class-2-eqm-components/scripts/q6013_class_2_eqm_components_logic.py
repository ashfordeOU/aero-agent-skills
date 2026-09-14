"""Commercial parts fitted to an engineering qualification model, Class 2.

Anchor: ECSS-Q-ST-60-13C clause 5.1.6 (commercial components fitted to an
engineering qualification model at the intermediate assurance class, and how
far they have to match the flight build for the qualification result to carry
over). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Compare each fitted component with its flight-intended counterpart across
   the catalogued build-standard attributes and collect the deviations.
2. Convert every deviation into a per-domain transfer-credit loss. A deviation
   does not remove the whole qualification argument; it removes a declared
   share of the domains it actually touches, so a package change costs the
   mechanical domain outright and the thermal domain in part.
3. Restore part of a loss only where a deviation acceptance record exists that
   names a justification and a delta test covering that domain. This graded
   restoration is what separates the intermediate class from the highest one,
   where a deviation simply removes the argument.
4. Refuse restoration on a manufacturer or part-number change: the model
   carries a different part, and no delta test turns it back into the one that
   will fly.
5. Categorize each component against the declared credit floor, accumulate the
   delta-test retest set, and return one model-level transfer verdict.
"""

import math

__all__ = [
    "CREDIT_TOLERANCE",
    "TRANSFER_DOMAINS",
    "ATTRIBUTE_DOMAIN_LOSS",
    "FUNDAMENTAL_ATTRIBUTES",
    "DEFAULT_CREDIT_FLOOR",
    "DEFAULT_ACCEPTANCE_CREDIT",
    "COMPONENT_CATEGORIES",
    "validate_acceptance",
    "compare_build_standard",
    "domain_transfer_credit",
    "domains_below_floor",
    "component_category",
    "evaluate_eqm_component",
    "model_domain_credit",
    "assess_class2_eqm_transfer",
]

# Credits are products of declared shares; an exactly-met floor can land a few
# ULPs low. Absorb that here, never by moving the floor.
CREDIT_TOLERANCE = 1e-9

TRANSFER_DOMAINS = ("electrical", "lifetime", "mechanical", "radiation", "thermal")

# Build-standard attribute -> the share of each qualification domain's transfer
# credit that a deviation on that attribute removes. A domain absent from an
# entry is untouched by that deviation.
ATTRIBUTE_DOMAIN_LOSS = {
    "manufacturer": {
        "electrical": 1.0,
        "lifetime": 1.0,
        "mechanical": 1.0,
        "radiation": 1.0,
        "thermal": 1.0,
    },
    "part_number": {
        "electrical": 1.0,
        "lifetime": 1.0,
        "mechanical": 1.0,
        "radiation": 1.0,
        "thermal": 1.0,
    },
    "package": {"mechanical": 1.0, "thermal": 0.6},
    "die_lot": {"lifetime": 0.8, "radiation": 1.0},
    "screening_flow": {"lifetime": 0.6, "electrical": 0.3},
    "board_mounting": {"mechanical": 0.7, "thermal": 0.4},
    "date_code_range": {"lifetime": 0.3},
}

# Attributes on which a deviation makes the fitted part a different part rather
# than a less representative one. No acceptance record restores credit here.
FUNDAMENTAL_ATTRIBUTES = ("manufacturer", "part_number")

DEFAULT_CREDIT_FLOOR = 0.7
DEFAULT_ACCEPTANCE_CREDIT = 0.5

COMPONENT_CATEGORIES = (
    "representative",
    "delta-credited",
    "non-representative",
)

_CATEGORY_SEVERITY = {
    "non-representative": 0,
    "delta-credited": 1,
    "representative": 2,
}


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_positive_int(value, label):
    """Return a strictly positive integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def _require_unit_interval(value, label, allow_zero=True):
    """Return a finite float inside [0, 1], or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    if not allow_zero and number == 0.0:
        raise ValueError("%s must be strictly positive" % label)
    return number


def _meets(value, limit):
    """Return True when value is at or above limit, tolerating representation error."""
    return value > limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=CREDIT_TOLERANCE
    )


def validate_acceptance(record, deviations):
    """Return a validated deviation acceptance record.

    record keys: attribute, justification, delta_test, domains (sequence of
    qualification domains the delta test covers), optional credit.
    """
    if not isinstance(record, dict):
        raise ValueError("each acceptance record must be a mapping")
    if not isinstance(deviations, (list, tuple)):
        raise ValueError("deviations must be a sequence of attribute names")
    attribute = _require_text(record.get("attribute"), "acceptance attribute")
    if attribute not in ATTRIBUTE_DOMAIN_LOSS:
        raise ValueError("attribute %s is not a catalogued build-standard attribute" % attribute)
    if attribute in FUNDAMENTAL_ATTRIBUTES:
        raise ValueError(
            "attribute %s cannot be accepted: the model carries a different part, "
            "not a less representative one" % attribute
        )
    if attribute not in deviations:
        raise ValueError(
            "acceptance record for %s, which does not deviate on this component" % attribute
        )
    justification = _require_text(record.get("justification"), "acceptance justification")
    delta_test = _require_text(record.get("delta_test"), "acceptance delta test")
    domains = record.get("domains")
    if not isinstance(domains, (list, tuple)) or not domains:
        raise ValueError("acceptance record for %s must name the domains its delta test covers" % attribute)
    touched = ATTRIBUTE_DOMAIN_LOSS[attribute]
    covered = []
    for entry in domains:
        domain = _require_text(entry, "acceptance domain")
        if domain not in TRANSFER_DOMAINS:
            raise ValueError("%s is not a qualification transfer domain" % domain)
        if domain not in touched:
            raise ValueError(
                "delta test claims the %s domain, which a %s deviation does not remove"
                % (domain, attribute)
            )
        if domain in covered:
            raise ValueError("domain %s listed more than once for %s" % (domain, attribute))
        covered.append(domain)
    credit = _require_unit_interval(
        record.get("credit", DEFAULT_ACCEPTANCE_CREDIT), "acceptance credit", allow_zero=False
    )
    return {
        "attribute": attribute,
        "justification": justification,
        "delta_test": delta_test,
        "domains": tuple(sorted(covered)),
        "credit": credit,
    }


def compare_build_standard(fitted, intended):
    """Return the catalogued attributes on which a fitted part differs from the flight part."""
    for label, mapping in (("fitted", fitted), ("intended", intended)):
        if not isinstance(mapping, dict):
            raise ValueError("%s component must be a mapping" % label)
    deviations = []
    for attribute in sorted(ATTRIBUTE_DOMAIN_LOSS):
        if attribute not in fitted:
            raise ValueError("fitted component lacks the attribute %s" % attribute)
        if attribute not in intended:
            raise ValueError("intended component lacks the attribute %s" % attribute)
        left = _require_text(fitted[attribute], "fitted %s" % attribute).lower()
        right = _require_text(intended[attribute], "intended %s" % attribute).lower()
        if left != right:
            deviations.append(attribute)
    return tuple(deviations)


def domain_transfer_credit(deviations, acceptances=()):
    """Return the per-domain transfer credit left after the deviations."""
    if not isinstance(deviations, (list, tuple)):
        raise ValueError("deviations must be a sequence of attribute names")
    names = []
    for entry in deviations:
        attribute = _require_text(entry, "deviation attribute")
        if attribute not in ATTRIBUTE_DOMAIN_LOSS:
            raise ValueError("deviation %s is not a catalogued build-standard attribute" % attribute)
        if attribute in names:
            raise ValueError("deviation %s listed more than once" % attribute)
        names.append(attribute)
    if not isinstance(acceptances, (list, tuple)):
        raise ValueError("acceptances must be a sequence of records")
    restored = {}
    for record in acceptances:
        checked = validate_acceptance(record, names)
        if checked["attribute"] in restored:
            raise ValueError("more than one acceptance record for %s" % checked["attribute"])
        restored[checked["attribute"]] = checked

    credits = {}
    for domain in TRANSFER_DOMAINS:
        value = 1.0
        for attribute in names:
            loss = ATTRIBUTE_DOMAIN_LOSS[attribute].get(domain)
            if loss is None:
                continue
            record = restored.get(attribute)
            if record is not None and domain in record["domains"]:
                loss = loss * (1.0 - record["credit"])
            value = value * (1.0 - loss)
        if value < 0.0:
            value = 0.0
        credits[domain] = value
    return credits


def domains_below_floor(credits, floor=DEFAULT_CREDIT_FLOOR):
    """Return the qualification domains whose transfer credit falls under the floor."""
    if not isinstance(credits, dict) or not credits:
        raise ValueError("credits must be a non-empty mapping of domain to credit")
    limit = _require_unit_interval(floor, "credit floor")
    short = []
    for domain in sorted(credits):
        if domain not in TRANSFER_DOMAINS:
            raise ValueError("%s is not a qualification transfer domain" % domain)
        value = _require_unit_interval(credits[domain], "credit of %s" % domain)
        if not _meets(value, limit):
            short.append(domain)
    return tuple(short)


def component_category(deviations, credits, floor=DEFAULT_CREDIT_FLOOR):
    """Return the representativeness category earned by a fitted component."""
    if not isinstance(deviations, (list, tuple)):
        raise ValueError("deviations must be a sequence of attribute names")
    names = [_require_text(entry, "deviation attribute") for entry in deviations]
    short = domains_below_floor(credits, floor)
    if any(name in FUNDAMENTAL_ATTRIBUTES for name in names):
        return "non-representative"
    if short:
        return "non-representative"
    if not names:
        return "representative"
    return "delta-credited"


def evaluate_eqm_component(item, floor=DEFAULT_CREDIT_FLOOR):
    """Return the transfer record of one fitted component.

    item keys: reference, fitted (mapping), intended (mapping), optional
    quantity (default 1), optional acceptances (sequence of records).
    """
    if not isinstance(item, dict):
        raise ValueError("each component item must be a mapping")
    reference = _require_text(item.get("reference"), "reference")
    quantity = _require_positive_int(item.get("quantity", 1), "quantity")
    deviations = compare_build_standard(item.get("fitted"), item.get("intended"))
    acceptances = item.get("acceptances", ())
    credits = domain_transfer_credit(deviations, acceptances)
    accepted = tuple(
        sorted(validate_acceptance(record, deviations)["attribute"] for record in acceptances)
    )
    undocumented = tuple(
        name for name in deviations if name not in accepted and name not in FUNDAMENTAL_ATTRIBUTES
    )
    return {
        "reference": reference,
        "quantity": quantity,
        "deviations": deviations,
        "accepted_deviations": accepted,
        "undocumented_deviations": undocumented,
        "domain_credit": credits,
        "retest_domains": domains_below_floor(credits, floor),
        "category": component_category(deviations, credits, floor),
    }


def model_domain_credit(records):
    """Return the quantity-weighted per-domain transfer credit of the whole model."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of component records")
    total = 0
    for record in records:
        if not isinstance(record, dict) or "domain_credit" not in record:
            raise ValueError("each record must carry 'domain_credit'")
        total += _require_positive_int(record.get("quantity", 1), "quantity")
    credits = {}
    for domain in TRANSFER_DOMAINS:
        credits[domain] = (
            math.fsum(
                record["domain_credit"][domain] * record.get("quantity", 1)
                for record in records
            )
            / total
        )
    return credits


def assess_class2_eqm_transfer(spec):
    """Run the full clause 5.1.6 intermediate-class model transfer assessment.

    spec keys: components (sequence of items), optional floor (default 0.7).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "components" not in spec:
        raise ValueError("spec missing required key 'components'")
    components = spec["components"]
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError("spec['components'] must be a non-empty sequence")
    floor = _require_unit_interval(spec.get("floor", DEFAULT_CREDIT_FLOOR), "credit floor")

    records = []
    seen = set()
    for item in components:
        record = evaluate_eqm_component(item, floor)
        if record["reference"] in seen:
            raise ValueError("component reference %s appears more than once" % record["reference"])
        seen.add(record["reference"])
        records.append(record)

    model_credit = model_domain_credit(records)
    retest = set()
    for record in records:
        retest.update(record["retest_domains"])
    retest.update(domains_below_floor(model_credit, floor))

    counts = {category: 0 for category in COMPONENT_CATEGORIES}
    for record in records:
        counts[record["category"]] += 1

    findings = []
    for record in records:
        if record["category"] != "representative":
            findings.append(
                {
                    "severity": _CATEGORY_SEVERITY[record["category"]],
                    "reference": record["reference"],
                    "detail": "%s deviates on %s; retest %s"
                    % (
                        record["reference"],
                        ", ".join(record["deviations"]),
                        ", ".join(record["retest_domains"]) or "none",
                    ),
                }
            )
        if record["undocumented_deviations"]:
            findings.append(
                {
                    "severity": 1,
                    "reference": record["reference"],
                    "detail": "%s carries no acceptance record for %s"
                    % (record["reference"], ", ".join(record["undocumented_deviations"])),
                }
            )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"], entry["detail"]))

    if counts["non-representative"]:
        verdict = "not-transferable"
    elif counts["delta-credited"]:
        verdict = "transferable-with-delta-tests"
    else:
        verdict = "transferable"
    return {
        "records": records,
        "model_domain_credit": model_credit,
        "floor": floor,
        "category_counts": counts,
        "retest_domains": tuple(sorted(retest)),
        "findings": findings,
        "verdict": verdict,
    }
