"""Fastener position tolerance calculation (ASME Y14.5 fixed and floating
fastener formulas), pure stdlib.

Design-side sizing for bolted and screwed joints: the total positional
tolerance budget is the clearance between the clearance hole MMC diameter
and the fastener maximum diameter, split between the two mating members
(floating fastener case, each member carries a positional tolerance) or
applied with the threaded member share acting through a projected
tolerance zone (fixed fastener case). The formula inverts to give the
minimum clearance hole MMC diameter for a fastener size and tolerance
split. All diameters and tolerances are in millimeters and reported at
DECIMAL_PLACES (0.01 mm).

Conventions (Y14.5 design method, summary only, not reproduced):
- F = fastener maximum diameter at MMC.
- H = clearance hole MMC diameter.
- T1 = positional tolerance of the clearance member.
- T2 = positional tolerance of the other member (threaded or stud side in
  the fixed case, carried through a projected tolerance zone).
- Floating fastener: H = F + T1 + T2, each member gets a positional
  tolerance, total budget = H - F.
- Fixed fastener: same budget H - F; the threaded or stud member share is
  applied through a projected tolerance zone whose height defaults to the
  full mating part thickness.
- Minimum clearance hole: H_min = F + T1 + T2.
"""

DECIMAL_PLACES = 2
DEFAULT_SPLIT_SHARE = 0.5
DEFAULT_PROJECTED_MULTIPLIER = 1.0

_REPORT_BASE_KEYS = ("case", "total_tolerance", "tol_clearance_member",
                     "tol_other_member", "hole_mmc")


def _validate_material_pair(hole_mmc, fastener_max):
    """Reject a non-physical clearance hole / fastener pair.

    Raises ValueError when the fastener maximum diameter is non-positive
    (no real fastener) or the clearance hole MMC diameter is not larger
    than the fastener maximum diameter (no clearance, so no positional
    tolerance budget exists).
    """
    if fastener_max <= 0:
        raise ValueError("fastener_max must be positive")
    if hole_mmc <= fastener_max:
        raise ValueError("hole_mmc must exceed fastener_max to leave clearance")


def floating_fastener_total_tolerance(hole_mmc, fastener_max):
    """Step 2 budget traverse for the floating fastener case.

    Total positional tolerance budget T_total = H - F for two clearance
    members, each of which carries its own positional tolerance.
    """
    _validate_material_pair(hole_mmc, fastener_max)
    return round(hole_mmc - fastener_max, DECIMAL_PLACES)


def fixed_fastener_total_tolerance(hole_mmc, fastener_max):
    """Step 2 budget traverse for the fixed fastener case.

    The same budget H - F applies when one member is threaded or carries
    a stud: the clearance member share and the other member share still
    have to fit in the hole clearance, and the other member share acts
    through a projected tolerance zone (height from projected_zone_height).
    """
    _validate_material_pair(hole_mmc, fastener_max)
    return round(hole_mmc - fastener_max, DECIMAL_PLACES)


def split_tolerance(total_tolerance, first_share=DEFAULT_SPLIT_SHARE):
    """Step 3 split traverse: divide the budget between the two members.

    Returns (round(T1, 2), round(T2, 2)) with T1 = total * first_share
    and T2 = total - T1, so the pair sums back to the total within 0.01 mm.
    Raises ValueError when the total is not positive or the first share is
    outside the open interval (0, 1).
    """
    if total_tolerance <= 0:
        raise ValueError("total_tolerance must be positive")
    if not (0.0 < first_share < 1.0):
        raise ValueError("first_share must lie strictly between 0 and 1")
    t1 = round(total_tolerance * first_share, DECIMAL_PLACES)
    t2 = round(total_tolerance - t1, DECIMAL_PLACES)
    return (t1, t2)


