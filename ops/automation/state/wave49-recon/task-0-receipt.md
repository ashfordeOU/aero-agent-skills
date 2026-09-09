# WAVE-49 GNC-AUTONOMY PROBE RECEIPT (task-0, whole-family FRESH)

- Repo: local AeroSkills repo, git HEAD 9c2b3fe4 (verified `git log --oneline
  -1`: "ops: stage wave-49 brief (655 baseline, daylight gate 11:45 UTC)").
  Working tree clean at probe start and end except the wave49-recon receipts
  directory (git status --porcelain: 1 untracked entry, this receipt).
- Scope: ENTIRE gnc-autonomy family, 65 leaves, probed FRESH at wave-49 HEAD.
  Read-only probe: no writes to skills/, eval/, standards-map.yaml, scripts/
  or briefs. One write only: this receipt.
- Family leaf count verified: `find skills/gnc-autonomy -mindepth 3 -name
  SKILL.md` = 65 (control 18, estimation-filtering 10, guidance 11,
  navigation 15, optimal-control 7, space 4), +1 family router SKILL.md
  (skills/gnc-autonomy/SKILL.md). All three wave-48 GOs verified on disk:
  control/h-infinity-synthesis, control/sliding-mode-control,
  control/feedback-linearization; their corpus tasks w48-h-infinity-synthesis-
  1/-2, w48-sliding-mode-control-1/-2, w48-feedback-linearization-1/-2
  present in eval/hit1-corpus.yaml (lines 5875-5936).
- Corpus baseline: eval/hit1-corpus.yaml = 1326 tasks (yaml parse recovered
  1326/1326 task blocks; header "1326"). Router tree indexed 667 SKILL.md
  under skills/ (655 leaves + 12 family routers) with the same loader as
  scripts/router_eval.py; gate check replicated at this HEAD: 0/1326
  failures with the exact tie-break (score desc, path asc).
- Standards map: 30 ids (`grep '^  - id:' standards-map.yaml` = 30);
  candidates map onto existing ids, grep-verified: arp4754a line 38.
- Ratings ledger: eval/skill-ratings.md total 655 rows (line 5, fresh).
- Prior-wave context read in full: wave-48 gnc receipt
  (ops/automation/state/wave48-recon/task-3-receipt.md) and wave-47 gnc
  receipt (ops/automation/state/wave47-recon/task-3-receipt.md); every item
  of the wave-48 closing "Recheck reminders for future waves" paragraph is
  adjudicated below.

## Verdict

2 GO candidates, ranked, both in the control pack, with full gate evidence
(a-f). Central finding: the wave-48 conditional on the nonlinear-control
vein is now SATISFIED — wave-48's declared next sibling (backstepping) was
gated on "only after one of them lands and proves the vein", and BOTH
sliding-mode-control and feedback-linearization landed at wave-48 (verified
on disk + corpus). Fresh whole-tree and whole-corpus greps confirm the
strict-feedback recursive design identity remains zero-owner everywhere and
zero in the 1326-task corpus: GO 1 is backstepping-control. A second,
genuinely fresh seam surfaced in the same FRESH probe: the
bandwidth-parameterized linear-extended-state-observer / active-disturbance-
rejection-control law (LESO + disturbance-cancellation identity) is
zero-owner tree-wide and corpus-wide, is NOT the L1/MRAC adaptation family
(wave-48 reminder honored: adaptive fences re-read fresh below), and routes
both wordable Hit@1 queries to itself with 18.5+ point margins: GO 2 is
active-disturbance-rejection-control. mu-synthesis re-declined FRESH on gate
(d) with the wave-48 reminder verbatim confirmed in the landed leaf's own
fence ("do not re-probe without a closed-form anchor"). The brief's probe
hint "L1-adaptive ... re-verify FRESH" resolves to OWNED, not zero-owner:
gnc-autonomy/control/l1-adaptive-control exists on disk with the state-
predictor/projection/filter identity (desc quoted under GO 1 (b)).

