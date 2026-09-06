# Wave-44 leaf plan (ops manager, continuation rescue - 11 probe receipts + 3 extension receipts)

RECEIPTS OVER LISTS: all 14 planned leaves come from probe receipts
(zero-owner greps + sibling fence reads at HEAD 496467d0), NOT a CEO
candidate list. Base probe batch deleg_2ff07eac (9 read-only agents, all
completed 2026-09-06 16:32:21 CEST, receipts archived in the delegation
summary files subagent-summary-{0..8}-20260906_163221_*.txt + wave44-recon/
task-{0..8}-receipt.md). Extension probe batch deleg_1a37284c (3 read-only
agents, completed 2026-09-06 16:52:27 CEST, receipts in
subagent-summary-{0..2}-20260906_165227_*.txt + wave44-recon/task-9-10-11-
receipt.md) was dispatched per the continuation-brief decision rule
(11 GO candidates sat below the ~12 plan threshold with thin margin against
spec-time declines: nozzle-area-ratio thin, stokes-creeping GO-lean, vmcg
borderline). Extension verdicts: vehicle-design 55 NO_CANDIDATES (10 decline
receipts), structures 57 -> 2 GO (both wave-43 reserves re-verified),
cross-cutting 54 -> 1 GO. Viable pool now 14, inside the 12-16 plan band.

## Planned leaves (14), smallest-family order, probe receipts cited
1. avionics/fsw/aperiodic-server-scheduling
   (AV 46; probe task-0 rank 1: fixed-priority schedulability of a periodic
   task set that also services aperiodic/event-driven jobs - polling/
   deferrable/sporadic server (C_s, T_s), budget replenishment, server
   folded into response-time analysis, aperiodic response bound;
   real-time-scheduling fence is periodic implicit-deadline only (quoted),
   shared-resource-access-control is PCP blocking only; Sprunt/Sha/Lehoczky
   1989 aperiodic-server theory, do-178c ref-only (fsw convention); spec
   caveat: prune generic schedulability/fixed-priority tag overlap,
   corpus reword carries sporadic-server/deferrable-server/aperiodic
   hyphenated tokens + a new RTS fence line)
2. propulsion/turbofan/mixed-flow-exhaust
   (PROP 46; probe task-1 rank 1, wave-43 reserve: two-stream turbofan
   mixing exhaust - constant-area mixer momentum + energy balance to mixed
   Tt/Pt, mixing loss, common choked (optionally afterburning) nozzle,
   net thrust + TSFC vs separate-exhaust baseline; turbofan-design-point is
   separate-exhaust only (quoted), afterburner-cycle is core-flow only,
   bypass-ratio-trade is velocity-level, propelling-nozzle single-stream;
   far-33; lead with mixed-flow-exhaust/exhaust-mixer/common-nozzle tokens)
3. propulsion/rocket/nozzle-area-ratio-selection
   (PROP 46; probe task-1 rank 2 GO-thin MED-overlap flagged: design-
   altitude expansion-ratio selection - solve epsilon such that
   Pe(epsilon) = Pa(h_design), matched/optimum epsilon, sea-level/vacuum/
   design-altitude Isp at chosen epsilon, flow-separation minimum-epsilon
   guard; nozzle-design's optimum_expansion is a verdict on a GIVEN
   epsilon not a solver, cea disclaims selection, separation owns the K_SEP
   limit not selection, divergence-loss takes geometry as input (fold did
   NOT happen wave-43 - verified); inverse isentropic area-Mach bisection;
   ecss. SPEC-TIME TRIAGE: verify against nozzle-design body before
   spec'ing; if genuine overlap found at spec time, decline and rely on
   buffer (reserve pool below))
4. flight-test-operations/envelope/vmcg-determination
   (FTO 47; probe task-3 rank 1 borderline-go: minimum control speed on
   the ground - asymmetric yawing moment vs steering + rudder authority
   over ground speed, 150 lbf pedal-force criterion family, authority-
   limited + pedal-force-limited speeds, Vmcg <= V1 gate on balanced-field
   scheduling; vmc-determination is the AIR leg only (0 ground/Vmcg/steer
   in body), engine-failure-takeoff-flight-test is ground-ROLL distance not
   directional control; far-25 + cs-25; DO NOT also build Vmcl; tokens
   vmcg-determination/ground-minimum-control-speed/nosewheel-steering-
   authority, never bare minimum-control-speed/vmc (FTO-3762 steal risk);
   extend-existing-into-vmc is the fallback if spec triage rejects)
