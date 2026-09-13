#!/usr/bin/env python3
"""Arcing provisions for exposed power-chain elements - ECSS-E-ST-20-06C
clause 7.3 (anchor only).

Clause 7.2 controls arcing on the solar-array itself; clause 7.3 extends the
same provisions outward to every other exposed element that carries the
generated current - drive mechanisms, rotary-transfer assemblies, exposed
harness runs and the exposed faces of conditioning units.

The module is deterministic, offline and stdlib-only. For each element it:

1. categorizes the element kind into one of four families;
2. computes the largest conductor-to-conductor differential it presents and
   the most negative exposed potential relative to the ambient plasma;
3. derives the arcing regime from those two figures against the
   primary-arc-inception and sustained-arc thresholds;
4. expands the family baseline into the provision set that regime demands;
5. compares the recorded provisions and bonding-resistance against that set
   and reports the shortfall.

No verbatim standard text is reproduced here.
"""

import math

__all__ = [
    "ELEMENT_FAMILIES",
    "FAMILY_BASELINE_PROVISIONS",
    "KNOWN_PROVISIONS",
    "ARCING_REGIMES",
    "PRIMARY_ARC_INCEPTION_V",
    "SUSTAINED_ARC_DIFFERENTIAL_V",
    "BONDING_RESISTANCE_LIMIT_OHM",
    "categorize_power_chain_element",
    "largest_conductor_differential",
    "most_negative_plasma_relative_potential",
    "categorize_arcing_regime",
    "required_provisions",
    "check_bonding_resistance",
    "evaluate_element",
    "assess_exposed_power_chain",
]

# Representation tolerance: differentials arrive as differences of two
# potentials, so an exactly-at-threshold element can land a few ULPs either
# side. The tolerance absorbs that only; the thresholds are never widened.
REL_TOL = 1e-9
ABS_TOL = 1e-12

# Magnitude of the negative potential relative to the ambient plasma at which
# a trigger (primary) arc on an exposed dielectric-conductor junction becomes
# credible.
PRIMARY_ARC_INCEPTION_V = 100.0

# Conductor-to-conductor differential above which the generated current can
# sustain a discharge once a trigger arc has struck.
SUSTAINED_ARC_DIFFERENTIAL_V = 55.0

# Maximum bonding-resistance of an exposed element to structure.
BONDING_RESISTANCE_LIMIT_OHM = 0.010

ELEMENT_FAMILIES = {
    "solar-array-drive-mechanism": "drive-mechanism",
    "gimbal-drive-unit": "drive-mechanism",
    "deployment-hinge": "drive-mechanism",
    "boom-articulation-joint": "drive-mechanism",
    "slip-ring-assembly": "rotary-transfer",
    "twist-capsule": "rotary-transfer",
    "rotary-transformer": "rotary-transfer",
    "exposed-harness-run": "conductor-run",
    "connector-backshell": "conductor-run",
    "bus-bar": "conductor-run",
    "array-string-interconnect": "conductor-run",
    "conditioning-unit-chassis": "conditioning-unit",
    "shunt-regulator-radiator": "conditioning-unit",
    "junction-box": "conditioning-unit",
}

FAMILY_BASELINE_PROVISIONS = {
    "drive-mechanism": ("bonding-to-structure", "insulation-barrier"),
    "rotary-transfer": ("bonding-to-structure", "insulation-barrier", "track-separation"),
    "conductor-run": ("bonding-to-structure", "insulation-barrier"),
    "conditioning-unit": ("bonding-to-structure", "insulation-barrier"),
}

# Provisions added by the arcing regime on top of the family baseline.
PRIMARY_ARC_PROVISIONS = ("primary-arc-mitigation",)
SUSTAINED_ARC_PROVISIONS = ("secondary-arc-evidence", "gap-integrity-inspection")

KNOWN_PROVISIONS = (
    "bonding-to-structure",
    "insulation-barrier",
    "track-separation",
    "primary-arc-mitigation",
    "secondary-arc-evidence",
    "gap-integrity-inspection",
)

ARCING_REGIMES = ("below-arcing-thresholds", "primary-arc-risk", "sustained-arc-risk")


