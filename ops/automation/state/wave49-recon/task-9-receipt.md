# WAVE-49 FLIGHT-TEST-OPERATIONS PROBE RECEIPT (task-9, whole-family FRESH extension probe)

- Repo: the local AeroSkills repo. HEAD verified `git log --oneline -1` =
  9c2b3fe4 ("ops: stage wave-49 brief (655 baseline, daylight gate 11:45
  UTC)"). Working tree clean except the wave49-recon receipts directory
  (git status --porcelain: 1 untracked entry, this receipt).
- Scope: ENTIRE flight-test-operations family, 49 leaves (envelope 14 +
  flutter 4 + performance 17 + planning 9 + stability 4 + uas 1), probed
  FRESH at wave-49 HEAD. This is an EXTENSION probe under the brief's
  smallest-first saturated-family extension tier: wave-48 declared
  NO_CANDIDATES for this family (ops/automation/state/wave48-recon/
  task-8-receipt.md, probed at 92d84a48) and that verdict stands only if
  fresh evidence at this HEAD confirms it.
- Doctrine read in full first: wave-48 task-8 (FTO whole-family, NO_
  CANDIDATES), wave-47 task-9 (FTO whole-family, NO_CANDIDATES), wave-46
  task-4 (FTO whole-family, NO_CANDIDATES), wave-45 task-5 (FTO, 1 GO
  vmcl-determination, now on disk). Sibling wave-49 receipts read for
  fence awareness: task-0 (gnc-autonomy), task-1 (vehicle-design), task-2
  (structures), task-3 (avionics), task-4 (propulsion), task-5
  (space-systems), task-6 (systems-engineering-safety), task-7
  (manufacturing-quality), task-8 (flight-mechanics). None probes FTO;
  their FTO mentions are cross-family fence citations only (wave-49
  task-8 lines 120-141 confirm FTO measured leaves live: lateral-
  directional-stability-flight-test owns steady-heading-sideslip, control-
  force-flight-test owns force-per-g, flight-loads-survey owns maneuver
  point, takeoff/landing distance measured slots live).
- Prior NO_CANDIDATES stand only where FRESH evidence confirms. Fresh
  confirmation performed at this HEAD for every standing decline (battery
  below) plus the family-unchanged proof and a corpus-delta scan the
  wave-48 receipt could not have seen (wave-48 close added +20 tasks).

## Verdict

NO_CANDIDATES. Saturation reaffirmed FRESH at wave-49 HEAD. Zero GO
candidates; no GO evidence block produced. The family is byte-identical
to every probe point since the wave-45 close (last FTO-path commit in all
history is e33f3205), standards-map.yaml is unchanged (30 ids), and the
only corpus delta the wave-48 FTO receipt could not see is the wave-48
close +20 (97b98aca, 1306 to 1326), which carries ZERO FTO expected_skill
tags and ZERO candidate-seam tokens (full parse below). Every standing
wave-45/46/47/48 decline re-verified FRESH at this HEAD with unchanged
owner evidence. A deliberate whole-family keyword hunt (189 keyword
tokens over the wave-44..49 receipt sets, the full skills tree, and the
full corpus at 1326 tasks) surfaced seams no prior FTO receipt ever
adjudicated; all first-time rows decline on the standing blockers:
sibling ownership inside the family (spin chute inside spin-testing,
accelerated stall / stick shaker inside stall-characteristics-testing,
pull-up / pushover / strain gauge inside flight-loads-survey, g-onset
maneuver set inside buffet-boundary-testing, recovery parachute inside
spin-testing, yaw damper dutch-roll surface inside dynamic-stability-
flight-test), cross-family ownership (autoland / autopilot in avionics +
SES certification, brake energy in vehicle-design brake-energy-sizing,
fuel system in vehicle-design fuel sizing + FTO fuel-jettison-flight-test,
gear retraction in vehicle-design landing-gear-retraction-sizing, descent
machinery in FM descent-performance / FTO glide-flight-test), or
deterministic-light demo content with zero corpus demand on every token.

## Family census + unchanged proof (FRESH at HEAD 9c2b3fe4)

find skills/flight-test-operations -mindepth 3 -name SKILL.md = 49
leaves; family router rows `| flight-test-operations/...` = 49 (parity
OK). Packs: envelope 14, flutter 4, performance 17, planning 9,
stability 4, uas 1 (49 total; set-identical to wave-46/47/48 census
lists).
- Last commit touching skills/flight-test-operations/ in ALL history:
  e33f3205 (wave-45 close, landed vmcl-determination). Re-verified:
  `git log --oneline -- skills/flight-test-operations/` newest entry is
  e33f3205.