5. aerodynamics/high-speed/ackeret-linearized-supersonic
   (AERO 49; probe task-6 rank 1: Cp = +-2*theta/sqrt(M^2-1),
   cl = 4*alpha/sqrt(M^2-1), supersonic lift-curve slope 4/sqrt(M^2-1),
   wave drag for flat-plate/biconvex/cambered thin sections; shock-
   expansion-airfoil self-fences curved/rounded sections out and uses
   linear theory only as a 10% validation anchor (quoted); Liepmann &
   Roshko/Anderson sec 9; naca-tr-824; corpus reword with ackeret/
   biconvex/linear-supersonic tokens - shock-expansion's generic
   supersonic-airfoil/wave-drag-coefficient tags are a live steal risk)
6. aerodynamics/high-speed/hypersonic-piston-theory
   (AERO 49; probe task-6 rank 2: Lighthill piston-theory surface pressure
   p/p_inf = (1 + ((gamma-1)/2)*v/a_inf)^(2gamma/(gamma-1)) with the
   linearized limit, shock vs expansion side split, unsteady/small-
   perturbation hypersonic surfaces; hypersonic-flow is steady blunt-body
   Newtonian only (quoted handover below Mach ~5), flutter-speed-prediction
   is Theodorsen subsonic; Lighthill 1953/Ashley-Zartarian; naca-tr-824)
7. aerodynamics/aeroelasticity/added-mass-coefficients-potential-flow
   (AERO 49; probe task-6 rank 3: virtual/apparent mass via
   T = 1/2*rho*integral(phi*dphi/dn dS) - 2-D cylinder rho*pi*R^2, normal
   flat plate rho*pi*a^2, 3-D sphere (2/3)*rho*pi*R^3, ellipsoids,
   kinetic-energy catalog; aeroelastic-gust-response explicitly disclaims
   apparent-mass terms (quoted), flutter-speed-prediction is oscillatory
   thin-airfoil C(k); Lamb Hydrodynamics Art. 136/Brennen; naca-tr-824)
8. aerodynamics/boundary-layer/stokes-creeping-flow-drag
   (AERO 49; probe task-6 rank 4 GO-lean lowest confidence: steady low-Re
   viscous flow - Stokes streamfunction for the sphere, F = 6*pi*mu*a*U,
   pressure/form drag split 1:2, Oseen correction, terminal velocity;
   unsteady-laminar-stokes-layers is unsteady 1st/2nd-problem only,
   hypersonic-flow sphere-drag is Newtonian M >> 5 (quoted handover);
   Stokes 1851/Schlichting sec 4; naca-tr-824; corpus intents worded to
   stay inside the boundary-layer viscous vein)
9. gnc-autonomy/optimal-control/ilqr-ddp
   (GNC 49; probe task-7 rank 1: iterative LQR / differential dynamic
   programming for nonlinear discrete-time systems - forward rollout,
   backward Riccati pass (Qx, Qu, Qxx, Qxu, Quu), local affine control
   law, forward pass with backtracking line search/regularization;
   lqr-design infinite-horizon linear scalar-input only, MPC linear
   receding-horizon QP only, dymos pseudospectral external-tool only,
   optimization-algorithms static design objectives only (all quoted);
   arp4754a; magnitude L - largest leaf of the wave)
10. gnc-autonomy/navigation/terrain-referenced-navigation
    (GNC 49; probe task-7 rank 2: non-GNSS INS aiding from radar-altimeter
    terrain profiles vs stored DEM - TERCOM-style grid correlation
    (surface + best-match offset) plus linearized terrain-slope
    measurement update (SITAN/point-mass); 0 gnc owners (9 token hits all
    outside gnc: coverage-path swath, weather radar clutter, part107);
    inertial-navigation/tightly-coupled-ins-gnss/ins-gnss-integrated-filter
    fence GNSS-or-pure-INS aiding (quoted); arp4754a)
