---
name: walker-forman-crack-growth
description: "Use when you must compute the walker-forman-crack-growth rate of a mode I crack under a nonzero stress ratio in airframe structure: apply the walker-equation equivalent range dK_bar = dK/(1-R)^(1-gamma) with the material gamma exponent and the forman-equation rate da/dN = C_F*dK^m/((1-R)*K_c - dK) with the kc-limited denominator, then extend the crack over a stated cycle block at constant or piecewise stress ratio R. Produces the R-corrected rate table with the walker-equation and forman-equation rates at each station, the equivalent-delta-k correction, the kc-limited amplification of the rate over the zero-R baseline that grows as the peak stress-intensity factor approaches fracture toughness K_c, and the block extension feeding the follow-on life and inspection-interval assessment. Trigger: walker equation, forman equation, stress ratio R, equivalent delta-k, kc-limited growth, R-ratio correction."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: damage-tolerance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: damage-tolerance
  tags: [walker-forman-crack-growth, walker-equation, forman-equation, r-ratio-correction, equivalent-delta-k, kc-limited-growth, stress-ratio-crack-growth]
  version: 0.1.0
  author: AeroSkills
---

# Walker-Forman Crack Growth (structures/damage-tolerance/walker-forman-crack-growth)

Use when the task is the stress-ratio-affected (mean-stress and
toughness-limited) fatigue crack growth rate of a mode I through-
thickness crack under constant-amplitude cyclic loading: the Walker
equivalent stress intensity range, the Forman rate with the K_c-limited
denominator, and the crack extension over a stated cycle block at
constant or piecewise stress ratio R. The Walker relation (Walker 1970,
ASTM STP 462) and the Forman relation (Forman, Kearney and Engle 1967,
ASME Journal of Basic Engineering) correct the da/dN rate of the
linear-elastic fracture mechanics domain for the stress ratio, where
goodman-diagram type corrections act on the S-N stress-life amplitude
domain instead; the R = 0, gamma = 1 limit reproduces the constant-
amplitude Paris baseline of the crack-growth sibling, which owns the
un-corrected Y*sigma*sqrt(pi*a) product as a delivered result. This leaf
reuses that form only as the input to the range correction. The fracture
endpoint stays with residual-strength: here K_c enters only as the
material constant inside the Forman rate denominator, and the arm raises
a deterministic guard at dK = (1-R)*K_c, the fracture state. Scope: mode
I through-thickness crack in a wide panel (geometry factor Y constant),
single half-crack length a growing from a0, far-field tension, constant
amplitude and constant R within a segment with R in [-1, 1) and the
Walker exponent gamma in (0, 1], linear-elastic small-scale-yielding
conditions, material constants C, m, C_F, gamma and K_c given (no da/dN
test-data fitting). No crack-closure (Elber) corrections, no threshold,
no spectrum cycle counting and no variable-amplitude sequence beyond
piecewise-constant R segments.

## Domain quick reference

- Applied cycle pinned by sigma_max and R = sigma_min/sigma_max =
  K_min/K_max: sigma_min = R*sigma_max and the range
  dsigma = sigma_max*(1 - R). Negative R is handled by the pinned
  formulas as written with no R = 0 clamp; both arms stay defined down
  to R = -1 and the equivalent range falls below dK under a compressive
  mean stress.
- Mode I stress intensity K = Y * sigma * sqrt(pi * a) in MPa*sqrt(m),
  with sigma in MPa and a in meters. K_max = Y*sigma_max*sqrt(pi*a) and
  the applied range dK(a) = Y*dsigma*sqrt(pi*a) = K_max*(1 - R).
- Walker equivalent range (Walker 1970, ASTM STP 462):
  dK_bar = dK/(1 - R)^(1 - gamma); the equivalent closed form
  dK_bar = Y*sigma_max*sqrt(pi*a)*(1 - R)^gamma holds to roundoff.
  Recovery limits: R = 0 gives dK_bar = dK for any gamma; gamma = 1
  gives dK_bar = dK for any R (no correction); at R = -1,
  dK_bar = dK/2^(1 - gamma) (dK/sqrt(2) at gamma = 0.5, exact).