- git log 92d84a48..HEAD -- skills/flight-test-operations/ : empty.
- git diff 92d84a48..HEAD --stat -- skills/flight-test-operations/ :
  0 lines.
- git diff 92d84a48..HEAD -- standards-map.yaml : empty. standards-map
  id count = 30 (`grep -c '^  - id:'` = 30), unchanged.
- eval/hit1-corpus.yaml: 1326 task blocks at HEAD (grep '^  - id:' =
  1326). FTO expected_skill tags = 98 = 49 leaves x 2, exact, 0 leaves
  short or over, 0 orphan expected_skill paths pointing at nonexistent
  skills anywhere in the tree (whole-tree orphan check: empty).
- git diff 92d84a48..HEAD -- eval/hit1-corpus.yaml: 85 insertions, all
  from 97b98aca (wave-48 close).

## Corpus delta the wave-48 FTO probe could not check (FRESH scan)

Wave-48 FTO receipt probed at 92d84a48 with 1306 tasks. Wave-48 close
(97b98aca) added +20 (1306 to 1326). Full extraction of the 20 added
task blocks (id, query, intent, expected_skill) at this HEAD:
- w48-cyclic-executive-scheduling-1/-2 -> avionics/fsw/
  cyclic-executive-scheduling
- w48-dual-cycle-1/-2 -> propulsion/reciprocating/dual-cycle
- w48-feedback-linearization-1/-2 -> gnc-autonomy/control/
  feedback-linearization
- w48-fuel-system-weight-estimation-1/-2 -> vehicle-design/sizing/
  fuel-system-weight-estimation
- w48-h-infinity-synthesis-1/-2 -> gnc-autonomy/control/
  h-infinity-synthesis
- w48-honeycomb-core-micromechanics-1/-2 -> structures/composites/
  honeycomb-core-micromechanics
- w48-laminate-bending-stiffness-1/-2 -> structures/composites/
  laminate-bending-stiffness
- w48-landing-gear-weight-estimation-1/-2 -> vehicle-design/sizing/
  landing-gear-weight-estimation
- w48-mmod-shielding-sizing-1/-2 -> space-systems/subsystems/
  mmod-shielding-sizing
- w48-sliding-mode-control-1/-2 -> gnc-autonomy/control/
  sliding-mode-control
All 20 parse and route to ten wave-48 leaves in avionics, propulsion,
gnc-autonomy, vehicle-design, structures, space-systems. Zero carry an
FTO expected_skill. Token scan of the added query+intent text against
the FTO seam vocabulary (flight-test, telemetry, flutter, stall, spin,
envelope, calibration, instrumentation, takeoff, landing, climb, v-speed,
vmc, vmo, overspeed, excitation, vibration, gust, load factor, angle of
attack, icing, noise, sora, uas, coast-down, surge, recovery factor,
uncertainty, warning, sensor, accelerometer, strain, pilot-static):
only incidental substrings, all inside vehicle-design / gnc queries
(landing-gear weight task, sliding-mode matched-uncertainty phrasing).
The +20 creates NO new corpus demand for any FTO candidate seam. Corpus
growth therefore does not reopen any wave-48 anchor-ground decline.

## Fresh-seam keyword sweep (adjudication map, wave-44..49 receipts)

