---
name: fuselage-skin-stringer
description: "Use when you must size a pressurized fuselage skin-stringer panel at the conceptual level: compute the hoop and longitudinal membrane stresses from the cabin differential pressure and the fuselage radius, derive the skin thickness from the governing hoop stress with the 1.5 factor of safety and the minimum gauge, bound the stringer spacing from the flat panel buckling allowable, set the frame pitch from the stringer column buckling length between frames, and size the stringer area from the compression strip load with the effective skin width. Produces the skin thickness, stringer spacing, frame pitch, and stringer area that gate the fuselage structure integration. Trigger: fuselage skin stringer, pressurized fuselage, hoop stress, stringer spacing, frame pitch, panel buckling."
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
  subdomain: structures-integration
  tags: [fuselage-skin-stringer, skin-stringer-panel, pressurized-fuselage, hoop-stress, skin-thickness, stringer-spacing, frame-pitch, panel-buckling, effective-skin-width, column-buckling]
  version: 0.1.0
  author: Aero Agent Skills
---

# Fuselage Skin-Stringer Panel (vehicle-design/structures-integration/fuselage-skin-stringer)

Use when the task is sizing the pressurized fuselage skin-stringer
panel at the conceptual level: skin thickness from the hoop stress
with the 1.5 factor of safety, stringer spacing from the flat panel
buckling allowable, frame pitch from the stringer column buckling
length, and stringer area from the effective skin width.

## Domain quick reference

- Thin-cylinder membrane stresses from the cabin differential
  pressure p and radius r on a skin of thickness t:
  hoop stress sigma_h = p * r / t and longitudinal stress
  sigma_l = p * r / (2 * t). The hoop stress governs the pressure
  skin.
- FAR-25.303 context: the factor of safety between limit and
  ultimate loads is 1.5, so the pressure skin thickness is
  t = p * r * 1.5 / sigma_allowable, floored by the minimum gauge
  (typical transport minimum gauge about 1.0 to 1.2 mm).
- Flat panel buckling between stringers (compression):
  sigma_cr = k * pi^2 * E * (t / b)^2 / (12 * (1 - nu^2)), with k
  about 4.0 for a long plate with simply supported edges. Solving
  for the spacing gives b = t * pi * sqrt(k * E / (12 * (1 - nu^2) *
  sigma_cr)).
- Stringer column buckling between frames (Euler):
  sigma_cr = pi^2 * E * I / (A * L^2), so the frame pitch is
  L = pi * sqrt(E * I / (A * sigma_cr)).
- Effective skin width in compression:
  b_eff = 1.9 * t * sqrt(E / sigma_allowable). The stringer area
  follows from the strip load P on one stringer bay:
  A = P / sigma_allowable - b_eff * t; the skin alone carries the
  strip when this goes to zero or below.
- Units: pressure in Pa, stress in Pa, radius and thickness in m,
  area in m^2, inertia in m^4, load in N, spacing and pitch in m.

## Workflow

1. Collect the cabin differential pressure, the fuselage radius, the
   skin material allowable stress, the factor of safety (default
   1.5), and the minimum gauge.
2. Compute the hoop and longitudinal membrane stresses with
   hoop_stress and longitudinal_stress.
3. Derive the skin thickness with skin_thickness; the hoop stress
   term governs under pressure and the minimum gauge floors the
   result.
4. Bound the stringer spacing with stringer_spacing from the skin
   thickness, the modulus, and the panel buckling allowable.
5. Set the frame pitch with frame_pitch from the stringer area and
   inertia, the modulus, and the column buckling allowable.
6. Size the stringer area with effective_skin_width and
   stringer_area from the compression strip load.
7. Check the sized panel: the hoop stress of the chosen skin must
   stay below the allowable scaled by the factor of safety.

## Pitfalls

- Using the longitudinal stress instead of the hoop stress for the
  skin thickness: the hoop stress p * r / t is twice the
  longitudinal stress and governs the pressure skin.
- Sizing at limit load without the 1.5 factor of safety: FAR-25.303
  requires the structure to carry ultimate load, so scale the
  pressure stress by 1.5 before comparing with the allowable.
- Forgetting the minimum gauge: manufacturing and corrosion practice
  floor the skin well above the pure stress thickness on small
  fuselages.
- Setting the frame pitch from the skin panel buckling length: the
  frames stop the stringer column, not the skin panel, so the pitch
  follows from the stringer Euler load, not the plate formula.
- Double counting the skin in the stringer area: the stringer only
  carries the strip load beyond the effective skin width b_eff * t,
  so subtract that term or the stringer comes out oversized.
- Mixing units: keep Pa, m, m^2, m^4, and N consistent; pressure in
  bar instead of Pa shifts every result by six orders.

## Behavior contract (gate 3)

The hoop and longitudinal stress, skin thickness, stringer spacing,
frame pitch, effective skin width, and stringer area logic is
exercised by the gate 3 contract test:
scripts/test_fuselage_skin_stringer.py against
scripts/fuselage_skin_stringer_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_fuselage_skin_stringer.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the membrane
  stress, panel buckling, and column buckling formulas are common
  aircraft structural analysis methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
