#!/usr/bin/env python3
"""Power-handling design and verification logic (ECSS-E-ST-20C cl. 7.3.2.2).

Deterministic, offline, stdlib only. The standard is cited as the anchor
only; the procedure below is a paraphrase, not standard text.

Scope: raise the maximum operating radio-frequency power of each chain
element by the agreed power-handling margin, check the declared design
capability against the resulting required design level, and judge the
substantiation offered for it.
"""

import math

# --- domain constants ------------------------------------------------------

# Category allowance in decibels. Thermally governed elements are well
# predicted; field-governed elements have a sharp onset and carry more.
CATEGORY_MARGIN_DB = {
    "waveguide-run": 3.0,
    "coaxial-line": 3.0,
    "terminating-load": 3.0,
    "filter-or-diplexer": 6.0,
    "switch-or-rotary-joint": 6.0,
    "antenna-feed": 6.0,
    "connector-or-transition": 6.0,
}

SUBSTANTIATION_METHODS = (
    "verification-by-test",
    "verification-by-analysis",
    "verification-by-similarity",
)

_METHOD_ALIASES = {
    "test": "verification-by-test",
    "measurement": "verification-by-test",
    "verification-by-test": "verification-by-test",
    "analysis": "verification-by-analysis",
    "prediction": "verification-by-analysis",
    "verification-by-analysis": "verification-by-analysis",
    "similarity": "verification-by-similarity",
    "heritage": "verification-by-similarity",
    "verification-by-similarity": "verification-by-similarity",
}

# Allowance added for the uncertainty of the substantiation route itself.
METHOD_MARGIN_ADDER_DB = {
    "verification-by-test": 0.0,
    "verification-by-analysis": 3.0,
    "verification-by-similarity": 4.0,
}

# Agreed minimum dwell at the elevated level, in minutes.
MIN_DWELL_MINUTES = 30.0

# Absorbs decibel and summation representation error at an exactly-met level.
LEVEL_TOLERANCE = 1e-9