11. gnc-autonomy/navigation/gnss-rtk-positioning
    (GNC 49; probe task-7 rank 3 fresh find: rover fix relative to a fixed
    base from double-difference carrier-phase - single then double
    differences across satellite pairs and epochs, float baseline +
    ambiguity by LS normal equations, integer rounding candidate sets +
    ratio test, fixed baseline/ENU offset; gnss-carrier-smoothing smooths
    CODE with carrier increments (explicitly not differencing),
    doppler leaf is velocity single-receiver, pseudorange leaf is
    code absolute; rtca-do-229)
12. structures/fem/statically-indeterminate
    (STRUCT 57; extension probe task-1 GO rank 1, wave-43 reserve
    re-verified: elastic redundancy analysis of indeterminate beams/
    continuous beams - fixed-end moments, three-moment (Clapeyron),
    slope-deflection, moment distribution (Hardy-Cross), consistent
    deformation/force method with stdlib Gaussian elimination; truss is
    pin-jointed DSM, beam-frame is stiffness-method numeric, plastic-
    collapse is LIMIT not elastic distribution (fences quoted);
    Roark/Shigley A-9/Bruhn; far-25 + cs-25)
13. structures/fem/restrained-warping
    (STRUCT 57; extension probe task-1 GO rank 2, wave-43 reserve
    re-verified: non-uniform torsion / warping restraint of thin-walled
    open sections - bimoment B, warping constant Cw = I_y*h^2/4 (I-
    section), hyperbolic closed-form solution of the non-uniform torsion
    ODE, St-Venant-vs-warping torque split for I/channel; torsion-shear-
    flow is FREE-warping only (Saint-Venant J and Bredt-Batho closed
    sections, quoted), shear-center is transverse V*Q/I only; Megson/
    Bruhn/Timoshenko-Vlasov; far-25 + cs-25)
14. cross-cutting/numerics/bandpass-bandstop-filter-design
    (CC 54; extension probe task-2 GO: Butterworth IIR bandpass/bandstop
    via the z-domain LP->BP / LP->BS digital frequency transformation
    (Oppenheim & Schafer/Proakis class), coefficients computed not looked
    up, both band edges verifiable at -3.0103 dB like the sibling prewarp
    anchors; digital-filter-design is LP/HP only with a hard ftype fence
    (quoted), fir-filter-design FIR lowpass only; naca-tr-824 numerics
    convention)

Family spread: avionics +1 (46 -> 47), propulsion +2 (46 -> 48),
flight-test-operations +1 (47 -> 48), aerodynamics +4 (49 -> 53),
gnc-autonomy +3 (49 -> 52), structures +2 (57 -> 59), cross-cutting +1
(54 -> 55). Total 597 -> 611 leaves; SKILL.md 609 -> 623; corpus
1210 -> 1238 (2N = 28); ledger 597 -> 611 rows (598-611). vehicle-design
55 NOT opened (extension probe NO_CANDIDATES with receipts).

## Spec-time triage gate (run per leaf before spec dispatch)
- nozzle-area-ratio-selection: read nozzle-design body; if the epsilon
  solver is genuinely owned there, DECLINE at spec time (do not spec a
  duplicate) and pull from the reserve pool.
- vmcg-determination: read vmc-determination body at HEAD; if the ground
  leg is genuinely claimed there, DECLINE and use the extend-existing-
  into-vmc fallback (no new leaf) - do NOT build Vmcl.
- stokes-creeping-flow-drag: confirm no low-Re body-drag owner appeared;
  if corpus intents cannot be worded inside the aero boundary-layer vein,
  DECLINE at spec time.
- aperiodic-server-scheduling: spec MUST pin exact aperiodic response-
  time formulas to one published source (verify-before-credit) and prune
  tag overlap with real-time-scheduling.

## Reserve pool (swap in if a planned leaf fails at spec/build)
- propulsion/rocket/nozzle-design-extension is NOT a leaf; instead:
  extend-existing adjudication is the documented fallback for #3.
- Any leaf below the 14 that survives spec-time triage but misses a
  build round is queued to 08:00 UTC 2026-09-07 (never after ~19:30 UTC).