To hunt only seams never adjudicated, 189 keywords were swept
case-insensitively over every receipt in ops/automation/state/
wave43-recon/ .. wave49-recon/ plus the whole skills tree (SKILL.md only,
scripts excluded) and eval/hit1-corpus.yaml at HEAD (helper
/tmp/t9_sweep.py, /tmp/t9_seams.py). Keywords that APPEARED in prior
receipt sets (adjudicated or owned, hence not re-litigated, per wave-48
convention): hydroplaning / wet-runway, pio / cooper-harper / handling
qualities / bandwidth, deep stall, thrust reverser, autopilot / flight-
director, vortex-ring / settling-with-power / windshear / go-around /
balked / best glide / drag polar / ground effect, freeplay / rigging /
water ingestion / tire speed / catapult-carrier / ground resonance / noy
/ IRIG, recovery factor (aerodynamics context), measurement uncertainty /
kline, weighing / weight-and-balance / mass-properties, plus the wave-45
(wat-limit, climb-limit, time-to-climb, vs1g, vdf, mdf, vmca, gust-loads,
ice-shape, crosswind), wave-46 (standard-day, measured-distance, v-g
recorder, parameter-estimation, derivative-extraction, noy, pnlt, irig-b,
freeplay, rigging, feathering, ground-resonance, remote-id, laanc),
wave-47 (ice-contaminated, appendix-o, brake-energy, rejected-takeoff,
vle, vlo, gear-operating, cooling-test, max-operating-temperature,
thermocouple-climb, stall-warning, stall-margin, roll-performance,
aileron-authority, time-to-bank) and wave-48 (overspeed-warning,
coast-down, deceleration-method, alpha-vane, flow-angle, angle-of-attack-
calibration, control-surface-balance, flutter-excitation, compressor-
stall, engine-surge, surge-margin, emergency-descent, takeoff-warning,
takeoff-configuration-warning, flap-retraction, flap-asymmetry, super-
stall, stick-pusher, error-propagation, flowmeter, exceedance, slung-
load, external-load, water-depth, grooved, hot-day, cold-day,
recovery-factor FTO context, measurement-uncertainty FTO context)
decline rows.

## Genuinely-new seam probes (first-time adjudicated, FRESH evidence at HEAD 9c2b3fe4)

Gate legend (wave-46/47/48 convention): (a) zero-owner grep over the
whole skills tree + corpus, 0 hits; (b) sibling fence verbatim quote;
(c) standards-map id exists for the seam's standard (30 ids, no new ids
allowed); (d) published deterministic closed-form anchor, offline, no
empirical tables; (e) wordable corpus demand; (f) hyphenated-tag /
sibling-fence ownership of the seam. Every token below ran over the
whole skills/ tree (SKILL.md only) and eval/hit1-corpus.yaml (1326
tasks), case-insensitive, at HEAD 9c2b3fe4. No row cleared (a or b) AND
(d) AND (e): every genuinely-new token measured zero existing corpus
demand on all its tokens and has a live in-family or cross-family owner,
or deterministic-light content, so no router_eval.py Hit@1 simulation or
zero-theft audit was warranted.

