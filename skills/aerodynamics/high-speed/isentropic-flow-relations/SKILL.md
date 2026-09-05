---
name: isentropic-flow-relations
description: 'Use when you must convert a Mach number into the isentropic total to static ratios of a compressible flow: the total temperature, pressure and density ratios of a perfect gas at gamma 1.4, rebuild total conditions from a static state and Mach number, recover the Mach number that produces a given area ratio from the area-Mach relation on the subsonic low branch or the supersonic high branch, and compute the choked mass flow a passage passes at its sonic throat from total pressure, total temperature and throat area. Produces the three total to static ratios, both Mach roots for the given area ratio and the choked mass flow in kg/s, the gate numbers for duct and wind tunnel analysis. Trigger: isentropic flow, total to static ratio, mach from area ratio, choked mass flow, sonic throat, wind tunnel contraction, compressible flow, mach number.'
license: Apache-2.0
compliance: STANDARDS-REF
standards:
- id: naca-tr-824
  reference-only: true
gated: false
domain: aerodynamics
pack: high-speed
compatibility: agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags:
  - isentropic-flow-relations
  - total-to-static-ratio
  - mach-from-area-ratio
  - choked-mass-flow
  version: 0.1.0
  author: AeroSkills
---

# Isentropic Flow Relations (aerodynamics/high-speed/isentropic-flow-relations)

Use when you must convert a Mach number into the isentropic total to
static ratios of a compressible flow, recover the Mach number from a
given area ratio on both branches of the area-Mach relation, or
compute the choked mass flow a passage passes at its sonic throat.
This leaf implements the standard isentropic relations for a perfect
gas at gamma 1.4 (air, R = 287.0) in pure Python, stdlib only: the
total temperature, total pressure and total density ratios from a Mach
number, the total condition rebuild from a static state, the subsonic
and supersonic roots of the area-Mach relation by deterministic
bisection, and the choked mass flow through the mass flow parameter.
It pairs with the high-speed pack leaves for the neighboring
non-isentropic mechanisms: normal-shock for the state change across a
shock, prandtl-meyer for expansion fans, and shock-expansion-airfoil
for the patched airfoil solution. It does not compute shock or fan
state changes, pitot pressure behind a shock, compressibility
corrections, or nozzle throat sizing and thrust; those belong to the
sibling leaves below.

## Domain quick reference

- Total temperature ratio: T0/T = 1 + (gamma - 1)/2 * M^2, from the
  energy equation at gamma 1.4: T0/T = 1 + 0.2 * M^2.
- Total pressure and density ratios from the isentropic exponents:
  p0/p = (T0/T)^(gamma/(gamma - 1)) = (T0/T)^3.5 and rho0/rho =
  (T0/T)^(1/(gamma - 1)) = (T0/T)^2.5 at gamma 1.4.
- All three ratios equal 1.0 at M = 0 and grow without bound with M.
- Area-Mach relation: A/A* = (1/M) * ((2/(gamma + 1)) * (1 + (gamma -
  1)/2 * M^2))^((gamma + 1)/(2 * (gamma - 1))) with A* the sonic throat
  area. The ratio is monotone decreasing on the subsonic branch (0, 1],
  monotone increasing on the supersonic branch [1, 20], and its minimum
  is 1.0 exactly at M = 1.0.
- Inverse on both branches: every A/A* above 1.0 has two Mach roots,
  the subsonic root below 1.0 (contraction side, low branch) and the
  supersonic root above 1.0 (test section, high branch).
- Rebuild of total conditions from a static state: p0 = p * (p0/p) and
  T0 = T * (T0/T) with the same closed forms, exact round trip.
- Choked mass flow at a sonic throat: mdot = MFP * p0 * A* /
  sqrt(T0) with the mass flow parameter MFP = sqrt(gamma/R) * (2/(gamma
  + 1))^((gamma + 1)/(2 * (gamma - 1))) = 0.0404184199 kg sqrt(K) /
  (Pa s); mdot in kg/s for p0 in Pa, T0 in K and A* in m2.
- Module constants: GAMMA = 1.4, R = 287.0, MACH_TOL = 1e-12, and the
  bisection brackets SUB_LO = 0.05, SUB_HI = 0.99, SUP_LO = 1.01,
  SUP_HI = 20.0.
- NACA-TR-824 frames the compressible flow methodology; the relations
  above are standard engineering formulas, summary-only (name and
  paraphrase, never reproduced verbatim).

## Workflow

1. State the flow point and the gas: record the Mach number M, the
   static pressure and static temperature when a static state is
   given, and the module constants GAMMA = 1.4 and R = 287.0 from
   scripts/isentropic_flow_relations_logic.py.
2. Convert the Mach number into the total to static ratio set with
   total_static_ratios(mach): the dict keys t0_over_t, p0_over_p and
   rho0_over_rho from the isentropic exponents at gamma 1.4.
3. Rebuild the total conditions from a static state with
   static_to_total(p_static, t_static, mach): p0 and t0 from the same
   closed forms, and confirm the round trip against
   total_static_ratios at the same Mach number (exact to machine
   precision).
