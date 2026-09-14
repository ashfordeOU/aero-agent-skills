"""Connector contacts and contact sourcing for a Class 1 commercial procurement.

Anchor: ECSS-Q-ST-60-13C clause 4.6.6 (connector contacts and their sourcing
for procurements at the highest assurance class). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Group the contact source and decide what that source leaves open.
2. Read the minimum gold thickness the contact finish needs for the declared
   number of mating cycles off a durability table, and grade the measured
   gold and nickel underplate against it.
3. Derate the contact current rating for the contact size and for how much of
   the connector is carrying current at once.
4. Convert the measured contact resistance into a millivolt drop at the
   applied current and grade it against the allowance.
5. Return an accept / accept-with-deviation / reject disposition with the
   findings that drove it.
"""

import math

__all__ = [
    "THICKNESS_TOLERANCE_UM",
    "CURRENT_TOLERANCE_A",
    "CLASS_1_CURRENT_FACTOR",
    "NICKEL_UNDERPLATE_MIN_UM",
    "CONTACT_SIZE_RATING_A",
    "GOLD_DURABILITY_TABLE",
    "BUNDLE_DERATING_TABLE",
    "CONTACT_SOURCES",
    "contact_size_rating_a",
    "interpolate_table",
    "minimum_gold_thickness_um",
    "plating_acceptance",
    "bundle_derating_factor",
    "allowed_contact_current_a",
    "contact_voltage_drop_mv",
    "contact_sourcing",
    "assess_connector_contacts",
]

# Plating thicknesses and currents are compared against interpolated bounds:
# an exactly satisfied bound can land a few ULPs on the wrong side. Absorb the
# representation error here instead of relaxing the engineering limit.
THICKNESS_TOLERANCE_UM = 1e-9
CURRENT_TOLERANCE_A = 1e-9

# The highest assurance class derates the contact current rating before any
# bundle effect is applied.
CLASS_1_CURRENT_FACTOR = 0.5

# Minimum nickel barrier under the gold, in micrometres.
NICKEL_UNDERPLATE_MIN_UM = 1.27

# Single-contact current ratings by contact size designation, in amperes.
CONTACT_SIZE_RATING_A = {
    "size-22d": 5.0,
    "size-20": 7.5,
    "size-16": 13.0,
    "size-12": 23.0,
    "size-8": 46.0,
}

# Minimum gold thickness in micrometres against the declared durability, as
# (mating cycles, micrometres) pairs.
GOLD_DURABILITY_TABLE = (
    (50.0, 0.75),
    (200.0, 1.27),
    (500.0, 1.65),
    (1000.0, 2.54),
)

# Derating factor against the fraction of contacts energised at once, as
# (active fraction, factor) pairs.
BUNDLE_DERATING_TABLE = (
    (0.0, 1.0),
    (0.25, 0.80),
    (0.50, 0.65),
    (0.75, 0.55),
    (1.00, 0.50),
)

# Where the contacts came from, and whether that source stands on its own.
CONTACT_SOURCES = {
    "contact-manufacturer-qualified": "accept",
    "connector-manufacturer-integrated": "accept",
    "distributor-with-lot-traceability": "deviation",
    "open-market": "reject",
}


