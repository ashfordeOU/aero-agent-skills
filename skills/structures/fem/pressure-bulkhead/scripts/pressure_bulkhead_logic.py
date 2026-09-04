"""Membrane-theory sizing of a fuselage pressure-bulkhead dome.

Pure Python stdlib, deterministic, no network, no external processes.
SI units throughout: pressure p in Pa, radii/axes/thickness in m,
stresses in Pa, loads per unit circumference in N/m, ring tension in N,
ring area in m^2.

Conventions follow the wave-33 pressure-bulkhead spec:
- Barrel (cylinder of radius a): hoop sigma_theta = p*a/t,
  longitudinal sigma_long = p*a/(2*t). Reported for cross-check only;
  the barrel skin itself is owned by the fuselage-skin-stringer leaf.
- Spherical dome radius R: sigma = p*R/(2*t) everywhere (equal
  meridional and circumferential membrane resultants).
- Ellipsoidal dome, semi-axes a (barrel radius) and b (dome depth):
  apex (both equal) sigma = p*a^2/(2*b*t);
  equator meridional sigma_phi = p*a/(2*t);
  equator circumferential sigma_theta = (p*a/t)*(1 - a^2/(2*b^2)).
  For b = a these reduce to p*a/(2*t) everywhere; for the 2:1 dome
  (b = a/2) the equator circumferential stress is compressive, the
  known 2:1 knuckle compression.
- Dome-cap rise of a spherical cap cutting the barrel at radius a:
  h = R - sqrt(R^2 - a^2).
- Junction ring of the spherical cap: the meridional resultant
  p*R/2 acts at the interface with a radial component (R - h)/R, so
  the unbalanced radial line load q = (p*R/2)*(R - h)/R, ring tension
  F_ring = q*a, ring area A_ring = F_ring*FS/sigma_ultimate. The
  hemisphere (h = R = a) carries zero unbalanced ring load.

Every geometry/stress entry point raises ValueError on non-positive
inputs; dome_cap_rise and the spherical-cap paths also reject a barrel
radius larger than the sphere radius.
"""

import math

# Module constants (no magic numbers in the functions).
_EMPTY_MSG = "must be positive"


def _require_positive(value, name):
    if not isinstance(value, (int, float)):
        raise ValueError("%s %s and numeric" % (name, _EMPTY_MSG))
    if value <= 0.0:
        raise ValueError("%s %s" % (name, _EMPTY_MSG))


def cylinder_membrane_stresses(p, radius_m, thickness_m):
    """Return (sigma_hoop, sigma_longitudinal) of a pressurized barrel.

    sigma_hoop = p*r/t, sigma_longitudinal = p*r/(2*t). Pa.
    """
    _require_positive(p, "pressure")
    _require_positive(radius_m, "barrel radius")
    _require_positive(thickness_m, "thickness")
    sigma_hoop = p * radius_m / thickness_m
    return (sigma_hoop, sigma_hoop / 2.0)


def spherical_dome_stress(p, radius_sphere_m, thickness_m):
    """Return the uniform membrane stress p*R/(2*t) of a spherical dome."""
    _require_positive(p, "pressure")
    _require_positive(radius_sphere_m, "sphere radius")
    _require_positive(thickness_m, "thickness")
    return p * radius_sphere_m / (2.0 * thickness_m)


