---
name: mixed-flow-exhaust
description: "Use when you must compute the two-stream turbofan design point with a mixing exhaust: traverse the fan and core streams to the mixer entry, close the constant-area mixer by the energy and momentum balance over the two streams' total states to the mixed total temperature and pressure with the mixing loss, expand the mixed stream through the common convergent nozzle, and report the net thrust and TSFC of the mixed-flow configuration against the separate-exhaust baseline. Produces the mixed total state, the mixer pressure loss ratio, the common-nozzle exit velocity, net thrust and TSFC, and the mixed-vs-separate comparison that gate the exhaust-configuration decision. Trigger: mixed-flow exhaust, turbofan mixing exhaust, constant-area mixer, common nozzle, mixing loss, exhaust mixer, low bypass ratio mixed turbofan."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: turbofan
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: turbofan
  tags: [mixed-flow-exhaust, turbofan-mixing-exhaust, constant-area-mixer, exhaust-mixer, common-nozzle, mixing-loss, mixed-vs-separate-exhaust]
  version: 0.1.0
  author: AeroSkills
---

# Mixed-Flow Exhaust (propulsion/turbofan/mixed-flow-exhaust)

Use when the task is the two-stream turbofan design point with a MIXING
(common) exhaust: the fan and core streams are traversed to the mixer
entry plane, the constant-area mixer is closed by the energy and momentum
balances over the two streams' total states, and the mixed stream expands
through ONE common convergent nozzle. This leaf produces the mixed total
temperature and pressure with the mixing loss ratio, the common-nozzle
exit velocity and pressure term, the net thrust and TSFC of the mixed-flow
configuration, and the same-traverse separate-exhaust baseline whose F and
TSFC comparison gates the mixed-vs-separate exhaust decision at a low-BPR
operating point. It is the exhaust-configuration partner of the
separate-exhaust design point leaf in this pack: the sibling
turbofan-design-point computes the same station chain but explicitly
disclaims mixed-stream configurations, and this leaf returns the favor by
using the separate-exhaust layout only as the comparison baseline, not as
its output. Pure Python, stdlib only (math), constant-gamma isentropic
component forms, single-layer ISA troposphere, deterministic.

## Domain quick reference

- Ram traverse: v0 = mach*sqrt(GAMMA_C*R_C*t0); tt0 = t0*(1 + 0.5*
  (GAMMA_C-1)*mach^2); pt0 = p0*(tt0/t0)^(1/KAPPA_C).
- Diffuser: tt2 = tt0; pt2 = p0*(1 + eta_d*(tt0/t0 - 1))^(1/KAPPA_C).
- Cold compressor (fan, booster, HPC) at isentropic efficiency eta:
  tt_s = tt_in*pr^KAPPA_C; tt_out = tt_in + (tt_s - tt_in)/eta;
  pt_out = pt_in*pr.
- Burner: f = CP_C*(tt4 - tt3)/(eta_b*LHV); pt4 = pt3.
- HP spool per unit core air: CP_G*(tt4 - tt45) = CP_C*(tt3 - tt25).
- LP spool per unit core air: CP_G*(tt45 - tt5) = CP_C*((1 + bpr)*
  (tt13 - tt2) + (tt25 - tt13)).
- Turbine expansion at eta: tt_s = tt_in - (tt_in - tt_out)/eta;
  pt_out = pt_in*(tt_s/tt_in)^(1/KAPPA_G).
- Mass flows per unit core air: m_fan = bpr, m_core = 1 + f,
  m_total = bpr + 1 + f; the fuel mass rides the core through the mixer
  and common nozzle.
- Fan duct: tt16 = tt13; pt16 = pi_duct*pt13.
- Mixer entry at the equal static PRESSURE plane: p_s = pt16/(1 + 0.5*
  (GAMMA_C-1)*M_fan_entry^2)^(GAMMA_C/(GAMMA_C-1)); the core entry Mach
  is the subsonic isentropic root at p_s; entry areas follow from
  continuity A = m*R*T_s/(p_s*v).
