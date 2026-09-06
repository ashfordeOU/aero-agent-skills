# Wave-44 leaf spec: mixed-flow-exhaust (propulsion, turbofan pack)

- Path: skills/propulsion/turbofan/mixed-flow-exhaust/
- Pack: turbofan (present siblings turbofan-cycle, turbofan-design-point,
  turbofan-off-design, bypass-ratio-trade; adjacent fences in
  propulsion/gas-turbine-cycle (afterburner-cycle, propelling-nozzle) and
  propulsion/turbofan/bypass-ratio-trade; the wave-43 reserve candidate,
  re-verified zero-owner GO at HEAD 496467d0 by probe deleg_2ff07eac
  task-1).
- Claim fences (quoted from the sibling frontmatter at prep, none owns the
  two-stream MIXING exhaust):
  - turbofan-design-point (this pack, wave-43): "compute the two-stream
    turbofan design point ... of the separate-exhaust-cycle ... and report
    the per-stream nozzle exit velocities with the choked pressure terms,
    and the net thrust and TSFC of the separate-exhaust turbofan". Its
    Does-NOT-do list names "mixed-stream or mixed-exhaust configurations
    (separate-exhaust only)" and its corpus tasks carry
    separate-exhaust-cycle tokens. The fan and core streams each exit
    their own convergent nozzle; no mixer thermodynamics anywhere.
  - afterburner-cycle (gas-turbine-cycle): "the reheat fuel flow for the
    core mass flow" - a SINGLE-stream core with reheat; no fan stream, no
    mixer, no common nozzle.
  - bypass-ratio-trade (this pack): "compute the thrust split between the
    fan and core streams" at the VELOCITY level for the trade sweep - no
    mixer energy/momentum balance, no mixed total state.
  - propelling-nozzle (gas-turbine-cycle): convergent single-stream choked
    regime sizing of one stream; the mixed-flow leaf's nozzle step is a
    single convergent nozzle on the MIXED stream (one stream after the
    mixer), using the same choked/unchoked relations.
  - rocket-turbopump (turbomachinery): the only "mixed-flow" token hits in
    the tree are its pump-TYPE classifier lines (mixed-flow pump vs
    centrifugal/axial) - noise, not an air-breathing owner (verified
    corpus 0).
  Whole-tree greps at prep: mixed-flow|mixed-stream|exhaust-mixer|mixing-
  loss|common-nozzle -> 0 air-breathing owners in skills/, 0 corpus tasks;
  only rocket-turbopump pump-type classifier noise (2 hits). Corpus
  neighbors tf1/tf2 (turbofan-cycle mass-flow/jet-velocity inputs),
  w43-turbofan-design-point-1/-2 (separate-exhaust-cycle tokens), bpr1/bpr2
  (fixed-core trade), aft1/aft2 (core-only reheat) carry no mixer claim.
  GENUINE propulsion gap (probe receipt task-1 rank 1, wave-43 reserve):
  no leaf produces the two-stream MIXED-FLOW station-level design point
  (mixer + common nozzle) that the separate-exhaust design-point leaf
  explicitly disclaims.
- Standards id: far-33 (14 CFR Part 33, reference-only, present in
  standards-map.yaml). Ledger Standard: far-33.
- Family: propulsion

## Claim

