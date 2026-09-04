---
name: delamination-growth
description: "Use when you must assess delamination growth in a composite laminate by fracture mechanics: compute the mode I strain energy release rate of a DCB double cantilever beam specimen and the mode II rate of an ENF end-notched flexure specimen from load, crack length and coupon geometry, blend mixed-mode rates with the Benzeggagh-Kenane criterion, and compare the total rate against the critical rate for the onset and growth verdict. Produces G_I, G_II, the mixed-mode ratio, critical rate G_c, onset margin and growth verdict gating the delamination tolerance assessment. Trigger: delamination growth, strain energy release rate, double cantilever beam, end notched flexure, mixed mode fracture, benzeggagh kenane criterion, mode I, mode II."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: cmh-17
    reference-only: true
gated: false
domain: structures
pack: composites
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [delamination-growth, strain-energy-release-rate, double-cantilever-beam, end-notched-flexure, mixed-mode-fracture, benzeggagh-kenane-criterion, mode-i, mode-ii]
  version: 0.1.0
  author: Aero Agent Skills
---

# Delamination Growth (structures/composites/delamination-growth)

Use when the task is assessing delamination onset and growth in a
composite laminate with fracture mechanics rather than ply-level
stress criteria: the mode I strain energy release rate of a DCB double
cantilever beam coupon and the mode II rate of an ENF end-notched
flexure coupon are computed from the applied load, crack length and
coupon geometry, the two rates are blended into a mixed-mode condition
with the Benzeggagh-Kenane criterion, and the total applied rate is
compared against the critical rate to produce the growth verdict. This
leaf implements the standard beam-theory delamination model in pure
Python, stdlib only. It pairs with structures/composites/failure-criteria
(stress-based ply failure at the lamina level, this leaf is
fracture-mechanics delamination at the laminate level) and with
structures/damage-tolerance/crack-growth (the metallic Paris-law
sibling).

## Domain quick reference

- DCB mode I rate: G_I = 12 * P^2 * a^2 / (E * b^2 * h^3), where h is
  the half-thickness of one DCB arm (specimen total thickness 2h), P
  the applied load, a the crack length, b the width, E the flexural
  modulus. Units: P in N, lengths in m, E in Pa, G in J/m2.
- Compliance form: G_I = 3 * P * delta / (2 * b * a), where delta is
  the total load-line opening of both arms. With the beam-theory
  opening delta = 2 * w, one-arm tip deflection w = P * a^3 / (3 * E *
  I) and arm inertia I = b * h^3 / 12, both forms agree exactly.
- ENF mode II rate: G_II = 9 * P^2 * a^2 / (16 * E * b^2 * h^3), h the
  half-thickness of one ENF half-beam.
- Mixed-mode ratio: r = G_II / (G_I + G_II); r = 0 in the unloaded
  state where both rates vanish.
- Benzeggagh-Kenane criterion: G_c = G_Ic + (G_IIc - G_Ic) * r^eta,
  with G_Ic and G_IIc the mode I and mode II critical rates and eta the
  B-K exponent. Pure mode I (r = 0) gives G_Ic, pure mode II (r = 1)
  gives G_IIc.
- Onset margin and verdict: margin = G_c - G_T with G_T = G_I + G_II;
  when G_T >= G_c the total applied rate exceeds the critical rate and
  delamination onset and growth are predicted.
- The relations are standard small-deflection beam theory on an
  isotropic-equivalent laminate flexural stiffness; the values in the
  worked example are engineering examples, not a material database.
  CMH-17 is referenced by name for the test-method context, not
  reproduced.

## Workflow

1. Fix the coupon states: DCB load p_dcb (N), crack length a_dcb (m),
   arm half-thickness h_dcb (m), ENF load p_enf, crack length a_enf,
   half-thickness h_enf, shared width b (m) and flexural modulus e (Pa).
   The two coupons are separate specimens, so their crack lengths and
   half-thicknesses are independent.
2. Compute the mode I rate of the DCB coupon with dcb_g1.
3. Cross-check the compliance route with dcb_g1_compliance when the
   load-line opening delta is measured: the opening equals 2 * w with
   w = P * a^3 / (3 * E * I) and I = b * h^3 / 12 in the beam model.
4. Compute the mode II rate of the ENF coupon with enf_g2.
5. Form the mixed-mode ratio with mixed_mode_ratio and the critical
   rate with bk_critical from G_Ic, G_IIc and eta.
6. Compute the onset margin with onset_margin, or run the whole
   assessment in one call with assess, which returns g1, g2, g_t,
   ratio, g_c, margin, the growth boolean and the verdict string
   "delamination-growth" or "no-delamination-growth".
7. Confirm the deterministic checks with the contract test
   scripts/test_delamination_growth.py.

## Worked example

Flexural modulus E = 135e9 Pa, width b = 0.02 m, G_Ic = 250 J/m2,
G_IIc = 800 J/m2, eta = 1.5.

- DCB at P = 50 N, a = 0.05 m, h = 0.0015 m (total 3 mm):
  E * b^2 * h^3 = 0.18225, so G_I = 12 * 2500 * 0.0025 / 0.18225 =
  411.52 J/m2. At P = 30 N the same coupon gives G_I = 148.15 J/m2.
