---
name: beam-column-analysis
description: "Use when you must margin-check a compression member that also carries bending: compute the Euler load P_E, the moment amplification factor delta that grows the moment as the axial load nears the Euler load, the amplified moment, the secant-formula peak compressive stress of an eccentrically loaded column, and the axial-plus-bending interaction ratio with its margin of safety and pass verdict. Produces P_E, the amplification factor, the amplified moment, the peak combined stress, the interaction ratio, the margin and the verdict for the combined-loading check. SI units, stdlib. Trigger: combined axial compression and bending, moment amplification factor, euler load, secant formula, load eccentricity, margin of safety."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: fem
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [beam-column-analysis, moment-amplification-factor, secant-formula, load-eccentricity, axial-bending-interaction-ratio]
  version: 0.1.0
  author: AeroSkills
---

# Beam-Column Analysis (structures/fem/beam-column-analysis)

Use when the task is the global member-level margin check of a slender
compression member that also carries bending: a longeron, spar cap or
actuator rod under combined axial compression and primary end moment or
lateral load. The Euler load P_E = pi^2 E I / (K L)^2 of the member sets
the amplification denominator, the moment amplification factor
delta = c_m / (1 - P/P_E) grows the primary moment as the axial load
approaches the Euler load, the secant formula gives the peak compressive
stress of an eccentrically loaded column, and the axial-plus-bending
interaction ratio P/P_cr + M/(M_cap (1 - P/P_E)) with its margin of
safety 1/ratio - 1 and the pass verdict closes the combined-loading
check. The logic module is pure Python standard library, deterministic,
with no FEA software. It pairs with structures/fem/buckling-analysis,
which owns the concentrically loaded Euler column and rates it slender
or stubby; this leaf takes P_E only as the amplification denominator and
interaction input. Structures/fem/beam-frame-analysis supplies first-
order member forces that this leaf then margin-checks under combined
loading. Units are SI: E in Pa, I in m^4, A in m^2, L and eccentricity in
m, forces in N, moments in N m, stresses in Pa.

## Domain quick reference

- Euler load of the member, the classic ideal-column critical load:

      P_E = pi^2 E I / (K L)^2

  where K is the effective length factor resolved from the end
  conditions (per the concentric-column sibling; pinned-pinned K = 1.0,
  fixed-fixed K = 0.5 raises P_E by the factor 4, cantilever K = 2.0
  lowers it by the factor 4).

- Moment amplification factor (standard second-order factor, name and
  paraphrase):

      delta = c_m / (1 - P/P_E)

  with c_m = 1.0 for the worst-case constant moment. delta is 1.0 at
  zero axial load and grows without bound as P approaches P_E from
  below. The amplified primary moment is M_amp = delta * M.

- Secant-formula peak compressive stress of an eccentrically loaded
  column (classical secant formula, name and paraphrase):

      sigma_max = (P/A) (1 + (e c / r^2) / cos((K L / (2 r)) sqrt(P/(E A))))

  with e the load eccentricity, c the extreme-fiber distance and
  r = sqrt(I/A) the radius of gyration. The secant argument reaches
  pi/2 exactly at P = P_E, so sigma_max diverges precisely where the
  member buckles. At e = 0 the formula returns P/A exactly, the pure
  axial stress limit.

- Section yield moment capacity of the extreme fiber:

      M_cap = sigma_y I / c

- Axial-plus-bending interaction ratio with its amplification carried
  inside the bending term:

      ratio = P/P_cr + M_applied / (M_cap (1 - P/P_E))
      margin = 1/ratio - 1
      pass = ratio <= 1.0  (inclusive)

  With M_applied = 0 the ratio degenerates to P/P_cr and the margin to
  P_cr/P - 1, the pure-axial margin-of-safety identity of the
  concentric-column sibling.

## Workflow

1. Fix the limit load case at the critical station: member properties
   E, I, A, L, the effective length factor K from the support
   conditions, the radius of gyration r = sqrt(I/A), the extreme-fiber
   distance c, the limit axial load P and the primary end moment M, or
   the load eccentricity e = M/P when the moment enters that way.
2. Euler load traverse: call euler_load(e_mod, i, l, k) to get P_E,
   form the axial ratio P/P_E and confirm it sits strictly below unity,
   the pole at which the amplification diverges. If the axial-only
   critical load P_cr comes from the concentric-column sibling, form
   the axial utilization P/P_cr too.
