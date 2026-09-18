"""Complementary branching rules for metallic braid-shielded bundles.

Anchor: ECSS-Q-ST-20-30C clause 7.7 (complementary ECSS requirements for
branching a bundle carrying a metallic braid shield, and for keeping the
shielding continuous through the breakout). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Compute the geometry of a braid from its construction -- carriers, ends per
   carrier, braid wire diameter, pick density and the diameter it is laid over
   -- to get the braid angle, the filling factor and the optical coverage the
   branch actually achieves.
2. Grade that coverage against the coverage the trunk carried: a breakout that
   continues a shield with a thinner braid has quietly downgraded the shield
   for everything downstream of it.
3. Grade the shielding continuity of each branch as a resistance budget that
   adds the trunk run, the junction and the branch run, against the end-to-end
   limit, and refuse a branch whose junction is not bonded at all.
4. Grade the unshielded length the breakout leaves exposed, since a shield
   that stops short of the branch takeoff leaves an aperture no coverage
   figure can compensate for.
5. Roll every branch up into one breakout verdict with named findings.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "RESISTANCE_TOLERANCE_OHM",
    "LENGTH_TOLERANCE_MM",
    "braid_angle_rad",
    "filling_factor",
    "optical_coverage",
    "braid_coverage_from_construction",
    "branch_shield_resistance_ohm",
    "coverage_meets_trunk",
    "exposed_length_acceptable",
    "evaluate_branch",
    "assess_breakout",
]

# A coverage, a resistance or a length landing exactly on its bound meets it;
# the equality is a representation question absorbed here rather than by
# moving the engineering limit.
COVERAGE_TOLERANCE = 1e-9
RESISTANCE_TOLERANCE_OHM = 1e-12
LENGTH_TOLERANCE_MM = 1e-9


def _require_number(value, label, positive=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if positive and number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _require_positive_int(value, label):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def braid_angle_rad(carriers, picks_per_mm, core_diameter_mm, wire_diameter_mm):
    """Return the braid angle in radians for one braid construction.

    The angle follows from how far the braid advances along the bundle between
    crossings against how far it travels around it, so it is set by the pick
    density, the carrier count and the mean diameter the braid rides on.
    """
    count = _require_positive_int(carriers, "carriers")
    picks = _require_number(picks_per_mm, "picks_per_mm")
    core = _require_number(core_diameter_mm, "core_diameter_mm")
    wire = _require_number(wire_diameter_mm, "wire_diameter_mm")
    mean_diameter = core + 2.0 * wire
    return math.atan((2.0 * math.pi * picks * mean_diameter) / count)


def filling_factor(ends_per_carrier, wire_diameter_mm, picks_per_mm, angle_rad):
    """Return the braid filling factor: the fraction of the surface one direction fills."""
    ends = _require_positive_int(ends_per_carrier, "ends_per_carrier")
    wire = _require_number(wire_diameter_mm, "wire_diameter_mm")
    picks = _require_number(picks_per_mm, "picks_per_mm")
    angle = _require_number(angle_rad, "angle_rad", positive=False)
    if angle <= 0.0 or angle >= math.pi / 2.0:
        raise ValueError("angle_rad must sit strictly between 0 and pi/2, got %r" % (angle_rad,))
    return (ends * wire * picks) / math.sin(angle)


def optical_coverage(fill):
    """Return the optical coverage of a braid from its filling factor."""
    value = _require_number(fill, "fill", positive=False)
    if value <= 0.0:
        raise ValueError("fill must be positive, got %r" % (fill,))
    if value > 1.0 + COVERAGE_TOLERANCE:
        raise ValueError(
            "fill %g exceeds unity; the coverage expression no longer describes this "
            "construction and the braid data must be rechecked" % value
        )
    capped = min(value, 1.0)
    return 2.0 * capped - capped * capped


def braid_coverage_from_construction(construction):
    """Return the braid angle, filling factor and optical coverage of a construction.

    construction keys: carriers, ends_per_carrier, wire_diameter_mm,
    picks_per_mm, core_diameter_mm.
    """
    if not isinstance(construction, dict):
        raise ValueError("construction must be a mapping")
    for key in ("carriers", "ends_per_carrier", "wire_diameter_mm", "picks_per_mm",
                "core_diameter_mm"):
        if key not in construction:
            raise ValueError("construction missing required key '%s'" % key)
    angle = braid_angle_rad(
        construction["carriers"],
        construction["picks_per_mm"],
        construction["core_diameter_mm"],
        construction["wire_diameter_mm"],
    )
    fill = filling_factor(
        construction["ends_per_carrier"],
        construction["wire_diameter_mm"],
        construction["picks_per_mm"],
        angle,
    )
    return {
        "braid_angle_rad": angle,
        "braid_angle_deg": math.degrees(angle),
        "filling_factor": fill,
        "optical_coverage": optical_coverage(fill),
    }


def branch_shield_resistance_ohm(trunk_ohm, junction_ohm, branch_ohm):
    """Return the end-to-end shield resistance a branch path presents."""
    trunk = _require_number(trunk_ohm, "trunk_ohm", positive=False)
    junction = _require_number(junction_ohm, "junction_ohm", positive=False)
    branch = _require_number(branch_ohm, "branch_ohm", positive=False)
    for label, value in (("trunk_ohm", trunk), ("junction_ohm", junction), ("branch_ohm", branch)):
        if value < 0.0:
            raise ValueError("%s must not be negative" % label)
    return trunk + junction + branch


def coverage_meets_trunk(branch_coverage, trunk_coverage, minimum_coverage):
    """Return True when a branch braid neither drops below the floor nor below the trunk."""
    branch = _require_number(branch_coverage, "branch_coverage")
    trunk = _require_number(trunk_coverage, "trunk_coverage")
    floor = _require_number(minimum_coverage, "minimum_coverage")
    for label, value in (("branch_coverage", branch), ("trunk_coverage", trunk),
                         ("minimum_coverage", floor)):
        if value > 1.0 + COVERAGE_TOLERANCE:
            raise ValueError("%s must be a fraction of unity, got %g" % (label, value))
    target = max(trunk, floor)
    return branch >= target - COVERAGE_TOLERANCE


def exposed_length_acceptable(exposed_mm, limit_mm):
    """Return True when the unshielded length a breakout leaves is inside its limit."""
    exposed = _require_number(exposed_mm, "exposed_mm", positive=False)
    limit = _require_number(limit_mm, "limit_mm", positive=False)
    if exposed < 0.0:
        raise ValueError("exposed_mm must not be negative")
    if limit < 0.0:
        raise ValueError("limit_mm must not be negative")
    return exposed <= limit + LENGTH_TOLERANCE_MM


def evaluate_branch(branch, trunk_coverage, requirements):
    """Evaluate one branch off a shielded trunk and return its findings.

    branch keys: id, construction, trunk_ohm, junction_ohm, branch_ohm,
    junction_bonded, exposed_length_mm.
    """
    if not isinstance(branch, dict):
        raise ValueError("branch must be a mapping")
    if not isinstance(requirements, dict):
        raise ValueError("requirements must be a mapping")
    for key in ("id", "construction", "trunk_ohm", "junction_ohm", "branch_ohm",
                "exposed_length_mm"):
        if key not in branch:
            raise ValueError("branch missing required key '%s'" % key)
    identifier = branch["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("branch id must be a non-empty string")
    geometry = braid_coverage_from_construction(branch["construction"])
    findings = []
    minimum_coverage = requirements.get("minimum_coverage", 0.85)
    if not coverage_meets_trunk(geometry["optical_coverage"], trunk_coverage, minimum_coverage):
        findings.append(
            "branch %s braid covers %.4f against the %.4f the trunk and the floor demand"
            % (identifier, geometry["optical_coverage"], max(trunk_coverage, minimum_coverage))
        )
    resistance = branch_shield_resistance_ohm(
        branch["trunk_ohm"], branch["junction_ohm"], branch["branch_ohm"]
    )
    limit = _require_number(requirements.get("continuity_limit_ohm", 0.010),
                            "continuity_limit_ohm")
    if resistance > limit + RESISTANCE_TOLERANCE_OHM:
        findings.append(
            "branch %s shield path measures %.6f ohm against the %.6f ohm limit"
            % (identifier, resistance, limit)
        )
    if not branch.get("junction_bonded", False):
        findings.append(
            "branch %s takes off from an unbonded junction; the trunk shield stops at the breakout"
            % identifier
        )
    exposed_limit = requirements.get("exposed_length_limit_mm", 25.0)
    if not exposed_length_acceptable(branch["exposed_length_mm"], exposed_limit):
        findings.append(
            "branch %s leaves %.2f mm unshielded at the breakout against the %.2f mm limit"
            % (identifier, float(branch["exposed_length_mm"]), float(exposed_limit))
        )
    return {
        "id": identifier,
        "geometry": geometry,
        "shield_resistance_ohm": resistance,
        "findings": findings,
        "conforming": not findings,
    }


def assess_breakout(spec):
    """Run the whole clause 7.7 branching assessment on one breakout.

    spec keys: trunk_construction, branches, optional requirements.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("trunk_construction", "branches"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    branches = spec["branches"]
    if not isinstance(branches, (list, tuple)) or not branches:
        raise ValueError("spec['branches'] must be a non-empty sequence")
    requirements = spec.get("requirements", {})
    trunk = braid_coverage_from_construction(spec["trunk_construction"])
    evaluated = []
    seen = set()
    for branch in branches:
        result = evaluate_branch(branch, trunk["optical_coverage"], requirements)
        if result["id"] in seen:
            raise ValueError("duplicate branch identifier %r" % result["id"])
        seen.add(result["id"])
        evaluated.append(result)
    findings = []
    for result in evaluated:
        findings.extend(result["findings"])
    max_branches = requirements.get("max_branches_per_breakout")
    if max_branches is not None:
        max_branches = _require_positive_int(max_branches, "max_branches_per_breakout")
        if len(evaluated) > max_branches:
            findings.append(
                "breakout carries %d branches against the %d allowed at one point"
                % (len(evaluated), max_branches)
            )
    worst = min(r["geometry"]["optical_coverage"] for r in evaluated)
    return {
        "trunk": trunk,
        "branches": evaluated,
        "branch_count": len(evaluated),
        "worst_branch_coverage": worst,
        "findings": findings,
        "compliant": not findings,
    }
