"""Hybrid microcircuit procurement at the lowest commercial assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.6.3 (procurement of hybrid microcircuits
where the programme works at the lowest commercial assurance class).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the hybrid record: a reference, a declared procurement basis and
   the constituent elements the assembly was built from.
2. Validate every element: an identifier, a kind drawn from the recognised
   set, the basis it was itself bought against, whether a lot identity was
   retained for it and whether its source is held under change notification.
3. Refuse any element carrying no procurement reference of its own. An
   unreferenced element has an unknown basis, not a low one, and ranking it
   would invent the answer the reference was supposed to supply.
4. Rank each element basis and take the weakest present as the effective
   basis the assembled hybrid can claim. Assurance does not average across an
   assembly; the hybrid fails where its poorest element fails.
5. Weight lot traceability and source-change exposure by element criticality,
   sharing a kind's criticality equally between elements of that kind, and
   normalise over the kinds actually present.
6. Compare coverage against its floor and exposure against its cap through a
   named tolerance, counting an exact landing as met, and return one verdict.
"""

import math

__all__ = [
    "ROLLUP_TOLERANCE",
    "BASIS_RANK",
    "UNREFERENCED_BASIS",
    "ELEMENT_KINDS",
    "DEFAULT_CRITICALITY",
    "DEFAULT_BASIS_FLOOR",
    "DEFAULT_TRACEABILITY_FLOOR",
    "DEFAULT_EXPOSURE_CAP",
    "PROCUREMENT_VERDICTS",
    "validate_identifier",
    "validate_criticality",
    "basis_rank",
    "validate_element",
    "validate_elements",
    "element_weights",
    "weakest_basis",
    "weighted_share",
    "assess_hybrid_procurement",
]

# Shares are sums of criticality weights divided by a normalising total; a
# share that should land on its floor can sit a few ULPs either side. Absorb
# that here, never by moving the floor.
ROLLUP_TOLERANCE = 1e-9

# The document an element was actually bought against, ranked by how much of
# the element the buyer can hold the supplier to afterwards.
BASIS_RANK = {
    "unreferenced": 0,
    "catalogue-datasheet": 1,
    "vendor-detail-specification": 2,
    "generic-and-detail-specification": 3,
}

# An element offered with nothing behind it. Its basis is unknown, which is
# why it closes the assessment ahead of any ranking.
UNREFERENCED_BASIS = "unreferenced"

# What a hybrid is made of once the outer part number is opened up, and the
# share of the assembly's assurance argument each kind carries. The weights
# sum to unity.
DEFAULT_CRITICALITY = {
    "die": 0.34,
    "substrate": 0.20,
    "interconnect": 0.18,
    "chip-capacitor": 0.12,
    "chip-resistor": 0.08,
    "package-seal": 0.08,
}

ELEMENT_KINDS = tuple(sorted(DEFAULT_CRITICALITY))

# The lowest class accepts a catalogue datasheet as a floor; a programme may
# demand more by raising the floor, never by lowering it below a reference.
DEFAULT_BASIS_FLOOR = 1

DEFAULT_TRACEABILITY_FLOOR = 0.60
DEFAULT_EXPOSURE_CAP = 0.40

PROCUREMENT_VERDICTS = (
    "procurement-accepted",
    "accepted-with-recorded-exposure",
    "escalate-to-parts-control-board",
    "refuse-unreferenced-element",
)


