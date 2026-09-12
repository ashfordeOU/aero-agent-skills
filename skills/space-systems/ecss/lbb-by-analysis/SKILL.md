---
name: lbb-by-analysis
description: "Use when determine whether a pressurized structure satisfies the leak-before-burst requirement by analysis per ECSS-E-ST-32C clause 5.3.2: compute the critical crack length at burst pressure using linear elastic fracture mechanics, verify that a through-wall leak crack remains stable below the residual-strength limit, integrate a Paris-law fatigue crack-growth model to confirm life from initial flaw to through-wall penetration exceeds mission life with margin, and assess residual strength with the largest stable leak crack. Trigger: ecss, e-st-32-structures-scope, leak-before-burst, lbb, fracture-mechanics, crack-growth, residual-strength, pressure-vessel."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32-structures-scope, leak-before-burst, lbb, fracture-mechanics, crack-growth, residual-strength, pressure-vessel]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Leak-Before-Burst Demonstration by Analysis (space-systems/ecss/lbb-by-analysis)

Use when the task is to determine whether a pressurized flight structure
meets the leak-before-burst requirement through fracture-mechanics analysis
under ECSS-E-ST-32C clause 5.3.2. The analysis combines crack stability,
fatigue crack-growth life, and residual-strength verification to demonstrate
that a through-wall crack producing a detectable leak is established before
a catastrophic burst can occur.

## Domain quick reference

- Clause 5.3.2 of ECSS-E-ST-32C requires LBB to be demonstrated either by
  test or by analysis. The analysis route establishes three conditions:
  (1) a surface crack penetrating the wall thickness produces a detectable
  leak at the highest operating pressure before the critical crack size for
  catastrophic failure is reached; (2) the fatigue crack-growth life from
  the assumed initial flaw at the NDE detection threshold to through-wall
  penetration exceeds the required service life with the design margin; and
  (3) the structure retains sufficient residual strength at proof load with
  the largest stable through-wall leak crack present.
- **Critical crack length (a_c)**: The half-crack length at which the
  stress intensity factor K equals the plane-strain fracture toughness K_Ic
  under burst pressure. Derived from linear elastic fracture mechanics as
  a_c = (K_Ic / (Y * sigma_burst))^2 / pi, where Y is the geometry
  correction factor and sigma_burst is the hoop or membrane stress at burst
  pressure.
- **Through-wall criterion**: A surface crack with depth a and half-length c
  becomes a through-wall leak when the depth dimension a equals the wall
  thickness t. The resulting through-wall half-crack length (a_tw) must
  satisfy a_tw < a_c at burst stress for LBB to hold.
- **Fatigue crack growth (Paris law)**: da/dN = C * (delta_K)^m, where C
  and m are material constants from fatigue crack-growth data. The number
  of load cycles for the crack to grow from the initial depth a_0 to the
  wall thickness t is integrated and compared against the required design
  life, scaled by the life safety factor per project requirement.
- **Residual strength**: Once a through-wall crack is confirmed stable under
  burst pressure, the cracked structure is assessed at proof pressure with
  the crack present; neither fracture nor net-section collapse must occur,
  confirming the leak is detectable before structural failure.

## Workflow

1. **Establish geometry and loading**: Record wall thickness t, vessel radius
   R, design burst pressure P_burst, proof pressure P_proof, and the number
   of pressurization cycles N_life. Compute hoop stress sigma = P * R / t
   for both burst and proof conditions.
2. **Define the initial flaw**: Select the assumed initial surface crack depth
   a_0 (NDE threshold) and half-length c_0 consistent with the aspect ratio
   from the NDE capability curve. Reject inputs where a_0 is greater than or
   equal to t (already through-wall) or a_0 is non-positive.
3. **Compute critical crack size at burst**: Using K_Ic, geometry factor Y,
   and sigma_burst, derive a_c = (K_Ic / (Y * sigma_burst))^2 / pi. This is
   the half-crack length that triggers unstable fracture at burst pressure.
4. **Determine through-wall crack half-length**: When depth a reaches t the
   surface crack becomes through-wall. Estimate the through-wall half-length
   a_tw from the crack shape evolution; as a conservative bound, preserve the
   initial aspect ratio c_0/a_0 so that a_tw = (c_0/a_0) * t.
5. **Check the LBB crack-size criterion**: Verify a_tw < a_c. If not, LBB by
   analysis is not demonstrated for these material and geometry parameters.
6. **Integrate fatigue crack growth**: Numerically integrate da/dN = C *
   (delta_K)^m from a = a_0 to a = t under the operating load spectrum.
   Confirm that the resulting cycle count N_through is greater than or equal
   to N_life multiplied by the life safety factor. Flag a shortfall as a
   crack-growth life violation.
7. **Assess residual strength with through-wall crack**: At proof pressure,
   compute K for the through-wall crack of half-length a_tw. Verify K < K_Ic
   (no fracture) and net-section stress < yield strength (no net-section
   collapse). Flag any violation as a residual-strength finding.
8. **Aggregate findings**: Collect all flags from steps 5 through 7. The LBB
   demonstration passes only when every check returns no violation.

## Pitfalls

- Applying burst-pressure stress intensity directly to the initial flaw to
  check critical size — the relevant comparison is the through-wall crack
  half-length (a_tw) against a_c, not the initial flaw against a_c.
- Using a geometry factor Y = 1.0 for a surface crack without verifying that
  the flat-plate assumption is appropriate; curved shells with R/t < 10
  require a Folias or equivalent bulging correction.
- Skipping the residual-strength check and treating the crack-size criterion
  alone as sufficient — a structure can satisfy a_tw < a_c yet still fail at
  proof pressure by net-section collapse if the material is ductile with a
  high K_Ic.
- Ignoring the aspect ratio evolution during fatigue growth — assuming a
  constant a/c ratio through the thickness traversal underestimates or
  overestimates the through-wall half-length depending on the initial shape.
- Accepting a safety factor on crack-growth life without also verifying the
  NDE detection threshold is smaller than the critical crack depth at proof
  pressure, so that inspection can confirm the leak before a test exceedance.

## Behavior contract (gate 3)

The fracture-mechanics, crack-growth, and residual-strength logic is
exercised by the gate 3 contract test: scripts/test_lbb_by_analysis.py
against scripts/lbb_by_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_lbb_by_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
