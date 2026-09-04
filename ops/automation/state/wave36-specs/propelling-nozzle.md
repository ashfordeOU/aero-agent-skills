# Wave-36 leaf spec: propelling-nozzle (propulsion, gas-turbine-cycle pack)

- Path: skills/propulsion/gas-turbine-cycle/propelling-nozzle/
- Pack: gas-turbine-cycle. Closest siblings: gas-turbine-cycle,
  regenerative-cycle, real-cycle-effects, combustor-design,
  afterburner-cycle (computes only the fully-expanded ideal exit
  velocity; its own docs state no pressure thrust term), turbofan-cycle
  (takes vj as an INPUT), engine-airframe-integration (defers nozzle
  work to nozzle-design), propulsion/rocket/nozzle-design (ROCKET
  nozzle: chamber-anchored combustion products, always choked; not the
  air-breathing convergent jet nozzle). Whole-tree grep: choked
  convergent-nozzle math exists only in ROCKET leaves (nozzle-design,
  cold-gas-thruster, solid/hybrid motors) and ramjet-inlet
  (supersonic-starting, unrelated); no leaf sizes an air-breathing jet
  nozzle area or checks the choked regime for it. ZERO owners for the
  gas-turbine propelling nozzle.
- Standards id: far-33 (pack convention; reference-only). Ledger
  Standard: far-33.
- Family: propulsion

## Claim

Size the convergent propelling nozzle of an air-breathing gas turbine
at the conceptual level: decide the choked or unchoked regime from the
nozzle pressure ratio against the critical ratio, size the throat area
from the design mass flow and total conditions under the choked
relation, and for the choked case return the exit total-to-static
conditions, exit velocity and gross thrust including the pressure term;
for an unchoked off-design case return the exit Mach number and the
actual mass flow the same throat passes. Produces the regime flag, the
throat area, exit velocity, exit static pressure, gross thrust (choked)
or exit Mach and actual mass flow (unchoked), and the expansion verdict
(fully expanded / pressure term active).

Does NOT do: rocket nozzle contour, expansion-ratio iteration and
combustion-product gas properties (rocket nozzle-design); afterburner
duct energy balance and fully-expanded velocity only (afterburner-cycle);
supersonic inlet starting (ramjet-inlet); turbine NGV flow (free-turbine).

## Model (implement exactly)

