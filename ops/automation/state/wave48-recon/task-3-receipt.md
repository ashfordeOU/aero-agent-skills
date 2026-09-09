# WAVE-48 GNC-AUTONOMY PROBE RECEIPT (task-3, whole-family FRESH)

- Repo: local AeroSkills repo at ~/AeroSkills, git HEAD 92d84a48 (verified
  `git log --oneline -1`: "ops: stage wave-48 brief (planning only — daylight
  dispatch 10:00 CEST)"). Working tree clean at probe start and end except
  the wave48-recon receipts directory (git status --porcelain: 1 untracked
  entry, this receipt).
- Scope: ENTIRE gnc-autonomy family, 62 leaves, probed FRESH at wave-48
  HEAD. Read-only probe: no writes to skills/, eval/, standards-map.yaml,
  scripts/ or briefs. One write only: this receipt.
- Family leaf count verified: `find skills/gnc-autonomy -mindepth 3 -name
  SKILL.md` = 62 (control 15, estimation-filtering 10, guidance 11,
  navigation 15, optimal-control 7, space 4), +1 family router SKILL.md.
  All four wave-47 GOs verified on disk: navigation/tropospheric-delay-
  correction, guidance/impact-angle-control-guidance, control/smith-
  predictor, control/h-infinity-control (corpus tasks w47-*-1/-2 exist for
  each: eval/hit1-corpus.yaml lines 5790-5836).
- Corpus baseline: eval/hit1-corpus.yaml = 1306 tasks (yaml parse recovered
  1306/1306); router sim indexed 657 SKILL.md under skills/ (645 leaves +
  12 family routers) with the same loader as scripts/router_eval.py;
  baseline gate check 0/1306 failures at this HEAD.
- Standards map: 30 ids (`grep '^  - id:' standards-map.yaml` = 30);
  candidates map onto existing ids, grep-verified: arp4754a line 38.
- Prior-wave context read: wave-47 gnc receipt
  (ops/automation/state/wave47-recon/task-3-receipt.md, HEAD a4ae6d1e) in
  full, including its closing "Recheck reminders for future waves"
  paragraph; every reminder is adjudicated below.

## Verdict

3 strong GO candidates, all in the control pack, ranked with full gate
evidence (a-f). Central finding: the wave-47 wave did NOT land the identity
its own receipt ranked GO4. h-infinity-control as built is a SISO
frequency-domain **norm-analysis** leaf (mixed-sensitivity S/KS review by
gamma iteration over the imaginary axis) whose own pitfalls explicitly
renounce controller synthesis and Riccati equations (quote under GO 1 b,
verbatim). The DGKF two-Riccati
state-space H-infinity **synthesis** identity wave-47 GO4 anchored to
(Doyle, Glover, Khargonekar & Francis, IEEE TAC 34(8) 1989) is therefore
still zero-owner tree-wide, zero in the 1306-task corpus, and fenced OUT by
the landed sibling: GO 1 is that seam. The wave-47 "recheck l1-adaptive/
adaptive fences before any further robust/adaptive member" reminder was
honored: both adaptive leaves are first-order model-reference/L1 structures
with no variable-structure or nonlinear claim (quotes below), so the
nonlinear-control vein — entirely absent from the tree (every vocabulary
grep exit 1) — yields GO 2 (sliding-mode-control) and GO 3
(feedback-linearization). Every wave-46/47 decline re-verified FRESH
stands; fresh declines this wave: mu-synthesis (no closed form),
trajectory-shaping-guidance (vocab owned by three guidance siblings),
celestial/sight-reduction (family-scope), backstepping (pool economy).

## Adjudication of wave-47 "Recheck reminders" (verbatim list items)

