# Wave-43 leaf plan (ops manager, from 7 probe receipts at 916485c0)

RECEIPTS OVER LISTS: all 16 planned leaves come from probe receipts
(zero-owner greps + sibling fence reads at HEAD), NOT a CEO candidate list.
Probe batch deleg_1db8b266, 7 read-only agents, all completed 2026-09-06
~13:33 UTC. Full receipts archived in the delegation summary files and
summarized below. Remote advanced to d357383c during prep (concurrent docs
automation push, expected wave class); baseline 916485c0 remains an ancestor.

## Planned leaves (16), smallest-family order, probe receipts cited
1. flight-test-operations/envelope/vmu-determination
   (FTO 44; probe C4: FAR 25.107(b) rotation-limit speed from takeoff
   rotation runs + standard-condition correction; sibling vmc-determination
   precedent; far-25/cs-25; LOW overlap)
2. flight-test-operations/performance/rotorcraft-forward-flight-climb-test
   (FTO; probe C1: rotorcraft ROC-vs-speed sweep reduction, Vy, ceilings;
   fixed-wing sibling climb-performance-flight-test is fixed-wing only;
   far-29; LOW)
3. flight-test-operations/performance/rotorcraft-height-velocity-diagram-test
   (FTO; probe C3: H-V demonstration reduction, hover/low-speed engine-
   failure height loss, boundary map vs diagram; rotorcraft-autorotation-
   flight-test owns steady-descent only (verified body grep 0 H-V hits);
   far-29; MED overlap flagged, fenced by regime)
4. propulsion/rocket/rocket-nozzle-divergence-loss
   (PROP 44; probe C1 re-verify: widened deterministic scope - conical
   half-angle lambda, bell/parabolic contour loss, BL displacement effect,
   delivered-Isp bridge; cea-rocket-combustion disclaims divergence losses
   (lines 63-65, 83-85, 105-107); ecss; LOW)
5. propulsion/turbofan/turbofan-design-point
   (PROP; probe C3: two-stream station-level design point given OPR/TIT/
   FPR/BPR/effs/M - the producer the turbofan-cycle/bypass-ratio-trade
   consumers lack; far-33; LOW-MED; pack turbofan per config grouping)
6. gnc-autonomy/navigation/gnss-doppler-velocity-positioning
   (GNC 45; probe #1: snapshot receiver velocity + clock-drift fix from
   carrier delta-range-rate, iterated LS; gnss-pseudorange-positioning is
   position-domain only; rtca-do-229; LOW)
7. gnc-autonomy/estimation-filtering/process-noise-discretization
   (GNC; probe #5: continuous PSD to discrete Q (van Loan); feeds every
   filter leaf; kalman-filter-design is scalar single-axis; arp4754a;
   MED - lead with van-loan/spectral-density tokens)
8. gnc-autonomy/estimation-filtering/imu-static-calibration
   (GNC; probe #4: six-position + rate-table test reduction to bias/scale/
   misalignment; inertial-navigation owns drift error growth only;
   arp4754a; LOW-MED)
9. gnc-autonomy/navigation/tightly-coupled-ins-gnss
   (GNC; probe #3: INS error-state filter on raw pseudorange observables +
   clock states; ins-gnss-integrated-filter body declares raw-observable
   filtering out of scope (owner-declared gap); rtca-do-229 + arp4754a;
   LOW; magnitude L - largest leaf of the wave)
10. aerodynamics/high-speed/fanno-flow
    (AERO 46; probe #1: constant-area adiabatic duct with friction, Fanno
    line integral fL*/D closed form, choking length, invert L to M by
    1-D root; isentropic-flow-relations is frictionless complement;
    naca-tr-824; LOW)
11. aerodynamics/high-speed/rayleigh-flow
    (AERO; probe #2: constant-area frictionless duct with heat addition,
    closed-form p/rho/T/p0/M relations, max heat addition to thermal
    choke; all 16 rayleigh hits are Rayleigh-pitot/Rayleigh-Ritz noise;
    naca-tr-824; LOW)
12. aerodynamics/boundary-layer/unsteady-laminar-stokes-layers
    (AERO; probe #3: Stokes 1st + 2nd problem exact erfc/oscillating-plate
    solutions; compressible-couette-flow steady precedent in family;
    naca-tr-824; LOW)
13. structures/fem/crippling-analysis
    (STRUCT 53; probe #1: local crippling + inter-rivet buckling of formed
    compression shapes, shape-constant method, Johnson-Euler interaction;
    buckling-analysis is global Euler only, plate-buckling hands off
    stiffened shells; far-25/cs-25; LOW; HIGH magnitude)