| Candidate seam (never adjudicated in wave-44..49 receipts before this probe) | Gate(s) failed | Fresh evidence at HEAD 9c2b3fe4 |
|---|---|---|
| Spin recovery parachute / spin chute planning leaf | b, f, e | tree: spin-chute 0 / chute 2 files, but the owner is spin-testing: description verbatim "decide when the recovery parachute is required", body "the spin chute is the last-resort recovery device, required when there is no prior recovery demonstration for the configuration, when developed spin testing is planned, when the recovery check predicts an unrecoverable spin"; tags recovery-parachute, spin-resistance, pro-spin-controls. Spin chute / recovery parachute seam is INSIDE spin-testing, not a separate leaf. corpus spin-chute 0. |
| Accelerated stall / g-stall entry leaf | b, f, e | tree: accelerated-stall tokens in stall-characteristics-testing (description verbatim "compare the natural stall with the accelerated stall at the entry load factor", tag accelerated-stall) and the family router; g-break 0. stall-characteristics-testing owns the accelerated-stall entry reduction; corpus accelerated-stall 1 routed task sch2 -> stall-characteristics-testing (accelerated stall entry recovery altitude loss). Not zero-owner. |
| g-onset / wind-up-turn buffet-onset maneuver leaf | b, f, e | tree: g-onset tokens in high-angle-of-attack-testing, buffet-boundary-testing, stall-characteristics-testing, spin-testing (as entry-technique vocabulary); wind-up-turn 0. buffet-boundary-testing description verbatim "schedule pull-up and steady-turn test points across a Mach sweep at constant altitude, detect buffet onset from the vertical accelerometer RMS rise above the 0.02 g threshold"; flight-loads-survey owns "steady symmetric maneuvers (elevator pull-ups and pushovers) and rolling maneuvers build load factor". The g-onset maneuver family is distributed across the two owned envelope leaves; a standalone leaf collides on pull-up / steady-turn / load-factor tokens. corpus g-onset 0. |
| Pushover / symmetric maneuver loads reduction | b, f, e | tree: pushover token in flight-loads-survey (maneuver points, symmetric maneuvers); pull-up tokens in flight-loads-survey + buffet-boundary-testing + control-force-flight-test + vmu-determination. Wave-46/48 declined the maneuver-demo class; loads reduction owned by flight-loads-survey. Not new. |
| Yaw damper / stability augmentation dutch-roll test leaf | b, f, e | tree: yaw-damper 0, stability-augmentation 0 in skills; but dynamic-stability-flight-test owns the dutch-roll surface verbatim: "select the excitation technique for each mode (elevator doublet for the short period, elevator pulse for the phugoid, rudder pulse for the Dutch roll, aileron step for roll subsidence, rudder step for the spiral), reduce the decaying oscillation records to the log decrement, damping ratio...". A yaw-damper-on/off comparison reduces to the same dutch-roll log-decrement reduction; corpus yaw-damper 2 tasks both route to SES certification (equivalent-level-of-safety, mmel-development), not FTO. Wave-46/47 declined the SAS/autopilot demo class (avionics map-block). |
| Autoland / autopilot flight demonstration reduction | c, d, e, f | tree: autoland 0, autopilot-flight-test 0; autopilot tokens live in avionics do178c planning (cert scope) + SES functional-hazard-assessment / fmes-coverage / dal (system safety) + FM pilot-induced-oscillation + gnc gain-scheduling; wave-46 task-2 map-blocked autopilot/flight-director to the avionics displays surface; wave-48 autopilot row (avionics displays, map-blocked) stands. Autoland demo is pass/fail recording with no FAR-25 reduction identity, cross-family token collision on autopilot. corpus autoland 0. |
| Chase plane / photo chase / airborne escort ops leaf | d, e, f | tree: chase-plane 0, photo-chase 0, chase-aircraft 0, mission-control 0, ground-crew 0, test-director 0; corpus 0. Chase/escort is qualitative support-crew content; flight-test-safety owns safety pilot duties and emergency procedures; no reduction closed form, no standards anchor. Deterministic-light ops content inside the planning/safety vein (closed wave-46). |
| Test cards / flight card authoring leaf | b, d, e | tree: test-card 2 files (both FTO, but as workflow vocabulary: cruise-performance-flight-test "build the test card with plan_test_matrix", position-error-calibration test point scheduling); test-card 0 corpus. flight-test-planning owns the planning surface verbatim: "order the test points with the build-up approach... check that the instrumentation covers the required sensors, and confirm the test matrix covers every test objective... go/no-go gate verdict"; test-point-matrix-design owns matrix construction and repeat points. A test-card authoring leaf is doc-format content inside the owned planning workflow, deterministic-light. corpus 0. |
| Quick-look / real-time monitoring display reduction | b, e | tree: quick-look tokens only in propulsion rocket/combustion leaves (unrelated); real-time 3 files (space launch-window, gnc router, aeroelastic gust response - unrelated). telemetry-data-acquisition owns the ground chain verbatim: "budget the end-to-end data latency against the requirement, and verify the ground station link margin and telemetry quality against the bit error rate and dropout limits"; flight-test-data-reduction owns the data quality verdict. Real-time display is the same measurement chain surface; no independent reduction identity. corpus quick-look 0. |
| Fuel system flight test (fuel transfer / imbalance / crossfeed) | d, e, f | tree: fuel-transfer 0, fuel-imbalance 0, crossfeed 0, fuel-flow-meter 0 in skills; corpus 0. FTO fuel-jettison-flight-test owns the measured fuel-dump reduction (dump rate from telemetered fuel-weight slope, 900 s landing-weight limit); vehicle-design fuel-feed-system-sizing + fuel-tank-sizing own the design side; engine-flight-test owns fuel flow measurement ("fuel flow" tokens). In-flight fuel transfer/imbalance demo is pass/fail recording with no reduction closed form; cross-family collision on fuel tokens. |
| Brake / anti-skid / autobrake flight demo reduction | d, e, f | tree: anti-skid 0, autobrake 0, brake-temperature 1 (vehicle-design brake-energy-sizing), wheel-brake 1 (brake-energy-sizing); corpus anti-skid 0, brake-energy 5 routed to vehicle-design brake-energy-sizing. accelerate-stop-distance owns the braking ground roll reduction (s_stop = v1^2/(2 a_brake)); landing-distance-determination owns the landing braking ground roll (a_brake = mu g). Anti-skid system demo is qualitative pass/fail; wave-47 declined the brake-energy/rejected-takeoff demo class; energy identity owned by vehicle-design. |
| Landing gear retraction / gear-cycle flight demo | d, e, f | tree: gear-cycle 0, gear-retraction tokens in vehicle-design landing-gear-retraction-sizing + landing-gear-layout (design side); corpus gear 0 FTO. wave-47 declined gear-operating demo (deterministic-light, no reduction closed form); the gear kinematic identity is owned by vehicle-design sizing; wave-48 VLE/VLO row stands. |
| Air-data boom / nose-boom calibration | b, e | tree: air-data-boom 0, nose-boom 0; position-error-calibration owns the air-data calibration family verbatim: "schedule the tower fly-by, trailing cone, and GPS ground speed doublet test points across the speed range, compute the calibrated airspeed from the indicated airspeed and the position error correction". A boom-mounted reference is an instrumentation variant inside that owned method set; high-angle-of-attack-testing owns the AoA vane calibration sibling ("calibrate the angle of attack sensor position error against a tower fly-by or trailing cone reference"). corpus 0. |
| Accelerometer / transducer calibration leaf | b, e | tree: accelerometer 10 files (FTO buffet, flight-vibration-survey, ground-vibration-testing + others), transducer 6 files (ground-vibration-testing, control-force-flight-test + others); flight-test-instrumentation owns sensor selection and "pre-test calibration... chain" verbatim; ground-vibration-testing owns accelerometer calibration for modal work. Calibration of the measurement chain is inside flight-test-instrumentation's fence (wave-46 closed the planning/measurement infrastructure vein). corpus accelerometer 13 routed, transducer 4 routed, none unserved. |
| Cold-soak / hot-day engine start demo | d, e, f | tree: cold-soak 0, cold-day 1 (cross-cutting density-altitude), hot-day 2 (cross-cutting density-altitude, propulsion turbofan-off-design); corpus cold-soak 0. Wave-48 flagged hot-day/cold-day as probed; engine-flight-test owns the FTO powerplant seam (fuel flow, EGT margin, ISA correction); wave-46/47 declined in-flight cooling and max-operating-temperature demos as pass/fail thermocouple checks. Same class. |
| Power assurance / magneto run-up check leaf | d, e, f | tree: power-assurance 0, magneto tokens 13 files but all unrelated (gnc complementary filter, propulsion electric thruster contexts); corpus 0. Ground run-up power check is a pass/fail engine health demo; engine-flight-test owns the powerplant flight surface; no reduction closed form. |
| Descent performance flight test leaf (powered descent measured slot) | d, e | tree: descent-flight-test 0, descent tokens in FTO only via glide-flight-test (idle-thrust L/D, descent angle atan(1/(L/D))) and climb leaf cross-refs; corpus descent tasks (de1/de2, gl1) all route to FM descent-performance / glide-performance analysis leaves; avionics vertical-navigation owns top-of-descent (vn1/vn2). A measured powered-descent FTO leaf composes owned machinery (glide reduction + climb correction) inside the closed descent/glide energy vein (wave-48 emergency-descent row: "FM descent-performance and glide-performance own the analytic surfaces"); zero corpus demand on every token. |
| Aircraft systems flight testing (generic FAR 25.1301 demo surface) | d, e, f | tree: aircraft-systems tokens only in gnc estimation/guidance files (unrelated phrase usage), systems-flight-test 0, airframe-systems 0; corpus 0. Systems function/installation demos are qualitative pass/fail; SES arp4754a/arp4761a + certification leaves own the system safety surface; vehicle-design owns system sizing; FTO has no systems demo leaf and wave-46/47/48 declined every system-demo variant (gear, cooling, warnings) on deterministic-light grounds. Same class. |
| Range-safety / flight test abort criteria leaf | b, d, e | tree: range-safety 0, abort-criteria 0, test-hazard 0; flight-test-safety owns the safety package verbatim: "score the hazards on the severity by likelihood risk matrix, check that every test point stays inside the flight envelope limits, confirm the emergency procedures cover the required conditions... run the go/no-go criteria gate"; flight-test-planning owns the go/no-go gate verdict. Abort criteria are part of the owned go/no-go gate; deterministic-light planning content. corpus 0. |

