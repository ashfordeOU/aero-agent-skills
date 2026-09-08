# WAVE-46 GNC-AUTONOMY PROBE RECEIPT (task-7, whole-family FRESH)

- Repo: the local AeroSkills repo at ~/AeroSkills, git HEAD 45931c16 (verified
  `git log --oneline -3`: 45931c16 fix(audit) / 8933b003 / 4fc1bdfa; working
  tree clean at probe start except the parallel wave46-recon receipts).
- Scope: ENTIRE gnc-autonomy family, 55 leaves, probed FRESH at wave-46 HEAD.
  Read-only probe: no writes to skills/, eval/, standards-map.yaml, scripts/,
  Makefile, or ops/automation briefs. One write only: this receipt.
  Helpers in /tmp/w46_t7/ (dump_fences.py, sim.py, theft.py).
- Corpus baseline: eval/hit1-corpus.yaml = 1266 tasks (regex parse recovered
  1266/1266 task blocks); 111 tasks target gnc-autonomy leaves (2 per leaf +
  one extra pid-control-design task, parity confirmed against the 55-leaf
  find).
- Standards map: 30 ids in standards-map.yaml; candidate ids grep-verified
  below (arp4754a line 38, rtca-do-229 line 303, far-25 line 16, cs-25 line
  27).