Compute the two-stream turbofan design point with a MIXING (common)
exhaust at flight Mach and altitude: traverse the component chain to the
mixer-entry states exactly as the separate-exhaust sibling does (fan on
both streams, booster, HPC, burner, HPT, LPT; station 0-2-13-2.5-3-4-
4.5-5), carry the bypass stream through the fan duct to the mixer entry
(station 16 = station 13 total state scaled by the duct pressure ratio
pi_duct) and the core stream from the LPT exit (station 5) to the same
mixer entry plane, then close the CONSTANT-AREA MIXER by the energy and
momentum balances over the two streams' total states and expand the
mixed stream through ONE common convergent nozzle. The mixer design
input is the fan-stream mixer-entry Mach M_fan_entry in (0, 1); the
common entry static pressure p_s follows from the fan stream's total
state, the core-stream entry Mach is derived from that same p_s
(subsonic root), the entry areas follow from continuity, and the
constant-area duct momentum balance (m_total*v_exit + p_exit*A =
m_f*v_f + m_g*v_g + p_s*A) with the exit static pressure from continuity
closes the uniform mixed exit state on the first (subsonic) root by
bisection. Produces the mixed total temperature and pressure (energy +
momentum balance), the mixer total-pressure loss ratio against the
mass-weighted entry total pressure, the common-nozzle exit velocity and
pressure term, the net thrust and TSFC of the mixed-flow configuration,
and the separate-exhaust baseline (same traverse, per-stream nozzles)
for the F and TSFC comparison that gates the mixed-vs-separate exhaust
decision at a given low-BPR operating point. Does NOT do: off-design
matching, corrected flow or throttle behavior (turbofan-off-design);
separate-exhaust per-stream nozzle bookkeeping as the OUTPUT (that is
turbofan-design-point; here it is the comparison baseline only); core-
only reheat (afterburner-cycle); the bypass-ratio trade sweep
(bypass-ratio-trade); combustor pressure loss, variable specific heats
or turbine cooling (real-cycle-effects); nozzle throat AREA sizing for
arbitrary entry states (propelling-nozzle); engine selection and
installed thrust sizing (vehicle-design engine-sizing). Component
efficiencies are constant-gamma isentropic forms on the module gas
constants only. Single-layer ISA troposphere only. The mixing model is
the standard equal-static-pressure constant-area mixer idealization of
design-point cycle analysis; mixer entry is subsonic on both streams by
construction (ValueError when the derived core entry Mach reaches 1).

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG. Module constants:
GAMMA_C = 1.4 (cold air), KAPPA_C = (GAMMA_C - 1)/GAMMA_C = 2/7;
GAMMA_G = 4/3 (hot gas), KAPPA_G = (GAMMA_G - 1)/GAMMA_G = 1/4;
CP_C = 1005.0 J/(kg K), CP_G = 1150.0 J/(kg K); R_C = CP_C*KAPPA_C
(287.142857), R_G = CP_G*KAPPA_G (287.5); LHV = 43.0e6 J/kg; ISA
constants ISA_SEA_T = 288.15 K, ISA_SEA_P = 101325.0 Pa, ISA_LAPSE =
0.0065 K/m, ISA_R = 287.0, G0 = 9.80665, ISA_EXP = G0/(ISA_R*ISA_LAPSE)
(about 5.25588), ALT_TROP = 11000.0 m, LBF_PER_HR = 3600.0*G0 (35303.9).
Bisection constants BISECT_TOL = 1e-12, BISECT_MAX = 200. OPR is the
turbomachinery ratio from the fan face (opr = pt3/pt2 = fpr*lpc_pr*
hpc_pr); station 13 is the fan discharge for BOTH streams.

Defining relations (pin these exactly; every function below derives from
them):
- Ram traverse: v0 = mach*sqrt(GAMMA_C*R_C*t0); tt0 = t0*(1 + 0.5*
  (GAMMA_C - 1)*mach^2); pt0 = p0*(tt0/t0)^(1/KAPPA_C).
- Diffuser: tt2 = tt0; pt2 = p0*(1 + eta_d*(tt0/t0 - 1))^(1/KAPPA_C).
- Cold compressor at isentropic efficiency eta: tt_s = tt_in*pr^KAPPA_C;
  tt_out = tt_in + (tt_s - tt_in)/eta; pt_out = pt_in*pr.
- Burner: f = CP_C*(tt4 - tt3)/(eta_b*LHV); pt4 = pt3.
- HP spool: CP_G*(tt4 - tt45) = CP_C*(tt3 - tt25) (per unit core air).
- LP spool (sibling convention): CP_G*(tt45 - tt5) = CP_C*((1 + bpr)*
  (tt13 - tt2) + (tt25 - tt13)) per unit core air.
- Turbine expansion at eta: tt_s = tt_in - (tt_in - tt_out)/eta;
  pt_out = pt_in*(tt_s/tt_in)^(1/KAPPA_G).
- Mass flows per unit core air: m_fan = bpr, m_core = 1 + f,
  m_total = bpr + 1 + f. The fuel mass rides the core through the mixer
  and the common nozzle (energy and thrust bookkeeping use m_core and
  m_total), while the LP spool balance keeps the sibling's per-unit-core
  convention.
- Fan duct: tt16 = tt13; pt16 = pt13*pi_duct.
- Mixer entry (equal static PRESSURE plane, static temperatures differ):
  p_s = pt16/(1 + 0.5*(GAMMA_C - 1)*M_fan_entry^2)^(GAMMA_C/(GAMMA_C - 1));
  core entry Mach M_g from pt5/p_s by the subsonic isentropic root;
  T_s_f and T_s_g from each stream's total temperature at its entry
  Mach; v = M*sqrt(gamma*R*T_s); entry areas A = m*R*T_s/(p_s*v);
  duct area A = A_f + A_g.
- Mixed gas: cp_mix = (m_f*CP_C + m_g*CP_G)/m_total;
  r_mix = (m_f*R_C + m_g*R_G)/m_total; gamma_mix = cp_mix/(cp_mix -
  r_mix).