- Walker rate: da/dN = C * dK_bar^m in m/cycle. Walker's published
  gamma = 0.5 fits the 2024-T3 and 7075-T6 aluminum data, so
  dK_bar = dK/sqrt(1 - R) in the worked examples.
- Forman rate (Forman, Kearney, Engle 1967):
  da/dN = C_F * dK^m / ((1 - R)*K_c - dK). The denominator vanishes at
  dK = (1 - R)*K_c, equivalent to K_max = K_c (dK = K_max*(1 - R)), the
  fracture state; the arm is undefined at and beyond that point and
  raises ValueError. The terminal acceleration as the denominator
  approaches zero is the kc-limited growth this leaf exists to capture:
  the forman-versus-paris ratio (C_F/C)/((1 - R)*K_c - dK) diverges like
  (1/(1 - R))/(1 - K_max/K_c) as K_max/K_c approaches 1.
- Paris baseline (comparison denominator only, never a growth
  projection): C*dK^m, the R = 0, K_c-infinite limit of both arms.
- Material constants: C and m are the crack-growth Paris arm constants
  of the sibling unit convention (anchor C = 1e-11, m = 3, which
  reproduces the sibling's own 8e-8 m/cycle at dK = 20 when R = 0 and
  gamma = 1). C_F is the Forman arm's own fitted constant; the
  worked-example value C_F = 1e-9 equals C*K_c numerically with
  K_c = 100 MPa*sqrt(m), an example fit whose R = 0 low-range limit
  collapses onto the Paris arm.
- Units (single convention, inherited from the crack-growth sibling):
  sigma in MPa, a in meters, K, dK and K_c in MPa*sqrt(m),
  C in (m/cycle)*(MPa*sqrt(m))^-m,
  C_F in (m/cycle)*(MPa*sqrt(m))^(1 - m), da/dN in m/cycle.
- FAR 25.571 damage tolerance practice for transport aeroplanes frames
  the certification context by name only (far-25, cs-25 reference-only
  in standards-map.yaml, never reproduced).

## Workflow

1. Pin the applied cycle and crack: sigma_max, the stress ratio R, the
   initial half-crack a0 and the geometry factor Y; evaluate the mode I
   stress intensity K_max and the applied range dK with stress_intensity
   (K = Y*sigma*sqrt(pi*a), dK from dsigma = sigma_max*(1 - R)). The
   module rejects non-positive stress, crack length and geometry factor
   with ValueError.
2. Apply the walker-equation equivalent range: compute
   dK_bar = dK/(1 - R)^(1 - gamma) with walker_equivalent_range using
   the material gamma exponent; confirm the R = 0 and gamma = 1 recovery
   limits (both give dK_bar = dK) as the no-correction sanity check.
3. Evaluate the R-corrected rate arms: the walker-equation rate from
   walker_dadN (C*dK_bar^m) and the forman-equation rate with the
   kc-limited denominator from forman_dadN (C_F*dK^m/((1-R)*K_c - dK)),
   plus the walker-versus-paris and forman-versus-paris ratios against
   the zero-R Paris baseline C*dK^m with walker_vs_paris_ratio and
   forman_vs_paris_ratio.
4. Project the block extension: block_extension marches the selected
   model over the stated cycle block with forward-Euler substeps
   (1.0 cycle each when cycles <= 5000, else 5000 equal substeps) that
   re-evaluate dK from the growing crack at every substep, and returns
   the R-corrected rate table rows at cycles 0, N/4, N/2, 3N/4, N plus
   the block extension, start and final rates, and dK / dK_bar bookends.
5. Handle a piecewise stress ratio R: piecewise_block_extension applies
   the ordered (cycles, sigma_max, R) segments, each run by the
   identical march starting from the previous segment's final crack
   length; the split identity (two equal segments reproduce one
   constant-R block bit for bit) is the built-in consistency check.
6. Watch the kc-limited singularity guard: the forman-equation arm
   raises ValueError when the marching crack reaches dK = (1-R)*K_c
   (peak K = K_c, the fracture state owned by residual-strength),
   stating the cycle at which peak K reaches K_c; the walker-equation
   arm carries no K_c term and marches on.
