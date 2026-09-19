"""Laminate, delamination and plated-hole repair decision for a printed board.

Anchor: ECSS-Q-ST-70-28 Methods (repair of laminate damage, delamination and
damaged plated holes on printed board assemblies). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the board geometry, the defect geometry and the repair history.
2. Size a laminate or delamination defect against the board area and against
   the conductor clearance envelope it sits in -- a small defect that has
   encroached between two conductors is worse than a larger one in clear
   laminate.
3. For a damaged plated hole, recompute the barrel wall left once the damaged
   plating is removed and the hole is replated, and check the hole diameter
   growth the removal caused.
4. Pick the repair method from that wall: barrel replating while the wall
   still meets its minimum, an eyelet or interfacial insert when it does not
   and the hole is large enough to take one, refusal otherwise.
5. Draw the repair against the allowance the board still has, and return one
   of repairable, repair-with-approval or not-repairable together with the
   findings that drove it.
"""

import math

__all__ = [
    "AREA_TOLERANCE",
    "LENGTH_TOLERANCE_MM",
    "WALL_TOLERANCE_UM",
    "DEFECT_KINDS",
    "MIN_EYELET_HOLE_DIAMETER_MM",
    "require_real",
    "require_count",
    "rectangle_area_mm2",
    "area_fraction",
    "assess_surface_defect",
    "barrel_wall_after_repair_um",
    "select_hole_repair_method",
    "repair_allowance",
    "assess_laminate_and_hole_repair",
]

# Areas and lengths are differences of measured numbers; an exact equality at a
# limit must not be pushed to the wrong side by representation error.
AREA_TOLERANCE = 1e-9
LENGTH_TOLERANCE_MM = 1e-9
WALL_TOLERANCE_UM = 1e-9

DEFECT_KINDS = (
    "laminate-damage",
    "delamination",
    "measling",
    "plated-hole-barrel",
)

# Below this finished diameter an eyelet cannot be seated without taking the
# remaining annular ring with it.
MIN_EYELET_HOLE_DIAMETER_MM = 0.8


