# WAVE-48 RECON RECEIPT: flight-test-operations (task 8, whole-family FRESH, pool-drop EXTENSION)

Probe date: 2026-09-09. Probe agent: read-only recon subagent (wave-48 pool-drop
extension probe, task 8 of 8).
Repo HEAD: 92d84a48 ("ops: stage wave-48 brief (planning only - daylight
dispatch 10:00 CEST)"). Working tree clean at probe start and end; the only
untracked path in git status is the pre-existing ops/automation/state/
wave48-recon/ receipt directory (this file included).
Extension-trigger context: wave-48 primary pool (tasks 0-5) plus extensions
task-6 SES NO_CANDIDATES and task-7 MQ NO_CANDIDATES leaves the viable pool at
9, below the ~12 line; brief doctrine then probes smallest-first among the
standing-NO_CANDIDATES saturated families (SES 47, MQ 48, FTO 49): flight-test-
operations is this probe (task 8), per the brief extension ladder.
Scope: whole flight-test-operations family probed FRESH at current HEAD: leaf
inventory, unchanged-proof vs the wave-47 probe point, standards-map id check,
zero-owner greps over the whole skills/ tree, corpus demand battery over
eval/hit1-corpus.yaml (1306 tasks), sibling fence re-reads with verbatim
quotes, and a keyword sweep of the wave-44/45/46/47 receipt, spec, and
leaf-plan sets to isolate seams NO prior receipt ever adjudicated.
Prior FTO receipts: wave-45 task-5 (48 leaves, 1 GO vmcl-determination, 10
declines), wave-46 task-4 NO_CANDIDATES (HEAD d4b4d590), wave-47 task-9
NO_CANDIDATES (whole-family FRESH, probe HEAD a4ae6d1e, expected 0 found 0).
Wave-48 extends because the pool dropped below ~12, NOT because family state
changed (unchanged proof below).
Mode: read-only except this receipt. No git writes, no edits to skills/, eval/,
standards-map.yaml, scripts/, docs/, or ops briefs.

## Verdict

NO_CANDIDATES. Saturation reaffirmed FRESH at wave-48 HEAD. Zero GO candidates;
no GO evidence block produced. The family is byte-identical to every probe
point since the wave-45 close (e33f3205), so all standing wave-45/46/47
declines stand on their original evidence, each re-verified FRESH below. A
deliberate hunt for GENUINELY NEW seams (keywords returning zero hits across
every wave-44..47 receipt, spec, and leaf plan) produced 10 first-time-
adjudicated probe rows; all decline on the same standing blockers (sibling
ownership in-family or cross-family, deterministic-light demo content with no
reduction closed form, zero wordable corpus demand, closed-vein adjacency).
The one corpus delta no prior FTO receipt could have seen (wave-47 close
d9ddab35, +20 tasks, 1286 to 1306) carries zero FTO expected_skill tags and
zero candidate-seam tokens.

## Family census + unchanged proof

find skills/flight-test-operations -mindepth 3 -name SKILL.md = 49 leaves;
family router rows `| flight-test-operations/...` = 49 (parity OK). Packs:
envelope 14, flutter 4, performance 17, planning 9, stability 4, uas 1 (49
total, set-identical to the wave-46/47 census lists).
- Last commit touching skills/flight-test-operations/ in ALL history: e33f3205
  (wave-45 close, landed vmcl-determination).
- git log --oneline a4ae6d1e..HEAD -- skills/flight-test-operations/ : empty.
- git diff a4ae6d1e..HEAD -- skills/flight-test-operations/ : 0 lines.
- git diff a4ae6d1e..HEAD -- standards-map.yaml : empty (30 ids, identical).
- eval/hit1-corpus.yaml: 1306 tasks at HEAD; FTO expected_skill tags = 98
  (49 leaves x 2, exact), 0 orphans.
- Corpus delta the wave-47 receipt COULD NOT have checked: wave-47 close
  commit d9ddab35 added +20 tasks (1286 to 1306) AFTER the wave-47 task-9 FTO
  probe. Fresh scan of the added lines: all +20 target wave-47 leaves (2 each:
  rotorcraft-cyclic-pitch-trim, virtual-deadline-scheduling, diesel-cycle,
  tropospheric-delay-correction, impact-angle-control-guidance, smith-
  predictor, h-infinity-control, component-weight-estimation,
  creep-stress-relaxation, unidirectional-lamina-micromechanics). Zero
  flight-test-operations tags and zero hits for every candidate seam token.

