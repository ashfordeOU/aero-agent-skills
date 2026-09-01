---
name: openvsp-geometry
description: "Use when you must build the parametric aircraft geometry in the OpenVSP style for conceptual design: define the wing planform from the span, the root and tip chords, the sweep, the dihedral and the twist, define the fuselage from its length and stationwise radii, and add the tail surfaces and nacelles, then compute the derived geometry quantities: the wing area, the aspect ratio, the mean aerodynamic chord, the wetted areas, the component volumes and the component centroids that feed the mass properties model. Produces the geometry parameter table and the derived quantities that gate sizing and mass estimation. Trigger: parametric geometry, wing planform, mean aerodynamic chord, wetted area, component volume."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: conceptual
  tags: [parametric-geometry, openvsp-style, wing-planform, mean-aerodynamic-chord, wetted-area, fuselage-geometry, component-volume, sweep-dihedral-twist, mass-properties-input, conceptual-design]
  version: 0.1.0
  author: AeroSkills
---

# Parametric Geometry (vehicle-design/conceptual/openvsp-geometry)

Use when the task is parametric aircraft geometry modeling in the
spirit of OpenVSP: build the wing, fuselage, tail and nacelle
geometry from user parameters, then derive the areas, volumes and
centroids that feed sizing and mass estimation.

## Domain quick reference

- Wing planform: trapezoid defined by span b, root chord c_r, tip
  chord c_t, leading edge sweep, dihedral and twist.
- Derived wing quantities: area S = (b/2)(c_r + c_t), aspect ratio
  AR = b^2/S, taper ratio lambda = c_t/c_r, mean geometric chord,
  mean aerodynamic chord (MAC) and its span station.
- Fuselage: body of revolution through stationwise radii; volume and
  wetted area come from the station integration.
- Wetted areas: lifting surfaces use two sides plus a thickness
  allowance; the fuselage uses the surface of revolution; nacelles
  use a cylinder with a hemispherical cap.
- Component volumes and centroids are the mass-property-relevant
  outputs; wetted-to-planform ratios support drag buildup.

## Workflow

1. Collect the wing parameters (span, root and tip chord, sweep,
   dihedral, twist) and call wing_planform.
2. Define the fuselage as stationwise (x, r) pairs and call
   fuselage_from_stations (or use fuselage_cylinder for a plain
   cylinder).
3. Add tail surfaces as small trapezoid wings and nacelles as
   (length, diameter) pairs.
4. Assemble everything with build_geometry to get the geometry
   parameter table and the derived quantities.
5. Hand the derived areas, volumes and centroids to the sizing and
   mass properties leaves.

## Geometry formulas

- Trapezoid area: S = (b/2)(c_r + c_t).
- Aspect ratio: AR = b^2/S.
- Taper ratio: lambda = c_t/c_r.
- Mean geometric chord: mgc = (c_r + c_t)/2.
- Mean aerodynamic chord (trapezoid): mac = (2/3) c_r
  (1 + lambda + lambda^2)/(1 + lambda).
- MAC span station: y_mac = (b/6)(1 + 2 lambda)/(1 + lambda).
- Sweep conversion: tan(Lambda_c4) = tan(Lambda_LE) - (c_r - c_t)/(2b).
- Wetted area of a lifting surface: S_wet = 2 S (1 + 0.2 t/c).
- Fuselage segment (truncated cone): volume
  V = pi dx (r1^2 + r1 r2 + r2^2)/3, wetted area
  S_wet = 2 pi r_avg dx sqrt(1 + (dr/dx)^2).
- Nacelle (cylinder with hemispherical cap): S_wet = pi D L,
  V = pi D^2 L/4 - pi D^3/24.
- Component centroid: lifting surfaces sit at the MAC station,
  mid-chord, offset in z by y_mac tan(dihedral); the fuselage
  centroid follows from the station volume integration.

## Worked example

Transport-class geometry: wing b = 30 m, c_r = 4.5 m, c_t = 1.2 m,
LE sweep 28 deg. Then S = 85.5 m^2, AR = 10.5, lambda = 0.267,
mac = 3.31 m at y_mac = 6.37 m, quarter chord sweep 24.5 deg.
Fuselage stations [(0, 0.9), (12, 1.9), (24, 1.9), (34, 0.7)] give
volume ~ 300 m^3 and wetted area ~ 370 m^2; the wing wetted area is
~ 2 x 85.5 x 1.024 = 175 m^2 at t/c = 0.12. These derived quantities
feed the weight and drag buildup.

## Pitfalls

- Tip chord larger than root chord (negative taper is rejected).
- Zero or negative spans, chords, radii or lengths.
- Fuselage stations that do not advance in x.
- Nacelle length shorter than the cap radius.
- Confusing wetted area with planform area: lifting surfaces are
  wetted on both sides.

## Behavior contract (gate 3)

The geometry logic is exercised by the gate 3 contract test:
scripts/test_openvsp_geometry.py against
scripts/openvsp_geometry_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_openvsp_geometry.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 appear as
  reference-only context in standards-map.yaml; the geometry methods
  here are common conceptual design practice, summary-only.
- compliance: STANDARDS-REF, gated: false.
