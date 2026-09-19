"""Land and pad repair on printed-circuit-board assemblies.

Anchor: ECSS-Q-ST-70-28C, methods clause -- a land that has lifted, torn or
lost area during rework is either re-bonded where it lies, replaced by a new
land bonded to the base material, or, where the hole barrel has gone with it,
rebuilt around an eyelet. Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Measure what survives: the remaining bond area as a fraction of the land
   the design drew, for a round land around a hole or a rectangular pad.
2. Pick the build-up method from that fraction and from the state of the hole
   barrel, and refuse the land that has lost too much to rebuild.
3. Derive the bond area the minimum pull-off load demands at the allowable
   bond stress, and compare it with the area the repair will actually have.
4. Check the annular ring the repaired land leaves around its hole.
5. Hold the number of repaired lands on one component footprint.
6. Return the repair with every finding that would send it back.
"""

import math

__all__ = [
    "MIN_REBOND_FRACTION",
    "MIN_REPLACEMENT_FRACTION",
    "MIN_PULL_OFF_N",
    "ALLOWABLE_BOND_STRESS_MPA",
    "MIN_ANNULAR_RING_MM",
    "MAX_REPAIRED_LANDS_PER_FOOTPRINT",
    "BARREL_STATES",
    "AREA_TOLERANCE_MM2",
    "GEOMETRY_TOLERANCE_MM",
    "FRACTION_TOLERANCE",
    "annular_land_area_mm2",
    "rectangular_pad_area_mm2",
    "land_area_mm2",
    "surviving_fraction",
    "required_bond_area_mm2",
    "annular_ring_mm",
    "select_build_up_method",
    "footprint_findings",
    "plan_land_repair",
]

# A land keeping this much of its bond area is re-bonded where it lies.
MIN_REBOND_FRACTION = 0.75

# Below this much surviving area the base material under the land is taken to
# be damaged too, and there is nothing sound to build a replacement onto.
MIN_REPLACEMENT_FRACTION = 0.05

# The pull-off load a repaired land carries, and the stress its bond may see.
MIN_PULL_OFF_N = 4.5
ALLOWABLE_BOND_STRESS_MPA = 3.5

# The smallest ring of land that may remain around a hole after the repair.
MIN_ANNULAR_RING_MM = 0.05

# Repaired lands tolerated on one component footprint.
MAX_REPAIRED_LANDS_PER_FOOTPRINT = 2

# Condition of the plated hole the land sits on.
BARREL_STATES = ("sound", "damaged", "absent", "not-applicable")

# Areas and dimensions are measured quantities; a value on a bound is inside.
AREA_TOLERANCE_MM2 = 1e-9
GEOMETRY_TOLERANCE_MM = 1e-9
FRACTION_TOLERANCE = 1e-9


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def annular_land_area_mm2(land_diameter_mm, hole_diameter_mm):
    """Return the copper area of a round land around a hole."""
    land = _positive(land_diameter_mm, "land_diameter_mm")
    hole = _positive(hole_diameter_mm, "hole_diameter_mm")
    if hole >= land - GEOMETRY_TOLERANCE_MM:
        raise ValueError(
            "hole diameter %g mm leaves no land inside a land diameter of %g mm"
            % (hole, land)
        )
    return math.pi * (land * land - hole * hole) / 4.0


def rectangular_pad_area_mm2(length_mm, width_mm):
    """Return the copper area of a rectangular surface-mount pad."""
    return _positive(length_mm, "length_mm") * _positive(width_mm, "width_mm")