## Adjudication of wave-48 "Recheck reminders" (verbatim list items)

1. "h-infinity-synthesis closes the robust-synthesis member of the control
   pack once built (further robust members — mu-synthesis/D-K — fail gate d
   as iterative with no closed form; do not re-probe without a closed-form
   anchor)" — CONFIRMED CLOSED. Leaf landed (w48 corpus tasks present); its
   own related-leaves fence lines 290-293 verbatim: "mu-synthesis and D-K
   iteration are not siblings: iterative uncertainty-model schemes with no
   deterministic closed form were declined at wave-48 gate (d); this leaf
   owns only the deterministic state-space member of the robust vein."
   Fresh tree grep `rg -i -l 'mu-synthesis|dk-iteration|structured-
   singular'` -> exactly that fence (1 hit, renouncement, not ownership);
   corpus 0. mu-synthesis decline STANDS on gate (d).
2. "sliding-mode-control and feedback-linearization open the nonlinear-
   control vein — backstepping is the declared next sibling only after one
   of them lands and proves the vein" — CONDITION MET. Both leaves on disk
   (w48 corpus tasks verified); the vein is proven with two members.
   Backstepping re-probed FRESH this wave: zero-owner, corpus-absent, no
   sibling fence (adaptive/L1 quotes under GO 1 (b); sliding-mode is the
   switching-law sibling of the same vein; feedback-linearization owns the
   Lie-derivative cancellation, not the recursive design) -> GO 1.
3. "the per-source delay seam, terminal-constraint family and adaptive/MRAC/
   L1 structures remain CLOSED unless a landed leaf narrows a fence" —
   REAFFIRMED. Per-source delay seam closed (tropospheric-delay-correction
   on disk, wave-47 GO 1); terminal-constraint family closed (impact-angle
   + impact-time both on disk); adaptive fences UNCHANGED, read fresh under
   GO 1 (b): neither claims a switching surface, an extended observer or a
   recursive design law.
4. "tdoa reopens only if acoustic-emission-inspection drops its generic
   hyperbolic iterated-LS claim" — NOT REOPENED: manufacturing-quality/ndt/
   acoustic-emission-inspection still on disk, no fence narrowing observed.
5. "TDCP only if the doppler sibling narrows AND corpus intent appears" —
   NOT REOPENED: gnss-doppler-velocity-positioning unchanged; corpus 0.
6. "the estimation and optimal-control veins stay closed; guidance/navigation
   growth should come from GO 1-3 territory, not from further siblings of
   closed veins" — REAFFIRMED FRESH: estimation form-variant greps
   information-filter/cubature/square-root-kalman/fading-memory -> 0 tree,
   0 corpus; multipath -> 0 tree, 0 corpus (no empirical closed-form
   anchor); receiver tracking-loop vocabulary -> 0 in gnc (RF/PNT
   interface); optimal-control vein closed (lqr/lqg/mpc/ilqr-ddp/dymos/
   loop-transfer-recovery own the AREs and backward passes; bang-bang owns
   the minimum-principle switching case).

## Ranked GO with evidence

### GO 1: gnc-autonomy/control/backstepping-control

One-line why: wave-48's own closing reminder declared backstepping the next
sibling of the nonlinear-control vein "only after one of them lands and
proves the vein" — both sliding-mode-control and feedback-linearization
landed at wave-48 — and the strict-feedback recursive design identity
(error-variable change, virtual control, final control from the recursion
plus its analytic derivative, quadratic-Lyapunov audit) is still zero-owner
tree-wide, zero in the 1326-task corpus, and fenced by NO sibling: the two
adaptive leaves are first-order model-reference/L1 gain-adaptation
structures, and neither new nonlinear sibling claims the recursion.

