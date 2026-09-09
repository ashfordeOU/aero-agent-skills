"""Meteoroid and orbital debris (MMOD) impact protection sizing.

Pure stdlib closed-form implementation of the NASA/JSC ballistic-limit
equation family (Christiansen et al., NASA TM-2009-214789 / JSC-64399,
equations 4-1 to 4-26, cited summary-only): the Cour-Palais single-wall
cratering equation and its critical-diameter inversion, the Christiansen
new-non-optimum Whipple shield ballistic limit across the low,
intermediate, and hypervelocity impact regimes, the per-impact
penetration verdict, and the Poisson mission penetration probability.

Debris flux, fluence, and collision-probability values are GIVEN inputs
from the space environment assessment; no environment quantity is
estimated here. All units follow the handbook: cm, g/cm^3, km/s, ksi,
degrees, grams. Deterministic and offline; no imports beyond math.
"""

import math

C_CP = 5.24
K_PERFORATION = 1.8
K_DETACHED_SPALL = 2.2
K_INCIPIENT_SPALL = 3.0
RHO_BRANCH = 1.5
C_HYPER = 3.918
C_WALL_DESIGN = 0.16
CB_NEAR = 0.25
CB_FAR = 0.20
SD_BRANCH = 30.0
V_LOW = 3.0
V_HIGH = 7.0
THETA_CAP_DEG = 65.0