7. Verify: run the gate 3 behavior contract
   (python3 scripts/test_walker_forman_crack_growth.py) under both
   /usr/bin/python3 and the pyenv 3.13.12 interpreter; the closed-form
   identities and the determinism sha256 of the canonical dump hold
   under both.

## Worked example

2024-T3 aluminium fuselage panel, central through-crack (Y = 1.0),
material constants C = 1e-11 (m/cycle)*(MPa*sqrt(m))^-3, m = 3.0,
gamma = 0.5, K_c = 100 MPa*sqrt(m), C_F = 1e-9
(m/cycle)*(MPa*sqrt(m))^(1 - m) (= C*K_c numerically, the example fit).
All values below are the real outputs of scripts/
walker_forman_crack_growth_logic.py, bitwise identical to the wave-45
prep anchor under both interpreters (canonical dump sha256
791d233f3a5c74e9030d56c2359d50b920605b5bba3777f12a7ba401175dab62).

Case 1 (tensile mean, R = 0.35): sigma_max = 100 MPa (sigma_min = 35
MPa, dsigma = 65 MPa), a0 = 0.02 m, block of 2000 cycles. K_max0 =
25.06628274631 MPa*sqrt(m) (K_max/K_c = 0.2507), dK0 = 16.2930837851015,
Walker equivalent dK_bar0 = 20.209083229248 MPa*sqrt(m). Rates at block
start: zero-R baseline 4.32523663134402e-08, Walker
8.25353196314273e-08, Forman 8.88012825993901e-08 m/cycle, so
walker/paris = 1.90822668598782 and forman/paris = 2.05309651628924:
both arms nearly double the R = 0 rate at this range. Walker 2000-cycle
block: a_final = 0.0201660975842774 m (extension 0.166098 mm), rate
growing to 8.3565620180878e-08 m/cycle. Forman block: a_final =
0.0201789260510205 m (extension 0.178926 mm). Far from K_c the two arms
differ only by the R-ratio correction shape.

Case 2 (compressive mean, R = -0.4): sigma_max = 140 MPa (sigma_min =
-56 MPa, dsigma = 196 MPa), a0 = 0.05 m, block of 2000 cycles. K_max0 =
55.4865821664841 (K_max/K_c = 0.5549), dK0 = 77.6812150330778, Walker
equivalent dK_bar0 = 65.6526093976865 MPa*sqrt(m), BELOW dK0: the
compressive mean pulls the equivalent range down. Rates: zero-R baseline
4.6875728436968e-06, Walker 2.82980152371443e-06 (walker/paris =
0.603681610520369 = 1.4^(-1.5), below 1) and Forman 7.52192592680504e-06
m/cycle (forman/paris = 1.60465259476863, above 1 because K_c is felt).
Walker block: a_final = 0.0561787832844155 m (extension 6.179 mm).
Forman block: a_final = 0.0727588016051557 m (extension 22.759 mm), the
kc-limited model grows the same block 3.68 times farther as the
denominator (1-R)*K_c - dK falls from 62.32 to 46.29 MPa*sqrt(m); the
difference IS the damage tolerance life driver.

Near-critical sweep (sigma_max = 100 MPa, R = 0.35): as a grows, the
forman/paris ratio equals 100/((1-R)*K_c - dK) =
(1/0.65)/(1 - K_max/K_c), reading 2.0531 (a = 0.02), 4.9069 (0.15),
13.5222 (0.25), 52.7104 (0.30) and 117.0871 (0.31, K_max/K_c = 0.98686)
while walker/paris stays 1.9082: the terminal acceleration of the
kc-limited denominator is the whole difference. The singularity sits at
dK = (1-R)*K_c = 65 MPa*sqrt(m), i.e. K_max = K_c, beyond which
block_extension raises.

Piecewise-R block (sigma_max = 100 MPa throughout): 1000 cycles at
R = 0.35 then 1000 at R = 0.6, a0 = 0.02 m. Walker model a_final =
0.0201229426364184 m with segment extensions 8.2791219901783e-05 and
4.01514165165699e-05 m (raising R cuts dsigma from 65 to 40 MPa and the
rate in the second segment falls despite the higher mean stress); Forman
model a_final = 0.0201230576354857 m. Split identity: two 1000-cycle
segments at R = 0.35 reproduce the single 2000-cycle block bit for bit
under both models.