4. Evaluate the area-Mach relation at the Mach number with
   area_ratio(mach) to get A/A*, the area ratio against the sonic
   throat area.
5. Recover the Mach number from a given area ratio A/A* with
   mach_from_area_ratio(aa, subsonic): pass subsonic True for the low
   branch root (contraction side) or subsonic False for the high
   branch root (test section). Deterministic bisection of area_ratio(M)
   - aa halves the fixed bracket [SUB_LO, SUB_HI] or [SUP_LO, SUP_HI]
   until the width falls below MACH_TOL = 1e-12 and returns the
   midpoint; near-sonic ratios re-bracket onto [SUB_HI, 1.0] or
   [1.0, SUP_LO] so the root stays inside a sign-change bracket.
6. Compute the choked mass flow the passage passes at its sonic throat
   with choked_mass_flow(p0, t0, area_star): mdot in kg/s through the
   mass flow parameter, and check the identity mdot * sqrt(t0) / (p0 *
   area_star) = MFP at every operating point.
7. Confirm the deterministic and rejection checks by running the
   contract test scripts/test_isentropic_flow_relations.py, which
   exercises steps 2 through 6 and every ValueError rejection.

## Worked example

Air at gamma = 1.4, R = 287.0. Supersonic wind tunnel test section at
M = 2.0 fed from a stilling chamber at p0 = 101325 Pa and T0 = 288.15 K
(real module outputs):

- Step 2, total_static_ratios(2.0): t0_over_t 1.8, p0_over_p
  7.8244490669 and rho0_over_rho 4.3469161483.
- Step 4, area_ratio(2.0): A/A* = 1.6875, the classic supersonic
  value; area_ratio(1.0) = 1.0 exactly and area_ratio(0.5) =
  1.33984375.
- Step 5, mach_from_area_ratio(1.6875, subsonic = False): returns
  2.000000000000 within the 1e-12 bracket width; the subsonic root for
  the same area ratio, mach_from_area_ratio(1.6875, subsonic = True),
  is 0.372244486203, the contraction-side Mach at the same station.
- Step 5 on the common contraction ratio A/A* = 2.0: the supersonic
  root is 2.197198121652 and the subsonic root is 0.305903834189.
- Step 2 at the subsonic cruise point M = 0.85: t0_over_t 1.1445,
  p0_over_p 1.6038187614, rho0_over_rho 1.4013270087 and A/A*
  1.020668536305.
- Step 3, static_to_total(30000.0, 220.0, 0.85): p0 = 48114.562843 Pa
  and t0 = 251.79 K. Rebuilding the M = 2.0 static state from the
  stilling chamber gives p = 12949.793543 Pa and T = 160.083333 K;
  feeding those back through static_to_total(12949.793543,
  160.083333, 2.0) returns p0 = 101324.999996 Pa and t0 =
  288.149999 K, and the full precision state rounds the trip to
  101325.000000 and 288.150000 exactly.
- Step 6, choked_mass_flow(101325.0, 288.15, 0.01): mdot =
  2.4126072679 kg/s through a 0.01 m2 sonic throat. Doubling p0 to
  202650 Pa doubles the flow to 4.8252145358 kg/s; doubling the throat
  area to 0.02 m2 gives the same 4.8252145358 kg/s; quadrupling T0 to
  1152.6 K halves the flow to 1.2063036339 kg/s. The identity mdot *
  sqrt(t0) / (p0 * area_star) = 0.0404184199 holds at every point.

## Verification

- Confirm total_static_ratios anchors: (0.85) gives 1.1445,
  1.6038187614 and 1.4013270087; (2.0) gives 1.8, 7.8244490669 and
  4.3469161483; (3.0) gives 2.8, 36.7327218050 and 13.1188292161; all
  ratios are exactly 1.0 at M = 0; a negative Mach number raises
  ValueError.
- Confirm the closed forms of area_ratio: 1.0 at M = 1.0 within 1e-15,
  1.6875 at M = 2.0 and 1.33984375 at M = 0.5 within 1e-12, and
  1.020668536305 at M = 0.85 within 1e-9; monotone decreasing on the
  subsonic branch and increasing on the supersonic branch; mach 0 or
  negative raises ValueError.
- Confirm the recovered roots: the supersonic root of 1.6875 is 2.0
  within 1e-10 and its subsonic root is 0.372244486203; the roots of
  2.0 are 2.197198121652 and 0.305903834189; the near-sonic ratio
  1.00005 gives 0.992270777840 and 1.007762554875; A/A* = 1.0 returns
  1.0 on both branches; A/A* below 1.0, subsonic ratios at or above
  11.591443867187, and supersonic ratios above 15377.343750000022
  raise ValueError.
- Confirm the round trips: mach_from_area_ratio(area_ratio(m)) returns
  m within 1e-10 for m = 0.5, 2.0 and 3.0 on their own branches, and
  static_to_total inverts total_static_ratios to machine precision.
- Confirm the choked flow scaling: linear in p0 and in the throat
  area, inverse in sqrt(t0), and the mass flow parameter identity
  holds for every input.
