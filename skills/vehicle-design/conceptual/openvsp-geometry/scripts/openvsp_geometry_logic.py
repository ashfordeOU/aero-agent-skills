#!/usr/bin/env python3
"""Parametric aircraft geometry builder (OpenVSP style), stdlib only.

Conceptual-design geometry: define the wing planform (span, root and
tip chords, leading edge sweep, dihedral, twist), the fuselage from
its length and stationwise radii, the tail surfaces, and the nacelles;
then derive the geometry quantities that feed sizing and mass
estimation: wing area, aspect ratio, taper ratio, mean aerodynamic
chord, sweep conversion, wetted areas, component volumes, component
centroids, and wetted-to-planform ratios.

All methods are deterministic common-knowledge geometry (paraphrase
summary, standards-map.yaml far-25 / cs-25 reference-only context).
Units are consistent within a call (metres for length, square metres
for area, cubic metres for volume). Inputs are validated: non-positive
or malformed inputs raise ValueError.

Formulas used (documented approximations):
- Trapezoid planform area: S = (b/2) * (c_r + c_t).
- Aspect ratio: AR = b^2 / S.
- Taper ratio: lambda = c_t / c_r.
- Mean geometric chord: mgc = (c_r + c_t) / 2.
- Mean aerodynamic chord (trapezoid): mac = (2/3) c_r (1 + lambda +
  lambda^2) / (1 + lambda), at span station y_mac = (b/6)
  (1 + 2 lambda) / (1 + lambda).
- Sweep conversion: tan(Lambda_c4) = tan(Lambda_LE) - (c_r - c_t)/(2 b).
- Wetted area of a lifting surface: S_wet = 2 S_plan (1 + 0.2 t/c),
  two sides plus a thickness allowance.
- Fuselage (surface of revolution through stations): volume
  V = sum pi ((r_i^2 + r_j^2)/2) dx; wetted area
  S_wet = sum 2 pi r_avg dx sqrt(1 + (dr/dx)^2).
- Nacelle (cylinder with hemispherical cap): S_wet = pi D L,
  V = pi D^2 L / 4 - pi D^3 / 24.
- Component centroid: lifting surfaces are placed at the MAC station,
  mid-chord, offset in z by y_mac * tan(dihedral); the fuselage
  centroid follows from the station volume integration.
"""

import math


def _positive(name, value):
    if value is None or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError("%s must be a positive number, got %r" % (name, value))
    return float(value)


def _nonnegative(name, value):
    if value is None or not isinstance(value, (int, float)) or value < 0:
        raise ValueError("%s must be a non-negative number, got %r" % (name, value))
    return float(value)


def wing_planform(b, c_root, c_tip, le_sweep_deg=0.0, dihedral_deg=0.0,
                  twist_deg=0.0):
    """Trapezoid wing planform geometry from user parameters.

    b: span (m); c_root: root chord (m); c_tip: tip chord (m);
    le_sweep_deg: leading edge sweep (deg, positive aft);
    dihedral_deg: dihedral (deg); twist_deg: geometric washout (deg,
    positive tip trailing edge down).
    """
    b = _positive("span b", b)
    c_root = _positive("root chord c_root", c_root)
    c_tip = _positive("tip chord c_tip", c_tip)
    if c_tip > c_root:
        raise ValueError("tip chord must be <= root chord for a normal taper")
    le_sweep = math.radians(_nonnegative("le_sweep_deg", le_sweep_deg))
    dihedral = math.radians(_nonnegative("dihedral_deg", dihedral_deg))
    twist = math.radians(_nonnegative("twist_deg", twist_deg))

    area = 0.5 * b * (c_root + c_tip)
    aspect_ratio = b * b / area
    taper = c_tip / c_root
    mgc = 0.5 * (c_root + c_tip)
    mac = (2.0 / 3.0) * c_root * (1.0 + taper + taper * taper) / (1.0 + taper)
    y_mac = (b / 6.0) * (1.0 + 2.0 * taper) / (1.0 + taper)

    # Quarter chord sweep from leading edge sweep (derived from the
    # quarter chord line x positions at root and tip).
    tan_c4 = math.tan(le_sweep) - (c_root - c_tip) / (2.0 * b)
    qc_sweep_deg = math.degrees(math.atan(tan_c4))
    # Mid chord sweep, used by some loading methods.
    tan_c2 = math.tan(le_sweep) - (c_root - c_tip) / b
    mc_sweep_deg = math.degrees(math.atan(tan_c2))

    # Area centroid of the half planform: x at the MAC station mid
    # chord, y at the MAC station, z from the dihedral.
    x_centroid = y_mac * math.tan(le_sweep) + 0.5 * mac
    y_centroid = y_mac
    z_centroid = y_mac * math.tan(dihedral)

    return {
        "span": b,
        "root_chord": c_root,
        "tip_chord": c_tip,
        "area": area,
        "aspect_ratio": aspect_ratio,
        "taper_ratio": taper,
        "mean_geometric_chord": mgc,
        "mean_aerodynamic_chord": mac,
        "mac_span_station": y_mac,
        "le_sweep_deg": le_sweep_deg,
        "qc_sweep_deg": qc_sweep_deg,
        "mc_sweep_deg": mc_sweep_deg,
        "dihedral_deg": dihedral_deg,
        "twist_deg": twist_deg,
        "centroid": (x_centroid, y_centroid, z_centroid),
    }


