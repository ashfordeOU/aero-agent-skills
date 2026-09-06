# Wave-42 leaf plan (ops manager, from 5 probe receipts at 58560772)

RECEIPTS OVER LISTS: all 14 planned leaves come from probe receipts
(zero-owner greps + sibling fence reads at HEAD), NOT the CEO candidate
list. Probe batch deleg_85fa5536, 5 read-only agents, all completed
2026-09-06 ~08:25 UTC.

## Planned leaves (14), smallest-family order
1. gnc-autonomy/navigation/gnss-carrier-smoothing         (GNC 42->44)
2. gnc-autonomy/optimal-control/lqg-design                (GNC)
3. aerodynamics/high-speed/shock-tube                     (AERO 43->46)
4. aerodynamics/airfoil/thin-airfoil-section-theory       (AERO)
5. aerodynamics/high-speed/compressible-couette-flow      (AERO)
6. flight-test-operations/performance/rotorcraft-autorotation-flight-test (FTO 43->44)
7. propulsion/gas-turbine-cycle/brayton-optimum-pressure-ratio (PROP 43->44)
8. systems-engineering-safety/arp4761a/fault-tree-quantification (SES 45->47)
9. systems-engineering-safety/arp4761a/reliability-allocation (SES)
10. flight-mechanics/performance/rotorcraft-main-rotor-sizing (FM 46->47)
11. structures/fem/shear-center-analysis                   (STRUCT 51->53)
12. structures/fem/shrink-fit-analysis                     (STRUCT)
13. vehicle-design/sizing/landing-gear-layout              (VD 54->55)
14. gnc-autonomy/navigation/bearing-only-localization       (GNC)

DECISION at prep: 14 leaves locked. Leaves 567->581; SKILL.md
579->593; corpus 1150->1178 (2N=28); ledger 567->581 (rows 568-581).

## Post-wave family counts (planned)
gnc 45, aero 46, fto 44, prop 44, ses 47, fm 47, avionics 46
(unchanged), mq 48 (unchanged), structures 53, space 52 (unchanged),
vehicle-design 55, cross-cutting 54 (unchanged; closed - smaller
families not exhausted).

## Declined / closed this wave (receipts)
- AV 46 / MQ 48 / SPACE 52 / CC 54: saturated reaffirmed fresh
  (whole-family reads); CC default CLOSED (smaller families not
  exhausted). SPACE ADCS/mission-design closed-form core complete
  (disturbance-torque + reaction-jet wave-41; RCS sizing owned by
  propulsion cold-gas-thruster; slew owned by gnc bang-bang + adcs).
- GNC: wave-41 "saturated reaffirmed" was candidate-set-specific;
  whole-family FRESH probe found navigation (carrier smoothing, tdoa,
  bearing-only) + optimal-control (lqg) veins still clean. Space/control/
  guidance packs remain saturated (declines listed in receipts:
  path-following -> avionics lateral-navigation; RLS -> kalman-filter;
  square-root/UDU/Joseph KF -> rts-smoother body; MEKF -> complementary-
  filter; attitude conversions -> cross-cutting quaternion-algebra;
  CW/Hohmann/J2/Lambert -> space-systems orbit-mechanics; TRIAD/QUEST ->
  space-systems adcs).
- AERO declines stood + fresh: SWBLI/real-gas/hypersonic-viscous-
  interaction/tangent-wedge/Ackeret/turbulent-BL-integral/whirl-flutter/
  LFC/NLF not reopened; aileron-reversal OWNED (flight-mechanics);
  van-Driest-II/Chapman-Rubesin = function dup of flat-plate-skin-
  friction-heating; Fay-Riddell dup of aerodynamic-heating;
  Falkner-Skan/Hartree-beta DECLINED (ODE/tables); law-of-the-wall
  fenced (cfd-turbulence-modeling + rough-wall-skin-friction);
  Pohlhausen dup of Thwaites machinery; Taylor-Maccoll ODE;
  method-of-characteristics marching; pitot-inversion dup.
- FTO: 13/14 saturation re-confirmed; rotorcraft-autorotation-flight-test
  is the ONE genuine gap (measurement side; FM rotorcraft-autorotative-
  descent is the analytic estimate and defers the test reduction to
  FTO). Endurance/Vmax/UAS/planning declines stand.
- PROP: scramjet-cycle CLOSED; wave-39 declines stood; rocket-nozzle-
  divergence-loss flagged MARGINAL (single-coefficient thinness) ->
  NOT planned; brayton-optimum-pressure-ratio is the clean gap.
- SES: reliability-prediction-parts-count NOW DECLINED definitively
  (no MIL-HDBK-217/Telcordia id in standards-map; fabricated generic
  base-failure-rate table violates verified-anchor discipline; residual
  logic owned by reliability-block-diagram + maintainability-prediction;
  reopen only if MIL-HDBK-217F is added to standards-map). weibull/
  distribution fits owned by cross-cutting. rpn-fmea/success-run/
  standby-extension/per-flight conversion declines stand.

## Reserve pool (not planned; swap in if a planned leaf fails at
spec/build)
- gnc-autonomy/navigation/tdoa-positioning (MED; fence wording needed
  vs manufacturing-quality acoustic-emission planar hyperbolic location
  - emitter geolocation framing keeps it distinct)
- gnc-autonomy/navigation/bearing-only-localization (MED-HIGH; the 14th
  slot holder)
- aerodynamics/boundary-layer/rayleigh-stokes-boundary-layer (MED-LOW)
- propulsion/rocket/rocket-nozzle-divergence-loss (marginal thin)

## Standards ids (verify at spec time against standards-map.yaml +
siblings)
GNC nav: rtca-do-229 (gnss-carrier-smoothing; sibling gnss-raim-fde
convention); GNC optimal-control: arp4754a (lqr/observer convention).
AERO: naca-tr-824 (family convention). FTO rotorcraft: far-29 (sibling
convention). PROP: far-33 (gas-turbine-cycle convention). SES: arp4761a
(+ arp4754a for reliability-allocation). FM rotorcraft: far-29. STRUCT:
far-25/cs-25. VD: far-25/cs-25.