## Keyword sweep of wave-44..47 receipts (adjudication map for NEW-seam hunt)

To hunt only seams never adjudicated, every candidate keyword was swept
case-insensitively over ops/automation/state/wave44-recon/, wave45-recon/,
wave46-recon/, wave47-recon/ (all receipts) plus wave44..47 specs dirs and
leaf-plan files (helper /tmp/w48_t8_sweep.py, 106 target files, 98 keywords).
Keywords that APPEARED in the prior receipt set (adjudicated or owned, hence
NOT re-litigated, with location):
- hydroplaning / wet-runway: wave47-recon/task-0-receipt.md line 229 (FM
  probe): declined as "thin single semi-empirical NASA formula (V_p = 9
  sqrt(psi)), no corpus demand... FTO landing-distance-determination is the
  measured slot". The wet/contaminated-runway vein (water-depth, grooved,
  flooded) sits inside that adjudicated row; not re-opened.
- pio / pilot-induced / cooper-harper / handling qualities / bandwidth:
  wave46-recon/task-0 (lines 45-46, 270), wave47-recon/task-0 (lines 56,
  275-276). FM handling-qualities pack owns live leaves cooper-harper-rating,
  mil-std-1797a, pilot-induced-oscillation, pitch-bandwidth-criteria. Not new.
- deep stall / super stall: FM stability-control pack holds live leaf
  deep-stall-analysis (wave47-recon/task-0 pack listing). Not new.
- thrust reverser: wave46-recon/task-5 line 319 (propulsion), wave47-recon/
  task-4 line 313 (vehicle-design), both declined (effectiveness
  measured/empirical). Not new.
- autopilot / flight-director: wave46-recon/task-2 line 180 (avionics
  displays row, map-blocked) and gnc guidance specs. Not new.
- vortex-ring / settling-with-power / windshear / go-around / balked / best
  glide / drag polar / ground effect: FM receipts (wave45 task-1, wave46
  task-0, wave47 task-0). FM axial-descent, windshear-analysis, oei-climb-
  gradient, glide-performance own the analytic surfaces; FTO measured slots
  named (landing-distance-determination, cruise/glide test leaves, balked-
  landing reserve). Not new.
- freeplay / rigging / water ingestion / tire speed / catapult-carrier /
  ground resonance / noy / IRIG: wave46-recon/task-4 (the FTO whole-family
  receipt) decline rows and battery lists. Not new.
- recovery factor / total temperature: appear ONLY in aerodynamics contexts
  (wave46-recon/task-8 line 38; wave44/45 specs mangler-axisymmetric-transform,
  ackeret-linearized-supersonic, mixed-flow-exhaust): compressible boundary-
  layer recovery factor OWNED by flat-plate-skin-friction-heating. The FTO-side
  probe-tube recovery calibration seam never appears in any receipt: probed
  FRESH below (first-time row 9).
- measurement uncertainty / uncertainty: wave45 task-4 line 63, wave45 task-11
  line 25 (quality/space contexts). FTO flight-test-data-reduction owns its
  RSS uncertainty function with live corpus task fdr2: first-time FTO row 10.
- weighing / weight-and-balance / mass-properties: wave45 task-9 and wave46
  task-9 (vehicle-design probes) closed the mass-properties vein (cg-envelope,
  inertia-estimation, mass-budget, weight-estimation) at the corpus-demand
  level. Airplane weighing for flight test W/B is cross-family fenced.
Zero-hit keywords (genuinely never adjudicated in wave-44..47, probed FRESH):
overspeed-warning, vmo-warning, coast-down, deceleration-method, alpha-vane,
flow-angle, angle-of-attack-calibration, control-surface-balance, mass-balance
(FTO context), flutter-excitation, excitation-system, compressor-stall,
engine-surge, surge-margin, emergency-descent, takeoff-warning,
takeoff-configuration-warning, flap-retraction, flap-asymmetry, super-stall,
stick-pusher, kline, error-propagation, flowmeter, exceedance (FTO context),
slung-load, external-load, water-depth, grooved, hot-day, cold-day. First-time
probe rows below use this zero-hit set, plus rows 9 and 10 (context-qualified:
recovery-factor and measurement-uncertainty appear in prior receipts only in
other-family contexts).