3. Moment amplification traverse: call moment_amplification(p, p_euler,
   c_m) for delta, multiply the primary moment by delta for the
   amplified moment, and form the amplified bending utilization
   delta * M / M_cap against the section capacity.
4. Secant-formula stress traverse: for an eccentrically loaded column
   call secant_stress(p, area, ecc, c, r, l, e_mod, k) to get the peak
   compressive stress sigma_max, and compare it against the yield
   strength. A result at or above P_E means the member buckles before
   it can resist the bending, and the guard raises ValueError.
5. Interaction-ratio traverse: call interaction_check(p, p_cr,
   m_applied, m_capacity, p_euler) and read the dict with keys ratio,
   margin and pass. The margin of safety 1/ratio - 1 and the pass
   verdict gate the global combined-loading margin check.
6. Contract-test confirmation: run python3
   scripts/test_beam_column_analysis.py and confirm every deterministic
   case passes offline.

## Worked example

The steel member of the buckling-analysis worked anchor, E = 200 GPa,
I = 1e-6 m^4, A = 1e-3 m^2, L = 3.0 m, pinned-pinned K = 1.0, now
carrying combined loading. Solid circular section: r = sqrt(I/A) =
0.031623 m, extreme fiber c = 2 r = 0.063246 m, effective slenderness
K L / r = 94.8683. Limit axial load P = 100 kN with a primary end moment
M = 1 kN m from a load eccentricity e = M/P = 10 mm at the loaded end.
Real outputs of the module:

- P_E = euler_load(200e9, 1e-6, 3.0) = 219324.542 N = 219.325 kN, so
  P/P_E = 0.455945. The same member at K = 0.5 gives 877.298 kN and at
  K = 2.0 gives 54.831 kN, the K-squared scaling.
- delta = moment_amplification(100e3, 219324.542) = 1.838051, so the
  amplified primary moment is 1.838 kN m. The unamplified bending
  utilization M/M_cap is 0.252982, but the amplified utilization
  M/(M_cap (1 - P/P_E)) is 0.464994: amplification is the whole story.
- sigma_max = secant_stress(100e3, 1e-3, 0.010, 0.063246, 0.031623, 3.0,
  200e9, 1.0) = 2.295230e8 Pa = 229.5230 MPa, 0.9181 of the 250 MPa
  yield strength; the secant argument is 1.060660 rad, comfortably below
  the pi/2 = 1.570796 rad pole at P_E.
- M_cap = sigma_y I / c = 250e6 * 1e-6 / 0.063246 = 3952.847 N m (3.953
  kN m).
- interaction_check(100e3, 219324.542, 1000.0, 3952.847, 219324.542):
  axial term 0.455945, amplified moment term 0.464994, ratio = 0.920939,
  margin = +0.085848 (8.58%), verdict PASS. The Euler-only margin of
  safety on this member is 1.19; adding the 1 kN m primary bending
  moment drops the combined margin to +0.086, about a 93% reduction,
  and ignoring the moment amplification would overstate the margin to
  1/0.708927 - 1 = +0.411.
- Overload case P = 130 kN, M = 1.2 kN m (e = 9.23 mm): delta =
  2.455424, ratio = 1.3381, margin = -0.2527, verdict FAIL; the secant
  peak stress is 344.61 MPa, above the 250 MPa yield. The member passes
  neither check at this load.

## Verification

Deterministic checks, all offline:

- moment_amplification(0.0, p_euler) = 1.0 exactly; secant_stress with
  ecc = 0.0 returns P/A = 1.0e8 Pa exactly; the pinned-pinned to
  fixed-fixed Euler load ratio is 4.0 exactly (K enters squared).
- Divergence consistency: the secant argument at P = P_E computes to
  1.570796 rad = pi/2, and moment_amplification raises ValueError at
  p >= p_euler, as does secant_stress once the argument reaches pi/2
  (asserted at p = p_euler + 1.0 N, strictly above the pole).
- Monotonicity: delta rises 1.295291 at P = 50 kN, 1.838051 at P =
  100 kN, 3.163736 at P = 150 kN; secant_stress rises with ecc at fixed
  P.
- Pure-axial degeneration: interaction_check(100e3, 219324.542, 0.0,
  3952.847, 219324.542) gives ratio 0.455945 and margin +1.193245, the
  buckling-analysis margin of safety MS = Pcr/P - 1 = 1.19 anchor.
- Rejection: non-positive modulus, moment of area, length, effective
  length factor, radius of gyration, extreme-fiber distance, capacity
  and negative eccentricity all raise ValueError, as do axial loads at
  or above the Euler load in every function that divides by
  1 - P/P_E.