- Prior-wave context read: wave-45 gnc receipt
  (ops/automation/state/wave45-recon/task-6-receipt.md, HEAD 5cc8fef3) and the
  wave-45 leaf plan, which DROPPED ionospheric-delay-correction at spec time
  purely on pool size ("CONDITIONAL on pool. Pool is 15; likely DROP at spec
  time to keep the gnc contribution at 3", wave45-leaf-plan.md line 186-187)
  AFTER it had cleared every gate a-f in the wave-45 receipt. That pool-drop
  is the only reason it is not on disk at wave-46 HEAD, and the wave-46 brief
  (item 8) declares gnc-autonomy "NOT saturated". It is re-issued below as a
  full GO with gates re-verified FRESH at this HEAD.

## Verdict

3 GO candidates, all seams the wave-45 receipt did NOT close and wave-46
doctrine names (navigation/guidance/control veins), ranked below with full
gate evidence (a-f each): navigation/ionospheric-delay-correction (the
wave-45 pool-dropped GO4, re-verified), guidance/impact-time-control-guidance
(fresh seam: salvo/impact-time tokens zero-owner tree-wide AND zero corpus),
control/deadbeat-control (fresh seam: deadbeat token zero-owner). 10 wave-45
declines re-verified with fresh evidence in the declines table below, all
STAND; tdoa-positioning fence re-checked vs manufacturing-quality
acoustic-emission-inspection as the brief ordered, still CLOSED (fresh quotes
below). Fresh seams probed and declined this wave: information-filter (KF
form-variant, family filter vein deep, trigger-claimed "sensor fusion"),
minimum-fuel-control/bang-off-bang (free-final-time minimum-fuel problem is
degenerate: infimum-zero unattained, so no clean station closed form; fixed-
time variant needs switching-time root solves), impact-angle-control-guidance
(PN-augmentation family, zero corpus). Closed veins list at the end.

## Whole-family enumeration (55 leaves, 6 packs, parity confirmed)

`find skills/gnc-autonomy -mindepth 3 -name SKILL.md` returned 55 files
(family router skills/gnc-autonomy/SKILL.md excluded; router rows counted per
pack below and agree with the find). Wave-45 +3 landed: loop-transfer-recovery
(optimal-control), l1-adaptive-control (control), cramer-rao-lower-bound
(estimation-filtering). Wave-45 conditional GO4 (ionospheric-delay-correction)
NOT on disk — navigation pack still 13, no ionospheric leaf anywhere.

- control 12: adaptive-control, control-allocation, digital-control-design,
  frequency-response-design, gain-scheduling, l1-adaptive-control,
  lead-lag-compensation, observer-design, pid-control-design,
  python-control-design, root-locus-design, state-space-analysis
- estimation-filtering 10: alpha-beta-filter, complementary-filter,
  cramer-rao-lower-bound, extended-kalman-filter, imu-static-calibration,
  interacting-multiple-model-filter, particle-filter,
  process-noise-discretization, rts-smoother, unscented-kalman-filter
- guidance 9: augmented-proportional-navigation, collision-course-guidance,
  command-to-line-of-sight, coverage-path-planning, dubins-path-planning,
  impact-point-prediction, midcourse-guidance, proportional-navigation,
  pursuit-guidance
- navigation 13: bearing-only-localization, dilution-of-precision,
  gnss-carrier-smoothing, gnss-doppler-velocity-positioning,
  gnss-pseudorange-positioning, gnss-raim-fde, gnss-rtk-positioning,
  inertial-navigation, ins-gnss-integrated-filter, kalman-filter-design,
  navigation-frames, terrain-referenced-navigation, tightly-coupled-ins-gnss
- optimal-control 7: bang-bang-control, dymos-trajectory, ilqr-ddp,
  loop-transfer-recovery, lqg-design, lqr-design, model-predictive-control
- space 4: attitude-dynamics, orbit-determination, orbit-dynamics,
  rendezvous-phasing

Router parity: 9 guidance rows, 13 navigation rows counted in the family
router SKILL.md; find and router totals agree at 55. Corpus: 111 gnc tasks
(55 x 2 plus one extra pid-control task), 0 orphans.

## Ranked GO with evidence

### GO 1: gnc-autonomy/navigation/ionospheric-delay-correction

One-line why: wave-45 GO4 cleared every gate and was dropped only on pool
size; at wave-46 HEAD the Klobuchar broadcast delay model is STILL zero-owner
tree-wide and zero corpus, both wordable Hit@1 queries win by 12.5+ points in
router simulation with zero theft, and rtca-do-229 exists for the GNSS-sibling
convention.

(a) Zero-owner grep, whole skills/ tree, FRESH:
`grep -rniE 'klobuchar' skills/ --include=SKILL.md -l` -> 0 hit(s) (exit 1).
Frontmatter scan for 'klobuchar': 0 owners. The only 'ionospheric' owners
tree-wide are gnss-carrier-smoothing (divergence-monitor context) and the
family router row for it.

(b) Quoted sibling fences (FRESH reads):
gnss-carrier-smoothing body line 68-73: "Ionospheric divergence: the code is
delayed by +I while the carrier is advanced by -I, so the smoothed range
carries a growing code-minus-carrier divergence error whose tau >> T form is
-2*(dI/dt)*tau." That leaf owns the divergence MONITOR and its fence line 39
explicitly lists "cycle-slip repair and integer ambiguity resolution are out
of scope" — no per-source delay model.
gnss-pseudorange-positioning body line 53-54: "Post-fit position error:
pos_1sigma = uere_equiv * pdop with uere_equiv = residual RMS". Positioning
works on pseudoranges as given; no leaf computes a per-source ionospheric
delay correction.

(c) Standards-map id exists (grep-verified):
`grep -n 'id: rtca-do-229' standards-map.yaml` -> line 303 (RTCA DO-229,
the convention of every GNSS navigation sibling; Klobuchar text sits in
IS-GPS-200 section 20.3.3.5.1, cited by name only under the reference-only
rule).

(d) Published deterministic anchor (summary-only): Klobuchar broadcast
ionospheric delay algorithm — pierce-point geomagnetic latitude from user and
satellite geometry, amplitude and period as quartic polynomials in the
broadcast alpha and beta coefficients, vertical delay
5e-9 + sum A_n phi_m^n seconds, elevation obliquity factor applied for the
slant correction. Equation family: spherical pierce-point geometry plus
quartic-in-latitude polynomials plus obliquity. Source: Klobuchar,
"Ionospheric Time-Delay Algorithm for Single-Frequency GPS Users," IEEE
TAES AES-23(3):325-331, 1987; IS-GPS-200. Deterministic offline closed form
given the broadcast coefficients.

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-46 HEAD with the
token router replicated from scripts/router_eval.py (hyphen-preserving
tokens, tags weight 3, name 2, desc 1, body 0.5, phrase bonus 4, tie-break
path asc) over the real 626-SKILL.md tree plus the candidate:
1. "apply the klobuchar-broadcast-model to the L1 pseudorange with the alpha
   and beta coefficients: compute the pierce-point geometry and the slant
   ionospheric delay correction" -> HIT1 at 19.5 vs 7.0
   (propulsion/rocket/rocket-nozzle-divergence-loss).
2. "compute the klobuchar broadcast model slant delay: evaluate the broadcast
   alpha and beta coefficient polynomials at the pierce point elevation and
   subtract the ionospheric delay correction from the L1 pseudorange" ->
   HIT1 at 24.0 vs 7.5 (flight-mechanics/stability-control/
   stability-derivatives-avl).
Theft audit (theft.py over all 1266 corpus tasks): 0 tasks reroute to the
candidate.

(f) Tag set all hyphenated compounds, no generic single words:
klobuchar-broadcast-model, ionospheric-delay-correction, slant-delay-
correction, pierce-point-geometry, broadcast-alpha-beta-coefficients.

### GO 2: gnc-autonomy/guidance/impact-time-control-guidance

One-line why: impact-time/salvo tokens are zero-owner across the whole tree
AND zero in the 1266-task corpus, no guidance sibling's fence claims the
time-constrained terminal law (midcourse owns handover/trajectory-shaping,
impact-point-prediction is open-loop ballistic), and both sim queries Hit@1
with clean margins and zero theft.

(a) Zero-owner grep, whole skills/ tree, FRESH:
`grep -rniE 'impact[- ]time|salvo|impact[- ]angle' skills/ --include=SKILL.md
-l` -> 0 hit(s) (exit 1). Corpus scan (impact-time-control, salvo,
simultaneous-impact, impact-angle): 0 of 1266 tasks. No mention in any
ops/automation/state wave40-45 recon or leaf-plan file (scan of
wave40..wave46 state files: 0 hits outside this receipt's topic list).

(b) Quoted sibling fences (FRESH reads):
impact-point-prediction body (lines 6-8 area): "Use when the task is
predicting where an unguided ballistic projectile lands from its launch
state: range, time of flight, impact..." — open-loop, unguided, no guidance
command. midcourse-guidance body line 34-35: steering to "a waypoint, a
constraint corridor, a handover geometry" rather than "to the target
directly; a terminal law (proportional navigation, pursuit, ...)" owns the
handover trigger and ZEM/trajectory-shaping (tags waypoint-steering,
trajectory-shaping, zero-effort-miss, handover-condition) — no claim over a
commanded-impact-time terminal law. augmented-proportional-navigation adds
only "the target lateral acceleration perpendicular to the line of sight
scaled by half the effective navigation ratio" (desc) — maneuvering-target
augmentation, not time-of-arrival control. proportional-navigation owns the
unaugmented planar law; its augmented sibling's Related-leaves fence:
"proportional-navigation: the unaugmented proportional navigation law ...;
this leaf adds the target-lateral-acceleration augmentation term on top."
No leaf in the guidance pack claims simultaneous-arrival / salvo / impact-time
error feedback.

(c) Standards-map id that exists: `grep -n 'id: arp4754a' standards-map.yaml`
-> line 38 (ARP4754A reference-only; proportional-navigation and the other
intercept-law siblings carry arp4754a as their convention).

(d) Published deterministic anchor (summary-only): impact-time-control
guidance (ITCG) laws that shape the command to steer an interceptor group to
a common commanded impact time — canonical form: proportional-navigation
baseline command plus an impact-time-error feedback term driven by
time-to-go, with the feedback gain scheduled on the engagement state. Source:
Jeon, Lee and Tahk, "Impact-time-control guidance law for anti-ship
missiles," IEEE Transactions on Aerospace and Electronic Systems 42(2):629-
641, 2006 (deterministic command computation for a commanded impact time;
the classic reference of the salvo-attack literature). Deterministic offline
closed-form command evaluation given the closing geometry, the navigation
constant and the commanded impact time.

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-46 HEAD:
1. "compute the impact-time-control-guidance command for the salvo attack:
   form the proportional navigation baseline from the line of sight rate and
   closing velocity, estimate time to go, and add the impact-time-error
   feedback term scaled by the navigation constant" -> HIT1 at 32.0 vs 21.5
   (gnc-autonomy/guidance/augmented-proportional-navigation).
2. "run the impact-time-control-guidance law so the interceptor group arrives
   at the commanded-impact-time: evaluate the time-to-go-error-feedback term
   and report the simultaneous-impact guidance command" -> HIT1 at 20.0 vs
   7.0 (gnc-autonomy/control/adaptive-control).
Theft audit: 0 of 1266 tasks reroute (existing PN/APN/CLOS tasks carry their
own law tokens and keep their owners).

(f) Tag set all hyphenated compounds:
impact-time-control-guidance, salvo-attack-guidance, commanded-impact-time,
time-to-go-error-feedback, simultaneous-impact-guidance.

### GO 3: gnc-autonomy/control/deadbeat-control

One-line why: deadbeat (finite-settling, all closed-loop poles at z = 0) is
zero-owner across the tree and corpus, the digital-control-design sibling
owns discretization/emulation/discrete-PID/stability/sample-rate but never a
direct deadbeat synthesis, and both wordable Hit@1 queries win by 7+ points
with zero theft in simulation.

(a) Zero-owner grep, whole skills/ tree, FRESH:
`grep -rniE 'deadbeat|dead[- ]beat' skills/ --include=SKILL.md -l` -> 0
hit(s) (exit 1). Corpus scan for deadbeat / finite-settling: 0 of 1266 tasks.
Frontmatter scan: 0 owners.

(b) Quoted sibling fence (nearest owner digital-control-design, desc):
"Use when you must design a sampled-data digital control loop in the
z-domain: discretize a continuous plant with a zero-order hold, emulate a
continuous compensator with the Tustin bilinear transform with frequency
prewarping, compute discrete PID coefficients in the position and velocity
forms, check the sampled poles against the unit circle for stability, and
select the sample rate from the closed-loop bandwidth." Its Related leaves
list pid-control-design, lead-lag-compensation, digital-filter-design
("signal-filter sibling (IIR Butterworth design); distinct scope, it shapes
signals, not control loops") and state-space-analysis — no deadbeat or
finite-settling design claim anywhere. pid-control-design owns continuous
pole placement "for a first or second order plant" in the s-domain only.

(c) Standards-map id that exists: `grep -n 'id: arp4754a' standards-map.yaml`
-> line 38 (ARP4754A reference-only, control-pack convention).

(d) Published deterministic anchor (summary-only): deadbeat control of a
discrete-time plant — choosing the controller so the closed-loop
characteristic polynomial is z^n = 0, driving the output to the reference in
a finite number of sample periods (settling in at most n samples for an
n-th-order plant) with the control sequence obtained by direct pole
placement at the origin of the z-plane. Source: Franklin, Powell and Workman,
Digital Control of Dynamic Systems, 3rd ed., ch. 4-5; Ogata, Discrete-Time
Control Systems, 2nd ed., ch. 6 (deadbeat response design). Deterministic
offline closed-form synthesis for the first/second-order discrete plants the
family convention already uses.

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-46 HEAD:
1. "design the deadbeat-control law for the discretized plant: place all
   closed loop poles at the origin of the z plane so the output settles in a
   finite number of sample periods and compute the minimum-settling-time
   control sequence" -> HIT1 at 27.5 vs 15.0
   (gnc-autonomy/control/digital-control-design).
2. "compute the z-domain deadbeat controller for the digital loop: solve the
   deadbeat design equation so the finite-settling-time response reaches the
   reference in N samples and report the control sequence" -> HIT1 at 18.0 vs
   11.0 (gnc-autonomy/control/digital-control-design).
Theft audit: 0 of 1266 tasks reroute.

(f) Tag set all hyphenated compounds:
deadbeat-control, finite-settling-time, pole-placement-at-origin,
minimum-settling-time, z-domain-deadbeat.

## Declines table (wave-45 rows re-verified FRESH; new seams probed this wave)

| Near-miss candidate | Gate(s) | Fresh evidence / decline reason |
|---|---|---|
| navigation/tdoa-positioning (brief-ordered fence re-check) | b | RE-CHECKED PER WAVE-46 BRIEF ITEM 8. Still CLOSED: manufacturing-quality acoustic-emission-inspection body (FRESH read, lines 58-62): "Source location: linear location uses two sensors on a line and the arrival-time difference; planar location triangulates from three or more sensors by solving the hyperbolic time-difference system with an iterative least-squares scheme." Logic docstring (scripts/acoustic_emission_inspection_logic.py lines 110-113): "Each pair (i, 0) gives the hyperbolic constraint d_i - d_0 = v*(t_i - t_0). The system is linearized around the current guess and solved as a 2x2 normal system (Cramer), iterating from the sensor centroid to convergence." The AE fence owns the deterministic core of a 2D TDOA leaf. Reopen only if the AE leaf drops the generic claim. |
| navigation/time-differenced-carrier-phase-positioning | e | STAY (wave-45): doppler fence FRESH quote lines 23-27: "estimate the 3-D ECEF velocity of a GNSS receiver and its receiver clock drift at a single epoch from per-satellite carrier-phase delta-range-rate (doppler) observables. Each tracked satellite is propagated from its broadcast-ephemeris Kepler elements..." The single-epoch doppler leaf and gnss-carrier-smoothing both own carrier-delta-range vocabulary; a TDCP leaf cannot clear wordable Hit@1 against them (wave-45 sim: stolen). Corpus 0 (tdcp/between-epoch-phase tokens 0 of 1266). |
| navigation/gnss multipath and range error budget | b, d | STAY: dilution-of-precision owns UERE-to-position mapping ("the 1-sigma position error from a user equivalent range error", desc) and gnss-pseudorange-positioning owns post-fit uere_equiv (quote under GO 1); per-source multipath magnitudes are empirical tables with no closed-form anchor; corpus 0 (multipath/uere query tokens 0). |
| navigation/tilt-compensated-magnetic-heading | b, d | STAY: FRESH grep 'tilt-compensated|magnetic heading|compass heading' over whole tree = 0 leaf owners AND 0 corpus tasks; heading-from-magnetometer anchors only in vendor application-note literature; complementary-filter (so3 mag fusion) + space-systems magnetometer-calibration own the magnetometer attitude vein. |
| navigation/air-data-dead-reckoning | b, d | STAY: FRESH grep 'dead reckoning|air-data-dead' = 0 owners, 0 corpus; elementary kinematics adjacent to inertial-navigation and flight-mechanics wind triangle; drift-error growth is generic Gaussian propagation owned by the cross-cutting uncertainty-propagation seam. |
| guidance/trajectory-shaping law | a | STAY: midcourse-guidance owns trajectory-shaping as tag, trigger and body claim (FRESH grep: only midcourse-guidance + family router match); zero-owner grep fails. |
| guidance/true-proportional-navigation and PN variants | b, e | STAY: proportional-navigation and augmented-proportional-navigation own the planar LOS-rate geometry; guidance vein now 9 leaves deep with the ITCG GO filling the one genuine gap; corpus 0 for true/pure-PN tokens. |
| guidance/3D engagement geometry | b, e | STAY: 3D LOS-rate geometry is the same command math the planar PN leaves own in scalar form; zero corpus; no fence gap. |
| guidance/waypoint path following | b | STAY: avionics lateral-navigation owns LNAV cross-track/track-angle tasks, command-to-line-of-sight owns cross-track-offset, midcourse-guidance owns waypoint steering; zero corpus; no fence gap. |
| estimation/observability-analysis standalone | a | STAY: state-space-analysis owns the observability-matrix/rank claim (desc), observer-design and the iterated-LS navigation leaves carry observability language; FRESH grep confirms same 4 owners as wave-45. |
| estimation/NEES and covariance consistency checks | a | STAY: unscented-kalman-filter owns nees in trigger, tags and body; FRESH grep: only UKF + family router. |
| optimal-control/LQR gain and phase margin robustness | b | STAY: frequency-response-design owns gain/phase margin computation; LQR-margin grep now also hits loop-transfer-recovery/ilqr-ddp/mpc bodies (margins as context), never as owners; Kalman-1964 property is theorem citation, not a leaf computation; corpus 0. |
| optimal-control/finite-horizon differential Riccati | b, e | STAY: ilqr-ddp owns the discrete backward-Riccati pass, lqr-design and lqg-design own both algebraic Riccati equations; continuous DRE specialization has zero corpus and no standalone aerospace framing. |
| control/L1-adjacent direct MRAC extensions | b | STAY: adaptive-control's fence is first-order MRAC; l1-adaptive-control (landed wave-45) now owns the L1 architecture; state-feedback/output-MRAC extensions belong inside the existing leaf; corpus 0. |
| estimation-filtering/information-filter (NEW this wave) | b | Fresh seam, zero-owner grep passes (information-filter/inverse-covariance 0 hits), sim Hit@1 passes (26.0 vs 13.0; 13.5 vs 9.5), but kalman-filter-design's own trigger claims "estimator design, sensor fusion, recursive least squares" and the information filter is the inverse-covariance algebraic form of the SAME single-axis KF the family owns; filter vein now 10 leaves deep (alpha-beta, complementary, ekf, ukf, imm, particle, rts, kf-design, process-noise, crlb); wave-45 precedent declined MRAC variants as "belong inside the existing leaf" — same rule applies; corpus 0. |
| optimal-control/minimum-fuel-control (bang-off-bang) (NEW this wave) | d | Fresh seam, zero-owner grep passes (fuel-optimal/min-fuel/bang-off-bang: only avionics performance-computation cost-index context, unrelated), sim Hit@1 passes (29.0 vs 14.0; 18.0 vs 10.5), but the free-final-time minimum-fuel double-integrator problem is degenerate — the fuel infimum is zero and unattained (thrust -> 0, time -> infinity), so there is no clean station closed form; the fixed-final-time formulation needs switching-time root solves and fuel-vs-time case splits; not clean closed-form per wave doctrine; corpus 0. |
| guidance/impact-angle-control-guidance (NEW this wave) | b, e | Zero-owner and zero corpus, but it is the impact-angle member of the same PN-augmentation family the ITCG GO fills this wave; one guidance-law leaf per wave for the seam family (midcourse already owns shaping-side impact-angle-adjacent trajectory shaping); revisit wave-47 if the pool needs it. |

## Closed veins (owner leaf per vein, reaffirmed FRESH)

- GNSS positioning: gnss-pseudorange-positioning (iterated-LS fix + post-fit
  uere_equiv), gnss-doppler-velocity-positioning (single-epoch doppler
  velocity; also propagates broadcast-ephemeris Kepler elements — the
  ephemeris-propagation token is claimed there), gnss-carrier-smoothing
  (Hatch recursion + ionospheric-divergence monitor; cycle-slip repair and
  integer ambiguity out of its scope), gnss-rtk-positioning (double-difference
  baseline + integer ambiguity), gnss-raim-fde (chi-square + protection
  level), dilution-of-precision (DOP + UERE position mapping + elevation mask
  + subset selection). Closed EXCEPT the per-source delay model seam (GO 1).
- Passive localization: bearing-only-localization (Stansfield iterated LS on
  bearing lines). Hyperbolic TDOA: closed by manufacturing-quality
  acoustic-emission-inspection (fresh quotes under declines). CLOSED.
- INS and integration: inertial-navigation, ins-gnss-integrated-filter (loose
  psi-angle), tightly-coupled-ins-gnss (tight, raw pseudoranges),
  terrain-referenced-navigation (TERCOM/SITAN), navigation-frames
  (WGS-84/ECEF/NED). CLOSED.
- Estimation filters: alpha-beta, complementary (Mahony so3), ekf, ukf (incl.
  NEES), imm, particle, rts-smoother, process-noise-discretization (van Loan),
  imu-static-calibration, kalman-filter-design (single axis), plus the
  variance-bound seam now OWNED (cramer-rao-lower-bound landed wave-45).
  CLOSED — information-filter form-variant declined this wave (see declines).
- Guidance laws: pursuit (pure and lead), proportional-navigation (planar),
  augmented-proportional-navigation (maneuvering target), command-to-line-of-
  sight, collision-course, midcourse (waypoints, VtG, ZEM, trajectory shaping,
  handover), impact-point-prediction (open-loop ballistic), coverage and
  dubins path planning. Planar vein closed except the impact-time/salvo seam
  (GO 2).
- Optimal control: bang-bang (time-optimal), lqr (ARE), lqg (dual ARE), mpc,
  ilqr-ddp (backward Riccati), dymos (pseudospectral), and loop-transfer-
  recovery now OWNED (landed wave-45). CLOSED (min-fuel seam declined this
  wave, see declines).
- Adaptive control: adaptive-control (first-order MRAC) and l1-adaptive-
  control now OWNED (landed wave-45). CLOSED.
- Space pack (4): attitude-dynamics, orbit-dynamics, orbit-determination,
  rendezvous-phasing — unchanged since wave-44; space-systems family (52,
  wave-46 task-6) is the saturated NO_CANDIDATES owner of the wider orbit/
  ADCS space. CLOSED at gnc-autonomy scope.

## Standards-map check

30 ids present (grep '^  - id:' = 30): arp4754a (line 38), rtca-do-229 (line
303), far-25 (line 16), cs-25 (line 27), plus the wave-46 full set. GO 1 uses
rtca-do-229 reference-only (GNSS convention, Klobuchar text in IS-GPS-200
cited by name); GO 2 and GO 3 use arp4754a reference-only (guidance and
control pack conventions). No new standards ids required; all candidates map
onto existing ids.

## Method note

All greps, scans, and sims above were read-only terminal runs at HEAD
45931c16. Helper scripts written to /tmp/w46_t7/ (dump_fences.py for the 55-
leaf frontmatter fence dump, sim.py and theft.py replicating the deterministic
token router from scripts/router_eval.py — hyphen-preserving tokens, tag
weight 3, name 2, desc 1, body 0.5, full-phrase bonus 4, tie-break by path —
over the real skills/ tree plus each hypothetical candidate, and over all
1266 eval/hit1-corpus.yaml tasks for the zero-theft audits). Corpus parser
recovered 1266/1266 task blocks. No repo file was modified except this
receipt; git status before and after showed only the parallel wave46-recon
receipts as untracked.

Recheck reminders for future waves: tdoa-positioning reopens only if
acoustic-emission-inspection drops the generic hyperbolic iterated-LS claim;
impact-angle-control-guidance is a wave-47 candidate if the pool needs a
second guidance leaf; information-filter reopens if kalman-filter-design's
fence narrows away from "sensor fusion / recursive least squares"; TDCP
reopens only if the doppler sibling narrows to single-epoch-only AND corpus
intent for between-epoch phase-delta velocity appears.