(a) Zero-owner greps, whole skills/ tree, FRESH:
`rg -i -l 'backstepping|back-stepping|strict-feedback|integrator-back'`
skills/ -g 'SKILL.md' -> 0 hit(s) (exit 1). Corpus scan `rg -ic
'backstepping|back-stepping|strict-feedback|virtual-control|control-
lyapunov'` eval/hit1-corpus.yaml -> 0 hits (exit 1). Extended variants:
adaptive-backstepping|tuning-function -> 0 tree, 0 corpus. The only
tree-wide 'lyapunov' owner is adaptive-control (Lyapunov-motivated MRAC
gradient law, body lines 58-60: "with the sign of ... Lyapunov function
down, e goes to zero, and the gains settle at the ideal-cancellation
values") — single-state adaptation analysis, NOT a control-Lyapunov
recursive design; no leaf anywhere owns the virtual-control construction.

(b) Sibling fences (FRESH reads, verbatim): adaptive-control desc line 3:
"model-reference adaptive controller (MRAC) for a first-order plant with an
unknown plant coefficient ... update the gains online with the gradient
(Lyapunov-motivated) adaptation law scaled by the tracking error";
l1-adaptive-control desc line 3: "run the state-predictor from the design
model, drive the projection-based-adaptation-law with the prediction error,
pass the adaptive signal through the low-pass filter omega_c/(s + omega_c)".
Neither mentions a recursion, virtual control or strict-feedback form.
sliding-mode-control related-leaves (read fresh) name adaptive-control,
l1-adaptive-control, pid-control-design, gain-scheduling, h-infinity-control
and deadbeat-control only — no recursive-design claim, and its plant is the
pinned two-state canonical form with a given uncertainty bound, never a
strict-feedback chain. feedback-linearization related-leaves name state-
space-analysis, sliding-mode-control ("the switching-law sibling of the
same nonlinear vein"), adaptive-control and gain-scheduling — the Lie-
derivative/relative-degree/decoupling inversion identity, disjoint from the
backstepping recursion. observer-design = full-order Luenberger LTI
estimation by pole placement (desc quote under GO 2 (b)); estimation veins
closed per reminder item 6.

(c) Standards-map id exists: `grep -n 'id: arp4754a' standards-map.yaml` ->
line 38 (ARP4754A reference-only, control-pack convention, same as the
sliding-mode and feedback-linearization siblings' own use).

(d) Published deterministic anchor (summary-only): integrator backstepping
for a second-order strict-feedback plant x1_dot = x2 + f1(x1), x2_dot = u +
f2(x1, x2) tracking a reference x1d: define the error variable z1 = x1 - x1d
and the virtual control alpha1 = -c1 z1 + x1d_dot - f1 (c1 > 0) so the
z1-subsystem Lyapunov candidate V1 = (1/2) z1^2 decays as V1_dot = -c1 z1^2
+ z1 z2 with the mismatch z2 = x2 - alpha1; the final control u = -f2 +
alpha1_dot - z1 - c2 z2 (c2 > 0) makes V2 = V1 + (1/2) z2^2 satisfy V2_dot
= -c1 z1^2 - c2 z2^2 < 0, giving asymptotic tracking with the closed-loop
error rates set by c1, c2; alpha1_dot is the analytic derivative along the
plant, and each recursion step adds one state and one virtual control.
Source: Krstic, Kanellakopoulos and Kokotovic, Nonlinear and Adaptive
Control Design (Wiley, 1995) chapters 1-2 (the canonical reference of the
recursion); Khalil, Nonlinear Systems (Prentice Hall, 3rd ed.) chapter 14.
Deterministic offline closed-form evaluation given f1, f2, the reference
and the gains — no search, no iteration, no adaptation.

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-49 HEAD with
the deterministic token router replicated exactly from scripts/router_eval.py
(hyphen-preserving tokens, stopword filter, tag weight 3 / name 2 / desc 1 /
body 0.5, verbatim-phrase bonus 4, tie-break score desc + path asc) over the
real 667-SKILL.md index plus the candidate:
1. "design the backstepping control law for the strict-feedback plant:
   choose the virtual control that stabilizes the first error variable,
   propagate the inner-state mismatch as the second error variable, and
   assemble the final control with the Lyapunov-derivative audit" -> HIT1
   at 22.0 vs 11.5 (gnc-autonomy/control/sliding-mode-control).
2. "apply integrator-backstepping to the second-order strict-feedback
   nonlinear system: compute the virtual control and its analytic
   derivative, form the recursive backstepping control law and verify the
   closed-loop Lyapunov function decays" -> HIT1 at 17.0 vs 12.0
   (gnc-autonomy/control/feedback-linearization).
Theft audit: 0 of 1326 tasks reroute with the candidate added; baseline
gate replication with the candidate absent also 0/1326 at this HEAD.

(f) Tag set all hyphenated compounds: backstepping-control,
integrator-backstepping, strict-feedback, virtual-control,
control-lyapunov-function, recursive-control-design, backstepping-control-
law, error-variable-recursion.

### GO 2: gnc-autonomy/control/active-disturbance-rejection-control

One-line why: the linear-extended-state-observer (LESO) bandwidth-
parameterized disturbance-rejection law (Gao/Han ADRC: augmented state
observer with observer gains from the (s + omega_o)^n expansion, control
u = (u0 - z3)/b0 canceling the total-disturbance estimate z3) is zero-owner
tree-wide AND zero in the corpus — it is not the L1/MRAC adaptation family
(those adapt gains against an unknown coefficient; this observer estimates a
total disturbance and cancels it at fixed bandwidths), and it is fenced by
no sibling: observer-design owns only full-order Luenberger LTI estimation,
sliding-mode sizes a switching gain against a given bound rather than
estimating the disturbance, and the only 'disturbance' neighbor tree-wide is
space-systems/adcs/environmental-disturbance-torque-budget, a torque
MODELLING leaf for ADCS sizing, not a control law. Both wordable Hit@1
queries route to the candidate with 18.5+ point margins and zero theft.

(a) Zero-owner greps, whole skills/ tree, FRESH: `rg -i -l 'active-
disturbance|extended-state-observer|adrc|leso|bandwidth-parameteriz|total-
disturbance|disturbance-observer'` skills/ -g 'SKILL.md' -> 0 hit(s) (exit
1). Corpus scan `rg -ic 'active-disturbance|extended-state-observer|adrc|
leso|bandwidth-parameteriz|total-disturbance'` eval/hit1-corpus.yaml -> 0
hits (exit 1). The only tree-wide disturbance-leaf neighbors, context-checked
as NOT owners: space-systems/adcs/environmental-disturbance-torque-budget
(desc verbatim: "estimate the worst-case environmental disturbance torque
budget for a spacecraft: compute gravity-gradient torque ... solar pressure
torque ... residual magnetic dipole torque ... aero drag torque" — an ADCS
sizing/magnitude leaf, no observer and no control law) and the gnc sliding-
mode leaf's own matched-uncertainty prose (bound F given, d never measured).

(b) Sibling fences (FRESH reads, verbatim): observer-design desc line 3:
"design a full-order Luenberger state observer for a linear time-invariant
system ... compute the estimator gain matrix by pole placement with the
Ackermann formula ... confirm the separation principle" — LTI state
estimation with no disturbance state and no bandwidth parameterization.
sliding-mode-control related-leaves (quoted under GO 1 (b)) name no
observer-based law, and its pitfalls renounce estimation outright ("the
nominal model f_nom, the uncertainty bound F and the disturbance d are all
given inputs, d is never measured or reconstructed"). adaptive-control /
l1-adaptive-control (quotes under GO 1 (b)) adapt GAINS against an unknown
plant coefficient on first-order plants; the LESO here runs fixed
bandwidth-parameterized gains and estimates a total disturbance state — the
wave-48 "recheck l1-adaptive/adaptive fences before any further robust/
adaptive member" reminder is honored: distinct identity, no collision.
h-infinity-synthesis / h-infinity-control own frequency-domain worst-case
synthesis/norm analysis (linear, ARE/gamma machinery), not a time-domain
augmented observer. control-allocation distributes a given command.

(c) Standards-map id exists: arp4754a line 38 (control-pack convention).

(d) Published deterministic anchor (summary-only): linear ADRC for the
canonical second-order plant y_ddot = f(y, y_dot, w) + b0 u with f the
"total disturbance" (internal dynamics plus external disturbance): run the
third-order linear extended state observer z1_dot = z2 + beta1 (y - z1),
z2_dot = z3 + beta2 (y - z1) + b0 u, z3_dot = beta3 (y - z1) with observer
gains from the bandwidth parameterization beta = (3 omega_o, 3 omega_o^2,
omega_o^3) placing all observer poles at -omega_o; form the disturbance-
rejection control u = (u0 - z3)/b0, and close the outer loop with u0 =
kp (r - z1) - kd z2 where kp = omega_c^2 and kd = 2 omega_c place the
tracking poles at -omega_c. Source: Gao, "Scaling and Bandwidth-
Parameterization Based Controller Tuning," Proceedings of the 2003 American
Control Conference (the standard closed-form LESO gain derivation); Han,
"From PID to Active Disturbance Rejection Control," IEEE Transactions on
Industrial Electronics 56(3):900-906, 2009. Deterministic offline closed-form
evaluation given b0, omega_o, omega_c and the plant simulation — no search,
no iteration, no adaptation.

(e) Two wordable Hit@1 corpus queries, sim-verified at wave-49 HEAD (same
router replication as GO 1):
1. "design the active-disturbance-rejection-control law for the second-order
   plant: run the linear-extended-state-observer with bandwidth-
   parameterized observer gains to estimate the total disturbance and cancel
   it with the disturbance-rejection term before the bandwidth-parameterized
   outer loop" -> HIT1 at 29.0 vs 10.5 (gnc-autonomy/control/adaptive-
   control).
2. "apply the linear-extended-state-observer in the adrc loop: estimate the
   state and the total disturbance from the plant output, divide the
   estimated disturbance by the plant gain for the rejection term, and close
   the controller on the estimated states" -> HIT1 at 21.0 vs 9.5
   (gnc-autonomy/control/observer-design).
Theft audit: 0 of 1326 tasks reroute with the candidate added.

(f) Tag set all hyphenated compounds: active-disturbance-rejection-control,
linear-extended-state-observer, adrc, bandwidth-parameterization, total-
disturbance-estimate, disturbance-rejection-term, observer-gain-parameter-
ization.

## Declines table (wave-46/47/48 rows re-verified FRESH; fresh seams probed this wave)

| Near-miss candidate | Gate(s) | Fresh evidence / decline reason |
|---|---|---|
| control/mu-synthesis (D-K iteration) | d | STAY (wave-48 reminder verbatim confirmed in the landed sibling's own fence, h-infinity-synthesis related-leaves lines 290-293: "mu-synthesis and D-K iteration are not siblings: iterative uncertainty-model schemes with no deterministic closed form were declined at wave-48 gate (d); this leaf owns only the deterministic state-space member of the robust vein."). Tree grep -> exactly that renouncement, corpus 0. Do not re-probe without a closed-form anchor. |
| L1-adaptive (brief hint: "still zero-owner?") | a | OWNED, not a candidate: gnc-autonomy/control/l1-adaptive-control on disk with the state-predictor / projection-based-adaptation-law / low-pass-filter identity (desc quote under GO 1 (b)); router row + routing note present. Fresh re-verify resolves the brief's probe hint to OWNED. |
| control/adaptive-backstepping (tuning functions) | scope | Zero-owner tree+corpus but the direct parameter-estimation extension of GO 1's recursion (Krstic et al. 1995 part II); pool economy — build the declared recursion core first, re-probe the adaptive variant only after backstepping lands and proves the identity. |
| control/nonlinear-dynamic-inversion as a separate leaf | a | Duplicate identity: feedback-linearization already owns the relative-degree / decoupling-inversion / zero-dynamics construction whose aerospace framing IS nonlinear dynamic inversion (wave-48 anchor). No distinct unowned math remains; a second leaf would fence-collide with the landed sibling. |
| estimation-filtering LESO/ESO placement | b | If placed in estimation-filtering it collides with the closed KF-form-variant doctrine (reminder item 6) and observer-design's Luenberger claim; as a CONTROL law (disturbance rejection with fixed bandwidths) it is the GO 2 identity above. Placement is control, not estimation. |
| navigation multipath / receiver tracking-loop | b, d | STAY: multipath whole-tree grep 0, corpus 0; empirical multipath magnitudes have no closed-form anchor; tracking-loop vocabulary 0 in gnc (RF/PNT interface, no standards id). |
| navigation/tdoa-positioning | b | STAY: acoustic-emission-inspection fence unchanged (leaf on disk); reopen only if it drops the generic hyperbolic iterated-LS claim. |
| navigation/time-differenced-carrier-phase | e | STAY: gnss-doppler-velocity-positioning unchanged (single-epoch delta-range-rate vocab owned); corpus 0. |
| navigation/vor-dme-positioning | b, e | STAY: avionics radio-navigation-aids owns the navaid geometry vocab with tag weight 3; corpus tasks unchanged. |
| estimation/attitude determination (QUEST/q-method/TRIAD) | a | STAY OWNED outside family: space-systems/adcs leaves (fresh listing verified). gnc space pack stays at 4 leaves. |
| guidance/trajectory-shaping / waypoint path following | b | STAY: trajectory-shaping vocab owned by impact-angle/impact-time/midcourse siblings + router; LNAV/CLOS own waypoint/cross-track vocab. |
| guidance/true-PN, PN variants, 3D engagement | b, e | STAY: PN/APN own planar LOS-rate geometry and maneuvering augmentation; corpus 0. |
| guidance/celestial / sight-reduction navigation | scope | STAY: stellar geometry adjacent to space-systems/adcs star-tracker territory; no wave brief raised it. |
| guidance/ascent linear-tangent / powered-descent | scope | STAY: launch/ascent territory is space-domain; space-systems mission-design owns entry-descent-landing etc. |
| optimal-control textbook cases (indirect methods etc.) | b, e | STAY: lqr/lqg/ilqr-ddp/mpc own AREs; bang-bang owns the minimum-principle switching case; corpus 0. |
| control/anti-windup | a | STAY OWNED: pid-control-design owns anti-windup clamping in desc + tags. |
| space pack additions (Hohmann, bi-elliptic, ADCS) | a | STAY OWNED outside family: space-systems orbit-mechanics + adcs leaves (fresh listing). gnc space pack CLOSED at 4 leaves. |

## Closed veins (owner leaf per vein, reaffirmed FRESH at wave-49 HEAD)

- GNSS positioning: pseudorange, doppler-velocity, carrier-smoothing, rtk,
  raim-fde, dilution-of-precision + per-source delay seam CLOSED
  (ionospheric + tropospheric on disk). Multipath (empirical anchor) and
  receiver tracking-loop (RF/PNT interface) declined.
- Passive localization: bearing-only. Hyperbolic TDOA CLOSED by
  manufacturing-quality/ndt/acoustic-emission-inspection.
- INS/integration: inertial-navigation, ins-gnss-integrated-filter,
  tightly-coupled-ins-gnss, terrain-referenced-navigation, navigation-frames.
  CLOSED.
- Estimation filters: alpha-beta, complementary, ekf, ukf, imm, particle,
  rts-smoother, process-noise-discretization, imu-static-calibration,
  kalman-filter-design, cramer-rao-lower-bound. CLOSED (form-variants
  declined; attitude determination owned by space-systems/adcs).
- Guidance laws: pursuit, pn, apn, command-to-line-of-sight, collision-
  course, midcourse, impact-point-prediction, coverage/dubins. Terminal-
  constraint family CLOSED (time + angle members both on disk).
- Optimal control: bang-bang, lqr, lqg, mpc, ilqr-ddp, dymos,
  loop-transfer-recovery. CLOSED.
- Control, linear: pid, lead-lag, root-locus, frequency-response,
  state-space, observer, digital-control-design, python-control,
  gain-scheduling, control-allocation, deadbeat, smith-predictor
  (delay compensation). CLOSED.
- Control, robust: h-infinity-control (S/KS norm analysis, w47) +
  h-infinity-synthesis (DGKF two-ARE, w48). CLOSED (mu-synthesis gate-d
  decline confirmed in the landed leaf's own fence).
- Control, adaptive: adaptive-control (MRAC), l1-adaptive-control. CLOSED
  (first-order gain-adaptation structures; fences unchanged, re-read FRESH).
- Nonlinear-control vein: sliding-mode-control + feedback-linearization
  landed w48 (vein proven) -> backstepping = GO 1 this wave; ADRC/LESO =
  GO 2 (fresh observer-based member, distinct from the switching and
  cancellation siblings). Backstepping's own adaptive variant (tuning
  functions) deferred to the wave after backstepping lands.
- Space pack (4 leaves): closed at gnc scope; space-systems owns the wider
  orbit/ADCS/mission-design space.

## Standards-map check

30 ids present (`grep '^  - id:' standards-map.yaml` = 30). Both GOs map
arp4754a (line 38, reference-only, control-pack convention — same as the
sliding-mode-control and feedback-linearization siblings' own frontmatter
use). No new standards ids required.

## Method note

All greps, scans and sims above were read-only terminal runs at HEAD
9c2b3fe4. The router sim replicates scripts/router_eval.py exactly
(hyphen-preserving tokens, stopword filter, tag weight 3 / name 2 / desc 1 /
body 0.5, verbatim-phrase bonus 4, tie-break score desc + path asc) with
per-skill token sets precomputed for speed, over the real 667-SKILL.md index
plus each hypothetical candidate, and over all 1326 eval/hit1-corpus.yaml
task blocks for the zero-theft audits (yaml parse recovered 1326/1326).
Baseline gate replication with candidates absent: 0/1326 failures at this
HEAD. Temporary read-only helper scripts lived outside the repo only; no
repo file was modified except this receipt (git status before/after: only
the wave49-recon receipts directory untracked).

Existing sibling corpus tasks confirmed distinct from the new query wording:
sliding-mode-control -> w48-sliding-mode-control-1/-2 (surface/reaching-law/
boundary-layer wording); feedback-linearization -> w48-feedback-linearization-
1/-2 (lie-derivative/relative-degree/decoupling wording); h-infinity-
synthesis -> w48-h-infinity-synthesis-1/-2 (dgkf/gamma-iteration wording).
The theft audit (0 reroutes of 1326 tasks per candidate) covers every
existing corpus task, including all w48 gnc tasks.

Recheck reminders for future waves: backstepping-control closes the
declared nonlinear-recursion sibling once built (its adaptive variant,
tuning-functions adaptive backstepping, is the re-probe seam only after the
core recursion lands and proves the identity; do not build both in one
wave); active-disturbance-rejection-control opens the observer-based
disturbance-rejection member of the control pack (further members of that
identity family — e.g. disturbance-observer-based-control DOBC variants —
share the same LESO total-disturbance core and should not be probed as
separate leaves); mu-synthesis/D-K stays closed on gate (d) unless a
closed-form anchor appears; the per-source delay seam, terminal-constraint
family, adaptive/MRAC/L1 structures, estimation and optimal-control veins,
and the space pack stay CLOSED unless a landed leaf narrows a fence (tdoa
reopens only if acoustic-emission-inspection drops its generic hyperbolic
iterated-LS claim; TDCP only if the doppler sibling narrows AND corpus
intent appears); guidance/navigation growth should come from the control
territory above, not from further siblings of closed veins.