1. "tropospheric-delay-correction closes the per-source delay seam once
   built" — CONFIRMED CLOSED. Leaf landed with the Saastamoinen identity
   (desc verbatim excerpt: "evaluate the saastamoinen-model delay from the
   surface pressure, temperature and water-vapour partial pressure ... form
   the zenith-hydrostatic-delay ... form the zenith-wet-delay"); corpus
   w47-tropospheric-delay-correction-1/-2 present. Its related leaves fence
   the seam (verbatim): ionospheric "owns the ionospheric member of the
   per-source delay model ... never the tropospheric term computed here";
   gnss-pseudorange-positioning "consumes the corrected pseudorange ...
   never a per-source delay model". Multipath/tracking-loop re-declined
   FRESH in the declines table.
2. "impact-angle-control-guidance closes the terminal-constraint family" —
   CONFIRMED CLOSED. Leaf landed (commanded terminal flight path angle via
   crossrange geometry; corpus w47-impact-angle-control-guidance-1/-2);
   pitfalls verbatim: "Do not add impact-time or salvo control:
   impact-time-control-guidance owns the time-constrained member of the
   terminal-law family; this leaf is angle-only." Fresh
   trajectory-shaping probe finds no remaining unowned member (declines).
3. "smith-predictor and h-infinity-control ... deepen the control pack
   toward delay compensation and robust synthesis" — PARTIALLY LANDED.
   smith-predictor landed (FOPDT delay-line compensation, corpus
   w47-smith-predictor-1/-2): delay compensation CLOSED. h-infinity-control
   landed as norm ANALYSIS only (see Verdict): robust worst-case SYNTHESIS
   remains open — GO 1 this wave.
4. "recheck l1-adaptive/adaptive fences before any further robust/adaptive
   member" — HONORED. adaptive-control desc (verbatim): MRAC "for a
   first-order plant with an unknown plant coefficient ... gradient
   (Lyapunov-motivated) adaptation law"; l1-adaptive-control desc
   (verbatim): "state-predictor ... projection-based-adaptation-law ...
   low-pass filter omega_c/(s + omega_c)"; its related leaves name only
   adaptive-control, control-allocation, state-space-analysis,
   observer-design. Neither claims a variable-structure, switching or
   nonlinear-cancellation law; the robust members recommended below are
   nonlinear design laws, not MRAC/L1 variants — no fence collision.
5. "tdoa reopens only if acoustic-emission-inspection drops the generic
   hyperbolic iterated-LS claim" — NOT REOPENED (quotes unchanged,
   declines). "TDCP reopens only if the doppler sibling narrows to
   single-epoch-only AND corpus intent appears" — NOT REOPENED (doppler
   desc still single-epoch delta-range-rate; corpus 0, declines).

## Ranked GO with evidence

### GO 1: gnc-autonomy/control/h-infinity-synthesis

One-line why: wave-47's own GO4 identity (DGKF two-Riccati state-space
H-infinity synthesis) was never built — the h-infinity-control leaf that
landed is a S/KS norm-analysis leaf that explicitly renounces synthesis and
Riccati equations (verbatim below), so the two-ARE gamma-iteration
synthesis is still zero-owner tree-wide, zero in the 1306-task corpus, and
both wordable Hit@1 queries route to the candidate with 17.5+ point margins
and zero theft.

(a) Zero-owner greps, whole skills/ tree, FRESH:
`rg -i -l 'dgkf|hinfsyn|two-riccati|h-infinity-synthesis' skills/ -g
'SKILL.md'` -> 0 hit(s) (exit 1). Corpus scan `rg -ic 'dgkf|two-riccati|
hinfsyn|h-infinity-synthesis' eval/hit1-corpus.yaml` -> 0 hits (exit 1).
The only 'riccati' owners tree-wide are single-ARE contexts: lqr-design,
lqg-design, ilqr-ddp, model-predictive-control, loop-transfer-recovery and
h-infinity-control itself — the last only to renounce (see (b)).
`rg -i -l 'h-infinity'` -> exactly h-infinity-control + the family router.