- Mixed gas: cp_mix, r_mix mass-weighted; gamma_mix = cp_mix/(cp_mix -
  r_mix); energy gives tt_mix; the constant-area momentum balance
  m_total*v_exit + p_exit*A = m_f*v_f + m_g*v_g + p_s*A with p_exit from
  continuity closes on the FIRST (subsonic) root by bisection.
- Mixing loss ratio: pt_mix/pt_tw below 1 when the entry velocities
  differ, with pt_tw the mass-weighted entry total pressure.
- Common convergent nozzle on the mixed stream: choked when npr >=
  ((gamma+1)/2)^(gamma/(gamma-1)); v_exit = cv*sqrt(2*cp*(tt_mix - Te));
  a_by_mdot = r*Te/(pe*v_exit).
- Net thrust: F = m_total*(v_exit_nozz - v0) + (pe - p0)*A9; TSFC = f/F
  per unit core air. kg/(N s) converts to lbm/(lbf hr) via
  LBF_PER_HR = 3600*G0 = 35303.94.
- Gas constants: GAMMA_C 1.4, CP_C 1005, R_C 287.142857; GAMMA_G 4/3,
  CP_G 1150, R_G 287.5. 14 CFR Part 33 (far-33) frames the engine
  certification context (reference-only); the relations are standard
  cycle-analysis methodology, summary-only.

## Workflow

1. Fix the operating point: mach, altitude (ISA troposphere, 0-11000 m),
   OPR with opr = fpr*lpc_pr*hpc_pr, BPR, Tt4, the component efficiencies
   eta_d/eta_fan/eta_bst/eta_hpc/eta_b/eta_hpt/eta_lpt, the nozzle
   velocity coefficient cv, the duct pressure ratio pi_duct and the
   fan-stream mixer entry Mach M_fan_entry in (0, 1).
2. Get the atmosphere and freestream: isa_atmosphere then
   freestream_state for t0, p0, v0, tt0, pt0.
3. Traverse the station chain 0-2-13-2.5-3-4-4.5-5 with
   design_point_traverse (fan on both streams, booster and HPC on the
   core, burner, HPT, LPT) and confirm the closure identities
   opr == fpr*lpc_pr*hpc_pr, m_core == 1 + f and m_total == bpr + m_core.
4. Carry the bypass stream through the fan duct to the mixer entry:
   station 16 with tt16 = tt13 and pt16 = pi_duct*pt13.
5. Close the constant-area mixer with mixing_state on the two entry total
   states (fan stream cold, core stream hot, mass flows per unit core
   air) at M_fan_entry: read p_s, the core entry Mach, the entry
   velocities and areas, the mixed total temperature tt_mix, the mixed
   exit state on the first subsonic momentum-balance root, and the mixing
   loss ratio pt_mix/pt_tw.
6. Expand the mixed stream through the common convergent nozzle with
   common_nozzle using the mixed gamma/cp/r and cv: choked check, exit
   velocity and the exit-plane area per unit mass flow.
7. Compute the net thrust with net_thrust and the TSFC = f/F per unit
   core air for the mixed-flow configuration.
8. Build the separate-exhaust baseline from the same traverse: two
   per-stream convergent nozzles (fan nozzle on tt13/pt13 cold, core
   nozzle on tt5/pt5 hot), F_sep = F_fan + F_core, and report the F ratio
   and TSFC ratio that gate the mixed-vs-separate exhaust decision.
9. Confirm the deterministic checks with the contract test
   scripts/test_mixed_flow_exhaust.py (offline, stdlib unittest).

## Worked example

Low-BPR military-style mixed-flow turbofan at Mach 0.85 and 10668 m:
OPR 24 (fan 4.0, booster 1.6, HPC 3.75), BPR 0.6, Tt4 = 1750 K;
eta_d 0.97, eta_fan 0.90, eta_bst 0.89, eta_hpc 0.88, eta_b 0.995,
eta_hpt 0.90, eta_lpt 0.91, cv 0.985, pi_duct 0.98, M_fan_entry 0.3.
All values are the real module outputs.

