# WAVE-46 FLIGHT-MECHANICS PROBE RECEIPT (task-0, whole-family FRESH)

- Repo: the local AeroSkills repo at git HEAD d4b4d590 (verified `git log
  --oneline -3` first line: "d4b4d590 ops: wave-46 brief (CEO dispatch post
  wave-45 audit)").
- Scope: ENTIRE flight-mechanics family, 47 leaves (TIED SMALLEST with
  systems-engineering-safety 47), probed fresh. Read-only probe: no writes to
  skills/, eval/, standards-map.yaml, scripts/, Makefile, or ops/automation
  briefs. One write only: this receipt (ops/automation/state/wave46-recon/).
- Corpus baseline: eval/hit1-corpus.yaml = 1266 tasks (regex parse recovered
  1266/1266 task blocks, helper /tmp/w46_fm_corpus.py); 94 tasks target
  flight-mechanics leaves (task id, query, intent, expected_skill parsed).
- Standards map: 30 ids in standards-map.yaml (grep '^  - id:' = 30);
  candidate ids grep-verified below.
- Doctrine: wave-43 declines (rotorcraft-height-velocity-diagram,
  rotorcraft-forward-flight-envelope-limits) and the wave-45 whole-family
  NO_CANDIDATES receipt were re-checked with fresh evidence and stand. The
  ranked GO below is a seam that NO wave-43/44/45 receipt, leaf plan, or
  builder kit ever adjudicated (verified: zero mentions of rotorcraft
  forward-flight flapping or tip-path-plane in any ops/automation/state
  wave43/44/45 recon file or leaf plan), so ranking it does not reopen any
  closed vein.

## Verdict

1 ranked GO candidate: flight-mechanics/performance/rotorcraft-forward-flight-
flapping (steady first-harmonic flapping equilibrium of the main rotor in
forward flight: tip-path-plane longitudinal and lateral tilt from the advance
ratio and inflow ratio under uniform inflow, the flap-equilibrium next sibling
of rotorcraft-blade-flapping-dynamics, which owns only hover coning and the
rotating flap frequency ratio). Everything else in the family declines with
receipts below. Flight-mechanics at 47 is nearly saturated, but this one
rotorcraft blade-dynamics seam is genuinely open: zero owner tree-wide and in
the corpus, a published closed-form anchor in the same textbook chapters the
sibling leaf already cites, and an existing standards-map id (far-29).

## Whole-family enumeration (47 leaves, all probed)

`find skills/flight-mechanics -mindepth 3 -name SKILL.md` returned 47 files
(quoted in full below). Router parity 47 rows confirmed in the family router
skills/flight-mechanics/SKILL.md (leaf rows counted per pack below).

