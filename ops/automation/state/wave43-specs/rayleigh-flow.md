# Wave-43 leaf spec: rayleigh-flow (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/rayleigh-flow/
- Pack: high-speed (verified present at prep with aerodynamic-heating,
  bow-shock-standoff, compressible-couette-flow, flat-plate-skin-friction-
  heating, hypersonic-flow, isentropic-flow-relations, normal-shock,
  oblique-shock, prandtl-meyer, regular-shock-reflection, shock-expansion-
  airfoil, shock-tube, supercritical-airfoil, swept-wing-aerodynamics,
  transonic-similarity, wave-drag-area-rule; the same-wave sibling
  fanno-flow is planned but NOT on disk at spec time).
- Claim fences (quoted from the sibling frontmatter at prep, none owns
  the constant-area frictionless heat-addition duct):
  - isentropic-flow-relations (this pack) is the frictionless ADIABATIC
    complement: its description reads "Use when you must convert a Mach
    number into the isentropic total to static ratios of a compressible
    flow: the total temperature, pressure and density ratios of a perfect
    gas at gamma 1.4, rebuild total conditions from a static state and
    Mach number, recover the Mach number that produces a given area
    ratio from the area-Mach relation on the subsonic low branch or the
    supersonic high branch, and compute the choked mass flow a passage
    passes at its sonic throat from total pressure, total temperature
    and throat area", and its quick reference pins the adiabatic
    conversions T0/T = 1 + 0.2 M^2, p0/p = (T0/T)^3.5, the area-Mach
    roots and the mass flow parameter MFP = 0.0404184199. There q is
    always zero: the total temperature is FROZEN across their duct and
    their sonic state is the isentropic throat A*. The new leaf adds
    heat, so total temperature CHANGES (T0_2 = T0_1 + q/cp) and the
    sonic state is the thermal-choking state of the same-mass-flow
    frictionless duct, a different star. Their tags total-to-static-
    ratio, mach-from-area-ratio and choked-mass-flow must not be reused.
  - fanno-flow (planned same-wave sibling, AERO 46 in the wave-43 leaf
    plan, lines 50-54: "constant-area adiabatic duct with friction,
    Fanno line integral fL*/D closed form, choking length, invert L to
    M by 1-D root"): its directory does not exist at prep (grep "fanno"
    = 0 hits in skills/ md and py), so no frontmatter can be quoted.
    The fence is physical and fixed by the probe pair: Fanno flow adds
    WALL FRICTION at constant area with zero heat transfer; Rayleigh
    flow adds HEAT at constant area with zero friction. The two are the
    complementary non-isentropic constant-area duct mechanisms of the
    wave. The new leaf must not claim friction, fanno-line, friction-
    duct, choking-length or any wall-friction quantity.
  - combustor-design (propulsion/gas-turbine-cycle) owns burner
    thermochemistry: its description reads "Use when the task is
    combustor sizing, burner fuel-air ratio, flame temperature, or heat
    release for a gas turbine engine. Compute the gas turbine combustor
    design point: the stoichiometric fuel-air-ratio from the fuel carbon
    and hydrogen mass fractions, the operating fuel-air-ratio from the
    fuel and air flows, the equivalence ratio, the combustion
    efficiency, the heat release from the fuel flow and lower heating
    value, and the temperature rise across the combustor with the
    adiabatic flame temperature estimate from a constant-specific-heat
    energy balance". Its q comes from fuel chemistry and component
    energy balance; the new leaf takes q as a prescribed external heat
    addition per unit mass of duct flow and never computes fuel flows,
    fuel-air ratio, flame temperature, combustion efficiency or burner
    sizing. Their tokens (fuel-air-ratio, adiabatic-flame-temperature,
    heat-release, equivalence-ratio) are forbidden here.
  - hypersonic-flow (this pack) owns the Rayleigh PITOT relation: its
    description reads "...stagnation pressure behind the normal shock
    (Rayleigh pitot relation)..." and its quick reference pins "Rayleigh
    pitot relation: p02/p1 = ((gamma+1)^2 * M^2 / (4*gamma*M^2 -
    2*(gamma-1)))^(gamma/(gamma-1)) * (2*gamma*M^2 - gamma + 1) /
    (gamma+1)". That is stagnation pressure recovery across a bow or
    normal shock at hypersonic speed, a shock relation, NOT Rayleigh
    flow; the tokens rayleigh-pitot and pitot must not appear in the
    queries, the description or the tags of the new leaf.
  - normal-shock, oblique-shock and shock-expansion-airfoil (this pack)
    own shock relations: the frictionless constant-area duct model
    contains no shocks and its entropy rise is purely thermal, so no
    shock or expansion-fan quantity is claimed.