def _check_positive(value, name):
    """Raise ValueError unless value is a positive real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be a positive number, got %s" % (name, value))


def _check_theta(theta_deg):
    """Raise ValueError unless theta_deg is a real number in [0, 90)."""
    if isinstance(theta_deg, bool) or not isinstance(theta_deg, (int, float)):
        raise ValueError("impact angle must be a real number, got %r" % (theta_deg,))
    if not (0.0 <= theta_deg < 90.0):
        raise ValueError(
            "impact angle must be in [0, 90) degrees, got %s" % (theta_deg,)
        )


def _effective_theta_rad(theta_deg):
    """Return the obliquity-capped impact angle in radians (eq 4-26)."""
    capped = min(theta_deg, THETA_CAP_DEG)
    return math.radians(capped)


def cour_palais_penetration_depth(d, rho_p, rho_t, bhn, v, theta_deg, c_t):
    """Return the Cour-Palais semi-infinite penetration depth P_inf (cm).

    Density-ratio branch switch at r = rho_p / rho_t = RHO_BRANCH
    selects eq (4-1) for r < 1.5 or eq (4-2) for r >= 1.5.
    """
    _check_positive(d, "projectile diameter")
    _check_positive(rho_p, "projectile density")
    _check_positive(rho_t, "target density")
    _check_positive(bhn, "target hardness BHN")
    _check_positive(v, "impact velocity")
    _check_positive(c_t, "target sound speed")
    _check_theta(theta_deg)
    r = rho_p / rho_t
    vn = v * math.cos(_effective_theta_rad(theta_deg))
    exponent = 0.5 if r < RHO_BRANCH else (2.0 / 3.0)
    return C_CP * d ** (19.0 / 18.0) * bhn ** (-0.25) * r ** exponent * (vn / c_t) ** (2.0 / 3.0)


def single_wall_required_thickness(d, rho_p, rho_t, bhn, v, theta_deg, c_t, k=K_PERFORATION):
    """Return the single-wall thickness t = k * P_inf (cm) for damage mode k."""
    _check_positive(k, "damage threshold k")
    p_inf = cour_palais_penetration_depth(d, rho_p, rho_t, bhn, v, theta_deg, c_t)
    return k * p_inf


def single_wall_critical_diameter(t, rho_p, rho_t, bhn, v, theta_deg, c_t, k=K_PERFORATION):
    """Return the critical projectile diameter dc (cm), the eq (4-6) inversion."""
    _check_positive(t, "wall thickness")
    _check_positive(rho_p, "projectile density")
    _check_positive(rho_t, "target density")
    _check_positive(bhn, "target hardness BHN")
    _check_positive(v, "impact velocity")
    _check_positive(c_t, "target sound speed")
    _check_positive(k, "damage threshold k")
    _check_theta(theta_deg)
    r = rho_p / rho_t
    density_term = (1.0 / r) ** 0.5 if r < RHO_BRANCH else (1.0 / r) ** (2.0 / 3.0)
    vn = v * math.cos(_effective_theta_rad(theta_deg))
    numerator = t * bhn ** 0.25 * density_term
    denominator = k * C_CP * (vn / c_t) ** (2.0 / 3.0)
    return (numerator / denominator) ** (18.0 / 19.0)


def sphere_mass_g(d, rho_p):
    """Return the spherical projectile mass Mp = (pi/6) * rho_p * d^3 (g)."""
    _check_positive(d, "projectile diameter")
    _check_positive(rho_p, "projectile density")
    return (math.pi / 6.0) * rho_p * d ** 3


def whipple_bumper_thickness(d, rho_p, rho_b, S):
    """Return the Whipple bumper thickness tb (cm), eq (4-21)."""
    _check_positive(d, "projectile diameter")
    _check_positive(rho_p, "projectile density")
    _check_positive(rho_b, "bumper density")
    _check_positive(S, "standoff distance")
    cb = CB_NEAR if (S / d) < SD_BRANCH else CB_FAR
    return cb * d * rho_p / rho_b


def whipple_rear_wall_thickness(d, rho_p, rho_b, S, sigma_ksi, v, theta_deg, mass_g=None):
    """Return the Whipple rear-wall design thickness tw (cm), eq (4-22).

    Valid only for a normal impact velocity Vn >= 7 km/s; mass_g
    defaults to the spherical projectile mass.
    """
    _check_positive(d, "projectile diameter")
    _check_positive(rho_p, "projectile density")
    _check_positive(rho_b, "bumper density")
    _check_positive(S, "standoff distance")
    _check_positive(sigma_ksi, "rear-wall yield stress")
    _check_positive(v, "impact velocity")
    _check_theta(theta_deg)
    vn = v * math.cos(_effective_theta_rad(theta_deg))
    if vn < V_HIGH:
        raise ValueError(
            "rear-wall design thickness requires a normal impact velocity "
            "of at least 7 km/s, got Vn %s km/s" % (vn,)
        )
    mp = mass_g if mass_g is not None else sphere_mass_g(d, rho_p)
    if isinstance(mp, bool) or not isinstance(mp, (int, float)) or mp <= 0.0:
        raise ValueError("projectile mass must be a positive number, got %r" % (mp,))
    return (
        C_WALL_DESIGN
        * d ** 0.5
        * (rho_p * rho_b) ** (1.0 / 6.0)
        * mp ** (1.0 / 3.0)
        * vn
        * (70.0 / sigma_ksi) ** 0.5
        / S ** 0.5
    )


def _dc_hyper(tw, rho_p, rho_b, S, sigma_ksi, vn):
    """Return the hypervelocity critical diameter (eq 4-23) at normal velocity vn."""
    return (
        C_HYPER
        * tw ** (2.0 / 3.0)
        * rho_p ** (-1.0 / 3.0)
        * rho_b ** (-1.0 / 9.0)
        * vn ** (-2.0 / 3.0)
        * S ** (1.0 / 3.0)
        * (sigma_ksi / 70.0) ** (1.0 / 3.0)
    )


def _dc_low(tb, tw, rho_p, sigma_ksi, v, theta_rad):
    """Return the low-velocity critical diameter (eq 4-24)."""
    numerator = tw * (sigma_ksi / 40.0) ** 0.5 + tb
    denominator = 0.6 * rho_p ** 0.5 * v ** (2.0 / 3.0) * math.cos(theta_rad) ** (5.0 / 3.0)
    return (numerator / denominator) ** (18.0 / 19.0)


def whipple_critical_diameter(tb, tw, sigma_ksi, rho_p, rho_b, S, v, theta_deg):
    """Return the Whipple shield critical diameter dc (cm), three-regime dispatch.

    Dispatches on the obliquity-capped normal velocity Vn = V cos(theta)
    across the low (eq 4-24), intermediate blend (eq 4-25), and
    hypervelocity (eq 4-23) regimes with transitions at V_LOW and V_HIGH.
    """
    _check_positive(tb, "bumper thickness")
    _check_positive(tw, "rear-wall thickness")
    _check_positive(sigma_ksi, "rear-wall yield stress")
    _check_positive(rho_p, "projectile density")
    _check_positive(rho_b, "bumper density")
    _check_positive(S, "standoff distance")
    _check_positive(v, "impact velocity")
    _check_theta(theta_deg)
    theta_rad = _effective_theta_rad(theta_deg)
    vn = v * math.cos(theta_rad)
    if vn <= V_LOW:
        return _dc_low(tb, tw, rho_p, sigma_ksi, v, theta_rad)
    if vn >= V_HIGH:
        return _dc_hyper(tw, rho_p, rho_b, S, sigma_ksi, vn)
    v_l3 = V_LOW / math.cos(theta_rad)
    v_h7 = V_HIGH / math.cos(theta_rad)
    dc_l3 = _dc_low(tb, tw, rho_p, sigma_ksi, v_l3, theta_rad)
    dc_h7 = _dc_hyper(tw, rho_p, rho_b, S, sigma_ksi, V_HIGH)
    return dc_l3 * (V_HIGH - vn) / 4.0 + dc_h7 * (vn - V_LOW) / 4.0


def penetration_verdict(projectile_diameter_cm, critical_diameter_cm):
    """Return (verdict, margin) with margin = d / dc; margin >= 1 is PENETRATION."""
    _check_positive(projectile_diameter_cm, "projectile diameter")
    _check_positive(critical_diameter_cm, "critical diameter")
    margin = projectile_diameter_cm / critical_diameter_cm
    verdict = "PENETRATION" if margin >= 1.0 else "NO_PENETRATION"
    return verdict, margin


def whipple_penetration_verdict(d, tb, tw, sigma_ksi, rho_p, rho_b, S, v, theta_deg):
    """Return {"verdict", "dc", "margin"} for a Whipple shield against a projectile."""
    dc = whipple_critical_diameter(tb, tw, sigma_ksi, rho_p, rho_b, S, v, theta_deg)
    verdict, margin = penetration_verdict(d, dc)
    return {"verdict": verdict, "dc": dc, "margin": margin}


def penetration_probability(expected_penetrating_impacts):
    """Return P = 1 - exp(-lambda), the mission penetration probability."""
    if isinstance(expected_penetrating_impacts, bool) or not isinstance(
        expected_penetrating_impacts, (int, float)
    ):
        raise ValueError(
            "expected penetrating impacts must be a real number, got %r"
            % (expected_penetrating_impacts,)
        )
    if expected_penetrating_impacts < 0.0:
        raise ValueError(
            "expected penetrating impacts must be non-negative, got %s"
            % (expected_penetrating_impacts,)
        )
    return 1.0 - math.exp(-expected_penetrating_impacts)


def worked_example():
    """Return the Case-1 Whipple design and Case-2 single-wall anchors (spec worked example)."""
    tb = whipple_bumper_thickness(1.0, 2.7, 2.7, 11.43)
    mp = sphere_mass_g(1.0, 2.7)
    tw = whipple_rear_wall_thickness(1.0, 2.7, 2.7, 11.43, 40.0, 7.0, 0.0)
    dc_design = whipple_critical_diameter(tb, tw, 40.0, 2.7, 2.7, 11.43, 7.0, 0.0)
    verdict_design = whipple_penetration_verdict(1.0, tb, tw, 40.0, 2.7, 2.7, 11.43, 7.0, 0.0)
    verdict_10kms = whipple_penetration_verdict(1.0, tb, tw, 40.0, 2.7, 2.7, 11.43, 10.0, 0.0)
    p_inf = cour_palais_penetration_depth(1.0, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)
    t_req = single_wall_required_thickness(1.0, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)
    dc_single = single_wall_critical_diameter(0.48, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)
    p_mission = penetration_probability(0.5)
    return {
        "tb": tb,
        "mp": mp,
        "tw": tw,
        "dc_design": dc_design,
        "verdict_design": verdict_design,
        "verdict_10kms": verdict_10kms,
        "p_inf": p_inf,
        "t_req": t_req,
        "dc_single": dc_single,
        "p_mission": p_mission,
    }


if __name__ == "__main__":
    for key, value in sorted(worked_example().items()):
        print(key, value)