- Energy: tt_mix = (m_f*CP_C*tt16 + m_g*CP_G*tt5)/(m_total*cp_mix).
- Momentum (constant area): m_total*v_exit + p_exit*A = m_f*v_f + m_g*
  v_g + p_s*A with the exit static pressure from continuity p_exit =
  m_total*r_mix*T_s_exit/(A*v_exit) and T_s_exit = tt_mix -
  v_exit^2/(2*cp_mix); solved by bisection on v_exit over the FIRST
  (subsonic) sign change of the residual in (0, sqrt(2*cp_mix*tt_mix)).
  M_exit = v_exit/sqrt(gamma_mix*r_mix*T_s_exit); pt_mix = p_exit*(1 +
  0.5*(gamma_mix - 1)*M_exit^2)^(gamma_mix/(gamma_mix - 1)).
- Mixing loss ratio: pt_mix/pt_tw with pt_tw = (m_f*pt16 + m_g*pt5)/
  m_total (mass-weighted entry total pressure; the ratio is below 1 when
  the entry velocities differ - the momentum mixing loss).
- Common nozzle: convergent nozzle on the mixed stream with the
  mixed-state gamma/cp/R and the nozzle velocity coefficient cv; choked
  when npr >= ((gamma+1)/2)^(gamma/(gamma-1)); exit velocity v_exit_nozz
  = cv*sqrt(2*cp*(tt_mix - Te)); exit-plane area per unit mass flow
  a_by_mdot = r_mix*Te/(pe*v_exit_nozz).
- Net thrust: F = m_total*(v_exit_nozz - v0) + (pe - p0)*A9 with A9 =
  a_by_mdot*m_total. TSFC = f/F per unit core air (fuel flow f per unit
  core air).
- Separate-exhaust baseline: the same traverse with two per-stream
  convergent nozzles (fan nozzle on (tt13, pt13) cold, core nozzle on
  (tt5, pt5) hot) and F_sep = F_fan + F_core; the comparison reports the
  F ratio and TSFC ratio.

Functions (with ValueError rejections as listed; no imports beyond
math):
- isa_atmosphere(altitude) -> (t0, p0): troposphere. ValueError if
  altitude outside [0, 11000].
- freestream_state(t0, p0, mach) -> (v0, tt0, pt0). ValueError if
  t0/p0 <= 0 or mach < 0.
- diffuser_state(tt0, t0, p0, eta_d) -> (tt2, pt2). ValueError if
  eta_d not in (0, 1] or states non-positive.
- cold_compressor(tt_in, pt_in, pr, eta) -> (tt_out, pt_out). ValueError
  if pr < 1 or eta out of range.
- burner_far(tt3, tt4, eta_b) -> f. ValueError if tt4 <= tt3.
- hp_spool(tt3, tt25, tt4, eta_hpt) -> tt45. ValueError if tt45 <= 0.
- lp_spool(tt45, tt2, tt13, tt25, bpr, eta_lpt) -> tt5. ValueError if
  tt5 <= 0 or bpr < 0.
- turbine_expansion(tt_in, tt_out, pt_in, eta) -> pt_out. ValueError if
  tt_out >= tt_in.
- design_point_traverse(mach, altitude, opr, fpr, bpr, lpc_pr, tt4,
  eta_d, eta_fan, eta_bst, eta_hpc, eta_b, eta_hpt, eta_lpt) -> dict of
  the station total states (tt2/pt2, tt13/pt13, tt25/pt25, tt3/pt3,
  tt45/pt45, tt5/pt5), f, m_fan, m_core, m_total, hpc_pr and the
  freestream state. ValueError if opr < fpr or hpc_pr < 1 or any
  efficiency out of (0, 1].
- mixing_state(tt_f, pt_f, gamma_f, cp_f, r_f, m_f, tt_g, pt_g, gamma_g,
  cp_g, r_g, m_g, m_fan_entry=0.3) -> dict with p_s, mach_f, mach_g,
  T_s_f, T_s_g, v_f, v_g, A_f, A_g, A, tt_mix, cp_mix, r_mix, gamma_mix,
  v_exit, p_exit, M_exit, T_s_exit, pt_mix, pt_tw, mixing_loss_ratio.
  ValueError if a mass flow is negative, m_fan_entry outside (0, 1), the
  core entry Mach reaches 1 (reduce m_fan_entry), or the momentum
  balance has no subsonic root.
- common_nozzle(tt, pt, p_amb, gamma, cp, r, cv) -> dict with choked,
  Me, Te, pe, v_ideal, v_exit, a_by_mdot. ValueError if cv out of
  (0, 1] or states non-positive.