14. structures/fem/hertzian-contact-stress
    (STRUCT; probe #3: Hertz contact patch/p0/subsurface tau_max spheres/
    cylinders/rollers; contact-analysis is FEA numerics (penalty),
    lug-joint is nominal pin bearing; far-25; LOW-MED; name distinct from
    contact-analysis)
15. structures/fem/metallic-fastener-joints
    (STRUCT; probe #5: multi-fastener metallic joints bolt/rivet shear,
    bearing, net-section, shear-out, eccentric bolt-group polar method vs
    MMPDS; composite-bolted-joints is laminate-only; mmpsd + far-25/cs-25;
    LOW)
16. structures/fem/plastic-collapse-analysis
    (STRUCT; probe #2: fully-plastic bending Mp = sigma_y*Zp, shape
    factor, plastic hinge + collapse mechanisms (kinematic/static
    theorems) for indeterminate beams/frames; ramberg-osgood is stress-
    strain curve only; far-25/cs-25; LOW)

Family spread: flight-test-operations +3 (44->47), propulsion +2 (44->46),
gnc-autonomy +4 (45->49), aerodynamics +3 (46->49), structures +4
(53->57). Total 581 -> 597 leaves; SKILL.md 593 -> 609; corpus
1178 -> 1210 (2N=32); ledger 581 -> 597 rows (582-597).

## Declined / closed this wave (probe receipts, honest)
- AV 46 / MQ 48 / SPACE 52 / SES 47: SATURATED - NO_CANDIDATES fresh
  whole-family receipts (probe agents 5 and 4). SES: all six ARP4761A
  process functions exist (FHA/PSSA/SSA/ZSA/PRA/CCA+CMA); reliability-
  prediction-parts-count NOT reopened (verified: NO MIL-HDBK-217/Telcordia
  id in standards-map.yaml; MIL-HDBK-189 is reliability-growth's legit
  anchor only). AV: TAWS/GPWS + Mode-S stay closed (wave-32 decline,
  RTCA-gated, no map id). MQ: CMM/coordinate-metrology seam is standards-
  map-blocked (no ISO 15530/ASME B89.4.x id) - not clean. SPACE: CCSDS
  131.0-B modulation/coding seam map-blocked; slew owned by bang-bang +
  attitude-control-sizing.
- flight-mechanics 47: probe found 2 candidates, both declined for wave-43:
  rotorcraft-height-velocity-diagram (ANALYSIS) conflicts with the FTO
  measurement-side slot (3) occupying the same H-V function this wave -
  the FTO demonstration-reduction slot is the cleaner in-family producer
  (autorotation measurement precedent); rotorcraft-forward-flight-envelope-
  limits (retreating-blade stall semi-empirical boundary) carries
  fabricated-table risk without a published closed-form anchor (parts-count
  decline precedent). FM not saturated but cleaner slots exist in smaller
  families; revisit next wave. absolute-ceiling / corner-velocity / V-n
  diagram etc. rejected with owners (receipt).
- cross-cutting 54: default CLOSED (smaller families not exhausted).
  vehicle-design 55: probed LAST by doctrine - not reached (smaller
  families still had clean slots).
- AERO declines stood + reflected-shock-tube-wall excluded (HIGH overlap
  with shock-tube - adjudicated extend-existing rather than new leaf);
  asymptotic-suction-boundary-layer excluded (LFC/NLF adjacency, lowest
  confidence).

## Reserve pool (swap in if a planned leaf fails at spec/build)
- flight-test-operations/performance/balked-landing-flight-test (far-25)
- flight-test-operations/performance/rotorcraft-category-a-oei-flight-test
  (far-29)
- propulsion/turbofan/mixed-flow-exhaust (far-33)
- gnc-autonomy/optimal-control/ilqr-ddp (arp4754a)
- gnc-autonomy/navigation/terrain-referenced-navigation (arp4754a)
- aerodynamics/boundary-layer/laminar-far-wake-free-shear (naca-tr-824)
- structures/fem/statically-indeterminate-analysis (far-25/cs-25)
- structures/fem/restrained-warping-torsion (far-25)

## Standards ids (all verified present in standards-map.yaml at prep)
far-25, cs-25, far-29, ecss, far-33, rtca-do-229, arp4754a, naca-tr-824,
mmpsd (arp4761a unused this wave).

## Prep commit scope
state/wave43-builder-kit.md, wave43-close-runbook.md, wave43-merge-corpus.py,
wave43-sim-merge.py, wave43-leaf-plan.md, wave43-recon/ (helpers). Specs
land in state/wave43-specs/ from spec-engineer agents and are committed
with the prep batch at the end of the spec phase.