def require_real(label, value, minimum=0.0, allow_equal=True):
    """Return value as a float, raising ValueError on anything unusable."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if allow_equal and out < minimum:
            raise ValueError("%s must be at least %g, got %g" % (label, minimum, out))
        if not allow_equal and out <= minimum:
            raise ValueError("%s must exceed %g, got %g" % (label, minimum, out))
    return out


def require_count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def rectangle_area_mm2(length_mm, width_mm):
    """Return the bounding-rectangle area of a defect or a board."""
    length = require_real("length_mm", length_mm, minimum=0.0, allow_equal=False)
    width = require_real("width_mm", width_mm, minimum=0.0, allow_equal=False)
    return length * width


def area_fraction(defect_area_mm2, board_area_mm2):
    """Return the fraction of the board the defect covers."""
    defect = require_real("defect_area_mm2", defect_area_mm2, minimum=0.0)
    board = require_real("board_area_mm2", board_area_mm2, minimum=0.0, allow_equal=False)
    if defect > board + AREA_TOLERANCE:
        raise ValueError(
            "defect area %g mm2 exceeds the board area %g mm2" % (defect, board)
        )
    return defect / board


def assess_surface_defect(kind, defect_area_mm2, board_area_mm2,
                          distance_to_conductor_mm, min_clearance_mm,
                          max_area_fraction=0.01):
    """Grade a laminate, delamination or measling defect on area and clearance."""
    if kind not in DEFECT_KINDS[:3]:
        raise ValueError(
            "kind must be one of %s, got %r" % (", ".join(DEFECT_KINDS[:3]), kind)
        )
    limit = require_real("max_area_fraction", max_area_fraction, minimum=0.0,
                         allow_equal=False)
    if limit > 1.0:
        raise ValueError("max_area_fraction must not exceed 1.0, got %g" % limit)
    fraction = area_fraction(defect_area_mm2, board_area_mm2)
    gap = require_real("distance_to_conductor_mm", distance_to_conductor_mm, minimum=0.0)
    clearance = require_real("min_clearance_mm", min_clearance_mm, minimum=0.0,
                             allow_equal=False)
    over_area = fraction > limit + AREA_TOLERANCE
    encroaches = gap < clearance - LENGTH_TOLERANCE_MM
    return {
        "kind": kind,
        "area_fraction": fraction,
        "max_area_fraction": limit,
        "over_area": over_area,
        "distance_to_conductor_mm": gap,
        "min_clearance_mm": clearance,
        "encroaches_clearance": encroaches,
        "repairable": not (over_area or encroaches),
    }


def barrel_wall_after_repair_um(original_wall_um, removed_um, replated_um):
    """Return the plated barrel wall thickness left after removal and replating."""
    original = require_real("original_wall_um", original_wall_um, minimum=0.0,
                            allow_equal=False)
    removed = require_real("removed_um", removed_um, minimum=0.0)
    replated = require_real("replated_um", replated_um, minimum=0.0)
    if removed > original + WALL_TOLERANCE_UM:
        raise ValueError(
            "removed_um %g exceeds the original wall %g um; the barrel is gone, "
            "not thinned" % (removed, original)
        )
    return original - removed + replated


def select_hole_repair_method(wall_after_um, min_wall_um, hole_diameter_mm,
                              diameter_growth_mm, max_diameter_growth_mm,
                              eyelet_permitted=True):
    """Pick the plated-hole repair method the remaining wall and geometry allow."""
    wall = require_real("wall_after_um", wall_after_um, minimum=0.0)
    min_wall = require_real("min_wall_um", min_wall_um, minimum=0.0, allow_equal=False)
    diameter = require_real("hole_diameter_mm", hole_diameter_mm, minimum=0.0,
                            allow_equal=False)
    growth = require_real("diameter_growth_mm", diameter_growth_mm, minimum=0.0)
    max_growth = require_real("max_diameter_growth_mm", max_diameter_growth_mm,
                              minimum=0.0)
    if not isinstance(eyelet_permitted, bool):
        raise ValueError("eyelet_permitted must be a bool, got %r" % (eyelet_permitted,))
    if growth > max_growth + LENGTH_TOLERANCE_MM:
        return {
            "method": "not-repairable",
            "reason": "hole diameter grew %g mm against an allowance of %g mm"
                      % (growth, max_growth),
            "wall_after_um": wall,
        }
    if wall >= min_wall - WALL_TOLERANCE_UM:
        return {
            "method": "barrel-replating",
            "reason": "replated wall %g um meets the %g um minimum" % (wall, min_wall),
            "wall_after_um": wall,
        }
    if eyelet_permitted and diameter >= MIN_EYELET_HOLE_DIAMETER_MM - LENGTH_TOLERANCE_MM:
        return {
            "method": "eyelet-insertion",
            "reason": "replated wall %g um is under the %g um minimum; the hole takes "
                      "an eyelet" % (wall, min_wall),
            "wall_after_um": wall,
        }
    return {
        "method": "not-repairable",
        "reason": "replated wall %g um is under the %g um minimum and the hole is too "
                  "small for an eyelet" % (wall, min_wall),
        "wall_after_um": wall,
    }


def repair_allowance(existing_repairs, max_repairs):
    """Return the repair budget state for the board."""
    existing = require_count("existing_repairs", existing_repairs)
    maximum = require_count("max_repairs", max_repairs)
    if maximum == 0:
        raise ValueError("max_repairs must be at least 1 for a repairable board")
    remaining = maximum - existing
    return {
        "existing_repairs": existing,
        "max_repairs": maximum,
        "remaining_after_this_repair": remaining - 1,
        "exhausted": remaining <= 0,
        "last_allowed": remaining == 1,
    }


def assess_laminate_and_hole_repair(spec):
    """Run the whole laminate / plated-hole repair decision for one board.

    spec keys: board_length_mm, board_width_mm, existing_repairs, max_repairs,
    optional surface_defect mapping (kind, length_mm, width_mm,
    distance_to_conductor_mm, min_clearance_mm, max_area_fraction) and optional
    plated_hole mapping (original_wall_um, removed_um, replated_um, min_wall_um,
    hole_diameter_mm, diameter_growth_mm, max_diameter_growth_mm,
    eyelet_permitted).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("board_length_mm", "board_width_mm", "existing_repairs", "max_repairs"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    if "surface_defect" not in spec and "plated_hole" not in spec:
        raise ValueError("spec must carry a 'surface_defect' or a 'plated_hole' record")

    board_area = rectangle_area_mm2(spec["board_length_mm"], spec["board_width_mm"])
    allowance = repair_allowance(spec["existing_repairs"], spec["max_repairs"])

    findings = []
    surface = None
    hole = None

    defect = spec.get("surface_defect")
    if defect is not None:
        if not isinstance(defect, dict):
            raise ValueError("spec['surface_defect'] must be a mapping")
        for key in ("kind", "length_mm", "width_mm", "distance_to_conductor_mm",
                    "min_clearance_mm"):
            if key not in defect:
                raise ValueError("surface_defect missing required key '%s'" % key)
        defect_area = rectangle_area_mm2(defect["length_mm"], defect["width_mm"])
        surface = assess_surface_defect(
            defect["kind"],
            defect_area,
            board_area,
            defect["distance_to_conductor_mm"],
            defect["min_clearance_mm"],
            defect.get("max_area_fraction", 0.01),
        )
        surface["area_mm2"] = defect_area
        if surface["over_area"]:
            findings.append(
                "%s covers %.4f of the board against an allowance of %.4f"
                % (surface["kind"], surface["area_fraction"], surface["max_area_fraction"])
            )
        if surface["encroaches_clearance"]:
            findings.append(
                "%s sits %.3f mm from a conductor, inside the %.3f mm clearance envelope"
                % (surface["kind"], surface["distance_to_conductor_mm"],
                   surface["min_clearance_mm"])
            )

    hole_spec = spec.get("plated_hole")
    if hole_spec is not None:
        if not isinstance(hole_spec, dict):
            raise ValueError("spec['plated_hole'] must be a mapping")
        for key in ("original_wall_um", "removed_um", "replated_um", "min_wall_um",
                    "hole_diameter_mm", "diameter_growth_mm", "max_diameter_growth_mm"):
            if key not in hole_spec:
                raise ValueError("plated_hole missing required key '%s'" % key)
        wall_after = barrel_wall_after_repair_um(
            hole_spec["original_wall_um"],
            hole_spec["removed_um"],
            hole_spec["replated_um"],
        )
        hole = select_hole_repair_method(
            wall_after,
            hole_spec["min_wall_um"],
            hole_spec["hole_diameter_mm"],
            hole_spec["diameter_growth_mm"],
            hole_spec["max_diameter_growth_mm"],
            hole_spec.get("eyelet_permitted", True),
        )
        if hole["method"] == "not-repairable":
            findings.append("plated hole cannot be repaired: %s" % hole["reason"])

    if allowance["exhausted"]:
        findings.append(
            "the board has already taken its %d permitted repairs"
            % allowance["max_repairs"]
        )

    blocked = allowance["exhausted"]
    if surface is not None and not surface["repairable"]:
        blocked = True
    if hole is not None and hole["method"] == "not-repairable":
        blocked = True

    if blocked:
        verdict = "not-repairable"
    elif (hole is not None and hole["method"] == "eyelet-insertion") or \
            allowance["last_allowed"]:
        verdict = "repair-with-approval"
        if hole is not None and hole["method"] == "eyelet-insertion":
            findings.append("eyelet insertion is a deviation and needs written approval")
        if allowance["last_allowed"]:
            findings.append("this repair consumes the last of the board's allowance")
    else:
        verdict = "repairable"

    return {
        "board_area_mm2": board_area,
        "surface_defect": surface,
        "plated_hole": hole,
        "allowance": allowance,
        "verdict": verdict,
        "findings": findings,
    }