def minimum_clearance_hole_mmc(fastener_max, tol_clearance_member, tol_other_member):
    """Step 5 minimum hole traverse: invert the fastener formula.

    Minimum clearance hole MMC diameter H = F + T1 + T2 for a given
    fastener maximum diameter and member tolerance split. Raises
    ValueError when the fastener is non-positive or a member tolerance is
    negative (a zero tolerance on one member is allowed).
    """
    if fastener_max <= 0:
        raise ValueError("fastener_max must be positive")
    if tol_clearance_member < 0 or tol_other_member < 0:
        raise ValueError("member tolerances cannot be negative")
    return round(fastener_max + tol_clearance_member + tol_other_member, DECIMAL_PLACES)


def projected_zone_height(mating_thickness, multiplier=DEFAULT_PROJECTED_MULTIPLIER):
    """Step 4 projected zone traverse: height of the fixed case zone.

    The threaded or stud member tolerance acts through a projected
    tolerance zone; the documented default height is the full mating part
    thickness (multiplier 1.0), with a shorter zone available through the
    multiplier variant. Raises ValueError on a non-positive thickness or
    multiplier.
    """
    if mating_thickness <= 0:
        raise ValueError("mating_thickness must be positive")
    if multiplier <= 0:
        raise ValueError("multiplier must be positive")
    return round(mating_thickness * multiplier, DECIMAL_PLACES)


def fastener_report(case="floating", fastener_max=None, hole_mmc=None,
                    first_share=DEFAULT_SPLIT_SHARE, tol_clearance_member=None,
                    tol_other_member=None, mating_thickness=None,
                    projected_multiplier=DEFAULT_PROJECTED_MULTIPLIER):
    """Step 6 report bookkeeping traverse: assemble the sizing record.

    Keys (documented contract): case, total_tolerance, tol_clearance_member,
    tol_other_member and hole_mmc are always present; minimum_hole_mmc is
    added when solving (hole_mmc omitted, the hole is sized from the
    member tolerances); projected_zone_height is added for the fixed case
    when a mating_thickness is supplied.

    Direct mode (hole_mmc given) computes the budget from H - F and splits
    it with split_tolerance unless both member tolerances are supplied.
    Solving mode (hole_mmc None) requires both member tolerances and
    returns the minimum hole from minimum_clearance_hole_mmc.
    """
    if case not in ("floating", "fixed"):
        raise ValueError("case must be 'floating' or 'fixed'")
    if fastener_max is None:
        raise ValueError("fastener_max is required")
    if fastener_max <= 0:
        raise ValueError("fastener_max must be positive")

    solving = hole_mmc is None
    if solving:
        if tol_clearance_member is None or tol_other_member is None:
            raise ValueError("solving mode needs both member tolerances")
        clearance_share = tol_clearance_member
        other_share = tol_other_member
        total = round(clearance_share + other_share, DECIMAL_PLACES)
        hole = minimum_clearance_hole_mmc(
            fastener_max, clearance_share, other_share)
    else:
        if case == "floating":
            total = floating_fastener_total_tolerance(hole_mmc, fastener_max)
        else:
            total = fixed_fastener_total_tolerance(hole_mmc, fastener_max)
        hole = hole_mmc
        if tol_clearance_member is None or tol_other_member is None:
            clearance_share, other_share = split_tolerance(total, first_share)
        else:
            clearance_share = round(tol_clearance_member, DECIMAL_PLACES)
            other_share = round(tol_other_member, DECIMAL_PLACES)

    report = {
        "case": case,
        "total_tolerance": total,
        "tol_clearance_member": clearance_share,
        "tol_other_member": other_share,
        "hole_mmc": hole,
    }
    if solving:
        report["minimum_hole_mmc"] = hole
    if case == "fixed" and mating_thickness is not None:
        report["projected_zone_height"] = projected_zone_height(
            mating_thickness, projected_multiplier)
    return report


def report_keys(case="floating", solving=False, fixed_zone=False):
    """Documented key contract for fastener_report output.

    Helper for the contract test: the exact key set a report of the given
    shape must expose, matching the docstring of fastener_report.
    """
    keys = set(_REPORT_BASE_KEYS)
    if solving:
        keys.add("minimum_hole_mmc")
    if case == "fixed" and fixed_zone:
        keys.add("projected_zone_height")
    return keys
