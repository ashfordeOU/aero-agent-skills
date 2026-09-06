# Wave-43 leaf spec: turbofan-design-point (propulsion, turbofan pack)

- Path: skills/propulsion/turbofan/turbofan-design-point/
- Pack: turbofan (present siblings turbofan-cycle, bypass-ratio-trade,
  turbofan-off-design; adjacent fences in propulsion/gas-turbine-cycle
  (turbojet-cycle, propelling-nozzle, real-cycle-effects,
  subsonic-inlet-recovery, combustor-design) and in
  vehicle-design/sizing (engine-sizing)).
- Claim fences (quoted from the sibling frontmatter at prep, none owns
  the two-stream station-level design point with the spool work
  balances):
  - turbofan-cycle (this pack) is the momentum-method consumer: its
    description reads "compute turbofan cycle parameters: calculate the
    bypass ratio from the fan and core mass flow, the propulsive
    efficiency from flight and jet velocity, the net thrust from total
    mass flow and the velocity change, and the specific thrust from net
    thrust per unit mass flow", with the quick reference "Net thrust
    F = mdot_total*(vj - v0), total mass flow times the jet-to-flight
    velocity change". Mass flows and jet velocities are INPUTS there;
    no station state, no fuel flow, no spool balance, no way to
    produce the velocities from the cycle.
  - bypass-ratio-trade (this pack) FIXES the core conditions and jet
    velocities: its description reads "compute the thrust split between
    the fan and core streams, the specific thrust, and the
    thrust-specific fuel consumption across candidate bypass ratios,
    and weigh them against the fan pressure ratio trend", and its
    workflow step 1 is "Fix the core conditions: total mass flow, core
    and fan jet velocities, flight velocity, and the core fuel/air
    ratio". Its TSFC-versus-BPR verdict assumes those jet velocities
    stay constant; the new leaf re-balances the LP spool, so the core
    jet velocity is an output that falls as BPR grows at fixed Tt4.
  - turbofan-off-design (this pack) PRESUMES an existing design point:
    its description reads "evaluate turbofan performance away from the
    design point: correct the inlet mass flow and the spool speed to
    standard-day conditions, scale the sea-level net thrust to altitude
    with the density ratio and the ram drag penalty, apply the SFC
    altitude and throttle behavior". It starts from a rated
    sea-level thrust and a rated SFC; it never builds the design point
    the corrections are relative to, and it owns corrected-mass-flow,
    corrected-speed, throttle and component-matching tokens.
  - turbojet-cycle (gas-turbine-cycle pack, structural analog) is
    SINGLE-stream: its description reads "analyze an ideal
    single-stream turbojet core cycle at flight conditions: compute the
    freestream stagnation temperature from the flight Mach number, the
    compressor exit temperature from the pressure ratio, the
    fuel-to-air ratio from the turbine inlet temperature and the
    combustor efficiency, the turbine exit temperature from the
    compressor-turbine work balance, the nozzle exit temperature and
    exit velocity, the net specific thrust as the exit velocity minus
    the flight velocity, the turbojet TSFC and the propulsive
    efficiency". It has one stream and one compressor-turbine balance;
    the new leaf is its two-stream, two-spool generalization with the
    fan and bypass stream added and the LP spool balance carrying the
    (1 + BPR) fan work multiplier.
  - propelling-nozzle (gas-turbine-cycle) sizes a nozzle at a GIVEN
    entry total state: its description reads "decide the choked or
    unchoked regime from the nozzle pressure ratio against the critical
    ratio 1.851, size the throat area from the design mass flow and
    total conditions under the choked flow relation, and return the
    choked exit temperature, velocity and static pressure plus the
    gross thrust with the pressure term, or for an unchoked off-design
    point the exit Mach number and the actual mass flow the throat
    passes". Nozzle throat sizing, regime decisions for arbitrary entry
    states and unchoked mass-flow accounting are theirs; the new leaf's
    nozzle step is a station traverse on the pressure ratios the cycle
    produces, returning exit velocity for the net-thrust bookkeeping.
  - real-cycle-effects (gas-turbine-cycle) owns combustor pressure
    loss and temperature-dependent specific heats; the new leaf keeps
    pt4 = pt3 and constant cp_c/cp_g. combustor-design owns the burner
    thermochemistry (adiabatic flame temperature, heat release,
    stoichiometry); the fuel/air ratio here is a single combustor
    energy balance. subsonic-inlet-recovery owns the inlet recovery
    design analysis against Mach; the new leaf consumes one diffuser
    efficiency eta_d in a single ram traverse. vehicle-design/sizing/
    engine-sizing owns aircraft engine selection and installed thrust
    sizing from thrust-to-weight (corpus task esg2); the new leaf
    produces engine cycle output, never aircraft thrust demand.
  Whole-tree greps at prep: the hyphenated tokens turbofan-design-point,
  fan-stream-station-states, two-spool-work-balance and
  separate-exhaust-cycle return 0 hits in eval/hit1-corpus.yaml and 0
  hits anywhere under skills/ (the only repo mentions are the wave-43
  planning files ops/automation/state/wave43-leaf-plan.md and
  wave43-recon/verify-plan.py); a second skills-tree grep for
  "two-spool|dual-spool|fan-stream|separate-exhaust|spool work" returns
  0 hits. Corpus neighbors tf1/tf2 route on mass flow and jet velocity
  inputs (turbofan-cycle), bpr1/bpr2 on the fixed-core trade
  (bypass-ratio-trade), tod1/tod2 on corrected flow and altitude
  scaling (turbofan-off-design), w39-turbojet-cycle-1/-2 on the
  single-stream core, cbd2 (combustor-design) uses the words "design
  point" but routes on adiabatic-flame-temperature and
  combustion-efficiency, acst2 (axial-compressor-stage) uses "design
  point" for one stage's velocity triangle, and esg2 (engine-sizing)
  selects engines from thrust-to-weight. GENUINE propulsion gap (probe
  receipt C3, verified zero-owner, GO): no leaf produces the two-stream
  station-level design point the turbofan-cycle and bypass-ratio-trade
  consumers take as given.