(b) Sibling fences (FRESH reads, verbatim):
h-infinity-control pitfalls lines 223-227: "Reading this leaf as an
H-infinity controller synthesis: no controller is ever synthesized, tuned,
placed or recovered here, and no algebraic Riccati equation solver lives in
the leaf; the plant, the candidate controller and the weight parameters are
all given inputs, and the review verdict only rates the supplied pair."
h-infinity-control related-leaves lines 211-214 (verbatim): "lqr-design
and lqg-design: solve the algebraic Riccati equations of optimal regulation
and estimation; this leaf computes no Riccati solution and no state-feedback
or compensator gain." Compliance lines 269-271 name the DGKF paper only as
"synthesis context". lqr-design pitfalls (verbatim line 66-67): "Applying
the closed form outside the canonical family: a general A and B need a
general Riccati solver, not this leaf's equations." — no sibling owns the
two-ARE gamma-coupled synthesis; the w47-h-infinity-control-1/-2 corpus
tasks are pure analysis wording (weighted-sensitivity, s-over-ks,
worst-case-peak-gain), so the synthesis corpus slot is empty.

(c) Standards-map id exists: `grep -n 'id: arp4754a' standards-map.yaml` ->
line 38 (ARP4754A reference-only, control-pack convention, same as the
h-infinity-control sibling's own use, frontmatter lines 7-8).

(d) Published deterministic anchor (summary-only): DGKF state-space
H-infinity synthesis — given the generalized plant with state matrices and
the performance/control weights, the suboptimal controller at level gamma
exists iff two algebraic Riccati equations (X_inf for the regulator, Y_inf
for the estimator) admit positive-semidefinite stabilizing solutions with
the spectral-radius coupling rho(X_inf Y_inf) < gamma^2; the central
controller is a closed form in X_inf, Y_inf, F_inf and H_inf (the
state-feedback and observer gains) with the D11-feedthrough correction.
Deterministic offline computation: bisect gamma between the spectral-radius
lower bound and the stabilizing upper bound, solve both AREs, form the
central controller state matrices. Source: Doyle, Glover, Khargonekar and
Francis, "State-Space Solutions to Standard H2 and H-infinity Control
Problems," IEEE Transactions on Automatic Control 34(8):831-847, 1989;
textbook treatment Skogestad & Postlethwaite, Multivariable Feedback
Control (Wiley, 2005) chapter 9 (the same works the sibling cites).

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-48 HEAD with
the deterministic token router replicated exactly from scripts/router_eval.py
(hyphen-preserving tokens, stopword filter, tag weight 3 / name 2 / desc 1 /
body 0.5, verbatim-phrase bonus 4, tie-break path asc) over the real
657-SKILL.md index plus the candidate:
1. "synthesize the state-space h-infinity controller with the
   dgkf-two-riccati method: iterate the gamma-level while the two
   algebraic-riccati equations admit stabilizing-solutions and the
   spectral-radius-coupling stays below gamma-squared, then form the
   central-h-infinity-controller from the stabilizing-solutions" -> HIT1
   at 35.5 vs 11.0 (gnc-autonomy/control/h-infinity-control).
2. "run the h-infinity-synthesis for the generalized-plant: solve the
   x-infinity and y-infinity algebraic-riccati equations under the
   spectral-radius-coupling check and assemble the central-h-infinity-
   controller state matrices from the state-feedback gain and the observer
   gain" -> HIT1 at 27.5 vs 10.0 (gnc-autonomy/control/observer-design).
Distinct from the two analysis-wording corpus tasks w47-h-infinity-control-
1/-2 (theft audit: 0 of 1306 tasks reroute with this candidate added).

(f) Tag set all hyphenated compounds: h-infinity-synthesis,
dgkf-two-riccati, gamma-level-iteration, spectral-radius-coupling,
central-h-infinity-controller, state-space-h-infinity-synthesis,
algebraic-riccati-synthesis.

### GO 2: gnc-autonomy/control/sliding-mode-control

One-line why: the nonlinear-control vein is entirely absent from the tree —
every variable-structure vocabulary grep exits 1 tree-wide and corpus-wide —
the two adaptive siblings fence only first-order MRAC/L1 structures
(quotes above), and both wordable Hit@1 queries route to the candidate with
22+ point margins and zero theft.

(a) Zero-owner greps, whole skills/ tree, FRESH:
`rg -i -l 'sliding[- ]mode|variable[- ]structure|reaching[- ]law|
equivalent[- ]control|chattering' skills/ -g 'SKILL.md'` -> 0 hit(s)
(exit 1). Corpus scan `rg -ic 'sliding-mode|variable-structure|reaching-
law|equivalent-control' eval/hit1-corpus.yaml` -> 0 hits (exit 1). The
runner-up bleed in Q2 is aerodynamics/boundary-layer/boundary-layer-theory
scoring on the generic 'boundary-layer' token only (6.5, all from desc/body
overlap); it is an aerodynamics flow-physics leaf, not a control owner.

(b) Sibling fences (FRESH reads, verbatim): adaptive-control desc line 3:
"model-reference adaptive controller (MRAC) for a first-order plant with an
unknown plant coefficient ... update the gains online with the gradient
(Lyapunov-motivated) adaptation law scaled by the tracking error";
l1-adaptive-control desc line 3: "l1-adaptive-control law for a first-order
plant with an unknown coefficient: run the state-predictor ... drive the
projection-based-adaptation-law ... low-pass filter omega_c/(s + omega_c)".
Neither mentions a switching surface, equivalent control or
variable-structure design; h-infinity-control owns worst-case norm analysis
(linear SISO) and GO 1 owns state-space robust synthesis; pid-control-design
is the sim runner-up on generic 'control'-family tokens only.
Smith-predictor dead-time and the adaptive law structures are disjoint from
the sliding-surface identity.

(c) Standards-map id exists: arp4754a line 38 (control-pack convention).

(d) Published deterministic anchor (summary-only): sliding-mode control for
a relative-degree-one (second-order canonical) plant with matched
uncertainty |f| bounded: sliding surface s = edot + lambda e, sliding
condition (1/2) d(s^2)/dt <= -eta |s|, equivalent control u_eq from setting
sdot = 0 on the nominal model, control u = u_eq - k sat(s/phi) with the
switching gain k sized above the uncertainty bound and the boundary-layer
thickness phi suppressing chattering; finite-time reachability of the
boundary layer follows from the constant-plus-proportional reaching law.
Source: Slotine and Li, Applied Nonlinear Control (Prentice Hall, 1991),
chapter 7 (Sliding Control); the switching law and reachability condition
are standard closed forms (Utkin 1977/1992). Deterministic offline
evaluation given the nominal model, the uncertainty bound and the surface
coefficients.

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-48 HEAD:
1. "design the sliding-mode-control law for the second-order plant with
   matched-uncertainty: choose the sliding-surface from the error and its
   derivative, compute the equivalent-control from the nominal model, and
   add the switching-term inside the boundary-layer to enforce the
   reachability condition" -> HIT1 at 36.5 vs 14.0 (gnc-autonomy/control/
   pid-control-design).