def land_area_mm2(geometry):
    """Return the designed land area from either geometry description."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping")
    if "land_diameter_mm" in geometry and "hole_diameter_mm" in geometry:
        return annular_land_area_mm2(
            geometry["land_diameter_mm"], geometry["hole_diameter_mm"]
        )
    if "length_mm" in geometry and "width_mm" in geometry:
        return rectangular_pad_area_mm2(geometry["length_mm"], geometry["width_mm"])
    raise ValueError(
        "geometry must give either land_diameter_mm with hole_diameter_mm, or "
        "length_mm with width_mm"
    )


def surviving_fraction(surviving_area_mm2, designed_area_mm2):
    """Return what fraction of the designed land is still bonded down."""
    surviving = _non_negative(surviving_area_mm2, "surviving_area_mm2")
    designed = _positive(designed_area_mm2, "designed_area_mm2")
    if surviving > designed + AREA_TOLERANCE_MM2:
        raise ValueError(
            "surviving area %g mm2 exceeds the designed area %g mm2"
            % (surviving, designed)
        )
    return surviving / designed


def required_bond_area_mm2(pull_off_n=MIN_PULL_OFF_N, stress_mpa=ALLOWABLE_BOND_STRESS_MPA):
    """Return the bond area the pull-off load needs at the allowable stress."""
    load = _positive(pull_off_n, "pull_off_n")
    stress = _positive(stress_mpa, "stress_mpa")
    return load / stress


def annular_ring_mm(land_diameter_mm, hole_diameter_mm):
    """Return the ring of land left around the hole, per side."""
    land = _positive(land_diameter_mm, "land_diameter_mm")
    hole = _positive(hole_diameter_mm, "hole_diameter_mm")
    return (land - hole) / 2.0


def select_build_up_method(fraction, barrel_state="not-applicable"):
    """Pick the build-up method from the surviving fraction and the barrel."""
    if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
        raise ValueError("fraction must be a real number, got %r" % (fraction,))
    value = float(fraction)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("fraction must lie in [0, 1], got %r" % (fraction,))
    state = _token(barrel_state, "barrel_state")
    if state not in BARREL_STATES:
        raise ValueError(
            "unknown barrel_state '%s'; expected one of %s"
            % (state, ", ".join(BARREL_STATES))
        )
    if state in ("damaged", "absent"):
        return {
            "method": "barrel-eyelet",
            "reason": "the hole barrel is %s, so the land is rebuilt around an eyelet "
            "that restores the through connection too" % state,
        }
    if value >= MIN_REBOND_FRACTION - FRACTION_TOLERANCE:
        return {
            "method": "land-rebond-in-place",
            "reason": None,
        }
    if value >= MIN_REPLACEMENT_FRACTION - FRACTION_TOLERANCE:
        return {
            "method": "replacement-land-epoxy-bond",
            "reason": "only %g of the land survives, below the %g that may be re-bonded "
            "where it lies" % (value, MIN_REBOND_FRACTION),
        }
    return {
        "method": None,
        "reason": "only %g of the land survives; there is too little sound base "
        "material to bond a replacement to" % value,
    }


def footprint_findings(repaired_on_footprint):
    """Grade how many lands on one component footprint have been repaired."""
    if not isinstance(repaired_on_footprint, int) or isinstance(
        repaired_on_footprint, bool
    ):
        raise ValueError(
            "repaired_on_footprint must be an integer count, got %r"
            % (repaired_on_footprint,)
        )
    if repaired_on_footprint < 0:
        raise ValueError("repaired_on_footprint must be non-negative")
    total = repaired_on_footprint + 1
    if total > MAX_REPAIRED_LANDS_PER_FOOTPRINT:
        return [
            "this would be repaired land %d on the footprint, past the %d allowed; "
            "the part is remounted on rebuilt copper"
            % (total, MAX_REPAIRED_LANDS_PER_FOOTPRINT)
        ]
    return []


def plan_land_repair(damage):
    """Plan one land or pad repair and return it with every finding.

    damage keys: geometry (a mapping), surviving_area_mm2, optional
    barrel_state, repaired_lands_on_footprint, repaired_land_diameter_mm and
    pull_off_n.
    """
    if not isinstance(damage, dict):
        raise ValueError("damage must be a mapping")
    for key in ("geometry", "surviving_area_mm2"):
        if key not in damage:
            raise ValueError("damage missing required key '%s'" % key)

    findings = []
    designed = land_area_mm2(damage["geometry"])
    fraction = surviving_fraction(damage["surviving_area_mm2"], designed)
    selection = select_build_up_method(fraction, damage.get("barrel_state", "not-applicable"))
    method = selection["method"]
    if method is None:
        findings.append(selection["reason"])

    required_area = required_bond_area_mm2(damage.get("pull_off_n", MIN_PULL_OFF_N))

    # A re-bond keeps only the copper still attached; a replacement land or an
    # eyelet is built back to the designed footprint.
    if method == "land-rebond-in-place":
        available_area = fraction * designed
    elif method is None:
        available_area = 0.0
    else:
        available_area = designed

    if method is not None and available_area < required_area - AREA_TOLERANCE_MM2:
        findings.append(
            "the repair leaves %.4f mm2 of bond area against the %.4f mm2 a %g N "
            "pull-off needs" % (available_area, required_area, damage.get("pull_off_n", MIN_PULL_OFF_N))
        )

    ring = None
    geometry = damage["geometry"]
    if "hole_diameter_mm" in geometry:
        repaired_diameter = damage.get(
            "repaired_land_diameter_mm", geometry.get("land_diameter_mm")
        )
        ring = annular_ring_mm(repaired_diameter, geometry["hole_diameter_mm"])
        if ring < MIN_ANNULAR_RING_MM - GEOMETRY_TOLERANCE_MM:
            findings.append(
                "the repaired land leaves an annular ring of %g mm, under the %g mm "
                "minimum" % (ring, MIN_ANNULAR_RING_MM)
            )

    findings.extend(footprint_findings(damage.get("repaired_lands_on_footprint", 0)))

    return {
        "designed_area_mm2": designed,
        "surviving_fraction": fraction,
        "method": method,
        "method_reason": selection["reason"],
        "required_bond_area_mm2": required_area,
        "available_bond_area_mm2": available_area,
        "annular_ring_mm": ring,
        "findings": findings,
        "ready": not findings,
    }
