---
name: airfoil-geometry
description: "Use when you must work with classic NACA airfoil geometry: decode NACA 4-digit, 5-digit, and 6-series designations into camber, camber position, and thickness; compute the 4-digit thickness distribution, mean camber line ordinates and slope; and derive leading-edge radius and section area from the public-domain NACA formulas. Produces the geometry parameters that feed section selection, structural depth checks, and coordinate generation for panel or CFD analysis. Trigger: naca airfoil, camber, thickness distribution, mean line, leading edge radius, section area, airfoil coordinates."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: airfoil
  tags: [airfoil-geometry, naca, camber, thickness-distribution, mean-line, leading-edge-radius, section-area, airfoil-coordinates]
  version: 0.1.0
  author: Aero Agent Skills
---

# NACA Airfoil Geometry (aerodynamics/airfoil/airfoil-geometry)

Use when the task is classic NACA airfoil geometry: designation
decode, thickness and camber formula computation, and derived
geometric properties.

## Domain quick reference

- NACA 4-digit MPXX: M = max camber in percent chord (m = M / 100),
  P = camber position in tenths chord (p = P / 10), XX = max thickness
  in percent chord (t = XX / 100).
- Thickness half-ordinate (NACA Report 460; public domain):
  y_t = (t / 0.2) * (0.29690 * sqrt(x) - 0.12600 * x - 0.35160 * x^2
  + 0.28430 * x^3 - 0.10150 * x^4). Max half-thickness t / 2 at
  x = 0.3; the polynomial leaves a small trailing-edge thickness
  (0.0105 * t) that is faired to a sharp edge in practice.
- Mean camber line: for x <= p, y_c = (m / p^2) * (2 * p * x - x^2);
  for x >= p, y_c = (m / (1 - p)^2) * (1 - 2 * p + 2 * p * x - x^2).
  Slope dy_c / dx = (2 * m / p^2) * (p - x) for x <= p, and
  (2 * m / (1 - p)^2) * (p - x) for x >= p; zero at x = p.
- Upper surface = y_c + y_t, lower surface = y_c - y_t.
- Leading-edge radius: r_le = 1.1019 * t^2 (fraction of chord).
- Enclosed section area per unit span: A = 2 * integral(y_t dx) =
  0.68508 * t (chord^2); independent of camber.
- NACA 5-digit: design cl = first digit * 0.15 (23012 -> 0.3), camber
  position = second digit * 5 percent chord (23012 -> 15 percent),
  thickness = last two digits percent. Mean line 230: m = 0.15,
  k1 = 15.957. Third digit 1 marks a reflexed mean line.
- NACA 6-series: 65-218 = 6-series, min pressure at 0.5 chord (digit
  5 in tenths), design cl 0.2 (digit 2 in tenths), thickness 18
  percent. A parenthetical digit (65(3)-218) marks a modified mean
  line; the decoder rejects it rather than guess the variant.
- Practical data sources: NACA Report 824 ordinate tables, Abbott and
  von Doenhoff "Theory of Wing Sections", and the UIUC airfoil
  coordinate database.

## Workflow

1. Decode the designation with decode_4digit, decode_5digit, or
   decode_6series.
2. Compute thickness half-ordinates with thickness_ord at the mesh
   stations.
3. Compute camber ordinates and slope with camber_ord and
   camber_slope; form surfaces with surface_ords.
4. Derive leading_edge_radius and section_area for structural and
   geometric checks.
5. Cross-check ordinates against published tables when available.

## Pitfalls

- Reading the 5-digit second digit as percent chord instead of digit
  times 5.
- Applying the 4-digit thickness formula to 5-digit or 6-series
  sections; each family has its own ordinate tables.
- Treating y_t as a surface ordinate; the upper surface is y_c + y_t
  and the lower is y_c - y_t.
- Quoting the polynomial's trailing-edge thickness as a design value.
- Confusing the 5-digit design cl with the cl at a flight condition.
- Assuming the decoder handles modified 6-series or A-series
  thickness variants; it does not.

## Behavior contract (gate 3)

The decode and geometry logic is exercised by the gate 3 contract
test: scripts/test_airfoil_geometry.py against
scripts/airfoil_geometry_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_airfoil_geometry.py

## Compliance

- NACA Report 824 is US government work (public domain); formulas and
  summary values only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