- Standards id: far-33 (14 CFR Part 33, reference-only, present in
  standards-map.yaml). Ledger Standard: far-33.
- Family: propulsion

## Claim

Compute the two-stream turbofan design point at flight Mach number and
altitude (the separate-exhaust-cycle, the producer the momentum-method
consumers lack): traverse the station chain 0-2-13-2.5-3-4-4.5-5-9/19
(0 freestream static; 2 fan face after the inlet; 13 fan exit, common to
both streams and the fan-nozzle inlet; 2.5 booster, the LP compressor,
exit and HPC inlet; 3 HPC exit, the combustor inlet; 4 combustor exit,
the turbine inlet Tt4; 4.5 HPT exit, the LPT inlet; 5 LPT exit, the
core-nozzle inlet; 9 core-nozzle exit; 19 fan-nozzle exit) and report
the fan and core stream total states (Tt and Pt) at every station. From
the freestream state and the diffuser efficiency eta_d the inlet gives
the fan face; the fan at fan pressure ratio FPR feeds both streams, the
booster (LP compressor) then the HPC compress the core stream, and the
overall pressure ratio OPR is closed from the fan face to the HPC exit,
opr = pt3/pt2 = fpr*lpc_pr*hpc_pr, so hpc_pr = opr/(fpr*lpc_pr). The
burner sets the fuel/air ratio f = cp_c*(Tt4 - Tt3)/(eta_b*lhv) with no
combustor pressure loss (pt4 = pt3). The HP spool work balance drives
the HPC from the HPT: cp_g*(Tt4 - Tt4.5) = cp_c*(Tt3 - Tt2.5); the LP
spool work balance drives the fan on BOTH streams plus the booster from
the LPT: cp_g*(Tt4.5 - Tt5) = cp_c*((1 + bpr)*(Tt13 - Tt2) + (Tt25 -
Tt13)) per unit core air, the (1 + bpr) multiplier being the signature
of the two-spool-work-balance. Each turbine pressure ratio follows from
its isentropic-efficiency expansion, and each convergent nozzle exits
choked (sonic, static pressure above ambient) or unchoked (fully
expanded) through the nozzle velocity coefficient, giving the fan and
core stream nozzle exit velocities v19 and v9. The net thrust is F =
mdot_core*(v9 - v0) + mdot_fan*(v19 - v0) + (p9 - p0)*A9 + (p19 - p0)*
A19 with the choked-nozzle pressure terms from the exit-plane areas
A = mdot*R*Te/(Pe*Ve), and TSFC = f*mdot_core/F. Produces the
fan-stream-station-states and the core stream states, the burner
fuel/air ratio, the HP and LP spool works with the Tt4.5 and Tt5
closing temperatures, the per-stream nozzle exit velocities and nozzle
pressure ratios, the net thrust and its momentum and pressure
decomposition, and the TSFC of the separate-exhaust turbofan, in SI
units. Does NOT do: off-design matching, corrected flow and corrected
speed, altitude thrust scaling or throttle behavior (turbofan-off-
design); bypass ratio, propulsive efficiency or specific thrust from
mass flows and jet velocities GIVEN as inputs, or the
bypass-ratio-trade TSFC sweep at fixed core and jet conditions with its
fan-pressure-ratio verdict (turbofan-cycle, bypass-ratio-trade);
single-stream core cycles (turbojet-cycle); mixed-stream or mixed-
exhaust configurations (separate-exhaust only); combustor pressure
loss, temperature-dependent specific heats or turbine cooling flows
(real-cycle-effects); nozzle throat area sizing or unchoked mass-flow
accounting at an arbitrary entry state (propelling-nozzle); inlet
recovery design analysis (subsonic-inlet-recovery); burner
thermochemistry (combustor-design); aircraft engine selection and
installed thrust sizing (vehicle-design engine-sizing). Component
efficiencies are constant-gamma isentropic forms on KAPPA_C and KAPPA_G
only; polytropic exponents and variable properties are out of scope.

