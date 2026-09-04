# Wave-33 leaf spec: delta-wing-vortex-lift (aerodynamics, cfd pack)

- Path: skills/aerodynamics/cfd/delta-wing-vortex-lift/
- Pack: cfd (hosts the lift-prediction methods; router routes
  potential-flow and lift-distribution methods to VLM/panel siblings).
  Sibling receipts: vortex-lattice-method owns horseshoe/bound vortex
  attached-flow only (self-declared: "invalid for |alpha| at or above
  45 degrees and never models stall", "straight trapezoidal wing");
  panel-method owns incompressible potential flow + Kutta + d'Alembert
  zero drag (attached only); swept-wing-aerodynamics owns simple-sweep
  cosine corrections (subsonic small-disturbance);
  high-lift-systems owns mechanical devices only (no blowing/powered/Cmu
  tokens); lift-curve-slope owns attached 3D slope corrections;
  drag-polar owns the parabolic polar. Zero Polhamus/suction-analogy/
  vortex-lift tokens family-wide. This leaf is the ONLY separated-flow
  vortex-lift model in the library.
- Standards id: naca-tr-824 (reference-only; the frontmatter anchor).
  Primary methodology source NASA TN D-3767 (Polhamus 1966) is named +
  paraphrased in the body (public-domain NTRS; reference-only, no
  reproduction). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Estimate the low-speed lift of a sharp-edged slender delta wing by the
Polhamus leading-edge suction analogy: total lift CL = Kp sin(alpha)
cos^2(alpha) + Kv cos(alpha) sin^2(alpha), the sum of the attached
potential term (Kp, the small-angle lift slope, slender-wing value pi
AR/2) and the leading-edge-separation vortex term (Kv, growing from
3.14 at AR 0 to about 3.45 at AR 4). Produces the potential/vortex lift
split, the drag due to lift, and the angle at which the vortex term
overtakes the potential term. Valid for sharp leading edges, subsonic
flow, AR about 0.5-2.0, alpha up to about 25 degrees.

Does NOT do: attached-flow linear methods (VLM/panel/swept-wing
cosine); mechanical high-lift devices (high-lift-systems); vortex
breakdown onset/location (empirical charts only - not modeled);
vortex generators; circulation control / blown flaps; ice accretion;
leading-edge extensions as separate devices.

## Model (implement exactly)

Module constants:
- PI = math.pi.
- KV_0 = 3.14 (Kv at AR = 0, NASA TN D-3767 text anchor).
- KV_4 = 3.45 (Kv at AR = 4, TN Fig. 9 discussion).
- AR_CLAMP = 4.0.

Functions (pure stdlib):

- delta_aspect_ratio(le_sweep_deg) -> AR = 4 / tan(Lambda_LE) for a
  full delta (76 deg -> about 1.0; 45 deg -> 4.0). ValueError if
  le_sweep_deg <= 0 or >= 90.
- slender_delta_kp(ar) -> pi * ar / 2. ValueError if ar <= 0.
- delta_kv(ar) -> linear interpolation KV_0 + (KV_4 - KV_0) * min(ar,
  AR_CLAMP) / AR_CLAMP over [0, 4]; clamp ar to [0, 4] with ValueError
  on ar < 0.
- polhamus_cl(kp, kv, alpha_deg) -> CL_total = kp * sin(a) * cos(a)^2
  + kv * cos(a) * sin(a)^2 (TN eq. 15).
- polhamus_cl_potential(kp, alpha_deg) -> kp sin(a) cos^2(a).
- polhamus_cl_vortex(kv, alpha_deg) -> kv cos(a) sin^2(a).
- cd_due_to_lift(cl, alpha_deg) -> cl * tan(a) (TN: "drag due to lift
  is the product of the total lift coefficient and the tangent of the
  angle of attack").
- vortex_potential_crossing_deg(kp, kv) -> angle where the vortex term
  equals the potential term: tan(alpha) = kp / kv ->
  alpha = atan(kp/kv) in degrees. ValueError if kv <= 0.
- delta_lift_summary(ar_or_sweep, alpha_deg, ...) -> dict {aspect
  ratio, kp, kv, alpha_deg, cl_potential, cl_vortex, cl_total,
  cd_due_to_lift, vortex_fraction, crossing_deg}. Document the input
  convention (accept AR directly, or sweep angle with a flag).

## Worked example

AR 1.0 delta (Lambda_LE = 76 deg), alpha = 15 deg, and AR 0.5.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- delta_aspect_ratio(76) about 1.0; delta_aspect_ratio(45) about 4.0.
- slender_delta_kp(1.0) = pi/2 about 1.570796.
- delta_kv(1.0) = 3.14 + 0.31/4 about 3.2175; delta_kv(0) = 3.14;
  delta_kv(4) = 3.45.
- alpha 15 deg, AR 1.0: CL_pot about 0.3793, CL_vort about 0.2082,
  CL_total about 0.5875 (vortex = 35.4% of lift).
- Sweep at AR 1.0: CL(5) about 0.160, CL(10) about 0.360, CL(15) about
  0.588, CL(20) about 0.828, CL(25) about 1.066 (monotone to 25 deg).
- cd_due_to_lift(15 deg) = 0.5875 * tan(15) about 0.157.
- AR 0.5 (Lambda_LE about 82.9 deg), alpha 20: CL about 0.5866 (vortex
  = about 60%).
- crossing_deg(AR 1.0): atan(pi/2 / 3.2175) about 26.0 deg; AR 0.5
  about 13.9 deg (vortex dominance earlier for slenderness).
- Identity: CL(0) = 0.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: sweep <= 0 or >= 90; ar < 0; kv <= 0 for crossing.
- AR identity: delta_aspect_ratio(76) about 1.0; 45 deg about 4.0.
- Kv anchors: 3.14 at AR 0; 3.45 at AR 4; linear in between.
- CL(0) == 0 exactly; CL positive increasing over 5-25 deg at AR 1.
- Vortex fraction grows as AR shrinks (AR 0.5 alpha 20 about 60% vs
  AR 1.0 alpha 15 about 35%).
- Crossing angle shrinks with AR (slender wings dominated by vortex
  lift earlier).
- Determinism: identical floats run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-delta-wing-vortex-lift.yaml)

Query 1 (copy verbatim):
  "estimate the lift of a sharp edged slender delta wing at 20 degrees angle of attack using the leading edge suction analogy and aspect ratio 1"
  intent: "aerodynamics; Polhamus leading-edge suction analogy delta-wing vortex lift estimate"
  expected_skill: "aerodynamics/cfd/delta-wing-vortex-lift"
Query 2 (copy verbatim):
  "compute the nonlinear vortex lift increment of the 76 degree swept delta beyond the linear attached flow range of the vortex lattice method"
  intent: "aerodynamics; delta-wing vortex-lift increment vs VLM attached-flow range"
  expected_skill: "aerodynamics/cfd/delta-wing-vortex-lift"
Task ids: w33-delta-wing-vortex-lift-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the vortex lift of a
sharp-edged delta wing:" and include the outputs in the Claim. First
tag: delta-wing-vortex-lift. Additional tags ONLY: polhamus-suction-
analogy, leading-edge-vortex, slender-delta-wing, vortex-lift-split,
drag-due-to-lift, nonlinear-lift. NEVER single generic words (delta,
wing, vortex, lift, sweep, angle, suction). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): horseshoe vortex, vortex
lattice, bound vortex (vortex-lattice-method); panel, Kutta, source
sink (panel-method); cosine sweep correction, critical Mach (swept-
wing-aerodynamics); slat, flap, Krueger, mechanical high lift
(high-lift-systems); vortex breakdown onset (not modeled);
circulation control, blowing. The tokens "leading edge suction
analogy", "vortex lift", "Polhamus", "slender delta" are this leaf's
own.

Tags: [delta-wing-vortex-lift, polhamus-suction-analogy,
leading-edge-vortex, slender-delta-wing, vortex-lift-split,
drag-due-to-lift, nonlinear-lift]

Sibling-citation lines for Related leaves:
aerodynamics/cfd/vortex-lattice-method (attached-flow linear sibling;
this leaf covers the separated vortex regime it excludes),
aerodynamics/high-lift/high-lift-systems,
aerodynamics/high-speed/swept-wing-aerodynamics.

Ledger Standard: naca-tr-824.