2. "apply sliding-mode-control with the constant-plus-proportional-
   reaching-law: evaluate the equivalent-control, size the switching-gain
   from the matched-uncertainty bound and report the boundary-layer command
   with the chattering-suppression check" -> HIT1 at 28.5 vs 6.5
   (aerodynamics/boundary-layer/boundary-layer-theory).
Theft audit: 0 of 1306 tasks reroute.

(f) Tag set all hyphenated compounds: sliding-mode-control,
sliding-surface-design, equivalent-control, constant-plus-proportional-
reaching-law, switching-term, chattering-suppression, matched-uncertainty,
variable-structure-control, boundary-layer-command.

### GO 3: gnc-autonomy/control/feedback-linearization

One-line why: the Lie-derivative input-output linearization identity
(relative degree, decoupling-matrix inversion, linearizing control, zero
dynamics) is zero-owner tree-wide and zero in the corpus — the only tree
text matching any pattern is propulsion/rocket/thrust-vector-control's
"works at zero dynamic pressure" (vacuum regime prose, line 48, not a
zero-dynamics claim) — and both wordable Hit@1 queries route to the
candidate with 29.5+ point margins and zero theft.

(a) Zero-owner greps, whole skills/ tree, FRESH:
`rg -i -l 'feedback[- ]lineariz|dynamic[- ]inversion|lie[- ]derivative|
zero[- ]dynamic|input[- ]output[- ]lineariz' skills/ -g 'SKILL.md'` -> 1
hit, context-checked as NOT an owner: thrust-vector-control SKILL.md line 48
"works at zero dynamic pressure and in vacuum; aerodynamic control" —
matching only 'zero[- ]dynamic' inside "zero dynamic pressure". Corpus scan
`rg -ic 'feedback-linearization|dynamic-inversion|lie-derivative|zero-
dynamics' eval/hit1-corpus.yaml` -> 0 hits (exit 1). The deadbeat-control
sibling uses "relative degree d = deg A - deg B" (lines 48/56) in its
z-domain pulse-transfer context — transfer-function usage, not the
Lie-derivative identity; not a fence or owner (Q2 runner-up at 9.5 on that
single body token, weight 0.5).