- Confirm determinism: two calls of mach_from_area_ratio on identical
  inputs return identical bits.
- The offline contract test asserts every item above; run it with
  python3 scripts/test_isentropic_flow_relations.py (33 test methods,
  deterministic, under 20 seconds).

## Contract test

Run the offline stdlib unittest from the leaf directory (or from the
repo root):

    python3 scripts/test_isentropic_flow_relations.py

The 33 methods assert the spec anchors inside the tolerance bounds
taken from this leaf's real module outputs: the total to static ratio
set at M = 0.85, 2.0 and 3.0 and the zero-Mach identity; the total
condition rebuild and the exact round trip at M = 2.0; the closed-form
and cruise area ratios and the monotone branch behavior of the
area-Mach relation; the recovered subsonic and supersonic roots for
A/A* = 1.6875, 2.0 and 1.00005; the branch round trips; the sonic,
floor and ceiling edge rules; the choked mass flow anchors and its
p0, area and temperature scalings; the mass flow parameter identity;
determinism; and ValueError rejection of every non-physical input
class. It must pass offline with exit code 0.

## Related leaves

- skills/aerodynamics/high-speed/normal-shock: state ratios across a
  normal shock, including the stagnation pressure loss.
- skills/aerodynamics/high-speed/prandtl-meyer: expansion fan turning
  and the downstream Mach number after the flow turns away from
  itself.
- skills/aerodynamics/high-speed/oblique-shock: wave angle from the
  upstream Mach number and flow deflection angle.
- skills/aerodynamics/high-speed/shock-expansion-airfoil: the patched
  oblique-shock and prandtl-meyer solution over a diamond airfoil.
- skills/aerodynamics/high-speed/transonic-similarity: compressibility
  corrections and the critical Mach number estimate.
- skills/aerodynamics/high-speed/hypersonic-flow: modified Newtonian
  impact theory and pitot pressure behind the normal shock.
- skills/propulsion/gas-turbine-cycle/propelling-nozzle: choked or
  unchoked regime from the nozzle pressure ratio and throat sizing in
  the gas-turbine context.
- skills/propulsion/ramjet/ramjet-inlet: diffuser total pressure
  recovery at the flight Mach number from the isentropic limit.
- skills/propulsion/rocket/nozzle-design: exit Mach for a target area
  ratio in the chamber-conditions context.
- skills/cross-cutting/numerics/root-finding: generic scalar root
  solving when a method of choice is required.

## Pitfalls

- Reading one root as the only root: the area-Mach relation inverts to
  two Mach numbers for every A/A* above 1.0 (0.3722 and 2.0 for A/A* =
  1.6875), so always pick the branch: subsonic True for the
  contraction-side low branch and subsonic False for the test section
  high branch.
- Feeding area ratios outside the bracket domain: A/A* below 1.0 is
  below the sonic-throat floor and is not physical; the subsonic
  branch has no root at or above 11.591443867187 (M 0.05) and the
  supersonic branch none above 15377.343750000022 (M 20.0); all three
  raise ValueError instead of returning a silently wrong Mach number.
- Inverting the ratios by hand: p0/p is 7.8244490669 at M = 2.0, so
  the static over total p/p0 is 0.1278; use static_to_total and the
  ratio functions rather than a manual reciprocal to avoid sign and
  exponent mistakes in the rebuild.
- Applying these relations across a shock or a fan: the relations here
  are isentropic only; the stagnation pressure loss across a normal
  shock (normal-shock) and the expansion fan relations (prandtl-meyer)
  are separate mechanisms with separate leaves, and the total pressure
  is not conserved across them.
- Reporting the static state as the total state: at M = 2.0 the test
  section static state is 12949.79 Pa and 160.08 K against chamber
  totals of 101325 Pa and 288.15 K, a factor of 7.82 in pressure; the
  round trip holds only when the same Mach number and the same gas
  constants are used on both legs.
- Treating the choked mass flow as linear in total temperature: mdot
  scales as 1/sqrt(T0), so quadrupling T0 halves the flow (2.4126 to
  1.2063 kg/s at fixed p0 and throat area) and the mass flow parameter
  identity must hold at every point, not just at the anchor.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_isentropic_flow_relations.py

The test covers the step 2 total to static ratio set at the spec Mach
anchors, the step 3 total condition rebuild with the exact round trip,
the step 4 area-Mach relation closed forms and monotone branches, the
step 5 subsonic and supersonic root recovery with the near-sonic
re-brackets and the domain limits, the step 6 choked mass flow with
its p0, throat area and total temperature scalings and the mass flow
parameter identity, plus determinism and ValueError rejection of every
non-physical input class. All 33 methods must pass offline with exit
code 0 before the leaf is committed.

## Compliance

- NACA-TR-824 is referenced, not reproduced: the isentropic relations
  above are standard engineering methodology summarized in this leaf's
  own words (name and paraphrase only), per standards-map.yaml. No
  verbatim tables or sections of the report appear here.
- compliance: STANDARDS-REF, gated: false.