def _real(value, label, positive=True, allow_zero=False):
    """Return value as a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive:
        if allow_zero:
            if out < 0.0:
                raise ValueError("%s must be non-negative, got %g" % (label, out))
        elif out <= 0.0:
            raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def contact_size_rating_a(size):
    """Return the single-contact current rating of a contact size."""
    if not isinstance(size, str) or not size.strip():
        raise ValueError("size must be a non-empty string")
    key = size.strip().lower()
    if key not in CONTACT_SIZE_RATING_A:
        raise ValueError(
            "unknown contact size '%s'; expected one of %s"
            % (size, ", ".join(sorted(CONTACT_SIZE_RATING_A)))
        )
    return CONTACT_SIZE_RATING_A[key]


def interpolate_table(table, x, name="table"):
    """Linearly interpolate a table of (x, y) pairs; refuse to extrapolate."""
    if not isinstance(table, (list, tuple)) or len(table) < 2:
        raise ValueError("%s needs at least two (x, y) points" % name)
    points = []
    for i, item in enumerate(table):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be an (x, y) pair" % (name, i))
        px = _real(item[0], "%s[%d] abscissa" % (name, i), positive=False)
        py = _real(item[1], "%s[%d] ordinate" % (name, i), positive=False)
        points.append((px, py))
    for i in range(1, len(points)):
        if points[i][0] <= points[i - 1][0]:
            raise ValueError("%s abscissae must strictly increase (index %d)" % (name, i))
    xv = _real(x, "%s abscissa" % name, positive=False)
    lo, hi = points[0][0], points[-1][0]
    if xv < lo or xv > hi:
        raise ValueError(
            "%s is tabulated over [%g, %g]; %g is outside it, extrapolation refused"
            % (name, lo, hi, xv)
        )
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        if xv <= x1:
            if xv == x0:
                return y0
            if xv == x1:
                return y1
            t = (xv - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return points[-1][1]


def minimum_gold_thickness_um(mating_cycles):
    """Return the gold thickness the finish needs for a durability requirement."""
    cycles = _real(mating_cycles, "mating_cycles")
    return interpolate_table(GOLD_DURABILITY_TABLE, cycles, name="gold-durability-table")


def plating_acceptance(gold_um, nickel_um, mating_cycles):
    """Grade the measured contact finish against the durability requirement."""
    gold = _real(gold_um, "gold_um", allow_zero=True)
    nickel = _real(nickel_um, "nickel_um", allow_zero=True)
    required_gold = minimum_gold_thickness_um(mating_cycles)
    gold_ok = gold >= required_gold - THICKNESS_TOLERANCE_UM
    nickel_ok = nickel >= NICKEL_UNDERPLATE_MIN_UM - THICKNESS_TOLERANCE_UM
    return {
        "gold_um": gold,
        "nickel_um": nickel,
        "required_gold_um": required_gold,
        "required_nickel_um": NICKEL_UNDERPLATE_MIN_UM,
        "gold_sufficient": gold_ok,
        "nickel_sufficient": nickel_ok,
        "accepted": gold_ok and nickel_ok,
    }


def bundle_derating_factor(active_fraction):
    """Return the derating factor for the fraction of contacts carrying current."""
    fraction = _real(active_fraction, "active_fraction", allow_zero=True)
    if fraction > 1.0:
        raise ValueError("active_fraction must not exceed 1.0, got %g" % fraction)
    return interpolate_table(BUNDLE_DERATING_TABLE, fraction, name="bundle-derating-table")


def allowed_contact_current_a(size, active_fraction):
    """Return the current one contact may carry in this connector."""
    rating = contact_size_rating_a(size)
    factor = bundle_derating_factor(active_fraction)
    return rating * CLASS_1_CURRENT_FACTOR * factor


def contact_voltage_drop_mv(current_a, resistance_mohm):
    """Return the millivolt drop across a contact at the applied current."""
    current = _real(current_a, "current_a", allow_zero=True)
    resistance = _real(resistance_mohm, "resistance_mohm", allow_zero=True)
    return current * resistance


def contact_sourcing(source):
    """Group the contact source into the disposition it leaves open."""
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string")
    key = source.strip().lower()
    if key not in CONTACT_SOURCES:
        raise ValueError(
            "unknown contact source '%s'; expected one of %s"
            % (source, ", ".join(sorted(CONTACT_SOURCES)))
        )
    return {"source": key, "standing": CONTACT_SOURCES[key]}


def assess_connector_contacts(spec):
    """Run the full clause 4.6.6 contact-and-sourcing assessment.

    spec keys: contact_source, contact_size, mating_cycles, gold_um, nickel_um,
    active_fraction, applied_current_a, contact_resistance_mohm,
    allowed_drop_mv, and optional contact_lot_identifier.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "contact_source",
        "contact_size",
        "mating_cycles",
        "gold_um",
        "nickel_um",
        "active_fraction",
        "applied_current_a",
        "contact_resistance_mohm",
        "allowed_drop_mv",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    sourcing = contact_sourcing(spec["contact_source"])
    plating = plating_acceptance(spec["gold_um"], spec["nickel_um"],
                                 spec["mating_cycles"])
    allowed_current = allowed_contact_current_a(spec["contact_size"],
                                                spec["active_fraction"])
    applied = _real(spec["applied_current_a"], "applied_current_a", allow_zero=True)
    drop = contact_voltage_drop_mv(applied, spec["contact_resistance_mohm"])
    allowed_drop = _real(spec["allowed_drop_mv"], "allowed_drop_mv")

    findings = []
    blocking = False
    deviated = False

    if sourcing["standing"] == "reject":
        findings.append(
            "contacts sourced from the %s; no lot traceability chain exists"
            % sourcing["source"]
        )
        blocking = True
    elif sourcing["standing"] == "deviation":
        findings.append(
            "contacts sourced through a %s; acceptable only on the traced contact lot"
            % sourcing["source"]
        )
        deviated = True

    if not plating["gold_sufficient"]:
        findings.append(
            "gold thickness %.4f um is under the %.4f um needed for %g mating cycles"
            % (plating["gold_um"], plating["required_gold_um"],
               float(spec["mating_cycles"]))
        )
        blocking = True

    if not plating["nickel_sufficient"]:
        findings.append(
            "nickel barrier %.4f um is under the %.4f um minimum"
            % (plating["nickel_um"], plating["required_nickel_um"])
        )
        blocking = True

    if applied - allowed_current > CURRENT_TOLERANCE_A:
        findings.append(
            "applied current %.4f A exceeds the %.4f A this contact may carry at "
            "the declared active fraction" % (applied, allowed_current)
        )
        blocking = True

    if drop - allowed_drop > 1e-9:
        findings.append(
            "contact drop %.4f mV exceeds the allowed %.4f mV" % (drop, allowed_drop)
        )
        blocking = True

    lot = spec.get("contact_lot_identifier")
    if not isinstance(lot, str) or not lot.strip():
        findings.append("traceability incomplete: 'contact_lot_identifier' is absent")
        blocking = True

    if blocking:
        disposition = "reject"
    elif deviated:
        disposition = "accept-with-deviation"
    else:
        disposition = "accept"

    return {
        "sourcing": sourcing,
        "plating": plating,
        "allowed_current_a": allowed_current,
        "applied_current_a": applied,
        "contact_drop_mv": drop,
        "allowed_drop_mv": allowed_drop,
        "disposition": disposition,
        "findings": findings,
    }