## Model (implement exactly)

Pure stdlib, math only. Module constants: GAMMA_C = 1.4 (cold air, fan
and core compression, fan nozzle), KAPPA_C = (GAMMA_C - 1)/GAMMA_C =
2/7; GAMMA_G = 4/3 (hot gas, turbines and core nozzle), KAPPA_G =
(GAMMA_G - 1)/GAMMA_G = 1/4; CP_C = 1005.0 J/(kg K), CP_G = 1150.0
J/(kg K); R_C = CP_C*KAPPA_C (= 287.142857 J/(kg K)), R_G = CP_G*
KAPPA_G (= 287.5 J/(kg K)); LHV = 43.0e6 J/kg; ISA constants
ISA_SEA_T = 288.15 K, ISA_SEA_P = 101325.0 Pa, ISA_LAPSE = 0.0065 K/m,
ISA_R = 287.0 J/(kg K), G0 = 9.80665 m/s^2, ISA_EXP = G0/(ISA_R*
ISA_LAPSE) (about 5.25588), ALT_TROP = 11000.0 m, and
LBF_PER_HR_FACTOR = 3600.0*G0 (35303.9, the kg/(N s) to lbm/(lbf hr)
conversion). OPR is the turbomachinery ratio from the fan face: opr =
pt3/pt2. Station 13 is the fan discharge for BOTH streams (the bypass
stream runs loss-free from 13 to the fan nozzle), and the core stream
enters the booster from the same fan-discharge state.

Defining relations (pin these exactly; every function below derives
from them):
- Ram traverse: v0 = mach*sqrt(GAMMA_C*R_C*t0); tt0 = t0*(1 + 0.5*
  (GAMMA_C - 1)*mach^2); pt0 = p0*(tt0/t0)**(1/KAPPA_C) (isentropic
  freestream).
- Diffuser: tt2 = tt0; pt2 = p0*(1 + eta_d*(tt0/t0 - 1))**(1/KAPPA_C)
  from the ambient STATIC pressure p0; equals pt0 at eta_d = 1.
- Cold compressor (fan, booster, HPC) at isentropic efficiency eta:
  tt_s = tt_in*pr**KAPPA_C and tt_out = tt_in + (tt_s - tt_in)/eta;
  pt_out = pt_in*pr.
- Burner: f = cp_c*(tt4 - tt3)/(eta_b*lhv); pt4 = pt3 (no pressure
  loss).
- HP spool balance: cp_g*(tt4 - tt45) = cp_c*(tt3 - tt25).
- LP spool balance: cp_g*(tt45 - tt5) = cp_c*((1 + bpr)*(tt13 - tt2)
  + (tt25 - tt13)), per unit core air; the fan term carries (1 + bpr)
  because the fan moves the bypass stream AND the core stream.
- Turbine expansion at isentropic efficiency eta: tt_s = tt_in -
  (tt_in - tt_out)/eta and pt_out/pt_in = (tt_s/tt_in)**(1/KAPPA_G).