(b) Sibling fences (FRESH reads): control pack has no nonlinear-design
leaf; adaptive-control/l1-adaptive-control fence only the first-order MRAC
and L1 predictor structures (quotes under GO 2); sliding-mode-control (GO 2)
is the switching-law sibling of the same new vein and owns no linearizing
map; state-space-analysis is the linear LTI toolbox of the pack. The
space-systems/adcs leaves (reaction-wheel-control, magnetorquer-control)
score as Q1 sim runner-ups only on generic nonlinear/control tokens; ADCS
control laws are not the plant-inversion identity. No sibling owns the
decoupling-matrix/zero-dynamics construction.

(c) Standards-map id exists: arp4754a line 38 (control-pack convention).

(d) Published deterministic anchor (summary-only): input-output
feedback linearization of a nonlinear plant xdot = f(x) + g(x) u, y = h(x):
compute the Lie derivatives L_f^r h and L_g L_f^{r-1} h along the drift and
control vector fields to establish the relative degree r (L_g L_f^{k} h = 0
for k < r-1, nonzero at r-1), invert the decoupling scalar/matrix
(L_g L_f^{r-1} h)^-1 to form the linearizing control u = (L_g L_f^{r-1}h)^-1
(v - L_f^r h) that cancels the nonlinear terms, apply the outer linear
tracking loop on y^(r) = v, and check the internal dynamics (the unobservable
part) are stable via their zero dynamics before accepting the design.
Source: Slotine and Li, Applied Nonlinear Control (1991), chapters 4 and 6
and Isidori, Nonlinear Control Systems (Springer), the standard references;
the aerospace framing is nonlinear dynamic inversion (NDI). Deterministic
offline polynomial/Lie-derivative arithmetic given the model.

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-48 HEAD:
1. "apply feedback-linearization to the nonlinear plant: compute the
   lie-derivative of the output along the control vector field to establish
   the relative-degree, invert the decoupling-matrix for the
   linearizing-control, and verify the zero-dynamics of the
   internal-dynamics are stable" -> HIT1 at 41.5 vs 12.0 (space-systems/
   adcs/magnetorquer-control).
2. "linearize the input-output response of the nonlinear plant by
   feedback-linearization: compute the lie-derivatives up to the
   relative-degree, form the linearizing-control from the decoupling-matrix
   and apply the outer tracking loop with the zero-dynamics stability
   check" -> HIT1 at 39.0 vs 9.5 (gnc-autonomy/control/deadbeat-control).
Theft audit: 0 of 1306 tasks reroute.

