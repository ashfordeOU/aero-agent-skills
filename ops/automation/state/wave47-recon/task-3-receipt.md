# WAVE-47 GNC-AUTONOMY PROBE RECEIPT (task-3, whole-family FRESH)

- Repo: local AeroSkills repo at ~/AeroSkills, git HEAD a4ae6d1e (verified
  `git log --oneline -1`: "a4ae6d1e Wave-47: close-out must auto-update
  products-state (FIX)"). Note: the brief cited HEAD a544f421; the repo has
  since moved — this probe ran FRESH at a4ae6d1e, the current wave-47 HEAD.
  Working tree clean at probe start and end except the wave47-recon receipts
  directory (git status --porcelain: 1 untracked entry, this receipt).
- Scope: ENTIRE gnc-autonomy family, 58 leaves, probed FRESH at wave-47 HEAD.
  Read-only probe: no writes to skills/, eval/, standards-map.yaml, scripts/,
  Makefile, or ops/automation briefs. One write only: this receipt.
- Family leaf count verified: `find skills/gnc-autonomy -mindepth 3 -name
  SKILL.md` = 58 (control 13, estimation-filtering 10, guidance 10,
  navigation 14, optimal-control 7, space 4), +1 family router SKILL.md.
  Wave-46 +3 all on disk: ionospheric-delay-correction (navigation),
  impact-time-control-guidance (guidance), deadbeat-control (control).
- Corpus baseline: eval/hit1-corpus.yaml = 1286 tasks (yaml parse recovered
  1286/1286; header line 286 "Corpus: 1286 tasks"); router tree indexed 647
  SKILL.md under skills/ (635 leaves + 12 family routers) with the same
  loader as scripts/router_eval.py.
- Standards map: 30 ids (grep '^  - id:' = 30); candidates map onto existing
  ids, grep-verified: arp4754a line 38, rtca-do-229 line 303.
- Prior-wave context read: wave-46 gnc receipt
  (ops/automation/state/wave46-recon/task-7-receipt.md, HEAD 45931c16), whose
  three GOs LANDED and whose reopen reminders govern this probe.

## Verdict

4 GO candidates ranked below with full gate evidence (a-f), first three
strong (navigation/tropospheric-delay-correction, guidance/impact-angle-
control-guidance, control/smith-predictor), fourth (control/h-infinity-
control) flagged conditional on pool size and a spec-time description
hardening (its second Hit@1 query margin is 1.5 points — fragile). The
wave-46 "Closed EXCEPT the per-source delay model seam" vein continues:
ionospheric-delay-correction is now on disk and its next sibling,
tropospheric-delay-correction, is GO 1. tdoa-positioning fence re-checked
FRESH vs manufacturing-quality acoustic-emission-inspection as ordered —
still CLOSED (unchanged quotes below). All wave-46 declines re-verified
STAND; fresh seams probed and declined this wave: vor-dme-positioning
(avionics owns the navaid vocab; sim margins 3.0/5.0), attitude
determination QUEST/q-method/TRIAD (OWNED by space-systems/adcs),
ascent/linear-tangent guidance (space-systems mission-design territory),
information-filter and other KF form-variants (wave-46 precedent),
anti-windup (OWNED by pid-control-design).

## Ranked GO with evidence

### GO 1: gnc-autonomy/navigation/tropospheric-delay-correction

One-line why: ionospheric-delay-correction (wave-46 GO1, on disk) opened the
per-source GNSS delay-model seam and owns only the ionospheric member; the
Saastamoinen/Hopfield tropospheric zenith-plus-mapping delay model is
zero-owner tree-wide AND zero in the 1286-task corpus, and both wordable
Hit@1 queries route to the candidate with 6.5+ point margins over the
ionospheric sibling and zero theft.

(a) Zero-owner greps, whole skills/ tree, FRESH:
`rg -i -l 'saastamoinen|hopfield|zenith-delay' skills/ -g 'SKILL.md'` -> 0
hit(s) (exit 1). Corpus scan `rg -ic 'tropospher|saastamoinen|hopfield'
eval/hit1-corpus.yaml` -> 0 hits. The only 'tropospher' owners tree-wide are
atmosphere-STATE leaves (cross-cutting/units-atmos/isa-atmosphere,
density-altitude, propulsion/vehicle-sizing consumers of ISA tables) — none
models radio-wave propagation delay; no gnc-autonomy SKILL.md contains the
word at all.

(b) Sibling fences (FRESH reads, verbatim):
ionospheric-delay-correction body lines 32-37: "It pairs with
gnc-autonomy/navigation/gnss-pseudorange-positioning, which consumes the
corrected pseudorange in its iterated least squares fix, and
gnc-autonomy/navigation/gnss-carrier-smoothing, whose ionospheric divergence
monitor tracks the code-carrier growth rate rather than the per-source delay
magnitude computed here." — the per-source delay claim is scoped to the
ionospheric member only; no leaf computes or even names a tropospheric term.
gnss-pseudorange-positioning description line 3: "given satellite positions
in ECEF and their pseudoranges (geometric range plus receiver clock bias),
solve the four-unknown navigation equations ... iterated least-squares
adjustment" and body lines 52-54: "Post-fit position error: pos_1sigma =
uere_equiv * pdop with uere_equiv = residual RMS" — positioning consumes
ranges as given and lumps all unmodeled error into a post-fit scalar.

(c) Standards-map id exists: `grep -n 'id: rtca-do-229' standards-map.yaml`
-> line 303 (RTCA DO-229, the GNSS-navigation sibling convention, same as
the ionospheric leaf's reference-only use).

(d) Published deterministic anchor (summary-only): Saastamoinen zenith
delays — hydrostatic zenith delay approx. 0.002277 * p / cos(z) with the
gravity/height correction term, wet zenith delay from the water-vapour
partial pressure e and temperature T (1255/T + 0.05 form), mapped to slant
by the cosecant elevation mapping function with the Black/height-correction
extension. Equation family: zenith met-model polynomials plus elevation
mapping. Source: Saastamoinen, "Contributions to the Theory of Atmospheric
Refraction," Bulletin Geodesique 107:13-34, 1973 (and his 1972 AGU
monograph chapter); Hopfield 1969 as the standard alternative. Deterministic
offline closed form given surface pressure, temperature, vapour pressure and
elevation.

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-47 HEAD with the
deterministic token router replicated from scripts/router_eval.py
(hyphen-preserving tokens, tag weight 3, name 2, desc 1, body 0.5, phrase
bonus 4, tie-break path asc) over the real 647-SKILL.md index plus the
candidate:
1. "compute the saastamoinen zenith hydrostatic delay and the zenith wet
   delay from the surface pressure, temperature and water-vapour partial
   pressure and map them to the slant tropospheric delay at the satellite
   elevation to correct the GNSS range" -> HIT1 at 19.0 vs 12.0
   (gnc-autonomy/navigation/ionospheric-delay-correction).
2. "apply the tropospheric-delay-correction to the pseudorange: evaluate the
   saastamoinen model zenith delay with the elevation mapping function and
   subtract the slant tropospheric delay in metres before the position fix"
   -> HIT1 at 22.5 vs 16.0 (gnc-autonomy/navigation/ionospheric-delay-
   correction).
Distinct from the two existing ionospheric corpus tasks (w46-ionospheric-
delay-correction-1/-2, klobuchar/pierce-point wording — listed in the method
note). Theft audit over all 1286 corpus tasks: 0 tasks reroute.

(f) Tag set all hyphenated compounds: tropospheric-delay-correction,
saastamoinen-model, zenith-hydrostatic-delay, zenith-wet-delay,
slant-tropospheric-delay, elevation-mapping-function.

### GO 2: gnc-autonomy/guidance/impact-angle-control-guidance

One-line why: the wave-46 receipt deferred this exact seam to wave-47 ("a
wave-47 candidate if the pool needs a second guidance leaf") and its landed
sibling impact-time-control-guidance now fences impact-angle OUT in its own
pitfalls (verbatim line 137-138 below); zero-owner and zero-corpus hold, and
both wordable Hit@1 queries route to the candidate with 7+ point margins and
zero theft.

(a) Zero-owner greps, whole skills/ tree, FRESH:
`rg -i -l 'impact[- ]angle|terminal[- ]angle' skills/ -g 'SKILL.md'` -> 1
hit: the impact-time-control-guidance sibling, whose only occurrence is the
fence quote in (b) — not an ownership claim. Corpus scan: 0 of 1286 tasks
contain impact-angle/terminal-angle tokens.

(b) Sibling fences (FRESH reads, verbatim):
impact-time-control-guidance pitfalls lines 137-138: "Do not add impact-
angle constraints: no leaf in the family claims them and they are out of
scope for the time-only law." — the closest sibling explicitly renounces the
impact-angle member of the terminal-law family. proportional-navigation /
augmented-proportional-navigation own the planar LOS-rate baseline and its
maneuvering-target augmentation only (wave-46 quotes re-verified unchanged);
midcourse-guidance owns waypoint/handover trajectory shaping, not a
terminal impact-angle constraint; impact-point-prediction is open-loop
ballistic.

(c) Standards-map id exists: `grep -n 'id: arp4754a' standards-map.yaml` ->
line 38 (ARP4754A reference-only, guidance-pack convention, same as the
ITCG leaf).

(d) Published deterministic anchor (summary-only): impact-angle-control
guidance laws that shape the command so the terminal flight-path angle meets
a commanded value — canonical form: proportional-navigation baseline plus an
impact-angle-error feedback term, the command a closed-form function of the
closing geometry, time-to-go and the commanded impact angle (time-to-go
polynomial shaping). Source: Ryoo, Cho and Tahk, "Optimal Guidance Laws with
Terminal Impact Angle Constraint," Journal of Guidance, Control, and
Dynamics 28(4):724-732, 2005 (deterministic offline closed-form command
evaluation; the standard reference of the impact-angle literature).

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-47 HEAD:
1. "compute the impact-angle-control-guidance command so the interceptor
   meets the target at the commanded impact angle: form the impact-angle
   error feedback from the current flight path angle and the time to go and
   shape the guidance command" -> HIT1 at 24.5 vs 17.5
   (gnc-autonomy/guidance/impact-time-control-guidance).
2. "run the terminal-impact-angle guidance law: evaluate the impact-angle-
   error-feedback term shaped by time to go and report the guidance command
   that drives the terminal flight path angle to the commanded-impact-angle"
   -> HIT1 at 21.0 vs 11.0 (gnc-autonomy/guidance/midcourse-guidance).
Distinct from the two existing ITCG corpus tasks (w46-impact-time-control-
guidance-1/-2, salvo/impact-time wording). Theft audit: 0 of 1286 tasks
reroute.

(f) Tag set all hyphenated compounds: impact-angle-control-guidance,
terminal-impact-angle, commanded-impact-angle, impact-angle-error-feedback,
terminal-flight-path-angle-constraint.

### GO 3: gnc-autonomy/control/smith-predictor

One-line why: dead-time compensation (Smith predictor structure) is
zero-owner across the tree AND zero in the 1286-task corpus, the control
pack (13 leaves) has no delay-compensation leaf and its tuning/synthesis
siblings never claim one, and both wordable Hit@1 queries route to the
candidate with 9+ point margins and zero theft.

(a) Zero-owner greps, whole skills/ tree, FRESH:
`rg -i -l 'smith[- ]predictor|dead[- ]time|transport[- ]delay|delay[- ]
compensat' skills/ -g 'SKILL.md'` -> 1 hit: flight-mechanics/handling-
qualities/pilot-induced-oscillation, context-checked as the MIL-STD-1797A
pilot-in-the-loop tau_e equivalent-time-delay (lines 54/70/135-137: "the
measured transport delay is one contributor" to tau_e) — handling-qualities
vocabulary, NOT a control-loop dead-time compensator owner. Corpus scan
`rg -ic 'smith|dead[- ]time|transport[- ]delay' eval/hit1-corpus.yaml` -> 0
hits (the only tree-wide 'Smith' in SKILL.md prose is the
Gordon-Salmond-Smith particle-filter ancestry citation in
estimation-filtering/particle-filter, also not an owner).

(b) Sibling fences (FRESH reads): pid-control-design description line 3
(verbatim excerpt): "Design PID controller gains for aerospace flight and
GNC control loops: compute the controller output from the proportional,
integral, and derivative error terms, tune the gains ... with Ziegler-
Nichols using the ultimate gain and ultimate period ... add integrator
anti-windup clamping, and check the gain margin and phase margin of the
loop." — tuning/anti-windup/margins, no dead-time or delay-compensation
claim. digital-control-design owns z-domain discretization/emulation/
discrete-PID/stability/sample-rate selection (wave-46 quote) — no transport-
delay structure. observer-design scores as the sim runner-up purely on the
'prediction' token of its estimator vocabulary; it is not a compensation
owner.

(c) Standards-map id exists: arp4754a line 38 (control-pack convention,
same as deadbeat-control's reference-only use).

(d) Published deterministic anchor (summary-only): the Smith predictor —
primary controller designed for the delay-free plant model, with the
predictor subtracting the delayed model output from the measured output so
the primary loop closes on a delay-free compensated error; equivalent
closed-loop transfer function with the 1 - exp(-sT) dead-time block and
explicit predictor output computable by convolution over the delay line.
Source: O. J. M. Smith, "Closer Control of Loops with Dead Time," Chemical
Engineering Progress 53(5):217-219, 1957. Deterministic offline closed-form
compensation given the delay-free model, the dead time and the primary
controller.

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-47 HEAD:
1. "design the smith-predictor for the loop with dead time: model the
   delay-free plant, compute the delayed model output, and form the
   compensated feedback by subtracting the delayed prediction from the
   measured plant output before the primary controller" -> HIT1 at 25.0 vs
   16.0 (gnc-autonomy/control/observer-design).
2. "apply dead-time-compensation with the smith predictor structure: build
   the predictor output from the delay-free plant model and the transport
   delay and report the compensated error signal for the primary loop" ->
   HIT1 at 19.5 vs 9.5 (gnc-autonomy/control/observer-design).
Distinct from the existing pid-control-design and digital-control-design
corpus tasks (gain-margin/tuning and z-domain wording; listed in the method
note). Theft audit: 0 of 1286 tasks reroute.

(f) Tag set all hyphenated compounds: smith-predictor,
dead-time-compensation, time-delay-compensation, delay-free-model-prediction,
predictor-feedback-signal.

### GO 4 (conditional): gnc-autonomy/control/h-infinity-control

One-line why: H-infinity synthesis (DGKF two-Riccati) is zero-owner
tree-wide and zero in the corpus — the control pack has no robust-synthesis
leaf (adaptive-control and l1-adaptive-control own adaptation, not
worst-case norm-bounded synthesis) — but its second Hit@1 query margin is
only 1.5 points, so it is ranked conditional: GO if the pool takes a 4th
gnc leaf this wave AND the spec hardens the description wording.

(a) Zero-owner grep: `rg -i -l 'h-infinity|h_inf|hinfsyn' skills/ -g
'SKILL.md'` -> 0 hit(s) (exit 1). Corpus scan: 0 of 1286 tasks.
(b) Sibling fences: frequency-response-design owns gain/phase-margin
computation (classical); lqr-design/lqg-design own the algebraic Riccati
equations of optimal control — neither claims the gamma-iteration
worst-case synthesis. (c) arp4754a line 38, control-pack convention.
(d) Deterministic anchor: Doyle, Glover, Khargonekar and Francis,
"State-Space Solutions to Standard H2 and H-infinity Control Problems,"
IEEE Transactions on Automatic Control 34(8):831-847, 1989 — two algebraic
Riccati equations with the spectral-radius coupling condition rho(X_inf
Y_inf) < gamma^2 and the central-controller formulas; deterministic offline
closed form at a fixed gamma level.
(e) Sim-verified Hit@1: Q1 at 25.0 vs 10.0 (lqr-design); Q2 at 16.5 vs 15.0
(observer-design) — Q2 margin 1.5 is the fragile one; the spec description
must carry gamma-iteration/weighting tokens more strongly. Theft audit: 0.
(f) Tags: h-infinity-control-synthesis, dgkf-two-riccati, gamma-iteration,
generalized-plant-weighting, central-h-infinity-controller.

## Declines table (wave-46 rows re-verified FRESH; fresh seams probed this wave)

| Near-miss candidate | Gate(s) | Fresh evidence / decline reason |
|---|---|---|
| navigation/tdoa-positioning (brief-ordered fence re-check) | b | RE-CHECKED PER BRIEF. Still CLOSED: manufacturing-quality acoustic-emission-inspection SKILL.md lines 58-60 (verbatim): "Source location: linear location uses two sensors on a line and the arrival-time difference; planar location triangulates from three or more sensors by solving the hyperbolic time-difference system" and scripts/acoustic_emission_inspection_logic.py lines 111-113: "Each pair (i, 0) gives the hyperbolic constraint d_i - d_0 = v*(t_i - t_0). The system is linearized around the current guess and solved as a 2x2 normal system (Cramer), iterating from the sensor centroid to convergence." UNCHANGED at this HEAD — the AE leaf owns the deterministic core of a 2D TDOA leaf. Reopen only if that generic claim is dropped. |
| navigation/time-differenced-carrier-phase-positioning | e | STAY (wave-46): doppler leaf still owns single-epoch carrier delta-range vocab; no fence narrowing since wave-46; corpus 0. |
| navigation/vor-dme-positioning (FRESH this wave) | b, e | Zero-owner tokens pass, but sim Hit@1 margins are 3.0 and 5.0 points against avionics/flight-management/radio-navigation-aids (18.0 vs 15.0; 17.0 vs 12.0), which owns VOR radial / DME slant-range geometry with tag weight 3 and has 2 corpus tasks (w27-radio-navigation-aids-1/-2); avionics dme-arc-leg owns the DME arc vocabulary. Cross-family seam into the avionics navaid vein; margins too thin for stable corpus routing. |
| estimation/attitude determination (QUEST / q-method / TRIAD) | a, b | OWNED: `rg -i -l 'wahba|davenport|q-method' skills/ -g 'SKILL.md'` -> space-systems/adcs/attitude-determination-quest, attitude-determination-triad, magnetometer-calibration (+space-systems router). space-systems is the saturated NO_CANDIDATES owner of the ADCS space (wave-46 closed-vein note); the gnc space pack stays at 4 orbit/attitude-dynamics leaves. |
| guidance/ascent linear-tangent / explicit / powered-descent guidance (FRESH) | scope | Zero-owner tree-wide AND corpus 0, but placement doctrine: launch/ascent guidance is space-domain, and space-systems/mission-design (entry-descent-landing, c3-departure-energy, synodic-launch-window) is the saturated owner of that territory; gnc guidance pack is intercept/terminal/planning (10 leaves). Declined on family-scope, not on the math. |
| estimation-filtering KF form-variants (information filter, square-root/UD-factorized, cubature, fading-memory) | b | STAY (wave-46 precedent): kalman-filter-design's trigger still claims "estimator design, sensor fusion, recursive least squares"; form-variants of the single-axis KF belong inside the existing leaves (wave-46 declined information-filter on exactly this rule); estimation vein 10 leaves deep. |
| control/anti-windup | a | OWNED: pid-control-design owns it in desc (line 3, quote under GO 3), tags (anti-windup, integrator-clamp) and body; gain-scheduling/frequency-response-design/bang-bang mention windup in context. |
| guidance/true-proportional-navigation, PN variants, 3D engagement geometry | b, e | STAY (wave-46): PN/APN own the planar LOS-rate geometry and maneuvering augmentation; corpus 0; no fence change. |
| guidance/waypoint path following | b | STAY: avionics lateral-navigation + command-to-line-of-sight + midcourse own cross-track/waypoint vocab; no fence change. |
| optimal-control textbook cases (LQR servo/integral action, discrete ARE specializations) | b, e | STAY (wave-46 closed vein): lqr-design/lqg-design/ilqr-ddp own both AREs and the backward-Riccati passes; wave-46 min-fuel and DRE declines stand (no new seam with a clean closed-form identity opened this wave); corpus 0. |
| navigation multipath / UERE budget, air-data-dead-reckoning | b, d | STAY (wave-46): dilution-of-precision + gnss-pseudorange-positioning own UERE-to-position mapping; empirical multipath magnitudes have no closed-form anchor; corpus 0. |
| space pack additions (Hohmann, bi-elliptic, etc.) | a | OWNED outside family: space-systems/orbit-mechanics owns hohmann-transfer, bi-elliptic-transfer, plane-change-maneuver, clohessy-wiltshire, low-thrust-spiral, gravity-assist-swingby; gnc space pack stays CLOSED at 4 leaves. |

## Closed veins (owner leaf per vein, reaffirmed FRESH at wave-47 HEAD)

- GNSS positioning: pseudorange (iterated-LS fix + post-fit uere_equiv),
  doppler-velocity (single-epoch + broadcast-ephemeris propagation), carrier-
  smoothing (Hatch + ionospheric-divergence monitor), rtk (double-difference
  + integer ambiguity), raim-fde, dilution-of-precision, ionospheric-delay-
  correction (Klobuchar per-source delay, landed wave-46). Per-source delay
  model seam now has its ionospheric member OWNED; tropospheric member is
  GO 1 this wave.
- Passive localization: bearing-only (Stansfield). Hyperbolic TDOA: CLOSED
  by manufacturing-quality acoustic-emission-inspection (fresh quotes above).
- INS/integration: inertial-navigation, ins-gnss-integrated-filter (loose
  psi-angle), tightly-coupled-ins-gnss, terrain-referenced-navigation,
  navigation-frames. CLOSED.
- Estimation filters: alpha-beta, complementary, ekf, ukf (NEES), imm,
  particle, rts-smoother, process-noise-discretization, imu-static-
  calibration, kalman-filter-design, cramer-rao-lower-bound. CLOSED
  (form-variants declined; attitude determination owned by space-systems).
- Guidance laws: pursuit, proportional-navigation, augmented-proportional-
  navigation, command-to-line-of-sight, collision-course, midcourse,
  impact-point-prediction, impact-time-control-guidance (landed wave-46),
  coverage/dubins planning. Terminal-constraint family: time member OWNED,
  angle member is GO 2 this wave.
- Optimal control: bang-bang, lqr, lqg, mpc, ilqr-ddp, dymos, loop-transfer-
  recovery. CLOSED.
- Control (classical/modern): pid, lead-lag, root-locus, frequency-response,
  state-space, observer, digital-control-design, python-control, gain-
  scheduling, control-allocation, adaptive (MRAC), l1-adaptive, deadbeat
  (landed wave-46). Delay-compensation member is GO 3 (smith-predictor);
  robust worst-case synthesis member is GO 4 conditional.
- Space pack (4 leaves): closed at gnc scope; space-systems owns the wider
  orbit/ADCS/launch space (see declines).

## Standards-map check

30 ids present (grep '^  - id:' = 30). GO 1 maps rtca-do-229 (line 303,
reference-only, GNSS convention); GO 2/GO 3/GO 4 map arp4754a (line 38,
reference-only, guidance/control pack conventions). No new standards ids
required.

## Method note

All greps, scans and sims above were read-only terminal runs at HEAD
a4ae6d1e. The router sim replicates scripts/router_eval.py exactly
(hyphen-preserving tokens, stopword filter, tag weight 3 / name 2 / desc 1 /
body 0.5, verbatim-phrase bonus 4, tie-break path asc) with per-skill token
sets precomputed for speed, over the real 647-SKILL.md index plus each
hypothetical candidate, and over all 1286 eval/hit1-corpus.yaml tasks for
the zero-theft audits (yaml parse recovered 1286/1286 task blocks).
Temporary read-only helper scripts (candidate payloads and the sim driver)
were written to a temp directory only; no repo file was modified except
this receipt — git status before and after showed only the wave47-recon
receipts directory as untracked.

Existing sibling corpus tasks confirmed distinct from the new query wording:
ionospheric-delay-correction -> w46-ionospheric-delay-correction-1/-2
(klobuchar-broadcast-model, pierce-point, alpha/beta coefficients);
impact-time-control-guidance -> w46-impact-time-control-guidance-1/-2
(salvo attack, commanded-impact-time); deadbeat-control ->
w46-deadbeat-control-1/-2; digital-control-design -> w32-*; pid-control-
design -> g3, pid-control-design-w8-1/-2; radio-navigation-aids ->
w27-radio-navigation-aids-1/-2; proportional-navigation -> pn1/pn2;
augmented-proportional-navigation -> w31-*.

Recheck reminders for future waves: tropospheric-delay-correction closes the
per-source delay seam once built (further GNSS siblings are multipath —
declined wave-46 on empirical-anchor grounds — and receiver tracking-loop
error, which sits at the RF/PNT interface outside the pack's positioning
scope and maps to no existing standards id); impact-angle-control-guidance
closes the terminal-constraint family (no further members with distinct
closed-form identities); smith-predictor and h-infinity-control (if taken)
deepen the control pack toward delay compensation and robust synthesis —
recheck l1-adaptive/adaptive fences before any further robust/adaptive
member; tdoa reopens only if acoustic-emission-inspection drops the generic
hyperbolic iterated-LS claim; TDCP reopens only if the doppler sibling
narrows to single-epoch-only AND corpus intent appears.