## Re-verification of standing wave-45/46/47/48 declines (FRESH greps at HEAD 9c2b3fe4)

Family byte-identical since e33f3205, so fences re-read verbatim-
identical; every standing decline re-grepped FRESH over the whole skills
tree (SKILL.md only) and eval/hit1-corpus.yaml (1326 tasks) at HEAD
(helper /tmp/t9_battery.py). Token -> skills files / corpus hits, owners
unchanged from the receipt-named owners:
- wave-45 rows: wat-limit 0/0; climb-limit 0/0; time-to-climb 2 files
  (FM climb-performance, FTO climb-performance-flight-test) / 0; vs1g 4
  files (stall-speed-determination, stall-characteristics-testing among
  owners) / 2 routed; vdf 0/0; mdf 0/0; vmca 0/0; gust-loads 2 files
  (structures gust-maneuver-loads, aerodynamics aeroelastic-gust-
  response) / 0; ice-shape 1 file (icing-flight-test) / 0; crosswind 4
  files (FM wind-effects etc) / 4 routed. STANDS.
- wave-46 rows: standard-day 5 correction-owner files / 0 corpus;
  measured-distance 1 file (balanced-field-length) / 0; v-g 8 files but
  all V-g method owners (flutter-speed-prediction, load-factor-envelope,
  gust-maneuver-loads) / 4 routed, no recorder leaf; parameter-estimation
  1 cross-cutting noise file / 0; derivative-extraction 0/0; noy 1 FTO
  file (noise-certification-test) / 0; pnlt 2 files (noise-certification-
  test owner) / 2 routed; irig-b 1 file (telemetry-data-acquisition) / 1
  routed; freeplay 2 files (limit-cycle-oscillation owner + router) / 2
  routed; rigging 1 file (FM rotorcraft-cyclic-pitch-trim) / 0;
  feathering 0/0; ground-resonance 2 files (FM lead-lag owners) / 1
  routed; remote-id 0/0; laanc 1 file (part107-sora) / 0. STANDS.