## Genuinely-new seam probes (first-time adjudicated, FRESH evidence at HEAD)

Gate legend (wave-46/47 convention): (a) zero-owner grep, whole skills/ tree +
corpus, 0 hits; (b) sibling fence verbatim quote; (c) standards-map id exists
for the seam's standard (30 ids, no new ids allowed); (d) published
deterministic closed-form anchor, offline, no empirical tables; (e) wordable
corpus demand; (f) hyphenated-tag / sibling-fence ownership of the seam. Every
token below ran over the whole skills/ tree (SKILL.md only, pycache excluded)
and eval/hit1-corpus.yaml, case-insensitive, at HEAD 92d84a48. No row cleared
(a or b) AND (d) AND (e), so no router_eval.py Hit@1 simulation or zero-theft
audit was warranted: every row has zero existing corpus demand on all its
tokens and either a live owner (b/f) or deterministic-light content (d).

| Candidate seam (never adjudicated before this probe) | Gate(s) failed | Fresh evidence |
|---|---|---|
| VMO/MMO overspeed-warning demonstration reduction | d, e, f | tree 0 / corpus 0 for overspeed, overspeed-warning, vmo-warning, overspeed-limiter. vmo/mmo tokens live only in SES type-certificate-data-sheet (TCDS placards) and FTO load-factor-envelope (V-n); no warning-reduction owner. v-speeds fence owns the computed cert-speed set plus "the vno normal operating limit and the vne never exceed speed... vne guard verdict" only; wave-45 VDF/MDF dive demo decline (deterministic-light, no reduction closed form) covers this class. |
| Coast-down / deceleration-method drag determination | d, e, f | tree 0 / corpus 0 for coast-down, deceleration-method. level-acceleration-test fence owns the trace-to-acceleration energy reduction ("P_s = dh/dt + V a / g... Estimates the excess thrust") and consumes a provided drag polar; glide-flight-test owns idle-thrust sink/L-D with residual idle-thrust correction; engine-flight-test derives thrust "from the rate of climb or the level acceleration and the measured drag". A deceleration drag leaf composes owned machinery in reverse (mirror class, IRIG-decode precedent wave-46) inside the closed energy vein. |
| Installed angle-of-attack sensor calibration | a, e, vein | tree: flow-angle / alpha-vane / vane-calibration hits zero outside propulsion blade-row context and one FTO file. That file is the owner: high-angle-of-attack-testing lines 44-58 own the seam verbatim ("the indicated AoA carries a bias and a scale error... corrected = bias + scale * indicated, fitted by least squares over the calibration points", reference methods tower fly-by and trailing cone "from which the flow angle is derived"). Not zero-owner; slot inside an existing leaf. |
| Control-surface mass-balance ground demonstration (flutter protection) | d, e, vein | tree 0 / corpus 0 for control-surface-balance, and for mass-balance in any aero/FTO context (propulsion afterburner/hybrid hits are chemical, unrelated). ground-vibration-testing owns modal "mass normalization" and excitation methods; flutter-testing owns damping/margin/flutter speed. Wave-46 declined the sibling ground-check class (control checks / freeplay / rigging: "no published deterministic closed form"); balancing a surface to a hinge-CG condition is the same qualitative ground demo, no canonical closed form in-repo. Flutter vein closed wave-46. |
| Flight flutter excitation systems (rotary-vane / oscillatory exciters) | e, f, vein | tree: the single FTO excitation token owner is structural-coupling-test ("plan the frequency response testing... with swept sine, chirp, or impulse excitation... Produces... the excitation test point set", live tags swept-sine, chirp, impulse-excitation); ground-vibration-testing owns "excitation methods (shakers, impact hammers, sine sweep, random)". Excitation content is token-owned across GVT (ground) and SCT (flight, closed-loop); flutter-testing owns the clearance reduction. Hardware content is deterministic-light inside the closed flutter/vibration vein (wave-46). |
| In-flight compressor stall / engine surge testing | c, e, f | tree: surge tokens only in propulsion compressor-map (surge margin, operating-line clearance; live corpus tasks route there, hit1 lines 1336-1338) and the propulsion router; zero in FTO. engine-flight-test owns the FTO powerplant seam (installed thrust, fuel flow, EGT margin, ISA correction, transient timing); wave-46/47 declined propeller feathering and in-flight cooling as powerplant config/demo variants of that fence. In-flight surge is a qualitative risk demo, no reduction closed form, cross-family token collision. |
| Emergency-descent demonstration reduction | d, e, f | tree 0 / corpus 0 for emergency-descent as a flight-test seam; descent/glide machinery owned by FM descent-performance and glide-performance; the only corpus demand for the phrase (hit1 line 4617, ram air turbine swept area "at the emergency descent airspeed") routes to vehicle-design ram-air-turbine-sizing. FTO-side demo is pass/fail recording, no FAR-25 reduction identity, cross-family collision on descent tokens. |
| Takeoff-configuration warning system demonstration (25.703 class) | d, e, f | tree 0 / corpus 0 for takeoff-warning / takeoff-configuration-warning / configuration-warning (broad "takeoff configuration" phrase hits are vmc/stall config matches, no warning content). Warning activation checks are qualitative pass/fail demos; wave-47 declined the sibling stall-warning margin calibration as demo class with no reduction closed form (owned high-angle-of-attack-testing). No deterministic identity. |
| Total-temperature probe recovery-factor calibration | d, e, f, vein | "recovery factor" appears in prior receipts only in the aerodynamics boundary-layer context (wave-46 task-8, OWNED flat-plate-skin-friction-heating r = sqrt(Pr) / Pr^(1/3)); the flight-test probe-tube context is first-time here. flight-test-instrumentation owns the measurement chain ("verify the recording, telemetry, pre-test calibration, and measurement uncertainty chain before the test"); position-error-calibration owns the air-data calibration family. Probe recovery calibration is deterministic-light instrumentation content inside the closed planning/measurement-infrastructure vein (wave-46). |
| Flight-test measurement-uncertainty leaf (Kline-McClintock style) | b, e, f | kline / error-propagation zero tree-wide, but the seam is OWNED in-family: flight-test-data-reduction desc verbatim "combine the measurement uncertainty sources with the root sum square into the combined uncertainty... and the data quality verdict that flags out-of-range values, NaN samples, and time gaps", with live corpus task fdr2 (hit1 line 1574) routing exactly that query to it; flight-test-instrumentation carries the measurement-uncertainty trigger. A standalone uncertainty leaf steals fdr2 traffic. |