- Run the contract test: python3
  scripts/test_beam_column_analysis.py (27 tests, deterministic,
  exit 0).

## Related leaves

- structures/fem/buckling-analysis: the concentrically loaded slender
  column, source of the Euler critical load, the end-condition factors
  and the slender-or-stubby rating; the pure-axial margin of safety
  this leaf reproduces at zero moment.
- structures/fem/beam-frame-analysis: first-order rigid-jointed frame
  solves whose member axial and bending results feed the combined
  margin check here when a member carries both.
- structures/fem/plate-buckling: flat-panel compression and shear
  stability, the panel-level stress interaction that this leaf does not
  cover.
- structures/fem/truss-analysis: pin-jointed axial bars with no bending
  moment, the pure-axial limit of this leaf's interaction ratio.

## Contract test

Run it offline and deterministic from the repo root:

    python3 scripts/test_beam_column_analysis.py

The suite exercises the numbered Workflow steps by name: the Euler load
traverse (step 2) against the 219.325 kN worked anchor with the K
scaling and the exact 4.0 ratio, the moment amplification traverse
(step 3) against delta 1.838051 with the monotone series, the zero-load
unity limit, the c_m scaling and the amplification-to-interaction
utilization bridge, the secant-formula stress traverse (step 4) against
the 229.5230 MPa peak with the ecc = 0 pure-axial limit, eccentricity
monotonicity, the pi/2 pole and the overload-yield case, the
interaction-ratio traverse (step 5) against ratio 0.920939 PASS and the
130 kN overload FAIL, the pure-axial margin identity 1.193245, the
inclusive ratio = 1.0 boundary, the exact dict keys and margin
recomputation, plus cross-step determinism and bool verdict typing
(step 6). It also asserts every ValueError rejection named in the spec
Validation list.

## Pitfalls

- Sizing on the unamplified moment: ignoring delta = 1/(1 - P/P_E)
  overstates the margin to +0.411 against the true +0.086 in the worked
  example. At P/P_E = 0.456 the amplification nearly doubles the
  bending utilization.
- Applying the pure-axial Euler margin to a bending member: the axial
  margin of safety is 1.19, but the combined margin falls to +0.086
  once the 1 kN m primary moment is added, a 93% reduction. The
  interaction ratio, not the axial ratio, gates the combined case.
- Running at or above the Euler load: both delta and the secant
  argument diverge at P = P_E, where the member buckles before it can
  resist the moment. Inputs at or above P_E raise ValueError in every
  amplification and interaction function; a result near the pole means
  the check is meaningless, not that the margin is huge.
- Feeding the eccentricity in millimeters: the worked eccentricity is
  10 mm = 0.010 m; passing 10.0 m for ecc makes the secant term
  e c / r^2 enormous and the stress wrong by orders of magnitude. All
  length inputs are meters.
- Confusing the extreme-fiber distance with the radius of gyration: for
  the solid circular section c = 2 r = 0.063246 m while r = 0.031623 m;
  swapping them halves the eccentricity leverage term and understates
  the peak stress.
- Double counting the amplification: the interaction bending term
  carries 1/(1 - P/P_E) built in, so the applied moment must enter
  interaction_check unamplified; multiplying M by delta first inflates
  the ratio and fails healthy members.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_beam_column_analysis.py

The test covers the Euler load traverse with the worked P_E anchor, the
K-squared scaling and the non-physical-input rejections, the moment
amplification traverse with the 1.838051 worked factor, the monotone
series to the pole, the exact unity limit and the c_m scaling, the
secant-formula stress traverse with the 229.5230 MPa worked peak, the
ecc = 0 pure-axial limit, the eccentricity monotonicity, the pi/2 pole
guard and the overload-yield comparison, the interaction-ratio traverse
with the PASS case, the FAIL overload, the pure-axial margin identity,
the inclusive ratio = 1.0 boundary, exact dict keys and the margin
recomputation, plus determinism and boolean verdict typing. All 27
methods must pass and the process must exit 0.

## Compliance

- Standards referenced, not reproduced: FAR/CS 25 airworthiness strength
  and margin requirements frame the combined-loading context
  (reference-only per standards-map.yaml). The Euler load, the moment
  amplification factor and the secant formula above are standard
  engineering methodology, summary-only, named and paraphrased, never
  quoted from a standard text.
- compliance: STANDARDS-REF, gated: false.