def _is_real(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_positive(value, label):
    if not _is_real(value):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return float(value)


# --- normalization ---------------------------------------------------------


def normalize_category(category):
    """Return the canonical chain-element category token."""
    if not isinstance(category, str):
        raise ValueError("element category must be a string, got %r" % (category,))
    key = category.strip().lower()
    if key not in CATEGORY_MARGIN_DB:
        raise ValueError(
            "unknown chain element category %r; expected one of %s"
            % (category, ", ".join(sorted(CATEGORY_MARGIN_DB)))
        )
    return key


def normalize_method(method):
    """Return the canonical substantiation-method token."""
    if not isinstance(method, str):
        raise ValueError("substantiation method must be a string, got %r" % (method,))
    key = method.strip().lower()
    if not key:
        raise ValueError("substantiation method must not be empty")
    resolved = _METHOD_ALIASES.get(key)
    if resolved is None:
        raise ValueError(
            "unknown substantiation method %r; expected one of %s"
            % (method, ", ".join(SUBSTANTIATION_METHODS))
        )
    return resolved


# --- margin arithmetic -----------------------------------------------------


def resolve_margin_db(category, method, agreed_margins=None):
    """Agreed power-handling margin for one element, in decibels.

    The category allowance (optionally overridden by a programme-agreed
    value) plus the allowance implied by the substantiation method.
    """
    key = normalize_category(category)
    route = normalize_method(method)
    base = CATEGORY_MARGIN_DB[key]
    if agreed_margins is not None:
        if not isinstance(agreed_margins, dict):
            raise ValueError(
                "agreed margins must be a mapping, got %r" % (agreed_margins,)
            )
        if key in agreed_margins:
            override = agreed_margins[key]
            if not _is_real(override):
                raise ValueError(
                    "agreed margin for %r must be a real number, got %r"
                    % (key, override)
                )
            if override < 0:
                raise ValueError(
                    "agreed margin for %r is negative (%r); a negative margin is "
                    "a deficit, not an agreement" % (key, override)
                )
            base = float(override)
    return base + METHOD_MARGIN_ADDER_DB[route]


def required_design_level_w(max_operating_w, margin_db):
    """Maximum operating level raised by the agreed margin, in watts."""
    operating = _require_positive(max_operating_w, "maximum operating level")
    if not _is_real(margin_db):
        raise ValueError("margin must be a real number, got %r" % (margin_db,))
    if margin_db < 0:
        raise ValueError("margin must not be negative, got %r" % (margin_db,))
    return operating * 10.0 ** (margin_db / 10.0)


def demonstrated_margin_db(capability_w, max_operating_w):
    """Margin in decibels that a capability actually supports."""
    capability = _require_positive(capability_w, "capability")
    operating = _require_positive(max_operating_w, "maximum operating level")
    return 10.0 * math.log10(capability / operating)


def meets_required_level(value_w, required_w):
    """True when a level reaches the required design level.

    Absorbs floating-point representation error at an exactly-met level;
    it never reduces the agreed margin.
    """
    if value_w >= required_w:
        return True
    return math.isclose(value_w, required_w, rel_tol=LEVEL_TOLERANCE, abs_tol=1e-15)


# --- substantiation --------------------------------------------------------


def substantiation_findings(substantiation, required_level_w):
    """Findings raised by one substantiation block against the required level."""
    if not isinstance(substantiation, dict):
        raise ValueError(
            "substantiation must be a mapping, got %r" % (substantiation,)
        )
    method = normalize_method(substantiation.get("method"))
    findings = []

    if method == "verification-by-test":
        applied = substantiation.get("applied_level_w")
        if applied is None:
            findings.append("substantiation-missing-applied-level")
        else:
            applied = _require_positive(applied, "applied level")
            if not meets_required_level(applied, required_level_w):
                findings.append(
                    "applied-level-below-required-design-level: %.4g W against %.4g W"
                    % (applied, required_level_w)
                )
        dwell = substantiation.get("dwell_minutes")
        if dwell is None:
            findings.append("substantiation-missing-dwell")
        else:
            if not _is_real(dwell) or dwell < 0:
                raise ValueError("dwell must be a non-negative real number, got %r" % (dwell,))
            if dwell < MIN_DWELL_MINUTES and not math.isclose(
                dwell, MIN_DWELL_MINUTES, rel_tol=LEVEL_TOLERANCE
            ):
                findings.append(
                    "dwell-below-agreed-minimum: %.4g min against %.4g min"
                    % (dwell, MIN_DWELL_MINUTES)
                )
    elif method == "verification-by-analysis":
        if not str(substantiation.get("model_reference", "")).strip():
            findings.append("substantiation-missing-model-reference")
        if not bool(substantiation.get("model_correlated", False)):
            findings.append(
                "analysis-model-not-correlated: an uncorrelated model is a hypothesis"
            )
        predicted = substantiation.get("predicted_capability_w")
        if predicted is None:
            findings.append("substantiation-missing-predicted-capability")
        else:
            predicted = _require_positive(predicted, "predicted capability")
            if not meets_required_level(predicted, required_level_w):
                findings.append(
                    "predicted-capability-below-required-design-level: "
                    "%.4g W against %.4g W" % (predicted, required_level_w)
                )
    else:
        if not str(substantiation.get("heritage_reference", "")).strip():
            findings.append("substantiation-missing-heritage-reference")
        if not str(substantiation.get("delta_environment", "")).strip():
            findings.append(
                "similarity-without-delta-environment: the flight and heritage "
                "environments are asserted equal"
            )
        heritage = substantiation.get("heritage_capability_w")
        if heritage is None:
            findings.append("substantiation-missing-heritage-capability")
        else:
            heritage = _require_positive(heritage, "heritage capability")
            if not meets_required_level(heritage, required_level_w):
                findings.append(
                    "heritage-capability-below-required-design-level: "
                    "%.4g W against %.4g W" % (heritage, required_level_w)
                )
    return method, findings


# --- element and chain assessment -----------------------------------------


def evaluate_element(element, agreed_margins=None):
    """Evaluate one chain element against clause 7.3.2.2."""
    if not isinstance(element, dict):
        raise ValueError("element must be a mapping, got %r" % (element,))
    ident = element.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("element is missing a non-empty 'id'")
    ident = ident.strip()
    category = normalize_category(element.get("category"))
    operating = _require_positive(
        element.get("max_operating_w"), "element %r maximum operating level" % ident
    )
    capability = _require_positive(
        element.get("design_capability_w"), "element %r design capability" % ident
    )
    substantiation = element.get("substantiation")
    if substantiation is None:
        raise ValueError("element %r carries no substantiation block" % ident)

    method = normalize_method(substantiation.get("method"))
    margin_db = resolve_margin_db(category, method, agreed_margins)
    required = required_design_level_w(operating, margin_db)

    findings = []
    if not meets_required_level(capability, required):
        findings.append(
            "design-capability-below-required-design-level: %.4g W against %.4g W"
            % (capability, required)
        )
    _, evidence_findings = substantiation_findings(substantiation, required)
    findings.extend(evidence_findings)

    achieved = demonstrated_margin_db(capability, operating)
    return {
        "id": ident,
        "category": category,
        "method": method,
        "max_operating_w": operating,
        "agreed_margin_db": margin_db,
        "required_design_level_w": required,
        "design_capability_w": capability,
        "demonstrated_margin_db": achieved,
        "margin_shortfall_db": max(0.0, margin_db - achieved),
        "findings": findings,
        "compliant": not findings,
    }


def assess_power_handling_design_and_verification(elements, agreed_margins=None):
    """Assess a whole chain against clause 7.3.2.2."""
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a list, got %r" % (elements,))
    if not elements:
        raise ValueError("element list must not be empty")

    results = []
    seen = set()
    for element in elements:
        result = evaluate_element(element, agreed_margins)
        if result["id"] in seen:
            raise ValueError("duplicate element identifier %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)

    worst = min(results, key=lambda r: r["demonstrated_margin_db"] - r["agreed_margin_db"])
    counts = {}
    for result in results:
        for finding in result["findings"]:
            code = finding.split(":", 1)[0]
            counts[code] = counts.get(code, 0) + 1
    return {
        "results": results,
        "finding_counts": counts,
        "finding_total": sum(counts.values()),
        "worst_element_id": worst["id"],
        "worst_margin_shortfall_db": worst["margin_shortfall_db"],
        "compliant": all(r["compliant"] for r in results),
    }