- wave-47 rows: ice-contaminated 0/0; appendix-o 0/0; brake-energy 3
  files (vehicle-design brake-energy-sizing owner + structures landing-
  ground-loads) / 0; rejected-takeoff 4 files (brake-energy-sizing,
  accelerate-stop-distance among owners) / 0; vle 0/0; vlo tokens in
  part107-sora UAS visual-line-of-sight + vmu + router only / 2 routed
  (UAS context); gear-operating 0/0; cooling-test 0/0;
  max-operating-temperature 0/0; thermocouple-climb 0/0; stall-warning
  1 file (high-angle-of-attack-testing owner) / 0; stall-margin 2 files
  (high-angle-of-attack-testing, stall-speed-determination) / 1 routed;
  roll-performance 1 file (FM mil-std-1797a) / 0; aileron-authority 0/0;
  time-to-bank 0/0. STANDS.
- wave-48 rows: overspeed-warning 0/0; coast-down 0/0;
  deceleration-method 0/0; flow-angle 0/0; alpha-vane 0/0; angle-of-
  attack-calibration 0/0 but high-angle-of-attack-testing owns the AoA
  calibration slot verbatim; control-surface-balance 0/0;
  flutter-excitation 0/0 (excitation owners ground-vibration-testing +
  structural-coupling-test); compressor-stall 0/0 (surge tokens in
  propulsion compressor-map only); engine-surge 0/0; surge-margin 1 file
  (propulsion compressor-map) / 0; emergency-descent 1 file (FM descent-
  performance) / 0; takeoff-configuration-warning 0/0; kline 0/0;
  error-propagation 0/0; recovery-factor 1 file (aerodynamics
  flat-plate-skin-friction-heating) / 1 routed; flowmeter 0/0;
  exceedance 9 files (structures load-spectrum-counting etc, no FTO
  warning-exceedance owner) / 4 routed non-FTO; slung-load 0/0;
  external-load 0/0; water-depth 0/0; grooved 0/0; hot-day 2 non-FTO
  files / 0; cold-day 1 non-FTO file / 0. STANDS.
- Reopen triggers (wave-46/47/48 recheck reminders) checked FRESH, none
  fired: measured-distance standard-day correction still zero corpus
  demand and no ac-25-7d id anywhere (tree grep 0; map still 30 ids, no
  far-121 / ac-120-42b / ads-33 / part-133 / ac-25-7d ids); stability-
  derivative extraction still 0/0; VMC family (25.149) four-leg complete
  since wave-45, NOT re-probed per the wave-45 closure instruction;
  field-length, climb, stall, energy, buffet, flutter, stability,
  rotorcraft, planning, UAS veins all unchanged.

## Sibling fence quotes (re-read at HEAD 9c2b3fe4, verbatim)

- spin-testing (owns spin chute + recovery parachute): "decide when the
  recovery parachute is required, and judge the FAR 25.201 spin
  resistance verdict with pro-spin controls held at the stall";
  "Recovery parachute requirements: the spin chute is the last-resort
  recovery device, required when there is no prior recovery demonstration
  for the configuration, when developed spin testing is planned, when the
  recovery check predicts an unrecoverable spin".
