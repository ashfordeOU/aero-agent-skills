# Wave-45 Recon Receipt: gnc-autonomy (task 6)

Probe date: 2026-09-07. Probe agent: read-only recon subagent.
Repo HEAD: 5cc8fef33ffa3bd5530847040ef891299dde107d (main, clean at probe start; only
untracked files are the sibling wave45-recon receipts written in parallel).
Scope: whole gnc-autonomy family probed FRESH, zero-owner greps over the whole skills/
tree (623 SKILL.md), sibling fence reads, standards-map grep, router Hit@1 simulation.
Baseline: wave-44 yielded +3 (ilqr-ddp, terrain-referenced-navigation,
gnss-rtk-positioning); wave-44 closed tdoa-positioning via the manufacturing-quality
acoustic-emission-inspection claim.
Mode: read-only except this receipt. No git add/commit/push, no edits to skills/, eval/,
docs/, Makefile, scripts/, ops/automation briefs, standards-map.yaml.

## Verdict

4 GO candidates, all in the navigation/optimal-control/control/estimation seams that the
existing leaves do not own, ranked below with full gate evidence (a-f each). 4 additional
near-misses declined with one-line reasons and sim receipts. Navigation and guidance
veins are the most contested: every guidance near-miss is fenced by planar leaves or the
avionics LNAV owner, and the closest navigation near-miss (time-differenced-carrier-phase)
cannot clear the wordable Hit@1 gate against the doppler sibling. tdoa-positioning stays
CLOSED: the acoustic-emission claim of the generic hyperbolic iterated-LS math is
re-verified and quoted below.

## Family inventory (52 leaves, 6 packs, parity confirmed)

Enumerated with `find skills/gnc-autonomy -mindepth 3 -name SKILL.md` (52; family router
at skills/gnc-autonomy/SKILL.md excluded):

- control 11: adaptive-control, control-allocation, digital-control-design,
  frequency-response-design, gain-scheduling, lead-lag-compensation, observer-design,
  pid-control-design, python-control-design, root-locus-design, state-space-analysis
- estimation-filtering 9: alpha-beta-filter, complementary-filter, extended-kalman-filter,
  imu-static-calibration, interacting-multiple-model-filter, particle-filter,
  process-noise-discretization, rts-smoother, unscented-kalman-filter
- guidance 9: augmented-proportional-navigation, collision-course-guidance,
  command-to-line-of-sight, coverage-path-planning, dubins-path-planning,
  impact-point-prediction, midcourse-guidance, proportional-navigation, pursuit-guidance
- navigation 13: bearing-only-localization, dilution-of-precision, gnss-carrier-smoothing,
  gnss-doppler-velocity-positioning, gnss-pseudorange-positioning, gnss-raim-fde,
  gnss-rtk-positioning, inertial-navigation, ins-gnss-integrated-filter,
  kalman-filter-design, navigation-frames, terrain-referenced-navigation,
  tightly-coupled-ins-gnss
- optimal-control 6: bang-bang-control, dymos-trajectory, ilqr-ddp, lqg-design,
  lqr-design, model-predictive-control
- space 4: attitude-dynamics, orbit-determination, orbit-dynamics, rendezvous-phasing

Note: the wave-45 brief per-pack split (control 12, guidance 8) does not match disk
(control 11, guidance 9); totals agree at 52. Corpus: 105 tasks route to gnc leaves
(52 x 2 plus one extra pid-control task).

## Ranked GO with evidence

### GO 1: gnc-autonomy/optimal-control/loop-transfer-recovery

One-line why: lqg-design's own fence leaves loop-shape recovery open, the topic is
zero-owner tree-wide, and both wordable Hit@1 queries win by wide margins in router
simulation with zero theft.

(a) Zero-owner grep, whole skills/ tree:
`grep -rniE 'loop[- ]transfer[- ]recovery|ltr design' skills/ --include=SKILL.md -l`
-> 0 hit(s). Frontmatter scan for 'loop.transfer.recovery' also 0 owners, 0 body
mentions.

(b) Quoted sibling fence (nearest owner lqg-design, Pitfalls):
"Carrying the leaf outside its family: general n-state Riccati solvers, discrete-time LQG
over sampled measurement streams is out of scope here (see kalman-filter-design), and
shaping the loop gain toward full-state recovery is not implemented in this leaf."
(skills/gnc-autonomy/optimal-control/lqg-design/SKILL.md lines 201-204). Explicit open
seam. frequency-response-design owns margin computation only, not recovery design.

