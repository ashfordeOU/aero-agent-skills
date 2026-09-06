---
name: turbofan-design-point
description: "Use when you must compute the two-stream turbofan design point at flight Mach and altitude: traverse the fan-stream-station-states and the core stream of the separate-exhaust-cycle down the 0-2-13-2.5-3-4-4.5-5-9/19 station chain from the overall pressure ratio, the turbine-inlet temperature, the bypass ratio and the fan pressure ratio with the component efficiencies; close the two-spool-work-balance of the high-pressure compressor on the HP turbine and of the fan plus booster on the LP turbine; and report the burner fuel-air ratio, the per-stream nozzle exit velocities with the choked pressure terms, and the net thrust and TSFC of the separate-exhaust turbofan. Produces the station total states, the spool works, the jet velocities, the net thrust and the TSFC, in SI units, that gate the engine design-point assessment. Trigger: turbofan design point, two-spool engine cycle, fan stream station states, separate exhaust cycle, overall pressure ratio, fuel-air ratio, net thrust and tsfc."
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
  tags: [turbofan-design-point, fan-stream-station-states, two-spool-work-balance, separate-exhaust-cycle, hp-and-lp-turbine-matching]
  version: 0.1.0
  author: AeroSkills
---

# Turbofan Design Point (propulsion/turbofan/turbofan-design-point)

Use when the task is the two-stream turbofan design point at flight Mach
number and altitude: the separate-exhaust-cycle that produces the mass
flows and jet velocities the momentum-method consumers take as given.
This leaf traverses the full station chain 0-2-13-2.5-3-4-4.5-5-9/19
(0 freestream static, 2 fan face, 13 fan exit common to both streams,
2.5 booster exit, 3 HPC exit, 4 turbine inlet Tt4, 4.5 HPT exit, 5 LPT
exit, 9 core-nozzle exit, 19 fan-nozzle exit), closes the overall
pressure ratio and both spool work balances, and reports the station
total states, the burner fuel/air ratio, the per-stream nozzle exit
velocities and the net thrust and TSFC of the separate-exhaust turbofan.
It implements the model in pure Python, stdlib only (math).

It is the producer that propulsion/turbofan/turbofan-cycle (bypass
ratio, propulsive efficiency and specific thrust from mass flows and jet
velocities GIVEN as inputs) and propulsion/turbofan/bypass-ratio-trade
(the thrust split and TSFC trade at fixed core and jet conditions)
consume. It is the two-stream, two-spool generalization of the single-
stream propulsion/gas-turbine-cycle/turbojet-cycle core cycle.

## Domain quick reference

Units are SI: temperature K, pressure Pa, mass flow kg/s, velocity m/s,
thrust N, fuel/air ratio kg fuel per kg air, TSFC kg/(N s) (also given
in lb/(lbf hr)). Module constants: GAMMA_C = 1.4 (KAPPA_C = 2/7),
GAMMA_G = 4/3 (KAPPA_G = 1/4), CP_C = 1005.0 J/(kg K), CP_G = 1150.0
J/(kg K), R_C = CP_C*KAPPA_C = 287.142857, R_G = CP_G*KAPPA_G = 287.5
J/(kg K), LHV = 43.0e6 J/kg.

- Ram traverse: v0 = mach*sqrt(GAMMA_C*R_C*t0); tt0 = t0*(1 + 0.5*
  (GAMMA_C - 1)*mach^2); pt0 = p0*(tt0/t0)**(1/KAPPA_C).
- Diffuser: tt2 = tt0; pt2 = p0*(1 + eta_d*(tt0/t0 - 1))**(1/KAPPA_C)
  from the ambient STATIC pressure p0 (equals pt0 at eta_d = 1).
- Cold compressor (fan, booster, HPC): tt_s = tt_in*pr**KAPPA_C;
  tt_out = tt_in + (tt_s - tt_in)/eta; pt_out = pt_in*pr.
- OPR closure: opr = pt3/pt2 = fpr*lpc_pr*hpc_pr, so hpc_pr =
  opr/(fpr*lpc_pr). Station 13 feeds BOTH streams; the bypass stream
  runs loss-free to the fan nozzle.
- Burner: f = cp_c*(tt4 - tt3)/(eta_b*lhv); pt4 = pt3 (no combustor
  pressure loss).
- HP spool balance: cp_g*(tt4 - tt45) = cp_c*(tt3 - tt25). The HPT
  drives only the HPC (per unit core air).
- LP spool balance: cp_g*(tt45 - tt5) = cp_c*((1 + bpr)*(tt13 - tt2) +
  (tt25 - tt13)). The fan term carries the (1 + bpr) multiplier, the
  signature of the two-spool-work-balance: the LPT drives the fan on
  the bypass stream AND the core stream, plus the booster.