- stall-characteristics-testing (owns accelerated stall + warning
  onset): "pick the entry technique (gradual deceleration at one knot
  per second, power-on, turning, accelerated), compare the natural stall
  with the accelerated stall at the entry load factor, verify the stall
  warning onset (buffet or stick shaker) against the required margin".
- buffet-boundary-testing (owns g-onset maneuver set): "schedule pull-up
  and steady-turn test points across a Mach sweep at constant altitude,
  detect buffet onset from the vertical accelerometer RMS rise above the
  0.02 g threshold".
- flight-loads-survey (owns maneuver loads): "calibrate strain gauge
  load stations against applied ground loads... reduce the load factor
  versus speed survey points (symmetric and rolling maneuvers)";
  "steady symmetric maneuvers (elevator pull-ups and pushovers) and
  rolling maneuvers build load factor at discrete points".
- dynamic-stability-flight-test (owns dutch-roll / SAS-mode surface):
  "select the excitation technique for each mode (elevator doublet for
  the short period, elevator pulse for the phugoid, rudder pulse for the
  Dutch roll, aileron step for roll subsidence, rudder step for the
  spiral), reduce the decaying oscillation records to the log decrement,
  damping ratio, damped and undamped frequencies".
- telemetry-data-acquisition (owns ground chain): "budget the end-to-end
  data latency against the requirement, and verify the ground station
  link margin and telemetry quality against the bit error rate and
  dropout limits".
- flight-test-safety (owns risk + abort surface): "score the hazards on
  the severity by likelihood risk matrix, check that every test point
  stays inside the flight envelope limits, confirm the emergency
  procedures cover the required conditions, verify the safety pilot
  duties are assigned, run the go/no-go criteria gate".
- flight-test-planning (owns build-up + test cards + go/no-go): "order
  the test points with the build-up approach so risk increases step by
  step... confirm the test matrix covers every test objective... and the
  go/no-go gate verdict that releases or blocks the flight".
- position-error-calibration (owns air-data calibration family):
  "schedule the tower fly-by, trailing cone, and GPS ground speed
  doublet test points across the speed range, compute the calibrated
  airspeed from the indicated airspeed and the position error
  correction"; high-angle-of-attack-testing (owns AoA calibration):
  "calibrate the angle of attack sensor position error against a tower
  fly-by or trailing cone reference".
- engine-flight-test, fuel-jettison-flight-test, accelerate-stop-
  distance, landing-distance-determination, ground-vibration-testing,
  structural-coupling-test: quoted in seam-table rows above (fuel flow /
  dump-rate reduction / s_stop = v1^2/(2 a_brake) / a_brake = mu g /
  excitation methods / swept-sine-chirp-impulse).

## Standards-map check (at HEAD)

standards-map.yaml holds exactly 30 `- id:` entries (unchanged). FTO-
relevant ids present: far-25 (44 FTO files incl router), cs-25 (39),
far-29 (6 rotorcraft leaves incl flight-vibration-survey), far-107 (1).
Counts identical to wave-46/47/48. Absence grep for every id a
genuinely-new seam would need returns 0 for all: far-121, ac-120-42b,
ac-25-7d, ads-33, part-133, astm, sae, iso-15530. No new ids since
wave-47; no id any declined seam needs has appeared. far-25/cs-25 exist
as reference-only ids for the demo-class rows, but a map id alone does
not clear gate (d) when the seam has no reduction closed form.

## Closed veins (owner leaf per vein, reaffirmed FRESH)

- VMC family (25.149) four legs + 25.107 rotation boundary:
  vmc-determination, vmcg-determination, vmcl-determination (incl
  VMCL-2), vmu-determination. CLOSED per wave-45 instruction; not
  re-probed.
- Climb 25.115/119/121, stall 25.103/207 (incl accelerated stall entry,
  warning onset, recovery), field length 25.109/113/125 (measured-
  distance standard-day correction inside), energy (Ps/zoom), envelope
  expansion + speed set, buffet and loads (incl pull-up/steady-turn
  g-onset maneuver set, strain gauge calibration, pushovers), flutter
  and vibration (incl GVT excitation methods, SCT swept-sine/chirp/
  impulse excitation, LCO freeplay/damping), stability measurement
  (static/dynamic incl dutch-roll log decrement / lateral-directional /
  control-force), rotorcraft performance (6 leaves, far-29), planning /
  measurement infrastructure (instrumentation, DAQ/PCM/IRIG, telemetry
  ground chain, data reduction with RSS uncertainty, PEC incl tower fly-
  by/trailing cone/GPS doublet, noise, test matrix, safety incl risk
  matrix + go/no-go), UAS part107-sora. All CLOSED at wave-45/46/47/48,
  all unchanged at this HEAD.