- Nozzle: npr = pt_in/p_amb; choked when npr >= critical =
  ((gamma+1)/2)**(gamma/(gamma-1)) (1.892929 cold, 1.852623 hot at the
  module constants); choked: Me = 1, te = 2*tt_in/(gamma+1), pe =
  pt_in*((gamma+1)/2)**(-gamma/(gamma-1)); unchoked: pe = p_amb, te =
  tt_in*(p_amb/pt_in)**((gamma-1)/gamma). Ideal velocity sqrt(2*cp*
  (tt_in - te)); actual ve = cv*v_ideal (nozzle velocity coefficient).
- Exit-plane area for the pressure term: A = mdot*R*te/(pe*ve) from
  continuity at the exit plane; the pressure term (pe - p0)*A is zero
  for an unchoked fully expanded nozzle.
- Net thrust F = mdot_core*(v9 - v0) + mdot_fan*(v19 - v0) + (pe9 -
  p0)*A9 + (pe19 - p0)*A19; TSFC = mdot_fuel/F with mdot_fuel = f*
  mdot_core.

Functions (10, all raising ValueError as listed; no imports beyond
math):
- isa_atmosphere(altitude) -> (t0, p0): ISA troposphere,
  t0 = 288.15 - 0.0065*altitude, p0 = 101325.0*(t0/288.15)**ISA_EXP.
  ValueError if altitude outside [0, 11000].
- freestream_state(t0, p0, mach) -> (v0, tt0, pt0): v0 = mach*a0 with
  a0 = sqrt(GAMMA_C*R_C*t0). ValueError if t0 <= 0, p0 <= 0 or mach
  < 0.
- diffuser_state(tt0, t0, p0, eta_d) -> (tt2, pt2): tt2 = tt0; pt2
  from the eta_d ram relation above (base pressure p0, the ambient
  static value). ValueError if tt0, t0 or p0 non-positive or eta_d
  outside (0, 1].
- compressor_exit_temperature(tt_in, pr, eta) -> float: the cold
  isentropic-efficiency compression relation. ValueError if tt_in <= 0,
  pr <= 1 or eta outside (0, 1].
- hp_spool_balance(tt25, tt3, tt4, cp_c = CP_C, cp_g = CP_G) -> float:
  tt45 = tt4 - (cp_c/cp_g)*(tt3 - tt25). ValueError unless 0 < tt25 <
  tt3 < tt4, and if the HP demand (cp_c/cp_g)*(tt3 - tt25) reaches tt4.
- lp_spool_balance(tt2, tt13, tt25, tt45, bpr, cp_c = CP_C, cp_g =
  CP_G) -> float: tt5 = tt45 - (cp_c/cp_g)*((1 + bpr)*(tt13 - tt2) +
  (tt25 - tt13)). ValueError unless 0 < tt2 < tt13 < tt25, bpr >= 0,
  and if the LP demand reaches tt45 (the fan-growth limit at fixed Tt4,
  anchor: bpr 40 raises).
- fuel_air_ratio(tt3, tt4, eta_b, cp = CP_C, lhv = LHV) -> float:
  f = cp*(tt4 - tt3)/(eta_b*lhv). ValueError if tt3 <= 0, tt4 <= tt3
  or eta_b outside (0, 1].
- turbine_pressure_ratio(tt_in, tt_out, eta) -> float: (tt_s/tt_in)**
  (1/KAPPA_G) with tt_s = tt_in - (tt_in - tt_out)/eta. ValueError if
  tt_in <= 0, tt_out >= tt_in (turbines must cool) or eta outside
  (0, 1].
- nozzle_exit(tt_in, pt_in, p_amb, gamma, cp, cv) -> dict: the
  choked-or-unchoked nozzle exit with keys choked, me, npr, critical,
  te, pe, v_ideal, ve. ValueError if tt_in <= 0, cp <= 0, pt_in <=
  p_amb (nothing to expand, sibling convention) or cv outside (0, 1].
- turbofan_design_point(mach, altitude, opr, fpr, lpc_pr, bpr, tt4,
  mdot_core, eta_d, eta_fan, eta_lpc, eta_hpc, eta_b, eta_hpt,
  eta_lpt, cv_core, cv_fan) -> dict: the full report with the station
  total states (tt0, pt0, tt2, pt2, tt13, pt13, tt25, pt25, tt3, pt3,
  tt4, pt4, tt45, pt45, tt5, pt5), ram_recovery pt2/pt0, hpc_pr and
  opr_actual pt3/pt2, f, the core_nz and fan_nz nozzle dicts, a9 and
  a19, mdot_core, mdot_fan, mdot_total, the four thrust terms
  (f_core_mom, f_fan_mom, f_core_pres, f_fan_pres), net_thrust,
  specific_thrust net_thrust/mdot_total, mdot_fuel, tsfc in kg/(N s)
  and tsfc_imp = tsfc*3600*9.80665 in lb/(lbf hr). ValueError if
  mdot_core <= 0 or opr <= fpr*lpc_pr (the HPC would have no ratio),
  plus every guard above.