## Verification

- Confirm the anchors: stress_intensity(65.0, 0.02, 1.0) =
  16.2930837851015, stress_intensity(100.0, 0.02, 1.0) =
  25.06628274631; walker_equivalent_range(16.2930837851015, 0.35, 0.5) =
  20.209083229248; walker_dadN = 8.25353196314273e-08 and forman_dadN =
  8.88012825993901e-08 m/cycle at the case 1 range, all within the spec
  tolerances (contract test asserts to 1e-9 relative).
- Confirm the recovery limits: R = 0 recovery and gamma = 1 recovery
  give dK_bar = dK exactly; at R = -1, gamma = 0.5 the relation
  dK_bar = dK/sqrt(2) holds to roundoff.
- Confirm the closed-form identities: the gamma = 0.5 square identity
  dK_bar^2*(1 - R) = dK^2 (residual -5.68e-14); the equivalent closed
  form dK_bar = Y*sigma_max*sqrt(pi*a)*(1 - R)^gamma (residual
  -3.55e-15); walker_vs_paris_ratio = (1 - R)^(m*(gamma - 1)) (residual
  -2.22e-16, ratio 1.90822668598782); forman_vs_paris_ratio =
  (C_F/C)/((1 - R)*K_c - dK) (residual 0.0, ratio 2.05309651628924).
- Confirm the direction bound at one fixed range:
  dK_bar(R = -0.4) = 13.7701690836267 < dK_bar(R = 0) = 16.2930837851015
  < dK_bar(R = 0.35) = 20.209083229248 (a tensile mean accelerates and a
  compressive mean retards the Walker rate against the zero-R baseline).
- Confirm the block outputs of both cases and both models, the station
  rows of the R-corrected rate table (monotone in a and rate, with the
  forman/paris ratio climbing 1.60 to 2.16 across the case 2 block while
  walker/paris stays pinned at 0.6037), the piecewise-R results, the
  split identity, the single-cycle march consistency (extension equals
  the rate at the start to a 7.06e-12 relative residual) and the
  superlinear doubling of the extension with the cycle count.
- Confirm ValueError rejection of every non-physical input class: the
  function-level domains (stress, crack length, geometry factor, range,
  R outside [-1, 1), gamma outside (0, 1], C, C_F, K_c, m, dK at or
  beyond (1 - R)*K_c) and the block-level guards (non-positive or
  non-integer cycles, unknown model, a forman block starting at or
  reaching the singularity mid-march with the cycle in the error, empty
  piecewise segments, a segment at R = 1).
- Confirm determinism: two identical full runs produce identical bits;
  the canonical dump sha256 791d233f3a5c74e9030d56c2359d50b920605b5bba3777f12a7ba401175dab62
  holds under both /usr/bin/python3 (3.9.6) and the pyenv 3.13.12 hook
  interpreter; the logic module imports only math and has no RNG.
- Run the gate 3 contract test offline under both interpreters in well
  under 1 s.

## Related leaves

- structures/damage-tolerance/crack-growth: the R = 0 constant-amplitude
  arm of this pack; it owns the Y*sigma*sqrt(pi*a) stress intensity
  evaluation as a delivered product and the Paris law rate and
  cycles-to-critical projection. Its unit convention and Paris anchor
  (C = 1e-11, m = 3, dK = 20 gives da/dN = 8e-8 m/cycle) are inherited
  here, and its zero-R rate is the comparison baseline of both arms of
  this leaf. Questions that lead with a nonzero stress ratio R or a
  K_c-limited rate belong to this leaf.
- structures/damage-tolerance/residual-strength: owns the fracture
  endpoint: residual strength, the critical crack length at which the
  applied stress drives K to K_c, and the fracture margins. K_c enters
  this leaf only as the material constant inside the Forman rate
  denominator, and the singularity guard hands the fracture state to
  that sibling.
- structures/damage-tolerance/widespread-fatigue-damage: the MSD/MED
  multiple-site damage screening of FAR 25.571(b)/(c), no rate content.
- structures/damage-tolerance/bird-strike: the certification impact
  energy vein; its residual_strength_fraction is a post-impact knock-
  down of a struck component, not a growing-crack rate.