(c) Standards-map id that exists: `grep -n 'id: arp4754a' standards-map.yaml` -> line 38
(ARP4754A reference-only convention used by every optimal-control sibling).

(d) Published deterministic anchor: output-side loop-transfer-recovery of an LQG
compensator, recovering the full-state loop by inflating the filter noise weight
Q = Q0 + q^2 B B^T and re-solving the filter algebraic Riccati equation per q until the
recovered loop matches the full-state target loop. Equation family: filter Riccati ARE
plus loop-gain comparison. Source: Doyle and Stein, "Multivariable feedback design:
concepts for a classical/modern synthesis," IEEE Transactions on Automatic Control
TAC-26(1):4-16, 1981; textbook treatment Maciejowski, Multivariable Feedback Design
(1989) chapter 5. Deterministic offline: same two-ARE machinery lqg-design already
ships, plus a recovery loop.

(e) Two wordable Hit@1 corpus queries, sim-verified against the full 623-SKILL.md tree
plus the candidate (token router replicated from scripts/router_eval.py, hyphenated
tokens, tag weight 3):
1. "design a loop-transfer-recovery controller for the lqg compensator: inflate the
   process noise weight q on the driven input channel and recover the full-state loop
   transfer function at the plant output" -> HIT1, 19.0 vs 14.0 (lqg-design).
2. "run loop-transfer-recovery on the lqg design: increase the recovery gain until the
   recovered output loop singular values match the target-feedback-loop full-state loop"
   -> HIT1, 18.0 vs 7.5 (lqg-design).
Theft audit over all 1238 existing corpus tasks: 0 tasks reroute to the candidate.

(f) Tag set all hyphenated compounds, no generic single-word tags:
loop-transfer-recovery, full-state-loop-recovery, lqg-loop-shaping, recovery-gain-tuning,
target-feedback-loop.

### GO 2: gnc-autonomy/control/l1-adaptive-control

One-line why: the adaptive-control leaf owns first-order MRAC only, L1 adaptive control
(state predictor plus low-pass-filtered adaptation) is zero-owner tree-wide, and two
natural queries route Hit@1 in simulation with clean margins.

(a) Zero-owner grep, whole skills/ tree:
`grep -rniE 'l1[- ]adaptive|state predictor' skills/ --include=SKILL.md -l`
-> 0 hit(s). Frontmatter scan for 'l1.adaptive' and 'state.predictor': 0 owners.

(b) Quoted sibling fence (nearest owner adaptive-control, description):
"Use when you must design and simulate a model-reference adaptive controller (MRAC) for a
first-order plant with an unknown plant coefficient: run the reference model from the
command, form the control as the sum of a state-feedback term and a feedforward term with
adaptive gains, update the gains online with the gradient (Lyapunov-motivated) adaptation
law scaled by the tracking error". The MRAC leaf claims the model-reference/gradient
architecture; it never claims the L1 architecture (state predictor, projection-based
adaptation, low-pass-filtered control signal, transient bounds). No L1 mention anywhere
in its body.

(c) Standards-map id that exists: `grep -n 'id: arp4754a' standards-map.yaml` -> line 38
(ARP4754A reference-only, control-pack convention).

(d) Published deterministic anchor: L1 adaptive control for a first-order uncertain
plant: state predictor x_hat_dot = a_m x_hat + b (u + sigma_hat), projection-based
adaptive law on the prediction error, control with the low-pass filter
C(s) = omega_c / (s + omega_c) on the adaptive signal. Equation family: predictor plus
projection adaptation plus first-order low-pass filter. Source: Cao and Hovakimyan, L1
Adaptive Control Theory: Guaranteed Robustness with Fast Adaptation, SIAM, 2010 (and the
2006/2007 IEEE TAC and ACC papers). Deterministic offline closed-form updates, same class
as the sibling MRAC simulation leaf.

(e) Two wordable Hit@1 corpus queries, sim-verified:
1. "design an l1-adaptive-control law for the first order plant with unknown coefficient:
   run the state-predictor and the low-pass-filtered projection adaptation law and report
   the tracking error" -> HIT1, 18.0 vs 14.0 (adaptive-control).