- Conversion note: 1 lb/(lbf hr) = 2.8325e-5 kg/(N s) and mg/(N s)
  equals g/(kN s) numerically, so the plausibility band 0.5-0.7
  lb/(lbf hr) is 1.416e-5 to 1.983e-5 kg/(N s), 14.16 to 19.83
  mg/(N s).

Identities to test (exact or to float noise):
- OPR closure: opr_actual = pt3/pt2 equals the input opr to 1e-9
  relative (hpc_pr = opr/(fpr*lpc_pr) by construction; anchor prints
  36.000000).
- HP spool: cp_g*(tt4 - tt45) == cp_c*(tt3 - tt25) to 1e-12 relative
  (anchor residual 2.667e-16); HP work equals the turbine work per kg
  core air exactly.
- LP spool: cp_g*(tt45 - tt5) == cp_c*((1 + bpr)*(tt13 - tt2) + (tt25
  - tt13)) to 1e-12 relative (anchor residual 1.381e-16); the fan term
  alone is cp_c*(1 + bpr)*(tt13 - tt2) = 381551.107739 J/kg at the
  anchor and the booster term cp_c*(tt25 - tt13) = 40082.672339 J/kg.
- TSFC round trip: tsfc*net_thrust == f*mdot_core == mdot_fuel to
  1e-12 relative (anchor 0.00e+00).
- Thrust decomposition: net_thrust equals the sum of the four printed
  terms to 1e-12 relative (anchor 0.00e+00); the momentum terms are
  mdot*(ve - v0) per stream and the pressure terms (pe - p0)*A vanish
  only for unchoked nozzles.
- Choked nozzles at the anchor: core NPR 2.673356 and fan NPR 2.485320
  both exceed their critical ratios, so both choked flags are True with
  Me = 1.000000 and pe above p0.
- Mass split: mdot_fan = bpr*mdot_core and mdot_total = (1 + bpr)*
  mdot_core; at the anchor 8.0 and 9.0 kg/s from mdot_core = 1.0.
- BPR trend at fixed core conditions (the bypass-ratio-trade direction
  while the core sustains the fan): TSFC falls from bpr 4 (anchor
  1.7955257472e-05 kg/(N s), Tt5 1001.2826 K, v9 562.1074 m/s, F
  1111.5060 N, 0.633891 lb/(lbf hr)) to bpr 8 (1.4461947730e-05,
  0.510564 lb/(lbf hr)); at bpr 12 the LP turbine has over-expanded the
  core: Tt5 falls to 706.3639 K, the core nozzle unchokes (choked
  False) and v9 = 63.6385 m/s falls below v0 = 237.2655 m/s, so the
  core stream drags, F falls back to 1286.9882 N and the TSFC rises
  again to 1.5507038944e-05 kg/(N s) = 0.547460 lb/(lbf hr): the
  fixed-Tt4 TSFC minimum sits between bpr 8 and 12; at bpr 40 the LP
  enthalpy guard raises ValueError. The monotone TSFC fall of
  bypass-ratio-trade requires FIXED jet velocities as inputs, which
  this re-balanced spool model does not have.
- Degenerate bpr 0: the fan stream vanishes (mdot_fan = 0, fan thrust
  terms zero) and F = core momentum + core pressure (anchor 757.465500
  N = 364.811750 + 392.653749).
- Determinism: a rerun returns byte-identical values; no imports beyond
  math; gamma constants fixed.

## Worked example

Representative 2-spool separate-exhaust turbofan at cruise: mach 0.8,
altitude 35000 ft (10668.0 m), opr 36, fpr 1.65, lpc_pr 1.50 (so hpc_pr
= 36/(1.65*1.5) = 14.545), bpr 8, Tt4 = 1600 K, mdot_core = 1.0 kg/s,
eta_d 0.97, eta_fan 0.90, eta_lpc 0.89, eta_hpc 0.87, eta_b 0.98,
eta_hpt 0.86, eta_lpt 0.86, cv_core 0.98, cv_fan 0.98. All values below
are REAL outputs of the prep anchor /tmp/w43spec/anchor_tfdp.py
(stdlib math, exit 0).