def wetted_surface(planform_area, thickness_ratio=0.12):
    """Wetted area of a lifting surface: two sides plus a thickness
    allowance: S_wet = 2 S (1 + 0.2 t/c)."""
    planform_area = _positive("planform_area", planform_area)
    thickness_ratio = _nonnegative("thickness_ratio", thickness_ratio)
    return 2.0 * planform_area * (1.0 + 0.2 * thickness_ratio)


def wetted_to_planform(planform_area, thickness_ratio=0.12):
    """Ratio of wetted area to planform area for a lifting surface."""
    return wetted_surface(planform_area, thickness_ratio) / _positive(
        "planform_area", planform_area)


def fuselage_from_stations(stations):
    """Fuselage geometry from stationwise radii.

    stations: iterable of (x, r) pairs from nose to tail (m). Returns
    length, maximum diameter, volume, wetted area, and the x centroid
    of the volume. The body is a surface of revolution through the
    stations; each segment contributes a truncated cone.
    """
    pts = [tuple(p) for p in stations]
    if len(pts) < 2:
        raise ValueError("fuselage needs at least two stations")
    xs = [p[0] for p in pts]
    rs = [p[1] for p in pts]
    for i, (x, r) in enumerate(pts):
        _nonnegative("station x[%d]" % i, x)
        if r < 0:
            raise ValueError("station radius r[%d] must be >= 0" % i)
    if any(xs[i] >= xs[i + 1] for i in range(len(xs) - 1)):
        raise ValueError("station x positions must be strictly increasing")

    length = xs[-1] - xs[0]
    if length <= 0:
        raise ValueError("fuselage length must be > 0")
    volume = 0.0
    wetted = 0.0
    vol_x = 0.0  # first moment of volume about x = 0
    for i in range(len(pts) - 1):
        dx = xs[i + 1] - xs[i]
        r1, r2 = rs[i], rs[i + 1]
        # Truncated cone volume and lateral area.
        seg_vol = math.pi * dx * (r1 * r1 + r1 * r2 + r2 * r2) / 3.0
        slope = (r2 - r1) / dx
        r_avg = 0.5 * (r1 + r2)
        seg_wet = 2.0 * math.pi * r_avg * dx * math.sqrt(1.0 + slope * slope)
        volume += seg_vol
        wetted += seg_wet
        vol_x += seg_vol * 0.5 * (xs[i] + xs[i + 1])
    x_centroid = vol_x / volume if volume > 0 else xs[0]
    return {
        "length": length,
        "max_diameter": 2.0 * max(rs),
        "volume": volume,
        "wetted_area": wetted,
        "centroid": (x_centroid, 0.0, 0.0),
    }