Module constants:
- GAMMA = 1.33 (air-breathing nozzle products convention, matching
  afterburner-cycle's anchor).
- R_GAS = 287.0 (J/kg K).
- P_AMB_DEFAULT = 101325.0 (Pa, sea level standard).

Conventions: total conditions P0 (Pa), T0 (K); mass flow mdot (kg/s);
ambient Pa (Pa). NPR = P0/Pa. Critical ratio = ((gamma+1)/2)^(gamma/
(gamma-1)); choked when NPR >= critical. Choked mass flow per unit
throat area: mdot = P0 At / sqrt(T0) * sqrt(gamma/R) * (2/(gamma+1))^
((gamma+1)/(2(gamma-1))). Exit at throat for a convergent nozzle
(Me = 1 when choked). Gross thrust Fg = mdot*Ve + (Pe-Pa)*At.

Functions (pure stdlib):
- nozzle_regime(p0_pa, p_amb_pa) -> dict {npr, critical_ratio, choked}.
  ValueErrors: p0 <= 0; p_amb <= 0; npr <= 1.
- throat_area(mdot_kg_s, p0_pa, t0_k) -> float m2 (choked sizing
  relation). ValueErrors: mdot <= 0; p0 <= 0; t0 <= 0.
- choked_exit_state(p0_pa, t0_k) -> dict {t_exit_k, v_exit_m_s,
  p_exit_pa, mach} with Te = T0*2/(gamma+1), Ve = sqrt(gamma R Te),
  Pe = P0*(2/(gamma+1))^(gamma/(gamma-1)), mach = 1.0. ValueErrors as
  above.
- gross_thrust(mdot_kg_s, v_exit_m_s, p_exit_pa, p_amb_pa,
  area_m2) -> float N = mdot*Ve + (Pe-Pa)*A. ValueErrors: mdot <= 0;
  v_exit < 0; area <= 0; p_exit <= 0; p_amb <= 0.
- unchoked_exit_state(p0_pa, p_amb_pa, t0_k) -> dict {mach, t_exit_k,
  v_exit_m_s} with Me from NPR = (1+(gamma-1)/2 Me^2)^(gamma/(gamma-1)),
  Te = T0/(1+(gamma-1)/2 Me^2), Ve = Me sqrt(gamma R Te). ValueErrors:
  regime must be unchoked (ValueError if NPR >= critical).
- unchoked_mass_flow(area_m2, p0_pa, t0_k, p_amb_pa) -> float kg/s =
  P0 At / sqrt(T0) * sqrt(gamma/R) * Me * (1+(gamma-1)/2 Me^2)^
  (-(gamma+1)/(2(gamma-1))) with Me from the unchoked relation.
  ValueErrors: as above; area <= 0; regime choked -> ValueError.
- nozzle_sizing(mdot_design_kg_s, p0_design_pa, t0_k, p_amb_pa) ->
  dict {regime, throat_area_m2, exit_state, gross_thrust_n,
  expansion_verdict} where expansion_verdict is FULLY_EXPANDED when
  p_exit <= p_amb + 1e-6 else PRESSURE_TERM_ACTIVE.
- off_design_nozzle(area_m2, p0_pa, t0_k, p_amb_pa) -> dict {regime,
  mach, v_exit_m_s, actual_mass_flow_kg_s}.

Identity to test: choked exit temperature Te == T0*2/(gamma+1);
gross thrust with p_exit == p_amb reduces to mdot*Ve; unchoked flow at
the critical ratio equals the choked flow (continuous at the boundary
within 1e-3 relative).

## Worked example

Reference design point: P0 = 300 kPa, T0 = 900 K, mdot = 70 kg/s,
Pa = 101.325 kPa. Off-design: same throat at P0 = 140 kPa.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- NPR = 2.961 >= critical 1.851 -> CHOKED.
- throat area = 70*sqrt(900)/(300000*sqrt(1.33/287)*0.5833) =
  0.176305 m2 (0.1763).
- choked exit: Te = 900*2/2.33 = 772.5 K; Ve = 543.0 m/s;
  Pe = 300000*(2/2.33)^(1.33/0.33) = 162109 Pa (162.1 kPa);
  Fg = 70*543.02 + (162109-101325)*0.176305 = 48728.7 N
  (48.7 kN); verdict PRESSURE_TERM_ACTIVE.
- off-design unchoked: NPR = 1.382 < 1.851; Me = 0.7115;
  Ve = 400.6 m/s; same throat passes 30.0 kg/s.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: npr <= 1; mdot <= 0; p0/t0/area <= 0; calling the
  unchoked exit state at a choked NPR raises; calling unchoked mass
  flow at a choked NPR raises.
- Regime: NPR 2.961 -> choked True; 1.382 -> choked False;
  critical ratio == 1.851 within 1e-3.
- Throat area 0.176305 within 1e-5.
- Choked exit: Te 772.5 within 1e-1; Ve 543.0 within 1e-1; Pe 162109
  within 1e-1 (magnitude ~162 kPa).
- Gross thrust 48728.7 within 1e-1; verdict PRESSURE_TERM_ACTIVE.
- Off-design: Me 0.7115 within 1e-3; Ve 400.6 within 1e-1; actual flow
  30.0 within 1e-2.
- Full-expansion identity: gross_thrust with Pe == Pa equals mdot*Ve.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-propelling-nozzle.yaml)

Query 1 (copy verbatim):
  "size the convergent propelling nozzle throat area for an air breathing gas turbine at 70 kg per second and 900 kelvin total temperature"
  intent: "propulsion; air-breathing jet nozzle throat area and choked regime"
  expected_skill: "propulsion/gas-turbine-cycle/propelling-nozzle"
Query 2 (copy verbatim):
  "compute the gross thrust of the choked propelling nozzle with the pressure thrust term at the exit"
  intent: "propulsion; convergent nozzle exit velocity and gross thrust"
  expected_skill: "propulsion/gas-turbine-cycle/propelling-nozzle"
Task ids: w36-propelling-nozzle-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the gas turbine propelling
nozzle:" and include the outputs in the Claim. First tag:
propelling-nozzle. Additional tags ONLY: convergent-jet-nozzle,
nozzle-throat-area, choked-nozzle-regime, gross-thrust-pressure-term,
air-breathing-nozzle. NEVER single generic words (nozzle, throat, jet,
choked, thrust, area, exit, pressure). 50-150 words, <=1000 chars, no
em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): expansion ratio, exit mach
iteration, chamber pressure, combustion products, cd (rocket
nozzle-design); afterburner duct, reheat (afterburner-cycle);
supersonic inlet, starting (ramjet-inlet); turbofan bypass (turbofan-
cycle); turbine nozzle guide vane (free-turbine).