- Ambient and flight: t0 = 218.8080 K, p0 = 23835.9189 Pa (ISA 35000
  ft), v0 = 237.2655 m/s; Tt0 = 246.815424 K, Pt0 = 36334.044867 Pa.
- Inlet: Tt2 = 246.815424 K, Pt2 = 35902.967650 Pa, ram recovery
  Pt2/Pt0 = 0.988136 (eta_d 0.97 against the isentropic 1.5243).
- Fan stream (fan-stream-station-states): station 13 fan exit, Tt13 =
  288.999073 K, Pt13 = 59239.896623 Pa = 2.485320*p0.
- Core stream: station 2.5 booster exit, Tt25 = 328.882329 K, Pt25 =
  88859.844935 Pa; station 3 HPC exit, Tt3 = 763.180293 K, Pt3 =
  1292506.835411 Pa with Pt3/Pt2 = 36.000000 (the OPR closure);
  station 4, Tt4 = 1600 K, Pt4 = Pt3 (no combustor pressure loss);
  station 4.5 HPT exit, Tt45 = 1220.461345 K, Pt45 = 355468.349294 Pa;
  station 5 LPT exit, Tt5 = 853.823275 K, Pt5 = 63721.905090 Pa.
- Burner: f = 0.01995738 kg fuel per kg air (about 19.96 g/kg),
  mdot_fuel = 0.01995738 kg/s at the 1 kg/s core flow.
- Spool works (J per kg core air): HP balance, w_hpc = cp_c*(Tt3 -
  Tt2.5) = 436469.453161 equals w_hpt = cp_g*(Tt4 - Tt4.5) =
  436469.453161 (residual 2.667e-16 relative). LP balance, the fan on
  both streams cp_c*(1 + bpr)*(Tt13 - Tt2) = 381551.107739 plus the
  booster cp_c*(Tt25 - Tt13) = 40082.672339 gives the demand
  421633.780078, equal to w_lpt = cp_g*(Tt4.5 - Tt5) = 421633.780078
  (residual 1.381e-16 relative).
- Nozzles: core NPR = 2.673356 above the hot critical 1.852623, choked
  with Me = 1.000000: Te = 731.848522 K, Pe = 34395.497291 Pa, v_ideal
  = 529.662094 m/s, v9 = 519.068852 m/s (cv_core 0.98), A9 =
  0.01178508 m^2 and the pressure term (Pe - p0)*A9 = 124.445462 N.
  Fan NPR = 2.485320 above the cold critical 1.892929, choked with
  Me = 1.000000: Te = 240.832561 K, Pe = 31295.358492 Pa, v_ideal =
  311.150590 m/s, v19 = 304.927578 m/s, A19 = 0.05797311 m^2 and the
  pressure term (Pe - p0)*A19 = 432.446886 N.
- Mass flows: mdot_core 1.0, mdot_fan 8.0, mdot_total 9.0 kg/s.
- Thrust: core momentum 281.803342 N, fan momentum 541.296544 N, core
  pressure 124.445462 N, fan pressure 432.446886 N, net thrust F =
  1379.992234 N (153.3325 N per kg/s of total flow); the decomposition
  sums to F with relative residual 0.00e+00.
- TSFC: mdot_fuel/F = 1.4461947730e-05 kg/(N s) = 14.461948 mg/(N s)
  = 14.461948 g/(kN s) = 0.510564 lb/(lbf hr), INSIDE the 0.5-0.7
  lb/(lbf hr) plausibility band (1.416e-5 to 1.983e-5 kg/(N s)); the
  round trip tsfc*F = 1.9957375554e-02 = mdot_fuel exactly
  (residual 0.00e+00).
- Read-off: the fan stream delivers 974 N (momentum plus pressure) of
  the 1380 N total at 8 times the core flow, the propulsive
  efficiencies are 0.875207 on the fan stream and 0.627409 on the core
  stream, and the design point closes both spool balances to float
  noise; TSFC 0.5106 lb/(lbf hr) is a plausible cruise figure for a
  36-OPR, 1600 K engine.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w43spec/anchor_tfdp.py
(stdlib math, exit 0).

## Validation list (contract test must include)

- isa_atmosphere(10668.0) = (218.8080, 23835.92) within (0.05 K, 2 Pa);
  freestream_state gives v0 = 237.2655 within 0.05 m/s and Tt0 =
  246.8154 within 0.01 K.