def ellipsoid_dome_stresses(p, semi_axis_a_m, semi_axis_b_m, thickness_m):
    """Return dict of ellipsoidal dome stresses at apex and equator, Pa.

    Keys: sigma_apex, sigma_equator_meridional, sigma_equator_hoop.
    Apex (both directions equal): p*a^2/(2*b*t).
    Equator meridional: p*a/(2*t).
    Equator hoop: (p*a/t)*(1 - a^2/(2*b^2)); negative (compressive)
    whenever b < a/sqrt(2), which includes the 2:1 dome b = a/2.
    """
    _require_positive(p, "pressure")
    _require_positive(semi_axis_a_m, "semi-axis a")
    _require_positive(semi_axis_b_m, "semi-axis b")
    _require_positive(thickness_m, "thickness")
    ratio = semi_axis_a_m / semi_axis_b_m
    return {
        "sigma_apex": p * semi_axis_a_m * semi_axis_a_m
        / (2.0 * semi_axis_b_m * thickness_m),
        "sigma_equator_meridional": p * semi_axis_a_m / (2.0 * thickness_m),
        "sigma_equator_hoop": (p * semi_axis_a_m / thickness_m)
        * (1.0 - ratio * ratio / 2.0),
    }


def dome_cap_rise(radius_sphere_m, barrel_radius_m):
    """Return the spherical-cap rise h = R - sqrt(R^2 - a^2), m."""
    _require_positive(radius_sphere_m, "sphere radius")
    _require_positive(barrel_radius_m, "barrel radius")
    if barrel_radius_m > radius_sphere_m:
        raise ValueError("barrel radius must not exceed sphere radius")
    return radius_sphere_m - math.sqrt(
        radius_sphere_m * radius_sphere_m - barrel_radius_m * barrel_radius_m
    )


def junction_ring_load(p, barrel_radius_m, radius_sphere_m, rise_m):
    """Return dict of the unbalanced junction-ring load of a spherical cap.

    Radial line load q_n_per_m = (p*R/2)*(R - h)/R, ring tension
    ring_tension_N = q*a. The hemisphere (h = R) returns zero exactly.
    """
    _require_positive(p, "pressure")
    _require_positive(barrel_radius_m, "barrel radius")
    _require_positive(radius_sphere_m, "sphere radius")
    _require_positive(rise_m, "cap rise")
    if rise_m > radius_sphere_m:
        raise ValueError("cap rise must not exceed sphere radius")
    q_n_per_m = (p * radius_sphere_m / 2.0) * (
        (radius_sphere_m - rise_m) / radius_sphere_m
    )
    return {"q_n_per_m": q_n_per_m, "ring_tension_N": q_n_per_m * barrel_radius_m}


def junction_ring_area(ring_tension_N, sigma_ultimate_pa, fs):
    """Return the ring cross-section area A = F*FS/sigma_ultimate, m^2."""
    _require_positive(ring_tension_N, "ring tension")
    _require_positive(sigma_ultimate_pa, "ultimate stress")
    _require_positive(fs, "factor of safety")
    return ring_tension_N * fs / sigma_ultimate_pa


def _dome_stress_dict(dome_type, p, barrel_radius_m, thickness_m, sphere_or_axes):
    """Inner helper: geometry and stresses for one dome type.

    dome_type is one of "spherical-cap", "hemisphere", "ellipsoidal".
    For the spherical types sphere_or_axes is the sphere radius R
    (hemisphere ignores it and uses R = a by geometry). For the
    ellipsoid it is the dome depth b as a float, or an (a, b) tuple
    whose a must equal the barrel radius.
    """
    if dome_type == "spherical-cap":
        if isinstance(sphere_or_axes, (tuple, list)):
            raise ValueError("spherical-cap expects a sphere radius, not a tuple")
        _require_positive(sphere_or_axes, "sphere radius")
        if barrel_radius_m > sphere_or_axes:
            raise ValueError("barrel radius must not exceed sphere radius")
        rise = dome_cap_rise(sphere_or_axes, barrel_radius_m)
        stress = spherical_dome_stress(p, sphere_or_axes, thickness_m)
        geometry = {"sphere_radius_m": sphere_or_axes, "cap_rise_m": rise}
        stresses = {"sigma_meridional_pa": stress, "sigma_circumferential_pa": stress}
        return geometry, stresses, rise
    if dome_type == "hemisphere":
        sphere_radius = barrel_radius_m
        rise = barrel_radius_m
        stress = spherical_dome_stress(p, sphere_radius, thickness_m)
        geometry = {"sphere_radius_m": sphere_radius, "cap_rise_m": rise}
        stresses = {"sigma_meridional_pa": stress, "sigma_circumferential_pa": stress}
        return geometry, stresses, rise
    if dome_type == "ellipsoidal":
        if isinstance(sphere_or_axes, (tuple, list)):
            if len(sphere_or_axes) != 2:
                raise ValueError("ellipsoidal axes tuple must have two entries")
            semi_a, semi_b = sphere_or_axes
            _require_positive(semi_a, "semi-axis a")
            _require_positive(semi_b, "semi-axis b")
            if abs(semi_a - barrel_radius_m) > 1e-9 * barrel_radius_m:
                raise ValueError("ellipsoid semi-axis a must equal the barrel radius")
        else:
            _require_positive(sphere_or_axes, "dome depth b")
            semi_a, semi_b = barrel_radius_m, sphere_or_axes
        stresses = ellipsoid_dome_stresses(p, semi_a, semi_b, thickness_m)
        geometry = {"semi_axis_a_m": semi_a, "semi_axis_b_m": semi_b}
        return geometry, stresses, None
    raise ValueError(
        "dome_type must be spherical-cap, hemisphere or ellipsoidal"
    )