- Vehicle-design/structures/cross-cutting re-probe only after corpus
  gains demand (per extension receipts).

## Declined / closed this wave (probe receipts, honest)
- flight-mechanics 47: NO_CANDIDATES (9 ranked near-misses declined:
  rotorcraft OGE-hover-ceiling + forward-flight climb fall in the wave-43
  FTO-slot-conflict class, stick-free stability out-of-mandate + corpus-
  steal risk, Dutch-roll/spiral/roll owned by lateral-directional-
  stability, V-n/corner/maneuvering owned structures+gust+load-factor,
  V-speeds -> FTO, cruise-optimum -> avionics FMS, fixed-wing ground
  effect -> aerodynamics, prop endurance in breguet-endurance
  prop_endurance; both wave-43 declines stay closed).
- systems-engineering-safety 47: NO_CANDIDATES (all six ARP4761A process
  functions owned; reliability-prediction-parts-count NOT reopened - no
  MIL-HDBK-217/Telcordia id in standards-map.yaml).
- manufacturing-quality 48: NO_CANDIDATES (SPC/gage R&R/sampling/
  disposition all owned; CMM seam standards-map-blocked - no ISO 15530/
  ASME B89.4.x id).
- space-systems 52: NO_CANDIDATES (slew owned gnc bang-bang +
  attitude-control-sizing; CCSDS 131.0-B map-blocked; staging/launcher/
  power/thermal/comms/orbits all fenced; TLE/SGP4 + MLI declined - no
  corpus/standards anchor).
- avionics 46: only fsw/aperiodic-server-scheduling GO; do160 sec-17 +
  vibration closed, TAWS/GPWS + Mode-S stay closed (RTCA-gated, no map
  id), ARINC 629/825/CAN map-blocked, UMS/FLS objective-table-gated.
- propulsion 46: scramjet CLOSED DEFINITIVELY; all 8 wave-39 declines
  re-checked and still closed at HEAD.
- aerodynamics: wave-43 declines stay closed (reflected-shock-tube-wall
  sandwiched between shock-tube + regular-shock-reflection; asymptotic-
  suction undemanded); 6 closed veins (area-Mach/choked -> isentropic,
  Karman-Tsien -> transonic-similarity, diamond -> shock-expansion,
  Sutton-Graves -> aerodynamic-heating, duct -> fanno/rayleigh, Stokes ->
  unsteady-laminar-stokes-layers); elementary-potential-flows declined
  (panel-method owns potential-flow tag + Kutta-Joukowski), Falkner-Skan
  needs numeric integration, Theodorsen/Sears owned, Knudsen owned space
  adcs + hypersonic.
- gnc-autonomy: tdoa-positioning CLOSED (manufacturing-quality acoustic-
  emission-inspection claims the hyperbolic time-difference iterated-LS
  localization math - quoted).
- vehicle-design 55: NO_CANDIDATES (10 declines with receipts, most
  plausible: high-lift/flap -> aero high-lift-systems, winglet -> aero
  winglet-design, rotorcraft main-rotor -> FM; 0-owner seams trim-tab/
  inlet-duct/oleo/reverser/fuel-vent all failed corpus demand).
- cross-cutting 54: 13 declines (QR -> SVD, iterative solvers, adaptive
  quadrature -> numerical-integration, stiff ODE, Shapiro-Wilk ->
  probability-distributions, constrained opt -> mdo, ANOVA -> mq + DOE,
  Bender/Mansoor stackup, QNH/QFE map-blocked, EVM/CPM/PERT, SE/safety ->
  SES, QA math -> MQ, converters -> gnc/FTO/space/avionics).

## Standards ids (all verified present in standards-map.yaml at prep)
do-178c, far-33, ecss, far-25, cs-25, naca-tr-824, arp4754a, rtca-do-229.
(8 ids, all grep-verified 1 hit each at prep.)

## Prep commit scope
state/wave44-leaf-plan.md (this file) + state/wave44-recon/ untracked
helpers + task-{0..8}-receipt.md extracts + task-9-10-11-receipt.md
(extension extracts). Specs land in state/wave44-specs/ from spec-
engineer agents (CAP <=4 concurrent, compact write-NOW prompts, anchor
script FIRST) and are committed after the spec phase.