def validate_identifier(value, label):
    """Return a non-blank stripped identifier, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_flag(value, label):
    """Return a strict boolean, or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _require_fraction(value, label):
    """Return a finite real number inside the unit interval, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return number


def _meets_floor(value, floor):
    """Return True when value reaches its floor, an exact landing counted in."""
    return value > floor or math.isclose(
        value, floor, rel_tol=0.0, abs_tol=ROLLUP_TOLERANCE
    )


def _within_cap(value, cap):
    """Return True when value stays under its cap, an exact landing counted in."""
    return value < cap or math.isclose(
        value, cap, rel_tol=0.0, abs_tol=ROLLUP_TOLERANCE
    )


def validate_criticality(weights=None):
    """Return a validated element-criticality mapping summing to unity."""
    if weights is None:
        weights = DEFAULT_CRITICALITY
    if not isinstance(weights, dict) or not weights:
        raise ValueError("criticality weights must be a non-empty mapping")
    cleaned = {}
    for name, value in weights.items():
        kind = validate_identifier(name, "criticality kind")
        if kind not in DEFAULT_CRITICALITY:
            raise ValueError(
                "%s is not a recognised hybrid element kind; declare it in the "
                "criticality map before weighting it" % kind
            )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("criticality of %s must be a real number" % kind)
        number = float(value)
        if not math.isfinite(number) or number <= 0.0:
            raise ValueError("criticality of %s must be positive and finite" % kind)
        cleaned[kind] = number
    total = math.fsum(cleaned.values())
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=ROLLUP_TOLERANCE):
        raise ValueError("criticality weights must sum to unity, got %.12f" % total)
    return cleaned


def basis_rank(name):
    """Return the rank of a declared procurement basis, or raise."""
    basis = validate_identifier(name, "procurement basis")
    if basis not in BASIS_RANK:
        raise ValueError("unknown procurement basis %s" % basis)
    return BASIS_RANK[basis]


def validate_element(element):
    """Return a normalised constituent-element record, or raise."""
    if not isinstance(element, dict):
        raise ValueError("each element must be a mapping")
    identifier = validate_identifier(element.get("identifier"), "element identifier")
    kind = validate_identifier(element.get("kind"), "element kind")
    if kind not in DEFAULT_CRITICALITY:
        raise ValueError("element %s has unrecognised kind %s" % (identifier, kind))
    basis = validate_identifier(element.get("basis"), "element basis")
    rank = basis_rank(basis)
    return {
        "identifier": identifier,
        "kind": kind,
        "basis": basis,
        "basis_rank": rank,
        "lot_traceable": _require_flag(
            element.get("lot_traceable"), "lot_traceable of %s" % identifier
        ),
        "change_notified": _require_flag(
            element.get("change_notified"), "change_notified of %s" % identifier
        ),
    }


def validate_elements(elements):
    """Return the normalised element list of one hybrid, or raise."""
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("elements must be a non-empty sequence")
    records = [validate_element(item) for item in elements]
    seen = set()
    for record in records:
        if record["identifier"] in seen:
            raise ValueError("element %s is listed twice" % record["identifier"])
        seen.add(record["identifier"])
    if not any(record["kind"] == "die" for record in records):
        raise ValueError("a hybrid element list must contain at least one die")
    return records


def element_weights(records, weights=None):
    """Return the criticality carried by each element, kind weight shared out."""
    graded = validate_criticality(weights)
    counts = {}
    for record in records:
        counts[record["kind"]] = counts.get(record["kind"], 0) + 1
    shares = []
    for record in records:
        kind = record["kind"]
        if kind not in graded:
            raise ValueError("kind %s carries no criticality weight" % kind)
        shares.append(graded[kind] / counts[kind])
    return tuple(shares)


def weakest_basis(records):
    """Return the poorest basis present and its rank."""
    if not records:
        raise ValueError("cannot take the weakest basis of an empty element list")
    poorest = min(records, key=lambda record: (record["basis_rank"], record["identifier"]))
    return poorest["basis"], poorest["basis_rank"]


def weighted_share(records, key, weights=None):
    """Return the share of assembly criticality whose flag is set."""
    if not isinstance(key, str) or key not in ("lot_traceable", "change_notified"):
        raise ValueError("key must be lot_traceable or change_notified, got %r" % (key,))
    shares = element_weights(records, weights)
    total = math.fsum(shares)
    if total <= 0.0:
        raise ValueError("element criticality total must be positive")
    held = math.fsum(
        share for record, share in zip(records, shares) if record[key]
    )
    return held / total


def assess_hybrid_procurement(record):
    """Run the full clause 6.6.3 lowest-class hybrid procurement assessment.

    record keys: reference, elements (non-empty sequence), optional
    basis_floor (default 1), optional traceability_floor, optional
    exposure_cap, optional criticality weights.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("reference", "elements"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    reference = validate_identifier(record["reference"], "hybrid reference")
    elements = validate_elements(record["elements"])
    graded = validate_criticality(record.get("criticality"))

    floor = record.get("basis_floor", DEFAULT_BASIS_FLOOR)
    if isinstance(floor, bool) or not isinstance(floor, int):
        raise ValueError("basis_floor must be an integer rank, got %r" % (floor,))
    if floor < 1 or floor > max(BASIS_RANK.values()):
        raise ValueError("basis_floor must name a referenced basis rank")

    traceability_floor = _require_fraction(
        record.get("traceability_floor", DEFAULT_TRACEABILITY_FLOOR),
        "traceability_floor",
    )
    exposure_cap = _require_fraction(
        record.get("exposure_cap", DEFAULT_EXPOSURE_CAP), "exposure_cap"
    )

    unreferenced = tuple(
        sorted(
            item["identifier"]
            for item in elements
            if item["basis"] == UNREFERENCED_BASIS
        )
    )
    basis_name, basis_value = weakest_basis(elements)
    shortfall = tuple(
        sorted(
            item["identifier"]
            for item in elements
            if item["basis_rank"] < floor
        )
    )
    coverage = weighted_share(elements, "lot_traceable", graded)
    exposure = 1.0 - weighted_share(elements, "change_notified", graded)
    untraceable = tuple(
        sorted(item["identifier"] for item in elements if not item["lot_traceable"])
    )
    exposed = tuple(
        sorted(item["identifier"] for item in elements if not item["change_notified"])
    )

    coverage_met = _meets_floor(coverage, traceability_floor)
    exposure_met = _within_cap(exposure, exposure_cap)

    findings = []
    for identifier in unreferenced:
        findings.append(
            {
                "severity": 0,
                "reference": identifier,
                "detail": "%s carries no procurement reference of its own" % identifier,
            }
        )
    for identifier in shortfall:
        if identifier in unreferenced:
            continue
        findings.append(
            {
                "severity": 1,
                "reference": identifier,
                "detail": "%s was bought below the declared basis floor" % identifier,
            }
        )
    if not coverage_met:
        findings.append(
            {
                "severity": 1,
                "reference": reference,
                "detail": "lot traceability covers %.4f of assembly criticality, "
                "below the %.4f floor" % (coverage, traceability_floor),
            }
        )
    if not exposure_met:
        findings.append(
            {
                "severity": 2,
                "reference": reference,
                "detail": "source-change exposure reaches %.4f of assembly "
                "criticality, above the %.4f cap" % (exposure, exposure_cap),
            }
        )
    findings.sort(key=lambda item: (item["severity"], item["reference"]))

    if unreferenced:
        verdict = "refuse-unreferenced-element"
    elif basis_value < floor or not coverage_met:
        verdict = "escalate-to-parts-control-board"
    elif not exposure_met:
        verdict = "accepted-with-recorded-exposure"
    else:
        verdict = "procurement-accepted"

    return {
        "reference": reference,
        "elements": tuple(elements),
        "effective_basis": basis_name,
        "effective_basis_rank": basis_value,
        "basis_floor": floor,
        "basis_shortfall": shortfall,
        "unreferenced_elements": unreferenced,
        "traceability_coverage": coverage,
        "traceability_floor": traceability_floor,
        "traceability_met": coverage_met,
        "untraceable_elements": untraceable,
        "source_change_exposure": exposure,
        "exposure_cap": exposure_cap,
        "exposure_met": exposure_met,
        "exposed_elements": exposed,
        "findings": findings,
        "verdict": verdict,
    }