## Re-verification of standing wave-46/47 declines (FRESH greps at HEAD)

Family byte-identical since e33f3205, so fences re-read verbatim-identical;
every standing decline re-grepped FRESH over the whole skills/ tree (SKILL.md
only) and eval/hit1-corpus.yaml at HEAD (helper /tmp/w48_t8_battery1.py).
Token -> skills files / corpus hits, owners unchanged from the receipt-named
owners:
- wave-45 rows: wat-limit 0/0; climb-limit 0/0; time-to-climb 2 files (FM
  climb-performance, FTO climb-performance-flight-test) / 0; vs1g 22 files
  (stall-speed-determination, stall-characteristics-testing among owners) / 2
  routed; vdf 0/0, mdf 0/0; vmca 0/0; gust-loads owners aerodynamics
  aeroelastic-gust-response + structures gust-maneuver-loads / 0; ice-shape 1
  file (icing-flight-test) / 0; crosswind owners FM wind-effects etc / 4
  routed. STANDS.
- wave-46 rows: standard-day 27 correction-owner files / 0 corpus (measured
  standard-day seam still demand-free); measured-distance 1 file (balanced-
  field-length) / 0; v-g 15 files but all V-g method owners (flutter-speed-
  prediction, load-factor-envelope), no recorder leaf; parameter-estimation 1
  cross-cutting noise file / 0, derivative-extraction 0/0; noy 1 FTO file
  (noise-certification-test) / 0; pnlt 8 files (noise-certification-test
  owners) / 2 routed; irig-b 6 files (telemetry-data-acquisition + pcm-
  telemetry-decommutation) / 1 routed; freeplay 8 files (limit-cycle-
  oscillation owner) / 2 routed; rigging 1 file (FM rotorcraft-cyclic-pitch-
  trim, wave-47 leaf) / 0; feathering 0/0; ground-resonance 7 files (FM
  lead-lag owners) / 1 routed; remote-id 0/0; laanc 7 files (part107-sora) /
  0. STANDS.