- Turbine: tt_s = tt_in - (tt_in - tt_out)/eta; pt_out/pt_in =
  (tt_s/tt_in)**(1/KAPPA_G).
- Nozzle: npr = pt_in/p_amb; choked when npr >= critical =
  ((gamma+1)/2)**(gamma/(gamma-1)) (1.892929 cold, 1.852623 hot).
  Choked: me = 1, te = 2*tt_in/(gamma+1); unchoked: pe = p_amb, te =
  tt_in*(p_amb/pt_in)**((gamma-1)/gamma). Ideal velocity
  sqrt(2*cp*(tt_in - te)); actual ve = cv*v_ideal.
- Exit-plane area for the pressure term: A = mdot*R*te/(pe*ve); the
  pressure term (pe - p0)*A vanishes for an unchoked nozzle (pe = p0).
- Net thrust: F = mdot_core*(v9 - v0) + mdot_fan*(v19 - v0) + (pe9 -
  p0)*A9 + (pe19 - p0)*A19; TSFC = f*mdot_core/F.
- Plausibility: 1 lb/(lbf hr) = 2.8325e-5 kg/(N s); the 0.5-0.7
  lb/(lbf hr) cruise band is 1.416e-5 to 1.983e-5 kg/(N s), 14.16 to
  19.83 mg/(N s), numerically equal to g/(kN s).

## Workflow

1. Fix the operating point: flight mach and altitude, the overall
   pressure ratio opr, the fan pressure ratio fpr, the booster ratio
   lpc_pr, the bypass ratio bpr, the turbine-inlet temperature tt4, the
   core mass flow mdot_core and the component efficiencies (eta_d,
   eta_fan, eta_lpc, eta_hpc, eta_b, eta_hpt, eta_lpt, cv_core, cv_fan).
2. Resolve the ambient and flight state: isa_atmosphere gives the ISA
   static state (t0, p0) at the altitude, then freestream_state runs
   the ram traverse to (v0, tt0, pt0).
3. Traverse the inlet and the fan: diffuser_state gives the fan face
   (tt2, pt2), then compressor_exit_temperature at fpr and eta_fan
   reaches the fan-stream-station-states at station 13 (tt13, pt13).
4. Compress the core stream: the booster takes station 13 to 2.5 at
   lpc_pr, then the HPC takes 2.5 to 3 at hpc_pr = opr/(fpr*lpc_pr),
   closing the OPR at pt3/pt2 = opr.
5. Burn: fuel_air_ratio sets f from the combustor energy balance over
   tt3 to tt4, with pt4 = pt3.
6. Close the HP spool balance: hp_spool_balance sizes the HPT exit
   tt45 so the turbine work cp_g*(tt4 - tt45) drives the HPC demand;
   turbine_pressure_ratio expands the HPT to pt45.
7. Close the LP spool balance: lp_spool_balance sizes the LPT exit tt5
   so the LPT work carries the fan on both streams, cp_c*(1 + bpr)*
   (tt13 - tt2), plus the booster, cp_c*(tt25 - tt13);
   turbine_pressure_ratio expands the LPT to pt5.
8. Exhaust both streams: nozzle_exit traverses the core nozzle (9) from
   the station-5 total state and the fan nozzle (19) from the station-13
   state, each choked or unchoked through its velocity coefficient, and
   the exit areas a9 and a19 come from continuity for the pressure
   terms.
9. Bookkeep the report: turbofan_design_point assembles the station
   total states, ram recovery, f, the mass split (mdot_fan = bpr*
   mdot_core), the four thrust terms, net thrust, specific thrust,
   mdot_fuel and the TSFC round trip tsfc*F = f*mdot_core.
10. Confirm the deterministic checks with the contract test:
    python3 scripts/test_turbofan_design_point.py (stdlib unittest,
    offline).

## Worked example

Representative 2-spool separate-exhaust turbofan at cruise: mach 0.8,
altitude 35000 ft (10668.0 m), opr 36, fpr 1.65, lpc_pr 1.50 (hpc_pr =
36/(1.65*1.5) = 14.545), bpr 8, Tt4 = 1600 K, mdot_core = 1.0 kg/s,
eta_d 0.97, eta_fan 0.90, eta_lpc 0.89, eta_hpc 0.87, eta_b 0.98,
eta_hpt 0.86, eta_lpt 0.86, cv_core 0.98, cv_fan 0.98. Values are REAL
outputs of scripts/turbofan_design_point_logic.py:

- Ambient and flight: t0 = 218.8080 K, p0 = 23835.9189 Pa (ISA 35000
  ft), v0 = 237.2655 m/s; Tt0 = 246.815424 K, Pt0 = 36334.0449 Pa.
- Inlet: Tt2 = 246.815424 K, Pt2 = 35902.9677 Pa, ram recovery
  Pt2/Pt0 = 0.988136.
- Fan stream: Tt13 = 288.999073 K, Pt13 = 59239.8966 Pa = 2.485320*p0.
- Core stream: Tt25 = 328.882329 K, Pt25 = 88859.8449 Pa; Tt3 =
  763.180293 K, Pt3 = 1292506.8354 Pa with Pt3/Pt2 = 36.000000 (the OPR
  closure); Tt4 = 1600 K, Pt4 = Pt3; Tt45 = 1220.461345 K, Pt45 =
  355468.3493 Pa; Tt5 = 853.823275 K, Pt5 = 63721.9051 Pa.
- Burner: f = 0.01995738 kg/kg (about 19.96 g/kg), mdot_fuel =
  0.01995738 kg/s at the 1 kg/s core flow.
- Spool works (J per kg core air): w_hpc = cp_c*(Tt3 - Tt2.5) =
  436469.453 equals w_hpt = cp_g*(Tt4 - Tt4.5) = 436469.453 (relative
  residual 2.667e-16). LP demand = cp_c*(1 + bpr)*(Tt13 - Tt2) +
  cp_c*(Tt25 - Tt13) = 381551.108 + 40082.672 = 421633.780, equal to
  w_lpt = cp_g*(Tt4.5 - Tt5) (residual 1.381e-16).
- Nozzles: core NPR 2.673356 above the hot critical 1.852623, choked
  with Me = 1: Te = 731.8485 K, Pe = 34395.4973 Pa, v_ideal =
  529.6621 m/s, v9 = 519.0689 m/s (cv_core 0.98), A9 = 0.0117851 m^2,
  pressure term 124.445 N. Fan NPR 2.485320 above the cold critical
  1.892929, choked with Me = 1: Te = 240.8326 K, Pe = 31295.3585 Pa,
  v19 = 304.9276 m/s, A19 = 0.0579731 m^2, pressure term 432.447 N.
- Mass flows: mdot_core 1.0, mdot_fan 8.0, mdot_total 9.0 kg/s.
- Thrust: core momentum 281.803 N, fan momentum 541.297 N, core
  pressure 124.445 N, fan pressure 432.447 N, net thrust F =
  1379.992 N (153.332 N per kg/s of total flow); the decomposition sums
  to F with relative residual 0.0.
- TSFC: mdot_fuel/F = 1.446195e-05 kg/(N s) = 14.4619 mg/(N s) =
  14.4619 g/(kN s) = 0.51056 lb/(lbf hr), INSIDE the 0.5-0.7
  lb/(lbf hr) cruise plausibility band; the round trip tsfc*F =
  mdot_fuel holds to float noise.
- Read-off: the fan stream delivers 974 N (momentum plus pressure) of
  the 1380 N total at 8 times the core flow, and the design point
  closes both spool balances to float noise. Fixed-Tt4 trade: at bpr 4
  TSFC is 1.795526e-05 kg/(N s) (0.6339 lb/(lbf hr)) with Tt5
  1001.28 K and v9 562.11 m/s; at bpr 8 it falls to 1.446195e-05; at
  bpr 12 the LP turbine has over-expanded the core, Tt5 falls to
  706.36 K, the core nozzle unchokes and v9 = 63.64 m/s falls below v0,
  so the core stream drags, F falls back to 1286.99 N and TSFC rises to
  1.550704e-05 kg/(N s): the minimum sits between bpr 8 and 12. At
  bpr 40 the LP enthalpy guard raises ValueError.

## Verification

- isa_atmosphere(10668.0) returns (218.8080 K, 23835.9189 Pa); the
  design point closes pt3/pt2 = opr = 36 to 1e-9 relative.
- Both spool balances close below 1e-12 relative at the anchor, the
  HP and LP turbine pressure ratios reproduce Pt45 and Pt5, and the
  station chain stays ordered Tt2 < Tt13 < Tt25 < Tt3 < Tt4 with
  Tt5 < Tt45 < Tt4.
- Both nozzles choke at the anchor (NPR 2.673356 and 2.485320 above
  their critical ratios, Me = 1); the exit areas and pressure terms
  follow continuity, and an unchoked case (bpr 12 core nozzle) expands
  fully with pe = p0.
- Net thrust equals the momentum plus pressure decomposition to 1e-9
  relative; tsfc*net_thrust = mdot_fuel round trips to 1e-9 relative.