- diffuser_state gives Pt2 = 35902.97 within 5 Pa (recovery 0.988136
  within 1e-5); turbofan_design_point closes Pt3/Pt2 = opr = 36.000000
  within 1e-9 relative.
- Station anchors: Tt13 = 288.9991 within 0.05 K and Pt13 = 59239.90
  within 5 Pa; Tt25 = 328.8823 within 0.05 K; Tt3 = 763.1803 within
  0.1 K; Tt45 = 1220.4613 within 0.1 K; Tt5 = 853.8233 within 0.1 K;
  the chain stays ordered Tt2 < Tt13 < Tt25 < Tt3 < Tt4 and Tt5 <
  Tt45 < Tt4.
- f = 0.01995738 within 1e-6; mdot_fuel = f*mdot_core exactly.
- HP and LP spool residuals below 1e-12 relative at the anchor
  (2.667e-16 and 1.381e-16); LP fan-share term cp_c*(1 + bpr)*(Tt13 -
  Tt2) = 381551.108 within 0.01 J/kg.
- Both nozzles choked at the anchor: core NPR 2.673356 and fan NPR
  2.485320 above their critical ratios, Me = 1 within 1e-9; v9 =
  519.0689 within 0.5 m/s and v19 = 304.9276 within 0.5 m/s; A9 =
  0.0117851 and A19 = 0.0579731 within 1e-5 m^2.
- Net thrust F = 1379.9922 within 1 N, equal to the momentum plus
  pressure decomposition within 1e-9 relative; specific thrust =
  153.3325 within 0.05 N/(kg/s); mdot_fan = 8.0 and mdot_total = 9.0
  kg/s.
- TSFC = 1.4461947730e-05 kg/(N s) within 1e-8, inside 1.416e-5 to
  1.983e-5 kg/(N s) (the 0.5-0.7 lb/(lbf hr) band); tsfc_imp = 0.5106
  within 0.005 lb/(lbf hr); round trip tsfc*F = mdot_fuel within 1e-9
  relative.
- Trend: TSFC(bpr 4) = 1.7955257472e-05 within 1e-8 kg/(N s) with F =
  1111.5060 within 1 N and v9 = 562.1074 within 0.5 m/s; TSFC(bpr 8) =
  1.4461947730e-05 < TSFC(bpr 4); at bpr 12 the core nozzle unchokes,
  Tt5 = 706.3639 within 0.1 K, v9 = 63.6385 within 0.1 m/s falls below
  v0, F = 1286.9882 within 1 N and TSFC = 1.5507038944e-05 within 1e-8;
  bpr 40 raises ValueError (LP enthalpy guard).
- Degenerate bpr 0: F = 757.4655 within 0.5 N with zero fan terms.
- ValueErrors: altitude -1.0 and 20000.0; negative mach; eta_d at 1.5;
  compressor pressure ratio 1.0 and eta 0; hp_spool_balance with tt3
  <= tt25; lp_spool_balance with bpr -1; fuel_air_ratio with tt4 <=
  tt3 and eta_b 1.01; turbine_pressure_ratio with tt_out >= tt_in;
  nozzle_exit with pt_in <= p_amb and cv 1.01; turbofan_design_point
  with opr 2.0 (below fpr*lpc_pr) and mdot_core 0.
- Determinism: two identical runs return identical reports; no imports
  beyond math.

## Corpus fragment (eval/hit1-wave43-turbofan-design-point.yaml)

Query 1 (copy verbatim):
  "analyze the turbofan-design-point of the two-spool
  separate-exhaust-cycle at mach 0.8 and 35000 feet: traverse the
  fan-stream-station-states and the core stream from the overall
  pressure ratio, the turbine-inlet temperature, the bypass ratio and
  the fan pressure ratio with the component efficiencies, and report
  the burner fuel-air ratio, the net thrust and the tsfc"
  intent: "propulsion; two-spool separate-exhaust turbofan
  design-point station-level cycle from OPR, turbine-inlet temperature,
  bypass ratio and fan pressure ratio with component efficiencies"
  expected_skill: "propulsion/turbofan/turbofan-design-point"