- Whole-tree greps at prep (REAL outputs, this repo state):
  - ops/automation/state/wave43-recon/corpus-collisions.py batch-C:
    rayleigh-flow tokens "rayleigh flow" -> 0, "heat addition duct" ->
    0, "thermal choking" -> 0, "rayleigh line" -> 0 in
    eval/hit1-corpus.yaml; fanno-flow tokens all 0.
  - grep -rin "rayleigh" eval/hit1-corpus.yaml: exactly 2 lines (one
    task at lines 4185-4186), the structures Rayleigh-quotient
    fundamental-frequency task; no pitot or flow task lines. The
    leaf-plan statement "all 16 rayleigh hits are Rayleigh-pitot/
    Rayleigh-Ritz noise" is confirmed in kind: every rayleigh token in
    the repo is pitot noise (hypersonic-flow SKILL.md 9 lines,
    aerodynamic-heating SKILL.md 1 line, plus their scripts) or
    quotient/Ritz vibration noise (beam-vibration, eigenvalue-
    decomposition, random-vibration-fatigue, plus index routing lines
    in cross-cutting/SKILL.md and structures/SKILL.md). Zero rayleigh
    tokens carry a heat-addition-duct context.
  - grep -rinE "rayleigh.?flow|rayleigh.?line|thermal.?choking|heat
    addition duct" skills/ (md and py, minus pycache): 0 hits.
  - grep -rin "heat addition|thermal chok" eval/*.yaml: 0 hits.
  - GENUINE AERO gap (fresh probe #2 of the wave-43 leaf plan): no leaf
    owns the closed-form constant-area frictionless duct with heat
    addition, its thermal choking limit, or the Rayleigh-line station
    relations; the wave-41 isentropic leaf handles the same geometry
    WITHOUT heat, and the planned fanno leaf handles it WITH friction.
- Standards id: naca-tr-824 (reference-only, present in
  standards-map.yaml). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Steady constant-area frictionless duct flow of a perfect gas with heat
addition (or rejection) per unit mass q, the Rayleigh flow that closes
the pair with the Fanno friction duct: from the inlet Mach number
compute the closed-form Rayleigh-line station relations against the
sonic state the duct reaches at thermal choking, T/T* =
M^2(1+gamma)^2/(1+gamma M^2)^2, p/p* = (1+gamma)/(1+gamma M^2),
rho/rho* = (1+gamma M^2)/((1+gamma) M^2), and the total ratios
T0/T0* = (T/T*) (1 + (gamma-1) M^2/2) 2/(gamma+1) and p0/p0* =
(p/p*) ((1 + (gamma-1) M^2/2) 2/(gamma+1))^(gamma/(gamma-1)), all
equal to 1 at M = 1. Determine the maximum heat addition before
thermal choking from the single closed form q_max = cp*T1*(1 -
M1^2)^2/(2*(gamma+1)*M1^2) = cp*(T0* - T0_1), valid on both branches
and symmetric under M1 to 1/M1 at equal static temperature, vanishing
at M1 = 1: on the subsonic branch heat addition accelerates the flow
toward M = 1 and on the supersonic branch it decelerates the flow
toward M = 1, both branches pinching to M2 = 1 exactly at q = q_max,
where the flow is thermally choked and further addition has no steady
solution. Recover the exit Mach number after a given heat addition
from the quadratic-in-M^2 balance T0/T0*(M2) = T0/T0*(M1) * (1 +
q/(cp*T0_1)) on the inlet's own branch (smaller positive root for a
subsonic inlet, larger positive root for a supersonic inlet, whose
branch floor (gamma^2 - 1)/gamma^2 bounds the allowable heat
rejection), and report the entropy rise of the heat addition from the
second law, ds = cp*ln(T2/T1) - R*ln(p2/p1) J/(kg K), equivalently
ds/cp = ln(T2/T1) - ((gamma-1)/gamma)*ln(p2/p1), which on the T-s
plane is the Rayleigh curve form (s - s*)/cp = ln(T/T*) -
((gamma-1)/gamma)*ln(p/p*) whose maximum value 0 sits at the sonic
point M = 1. Heat addition always raises the stagnation temperature,
T0_2/T0_1 = 1 + q/(cp*T0_1), and always lowers the stagnation
pressure, p0_2/p0_1 = p0/p0*(M2) / p0/p0*(M1) below 1 (0.8976 at
thermal choke from a Mach 0.5 inlet), with static temperature rising
only up to M = 1/sqrt(gamma), where T/T* peaks at (1+gamma)^2/(4
gamma) = 36/35 at gamma 1.4; heat rejection
reverses the Mach drift and the entropy change, cooling a subsonic
flow toward M = 0 and a supersonic flow toward unbounded Mach at the
finite rejection floor. Produces the five station ratios at any Mach,
the thermal-choking heat addition per kilogram with its branch
duality, the exit Mach number, downstream static and stagnation state,
and the entropy rise, in SI units, that gate the heat-addition duct
assessment. Does NOT do: wall friction, fanno-line or choking-length
quantities (fanno-flow, same-wave sibling); isentropic total-to-static
conversions, the area-Mach relation or the choked mass flow of an
isentropic throat (isentropic-flow-relations); fuel-air ratio, flame
temperature, heat release or combustor sizing (combustor-design);
stagnation pressure behind a shock or any shock, pitot or expansion
relation (hypersonic-flow, normal-shock, oblique-shock,
shock-expansion-airfoil). Air at gamma = 1.4, R = 287.0, constant cp
only; variable specific heat, real-gas effects, area change,
friction, mass addition or unsteady flow are out of scope.

## Model (implement exactly)

Pure stdlib, math only, closed form (quadratic root on each branch, no
iteration). Module constants: GAMMA = 1.4 (air), R = 287.0, and CP =
GAMMA * R / (GAMMA - 1) = 1004.5 J/(kg K) DERIVED from gamma and R
(not an independent constant), so the second-law identity ds = cp*ln
- R*ln and the heat balance q = cp*(T0_2 - T0_1) close consistently.

Defining relations (pin these exactly; every function below derives
from them), with the star denoting the state of the same-mass-flow
constant-area frictionless duct at M = 1, i.e. thermal choking, and
f = 1 + gamma*M^2:
- T/T* = M^2 (1+gamma)^2 / f^2 (static temperature ratio, peak
  (1+gamma)^2/(4 gamma) = 36/35 at M = 1/sqrt(gamma)).
- p/p* = (1+gamma) / f; rho/rho* = f / (M^2 (1+gamma)); the three are
  linked by rho/rho* = (p/p*)/(T/T*) exactly.
- T0/T0* = (T/T*) (1 + (gamma-1) M^2/2) / ((gamma+1)/2); p0/p0* =
  (p/p*) ((1 + (gamma-1) M^2/2) / ((gamma+1)/2))^(gamma/(gamma-1)).
  All five ratios equal 1 at M = 1.
- Heat balance: T0_2 = T0_1 + q/cp, so T0_2/T0_1 = 1 + q/(cp*T0_1).
- Thermal-choking heat addition, from T0* = T0_1 / (T0_1/T0*):
  q_max = cp*(T0* - T0_1) = cp*T1*(1 - M1^2)^2/(2*(gamma+1)*M1^2),
  the static-temperature closed form. Because the expression depends on
  M1^2 only through (1 - M^2)^2/M^2, q_max(M1) = q_max(1/M1) exactly:
  a Mach 0.5 inlet and a Mach 2.0 inlet at the same static T1 choke on
  the same heat per kilogram.
- Exit Mach from heat addition: with g(M) = T0/T0*(M) and g2 = g(M1) *
  (1 + q/(cp*T0_1)), the balance g(M2) = g2 is a quadratic in
  x = M2^2, (gamma^2 - 1 - g2*gamma^2)*x^2 + (2*(1+gamma) - 2*g2*gamma)
  *x - g2 = 0, solved by the quadratic formula. Subsonic inlet (M1 <
  1): smaller positive root, M2 in (0, 1]; supersonic inlet (M1 > 1):
  larger positive root, M2 in [1, infinity), which exists only for g2
  above the branch floor (gamma^2 - 1)/gamma^2 (the g2 value reached
  asymptotically as M goes to infinity); rejection past the floor has
  no steady supersonic Rayleigh state and raises.
- Entropy: ds = cp*ln(T2/T1) - R*ln(p2/p1); ds/cp = ln(T2/T1) -
  ((gamma-1)/gamma)*ln(p2/p1); Rayleigh T-s curve form (s - s*)/cp =
  ln(T/T*) - ((gamma-1)/gamma)*ln(p/p*), strictly negative off M = 1,
  zero at M = 1 (the sonic point is the entropy maximum of the
  Rayleigh line), and ds/cp between two stations of one duct equals
  the curve-offset difference at their Mach numbers.

Functions (pure stdlib, math only; gamma, r, cp default to the module
constants):
- rayleigh_ratios(mach, gamma = GAMMA) -> dict with keys
  t_over_tstar, p_over_pstar, rho_over_rhostar, t0_over_t0star,
  p0_over_p0star from the five closed forms above. ValueError if mach
  <= 0.
- heat_addition_maximum(t_static, mach, gamma = GAMMA, cp = CP) ->
  float q_max in J/kg from cp*t_static*(1 - mach^2)^2/(2*(gamma+1)*
  mach^2). Zero at mach = 1; symmetric under mach to 1/mach. ValueError
  if t_static <= 0 or mach <= 0.
- exit_mach(t_static, mach, q, gamma = GAMMA, cp = CP) -> float exit
  Mach number after heat addition q in J/kg (positive heats, negative
  rejects). q at or above q_max*(1 - 1e-12) returns 1.0 (thermally
  choked); q strictly above q_max raises ValueError with the message
  containing "thermal choking limit". Subsonic inlet: q down to just
  above -cp*T0_1 is accepted (exit M tends to 0); q <= -cp*T0_1 raises.
  Supersonic inlet: q below the rejection floor (g2 <= (gamma^2 -
  1)/gamma^2) raises ValueError with the message containing "branch
  limit"; mach == 1 with nonzero q raises (already choked). ValueError
  if t_static <= 0 or mach <= 0.
- heat_addition(t_static, p_static, mach, q, gamma = GAMMA, r = R,
  cp = CP) -> dict of the full downstream station: m2, t2, p2, rho2,
  t02, p02 (absolute SI values) and the ratios t2_over_t1,
  p2_over_p1, rho2_over_rho1, t02_over_t01 = 1 + q/(cp*t0_1),
  p02_over_p01, ds (J/(kg K)), ds_over_cp, choked (True when m2 = 1).
  ValueError as exit_mach, plus ValueError if p_static <= 0.
- entropy_rise(t1, p1, t2, p2, gamma = GAMMA, r = R, cp = CP) -> float
  ds = cp*ln(t2/t1) - r*ln(p2/p1) in J/(kg K). ValueError if any
  argument is <= 0.
- rayleigh_curve_offset(mach, gamma = GAMMA) -> float (s - s*)/cp =
  ln(T/T*) - ((gamma-1)/gamma)*ln(p/p*) at the Mach number, <= 0 with
  maximum 0 at mach = 1. ValueError if mach <= 0.

Identities to test (tolerance-based; no exact-float equality):
- Published gamma-1.4 table agreement: at M = 0.5 the ratios equal
  64/81, 16/9, 9/4, 56/81 and 1.11405250318 within 1e-12 (1e-9 for
  p0/p0*); at M = 2.0 they equal 64/121, 4/11, 11/16, 96/121 and
  1.50309597853 within the same tolerances.
- All five ratios return 1 at M = 1 within 1e-12; the density
  roundtrip rho/rho* == (p/p*)/(T/T*) holds within 1e-12 at M = 0.5
  and M = 2.
- q_max duality: heat_addition_maximum(300, 0.5) ==
  heat_addition_maximum(300, 2.0) = 141257.8125 within 1e-12 relative;
  q_max/(cp*T1) = 0.46875; q_max == cp*(T0* - T0_1) within 1e-12 with
  T0* = 455.625 K for the M = 0.5 case; heat_addition_maximum(300, 1)
  is 0 within 1e-15.
- Thermal choke: exit_mach(300, 0.5, 141257.8125) = 1.0 within 1e-9;
  heat_addition at q_max returns choked True and p02_over_p01 =
  1/p0_over_p0star(0.5) = 0.897623762925 within 1e-12; q = 1.01*q_max
  raises.
- Subsonic half-choke example (q = q_max/2 = 70628.90625): m2 =
  0.625879453912, ds = 214.987084722, all within 1e-9 relative of the
  real anchor outputs; p02/p01 = 0.957052789099 < 1; ds/cp =
  0.214023976827 equals the curve-offset difference
  offset(0.625879453912) - offset(0.5) within 1e-12; ds equals
  cp*ln(T2/T1) - R*ln(p2/p1) within 1e-9.
- Supersonic half-choke example (M1 = 2, same q): m2 =
  1.54998945381 in (1, 2), ds = 200.481131945, p02/p01 =
  0.763277518128 < 1, all within 1e-9 relative of the anchor outputs.
- Rejection: q = -50000 at M1 = 0.5 gives m2 = 0.430803500026 < 0.5
  and ds < 0 (ds/cp = -0.17940496639); q = -200000 at M1 = 2.0 gives
  m2 = 12.5126628564 > 2; q = -250000 at M1 = 2.0 raises the
  supersonic branch-limit ValueError; q = -cp*315 at M1 = 0.5 raises.
- Curve shape: rayleigh_curve_offset(m) < 0 at M = 0.05, 0.2, 0.5,
  0.8451542547285166, 1.5, 2.0, 5.0 and equals 0 within 1e-12 at
  M = 1; t_over_tstar peaks at 1.02857142857 (36/35) at
  M = 1/sqrt(gamma) within 1e-12.
- ValueErrors across the module: mach at 0 and -0.5 on
  rayleigh_ratios; t_static at 0 and -300 and mach at 0 on
  heat_addition_maximum; q at 1.01*q_max, q at -cp*T0_1 and q at
  -250000 (M1 = 2) on exit_mach; mach = 1 with nonzero q; entropy_rise
  with t1 = 0 and with p1 = -1; rayleigh_curve_offset at 0;
  heat_addition with p_static = 0 (13 rejections exercised in the
  anchor).
- Determinism; no imports beyond math; gamma fixed at 1.4 by default;
  dict keys exactly as pinned above.

## Worked example

Air at gamma = 1.4, R = 287.0, cp = 1004.5 J/(kg K). Duct inlet at
T1 = 300 K and p1 = 101325 Pa, run at the dual inlet pair M1 = 0.5
(subsonic branch) and M1 = 2.0 (supersonic branch). All values below
are REAL outputs of the prep anchor /tmp/w43spec/anchor_rayleigh.py
(stdlib math, closed form, exit 0).

- Station ratios at the inlet (rayleigh_ratios):
  - M1 = 0.5: T/T* = 0.790123456790, p/p* = 1.777777777778, rho/rho*
    = 2.25, T0/T0* = 0.691358024691, p0/p0* = 1.11405250318.
    T0_1 = 315.000 K; T0* = T0_1/(T0_1/T0*) = 455.625 K.
  - M1 = 2.0: T/T* = 0.528925619835, p/p* = 0.363636363636, rho/rho*
    = 0.6875, T0/T0* = 0.793388429752, p0/p0* = 1.50309597853.
    T0_1 = 540.000 K; T0* = 680.625 K.
- Maximum heat addition (thermal choking): q_max =
  heat_addition_maximum(300, 0.5) = heat_addition_maximum(300, 2.0) =
  141257.8125 J/kg in BOTH cases: q_max/(cp*T1) = 0.46875, the
  M to 1/M duality, so 141.3 kJ/kg of heat chokes either duct; the
  q_max == cp*(T0* - T0_1) equivalence reads cp*(455.625 - 315) =
  cp*(680.625 - 540) = cp*140.625 J/kg. q_max falls to 0 at M1 = 1.
- Subsonic inlet M1 = 0.5, heat addition q = q_max/2 = 70628.90625
  J/kg (half the choking heat):
  - heat_addition(300, 101325, 0.5, q): exit M2 = 0.625879453912
    (heating accelerates the subsonic flow toward 1); exit station
    ratios at M2: T/T* = 0.941085457548, p/p* = 1.54997194092,
    rho/rho* = 1.64700445479, T0/T0* = 0.845679012346, p0/p0* =
    1.06620705537.
  - Exit state: T2 = 357.318 K (T2/T1 = 1.19106128221), p2 =
    88341.135 Pa (p2/p1 = 0.871859216769), rho2/rho1 =
    0.732001979908, T0_2/T0_1 = 1.22321428571, p0_2/p0_1 =
    0.957052789099: the stagnation pressure FALLS 4.3% while the
    stagnation temperature rises 22.3%.
  - Entropy rise: ds = 214.987 J/(kg K), ds/cp = 0.214023976827,
    ds/R = 0.749083918894; ds/cp equals offset(M2) - offset(M1), the
    Rayleigh T-s curve climb toward the M = 1 maximum.
  - At q = q_max the exit reaches M2 = 1 exactly and
    p0_2/p0_1 = 0.897623762925 = 1/1.11405250318, the minimum
    stagnation pressure ratio the heating duct can deliver.
- Supersonic inlet M1 = 2.0, same q = 70628.90625 J/kg (half the same
  choking heat):
  - heat_addition(300, 101325, 2.0, q): exit M2 = 1.54998945381
    (heating decelerates the supersonic flow toward 1); exit station
    ratios at M2: T/T* = 0.72680703152, p/p* = 0.550022957427,
    rho/rho* = 0.756766147786, T0/T0* = 0.896694214876, p0/p0* =
    1.147279368.
  - Exit state: T2 = 412.236 K (T2/T1 = 1.37411954397), p2 =
    153260.459 Pa (p2/p1 = 1.51256313292), rho2/rho1 = 1.10075076042,
    T0_2/T0_1 = 1.13020833333, p0_2/p0_1 = 0.763277518128: the same
    heat per kilogram costs 23.7% of the stagnation pressure.
  - Entropy rise: ds = 200.481 J/(kg K), ds/cp = 0.199583008408.
- Heat rejection (cooling): q = -50000 J/kg at M1 = 0.5 drives the
  exit to M2 = 0.430803500026 (< 0.5, subsonic cooling decelerates)
  with ds/cp = -0.17940496639 (< 0, rejection lowers entropy);
  q = -200000 J/kg at M1 = 2.0 accelerates the exit to M2 =
  12.5126628564, and rejection past the supersonic branch floor
  (roughly -207.6 kJ/kg for this case, where the exit would reach
  infinite Mach) has no steady Rayleigh state and raises.
- Read-off: adding 70.6 kJ/kg to the Mach 0.5 duct accelerates it to
  M 0.626 with a 4.3% stagnation pressure loss and ds = 215 J/(kg K);
  the identical heat input to the Mach 2 duct decelerates it to
  M 1.55 with a 23.7% loss and ds = 200 J/(kg K); 141.3 kJ/kg chokes
  either duct at M2 = 1.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w43spec/anchor_rayleigh.py
(stdlib math, closed form, exit 0).

## Validation list (contract test must include)

- rayleigh_ratios(0.5): t_over_tstar 0.790123456790, p_over_pstar
  1.777777777778, rho_over_rhostar 2.25, t0_over_t0star
  0.691358024691 within 1e-12; p0_over_p0star 1.11405250318 within
  1e-9. rayleigh_ratios(2.0): 0.528925619835, 0.363636363636, 0.6875,
  0.793388429752 within 1e-12; p0_over_p0star 1.50309597853 within
  1e-9. All five ratios within 1e-12 of 1 at mach = 1; density
  roundtrip rho/rho* == (p/p*)/(T/T*) within 1e-12.
- heat_addition_maximum(300.0, 0.5) = 141257.8125 J/kg within 1e-9;
  equal to heat_addition_maximum(300.0, 2.0) within 1e-12 relative
  (duality); equals cp*(T0* - T0_1) within 1e-12; 0 within 1e-15 at
  mach = 1.
- exit_mach(300.0, 0.5, 70628.90625) = 0.625879453912 within 1e-9;
  exit_mach(300.0, 2.0, 70628.90625) = 1.54998945381 within 1e-9;
  exit_mach(300.0, 0.5, 141257.8125) = 1.0 within 1e-9 (assert with
  the module q_max, not the rounded literal).
- heat_addition(300.0, 101325.0, 0.5, 70628.90625): t2 357.318384663
  within 1e-6, p2 88341.1351391 within 1e-3, p02/p01 0.957052789099
  within 1e-9, t2_over_t1 1.19106128221 within 1e-9, p2_over_p1
  0.871859216769 within 1e-9, rho2_over_rho1 0.732001979908 within
  1e-9, t02_over_t01 1.22321428571 within 1e-9, ds 214.987084722
  within 1e-6, ds/cp 0.214023976827 within 1e-9, choked False.
- heat_addition at q_max (module value): m2 = 1.0, choked True,
  p02/p01 = 0.897623762925 within 1e-9, equal to 1/
  rayleigh_ratios(0.5)["p0_over_p0star"] within 1e-12.
- Supersonic example heat_addition(300.0, 101325.0, 2.0, 70628.90625):
  t2 412.23586319 within 1e-6, p2 153260.459443 within 1e-3, p2/p1
  1.51256313292 within 1e-9, t2_over_t1 1.37411954397 within 1e-9,
  p02/p01 0.763277518128 within 1e-9, ds 200.481131945 within 1e-6;
  exit station ratios p0_over_p0star 1.147279368 and t_over_tstar
  0.72680703152 within 1e-9.
- Entropy identity: ds equals cp*ln(t2_over_t1) - R*ln(p2_over_p1)
  within 1e-9 and ds/cp equals rayleigh_curve_offset(m2) -
  rayleigh_curve_offset(0.5) within 1e-12; rayleigh_curve_offset(m) <
  0 at m = 0.05, 0.2, 0.5, 0.8451542547285166, 1.5, 2.0, 5.0 and
  equals 0 within 1e-12 at m = 1; t_over_tstar at 1/sqrt(gamma) =
  1.02857142857 within 1e-12.
- Rejection: exit_mach(300.0, 0.5, -50000.0) = 0.430803500026 within
  1e-9; exit_mach(300.0, 2.0, -200000.0) = 12.5126628564 within 1e-6;
  ds < 0 for the rejection case.
- ValueErrors: rayleigh_ratios at 0 and -0.5; heat_addition_maximum at
  t 0, t -300 and mach 0; exit_mach q at 1.01*q_max (message contains
  "thermal choking limit"), q at -cp*315.0, q at -250000.0 with
  mach 2.0 (message contains "branch limit"), and mach 1 with q 1000;
  entropy_rise with t1 0 and p1 -1; rayleigh_curve_offset at 0;
  heat_addition with p_static 0.
- Determinism: two identical heat_addition calls return identical
  dicts; no imports beyond math; gamma default 1.4; dict keys exactly
  as pinned in the model.

## Corpus fragment (eval/hit1-wave43-rayleigh-flow.yaml)

Query 1 (copy verbatim):
  "compute the rayleigh-flow state change of air heated in a
  constant-area frictionless duct: the rayleigh-line static and total
  pressure and temperature ratios at the inlet Mach number, and the
  exit Mach and stagnation pressure ratio after a given heat addition
  per kilogram"
  intent: "aerodynamics; the closed-form Rayleigh-line station ratios
  of a constant-area frictionless heat-addition duct and the exit Mach
  and stagnation pressure change after a specified heat addition"
  expected_skill: "aerodynamics/high-speed/rayleigh-flow"
Query 2 (copy verbatim):
  "find the maximum heat addition that thermally chokes a
  constant-area heat-addition duct from a subsonic or supersonic inlet
  Mach number and the entropy rise of the heated flow"
  intent: "aerodynamics; the thermal-choking heat addition q_max of a
  Rayleigh flow duct from either inlet branch and the second-law
  entropy rise of the heat addition"
  expected_skill: "aerodynamics/high-speed/rayleigh-flow"
Task ids: w43-rayleigh-flow-1 and -2. Prep collision evidence (REAL
runs at spec time): ops/automation/state/wave43-recon/corpus-
collisions.py batch-C returns 0 for "rayleigh flow", "heat addition
duct", "thermal choking" and "rayleigh line" in eval/hit1-corpus.yaml;
grep for those tokens across eval/*.yaml returns 0 hits; the only
rayleigh tokens in eval/hit1-corpus.yaml are lines 4185-4186, one
structures Rayleigh-quotient beam-frequency task, and every repo
skill-tree rayleigh token is Rayleigh-pitot (hypersonic-flow,
aerodynamic-heating) or Rayleigh-quotient/Ritz (beam-vibration,
eigenvalue-decomposition, random-vibration-fatigue) noise, so the
queries above are collision-free. The queries deliberately carry no
pitot token, so they cannot route to the hypersonic-flow rayleigh-
pitot tasks, and no fanno or friction token, which the same-wave
fanno-flow sibling owns.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the rayleigh-flow
state change of a perfect gas heated or cooled in a constant-area
frictionless duct:" and include the outputs in the Claim. First tag:
rayleigh-flow. Additional tags ONLY: heat-addition-duct,
thermal-choking, rayleigh-line. NEVER single generic words (flow,
duct, heat, mach, temperature, pressure, entropy, choking, ratio,
sonic) and NEVER the sibling-owned tags total-to-static-ratio,
mach-from-area-ratio, choked-mass-flow (isentropic-flow-relations),
rayleigh-pitot or any pitot token (hypersonic-flow), fuel-air-ratio,
adiabatic-flame-temperature, heat-release (combustor-design), or any
fanno/friction token (fanno-flow). 50-150 words, <=1000 chars, no em
dash, no content-policy sweep term (the banned word from the builder
kit), action verb present. Recommended wording (outputs in Claim
order): "Use when you must compute the rayleigh-flow state change of a
perfect gas heated or cooled in a constant-area frictionless duct:
convert the inlet Mach number into the Rayleigh-line ratios against
the sonic state T/T*, p/p*, rho/rho*, T0/T0*, p0/p0*; find the
maximum heat addition that thermally chokes the duct from a subsonic
or supersonic inlet Mach number, q_max = cp*T1*(1 - M^2)^2/(2*
(gamma+1)*M^2); recover the exit Mach number after a given heat
addition per unit mass on the inlet branch; and report the entropy
rise from the second law. Produces the station ratio set, the choking
heat addition, the exit Mach and stagnation pressure ratio, and the
entropy rise, in SI units, that gate the heat-addition duct
assessment. Trigger: heat addition duct, thermal choking, rayleigh
flow, rayleigh line, constant area frictionless duct." The words
fanno, pitot, shock, isentropic, combustor,
flame, fuel, friction-duct and wall-friction must not appear in the
description ("frictionless duct" is the mandated geometry descriptor,
allowed).