2. "run the l1-adaptive-control simulation: propagate the state-predictor with the
   low-pass-filtered adaptation term and the projection based adaptation law and verify
   the transient bound of the tracking error" -> HIT1, 17.0 vs 10.5 (adaptive-control).
Theft audit: 0 of 1238 existing tasks reroute (the existing MRAC tasks carry mrac /
model-reference-adaptive tokens and keep their owner).

(f) Tag set all hyphenated compounds:
l1-adaptive-control, state-predictor, low-pass-filtered-adaptation,
projection-based-adaptation-law, guaranteed-transient-response.

### GO 3: gnc-autonomy/estimation-filtering/cramer-rao-lower-bound

One-line why: estimation-performance bounds are zero-owner across the tree (the only
cramer hit is Cramer's rule in a torsion leaf), the filter leaves own recursive estimators
but no variance bound, and the candidate wins both sim queries by wide margins.

(a) Zero-owner grep, whole skills/ tree:
`grep -rniE 'cramer|fisher information' skills/ --include=SKILL.md -l`
-> 1 hit: skills/structures/fem/torsion-shear-flow/SKILL.md (line 54 "solved by Cramer's
rule", a linear-system solver, not Cramer-Rao). Frontmatter scan for 'cramer' and
'fisher.information': 0 owners. The only fisher frontmatter owner anywhere is
cross-cutting/numerics/fisher-exact-test (Fisher's exact categorical test, unrelated).

(b) Quoted sibling fence (nearest owner unscented-kalman-filter, body):
"NEES: normalized estimation error squared, (x_est - x_true)^T P_est^-1 (x_est - x_true).
Its expected value is n for a consistent filter; averaged over many Monte Carlo runs NEES
should sit near n". The UKF owns the post-hoc consistency metric for its own run. No
estimation leaf claims the pre-data variance bound (Fisher information, Cramer-Rao lower
bound), which is a different quantity.

(c) Standards-map id that exists: `grep -n 'id: arp4754a' standards-map.yaml` -> line 38
(ARP4754A reference-only, estimation-filtering-pack convention).

(d) Published deterministic anchor: Fisher information
I(theta) = -E[d^2 ln p(x; theta) / d theta^2] and the Cramer-Rao lower bound
var(theta_hat) >= 1 / I(theta), vector form CRLB = I(theta)^-1, with the equality cases
(DC level in white Gaussian noise: var >= sigma^2 / N). Equation family: log-likelihood
second-derivative identity, information matrix inversion. Source: Kay, Fundamentals of
Statistical Signal Processing: Estimation Theory (1993) chapter 3; Van Trees, Detection,
Estimation, and Modulation Theory, Part I (1968). Deterministic offline closed form for
the canonical scalar and vector cases.

(e) Two wordable Hit@1 corpus queries, sim-verified:
1. "compute the cramer-rao-lower-bound for the scalar dc level in gaussian noise: build
   the fisher-information-matrix and report the best achievable variance" -> HIT1, 17.0
   vs 6.0 (manufacturing-quality additive leaf, distant).
2. "check whether the maximum likelihood estimator reaches the cramer-rao-lower-bound:
   compare the sample covariance to the fisher-information-matrix inverse and report the
   estimator efficiency" -> HIT1, 15.0 vs 7.0 (observer-design).
Theft audit: 0 of 1238 existing tasks reroute.

(f) Tag set all hyphenated compounds:
cramer-rao-lower-bound, fisher-information-matrix, estimator-efficiency,
best-achievable-variance, bound-achieving-estimator.

### GO 4: gnc-autonomy/navigation/ionospheric-delay-correction (conditional)

One-line why: the Klobuchar broadcast delay model is zero-owner, the navigation siblings
own only the divergence check and the post-fit residual mapping (never the per-source
delay model), and both sim queries Hit@1, but existing corpus demand is zero so spec it
only if the plan pool needs a fourth gnc leaf.

(a) Zero-owner grep, whole skills/ tree:
`grep -rniE 'klobuchar' skills/ --include=SKILL.md -l` -> 0 hit(s). Frontmatter scan for
'klobuchar': 0 owners; 'ionospheric' frontmatter owner is only gnss-carrier-smoothing
(divergence check context, quoted below).

(b) Quoted sibling fences:
gnss-carrier-smoothing body: "Ionospheric divergence: the code is delayed by +I while the
carrier is advanced by -I, so the smoothed range carries a growing code-minus-carrier
divergence error whose tau >> T form is -2*(dI/dt)*tau." The leaf owns the divergence
monitor, not the delay model.
gnss-pseudorange-positioning body: "Post-fit position error: pos_1sigma = uere_equiv *
pdop with uere_equiv = residual RMS". The positioning leaf works on pseudoranges as given
and maps residuals to position error; no leaf computes a per-source delay correction.

(c) Standards-map id that exists: `grep -n 'id: rtca-do-229' standards-map.yaml` -> line
303 (RTCA DO-229 GPS/GNSS MOPS, the convention of every GNSS navigation sibling). The
Klobuchar model text lives in IS-GPS-200 section 20.3.3.5.1, cited by reference under the
reference-only rule.

(d) Published deterministic anchor: Klobuchar broadcast ionospheric delay algorithm:
pierce-point geomagnetic latitude from user and satellite position, amplitude and period
polynomials A_n and P_n from the broadcast alpha and beta coefficients, vertical delay
5e-9 + sum A_n phi_m^n seconds, obliquity factor from elevation. Equation family:
spherical-geometry pierce point plus quartic polynomials in geomagnetic latitude plus
elevation obliquity. Source: Klobuchar, "Ionospheric Time-Delay Algorithm for
Single-Frequency GPS Users," IEEE Transactions on Aerospace and Electronic Systems
AES-23(3):325-331, 1987; IS-GPS-200. Deterministic offline closed form given the
broadcast coefficients.

(e) Two wordable Hit@1 corpus queries, sim-verified:
1. "apply the klobuchar-broadcast-model to the L1 pseudorange with the alpha and beta
   coefficients: compute the pierce-point geometry and the slant ionospheric delay
   correction" -> HIT1, 15.0 vs 7.0 (rocket-nozzle-divergence-loss, distant).
2. "compute the klobuchar broadcast model slant delay: evaluate the broadcast alpha and
   beta coefficient polynomials at the pierce point elevation and subtract the
   ionospheric delay correction from the L1 pseudorange" -> HIT1, 17.0 vs 7.5
   (stability-derivatives-avl, distant).
Theft audit: 0 of 1238 existing tasks reroute; the only existing ionospheric task
(w42-gnss-carrier-smoothing-2) keeps its owner because it asks for the divergence check.

(f) Tag set all hyphenated compounds:
klobuchar-broadcast-model, ionospheric-delay-correction, slant-delay-correction,
pierce-point-geometry, broadcast-alpha-beta-coefficients.

## Declines table (near-miss per plausible gap, probed FRESH)

| Near-miss candidate | Gate(s) | Decline reason |
|---|---|---|
| navigation/tdoa-positioning (reserve class) | b | Re-checked per wave-45 brief: acoustic-emission-inspection claims the generic hyperbolic iterated-LS math, body line 58-62: "planar location triangulates from three or more sensors by solving the hyperbolic time-difference system with an iterative least-squares scheme", and its shipped logic docstring states "Each pair (i, 0) gives the hyperbolic constraint d_i - d_0 = v*(t_i - t_0). The system is linearized around the current guess and solved as a 2x2 normal system (Cramer), iterating from the sensor centroid to convergence". The AE fence owns the deterministic core of a 2D TDOA leaf; wave-44 ruling reaffirmed. Zero tdoa token anywhere else. Reopen only if the AE leaf drops the generic claim. |
| navigation/time-differenced-carrier-phase-positioning | e | Genuine zero-owner gap (grep 0) with a real anchor (van Graas and Soloviev, Navigation 51(2), 2004), but the wordable Hit@1 gate fails: sim query 1 wins by only 2.0 over gnss-doppler-velocity-positioning (23.0 v 21.0) and query 2 is STOLEN by the doppler leaf (17.5 v 17.0) because its desc and body saturate the shared velocity/clock-drift/epoch vocabulary; no honest phrasing separates two queries without tag-stuffing. |
| navigation/gnss multipath and range error budget | b, d | dilution-of-precision owns the UERE-to-position mapping ("A pseudorange error with standard deviation sigma gives a position error standard deviation of pdop * sigma") and gnss-pseudorange-positioning owns the post-fit uere_equiv; per-source multipath magnitudes are empirical tables with no closed-form anchor; zero corpus tasks (multipath, uere, pseudorange-error all 0 of 1238). |
| navigation/tilt-compensated-magnetic-heading | b, d | Heading-from-magnetometer anchors only in vendor application-note literature (no canonical published closed-form source); the magnetometer attitude vein is owned by complementary-filter (so3 mag fusion), space-systems magnetometer-calibration (hard/soft iron) and attitude-determination-triad; zero corpus tasks (magnetic heading, compass heading, tilt-compensated all 0). |
| navigation/air-data-dead-reckoning | b, d | Elementary kinematics adjacent to flight-mechanics wind-effects (owns the wind triangle) and inertial-navigation; drift-error growth is generic Gaussian propagation owned by the cross-cutting uncertainty-propagation seam; no distinct published closed-form anchor; zero corpus tasks; sim query 2 margin only 3.0. |
| guidance/trajectory-shaping law | a | midcourse-guidance owns trajectory-shaping as tag, trigger and body claim ("Shape the midcourse flight of an interceptor ... shape ascent trajectories", trigger "trajectory shaping"); zero-owner grep fails (2 SKILL.md hits including the family router). |
| guidance/true-proportional-navigation and PN variants | b, e | proportional-navigation and augmented-proportional-navigation own the planar LOS-rate geometry and commands; sim query 2 for a true-PN leaf is STOLEN (aeroelastic-gust-response, 7.0 v 6.5) and query 1 margin is thin (14.0 v 10.5 pursuit-guidance); zero corpus tasks for true/pure PN tokens; guidance vein 9 leaves deep with no fence gap. |
| guidance/3D engagement geometry | b, e | The 3D LOS-rate vector geometry is the same command math the planar PN leaves own in scalar form; any natural 3D query shares the line-of-sight-rate/closing-velocity vocabulary and cannot Hit@1 cleanly; zero corpus tasks (three-dimensional, los rate beyond the 2 existing PN/CLOS tasks). |
| guidance/waypoint path following (cross-track heading law) | b | avionics/flight-management/lateral-navigation owns the LNAV cross-track and track-angle error tasks (w25), command-to-line-of-sight owns cross-track-offset, midcourse-guidance owns waypoint steering; zero corpus tasks for path following; no fence gap. |
| estimation/observability-analysis standalone | a | state-space-analysis owns "form the controllability and observability matrices, decide controllability and observability from their ranks" (description quote) plus observer-design and four iterated-LS navigation leaves carry the observability language; nonlinear Lie-rank observability is niche with zero corpus tasks. |
| estimation/NEES and covariance consistency checks | a | unscented-kalman-filter owns nees in description trigger, tags and body ("the NEES consistency metric that gate a nonlinear estimation assessment", body formula quoted under GO 3); zero-owner grep fails (2 hits incl. family router). |
| optimal-control/LQR gain and phase margin robustness | b | frequency-response-design owns gain/phase margin computation (description: "gain margin, phase margin, or stability from the margins") and pid/lead-lag siblings own margin design; the Kalman-1964 LQR margin property is theorem citation, not a leaf computation; zero corpus tasks. |
| optimal-control/finite-horizon differential Riccati | b, e | ilqr-ddp owns the discrete backward-Riccati pass (task "compute the iterative-lqr backward-riccati-pass gains"), lqr-design and lqg-design own both algebraic Riccati equations; the continuous DRE specialization has zero corpus tasks and no standalone aerospace framing. |
| control/L1-adjacent direct MRAC extensions (state feedback MRAC, output MRAC) | b | adaptive-control's fence is first-order MRAC only and its body explicitly keeps the leaf in that scope; extensions belong inside the existing leaf, and zero corpus tasks phrase any MRAC variant. |

## Closed veins (owner leaf per vein, reaffirmed FRESH)

- GNSS positioning: gnss-pseudorange-positioning (code fix), gnss-doppler-velocity-positioning
  (single-epoch doppler velocity), gnss-carrier-smoothing (Hatch recursion plus
  ionospheric-divergence check), gnss-rtk-positioning (double-difference baseline and
  integer ambiguity), gnss-raim-fde (protection level and chi-square), dilution-of-precision
  (DOP and UERE position-error mapping). Closed except the GO 4 seam (per-source delay
  model) and the declined TDCP variant.
- Passive localization: bearing-only-localization (Stansfield iterated LS on bearing
  lines). Hyperbolic TDOA localization: closed by manufacturing-quality
  acoustic-emission-inspection (quote under declines). Closed.
- INS and integration: inertial-navigation (error growth, Schuler, gyrocompass alignment),
  ins-gnss-integrated-filter (loose psi-angle), tightly-coupled-ins-gnss (tight, raw
  pseudoranges), terrain-referenced-navigation (radar-altimeter correlation and
  point-mass). Navigation-frames (WGS-84/ECEF/NED). Closed.
- Estimation filters: alpha-beta-filter, complementary-filter (Mahony so3, magnetometer
  vector fusion), extended-kalman-filter, unscented-kalman-filter (incl. NEES),
  interacting-multiple-model-filter, particle-filter, rts-smoother,
  process-noise-discretization (van Loan), imu-static-calibration (six-position and rate
  table), kalman-filter-design (single axis). Closed, except the variance-bound seam
  (GO 3).
- Guidance laws: pursuit-guidance (pure and lead pursuit), proportional-navigation (planar),
  augmented-proportional-navigation (maneuvering target), command-to-line-of-sight,
  collision-course-guidance, midcourse-guidance (waypoint steering, velocity-to-be-gained,
  zero-effort-miss, trajectory shaping, handover), impact-point-prediction,
  coverage-path-planning, dubins-path-planning. Planar vein closed; 3D and variant seams
  declined above.
- Optimal control: bang-bang-control, lqr-design (ARE), lqg-design (dual ARE, separation;
  loop recovery explicitly not implemented, GO 1 seam), model-predictive-control,
  ilqr-ddp (discrete backward Riccati), dymos-trajectory (pseudospectral, external tool).
  Closed except the LTR seam (GO 1).
- Adaptive control: adaptive-control (first-order MRAC). Closed except the L1 architecture
  (GO 2).

## Method notes

Probe steps executed: (1) find enumeration of all 52 leaves plus family router; (2)
frontmatter fence dump of all 52 (description, standards, metadata tags); (3) family
router and prior-wave receipts read (wave44-leaf-plan gnc rows, wave-44 closed-vein
rulings); (4) standards-map.yaml id dump (30 ids; arp4754a at line 38, rtca-do-229 at
line 303, arinc-429 at line 204); (5) zero-owner grep battery over the whole skills tree
for 40+ tokens covering TDOA, TDCP, multipath, UERE, Klobuchar, magnetometer heading,
dead reckoning, Cramer-Rao/Fisher, observability, NEES, trajectory shaping, PN variants,
3D geometry, LTR, L1 adaptive, Riccati variants (helpers at /tmp/w45_t6/probe.py and
evidence.py, direct greps quoted per gate a); (6) sibling fence reads of the 12 nearest
owners (quotes above); (7) corpus demand scan over all 1238 eval/hit1-corpus.yaml tasks
on the query and intent fields (helpers at /tmp/w45_t6/corpus_battery2.py); (8) router
Hit@1 simulation (token router replicated from scripts/router_eval.py: hyphen-preserving
tokens, tag weight 3, name 2, desc 1, body 0.5, full-phrase bonus 4, tie-break by path)
over the real 623-SKILL.md tree plus each hypothetical candidate, checking the 2 crafted
queries Hit@1 with margin and a zero-theft audit of all 1238 existing tasks
(/tmp/w45_t6/sim.py, output /tmp/w45_t6/sim_out.txt); (9) git status clean before and
after; no files modified outside this receipt.

Recheck reminders for future waves: TDCP is the only methodically real but declined
near-miss; reopen if the doppler sibling fence narrows (single-epoch doppler only) AND a
corpus intent for between-epoch phase-delta velocity appears, or if the router gains
multi-word phrase scoring. tdoa-positioning reopens only if acoustic-emission-inspection
drops the generic hyperbolic iterated-LS claim. GO 4 (ionospheric-delay-correction) is
conditional on pool size, not on gates.