- Degenerate bpr 0 keeps the core choked with zero fan terms, and the
  bpr trend through 4-8-12 shows the TSFC minimum with the core
  unchoking past bpr 12.
- ValueErrors reject: altitude outside [0, 11000] m, negative mach,
  eta_d 1.5, compressor pr 1.0 and eta 0, tt3 <= tt25, bpr -1, the LP
  demand reaching tt45 (bpr 40), tt4 <= tt3, eta_b 1.01, tt_out >=
  tt_in, nozzle pt_in <= p_amb and cv 1.01, opr <= fpr*lpc_pr and
  mdot_core 0.
- Two identical runs return byte-identical reports (no RNG, imports
  only math).

## Related leaves

- propulsion/turbofan/turbofan-cycle: momentum-method consumer; bypass
  ratio, propulsive efficiency and net thrust from mass flows and jet
  velocities GIVEN as inputs.
- propulsion/turbofan/bypass-ratio-trade: the fixed-core thrust-split
  and TSFC trade across bypass ratio at constant jet velocities.
- propulsion/turbofan/turbofan-off-design: corrects the rated design
  point away from it; this leaf is the design point those corrections
  are relative to.
- propulsion/gas-turbine-cycle/turbojet-cycle: the single-stream,
  single-spool structural analog; this leaf is its two-stream, two-spool
  generalization.
- propulsion/gas-turbine-cycle/propelling-nozzle: nozzle throat sizing
  and regime decisions for arbitrary entry states; this leaf only
  traverses the pressure ratios the cycle produces.
- propulsion/gas-turbine-cycle/real-cycle-effects and combustor-design:
  combustor pressure loss, variable properties and burner
  thermochemistry are out of scope here.
- propulsion/gas-turbine-cycle/subsonic-inlet-recovery: the inlet
  recovery design analysis; this leaf consumes one eta_d.
- vehicle-design/sizing/engine-sizing: aircraft thrust demand and
  engine selection; this leaf produces cycle output, never aircraft
  sizing.

## Pitfalls

- Reading the OPR from the fan face: opr = pt3/pt2 = fpr*lpc_pr*hpc_pr
  is the turbomachinery ratio from the fan face, not from freestream,
  so hpc_pr = opr/(fpr*lpc_pr) closes the cycle and the ram recovery
  pt2/pt0 sits below 1.
- Forgetting the (1 + bpr) fan multiplier: the LP turbine drives the
  fan on BOTH streams, so the fan term in the LP balance is cp_c*(1 +
  bpr)*(Tt13 - Tt2) per unit core air, and the fan-growth limit at
  fixed Tt4 raises at high bypass ratio (bpr 40).
- Treating the fixed-core TSFC trade as universal: the monotone TSFC
  fall of the bypass-ratio-trade leaf requires jet velocities FIXED as
  inputs; the re-balanced spool model here sheds Tt5 as bpr grows and
  the core nozzle can unchoke and drag (bpr 12), so the TSFC minimum
  sits mid-range.
- Expanding the nozzle against pt_in <= p_amb: with nothing to expand
  the nozzle relation is undefined and the function raises.
- Mixing stream gamma and cp: the core nozzle is hot (GAMMA_G 4/3,
  CP_G 1150) and the fan nozzle cold (GAMMA_C 1.4, CP_C 1005), and each
  exit area uses the stream gas constant R = cp*KAPPA.
- Reading the pressure terms as optional: a choked convergent nozzle
  exits above ambient, and (pe - p0)*A is a real share of the net
  thrust (557 N of 1380 N at the anchor); it only vanishes when the
  nozzle unchokes.
- Nozzle throat sizing and off-design matching belong to the
  propelling-nozzle and turbofan-off-design leaves, not here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_turbofan_design_point.py

The test covers the worked-example anchors (37 tests): the ISA and ram
traverse, the diffuser recovery, the fan-stream-station-states, the
booster and HPC compression with the OPR closure, the burner fuel/air
ratio, the HP and LP spool balance closures with the fan-share term,
the turbine pressure ratios, the choked and unchoked nozzle branches
with the velocity coefficient, the exit areas, the mass split, the
four-term thrust decomposition, the net thrust and specific thrust, the
TSFC round trip inside the cruise plausibility band, the bpr trend with
the core unchoking past bpr 12 and the bpr-40 enthalpy guard, the bpr-0
degenerate case, the ValueError rejections of every non-physical input,
and byte-identical determinism.

## Compliance

- Standards referenced, not reproduced: FAR-33 (14 CFR Part 33) frames
  the aircraft engine design context; the cycle relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