- ENF at P = 500 N, a = 0.03 m, h = 0.0015 m: 16 * 0.18225 = 2.916,
  so G_II = 9 * 250000 * 0.0009 / 2.916 = 694.44 J/m2.
- Compliance cross-check with h = 0.003 m: I = b * h^3 / 12 =
  4.5e-11, one-arm tip deflection w = 50 * 1.25e-4 / (3 * 135e9 *
  4.5e-11) = 3.429e-4 m, load-line opening delta = 2 * w = 6.859e-4 m.
  dcb_g1 gives 51.44 J/m2 and dcb_g1_compliance gives 3 * 50 * 6.859e-4
  / (2 * 0.02 * 0.05) = 51.44 J/m2; with the exact opening the two
  forms agree to 1e-6.
- Growth case: DCB P = 50 N at h = 0.003 m (G_I = 51.44) with ENF
  P = 500 N at h = 0.0015 m (G_II = 694.44) gives G_T = 745.89,
  r = 0.9310, G_c = 250 + 550 * 0.89837 = 744.1 J/m2, margin = -1.76,
  so growth is predicted: verdict delamination-growth.
- No-growth case: DCB P = 30 N at h = 0.003 m (G_I = 18.52) with ENF
  P = 350 N at h = 0.0015 m (G_II = 340.28) gives G_T = 358.80,
  r = 0.94841, G_c = 250 + 550 * 0.92361 = 757.98 J/m2, margin = +399.18,
  so no delamination growth is predicted.


## Pitfalls

- Comparing ply-level stress indices to a fracture criterion: this
  leaf assesses delamination onset by energy release rate at the
  laminate level; stress-based ply failure (Tsai-Wu, max stress)
  belongs to failure-criteria, and metallic Paris-law growth to
  damage-tolerance/crack-growth.
- Mixing the coupon half-thicknesses: h is the half-thickness of one
  DCB arm or ENF half-beam (total specimen 2h); the worked example
  uses h = 0.0015 m for a 3 mm coupon and h = 0.003 m in the
  compliance cross-check, and the rate scales as h^-3, so an
  off-by-two in h shifts G by 8x.
- Treating the two coupons as one specimen: the DCB and ENF crack
  lengths and half-thicknesses are independent inputs; reusing one
  coupon's geometry for both silently mis-blends the mode ratio.
- Trusting one form without the cross-check: the load-squared form
  and the compliance form agree to 1e-6 only when delta = 2 * w with
  w = P a^3 / (3 E I) and I = b h^3 / 12, so a measured opening that
  does not follow the beam model breaks the identity.
- Reading the verdict at the boundary: growth is predicted when
  G_T >= G_c, so a zero or slightly negative margin is a predicted
  onset; the onset margin is G_c - G_T, not a ratio.
- Feeding non-physical coupons: negative loads, zero or negative
  geometry or modulus, zero or negative critical rates, and a
  non-positive B-K exponent all raise ValueError.
## Verification

- Confirm dcb_g1(50.0, 0.05, 0.02, 0.0015, 135e9) returns 411.52 J/m2
  and enf_g2(500.0, 0.03, 0.02, 0.0015, 135e9) returns 694.44 J/m2.
- Confirm the compliance-form and load-squared-form DCB rates agree to
  1e-6 when delta = 2 * P * a^3 / (3 * E * I), I = b * h^3 / 12.
- Confirm the B-K critical rate grows monotonically from G_Ic to G_IIc
  as the mode II share of G_T rises.
- Confirm the growth case returns a negative margin and verdict
  delamination-growth, and the no-growth case a positive margin and
  verdict no-delamination-growth.
- Confirm every negative load, zero or negative geometry or modulus,
  zero or negative critical rate, and non-positive B-K exponent raises
  ValueError.
- Run the contract test offline: python3
  scripts/test_delamination_growth.py (34 tests, deterministic).

## Related leaves

- structures/composites/failure-criteria: stress-based ply failure with
  Tsai-Wu and max-stress indices, the lamina-level complement to this
  laminate-level fracture leaf.
- structures/composites/cmh17-allowables: the laminate and lamina
  allowables context behind the critical energy release rates.
- structures/damage-tolerance/crack-growth: metallic fatigue crack
  growth with the Paris law, the metallic analog of growth prediction.
- structures/damage-tolerance/residual-strength: remaining strength of
  a cracked panel once growth tolerance is lost.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_delamination_growth.py

The test covers the DCB mode I rate anchors (411.52 and 148.15 J/m2),
the ENF mode II anchors (694.44 and 340.28 J/m2), the compliance-form
cross-check at h = 0.003 m (51.44 J/m2 from both forms, exact
agreement to 1e-6), load-squared and h-cubed scaling, the mixed-mode
ratio including pure mode I, pure mode II and the unloaded state, B-K
critical rates for the growth and no-growth cases plus monotonicity and
bounds, the onset margins, the full assess verdicts for both worked
cases, the report keys, and ValueError rejection of negative loads,
zero geometry or modulus, non-positive critical rates and a non-positive
B-K exponent.

## Compliance

- Standards referenced, not reproduced: CMH-17 (Composite Materials
  Handbook, sae.org) frames the DCB and ENF test-method context; the
  energy release rate relations above are standard textbook beam-theory
  results, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