(f) Tag set all hyphenated compounds: feedback-linearization,
lie-derivative, relative-degree, decoupling-matrix, linearizing-control,
zero-dynamics, internal-dynamics-stability, input-output-linearization.

## Declines table (wave-46/47 rows re-verified FRESH; fresh seams probed this wave)

| Near-miss candidate | Gate(s) | Fresh evidence / decline reason |
|---|---|---|
| navigation/tdoa-positioning (brief-ordered fence re-check) | b | RE-CHECKED FRESH. Still CLOSED: manufacturing-quality/ndt/acoustic-emission-inspection logic (scripts/acoustic_emission_inspection_logic.py line 83, verbatim): "ValueError when the arrival-time difference is impossible for a" and SKILL.md still owns the planar hyperbolic arrival-time-difference system; no fence narrowing since wave-47. Reopen only if the generic hyperbolic iterated-LS claim is dropped. |
| navigation/time-differenced-carrier-phase-positioning | e | STAY: gnss-doppler-velocity-positioning desc (verbatim): "estimate the 3-D velocity ... at a single epoch from carrier-phase delta-range-rate (doppler) observables: propagate each satellite ECEF position and velocity from the broadcast-ephemeris Kepler elements" — delta-range vocab still owned; corpus 0; no corpus intent appeared (the wave-47 reopen condition is not met). |
| navigation/vor-dme-positioning | b, e | STAY: avionics/flight-management/radio-navigation-aids desc (verbatim): "derive the VOR radial and the bearing from the aircraft to the station from the planar station and aircraft coordinates, compute the DME slant range from the ground distance and the aircraft altitude" — navaid geometry vocab owned with tag weight 3; no fence change; corpus tasks w27-radio-navigation-aids-1/-2 unchanged. |
| estimation/attitude determination (QUEST/q-method/TRIAD) | a, b | STAY OWNED: `rg -i -l 'wahba\|davenport\|q-method'` -> space-systems/adcs/attitude-determination-quest, attitude-determination-triad, magnetometer-calibration + space-systems router (fresh). gnc space pack stays at 4 leaves. |
| guidance/ascent linear-tangent / powered-descent | scope | STAY: space-systems/mission-design owns entry-descent-landing, c3-departure-energy, launch-window-analysis, synodic-launch-window, mission-delta-v-budget (fresh listing) — launch/ascent territory remains space-domain; guidance pack is intercept/terminal/planning. |
| estimation-filtering KF form-variants (information filter, square-root/UD, cubature, fading-memory) | b | STAY: kalman-filter-design desc (verbatim) still claims the estimator-design family ("design or run a discrete-time Kalman filter for single-axis state estimation ... predict the state and its error covariance ... calculate the Kalma[n gain]"); fresh greps `information-filter|cubature|fading-memory|square-root-kalman` -> 0 hits (no new seam opened). Estimation vein stays 10 leaves + KF leaf. |
| control/anti-windup | a | STAY OWNED: pid-control-design desc (verbatim): "... add integrator anti-windup clamping, and check the gain margin and phase margin of the loop." |
| guidance/true-PN, PN variants, 3D engagement | b, e | STAY: proportional-navigation pitfalls (fresh, verbatim lines 65-68): closing-velocity sign and degree/radian pitfalls only — no angle-constraint or 3D claim; APN owns maneuvering-target augmentation; corpus 0; no fence change. |
| guidance/waypoint path following | b | STAY: avionics/flight-management/lateral-navigation desc owns LNAV leg quantities ("derive the great-circle track angle and ..."); midcourse-guidance desc owns intermediate-condition shaping and handover; command-to-line-of-sight unchanged. No fence change. |
| optimal-control textbook cases (LQR servo, discrete ARE, indirect methods) | b, e | STAY: lqr/lqg/ilqr-ddp/mpc own the AREs and backward-Riccati passes (fresh `rg -i -l 'riccati'` list); fresh probe `pontryagin|minimum-principle|indirect-method` -> 1 hit: optimal-control/bang-bang-control, which owns the minimum-principle switching formulation of the canonical case — an indirect-method leaf would collide. Corpus 0. Closed vein. |
| navigation multipath / UERE / air-data dead-reckoning | b, d | STAY: multipath whole-tree `rg -i -l` over SKILL.md -> 0 hits and corpus 0 (fresh, exit 1); empirical multipath magnitudes have no closed-form anchor; dilution-of-precision desc still owns the UERE-to-DOP read ("read the dilution of precision values (GDOP, PDOP, HDOP, VDOP, TDOP) off the diagonal"); receiver tracking-loop vocabulary -> 0 hits in gnc-autonomy (RF/PNT interface, no standards id) — wave-47 reminder item stands. |
| space pack additions (Hohmann, bi-elliptic, etc.) | a | STAY OWNED outside family: space-systems/orbit-mechanics fresh listing includes hohmann-transfer, bi-elliptic-transfer, plane-change-maneuver, clohessy-wiltshire, low-thrust-spiral, gravity-assist-swingby, lambert-transfer, kepler-orbit-propagation. gnc space pack stays CLOSED at 4 leaves. |
| control/mu-synthesis (D-K iteration) (FRESH) | d | No single deterministic closed form: mu-synthesis is an iterative D-K scheme (alternating H-infinity synthesis with structured-singular-value analysis of the scaled plant) and mu itself has no closed-form evaluation; GO 1 owns the deterministic state-space member of the robust vein. Zero-owner/corpus, but identity fails gate d. |
| guidance/trajectory-shaping-guidance (FRESH) | b | Vocabulary owned across three siblings + router: `rg -i -l 'trajectory[- ]shaping'` -> gnc-autonomy router, impact-angle-control-guidance, impact-time-control-guidance, midcourse-guidance (IACG related-leaves line 169-170 verbatim: "midcourse-guidance (waypoint steering, handover, trajectory shaping)"). Terminal-law family closed by the time (w46) and angle (w47) members; no distinct unowned identity remains. |
| guidance/celestial / sight-reduction navigation (FRESH) | scope | Zero-owner (fresh grep exit 1) and corpus 0, but the pack's navigation vein is GNSS/INS + passive RF localization per the closed-vein doctrine of waves 46-47, and stellar geometry is adjacent to space-systems/adcs/star-tracker territory; no wave brief raised it. Declined on family-scope, not on the math. |
| control/backstepping (FRESH) | scope | Strict-feedback recursive Lyapunov backstepping (Krstic, Kanellakopoulos, Kokotovic 1995) is a genuinely distinct deterministic identity and zero-owner, but it is the direct sibling of GO 3 within one new nonlinear vein; pool economy — do not build two members of an unproven vein in one wave. Re-probe next wave after feedback-linearization lands. |