- wave-47 rows: ice-contaminated 0/0; appendix-o 0/0; brake-energy 9 files
  (vehicle-design brake-energy-sizing owner) / 5 routed; rejected-takeoff 9
  files (same owner) / 0; vle 0/0; vlo files are part107-sora UAS
  visual-line-of-sight tokens only / 2 routed (UAS context); gear-operating
  0/0; cooling-test / max-operating-temperature / thermocouple-climb 0/0
  (thermocouple 1 file, MQ layup-cure, unrelated); stall-warning 1 file
  (high-angle-of-attack-testing owner) / 0; stall-margin 2 files
  (high-angle-of-attack-testing, stall-speed-determination) / 1 routed;
  roll-performance 1 file (FM mil-std-1797a); aileron-authority 0/0;
  time-to-bank 0/0. STANDS.
- Reopen triggers (wave-46/47 recheck reminders) checked FRESH, none fired:
  measured-distance standard-day correction still zero corpus demand and no
  ac-25-7d id anywhere (tree grep 0 files; map still 30 ids, no far-121 /
  ac-120-42b / ads-33 / part-133 ids either); stability-derivative extraction
  still 0/0 (single parameter-estimation noise hit unchanged); VMC family
  (25.149) four-leg complete since wave-45, NOT re-probed per the wave-45
  closure instruction; field-length, climb, stall, energy, buffet, flutter,
  stability, rotorcraft, planning, UAS veins all unchanged.

## Sibling fence quotes (re-read at HEAD 92d84a48, verbatim)

- high-angle-of-attack-testing (owns AoA calibration + stall-warning margin):
  "the indicated AoA carries a bias and a scale error. The correction relates
  indicated AoA to a reference AoA measured by an independent method...
  Calibration model: corrected = bias + scale * indicated, fitted by least
  squares over the calibration points" and "Stall warning margin (FAR 25.201 /
  CS-25.201 context, paraphrased)".
- flight-test-data-reduction (owns uncertainty + data quality): "combine the
  measurement uncertainty sources with the root sum square into the combined
  uncertainty. Produces the corrected and filtered channel time series, the
  corrected airspeed, the combined uncertainty, and the data quality verdict
  that flags out-of-range values, NaN samples, and time gaps".
- flight-test-instrumentation (owns measurement chain): "verify the recording,
  telemetry, pre-test calibration, and measurement uncertainty chain before
  the test".
- level-acceleration-test (owns acceleration-direction energy reduction):
  "compute the acceleration from the smoothed trace with central differences,
  and evaluate the specific excess power by the total energy method, P_s =
  dh/dt + V a / g... when the drag polar is provided, the thrust available and
  the thrust required".
- glide-flight-test (owns idle-thrust L/D): "derive the sink rate from the
  altitude loss and the segment time, compute the lift to drag ratio from the
  true airspeed and the sink rate, correct the results for... the residual
  idle thrust, and locate the best glide speed".
- engine-flight-test, v-speeds, ground-vibration-testing, structural-coupling-
  test: verbatim quotes already given in seam-table rows 1, 5, and 6 above
  (installed-thrust fence; v-speeds cert-speed set with vne guard verdict
  only; GVT "excitation methods (shakers, impact hammers, sine sweep, random)";
  SCT swept-sine/chirp/impulse excitation plan).

## Standards-map check (at HEAD)

standards-map.yaml holds exactly 30 `- id:` entries (unchanged). FTO-relevant
ids present: far-25 (44 FTO files incl router), cs-25 (39), far-29 (6
rotorcraft leaves incl router), far-107 (1); counts identical to wave-46/47.
Absence grep for every id a genuinely-new seam would need returns 0 for all:
far-121, ac-120-42b, ac-25-7d, ads-33, part-133, astm, sae, iso-15530. No new
ids since wave-47; no id any declined seam needs has appeared. far-25/cs-25
exist as reference-only ids for the demo-class rows, but a map id alone does
not clear gate (d) when the seam has no reduction closed form.

## Closed veins (owner leaf per vein, reaffirmed FRESH)

- VMC family (25.149) four legs + 25.107 rotation boundary: vmc-determination,
  vmcg-determination, vmcl-determination (incl VMCL-2), vmu-determination.
  CLOSED per wave-45 instruction; not re-probed.
