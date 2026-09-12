#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 4.6.2.15 riveted-joint analysis
(paraphrase, not a copy of the standard).

Common-knowledge summary (standards-map.yaml, ecss: gated false): a
riveted joint transfers shear between structural members through discrete
fasteners. Load is distributed to each rivet by the centroid method
(direct shear + moment component). Each rivet is checked for shear and
bearing margins. The skin panel between rivets is checked for inter-rivet
buckling under compressive running load using a plate-column formula
with a fixity coefficient. Thin-walled outstanding flange or web
elements are checked for crippling — the lesser of material yield stress
and elastic plate-buckling stress governs. This module implements load
distribution, margin calculations, and a full-group check; it does not
compute the sheet net-section tension or overall joint bending checks.
"""

import math


class RivetJointError(ValueError):
    pass


def _require_positive(value, name):
    if value <= 0:
        raise RivetJointError(f"{name} must be > 0, got {value!r}")


def _require_non_negative(value, name):
    if value < 0:
        raise RivetJointError(f"{name} must be >= 0, got {value!r}")


# ---------------------------------------------------------------------------
# Load distribution
# ---------------------------------------------------------------------------

def distribute_shear_to_rivets(shear_x, shear_y, moment, rivet_coords):
    """Distribute shear (shear_x, shear_y) and in-plane moment to rivets.

    Uses the centroid method: direct shear is split equally; the moment
    produces a tangential force on each rivet proportional to its distance
    from the group centroid, directed perpendicular to the radius vector.

    rivet_coords: list of (x, y) tuples (any consistent length unit).
    Returns list of (Fx, Fy) per rivet in the same force unit as the inputs.
    """
    if not rivet_coords:
        raise RivetJointError("rivet_coords must not be empty")

    n = len(rivet_coords)
    cx = sum(r[0] for r in rivet_coords) / n
    cy = sum(r[1] for r in rivet_coords) / n

    Ip = sum((r[0] - cx) ** 2 + (r[1] - cy) ** 2 for r in rivet_coords)

    if Ip == 0.0 and moment != 0.0:
        raise RivetJointError(
            "All rivets are coincident (Ip = 0) but moment is non-zero; "
            "moment cannot be distributed."
        )

    direct_x = shear_x / n
    direct_y = shear_y / n

    forces = []
    for rx, ry in rivet_coords:
        dx = rx - cx
        dy = ry - cy
        if Ip > 0.0:
            moment_fx = moment * (-dy) / Ip
            moment_fy = moment * dx / Ip
        else:
            moment_fx = 0.0
            moment_fy = 0.0
        forces.append((direct_x + moment_fx, direct_y + moment_fy))
    return forces


# ---------------------------------------------------------------------------
# Rivet shear margin
# ---------------------------------------------------------------------------

def rivet_shear_margin(applied_force, allowable_shear):
    """Margin of safety for rivet shear.

    MS = Fs_allow / F_applied - 1.
    Returns math.inf when applied_force == 0 (no load case).
    """
    _require_positive(allowable_shear, "allowable_shear")
    _require_non_negative(applied_force, "applied_force")
    if applied_force == 0.0:
        return math.inf
    return allowable_shear / applied_force - 1.0


# ---------------------------------------------------------------------------
# Sheet bearing
# ---------------------------------------------------------------------------

def bearing_stress(applied_force, diameter, thickness):
    """Bearing stress on the sheet: sigma_br = F / (d * t).

    applied_force: resultant force on the rivet (N or consistent unit).
    diameter: rivet hole diameter (m or consistent unit).
    thickness: sheet thickness (m or consistent unit).
    """
    _require_positive(diameter, "diameter")
    _require_positive(thickness, "thickness")
    _require_non_negative(applied_force, "applied_force")
    return applied_force / (diameter * thickness)


def bearing_margin(applied_force, diameter, thickness, allowable_bearing):
    """Margin of safety for sheet bearing.

    MS = Fbr_allow / sigma_br - 1.
    Returns math.inf when applied_force == 0.
    """
    _require_positive(allowable_bearing, "allowable_bearing")
    sigma_br = bearing_stress(applied_force, diameter, thickness)
    if sigma_br == 0.0:
        return math.inf
    return allowable_bearing / sigma_br - 1.0


# ---------------------------------------------------------------------------
# Inter-rivet buckling
# ---------------------------------------------------------------------------

def inter_rivet_buckling_stress(E, nu, t, pitch, fixity_c=4.0):
    """Critical inter-rivet buckling stress for a skin panel.

    Uses the plate-column formula (paraphrase, anchor ECSS-E-ST-32C cl. 4.6.2.15):
        sigma_cr = fixity_c * pi^2 * E / (12 * (1 - nu^2)) * (t / pitch)^2

    E       : Young's modulus (Pa)
    nu      : Poisson's ratio (0 < nu < 0.5)
    t       : sheet thickness (m)
    pitch   : rivet pitch — centre-to-centre spacing along load direction (m)
    fixity_c: edge-fixity coefficient.
                3.62 — one edge simply supported, one clamped (common for
                        countersunk rivets bearing on one face).
                4.0  — default conservative value for standard riveted panels.
                6.97 — both edges clamped (interference-fit or large-head rivets).

    Returns sigma_cr in Pa.
    """
    _require_positive(E, "E")
    _require_positive(t, "t")
    _require_positive(pitch, "pitch")
    if not (0.0 < nu < 0.5):
        raise RivetJointError(f"nu must be in (0, 0.5), got {nu!r}")
    if fixity_c <= 0.0:
        raise RivetJointError(f"fixity_c must be > 0, got {fixity_c!r}")

    return fixity_c * math.pi ** 2 * E / (12.0 * (1.0 - nu ** 2)) * (t / pitch) ** 2


def inter_rivet_buckling_margin(applied_compressive_stress, E, nu, t, pitch,
                                fixity_c=4.0):
    """Margin of safety for inter-rivet buckling.

    MS = sigma_cr / sigma_applied - 1.
    Returns math.inf when applied_compressive_stress == 0.
    """
    _require_non_negative(applied_compressive_stress, "applied_compressive_stress")
    sigma_cr = inter_rivet_buckling_stress(E, nu, t, pitch, fixity_c)
    if applied_compressive_stress == 0.0:
        return math.inf
    return sigma_cr / applied_compressive_stress - 1.0


# ---------------------------------------------------------------------------
# Section crippling (outstanding flange element)
# ---------------------------------------------------------------------------

def crippling_stress_fcc(Fcy, E, b, t, K_cr=0.9):
    """Crippling stress for an outstanding flange element.

    The crippling stress is the lesser of:
        (a) material compressive yield stress  Fcy
        (b) elastic plate-buckling stress       K_cr * E * (t / b)^2

    Fcy  : compressive yield stress (Pa)
    E    : Young's modulus (Pa)
    b    : outstanding element free-edge width (m)
    t    : element thickness (m)
    K_cr : plate-buckling coefficient.
             0.9 — simply supported free edge (conservative default).
             4.0 — clamped free edge (stiff attachment).

    Returns Fcc in Pa.
    """
    _require_positive(Fcy, "Fcy")
    _require_positive(E, "E")
    _require_positive(b, "b")
    _require_positive(t, "t")
    if K_cr <= 0.0:
        raise RivetJointError(f"K_cr must be > 0, got {K_cr!r}")

    sigma_elastic = K_cr * E * (t / b) ** 2
    return min(Fcy, sigma_elastic)


def crippling_margin(applied_stress, Fcy, E, b, t, K_cr=0.9):
    """Margin of safety for section crippling.

    MS = Fcc / sigma_applied - 1.
    Returns math.inf when applied_stress == 0.
    """
    _require_non_negative(applied_stress, "applied_stress")
    Fcc = crippling_stress_fcc(Fcy, E, b, t, K_cr)
    if applied_stress == 0.0:
        return math.inf
    return Fcc / applied_stress - 1.0


# ---------------------------------------------------------------------------
# Full rivet-group check
# ---------------------------------------------------------------------------

def check_rivet_group(shear_x, shear_y, moment, rivet_coords,
                      rivet_diameter, sheet_thickness,
                      allowable_rivet_shear, allowable_bearing):
    """Distribute loads and evaluate shear + bearing margins for every rivet.

    Returns a dict:
      per_rivet      : list of per-rivet dicts (index, Fx, Fy, F_total,
                       ms_shear, ms_bearing)
      worst_shear_ms : minimum rivet shear margin across the group
      worst_bearing_ms: minimum bearing margin across the group
      joint_passes   : True only when both worst margins are >= 0
    """
    _require_positive(rivet_diameter, "rivet_diameter")
    _require_positive(sheet_thickness, "sheet_thickness")
    _require_positive(allowable_rivet_shear, "allowable_rivet_shear")
    _require_positive(allowable_bearing, "allowable_bearing")

    forces = distribute_shear_to_rivets(shear_x, shear_y, moment, rivet_coords)

    per_rivet = []
    worst_shear_ms = math.inf
    worst_bearing_ms = math.inf

    for i, (fx, fy) in enumerate(forces):
        f_total = math.hypot(fx, fy)
        ms_s = rivet_shear_margin(f_total, allowable_rivet_shear)
        ms_b = bearing_margin(f_total, rivet_diameter, sheet_thickness,
                              allowable_bearing)
        per_rivet.append({
            "rivet": i,
            "Fx": fx,
            "Fy": fy,
            "F_total": f_total,
            "ms_shear": ms_s,
            "ms_bearing": ms_b,
        })
        if ms_s < worst_shear_ms:
            worst_shear_ms = ms_s
        if ms_b < worst_bearing_ms:
            worst_bearing_ms = ms_b

    return {
        "per_rivet": per_rivet,
        "worst_shear_ms": worst_shear_ms,
        "worst_bearing_ms": worst_bearing_ms,
        "joint_passes": worst_shear_ms >= 0.0 and worst_bearing_ms >= 0.0,
    }
