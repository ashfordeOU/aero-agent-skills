---
name: wave-drag-area-rule
description: "Compute transonic wave drag with the Whitcomb area rule: build the streamwise cross-sectional area distribution of a wing-body combination, size the Sears-Haack minimum-drag body for a given length and volume, evaluate its zero-lift wave drag, and estimate the drag-divergence Mach number and the parabolic wave drag rise above it. Produces the Sears-Haack radius and area distributions, the equivalent drag area, the wave drag coefficient and force, and the area-rule fuselage pinch that smooths the total area distribution. Use when the task is wave drag estimation, area ruling, Sears-Haack bodies, drag divergence, or cross-sectional area distribution in transonic design. Trigger: wave drag, area rule, Sears-Haack, drag divergence, cross-sectional area."
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
  subdomain: high-speed
  tags: [wave-drag, area-rule, sears-haack, drag-divergence, cross-sectional-area]
  version: 0.1.0
  author: AeroSkills
---

# Wave Drag and the Whitcomb Area Rule (aerodynamics/high-speed/wave-drag-area-rule)

Use when the task is transonic wave drag: the Whitcomb area rule,
cross-sectional area distributions, the Sears-Haack minimum-drag body,
and drag divergence in high-speed configuration design.

## Domain quick reference

- Whitcomb area rule (1952): at transonic speeds the zero-lift wave
  drag of a wing-body combination depends mainly on the streamwise
  distribution of the total cross-sectional area (fuselage plus wing
  and nacelle contributions), not on the details of the individual
  components. The rule follows from the equivalence between the
  aircraft and an equivalent body of revolution.
- Area-rule shaping: where the wing adds area, the fuselage is pinched
  so the total area distribution stays smooth; the coke-bottle waist.
  The pinch at a station is S_fuselage = S_target - S_wing, computed
  with area_rule_fuselage_area. area_rule_deviation gives the RMS
  distance of an actual distribution from its ideal smooth target; a
  rougher equivalent body costs more wave drag.
- Sears-Haack body: the minimum-wave-drag body of revolution for a
  given length and volume (Haack 1941, Sears 1947). Radius
  r(x) = r_max * (4 * (x / L) * (1 - x / L))^(3/4), zero at both ends
  and r_max at the midpoint. This is the shape the total area
  distribution should approach at transonic speeds.
- Volume: V = (3 * pi^2 / 16) * r_max^2 * L. A 15 m body with a 0.54 m
  maximum radius holds about 8.1 m^3.
- Zero-lift wave drag area: D/q = (9 * pi / 2) * (A_max / L)^2 with
  A_max = pi * r_max^2 (drag-area form; identical to the volume form
  D/q = 128 * V^2 / (pi * L^4)). Multiply by dynamic pressure q for
  the wave drag force. The wave drag coefficient based on A_max is
  C_Dw = (9 * pi / 2) * (A_max / L^2), about 0.11 for a fineness
  ratio of 10 and 0.44 for a fineness ratio of 5.
- Drag divergence: wave drag stays negligible below the critical Mach
  number and rises steeply past the drag-divergence Mach number
  M_DD, which sits roughly 0.05 to 0.08 above M_cr for typical
  sections; drag_divergence_mach applies that margin. The rise above
  M_DD is modeled as parabolic, Delta C_Dw = k * (M - M_DD)^2, with k
  an empirical configuration-dependent constant (wave_drag_rise_coef).
- Mach number effects: at a fixed Mach number, wave drag scales with
  the dynamic pressure and with the square of the body slenderness
  ratio A_max / L; sweep and supercritical sections push M_DD up, and
  this leaf's divergence estimate feeds the high-speed design loop.
- Range: the Sears-Haack and area-rule results are slender-body
  linearized results, valid in the transonic and low-supersonic
  regime for smooth, slender configurations; a drag-divergence Mach at
  or above 1 is out of domain.
- Validation anchor: NACA Report 824 (public domain) supplies the
  section data family the pack references; the area rule itself is
  public-domain US government work (NACA Report 1273) and is used here
  as summary only per standards-map.yaml.

## Workflow

1. Collect the body length L, maximum radius r_max (or the volume V),
   and the station-by-station total area distribution.
2. Compute the Sears-Haack radius and area distributions with
   sears_haack_radius and sears_haack_area, and the volume with
   sears_haack_volume.
3. Evaluate the zero-lift wave drag: the drag area with
   sears_haack_wave_drag_area, the coefficient with
   sears_haack_wave_drag_coef, and the force with wave_drag_force at
   the cruise dynamic pressure.
4. Apply the area rule: at each station where the wing contributes
   area, size the fuselage pinch with area_rule_fuselage_area so the
   total stays on the smooth target; check the whole distribution
   with area_rule_deviation.
5. Estimate M_DD with drag_divergence_mach from the section critical
   Mach, then the wave drag rise at the cruise Mach with
   wave_drag_rise_coef.
6. Report the Sears-Haack values next to the actual configuration so
   the wave drag penalty of the real area distribution is visible.

## Pitfalls

- Reading Raymer's drag-area form as a coefficient: D/q has units of
  area and must be multiplied by q; the coefficient C_Dw divides by
  A_max.
- Squaring A_max / L^2 instead of A_max / L in the drag area: the
  drag area is (9 * pi / 2) * (A_max / L)^2.
- Area ruling the fuselage alone: the rule applies to the total area
  distribution, wing and nacelle contributions included.
- Pinching the fuselage past zero area at a station: the wing
  contribution must stay below the target total.
- Expecting zero wave drag below M_cr: the area rule reduces the
  drag rise; it does not remove wave drag entirely.
- Applying slender-body results to short, blunt bodies: the Sears-Haack
  and equivalent-body results are linearized slender-body theory.
- Confusing critical Mach with drag-divergence Mach: M_DD is higher by
  about 0.05 to 0.08, and the wave drag rise is driven by M_DD.
- Treating the parabolic rise constant k as a physical constant: it is
  empirical and configuration dependent.
- Using the divergence estimate past M = 1: the parabolic rise model
  is transonic; a supersonic result is out of domain.

## Behavior contract (gate 3)

The wave drag and area rule logic is exercised by the gate 3 contract
test: scripts/test_wave_drag_area_rule.py against
scripts/wave_drag_area_rule_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_wave_drag_area_rule.py

## Compliance

- The Sears-Haack body, the area rule, and the drag-divergence
  relations are standard transonic aerodynamics content (public-domain
  textbook and report material, e.g. Raymer, Aircraft Design; Anderson,
  Fundamentals of Aerodynamics; Whitcomb, NACA Report 1273). Paraphrase
  and computed values only, no verbatim excerpts.
- Standards reference: NACA TR 824 (section data family, reference-only)
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