def fuselage_cylinder(length, diameter):
    """Degenerate fuselage model: a plain cylinder of given length and
    diameter (wetted area pi D L, volume pi (D/2)^2 L, centroid at the
    mid length)."""
    length = _positive("length", length)
    diameter = _positive("diameter", diameter)
    r = 0.5 * diameter
    volume = math.pi * r * r * length
    wetted = math.pi * diameter * length
    return {
        "length": length,
        "max_diameter": diameter,
        "volume": volume,
        "wetted_area": wetted,
        "centroid": (0.5 * length, 0.0, 0.0),
    }


def nacelle_geometry(length, diameter):
    """Nacelle modeled as a cylinder with a hemispherical cap:
    wetted area pi D L and volume pi D^2 L / 4 - pi D^3 / 24.
    Centroid at the mid length on the engine axis."""
    length = _positive("length", length)
    diameter = _positive("diameter", diameter)
    if length < 0.5 * diameter:
        raise ValueError("nacelle length must be >= diameter/2 for the cap model")
    volume = math.pi * diameter * diameter * length / 4.0 \
        - math.pi * diameter ** 3 / 24.0
    wetted = math.pi * diameter * length
    return {
        "length": length,
        "diameter": diameter,
        "volume": volume,
        "wetted_area": wetted,
        "centroid": (0.5 * length, 0.0, 0.0),
    }


def build_geometry(wing=None, fuselage=None, tails=None, nacelles=None,
                   wing_thickness_ratio=0.12, tail_thickness_ratio=0.10):
    """Assemble the full parametric geometry and the derived quantities.

    wing: dict with b, c_root, c_tip, le_sweep_deg, dihedral_deg,
    twist_deg (as wing_planform accepts).
    fuselage: list of (x, r) stations, or None.
    tails: list of dicts like wing entries, each with a name key.
    nacelles: list of (length, diameter) tuples.
    Returns a dict with the geometry parameter table and the derived
    quantities, including component volumes, centroids, and
    wetted-to-planform ratios for the mass properties model.
    """
    components = []

    if wing is not None:
        w = wing_planform(**wing)
        w_wet = wetted_surface(w["area"], wing_thickness_ratio)
        components.append({
            "name": "wing",
            "volume": None,  # thin surface; volume handled by tanks elsewhere
            "centroid": w["centroid"],
            "wetted_area": w_wet,
            "planform_area": w["area"],
            "wetted_to_planform": w_wet / w["area"],
        })

    fus = None
    if fuselage is not None:
        fus = fuselage_from_stations(fuselage)
        components.append({
            "name": "fuselage",
            "volume": fus["volume"],
            "centroid": fus["centroid"],
            "wetted_area": fus["wetted_area"],
            "planform_area": None,
            "wetted_to_planform": None,
        })

    for t in tails or []:
        name = t.pop("name", "tail")
        tw = wing_planform(**t)
        tw_wet = wetted_surface(tw["area"], tail_thickness_ratio)
        components.append({
            "name": name,
            "volume": None,
            "centroid": tw["centroid"],
            "wetted_area": tw_wet,
            "planform_area": tw["area"],
            "wetted_to_planform": tw_wet / tw["area"],
        })

    nac = []
    for (ln, dm) in nacelles or []:
        g = nacelle_geometry(ln, dm)
        nac.append(g)
        components.append({
            "name": "nacelle",
            "volume": g["volume"],
            "centroid": g["centroid"],
            "wetted_area": g["wetted_area"],
            "planform_area": None,
            "wetted_to_planform": None,
        })

    total_wetted = sum(c["wetted_area"] for c in components)
    volumes = [c["volume"] for c in components if c["volume"] is not None]
    total_volume = sum(volumes)

    wing_geom = wing_planform(**wing) if wing is not None else None
    return {
        "wing": wing_geom,
        "fuselage": fus,
        "nacelles": nac,
        "components": components,
        "totals": {
            "wetted_area": total_wetted,
            "component_volume": total_volume,
        },
    }