def _ge(value, limit):
    """value >= limit, tolerant of float representation error at equality."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _le(value, limit):
    """value <= limit, tolerant of float representation error at equality."""
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _real(value, name, context):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: %s must be a real number, got %r" % (context, name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: %s must be finite, got %r" % (context, name, value))
    return value


def _mapping(value, context):
    if not isinstance(value, dict):
        raise ValueError("%s: expected a mapping, got %s" % (context, type(value).__name__))
    return value


def categorize_power_chain_element(kind):
    """Map an element kind onto its provision family.

    Raises ValueError for an uncategorized kind: clause 7.3 has to be applied
    deliberately to every exposed element, so an unrecognized one is a gap in
    the inventory, never a silent pass.
    """
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("element kind must be a non-empty string, got %r" % (kind,))
    family = ELEMENT_FAMILIES.get(kind)
    if family is None:
        raise ValueError(
            "uncategorized power-chain element kind %r; known kinds: %s"
            % (kind, ", ".join(sorted(ELEMENT_FAMILIES)))
        )
    return family


def largest_conductor_differential(potentials, context="element"):
    """Largest potential difference among the exposed conductors of one element.

    ``potentials`` are referred to spacecraft ground and need at least two
    entries - an exposed element of the chain always presents a feed and a
    return.
    """
    if not isinstance(potentials, (list, tuple)):
        raise ValueError("%s: exposed conductor potentials must be a list" % context)
    if len(potentials) < 2:
        raise ValueError(
            "%s: need at least two exposed conductor potentials, got %d"
            % (context, len(potentials))
        )
    values = [_real(v, "exposed conductor potential", context) for v in potentials]
    return max(values) - min(values)


def most_negative_plasma_relative_potential(potentials, ground_potential_v, context="element"):
    """Most negative exposed potential referred to the ambient plasma.

    Exposed conductor potentials are referred to spacecraft ground; the ground
    itself floats at ``ground_potential_v`` relative to the plasma, so the two
    add.
    """
    if not isinstance(potentials, (list, tuple)) or not potentials:
        raise ValueError("%s: exposed conductor potentials must be a non-empty list" % context)
    ground = _real(ground_potential_v, "ground_potential_v", context)
    values = [_real(v, "exposed conductor potential", context) + ground for v in potentials]
    return min(values)


def categorize_arcing_regime(
    differential_v,
    plasma_relative_potential_v,
    plasma_exposed,
    primary_threshold_v=PRIMARY_ARC_INCEPTION_V,
    sustained_threshold_v=SUSTAINED_ARC_DIFFERENTIAL_V,
):
    """Categorize the arcing regime of one element.

    An element shielded from the ambient plasma cannot strike a trigger arc,
    so it stays below the arcing thresholds whatever differential it carries.
    A plasma-exposed element whose most negative potential reaches the
    inception magnitude is at primary-arc risk; if it also carries a
    differential able to feed the discharge, it is at sustained-arc risk.
    """
    if not isinstance(plasma_exposed, bool):
        raise ValueError("plasma_exposed must be a boolean, got %r" % (plasma_exposed,))
    primary = _real(primary_threshold_v, "primary_threshold_v", "regime")
    sustained = _real(sustained_threshold_v, "sustained_threshold_v", "regime")
    if primary <= 0.0 or sustained <= 0.0:
        raise ValueError("arcing thresholds must be positive magnitudes")
    differential = _real(differential_v, "differential_v", "regime")
    if differential < 0.0:
        raise ValueError("differential_v must be a magnitude, got %g" % differential)
    relative = _real(plasma_relative_potential_v, "plasma_relative_potential_v", "regime")

    if not plasma_exposed:
        return "below-arcing-thresholds"
    if not _ge(abs(min(relative, 0.0)), primary):
        return "below-arcing-thresholds"
    if _ge(differential, sustained):
        return "sustained-arc-risk"
    return "primary-arc-risk"


def required_provisions(family, regime):
    """Provision set an element of ``family`` in ``regime`` has to carry."""
    if family not in FAMILY_BASELINE_PROVISIONS:
        raise ValueError("unknown provision family %r" % (family,))
    if regime not in ARCING_REGIMES:
        raise ValueError("unknown arcing regime %r" % (regime,))
    provisions = set(FAMILY_BASELINE_PROVISIONS[family])
    if regime in ("primary-arc-risk", "sustained-arc-risk"):
        provisions.update(PRIMARY_ARC_PROVISIONS)
    if regime == "sustained-arc-risk":
        provisions.update(SUSTAINED_ARC_PROVISIONS)
    return tuple(sorted(provisions))


def check_bonding_resistance(element, limit_ohm=BONDING_RESISTANCE_LIMIT_OHM):
    """Findings on the bonding-resistance of one element to structure."""
    element = _mapping(element, "element")
    limit = _real(limit_ohm, "limit_ohm", "bonding")
    if limit <= 0.0:
        raise ValueError("bonding-resistance limit must be positive, got %g" % limit)
    if "bonding_resistance_ohm" not in element:
        return ["bonding-resistance not on record"]
    value = _real(element["bonding_resistance_ohm"], "bonding_resistance_ohm", "element")
    if value < 0.0:
        raise ValueError("element: bonding_resistance_ohm must be non-negative, got %g" % value)
    if not _le(value, limit):
        return [
            "bonding-resistance %.4g ohm exceeds the %.4g ohm limit" % (value, limit)
        ]
    return []


def evaluate_element(
    element,
    primary_threshold_v=PRIMARY_ARC_INCEPTION_V,
    sustained_threshold_v=SUSTAINED_ARC_DIFFERENTIAL_V,
    bonding_limit_ohm=BONDING_RESISTANCE_LIMIT_OHM,
):
    """Evaluate one exposed element against the clause 7.3 provisions.

    Required keys: ``id``, ``kind``, ``plasma_exposed`` (bool),
    ``exposed_conductor_potentials_v`` (>= 2 values referred to spacecraft
    ground), ``ground_potential_v``. Optional: ``provisions`` (list of
    KNOWN_PROVISIONS), ``bonding_resistance_ohm``.
    """
    element = _mapping(element, "element")
    identifier = element.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("element: 'id' must be a non-empty string, got %r" % (identifier,))
    context = "element %s" % identifier

    if "kind" not in element:
        raise ValueError("%s: missing required field 'kind'" % context)
    family = categorize_power_chain_element(element["kind"])

    if "plasma_exposed" not in element:
        raise ValueError("%s: missing required field 'plasma_exposed'" % context)
    exposed = element["plasma_exposed"]
    if not isinstance(exposed, bool):
        raise ValueError("%s: 'plasma_exposed' must be a boolean" % context)

    if "exposed_conductor_potentials_v" not in element:
        raise ValueError("%s: missing required field 'exposed_conductor_potentials_v'" % context)
    if "ground_potential_v" not in element:
        raise ValueError("%s: missing required field 'ground_potential_v'" % context)

    potentials = element["exposed_conductor_potentials_v"]
    differential = largest_conductor_differential(potentials, context)
    relative = most_negative_plasma_relative_potential(
        potentials, element["ground_potential_v"], context
    )
    regime = categorize_arcing_regime(
        differential, relative, exposed, primary_threshold_v, sustained_threshold_v
    )
    required = required_provisions(family, regime)

    recorded = element.get("provisions", [])
    if not isinstance(recorded, (list, tuple)):
        raise ValueError("%s: 'provisions' must be a list" % context)
    for provision in recorded:
        if provision not in KNOWN_PROVISIONS:
            raise ValueError("%s: uncategorized provision %r" % (context, provision))

    missing = tuple(p for p in required if p not in set(recorded))
    findings = ["missing provision: %s" % p for p in missing]
    findings.extend(
        "%s" % f for f in check_bonding_resistance(element, bonding_limit_ohm)
    )

    return {
        "id": identifier,
        "family": family,
        "regime": regime,
        "differential_v": differential,
        "plasma_relative_potential_v": relative,
        "required_provisions": required,
        "missing_provisions": missing,
        "findings": findings,
        "compliant": not findings,
    }


def assess_exposed_power_chain(elements, **kwargs):
    """Evaluate every exposed element and aggregate the clause 7.3 verdict."""
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a list or tuple, got %s" % type(elements).__name__)
    if not elements:
        raise ValueError("elements must not be empty: an empty inventory proves nothing")

    results = [evaluate_element(element, **kwargs) for element in elements]
    seen = set()
    for result in results:
        if result["id"] in seen:
            raise ValueError("duplicate element id %r in the inventory" % result["id"])
        seen.add(result["id"])

    non_compliant = [r["id"] for r in results if not r["compliant"]]
    regime_counts = {name: 0 for name in ARCING_REGIMES}
    for result in results:
        regime_counts[result["regime"]] += 1

    return {
        "elements": results,
        "regime_counts": regime_counts,
        "non_compliant_ids": non_compliant,
        "finding_count": sum(len(r["findings"]) for r in results),
        "verdict": "pass" if not non_compliant else "fail",
    }