- net_thrust(mdot, v_exit, v0, pe, p0, a_by_mdot) -> F. ValueError if
  mdot <= 0.

Identities to test (closed form, from the real anchor outputs):
- isa_atmosphere(0) = (288.15, 101325.0) exactly; freestream at
  sea-level static (mach 0) returns v0 = 0 and tt0 = t0.
- Traverse closure: opr = fpr*lpc_pr*hpc_pr with the returned hpc_pr
  (real anchor: 24 = 4.0*1.6*3.75); f from the burner energy balance
  closes tt4 exactly; m_core = 1 + f and m_total = bpr + m_core (real
  anchor f = 0.025099, m_core = 1.025099, m_total = 1.625099 at the
  worked point).
- Mixer energy: tt_mix = 992.152327 K at the worked point; cp_mix
  1096.4648, r_mix 287.368140, gamma_mix 1.355172 (real anchor); the
  mass-weighted cp/r identities hold exactly.
- Mixing loss: pt_mix 195867.8819 Pa vs pt_tw 207854.6290 Pa gives
  mixing_loss_ratio 0.942331 (real anchor); the loss is below 1 because
  the entry velocities differ (v_f 117.0737 vs v_g 625.0169 m/s).
- Momentum root: M_exit = 0.591555 subsonic on the first branch
  (real anchor); the residual changes sign once below v_hi.
- Common nozzle choked: npr at the worked point exceeds the critical
  ratio, choked = True, Me = 1 exactly; v_exit 564.216238 m/s = cv*
  v_ideal with cv = 0.985.
- Mixed vs separate: F ratio 1.056083 and TSFC ratio 0.946895 (real
  anchor) - the mixed configuration at this low-BPR point beats the
  separate-exhaust baseline on both thrust and SFC (the two jets have
  very different velocities: fan v19 354.044 vs core v9 644.348 m/s).
- ValueErrors across the module: isa_atmosphere at -1 and 12000 m;
  freestream_state at mach -0.1; diffuser_state at eta_d 0;
  cold_compressor at pr 0.9; burner_far at tt4 == tt3; design_point_
  traverse at opr 3 < fpr 4; mixing_state at m_f negative and at
  m_fan_entry 1.5; common_nozzle at cv 0.
- Determinism: no imports beyond math; constants fixed; the bisection
  loops are fixed-iteration deterministic (no RNG anywhere).

## Worked example

Low-BPR military-style mixed-flow turbofan at Mach 0.85, 10668 m:
OPR 24 (fan 4.0, booster 1.6, HPC 3.75), BPR 0.6, Tt4 = 1750 K;
eta_d 0.97, eta_fan 0.90, eta_bst 0.89, eta_hpc 0.88, eta_b 0.995,
eta_hpt 0.90, eta_lpt 0.91, cv 0.985, pi_duct 0.98, M_fan_entry 0.3.
All values below are REAL outputs of the prep anchor
/tmp/w44spec/anchor_mixedflow.py (stdlib math, closed form).
- Atmosphere: troposphere at 10668 m: t0 = 288.15 - 0.0065*10668 =
  218.81 K, p0 = 23835.9 Pa, v0 = 252.0946 m/s.
- Traverse (per unit core air): tt2 250.4258 K, pt2 37724.0983 Pa;
  tt13 385.6541 K, pt13 150896.3931 Pa; tt25 447.9310 K, pt25
  241434.2290 Pa; tt3 681.4885 K, pt3 905378.3586 Pa; tt45 1545.8911 K,
  pt45 519660.4508 Pa; tt5 1302.3820 K, pt5 242959.2421 Pa;
  f 0.025099, m_fan 0.600, m_core 1.025099, m_total 1.625099.
- Fan duct: tt16 385.6541 K, pt16 147878.4652 Pa (pi_duct 0.98).
- Mixer: p_s 138927.3372 Pa with fan entry Mach 0.3000 and core entry
  Mach 0.9486; fan stream T_s 378.8350 K, v 117.0737 m/s, A 0.004013 m2;
  core stream T_s 1132.5358 K, v 625.0169 m/s, A 0.003844 m2; duct area
  0.007857 m2. Mixed state tt_mix 992.152327 K, cp_mix 1096.4648,
  r_mix 287.368140, gamma_mix 1.355172; exit v 356.787259 m/s, p_exit
  155617.8612 Pa, M_exit 0.591555, T_s_exit 934.103428 K; pt_mix
  195867.8819 Pa, pt_tw 207854.6290 Pa, mixing_loss_ratio 0.942331.
