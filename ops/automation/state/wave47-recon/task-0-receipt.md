# WAVE-47 FLIGHT-MECHANICS PROBE RECEIPT (task-0, whole-family FRESH)

- Repo: the local AeroSkills repo. HEAD verified `git log --oneline -1` =
  a4ae6d1e ("Wave-47: close-out must auto-update products-state (FIX)");
  the wave-47 dispatch baseline a544f421 ("ops: wave-47 brief ... baseline
  635") is the second commit back, same wave, no family change between.
  Family state matches the wave-46-close baseline (635 leaves, 1286 corpus
  tasks, 30 standards) plus the wave-46 landing the brief names.
- Scope: ENTIRE flight-mechanics family, 48 leaves (2 flight-dynamics-sim +
  4 handling-qualities + 31 performance + 11 stability-control), probed
  FRESH. Read-only probe: no writes to skills/, eval/, standards-map.yaml,
  scripts/, Makefile, or any ops/automation brief. One write only: this
  receipt (ops/automation/state/wave47-recon/).
- Corpus baseline: eval/hit1-corpus.yaml = 1286 task blocks (regex parser
  recovered 1286/1286, helper script in /tmp); 96 tasks target the 48
  flight-mechanics leaves, exactly 2 per leaf including the wave-46 leaf
  (w46-rotorcraft-forward-flight-flapping-1/-2). Standards map: 30 ids
  (grep '^  - id:' = 30), far-29 verified at line 270.
- Doctrine: wave-43 declines (rotorcraft-height-velocity-diagram,
  rotorcraft-forward-flight-envelope-limits), the wave-45 whole-family
  NO_CANDIDATES (fixed-wing Vmax/Vmin row included) and the wave-46 ranked
  GO (rotorcraft-forward-flight-flapping, LANDED) were all re-checked with
  fresh greps. The ranked GO below is the seam the wave-46 receipt left
  open ("forward-flight flapping equilibrium OPEN (rank-1 GO above...)" -
  the wave-46 leaf models collective-only forcing; control inputs were
  never adjudicated in waves 43-46; verified: zero mentions of rotorcraft
  cyclic pitch, swashplate or control-plane in any wave43/44/45/46 recon
  file, leaf plan, builder kit, or spec).

## Verdict

1 ranked GO candidate:
flight-mechanics/performance/rotorcraft-cyclic-pitch-trim (steady
first-harmonic flap equilibrium WITH longitudinal and lateral cyclic pitch
control under uniform inflow, plus the trim inversion: the cyclic and
swashplate-tilt inputs required to hold the tip-path plane at a target
longitudinal/lateral attitude). It is the control-channel completion of the
wave-46 leaf, which models the flap equilibrium with collective pitch only
(the workflow inputs are "advance ratio mu, uniform inflow ratio lambda,
collective pitch theta0 and blade Lock number gamma" - no control channel).
Everything else in the family declines with receipts below; the three
wave-47-hinted blade-dynamics seams (nonuniform-inflow flapping, flapping
in maneuvers, lag dynamics in forward flight) each fail the deterministic-
anchor gate on fresh evidence, and the fixed-wing and rotorcraft performance
veins re-confirm saturated. Flight-mechanics at 48 is at its leaf margins;
this one control-channel seam is the family's remaining yielding point.

## Whole-family enumeration (48 leaves, all probed)

`find skills/flight-mechanics -mindepth 3 -name SKILL.md` = 48 files; router
parity 48 rows confirmed in skills/flight-mechanics/SKILL.md.

```
flight-dynamics-sim (2): point-mass-trajectory, six-dof-simulation
handling-qualities (4): cooper-harper-rating, mil-std-1797a,
  pilot-induced-oscillation, pitch-bandwidth-criteria
performance (31): balanced-field-length, breguet-endurance, breguet-range,
  climb-performance, descent-performance, energy-height, glide-performance,
  landing-performance, oei-climb-gradient, propeller-range,
  rotorcraft-autorotative-descent, rotorcraft-axial-descent-flow-states,
  rotorcraft-blade-element-hover-performance, rotorcraft-blade-flapping-dynamics,
  rotorcraft-forward-flight-flapping (wave-46), rotorcraft-forward-flight-performance,
  rotorcraft-hover-ground-effect, rotorcraft-hover-performance,
  rotorcraft-lead-lag-dynamics, rotorcraft-main-rotor-sizing,
  rotorcraft-range-endurance, rotorcraft-tail-rotor-sizing,
  rotorcraft-turn-performance, rotorcraft-vertical-climb-performance,
  specific-range, speed-stability, takeoff-performance, thrust-required,
  turn-performance, wind-effects, windshear-analysis
stability-control (11): aileron-reversal, control-surface-effectiveness,
  deep-stall-analysis, dynamic-stability, lateral-directional-stability,
  longitudinal-stability, phugoid-mode-analysis, short-period-mode-analysis,
  spin-recovery, stability-derivatives-avl, trim-analysis
```

## Ranked GO candidate

### 1. flight-mechanics/performance/rotorcraft-cyclic-pitch-trim (GO, rank 1)

Extend the wave-46 steady first-harmonic flap equilibrium of the idealized
centrally hinged, untwisted blade under uniform inflow with the control
channel: blade pitch theta = theta0 + theta1c*cos(psi) + theta1s*sin(psi)
instead of collective theta0 alone. The leaf computes (forward map) the
tip-path-plane longitudinal and lateral flapping response to longitudinal
and lateral cyclic pitch at a given advance ratio and inflow ratio - the
affine control-to-flap response, which must reproduce the wave-46 leaf's
closed forms exactly at zero cyclic - and (trim inversion) the cyclic
pitch and swashplate tilt required to hold the tip-path plane at a target
attitude (level disk, or a prescribed longitudinal/lateral tilt) for a
trim assessment. Deterministic algebraic harmonic balance on the same 3 by
3 system family, no numeric integration, no tables, no empirical inputs;
the cyclic-forced response and its inversion are linear algebra with the
same polynomial denominators the wave-46 leaf already publishes.

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/ (real output):

```
$ grep -rniE "cyclic pitch|swashplate|longitudinal cyclic|lateral cyclic|control plane|control-plane" skills/ eval/
   (SKILL.md, *.yaml, *.yml; __pycache__ excluded)
skills+eval 'cyclic pitch':  0    skills+eval 'swashplate':  0
skills+eval 'longitudinal cyclic': 0    skills+eval 'lateral cyclic': 0
skills+eval 'control plane': 0    skills+eval 'control-plane': 0
```

Corpus scan: the ONLY task in eval/hit1-corpus.yaml carrying "cyclic" is
w24r-strain-life-fatigue-2 (structural fatigue loading; stress-cycle
tokens, no rotorcraft content). Zero corpus tasks mention swashplate or
any rotorcraft control input. The wave-46 corpus tasks
(w46-rotorcraft-forward-flight-flapping-1/-2) carry forward-flight-flapping,
tip-path-plane-tilt, first-harmonic, longitudinal/lateral-flapping-angle
tokens only - no control tokens - so they continue to route to the wave-46
leaf, not this one.

(b) Nearest sibling fences (quoted):

- rotorcraft-forward-flight-flapping (the direct parent, wave-46), workflow
  step 1: "Fix the operating point: advance ratio mu, uniform inflow ratio
  lambda, collective pitch theta0 and blade Lock number gamma (the same
  gamma the hover sibling computes from blade geometry)." Scope note: "0
  <= mu < 1 (singular at mu = 1, reverse flow out of scope), lambda > 0
  (downward-positive convention), theta0 > 0, centrally hinged, first
  harmonic only, small angles." The wave-46 leaf models collective-only
  forcing; no cyclic pitch appears anywhere in its inputs, closed forms or
  fence, and its corpus tasks invoke "the trim assessment" without any leaf
  able to supply the control inputs a trim assessment requires.
- rotorcraft-blade-flapping-dynamics lines 23-36: "the steady hover coning
  angle of an untwisted centrally hinged blade under uniform inflow, and
  the rotating flap natural frequency ratio for a flap hinge offset...
  Flap dynamics here covers coning and frequency ratio, not ground
  resonance or lag dynamics." Hover-state quantities only; no 1/rev
  control content.
- rotorcraft-lead-lag-dynamics lines 30-34: "damping and coupled
  eigenvalue stability analysis are out of scope, and blade flapping
  motion, coning and the rotating flap natural frequency belong to the
  flap-dynamics sibling."
- rotorcraft-forward-flight-performance: "Uniform inflow only: no
  reverse-flow region, no blade-element section polars, no
  compressibility." Power and best-speeds leaf; never touches blade motion
  or control.
No sibling produces, fences, or tags cyclic pitch, swashplate tilt or any
control-plane quantity. The family router row for rotorcraft-blade-flapping-
dynamics ("blade flapping... rotor dynamics") is broad and will need a
fence addition at merge (build-time note below).

(c) Standards-map id exists (grep-verified): standards-map.yaml line 270
`- id: far-29`, the established FM rotorcraft reference-only id in the
family convention (30 ids total, grep '^  - id:' = 30). far-29 frames the
transport-category rotorcraft certification context for rotor loads and
trim; reference-only per the sibling convention.

(d) Published deterministic anchor (summary-only, no standard text
reproduced):
- Chapter-continuous with both flap siblings: rotorcraft-blade-flapping-
  dynamics and rotorcraft-forward-flight-flapping both cite "Johnson,
  Helicopter Theory ch.4 and Leishman, Principles of Helicopter
  Aerodynamics ch.4, paraphrased, never reproduced". Those chapters derive
  the forward-flight flap equilibrium from the blade pitch that includes
  the cyclic terms (theta1s on sin(psi), theta1c on cos(psi)); the wave-46
  leaf implements the collective-only specialization of that derivation
  (its own scope line: the only pitch input is theta0). Adding the cyclic
  forcing to the same harmonic balance, and inverting the resulting affine
  control-to-flap map for the trim cyclic, is the standard control/trim
  content of the same chapter material. The classical longitudinal-cyclic
  plus hinged-blade flapping literature (e.g. ARC R&M 2958, "An Analysis
  of the Longitudinal Stability and Control..." of hinged-blade
  helicopters) treats exactly this control-to-flap channel.
- Determinism anchors IN-REPO (the strongest check, same style the wave-46
  leaf used for its hover-limit identity): at theta1c = theta1s = 0 the
  leaf must reproduce the wave-46 closed forms for a0, a1s and b1s
  exactly, and at mu = 0 with zero cyclic the hover sibling's coning
  closed form - two exact cross-leaf identities verifiable at build time
  from leaves already in the tree. The trim-cyclic magnitudes must stay in
  the published few-degree band the wave-46 leaf reports for its own
  flapping angles (a1s magnitude ~1.5-5 deg over mu = 0.1-0.35), an
  ordering identity the worked example can check.
- Computation class: deterministic affine linear algebra on the wave-46
  equilibrium system; no numeric integration, no tables, no empiricism.
  Build-time caution (recorded for the spec phase, anchor-first): the spec
  must derive the cyclic-forced system from the general textbook
  derivation and pin sign conventions to the wave-46 leaf's (psi from the
  downwind blade position, advancing side at psi = pi/2, a1s < 0 = aft
  tilt) before writing any module formula; the in-repo identities above
  are the acceptance tests.

(e) 2 wordable Hit@1 corpus queries carrying DISTINCTIVE hyphenated tokens
that route to this leaf without stealing existing corpus tasks (existing
w46 tasks carry forward-flight-flapping, tip-path-plane-tilt,
longitudinal-flapping-angle, lateral-flapping-angle, advance-ratio-flapping
tokens; no existing task in the 1286-task corpus carries cyclic-pitch,
swashplate or control-plane tokens - the only "cyclic" task is the fatigue
one with stress-cycle tokens, so no theft):

1. "check the main-rotor trim control at cruise: solve for the
   longitudinal-cyclic-pitch and the lateral-cyclic-pitch required to hold
   the tip-path plane at the level-disk attitude at an advance ratio of
   0.3 with uniform inflow"
2. "compute the swashplate-tilt cyclic inputs to trim the rotor disk to a
   target longitudinal and lateral flapping state at a given advance ratio
   and inflow ratio, and report the cyclic-flap-response gains of the
   centrally hinged blade"

(f) No generic single-word tag overlap: proposed tags are hyphenated
compounds only: longitudinal-cyclic-pitch, lateral-cyclic-pitch,
swashplate-tilt, cyclic-flap-response, trim-cyclic, control-plane-tilt,
disk-attitude-trim. Prune generic single-word tags (cyclic, pitch, rotor
control, rotorcraft) since the flap siblings and the family router own the
generic rotorcraft/blade-dynamics surface. Build-time notes (wave-46
precedent): add a fence line to rotorcraft-forward-flight-flapping
("collective-only equilibrium; cyclic pitch, swashplate-tilt and
control-plane content belong to the cyclic-trim sibling"), fence the broad
rotorcraft-blade-flapping-dynamics router guidance row, add a router row in
skills/flight-mechanics/SKILL.md, and add 2 corpus tasks at merge.

Family spread note: flight-mechanics 48 -> 49 after landing, matching the
wave pattern where this family contributes a small number of leaves.

## Declines table (all fresh probes this wave; STAY rows re-verified)

| Candidate seam | Reason |
|---|---|
| rotorcraft-flapping-nonuniform-inflow (linear-inflow gradient in the 1/rev equilibrium) | Zero-owner verified (nonuniform/linear inflow, inflow gradient/distribution: 0 skills + 0 corpus) but the deterministic-anchor gate fails on fresh evidence: NASA TP (Johnson, "Comparison of Calculated and Measured ... flapping angles", 1980, ntrs) documents that simple linear-inflow-gradient models systematically underpredict lateral flapping below mu ~0.2 and that even undistorted-wake nonuniform inflow is inadequate there - the useful treatments need wake-geometry/free-wake machinery, not a closed form. No single canonical published formula set with verifiable magnitudes; parameterization-dependent (gradient sign/scale conventions vary) -> fabricated-formula risk, wave-43 rotorcraft-forward-flight-envelope-limits precedent. The wave-46 leaf's own pitfall ("the underlying uniform-inflow idealization and reverse-flow omission break down long before mu = 1") shows the refinement chases a model already at its idealization limit |
| rotorcraft-flapping-in-maneuvers (hub roll/pitch-rate terms in the equilibrium) | Zero-owner verified (maneuver flapping: 0 skills + 0 corpus) but anchor exists only at research/aeroelastic level: forward-flight coupled flap-lag-torsional response is solved as sequences of linear periodic response problems with quasilinearization (JAHS literature), and the hinged-blade stability/control treatments (ARC R&M 2958) are stability analyses, not equilibrium closed forms; the body-rate flap response is model-dependent (hinge offset, damping) with no canonical magnitude set. Degenerates toward rotorcraft flight dynamics/control, which the family does not host (stability-control pack is fixed-wing only). Zero corpus demand |
| rotorcraft-lag-dynamics-forward-flight | The lead-lag sibling already fences the needed machinery out ("damping and coupled eigenvalue stability analysis are out of scope"); forward-flight lag response is periodic-coefficient aeroelastic response, not clean closed form (JAHS: sequence of linear periodic response problems); needs damping/eigenvalue content the family convention excludes |
| rotorcraft-flapping-transient-response (rotor first-order lag / time constant from the Lock number) | Zero-owner verified and fence-clean, but declined: the canonical time-constant formula lives in rotorcraft flight-dynamics texts (not the Johnson/Leishman ch.4 equilibrium derivations the flap siblings cite), giving no chapter-continuous anchor and no in-repo cross-check identity; single-formula-plus-step-response content is thinner than any existing FM leaf; transient rotor response sits closer to rotorcraft stability/control (unhosted in this family; stability-control pack is fixed-wing); zero corpus demand. Reopen trigger: a verified textbook equation set with magnitudes AND any demand signal (corpus task or FTO-adjacent slot) |
| fixed-wing level-flight Vmax/Vmin speed envelope (thrust-available = thrust-required intersection) | STAY (wave-45 row, re-verified with fresh greps): thrust-required owns the level-flight TR/PR envelope (v_md, v_mp, T_min closed forms) and speed-stability owns level-flight trim-speed classification on the same curve; propeller Vmax root has no clean closed form; zero corpus tasks; generic-tag overlap. Fresh addition: the available side is token-owned by vehicle-design/sizing/engine-sizing (live tags sea-level-static-thrust, thrust-lapse, thrust-margin, top-of-climb) and thrust-required's own pitfall routes "sea level static thrust, thrust lapse, and the thrust margin against the cruise drag" to engine-sizing - an FM Vmax leaf would collide on thrust-lapse tokens. No fresh counter-evidence |
| cruise-climb profile / optimum-cruise-altitude (constant-CL cruise-climb fuel identity) | Cross-family tie: the only SKILL.md in skills/ holding "step climb" is avionics/flight-management/performance-computation (FMS cruise-speed/cost-index domain, which also owns the max-range speed roots); mission segment fuel and reserve policy are owned by vehicle-design/conceptual/sizing-mission-profile (wave-45 decline row). "Cruise profile"/"altitude profile"/"optimum altitude" tokens are zero tree-wide, but every natural routing surface for "which altitude/schedule to cruise at" is FMS or mission design; zero corpus demand |
| analytic stick-force-per-g / maneuvering stability (stick-free stability) | FTO stability/control-force-flight-test owns the live hyphenated tokens force-per-g and stick-force-gradient with corpus task support (pull-up per-g reduction); FM control-surface-effectiveness owns stick-force magnitude at the FAR-25.143 limit maneuver; an FM analytic-gradient leaf collides at token level with the FTO measured slot (wave-45/46 FTO-measured doctrine, Vy precedent) |
| fixed-wing maximum-specific-range / optimum cruise speed | STAY (wave-46): avionics performance-computation owns max-range-speed root and cost-index optimum; FTO cruise-performance-flight-test owns maximum-range-cruise-Mach/long-range-cruise-Mach; every natural token routes to an existing owner. No fresh counter-evidence |
| best-climb-speed Vx/Vy analytic selection | STAY (wave-46): FTO climb-performance-flight-test owns best-rate identification from its measured sweep (live tag best-rate-of-climb-speed), FTO rotorcraft-forward-flight-climb-test owns the rotorcraft Vy side; climb-performance owns ROC/gradient/ceiling identities. No fresh counter-evidence |
| hydroplaning speed / wet-runway stopping | Thin single semi-empirical NASA formula (V_p = 9 sqrt(psi)), no corpus demand, no independent closed-form identity; landing-performance owns stopping distance through the braking coefficient (condition enters as mu) and FTO landing-distance-determination is the measured slot |
| rotorcraft power-limited maximum level speed Vmax | STAY (wave-46): high-speed intersection of available-power with Glauert-inflow power-required needs a numeric root; engine power lapse empirical; retreating-blade-stall side semi-empirical (wave-43 envelope-limits closure); FTO rotorcraft-performance-flight-test / rotorcraft-forward-flight-performance-test measured owners. No fresh counter-evidence |
| rotorcraft-height-velocity-diagram | STAY (wave-43): ANALYSIS vs FTO measurement slot; FTO rotorcraft-height-velocity-diagram-test fills the H-V function incl. failure-height-loss boundary. No fresh counter-evidence |
| rotorcraft-forward-flight-envelope-limits | STAY (wave-43): retreating-blade-stall boundary semi-empirical, fabricated-table risk without a published closed-form anchor. No fresh counter-evidence |
| hover ceiling OGE density-altitude root | STAY (wave-45): engine power lapse empirical exponent; FTO rotorcraft-performance-flight-test reduces measured OGE/IGE ceilings; rotorcraft-hover-ground-effect owns the IGE ceiling height; rotorcraft-vertical-climb-performance re-runs climb checks at any density altitude |
| rotorcraft forward-flight climb Vy / ceilings | STAY (wave-45): FTO rotorcraft-forward-flight-climb-test owns Vy-schedule and ceiling reduction; rotorcraft-forward-flight-performance owns the power sweep; vertical-climb owns VROC |
| drift-down / OEI en-route ceiling | STAY (wave-45): standards-map-blocked (no far-121 or ac-120-42b in the 30 ids); energy integration, not closed form; zero corpus tasks |
| balked-landing / go-around gradient | STAY (wave-45): oei-climb-gradient owns the 25.121 landing/approach rows; FTO balked-landing measurement reserve; zero corpus tasks |
| autorotative forward-flight glide range / vortex-ring-windmill transition range | STAY (wave-31/45/46): rotorcraft-autorotative-descent explicitly owns the steady autorotative glide ("descent rate that the airframe reaches in a steady autorotative glide", line 25) and its Leishman receipts; rotorcraft-axial-descent-flow-states owns the windmill-brake band |
| rotorcraft Category A OEI takeoff | STAY (wave-43): decision-point envelope procedure, not closed form; FTO rotorcraft-category-a-oei flight test designated reserve |
| translation-lift / ETL onset | STAY (wave-46): empirical onset band; Glauert induced-power falloff already in rotorcraft-forward-flight-performance |
| absolute/cruise ceiling, time-to-climb, climb fuel/distance | STAY (wave-45/46): climb-performance owns the ROC-lapse ceilings and time-to-climb; mission fuel segments route to vehicle-design sizing-mission-profile |
| corner velocity / instantaneous turn | STAY (wave-43): FTO envelope-expansion owns corner speed; V-n owned by structures loads + FTO load-factor-envelope |
| rotorcraft tail-rotor yaw trim in forward flight / vertical-fin unloading | Semi-empirical: fin-offload and tail-rotor yaw-moment closure in forward flight need empirical fin/tail-rotor interference inputs; rotorcraft-tail-rotor-sizing owns the anti-torque thrust/power identities; no corpus demand |
| wind-corrected range / still-air-range scaling | STAY (wave-45): thin extension of wind-effects over breguet-range/propeller-range/specific-range; no independent closed-form identity; zero corpus tasks |

## Wave-43/45/46 stays confirmed (no fresh counter-evidence found)

rotorcraft-height-velocity-diagram, rotorcraft-forward-flight-envelope-
limits, fixed-wing level Vmax/Vmin, drift-down, balked landing,
propeller-endurance (breguet-endurance owns the prop branch), hover
ceilings, Vy/ceilings, translation-lift, corner velocity, autorotative
range, Category A OEI, wind-corrected range - all re-verified this wave
with fresh greps; all measured slots under flight-test-operations remain
filled leaves. The wave-45 whole-family NO_CANDIDATES and the wave-46
declines table stand; the only family change since wave-46 is the landed
rotorcraft-forward-flight-flapping leaf, whose control-channel seam is
exactly the rank-1 GO above and was never adjudicated in waves 43-46.

## Closed veins list (fresh confirmations)

- Climb/descent/glide: ROC, gradient, time-to-climb, ceilings, descent
  planning, glide ratio/sink/best glide, windshear all owned; Vx/Vy
  tokens FTO-owned.
- Energy: Ps, energy height, zoom climb owned; level-acceleration measured
  side FTO-owned; E-M contour mapping is a sweep of energy-height, no new
  identity.
- Range/endurance/cruise: jet/prop range, endurance, SAR, rotorcraft
  range/endurance owned; cruise-speed and altitude-profile optimization
  token space owned by avionics performance-computation (step-climb) and
  FTO cruise test; mission segments by vehicle-design.
- Takeoff/landing field: distances, V1 balance with ASD/AGD, OEI gradients,
  landing flare/stopping, measured slots (FTO), sizing constraints
  (vehicle-design) all owned.
- Turn/maneuver: sustained turn, rotorcraft banked-turn power, corner speed
  (FTO), V-n (structures + FTO) owned; stick-force-per-g measured (FTO).
- Speed stability and handling qualities: TR/PR back side, v_md/v_mp,
  cooper-harper, mil-std-1797a, PIO, pitch bandwidth all owned; Neal-Smith
  declined wave-46; rotorcraft HQ standards-map-blocked (no ADS-33 id
  among the 30).
- Rotorcraft blade dynamics: hover coning + flap frequency (hover leaf),
  lead-lag frequency/modes/ground-resonance clearance (lead-lag leaf),
  steady 1/rev forward-flight equilibrium collective-only (wave-46 leaf).
  Control channel: cyclic pitch/swashplate/control-plane OPEN (rank-1 GO
  above). Nonuniform inflow, maneuver flapping, transient response,
  forward-flight lag each fail the deterministic-anchor gate (declines
  above).

## Standards-map check

30 ids present in standards-map.yaml (grep-verified): arinc-429, arinc-664,
arp4754a, arp4761a, as9100, as9102, asme-y14-5, cmh-17, cs-25, do-160,
do-178c, do-254, do-330, ecss, far-107, far-25, far-29, far-33, itar-ear,
mil-std-1553, mil-std-1797a, mmpsd, msg-3, naca-tn-902, naca-tr-824,
nas-410, rtca-do-185, rtca-do-229, rtca-do-260b, sep-2640. far-25, cs-25
and far-29 are the FM family conventions; the rank-1 GO uses far-29
reference-only (line 270). No far-121, no ac-120-42b, no ads-33 (drift-down
and rotorcraft-HQ seams stay map-blocked).

## Method note

All greps and scans above were read-only terminal/search_files runs; helper
scripts written to /tmp only. The corpus parser recovered 1286/1286 task
blocks (id, query, intent, expected_skill), so the FM inventory of 96 tasks
and every token-demand scan are complete-file scans. Web lookups were used
only to check the existence and adequacy of published anchors (NASA TP on
nonuniform-inflow flapping; Leishman chapter structure; hinged-blade
longitudinal-cyclic literature); no candidate was ranked from memory.
No repo file was modified except this receipt.