## Closed veins (owner leaf per vein, reaffirmed FRESH at wave-48 HEAD)

- GNSS positioning: pseudorange, doppler-velocity, carrier-smoothing, rtk,
  raim-fde, dilution-of-precision; per-source delay seam CLOSED (ionospheric
  w46 + tropospheric w47, owner leaves listed in their own related-leaves
  fences). Multipath (empirical anchor) and receiver tracking-loop (RF/PNT
  interface, no standards id) declined — see declines.
- Passive localization: bearing-only (Stansfield). Hyperbolic TDOA CLOSED by
  manufacturing-quality/ndt/acoustic-emission-inspection.
- INS/integration: inertial-navigation, ins-gnss-integrated-filter,
  tightly-coupled-ins-gnss, terrain-referenced-navigation, navigation-frames.
  CLOSED.
- Estimation filters: alpha-beta, complementary, ekf, ukf, imm, particle,
  rts-smoother, process-noise-discretization, imu-static-calibration,
  kalman-filter-design (navigation subfamily), cramer-rao-lower-bound.
  CLOSED (form-variants declined; attitude determination owned by
  space-systems/adcs).
- Guidance laws: pursuit, proportional-navigation, augmented-proportional-
  navigation, command-to-line-of-sight, collision-course, midcourse,
  impact-point-prediction, coverage/dubins. Terminal-constraint family
  CLOSED: time member (impact-time-control-guidance, w46) and angle member
  (impact-angle-control-guidance, w47) both on disk.