def bulkhead_summary(
    p, barrel_radius_m, thickness_m, dome_type, sigma_ultimate_pa, fs, sphere_or_axes
):
    """Return the full sizing summary dict for one dome geometry, SI units.

    Keys: dome_type, geometry_m, stresses_pa, sigma_max_pa,
    allowable_pa, margin_of_safety, reserve_factor, q_n_per_m,
    ring_tension_N, ring_area_m2.

    margin_of_safety = allowable/sigma_max - 1 and reserve_factor =
    allowable/sigma_max with allowable = sigma_ultimate/fs and
    sigma_max the largest absolute dome membrane stress. q_n_per_m,
    ring_tension_N and ring_area_m2 describe the spherical-cap
    junction ring (hemisphere: exactly zero; ellipsoidal: None, the
    ellipsoid junction ring model is not part of this module).

    sphere_or_axes: sphere radius R in m for "spherical-cap" (ignored
    for "hemisphere", which closes the barrel with R = a), or the dome
    depth b in m (or an (a, b) tuple matching the barrel radius) for
    "ellipsoidal".
    """
    _require_positive(p, "pressure")
    _require_positive(barrel_radius_m, "barrel radius")
    _require_positive(thickness_m, "thickness")
    _require_positive(sigma_ultimate_pa, "ultimate stress")
    _require_positive(fs, "factor of safety")
    geometry, stresses, rise = _dome_stress_dict(
        dome_type, p, barrel_radius_m, thickness_m, sphere_or_axes
    )
    sigma_max = max(abs(value) for value in stresses.values())
    allowable = sigma_ultimate_pa / fs
    margin = allowable / sigma_max - 1.0
    reserve = allowable / sigma_max
    if dome_type == "ellipsoidal":
        q_value = None
        tension = None
        area = None
    else:
        ring = junction_ring_load(p, barrel_radius_m, geometry["sphere_radius_m"], rise)
        q_value = ring["q_n_per_m"]
        tension = ring["ring_tension_N"]
        # The hemisphere carries zero ring tension and needs no ring.
        area = 0.0 if tension == 0.0 else junction_ring_area(
            tension, sigma_ultimate_pa, fs
        )
    return {
        "dome_type": dome_type,
        "geometry_m": geometry,
        "stresses_pa": stresses,
        "sigma_max_pa": sigma_max,
        "allowable_pa": allowable,
        "margin_of_safety": margin,
        "reserve_factor": reserve,
        "q_n_per_m": q_value,
        "ring_tension_N": tension,
        "ring_area_m2": area,
    }