- structures/fatigue/goodman-diagram: the S-N infinite-life mean-stress
  correction (stress-life domain); Goodman, Gerber and Soderberg correct
  the allowable stress amplitude, while Walker and Forman correct the
  da/dN rate of the crack-growth (LEFM) domain this leaf lives in.
- structures/fatigue/stress-life-curve and
  structures/fatigue/strain-life-fatigue: stress-life curve fitting and
  the strain-life domain under fully reversed loading; no leaf of the
  fatigue pack touches da/dN.

## Pitfalls

- Mixing units: passing sigma or dK in Pa while C is in
  (m/cycle)*(MPa*sqrt(m))^-m (or the reverse) shifts the rate by
  (1e6)^m. Keep the single convention: sigma in MPa, a in meters, K, dK
  and K_c in MPa*sqrt(m), C in (m/cycle)*(MPa*sqrt(m))^-m and C_F in
  (m/cycle)*(MPa*sqrt(m))^(1 - m).
- Treating R as zero: the whole point of this leaf is the stress-ratio
  correction. At R = 0.35 both corrected arms nearly double the zero-R
  baseline; running the uncorrected rate silently drops the mean-stress
  and K_c-proximity content of the answer.
- Holding dK constant while the crack grows: the block march
  re-evaluates dK = Y*dsigma*sqrt(pi*a) from the growing crack at every
  substep; a constant-range shortcut understates the extension of a
  fast-growing crack (doubling the cycles more than doubles the
  extension).
- Running the forman-equation arm at or beyond the singularity: the
  denominator (1 - R)*K_c - dK vanishes at dK = (1 - R)*K_c, i.e.
  K_max = K_c, the fracture state. The arm raises ValueError there; the
  fracture endpoint, critical crack length and margins belong to
  residual-strength, not to a rate computation.
- Confusing the correction domains: Walker and Forman correct the da/dN
  rate of the LEFM domain; Goodman, Gerber and Soderberg correct the S-N
  amplitude of the stress-life domain (goodman-diagram). The stress
  ratio R is defined the same way (R = sigma_min/sigma_max) in both, but
  the outputs are not interchangeable.
- Clamping negative R to zero: the pinned formulas handle R in
  [-1, 1) as written; an R = 0 lower clamp would erase the compressive-
  mean retardation the Walker arm is built to show (at R = -0.4 the
  equivalent range falls below dK).
- Forgetting the certification context is reference-only: FAR 25 and
  CS 25 are named as context only, never reproduced; the Walker and
  Forman relations are standard published engineering methodology,
  summary-only per standards-map.yaml.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_walker_forman_crack_growth.py

The test covers, step by step, the stress intensity anchors and the
dK = K_max*(1 - R) range split (step 1), the walker-equation equivalent
range with the recovery limits, the R = -1 square-root relation, the
square identity and the equivalent closed form (step 2), the
walker-equation and forman-equation rates and both model-versus-baseline
ratios including the R = 0 far limit, linearity in C_F and the
monotone near-critical sweep (step 3), the case 1 and case 2 block
outputs and the R-corrected rate table rows of both models (step 4),
the piecewise-R block and the bit-for-bit split identity (step 5), the
ValueError battery of function domains and the kc-limited singularity
guard with the cycle in the error (step 6), and the canonical dump
determinism sha256 791d233f3a5c74e9030d56c2359d50b920605b5bba3777f12a7ba401175dab62
plus the stdlib-only purity of the logic module (step 7). It passes
under both /usr/bin/python3 (3.9.6) and the pyenv 3.13.12 interpreter.
33 tests, deterministic, well under 1 s.

## Compliance

- The Walker equivalent range and the Forman rate are published
  engineering methodology (Walker 1970, ASTM STP 462; Forman, Kearney
  and Engle 1967, ASME Journal of Basic Engineering), summary-only
  paraphrase. The airworthiness context is the FAR-25.571 damage
  tolerance basis of transport aeroplanes and its CS-25 counterpart,
  referenced by name only per standards-map.yaml (both reference-only,
  never reproduced).
- compliance: STANDARDS-REF, gated: false.