- Optimal control: bang-bang (owns the minimum-principle switching case),
  lqr, lqg, mpc, ilqr-ddp, dymos, loop-transfer-recovery. CLOSED.
- Control, linear: pid, lead-lag, root-locus, frequency-response,
  state-space, observer, digital-control-design, python-control,
  gain-scheduling, control-allocation, deadbeat (w46). Delay compensation
  CLOSED (smith-predictor, w47). Robust analysis CLOSED (h-infinity-control,
  w47, S/KS norm review) — but robust worst-case SYNTHESIS open: GO 1.
- Control, adaptive: adaptive-control (MRAC), l1-adaptive-control. CLOSED
  (first-order structures only; fences re-checked FRESH this wave).
- Nonlinear control vein: NO leaf anywhere in the 645-leaf tree (fresh
  vocabulary greps exit 1); sliding-mode-control = GO 2,
  feedback-linearization = GO 3; backstepping deferred (declines).
- Space pack (4 leaves): closed at gnc scope; space-systems owns the wider
  orbit/ADCS/mission-design space (fresh leaf listings in declines).

## Standards-map check

30 ids present (`grep '^  - id:' standards-map.yaml` = 30). All three GOs
map arp4754a (line 38, reference-only, the control-pack convention — same
as h-infinity-control's own frontmatter use). No new standards ids required.

## Method note

All greps, scans and sims above were read-only terminal runs at HEAD
92d84a48. The router sim replicates scripts/router_eval.py exactly
(hyphen-preserving tokens, stopword filter, tag weight 3 / name 2 / desc 1 /
body 0.5, verbatim-phrase bonus 4, tie-break path asc) with per-skill token
sets precomputed for speed, over the real 657-SKILL.md index plus the three
hypothetical candidates, and over all 1306 eval/hit1-corpus.yaml tasks for
the zero-theft audits (yaml parse recovered 1306/1306 task blocks;
baseline gate check with candidates absent: 0 failures). Temporary
read-only helper scripts lived in a temp directory only; no repo file was
modified except this receipt (git status before/after: only the wave48-recon
receipts directory untracked).

Existing sibling corpus tasks confirmed distinct from the new query wording:
h-infinity-control -> w47-h-infinity-control-1/-2 (weighted-sensitivity,
s-over-ks, worst-case-peak-gain, imaginary-axis sweep — analysis wording
only; no dgkf/two-riccati/central-controller tokens anywhere in the corpus);
tropospheric-delay-correction -> w47-tropospheric-delay-correction-1/-2;
impact-angle-control-guidance -> w47-impact-angle-control-guidance-1/-2;
smith-predictor -> w47-smith-predictor-1/-2. The theft audit (0 reroutes of
1306 tasks) covers every existing corpus task, including all w47 gnc tasks.

Recheck reminders for future waves: h-infinity-synthesis closes the robust-
synthesis member of the control pack once built (further robust members —
mu-synthesis/D-K — fail gate d as iterative with no closed form; do not
re-probe without a closed-form anchor); sliding-mode-control and
feedback-linearization open the nonlinear-control vein — backstepping is the
declared next sibling only after one of them lands and proves the vein;
the per-source delay seam, terminal-constraint family and adaptive/MRAC/L1
structures remain CLOSED unless a landed leaf narrows a fence (tdoa reopens
only if acoustic-emission-inspection drops its generic hyperbolic iterated-LS
claim; TDCP only if the doppler sibling narrows AND corpus intent appears);
the estimation and optimal-control veins stay closed; guidance/navigation
growth should come from GO 1-3 territory, not from further siblings of
closed veins.