- Spin chute / recovery parachute decision: INSIDE spin-testing.
  Accelerated stall entry: INSIDE stall-characteristics-testing.
  g-onset maneuver vocabulary: INSIDE buffet-boundary-testing /
  stall-characteristics-testing / high-angle-of-attack-testing.
  Yaw-damper dutch-roll surface: INSIDE dynamic-stability-flight-test.
  AoA vane calibration: INSIDE high-angle-of-attack-testing. All
  reaffirmed by fresh desc reads above.

## Method notes

Probe steps executed: (1) git HEAD/date/status capture (9c2b3fe4, only
wave49-recon untracked); (2) find enumeration = 49 leaves, pack counts,
router parity 49, FTO expected_skill parity 98 of 1326, 0 orphans
whole-tree; (3) content-delta proof: last-ever FTO commit e33f3205;
path-restricted log and tree diff vs the wave-48 probe point 92d84a48
both empty for skills/flight-test-operations/ and standards-map.yaml;
extraction of the wave-48-close +20 corpus lines (97b98aca) with id /
query / intent / expected_skill parse and FTO token scan (all zero);
(4) keyword sweep of ALL wave-43..49 receipts + skills tree + corpus
(189 keywords, helpers /tmp/t9_sweep.py and /tmp/t9_seams.py): see
adjudication map above; (5) standards-map id count (30) and targeted
absence grep; (6) zero-owner grep battery over the whole skills tree for
every genuinely-new token and the same tokens over eval/hit1-corpus.yaml
at 1326 tasks (helper /tmp/t9_battery.py); (7) standing-decline re-
verification battery over all wave-45/46/47/48 FTO decline tokens plus
the reopen-trigger greps (ac-25-7d 0, map absence list, derivative
extraction, standard-day demand, measured-distance); (8) sibling fence
re-reads with verbatim quotes from spin-testing, stall-characteristics-
testing, buffet-boundary-testing, flight-loads-survey, dynamic-stability-
flight-test, telemetry-data-acquisition, flight-test-safety, flight-test-
planning, position-error-calibration, high-angle-of-attack-testing,
engine-flight-test, fuel-jettison-flight-test, accelerate-stop-distance,
landing-distance-determination, plus cross-family owners (vehicle-design
brake-energy-sizing / fuel-feed-system-sizing / landing-gear-retraction-
sizing, FM descent-performance / glide-performance / mil-std-1797a,
avionics, SES certification); (9) git status clean before and after
(only the untracked wave49-recon directory). No candidate cleared gates
(a/b) + (d) + (e): every genuinely-new token measured zero existing
corpus demand and has a live in-family or cross-family owner or
deterministic-light content, so no router_eval.py Hit@1 simulation or
zero-theft audit run was warranted this probe. No files modified outside
this receipt.

Recheck reminders for future waves: FTO state change would require a
commit touching skills/flight-test-operations/ (none since wave-45 close
e33f3205). The only methodically real near-misses remain the ones
already on file: the measured-distance standard-day correction (reopen
only with the field-length vein reopened by a brief, an AC 25-7D style
anchor, or natural-language corpus demand) and the AoA-calibration /
uncertainty functions (owned; reopen only if the high-angle-of-attack-
testing or flight-test-data-reduction fences change). First-time rows
above add no reopen candidates: each is either owned (spin chute,
accelerated stall, g-onset, pushover, yaw damper, test cards, quick-look,
air-data boom, accelerometer calibration) or deterministic-light demo
content (autoland, chase plane, fuel transfer, anti-skid, gear cycle,
cold-soak, power assurance, descent measured slot, systems demo, abort
criteria) with zero corpus demand on every token.

## Read-only verification note

Only this file was written: ops/automation/state/wave49-recon/
task-9-receipt.md. git status --porcelain before and after shows only the
pre-existing untracked wave49-recon state directory (sibling receipts);
no git add/commit/push, no edits to skills/, eval/, docs/, Makefile,
scripts/, ops/automation briefs, or standards-map.yaml. No em dashes in
this receipt. No machine-local absolute paths cited (repo-relative paths
and the home-relative repo name only; helper scripts under /tmp/
t9_*.py). Probe was fresh at HEAD 9c2b3fe4.