- Climb 25.115/119/121, stall 25.103/207, field length 25.109/113/125
  (measured-distance standard-day correction inside), energy (Ps/zoom),
  envelope expansion + speed set, buffet and loads, flutter and vibration
  (incl GVT excitation methods, SCT swept-sine/chirp/impulse excitation, LCO
  freeplay/damping), stability measurement (static/dynamic/lateral-
  directional/control-force), rotorcraft performance (6 leaves, far-29),
  planning/measurement infrastructure (instrumentation, DAQ/PCM/IRIG, data
  reduction with RSS uncertainty, PEC, noise, matrix, safety), UAS
  part107-sora. All CLOSED at wave-45/46, all unchanged.
- AoA sensor calibration + stall-warning margin: INSIDE high-angle-of-attack-
  testing (not a separate seam). Data-quality/measurement uncertainty: INSIDE
  flight-test-data-reduction (corpus task fdr2). Both reaffirmed by fresh
  desc reads.

## Method notes

Probe steps executed: (1) git HEAD/date/status capture (92d84a48, only
wave48-recon untracked); (2) find enumeration = 49 leaves, pack counts, router
parity 49, FTO expected_skill parity 98 of 1306, 0 orphans; (3) content-delta
proof: last-ever FTO commit e33f3205; path-restricted log and tree diff vs
the wave-47 probe point a4ae6d1e both empty for skills/flight-test-
operations/ and standards-map.yaml; scan of the wave-47-close +20 corpus lines
(d9ddab35) for FTO tags and seam tokens (all zero); (4) keyword sweep of ALL wave-44..47 receipts, specs dirs, and leaf plans
(106 files, 98 keywords, helper /tmp/w48_t8_sweep.py): see adjudication map
above; (5) standards-map id count (30) and targeted absence grep; (6) zero-owner grep
battery over the whole skills/ tree for every genuinely-new token (helper
/tmp/w48_t8_battery2.py, SKILL.md only, pycache excluded) and the same tokens
over eval/hit1-corpus.yaml; (7) standing-decline re-verification battery over
all wave-45/46/47 FTO decline tokens (helper /tmp/w48_t8_battery1.py) plus the
wave-46/47 reopen-trigger greps (ac-25-7d 0, map absence list, derivative
extraction, standard-day demand); (8) sibling fence re-reads with verbatim
quotes from high-angle-of-attack-testing, flight-test-data-reduction,
flight-test-instrumentation, level-acceleration-test, glide-flight-test,
engine-flight-test, v-speeds, ground-vibration-testing, structural-coupling-
test, plus cross-family owners (propulsion compressor-map, vehicle-design
ram-air-turbine-sizing, FM descent/glide, mil-std-1797a, deep-stall-analysis);
(9) git status clean before and
after (only the untracked wave48-recon directory). No candidate cleared gates
(a/b) + (d) + (e): every genuinely-new token measured zero existing corpus
demand and has a live in-family or cross-family owner or deterministic-light
content, so no router_eval.py Hit@1 simulation or zero-theft audit run was
warranted this probe. No files modified outside this receipt.

Recheck reminders for future waves: FTO state change would require a commit
touching skills/flight-test-operations/ (none since wave-45 close e33f3205).
The only methodically real near-misses remain the ones already on file: the
measured-distance standard-day correction (reopen only with the field-length
vein reopened by a brief, an AC 25-7D style anchor, or natural-language corpus
demand) and the AoA-calibration / uncertainty functions (owned; reopen only if
the high-angle-of-attack-testing or flight-test-data-reduction fences change).
First-time rows above add no reopen candidates: each is either owned (AoA
calibration, uncertainty, excitation) or deterministic-light demo content
(overspeed warning, takeoff-configuration warning, emergency descent, mass
balance, surge, coast-down, recovery-factor calibration) with zero corpus
demand on every token.

## Read-only verification note

Only this file was written: ops/automation/state/wave48-recon/task-8-receipt.md.
git status --porcelain before and after shows only the pre-existing untracked
wave48-recon state directory (sibling receipts); no git add/commit/push, no
edits to skills/, eval/, docs/, Makefile, scripts/, ops/automation briefs, or
standards-map.yaml. No em dashes in this receipt. No machine-local absolute
paths cited (repo-relative paths and ~/AeroSkills only; helper scripts under
/tmp/w48_t8_*.py). Probe was fresh at HEAD 92d84a48.