- Atmosphere and freestream: t0 = 218.808 K, p0 = 23835.9 Pa,
  v0 = 252.0946 m/s.
- Traverse per unit core air: tt2 250.4258 K, pt2 37724.0983 Pa;
  tt13 385.6541 K, pt13 150896.3931 Pa; tt25 447.9310 K,
  pt25 241434.2290 Pa; tt3 681.4885 K, pt3 905378.3586 Pa;
  tt45 1545.8911 K, pt45 519660.4508 Pa; tt5 1302.3820 K,
  pt5 242959.2421 Pa; f 0.025099; m_fan 0.600, m_core 1.025099,
  m_total 1.625099; hpc_pr 3.75.
- Fan duct: tt16 385.6541 K, pt16 147878.4652 Pa.
- Mixer: p_s 138927.3372 Pa at fan entry Mach 0.3000, core entry Mach
  0.9486; fan stream T_s 378.8350 K, v 117.0737 m/s, A 0.004013 m2;
  core stream T_s 1132.5358 K, v 625.0169 m/s, A 0.003844 m2; duct area
  0.007857 m2. Mixed state tt_mix 992.1523 K, cp_mix 1096.4648,
  r_mix 287.3681, gamma_mix 1.35517; exit v 356.7873 m/s,
  p_exit 155617.86 Pa, M_exit 0.591555 subsonic on the first branch,
  T_s_exit 934.1034 K; pt_mix 195867.88 Pa against pt_tw 207854.63 Pa,
  mixing_loss_ratio 0.942331 (below 1 because the entry velocities
  differ, v_f 117 vs v_g 625 m/s).
- Common nozzle: choked, Me 1.0, Te 842.5308 K, pe 104975.57 Pa,
  v_ideal 572.8084 m/s, v_exit 564.2162 m/s = cv*v_ideal, A/mdot
  0.004088.
- Mixed-flow net thrust 1046.247 N per unit core air (106.7 lbf per
  kg/s core) and TSFC 2.40e-5 kg/(N s) = 0.847 lbm/(lbf hr).
- Separate-exhaust baseline from the same traverse: fan nozzle v19
  354.044 m/s (choked), core nozzle v9 644.348 m/s (choked),
  F_sep 990.686 N, TSFC_sep 2.53e-5 kg/(N s) = 0.894 lbm/(lbf hr).
- Comparison: F ratio 1.056083 and TSFC ratio 0.946895: the mixed
  configuration gains about 5.6 percent thrust and 5.3 percent SFC at
  this low-BPR point, because mixing equalizes the very different jet
  velocities (354 vs 644 m/s).

## Verification

- Confirm isa_atmosphere(0) returns (288.15, 101325.0) exactly and the
  freestream at sea-level static (mach 0) gives v0 = 0, tt0 = t0.
- Confirm the traverse closures: opr = fpr*lpc_pr*hpc_pr = 24, f from the
  burner energy balance closes tt4 = 1750 K, m_core = 1 + f and
  m_total = bpr + m_core.
- Confirm the mixer energy result tt_mix = 992.1523 K and the
  mass-weighted cp_mix/r_mix identities hold exactly; the momentum
  residual m_total*v + p*A = m_f*v_f + m_g*v_g + p_s*A closes at
  M_exit = 0.591555 on the first subsonic branch.
- Confirm the mixing loss ratio 0.942331 stays below 1 (momentum mixing
  loss when the entry velocities differ).
- Confirm the common nozzle is choked at the worked point with Me = 1
  and v_exit = cv*v_ideal (ratio 0.985 exactly).
- Confirm F and TSFC (1046.247 N, 2.40e-5 kg/(N s)) and the comparison
  ratios F 1.056083 and TSFC 0.946895 against the separate-exhaust
  baseline.
