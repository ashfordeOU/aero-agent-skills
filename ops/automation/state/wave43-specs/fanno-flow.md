# Wave-43 leaf spec: fanno-flow (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/fanno-flow/
- Pack: high-speed (16 leaves present at prep: aerodynamic-heating,
  bow-shock-standoff, compressible-couette-flow, flat-plate-skin-friction-heating,
  hypersonic-flow, isentropic-flow-relations, normal-shock, oblique-shock,
  prandtl-meyer, regular-shock-reflection, shock-expansion-airfoil, shock-tube,
  supercritical-airfoil, swept-wing-aerodynamics, transonic-similarity,
  wave-drag-area-rule; fanno-flow and rayleigh-flow are the two wave-43
  additions). Claim fences (quoted from the sibling frontmatter at prep; none
  owns wall-friction duct flow):
  - isentropic-flow-relations (this pack) is the frictionless complement: its
    description reads "Use when you must convert a Mach number into the
    isentropic total to static ratios of a compressible flow: the total
    temperature, pressure and density ratios of a perfect gas at gamma 1.4,
    rebuild total conditions from a static state and Mach number, recover the
    Mach number that produces a given area ratio from the area-Mach relation on
    the subsonic low branch or the supersonic high branch, and compute the
    choked mass flow a passage passes at its sonic throat from total pressure,
    total temperature and throat area". Its flow is frictionless by claim: no
    wall-friction term, no fL*/D integral, no Fanno line, no friction length,
    and its choking is the geometric throat of the area-Mach relation (area A*
    where M = 1), never a friction-choked duct length.
  - normal-shock (this pack) is the shock-jump reference: "find the downstream
    Mach number, static pressure, density, and temperature ratios across the
    shock, and the stagnation pressure loss from the upstream Mach number". Its
    stagnation loss is the discontinuous jump across a shock at a station; the
    total-pressure decay here is integrated continuously along a duct by wall
    friction, with no shock and no jump relations.
  - shock-tube (this pack) is the accepted deterministic-bisection precedent:
    its description reads "recover the incident-shock Mach number by
    deterministic bisection of the implicit diaphragm-match equation". It is an
    unsteady diaphragm wave system with no duct-friction content; the bisection
    discipline (bracket, tolerance, no RNG) is the pattern reused here.
  - rayleigh-flow (this pack, same-wave sibling; its SKILL.md is in flight at
    prep, so the fence is quoted from the wave-43 leaf plan, entry 11, probe
    #2: "constant-area frictionless duct with heat addition, closed-form
    p/rho/T/p0/M relations, max heat addition to thermal choke"). It is the
    heat-addition line of a FRICTIONLESS duct. The two mechanisms are fenced
    cleanly: this leaf is adiabatic (heat addition exactly zero, T0 constant)
    and rayleigh-flow is frictionless (friction exactly zero); friction WITH
    heat addition is out of scope for both.
  - flat-plate-skin-friction-heating (this pack) owns boundary-layer skin
    friction, drag and heating on a flat plate; the duct-averaged Fanning
    friction factor of a confined channel is a different quantity with no
    boundary-layer profile content.
  Whole-tree greps at prep: "fanno" = 0 hits in skills/ (SKILL.md bodies and
  scripts, grep exit 1) and 0 hits in eval/hit1-corpus.yaml. The wave-43
  collision probe run (ops/automation/state/wave43-recon/corpus-collisions.py
  batch-C, real run) counts for fanno-flow: 'fanno' -> 0, 'fanno line' -> 0,
  'friction duct' -> 0, 'choking length' -> 0. The distinctive tokens
  fanno-flow, fanno-line, friction-duct-choking and fld-star each match 0
  corpus tasks; the only "rayleigh" hit in the corpus is the wave-33
  structures/fem/beam-vibration Rayleigh-quotient task (a different meaning, a
  different family), so neither wave-43 aero duct leaf collides. GENUINE AERO
  gap (fresh probe): no leaf computes wall-friction Fanno duct states, the
  fL*/D Fanno-line integral, a friction choke length or the friction required
  to choke a duct; isentropic-flow-relations is frictionless by claim.
- Standards id: naca-tr-824 (reference-only, present in standards-map.yaml,
  matching every high-speed sibling). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Solve the Fanno-flow problem of a steady adiabatic constant-area duct with
wall friction: evaluate the Fanno-line integral fL*/D = (1 - M^2)/(gamma M^2)
+ ((gamma + 1)/(2 gamma)) ln((gamma + 1) M^2 / (2 + (gamma - 1) M^2)), the
friction parameter (Fanning factor f, hydraulic diameter D) that chokes the
duct from the Mach number M; compute the choking length L* = (D/f) fL*/D from
a given inlet Mach; recover the Mach number at a downstream station for a
given duct friction parameter fL/D by a deterministic 1-D root on the inlet
branch, where the segment consumes fL/D = fL*/D(M1) - fL*/D(M2) of the choke
margin (subsonic branch: friction accelerates the flow, M2 in (M1, 1);
supersonic branch: friction decelerates it, M2 in (1, M1)); compute the
friction factor required to choke a duct of given length and diameter,
f_req = (D/L) fL*/D(M1); and evaluate the total-pressure loss ratio p0/p0* =
(1/M) (2 (1 + (gamma - 1) M^2 / 2)/(gamma + 1))^((gamma + 1)/(2 (gamma - 1)))
with the static ratios to the sonic reference of the same duct T/T* =
(gamma + 1)/(2 + (gamma - 1) M^2), p/p* = (1/M) sqrt((gamma + 1)/(2 + (gamma
- 1) M^2)) and rho/rho* = (1/M) sqrt((2 + (gamma - 1) M^2)/(gamma + 1)), so
the station-to-station ratios across a duct segment, p02/p01 (always below 1,
the friction total-pressure loss), p2/p1, T2/T1 and rho2/rho1, are the
quotients of the starred ratios at the two stations. Produces the fL*/D
values, the choke lengths, the downstream Mach numbers on both branches, the
friction required to choke and the total-pressure and static ratios along the
duct that gate duct and wind-tunnel piping design, friction-choked bleed and
valve line checks and gas-dynamics coursework. Does NOT do: frictionless
isentropic total-to-static ratios, area-Mach inversion or simple choked mass
flow at a geometric throat (isentropic-flow-relations); normal or oblique
shock jump relations at a given upstream Mach number (normal-shock,
oblique-shock); Rayleigh heat-addition flow of a frictionless duct
(rayleigh-flow, same wave; friction with heat addition is out of scope here);
boundary-layer skin friction, drag and heating on surfaces
(flat-plate-skin-friction-heating); the unsteady shock-tube wave system
(shock-tube). Scope: steady adiabatic perfect-gas flow in a constant-area
duct, constant Fanning friction factor, no area change, no heat addition, no
embedded shock and no internally choked duct (fL/D strictly below the choke
value; at fL/D = fL*/D(M1) the exit is exactly sonic and the module raises).
gamma = 1.4 air by default and a parameter elsewhere. Deterministic, pure
stdlib.

## Model (implement exactly)

Pure stdlib, math only. Module constants: GAMMA = 1.4 (air default; gamma is a
parameter of every function), BISECT_TOL = 1e-12 (absolute Mach tolerance of
the deterministic bisection), MAX_ITER = 200 (iteration cap, no RNG,
identical inputs give identical bits). Friction convention, pinned: f is the
Fanning (skin-friction) factor f = tau_w / (rho u^2 / 2); texts and tables
that use the Darcy factor f_D = 4 f tabulate (4 f) L/D, so a caller converting
table values must divide f_D by 4 before calling. D is the hydraulic diameter
(pipe diameter for a circular duct, D = 4A/P generally). The starred state is
the sonic state (M = 1) of the same constant-area adiabatic duct; the duct is
adiabatic so T0 = T0* exactly and T0 stays constant along the duct.

Defining relations (pin these exactly; every function below derives from
them):
- Fanno-line integral (the claim formula): phi(M) = fL*/D = (1 - M^2)/(gamma
  M^2) + ((gamma + 1)/(2 gamma)) ln((gamma + 1) M^2 / (2 + (gamma - 1) M^2)).
  phi has its only zero and minimum at M = 1 (both terms vanish there), it is
  strictly decreasing on the subsonic branch (0, 1), from infinity at M = 0
  down to 0 at M = 1, and strictly increasing on the supersonic branch (1,
  inf), toward the plateau ((gamma + 1)/(2 gamma)) ln((gamma + 1)/(gamma - 1))
  - 1/gamma (0.8215 at gamma 1.4). Derivative identity pinning the
  monotonicity: d(phi)/dM = (2/(gamma M^3)) ((gamma + 1) M^2 / (2 + (gamma -
  1) M^2) - 1), negative below M = 1, zero at M = 1, positive above; the
  residual phi(M2) - target is therefore monotone on each branch and the
  bisection root is unique.
- Segment rule: a duct segment of friction parameter fL/D strictly below
  phi(M1) moves the Mach number toward 1 on the same branch, consuming
  fL/D = phi(M1) - phi(M2) of the choke margin; the margin left to the sonic
  state at the exit is phi(M2) = phi(M1) - fL/D. At fL/D = phi(M1) the exit is
  exactly sonic (the duct is exactly choked); beyond phi(M1) the duct chokes
  internally, which is out of scope and raises.
- Starred total ratio: p0/p0* = (1/M) (2 (1 + (gamma - 1) M^2 / 2)/(gamma +
  1))^((gamma + 1)/(2 (gamma - 1))); equals 1 at M = 1 and grows on both
  branches away from M = 1 (the farther a station is from the sonic state, the
  more friction loss remains). Numeric identity for tests: p0/p0*(M) is the
  reciprocal of the frictionless area-Mach ratio A/A* of the same closed form
  (isentropic-flow-relations owns that relation; the module never computes an
  area ratio, the test may cross-check the closed form only).
- Starred static ratios: T/T* = (gamma + 1)/(2 + (gamma - 1) M^2), p/p* =
  (1/M) sqrt((gamma + 1)/(2 + (gamma - 1) M^2)), rho/rho* = (1/M) sqrt((2 +
  (gamma - 1) M^2)/(gamma + 1)); all 1.0 at M = 1 and mutually consistent with
  p/p* = (rho/rho*)(T/T*) and T0/T0* = 1 (adiabatic).
- Station ratios across a segment (one duct, one sonic reference): p02/p01 =
  (p0/p0*)2/(p0/p0*)1 below 1 on both branches (friction loss), and for X in
  p, T, rho: X2/X1 = (X/X*)2/(X/X*)1. Entropy cross-check of the loss:
  ds/R = -ln(p02/p01) > 0 on both branches; T02/T01 = 1 within float noise.

Functions:
- fanno_function(mach, gamma = GAMMA) -> float: phi = fL*/D by the claim
  closed form above. ValueError if mach <= 0 or gamma <= 1.
- choke_length(mach, friction_factor, diameter, gamma = GAMMA) -> float:
  L* = diameter / friction_factor * phi(mach), metres; the duct length that
  brings the exit exactly to M = 1 (0.0 at mach = 1, already choked).
  ValueError if friction_factor <= 0, diameter <= 0, or the fanno_function
  guard trips.
- downstream_mach(mach_in, fld, gamma = GAMMA) -> float: the downstream Mach
  number on the inlet branch solving phi(M2) = phi(M1) - fld by deterministic
  bisection: subsonic inlet M1 in (0, 1) brackets [M1, 1 - 1e-12], supersonic
  inlet M1 > 1 brackets [1 + 1e-12, M1], converging while the bracket is wider
  than BISECT_TOL up to MAX_ITER, returning the bracket midpoint. At fld = 0
  the root sits on the bracket edge and the bisection returns M1. ValueError
  if mach_in <= 0, mach_in == 1 (a sonic inlet is already choked; there is no
  duct inversion), gamma <= 1, fld < 0, or fld >= phi(mach_in) (the duct
  chokes at or before the exit; use choke_length or friction_to_choke for the
  exactly choked duct).
- friction_to_choke(mach, duct_length, diameter, gamma = GAMMA) -> float:
  f_req = diameter / duct_length * phi(mach), the Fanning factor that makes a
  duct of the given length and diameter exactly choked from the inlet Mach.
  ValueError if duct_length <= 0 or diameter <= 0 (plus the phi guard).
- total_pressure_ratio(mach, gamma = GAMMA) -> float: p0/p0* by the pinned
  closed form. ValueError if mach <= 0 or gamma <= 1.
- static_ratios(mach, gamma = GAMMA) -> dict with keys "T_Tstar", "p_pstar",
  "rho_rhostar" by the pinned closed forms (names and paraphrase only, the
  standard Fanno table columns). ValueError as total_pressure_ratio.
- duct_state(mach_in, fld, gamma = GAMMA) -> dict with keys "mach_out",
  "p02_over_p01", "p2_over_p1", "T2_over_T1", "rho2_over_rho1": runs
  downstream_mach then the quotient identities above. Identical ValueError set
  as downstream_mach.

Identities to test (closed form, deterministic):
- phi(M) table values at gamma 1.4: phi(0.3) = 5.299253105091, phi(0.5) =
  1.069060312718, phi(0.8) = 0.072289972363, phi(0.95) = 0.003278221120,
  phi(1.0) = 0.0, phi(1.2) = 0.033638068346, phi(2.0) = 0.304996502581,
  phi(3.0) = 0.522159408179, phi(5.0) = 0.693803924944, phi(10.0) =
  0.786830832907 (all REAL anchor outputs; textbook Fanno tables agree:
  1.0691 at M = 0.5, 0.3050 at M = 2.0, 0.5222 at M = 3.0).
- Branch monotonicity: phi strictly decreasing on (0, 1) and strictly
  increasing on (1, inf); p0/p0* minimal at M = 1.
- Segment round trip: phi(downstream_mach(M1, fld)) + fld - phi(M1) is zero to
  within 1e-9 (anchor residuals 2.498e-12 subsonic, -8.171e-14 supersonic).
- Zero-friction limit: downstream_mach(M1, 0.0) = M1 within 1e-9 on both
  branches (anchor 0.300000000000 and 2.000000000000).
- Station ratios are quotients of starred ratios by construction; p02/p01 < 1
  and -ln(p02/p01) > 0 on both branches; T02/T01 = 1 within 1e-9 (anchor
  1.000000000000); p/p* = (rho/rho*)(T/T*) within 1e-12.
- Choke-consistency: friction_to_choke(M1, L, D) * L / D = phi(M1), and
  choke_length(M1, f, D) = D * phi(M1) / f; at fL/D = phi(M1) the module
  raises (exit exactly sonic), never returns a fake Mach below the branch
  floor.
- ValueErrors across the module: mach at 0 and negative; mach_in == 1; gamma
  at 1.0; friction_factor, diameter and duct_length at 0 and negative; fld
  negative and at/above phi(M1) (5.3 for M1 = 0.3, 0.3050 for M1 = 2.0).
- Determinism; no imports beyond math; gamma defaults to 1.4 but the gamma
  parameter is honored everywhere (anchor phi(2.0, 1.3) = 0.357277365682).

## Worked example

Representative duct: D = 0.1 m, Fanning f = 0.005, so the friction parameter
gradient is f/D = 0.05 per metre; gamma = 1.4. All values below are REAL
outputs of the prep anchor /tmp/w43spec/anchor_fanno.py (stdlib math,
deterministic bisection, exit 0).

- Fanno-line integral (the choke parameters): fL*/D(0.3) = 5.299253105091 and
  fL*/D(2.0) = 0.304996502581, so a 0.005-friction duct chokes from M = 0.3
  in L* = 105.985062101823 m and from M = 2.0 in L* = 6.099930051630 m: the
  supersonic duct chokes more than seventeen times sooner than the subsonic
  duct at the same friction level (105.985/6.09993 = 17.37).
- Total-pressure and static references: p0/p0* = 2.035065262346 at M = 0.3
  and 1.687500000000 at M = 2.0 (the classic value), 1.000000000000 at M = 1.
  At M = 0.3: T/T* = 1.178781925344, p/p* = 3.619057466836, rho/rho* =
  3.070167084366. At M = 2.0: T/T* = 0.666666666667, p/p* = 0.408248290464,
  rho/rho* = 0.612372435696 (the standard Fanno table row).
- Subsonic branch, M1 = 0.3, duct L = 50 m: fL/D = 0.005 * 50/0.1 = 2.5,
  below the choke value 5.299253105091. Downstream Mach:
  downstream_mach(0.3, 2.5) = 0.375749134774, the subsonic flow accelerated
  toward M = 1; the round-trip residual phi(M2) + fL/D - phi(M1) =
  2.498e-12, and the margin left to sonic is phi(0.3) - 2.5 =
  2.799253105091 = phi(M2). Duct state across the 50 m:
  p02/p01 = 0.822735477531 (17.7% total-pressure loss), p2/p1 =
  0.794420493240, T2/T1 = 0.990043659533, rho2/rho1 = 0.802409555973; the
  static pressure falls most, the static temperature almost stays (adiabatic,
  T02/T01 = 1.000000000000). Station references: p0/p0* = 2.035065262346 at
  the inlet and 1.674320390423 at the exit, ratio 0.822735477531. Entropy
  rise: ds/R = -ln(p02/p01) = 0.195120542447 (> 0). The friction that would
  exactly choke this 50 m duct: friction_to_choke(0.3, 50, 0.1) =
  0.010598506210, about double the actual 0.005, so the duct is not choked;
  zero-friction limit downstream_mach(0.3, 0.0) = 0.300000000000.
- Supersonic branch, M1 = 2.0, duct L = 3 m: fL/D = 0.005 * 3/0.1 = 0.15,
  below the choke value 0.304996502581. Downstream Mach:
  downstream_mach(2.0, 0.15) = 1.552005392004, the supersonic flow decelerated
  toward M = 1; round-trip residual -8.171e-14, margin to sonic
  phi(2.0) - 0.15 = 0.154996502581. Duct state across the 3 m:
  p02/p01 = 0.718851057841 (28.1% total-pressure loss), p2/p1 =
  1.420320685669, T2/T1 = 1.214784619331, rho2/rho1 = 1.169195479649: the
  static pressure, temperature and density all RISE as supersonic flow slows
  toward M = 1, the mirror image of the subsonic branch. Station references:
  p0/p0* = 1.687500000000 at the inlet and 1.213061160106 at the exit, ratio
  0.718851057841. Entropy rise: ds/R = 0.330101094541 (> 0). The friction
  that would exactly choke this 3 m duct: friction_to_choke(2.0, 3, 0.1) =
  0.010166550086, about double the actual 0.005.
- Read-off: friction pulls both branches toward M = 1 and spends total
  pressure doing it (p02/p01 below 1 both ways); a Mach-0.3 duct run must
  stay below fL/D 5.299 to avoid choking, a Mach-2.0 run below fL/D 0.305,
  and a duct above the choke parameter at its inlet is physically
  over-length for that inlet state (module ValueError).
Run your module and take the real outputs as assert targets; the anchors above
are real prep outputs of /tmp/w43spec/anchor_fanno.py (stdlib math,
deterministic bisection, exit 0).

## Validation list (contract test must include)

- fanno_function table: (0.3) = 5.299253105091 within 1e-5, (0.5) =
  1.069060312718 within 1e-5, (0.8) = 0.072289972363 within 1e-6, (1.0) = 0
  within 1e-12, (1.2) = 0.033638068346 within 1e-6, (2.0) = 0.304996502581
  within 1e-5, (3.0) = 0.522159408179 within 1e-5, (10.0) = 0.786830832907
  within 1e-5; textbook table anchors phi(0.5) 1.0691, phi(2.0) 0.3050,
  phi(3.0) 0.5222 reproduced within 1e-4.
- fanno_function(2.0, gamma = 1.3) = 0.357277365682 within 1e-5 (the gamma
  parameter is honored).
- total_pressure_ratio: (0.3) = 2.035065262346 within 1e-5, (0.5) =
  1.339843750000 within 1e-5, (1.0) = 1.000000000000 within 1e-12, (1.5) =
  1.176167052469 within 1e-5, (2.0) = 1.687500000000 within 1e-6, (3.0) =
  4.234567901235 within 1e-5; p0/p0* minimal at M = 1 on both branches.
- static_ratios at M = 0.3: T/T* 1.178781925344, p/p* 3.619057466836,
  rho/rho* 3.070167084366 within 1e-5; at M = 2.0: 0.666666666667,
  0.408248290464, 0.612372435696 within 1e-6; p/p* = (rho/rho*)(T/T*) within
  1e-12 (anchor both sides 2.138089935299 at M = 0.5); all three 1.0 at M = 1.
- choke_length(0.3, 0.005, 0.1) = 105.985062101823 within 1e-3 m and
  choke_length(2.0, 0.005, 0.1) = 6.099930051630 within 1e-4 m; the supersonic
  choke length is the shorter.
- downstream_mach(0.3, 2.5) = 0.375749134774 within 1e-5 (above M1, subsonic
  acceleration); downstream_mach(2.0, 0.15) = 1.552005392004 within 1e-5
  (below M1, supersonic deceleration); round-trip residuals phi(M2) + fL/D -
  phi(M1) below 1e-9 (anchor 2.498e-12 and -8.171e-14); downstream_mach(0.3,
  0.0) = 0.300000000000 within 1e-9 and downstream_mach(2.0, 0.0) =
  2.000000000000 within 1e-9.
- duct_state(0.3, 2.5): p02/p01 = 0.822735477531 within 1e-5, p2/p1 =
  0.794420493240 within 1e-5, T2/T1 = 0.990043659533 within 1e-5, rho2/rho1 =
  0.802409555973 within 1e-5; station p0/p0* 1.674320390423 at M2 within
  1e-5; ds/R = -ln(p02/p01) = 0.195120542447 within 1e-5 (> 0);
  T02/T01 = 1.000000000000 within 1e-9 (adiabatic).
- duct_state(2.0, 0.15): p02/p01 = 0.718851057841 within 1e-5, p2/p1 =
  1.420320685669 within 1e-5, T2/T1 = 1.214784619331 within 1e-5, rho2/rho1 =
  1.169195479649 within 1e-5; station p0/p0* 1.213061160106 at M2 within
  1e-5; ds/R = 0.330101094541 within 1e-5 (> 0). Both branches: p02/p01 < 1;
  the supersonic segment loses more total pressure (0.7189 < 0.8227) from a
  friction parameter sixteen times smaller (0.15 versus 2.5).
- friction_to_choke(0.3, 50, 0.1) = 0.010598506210 within 1e-6 and
  friction_to_choke(2.0, 3, 0.1) = 0.010166550086 within 1e-6; consistency
  friction_to_choke(M1, L, D) * L / D = fanno_function(M1) within 1e-9.
- Branch monotonicity (REAL anchor values): phi falls from 5.299253105091
  (M = 0.3) through 1.069060312718 (0.5) and 0.003278221120 (0.95) to 0 at
  M = 1, then rises through 0.033638068346 (1.2), 0.304996502581 (2.0),
  0.522159408179 (3.0), 0.693803924944 (5.0) and 0.786830832907 (10.0).
- ValueErrors: fanno_function at mach 0 and -0.5 and gamma 1.0;
  choke_length with friction_factor 0 and diameter 0; downstream_mach with
  fld -1.0, fld 5.3 at M1 = 0.3 (at/above the choke value 5.299253105091),
  fld 0.3050 at M1 = 2.0, and mach_in 1.0; friction_to_choke with duct_length
  0; total_pressure_ratio at mach -2.0; static_ratios with gamma 1.0 (the 12
  anchor cases).
- Determinism: two identical runs return identical bits; no imports beyond
  math; no RNG; gamma defaults to 1.4. Contract test file named
  test_fanno_flow.py (underscores), unittest, offline in under 20 seconds.

## Corpus fragment (eval/hit1-wave43-fanno-flow.yaml)

Query 1 (copy verbatim):
  "analyze the fanno-flow of the constant-area adiabatic duct with wall
  friction: from the inlet mach number compute the fanno-line integral
  fL*/D, the friction-duct-choking length and the friction required to
  choke, then recover the downstream mach number for a given duct length on
  the subsonic and the supersonic branch"
  intent: "aerodynamics; Fanno friction-duct states: fL*/D Fanno-line
  integral, friction choke length, branch-preserving downstream Mach
  inversion and friction required to choke"
  expected_skill: "aerodynamics/high-speed/fanno-flow"
Query 2 (copy verbatim):
  "find the total pressure loss p0/p0* and the static pressure, temperature
  and density ratios along a fanno-line duct of given friction parameter,
  with the fld-star margin remaining to the sonic state for subsonic and
  supersonic entry"
  intent: "aerodynamics; total-pressure loss and static ratios to the sonic
  reference along a constant-area adiabatic friction duct"
  expected_skill: "aerodynamics/high-speed/fanno-flow"
Task ids: w43-fanno-flow-1 and -2. Prep grep and probe: "fanno" appears in NO
existing eval/hit1-corpus.yaml task and in NO skills/ file (0 hits both, real
greps); the corpus-collisions.py batch-C run reports 'fanno' 0, 'fanno line'
0, 'friction duct' 0, 'choking length' 0, and the distinctive tokens
fanno-flow, fanno-line, friction-duct-choking and fld-star each match 0 tasks;
the isentropic-flow-relations tasks route on frictionless area-Mach and
choked-mass-flow quantities at a geometric throat, the normal-shock tasks
route on shock jump ratios at a given upstream Mach, and the single corpus
"rayleigh" hit is the beam-vibration Rayleigh-quotient task, so the queries
above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must solve the Fanno flow of a steady
adiabatic constant-area duct with wall friction:" and include the outputs in
the Claim. First tag: fanno-flow. Additional tags ONLY: fanno-line,
friction-duct-choking, fld-star, fanno-choking-length. NEVER single generic
words (mach, friction, duct, choking, flow, adiabatic, pressure,
temperature, gas, dynamics) and NEVER choked-mass-flow, mach-from-area-ratio,
total-to-static-ratio (isentropic-flow-relations), shock-relations,
stagnation-pressure (normal-shock and oblique-shock context), rayleigh,
rayleigh-line, heat-addition-duct, thermal-choking (rayleigh-flow, the
same-wave sibling), skin-friction-heating (flat-plate-skin-friction-heating)
or shock-tube. 50-150 words, <=1000 chars, no em dash, action verb present.
Recommended wording (outputs in Claim order): "Use when you must solve the
Fanno flow of a steady adiabatic constant-area duct with wall friction:
evaluate the fanno-line integral fL*/D that chokes the duct from a Mach
number, compute the friction-duct-choking length from the inlet Mach, recover
the downstream Mach number for a given friction parameter fL/D on the
subsonic or the supersonic branch, find the friction required to choke a duct
of given length, and report the total-pressure loss ratio p0/p0* and the
static pressure, temperature and density ratios to the sonic state along the
duct. Produces the fL*/D values, choke lengths, downstream Mach numbers,
friction to choke and the loss ratios that gate duct sizing and
gas-dynamics coursework. Trigger: fanno flow, fanno line, friction duct,
choking length, adiabatic duct friction, fL*/D." The sibling
triggers "area ratio", "choked mass flow", "sonic throat", "normal shock" and
"heat addition" must not appear.