Query 2 (copy verbatim):
  "close the two-spool-work-balance of the turbofan-design-point: size
  the hp and lp turbine exit temperatures that drive the high-pressure
  compressor and the fan plus booster, then the core and fan nozzle
  exit velocities and the net thrust of the separate-exhaust-cycle"
  intent: "propulsion; HP and LP spool work balances of the turbofan
  design point with the per-stream nozzle exit velocities and net
  thrust"
  expected_skill: "propulsion/turbofan/turbofan-design-point"
Task ids: w43-turbofan-design-point-1 and -2. Prep grep: the tokens
turbofan-design-point, fan-stream-station-states, two-spool-work-balance
and separate-exhaust-cycle appear in NO existing eval/hit1-corpus.yaml
task and in no skills leaf; the turbofan-cycle tasks (tf1/tf2) route on
bypass ratio and thrust from given mass flows and jet velocities, the
bypass-ratio-trade tasks (bpr1/bpr2) route on the fixed-core thrust
split and TSFC trend, the turbofan-off-design tasks (tod1/tod2) route
on corrected mass flow, corrected speed and altitude thrust, the
turbojet-cycle tasks (w39-turbojet-cycle-1/-2) on the single-stream
core, combustor-design task cbd2 carries the words "design point" but
routes on adiabatic-flame-temperature and combustion-efficiency, and
axial-compressor-stage task acst2 uses "design point" for a single
stage, so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the two-stream turbofan
design point at flight Mach and altitude:" and include the outputs in
the Claim. First tag: turbofan-design-point. Additional tags ONLY:
fan-stream-station-states, two-spool-work-balance,
separate-exhaust-cycle, hp-and-lp-turbine-matching. NEVER single
generic words (turbofan, design, point, cycle, fan, core, bypass,
station, thrust, nozzle, spool, turbine, compressor, efficiency, tsfc)
and NEVER sibling tags (turbofan-cycle, bypass-ratio-trade,
turbofan-off-design, turbojet-cycle, propelling-nozzle, off-design,
corrected-mass-flow, corrected-speed, component-matching, bpr,
bypass-ratio, specific-thrust, propulsive-efficiency). 50-150 words,
<=1000 chars, no em dash, no content-policy sweep term, action verb
present.
Recommended wording (outputs in Claim order): "Use when you must
compute the two-stream turbofan design point at flight Mach and
altitude: traverse the fan-stream-station-states and the core stream of
the separate-exhaust-cycle down the 0-2-13-2.5-3-4-4.5-5-9/19 station
chain from the overall pressure ratio, the turbine-inlet temperature,
the bypass ratio and the fan pressure ratio with the component
efficiencies; close the two-spool-work-balance of the high-pressure
compressor on the HP turbine and of the fan plus booster on the LP
turbine; and report the burner fuel-air ratio, the per-stream nozzle
exit velocities with the choked pressure terms, and the net thrust and
TSFC of the separate-exhaust turbofan. Produces the station total
states, the spool works, the jet velocities, the net thrust and the
TSFC, in SI units, that gate the engine design-point assessment.
Trigger: turbofan design point, two-spool engine cycle, fan stream
station states, separate exhaust cycle, overall pressure ratio,
fuel-air ratio, net thrust and tsfc."

FORBIDDEN TOKENS (belong to siblings): net thrust or bypass ratio or
propulsive efficiency or specific thrust from GIVEN mass flows and jet
velocities, fan and core mass flow as inputs (turbofan-cycle);
bypass-ratio trade sweep, thrust split at fixed core conditions,
TSFC-versus-BPR trend with jet velocities FIXED as inputs,
fan-pressure-ratio trade verdict, the g/(kN s) reporting of a fixed-
core sweep (bypass-ratio-trade); corrected-mass-flow, corrected-speed,
altitude thrust scaling, ram drag penalty, throttle setting,
component matching, cruise SFC factor, existing-design-point rating
(turbofan-off-design); single-stream core cycle station states without
the bypass stream (turbojet-cycle); mixed-stream-exhaust, mixer,
mixed-exhaust (reserved mixed-flow-exhaust); combustor pressure loss,
temperature-dependent specific heat, turbine blade cooling flows,
bleed (real-cycle-effects); nozzle throat area sizing, unchoked
off-design mass flow through a sized throat, gross thrust of a
standalone nozzle (propelling-nozzle); inlet recovery design analysis,
recovery-versus-Mach curve (subsonic-inlet-recovery); adiabatic flame
temperature, combustion efficiency, heat release, stoichiometry
(combustor-design); engine selection, installed thrust, engine weight,
thrust-to-weight sizing (vehicle-design engine-sizing).