- Confirm every non-physical input raises ValueError: altitude outside
  [0, 11000] m, negative mach, efficiencies and cv outside (0, 1],
  pressure ratios below 1, tt4 <= tt3, opr < fpr, hpc_pr < 1, negative
  mass flows, m_fan_entry outside (0, 1), a core entry Mach reaching 1
  (reduce m_fan_entry), a momentum balance with no subsonic root, and
  non-positive nozzle states or mass flow.
- Run the contract test offline under both interpreters:
  python3 scripts/test_mixed_flow_exhaust.py and
  ~/.pyenv/versions/3.13.12/bin/python3 scripts/test_mixed_flow_exhaust.py
  (56 tests, deterministic).

## Related leaves

- propulsion/turbofan/turbofan-design-point: the separate-exhaust design
  point on the same station chain; the per-stream nozzle bookkeeping
  this leaf reuses only as the comparison baseline.
- propulsion/turbofan/turbofan-cycle: the one-stream cycle context and
  mass-flow/jet-velocity inputs.
- propulsion/turbofan/bypass-ratio-trade: the bypass-ratio thrust split
  at the velocity level for the trade sweep.
- propulsion/turbofan/turbofan-off-design: off-design matching and
  throttle behavior, explicitly outside this leaf's design-point scope.
- propulsion/gas-turbine-cycle/afterburner-cycle: core-only reheat, no
  fan stream or mixer.
- propulsion/gas-turbine-cycle/propelling-nozzle: single-stream choked
  convergent nozzle sizing; the common-nozzle step here uses the same
  choked/unchoked relations on the mixed stream.

## Pitfalls

- Reporting the mixed total state without the momentum balance: the
  energy balance alone gives tt_mix; pt_mix must come from the
  constant-area momentum balance on the first subsonic root, and the
  mixing loss ratio pt_mix/pt_tw falls below 1 only when the entry
  velocities differ (0.9423 at the worked point).
- Feeding the entry total pressures into the loss bookkeeping as the
  mixed total pressure: pt_tw is the mass-weighted entry total pressure
  (207854.6 Pa at the worked point), and pt_mix (195867.9 Pa) sits below
  it by the momentum mixing loss, not above any single stream value.
- Assuming the mixer entry Mach on the core stream: the design input is
  the fan-stream entry Mach M_fan_entry; the core entry Mach is DERIVED
  from the equal static pressure plane (0.9486 at the worked point) and
  reaches 1 when the fan entry Mach is pushed too high, which raises
  ValueError (reduce M_fan_entry).
- Reading the separate-exhaust sibling's output as this leaf's model:
  turbofan-design-point owns the separate-exhaust per-stream nozzle
  output; here the per-stream nozzles appear only as the comparison
  baseline that produces the F and TSFC ratios.
- Treating the mixed nozzle as a second mixer stream: after the mixer
  there is ONE common convergent nozzle on the mixed stream with the
  mixed gamma/cp/r, sized by the same choked/unchoked relations as
  propelling-nozzle but never on two streams at once.
- Using variable specific heats or turbine cooling: all component forms
  are constant-gamma isentropic on the module gas constants only; real
  cycle effects and the nozzle throat AREA sizing for arbitrary entry
  states belong to other leaves.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_mixed_flow_exhaust.py

The test covers the module constants, the atmosphere and freestream step
at sea level and at the worked altitude, the diffuser and cold
compression steps, the burner fuel-to-air ratio and its energy closure,
the HP and LP spool work balances, the turbine expansion pressures, the
full station traverse with the opr-product and mass-flow closure
identities, the fan duct carry, the mixer entry plane with the derived
core entry Mach and the continuity areas, the mixed gas properties, the
energy balance, the momentum-balance subsonic root, the total pressure
loss ratio, the common nozzle choked and unchoked regimes with the
velocity coefficient round trip, the net thrust and TSFC at the worked
point, the separate-exhaust baseline, the mixed-vs-separate F and TSFC
ratio comparison, the full ValueError rejection list, and the
determinism checks (no RNG, repeat runs identical).

## Compliance

- Standards referenced, not reproduced: 14 CFR Part 33 (far-33) is named
  as the engine certification frame; the cycle relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