- Common nozzle: choked, Me 1.0, Te 842.530824 K, pe 104975.5711 Pa,
  v_ideal 572.808364 m/s, v_exit 564.216238 m/s, A/mdot 0.004088.
- Mixed net thrust F 1046.246808 N per unit core air (106.687 lbf per
  kg/s core), TSFC 0.0000240 kg/(N s) = 0.8469 lbm/(lbf hr).
- Separate-exhaust baseline from the same traverse: fan nozzle v19
  354.044292 m/s (choked), core nozzle v9 644.347748 m/s (choked),
  F_sep 990.685872 N, TSFC_sep 0.0000253 kg/(N s) = 0.8944 lbm/(lbf hr).
- Comparison: F ratio 1.056083, TSFC ratio 0.946895 - the mixed exhaust
  gains 5.6 percent thrust and 5.3 percent SFC at this low-BPR point
  (mixing equalizes the very different jet velocities: 354 vs 644 m/s).

## Validation list (deterministic checks the contract test must run)

1. Module import + constants match the spec values (GAMMA_C 1.4, CP_C
   1005.0, R_C 287.142857, LBF_PER_HR 35303.9 within tolerance).
2. isa_atmosphere(0) == (288.15, 101325.0) exact.
3. Traverse closure identities: opr == fpr*lpc_pr*hpc_pr; m_core == 1 +
   f; m_total == bpr + m_core.
4. Worked-example station states within 1e-6 relative of the anchor
   outputs (spot-check tt5 1302.3820 K, pt5 242959.2421 Pa, f
   0.025099).
5. Mixer: p_s, entry Mach numbers, tt_mix, pt_mix, mixing_loss_ratio
   within 1e-6 relative of the anchor outputs (0.942331); M_exit
   subsonic on the first branch (0.591555).
6. Common nozzle choked with Me == 1 at the worked point; v_exit =
   cv*v_ideal exactly (ratio 0.985).
7. F and TSFC match the anchor (1046.246808 N, 0.0000240 kg/(N s));
   F ratio 1.056083 and TSFC ratio 0.946895 against the baseline.
8. All ValueErrors listed under Identities fire.
9. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
   ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
   computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (2 verbatim queries for eval/hit1-wave44-mixed-flow-
exhaust.yaml)

1. "compute the mixed total temperature and pressure of a low bypass
   ratio turbofan mixing exhaust by the constant area mixer energy and
   momentum balance and size the common choked nozzle for the mixed
   stream" (routes on mixed-flow-exhaust, exhaust-mixer, common-nozzle,
   mixing-loss tokens)
2. "compare the mixed flow exhaust net thrust and TSFC of a two stream
   turbofan against the separate exhaust baseline at the design point"
   (routes on mixed-flow-exhaust, mixed-vs-separate comparison tokens)
intent lines: "propulsion; two-stream turbofan mixing exhaust design
point with the constant-area mixer and common nozzle" and "propulsion;
mixed-flow vs separate-exhaust F and TSFC comparison at a low-BPR design
point".

## Description/tag guidance for the builder

- Description: "Use when you must compute the two-stream turbofan design
  point with a mixing exhaust: traverse the fan and core streams to the
  mixer entry, close the constant-area mixer by the energy and momentum
  balance over the two streams' total states to the mixed total
  temperature and pressure with the mixing loss, expand the mixed stream
  through the common convergent nozzle, and report the net thrust and
  TSFC of the mixed-flow configuration against the separate-exhaust
  baseline. Produces the mixed total state, the mixer pressure loss
  ratio, the common-nozzle exit velocity, net thrust and TSFC, and the
  mixed-vs-separate comparison that gate the exhaust-configuration
  decision. Trigger: mixed-flow exhaust, turbofan mixing exhaust,
  constant-area mixer, common nozzle, mixing loss, exhaust mixer, low
  bypass ratio mixed turbofan." (<=1000 chars, <=148 words; draft at
  ~920 chars.)
- metadata tags: [mixed-flow-exhaust, turbofan-mixing-exhaust, constant-
  area-mixer, exhaust-mixer, common-nozzle, mixing-loss, mixed-vs-
  separate-exhaust]
- FORBIDDEN tokens (sibling claims): separate-exhaust-cycle (except in
  the baseline comparison phrase "separate-exhaust baseline"),
  reheat-fuel-flow-for-the-core-mass-flow (afterburner-cycle), thrust-
  split-between-the-fan-and-core-streams (bypass-ratio-trade),
  single-stream choked nozzle sizing as the OUTPUT (propelling-nozzle).
- ZERO em dashes in every file; never the word "classified" in prose.
- Standards reference-only: far-33 named + paraphrased, never reproduced.