```
flight-dynamics-sim (2): point-mass-trajectory, six-dof-simulation
handling-qualities (4): cooper-harper-rating, mil-std-1797a,
  pilot-induced-oscillation, pitch-bandwidth-criteria
performance (30): balanced-field-length, breguet-endurance, breguet-range,
  climb-performance, descent-performance, energy-height, glide-performance,
  landing-performance, oei-climb-gradient, propeller-range,
  rotorcraft-autorotative-descent, rotorcraft-axial-descent-flow-states,
  rotorcraft-blade-element-hover-performance,
  rotorcraft-blade-flapping-dynamics, rotorcraft-forward-flight-performance,
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

### 1. flight-mechanics/performance/rotorcraft-forward-flight-flapping (GO, rank 1)

Steady first-harmonic (1/rev) flapping of an idealized centrally hinged rotor
blade in forward flight under uniform inflow: solve the flap-equilibrium
harmonic balance for the longitudinal flapping angle (tip-path-plane aft tilt)
and the lateral flapping angle as functions of the advance ratio mu and the
inflow ratio lambda, with the same uniform-inflow idealization, Lock-number
machinery, and closed-form conventions the sibling hover flapping leaf already
uses. Deterministic algebraic equilibrium solution, no numeric integration, no
empirical tables, no reverse-flow modeling. It is rotorcraft blade-dynamics
mechanics in the exact family convention that already hosts
rotorcraft-blade-flapping-dynamics and rotorcraft-lead-lag-dynamics under
performance/.

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/ (real output):

```
$ grep -rniE "tip[- ]path[- ]plane" skills/ eval/ | grep -v __pycache__; echo EXIT=$?
EXIT=1
```

```
$ grep -rniE "forward[- ]flight[- ]flapping|first[- ]harmonic[- ]flap|longitudinal[- ]flapping|lateral[- ]flapping|flap.*advance ratio" skills/ eval/ | grep -v __pycache__; echo EXIT=$?
EXIT=1
```

Tree-wide SKILL.md owner scan (grep -rniE "flapping" skills/ --include=SKILL.md
-l): only 4 files, all rotorcraft: the family router (routing row for
rotorcraft-blade-flapping-dynamics), rotorcraft-blade-element-hover-performance
(hover collective/torque side), rotorcraft-blade-flapping-dynamics (hover
coning + flap frequency ratio), rotorcraft-lead-lag-dynamics (hands flapping
motion to the flap sibling, quoted below). Corpus eval/hit1-corpus.yaml token
scan for tip-path-plane, tip path, first-harmonic, longitudinal flapping,
forward-flight-flapping: zero tasks (empty scan). Corpus tasks
w32-rotorcraft-blade-flapping-dynamics-1/-2 carry only lock-number, hover
coning angle, flap frequency ratio tokens and route to the hover leaf; w30
forward-flight tasks carry glauert-inflow, parasite-power, best-endurance
tokens and route to the power leaf. The "advance ratio" token exists in the
corpus only for propeller geometry tasks (w26-era advance-ratio tasks route to
vehicle-design/sizing/propeller-sizing and propulsion/turboprop/turboprop-
cycle on propeller-diameter and revolutions tokens), which do not overlap.

(b) Nearest sibling fence (quoted, skills/flight-mechanics/performance/
rotorcraft-blade-flapping-dynamics/SKILL.md lines 23-36):

"Use when the task is the basic blade-flapping dynamics of a helicopter
main rotor: the Lock number that fixes the ratio of aerodynamic flap
moment to centrifugal restoring moment, the steady hover coning angle
of an untwisted centrally hinged blade under uniform inflow, and the
rotating flap natural frequency ratio for a flap hinge offset."

and the same leaf, line 35-36:

"Flap dynamics here covers coning and frequency ratio, not ground
resonance or lag dynamics."

Supporting sibling fences:
- rotorcraft-lead-lag-dynamics lines 32-33: "damping and coupled eigenvalue
  stability analysis are out of scope, and blade flapping motion, coning and
  the rotating flap natural frequency belong to the flap-dynamics sibling."
  Flapping motion in ANY flight state is thus fenced to the flap-dynamics
  sibling, which owns only the hover-state quantities above.
- rotorcraft-forward-flight-performance lines 30-39: "implements the standard
  uniform-inflow momentum theory (Glauert inflow)..." and "Uniform inflow
  only: no reverse-flow region, no blade-element section polars, no
  compressibility." That leaf is power components and best speeds only
  (induced, parasite, profile power; best endurance and best range speed); it
  never touches blade motion, so the forward-flight flap equilibrium is not
  claimed there.

(c) Standards-map id exists (grep-verified):

```
$ grep -n "id: far-29" standards-map.yaml
270:  - id: far-29
```

far-29 is the established FM rotorcraft reference-only id (the rotorcraft
performance leaves carry the FAR-29 framing, e.g. rotorcraft-forward-flight-
performance "14 CFR Part 29 (FAR-29) frames rotorcraft performance
requirements"), matching the family convention.

(d) Published closed-form / deterministic computation anchor (summary-only, no
standard text reproduced):
- Johnson, Helicopter Theory, ch. 4, and Leishman, Principles of Helicopter
  Aerodynamics, ch. 4: the classical articulated-rotor flap model and the
  first-harmonic flapping response in forward flight (longitudinal and lateral
  flapping vs advance ratio and inflow) for uniform inflow. These are the
  SAME two chapters the sibling leaf already cites for its flap model
  (blade-flapping-dynamics lines 28-30: "This leaf implements the classical
  articulated-rotor flap model (Johnson, Helicopter Theory ch.4 and Leishman,
  Principles of Helicopter Aerodynamics ch.4, paraphrased, never reproduced)
  in pure Python, stdlib only, deterministic."), so the anchor is
  chapter-continuous with the existing leaf, not a new standard.
- Prouty, Helicopter Performance, Stability and Control, covers the same
  first-harmonic flap equilibrium for trimmed forward flight.
- The computation is deterministic algebraic harmonic balance on the flap
  equation with uniform inflow and an idealized centrally hinged blade, the
  direct forward-flight extension of the hover coning closed form the sibling
  already implements; no tables, no empiricism, no numeric integration.

(e) 2 wordable Hit@1 corpus queries carrying DISTINCTIVE hyphenated tokens
that route to this leaf without stealing existing corpus tasks (existing w32
flapping tasks carry lock-number, hover-coning, flap-frequency-ratio tokens;
w30 forward-flight tasks carry glauert-inflow and best-endurance tokens; the
propeller advance-ratio tasks route on propeller-diameter/revolutions tokens;
none carry forward-flight-flapping, tip-path-plane-tilt, first-harmonic, or
longitudinal-flapping-angle, so no theft):

1. "check the forward-flight-flapping of the helicopter main rotor at cruise:
   solve the first-harmonic flap equilibrium for the longitudinal and lateral
   flapping angles and report the tip-path-plane-tilt from the inflow ratio
   and the advance ratio"
2. "compute the rotorcraft tip-path-plane-tilt in forward flight for the trim
   assessment: the steady first-harmonic longitudinal-flapping-angle of the
   centrally hinged uniform blade at an advance ratio of 0.3 with uniform
   inflow"

(f) No generic single-word tag overlap: proposed tags are hyphenated compounds
only: forward-flight-flapping, tip-path-plane-tilt, first-harmonic-flap-
response, longitudinal-flapping-angle, lateral-flapping-angle,
advance-ratio-flapping, flap-equilibrium-tilt. Prune generic single-word tags
(flapping, rotorcraft, blade dynamics, rotor dynamics) since the family router
rows for rotorcraft-blade-flapping-dynamics and rotorcraft-forward-flight-
performance already own the generic rotorcraft/rotor-dynamics surface. Build-
time notes (rotorcraft-forward-flight-climb-test wave-45 precedent): add a
fence line to rotorcraft-blade-flapping-dynamics ("forward-flight flapping and
tip-path-plane tilt belong to the forward-flight sibling"), a router row in
skills/flight-mechanics/SKILL.md, and 2 corpus tasks at merge.

Family spread note: this keeps flight-mechanics at 47 -> 48 after landing,
matching the wave pattern where the tied-smallest family contributes a small
number of leaves.

## Declines table (all fresh probes this wave; STAY rows re-verified)

| Candidate seam | Reason |
|---|---|
| fixed-wing best-angle / best-rate-of-climb speed selection (Vx/Vy analytic, climb-performance sibling) | Measured-side owners and the hyphenated token are taken: FTO climb-performance-flight-test owns best-rate identification from its measured sweep ("Best rate of climb: best_rate_of_climb_fpm scans the true airspeed band at the test density and returns the maximum rate and the speed that achieves it", lines 71-75, plus service/absolute ceilings and time-to-climb from the best-rate schedule); corpus task w18-climb-performance-flight-test-2 ("determine the service ceiling and the time to climb from the best rate of climb schedule...") routes there; FTO rotorcraft-forward-flight-climb-test already carries the live tag best-rate-of-climb-speed plus vy-determination for the rotorcraft side. A new FM leaf would collide with a live hyphenated token (wave-45 cross-family tie class) and wave-45 doctrine closed the FM analytic Vy for rotorcraft on the FTO-measured-slot precedent. climb-performance owns ROC-at-speed/gradient/time/ceiling identities; no clean unowned token space remains |
| jet maximum-specific-range / optimum cruise speed from the drag polar (specific-range sibling) | Concept tokens owned on both sides: avionics/flight-management/performance-computation owns the max-range speed ("TAS in knots at which fuel per nm is minimum (max-range speed)", performance_computation_logic.py line 161; "g(V) = a*(c1 - 3 c2/V^4 + 7 c3 V^6); root is the max-range speed", line 168; "At CI = 0 the optimum collapses to the max range speed", SKILL.md line 104); FTO cruise-performance-flight-test owns maximum-range-cruise-Mach (parabola vertex M_mrc = -c1/(2*c2)) and long-range-cruise-Mach at 99 percent, with corpus task w28-cruise-performance-flight-test-1 carrying "maximum range cruise speed" tokens. The FM drag-polar optimum (CL for max specific air range, cd0 = 3 * cd_i balance) is a distinct formula but every natural English token for the concept routes to existing owners at Hit@1; tag space max-range-cruise-speed/long-range-cruise-speed occupied |
| rotorcraft power-limited maximum level speed Vmax (rotorcraft-forward-flight-performance sibling) | Not clean closed form: the high-speed intersection of an available-power curve with the Glauert-inflow power-required curve needs a numeric root, and engine power lapse with altitude needs empirical inputs; the retreating-blade-stall side of Vmax is semi-empirical (rotorcraft-forward-flight-envelope-limits closure applies). Measured owners exist: FTO rotorcraft-performance-flight-test, rotorcraft-forward-flight-performance-test, and envelope expansion. Corpus demand zero |
| fixed-wing banked / turning stall speed | FTO envelope/stall-characteristics-testing owns it: "level_turn_load_factor(bank_deg) and the corresponding stall speed" (line 65) and "Calling the turning stall speed the 1g stall speed: in a banked ... degree bank doubles the load factor and raises the stall speed by ..." (lines 78-80) |
| wind-adjusted best glide / MacCready speed-to-fly | Zero tree-wide and zero corpus for maccready, speed-to-fly, soaring; soaring cross-country optimization whose general-polar optimum is not clean closed-form station math; glide-performance owns still-air best glide, sink rate and time to descend |
| crossover altitude (CAS = Mach TAS) | Zero tree-wide and zero corpus; air-data conversion domain is cross-cutting units-atmos (isa-atmosphere, airspeed-conversion, density-altitude) plus FTO position-error-calibration; cross-cutting family is default CLOSED for this wave, and no FM home exists |
| fixed-wing ground effect on takeoff/landing distance | Published treatment is semi-empirical percent corrections, no clean closed-form physics anchor; takeoff-performance and landing-performance own their distance models; only VMCL-determination mentions ground effect and fences it out of scope |
| Neal-Smith pitch tracking criterion (handling-qualities) | Deterministic but requires a closed-loop pilot-model compensation search, not clean closed-form station math; zero corpus demand; mil-std-1797a and pitch-bandwidth-criteria own the pitch frequency-response HQ seam (MIL-STD-1797A bandwidth/phase-delay grading) |
| rotorcraft-height-velocity-diagram | STAY (wave-43): ANALYSIS vs FTO measurement slot. FTO rotorcraft-height-velocity-diagram-test fills the H-V function incl. failure-height-loss boundary analysis; wave-43 leaf-plan recorded "rotorcraft-height-velocity-diagram (ANALYSIS) conflicts with the FTO". No fresh counter-evidence |
| rotorcraft-forward-flight-envelope-limits | STAY (wave-43): retreating-blade-stall boundary is semi-empirical, fabricated-table risk without a published closed-form anchor. No fresh counter-evidence |
| hover ceiling OGE density-altitude root (FM analysis side) | STAY (wave-45): engine power lapse needs an empirical exponent (fabricated-correlation risk, rotorcraft-forward-flight-envelope-limits precedent); FTO rotorcraft-performance-flight-test reduces measured OGE/IGE hover ceilings (corpus w31 task); FM rotorcraft-hover-ground-effect owns the IGE hover ceiling height; rotorcraft-vertical-climb-performance re-runs the climb check at any density altitude |
| rotorcraft forward-flight climb Vy / ceilings analysis | STAY (wave-45): FTO rotorcraft-forward-flight-climb-test owns Vy-schedule and ceiling reduction (tags best-rate-of-climb-speed, vy-determination); FM rotorcraft-forward-flight-performance owns the analytic power-required sweep (best endurance/range speeds); rotorcraft-vertical-climb-performance owns VROC for available power |
| drift-down / OEI en-route ceiling | STAY (wave-45): standards-map-blocked, no far-121 or ac-120-42b id (30 ids verified); the drift-down path to ceiling is an energy integration, not clean closed form; zero corpus tasks |
| balked-landing / go-around gradient | STAY (wave-45): oei-climb-gradient owns the landing-configuration rows (approach climb gear down go-around power 2.1/2.4/2.7 by engine count, landing climb 3.2); FTO balked-landing-flight-test is the designated measurement reserve (wave-43); zero corpus tasks |
| propeller-endurance | STAY: breguet-endurance carries the propeller branch (prop_endurance with PSFC); propeller-range's Does NOT list confirms endurance of either propulsion type belongs to breguet-endurance |
| absolute ceiling / cruise ceiling extensions | STAY: climb-performance owns the service-ceiling closed form under linear ROC lapse and absolute ceiling is that identity at ROC = 0; cruise ceiling has no published deterministic definition; zero corpus tasks |
| time-to-climb / climb fuel and distance to cruise altitude | STAY: climb-performance owns time-to-climb at average ROC (corpus roc2); climb fuel and segment fuel fractions route to vehicle-design sizing-mission-profile |
| translation-lift / ETL onset | STAY: empirical onset band, no published closed-form anchor; Glauert induced-power falloff with speed already in rotorcraft-forward-flight-performance; zero corpus tasks |
| corner velocity / instantaneous turn | STAY (wave-43): FTO envelope-expansion owns corner speed (corpus task ee1); V-n diagram owned by structures/loads/gust-maneuver-loads and FTO load-factor-envelope |
| rotorcraft autorotative glide range / vortex-ring-windmill transition range | STAY (wave-31/45): wave-31 review declined (Leishman receipts cited in rotorcraft-autorotative-descent); rotorcraft-axial-descent-flow-states owns the windmill-brake momentum band |
| rotorcraft Category A OEI takeoff | Decision-point envelope procedure, not clean closed form; FTO rotorcraft-category-a-oei-flight-test designated measurement reserve (wave-43 plan) |
| runway-limited MTOW / field-length-constrained takeoff weight | vehicle-design owner (payload-range-diagram MTOW, ws-tw-trade, constraint-analysis); balanced-field-length fence line 39 explicitly assigns "the inverse sizing of thrust or wing loading from a required field length (vehicle-design/conceptual/constraint-analysis)" away from FM |
| first/approach/landing FAR-25.121 segment rows beyond the owned set | oei-climb-gradient owns the 25.121 minima rows; any new row-content leaf is table-gated with fabricated-table risk, no closed-form anchor |

## Wave-43/45 stays confirmed (no fresh counter-evidence found)

rotorcraft-height-velocity-diagram and rotorcraft-forward-flight-envelope-
limits stays stand, re-verified this wave (reasons above; both FTO measurement
slots are filled leaves under skills/flight-test-operations/performance/:
rotorcraft-height-velocity-diagram-test, rotorcraft-forward-flight-climb-test,
rotorcraft-performance-flight-test). The wave-45 declines re-run here
(drift-down, balked-landing, propeller-endurance, hover-ceiling, Vy/ceilings,
translation-lift, absolute/cruise ceiling, corner velocity, autorotation
range, Category A OEI, zero-token seams) all still stand with the same or
stronger evidence.

## Closed veins list (fresh confirmations)

- Climb/descent/glide family: ROC, gradient, time-to-climb, service ceiling,
  descent planning, glide ratio/sink/best glide, windshear F-factor all owned;
  best-climb-speed selection tokens are FTO-owned (climb-performance-flight-
  test, rotorcraft-forward-flight-climb-test), see declines.
- Energy family: Ps, energy height, zoom climb owned (energy-height); level
  acceleration measured side owned (FTO level-acceleration-test).
- Range/endurance/cruise family: jet range, prop range, jet+prop endurance,
  specific air range, rotorcraft range/endurance, payload-range and ferry
  (vehicle-design) all owned; the cruise-speed optimization token space is
  owned by avionics flight-management performance-computation and FTO
  cruise-performance-flight-test, see declines. Vein closed on both
  propulsion branches and both measured sides.
- Takeoff/landing field length family: stall/liftoff/ground roll,
  balanced field V1 with ASD/AGD and 35-ft OEI air segment, OEI gradients,
  landing approach/flare/50-ft/stopping, measured takeoff/landing distance
  (FTO), takeoff-distance sizing constraint (vehicle-design). Vein closed.
- Turn/maneuver family: fixed-wing sustained turn, rotorcraft banked-turn
  power, corner speed measured (FTO), V-n (structures + FTO). Vein closed.
- Rotorcraft performance family: hover (momentum + FM), blade-element hover,
  IGE hover + IGE ceiling height, vertical climb VROC, forward flight power +
  best speeds, turn, autorotation, axial descent/vortex-ring/windmill,
  range/endurance, main/tail rotor sizing, lead-lag/ground-resonance-adjacent.
  Blade dynamics vein: hover coning + flap frequency ratio OWNED
  (blade-flapping-dynamics); lead-lag OWNED; ground/air resonance stability
  analysis OUT (lead-lag fence); forward-flight flapping equilibrium OPEN
  (rank-1 GO above, never adjudicated in waves 43-45).
- Speed stability: TR/PR curves, back side, v_md/v_mp owned.
- Handling qualities: cooper-harper, mil-std-1797a levels, PIO, pitch
  bandwidth/phase delay all owned; Neal-Smith declines (above).

## Standards-map check

30 ids present in standards-map.yaml (verified by grep): arinc-429, arinc-664,
arp4754a, arp4761a, as9100, as9102, asme-y14-5, cmh-17, cs-25, do-160,
do-178c, do-254, do-330, ecss, far-107, far-25, far-29, far-33, itar-ear,
mil-std-1553, mil-std-1797a, mmpsd, msg-3, naca-tn-902, naca-tr-824, nas-410,
rtca-do-185, rtca-do-229, rtca-do-260b, sep-2640. No far-121, no ac-120-42b,
no iso-15530, no mil-hdbk-217 (drift-down and parts-count style seams stay
map-blocked). far-25, cs-25 and far-29 exist and are the FM family
conventions; the rank-1 GO uses far-29 reference-only.

## Method note

All greps and scans above were read-only terminal/search_files runs. Helper
scripts written to /tmp (w46_fm_corpus.py, w46_fences.py). The corpus parser
recovered 1266/1266 task blocks (id, query, intent, expected_skill), so the
FM inventory of 94 tasks and every token-demand scan are complete-file scans.
No repo file was modified except this receipt.
