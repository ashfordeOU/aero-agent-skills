# WAVE-47 VEHICLE-DESIGN FAMILY PROBE RECEIPT (task-4, whole-family FRESH)

- Repo: local AeroSkills clone. Brief commit a544f421 ("ops: wave-47
  brief, relay dispatch post wave-46 close, baseline 635") verified in
  the log as the direct parent of HEAD a4ae6d1e ("Wave-47: close-out
  must auto-update products-state (FIX)"). Probe ran at HEAD a4ae6d1e.
  `git diff --stat a544f421..HEAD` = 1 file, ops/automation/wave47-brief.md
  (5 insertions, 1 deletion): the skill tree is byte-identical at both
  commits, so the probe is valid for the brief commit. HEAD is clean.
- Scope: ENTIRE vehicle-design family, probed FRESH, read-only. No
  writes to skills/, eval/, standards-map.yaml, scripts/, Makefile or
  ops/automation briefs. One write only: this receipt.
- Leaf count re-verified at HEAD: `ls skills/vehicle-design/*/*/SKILL.md`
  = 56 (conceptual 5, cost-estimation 3, mass-properties 3, mdo 3,
  sizing 40, structures-integration 2). Router parity re-verified:
  `grep -c '^| vehicle-design/' skills/vehicle-design/SKILL.md` = 56.
  Wave-46 added landing-gear-height-sizing (sizing, commit 46214897),
  the only family change since the wave-45 whole-family probe.
- Corpus baseline: eval/hit1-corpus.yaml parsed fresh at HEAD, 1286
  task blocks (`grep -c '^  - id:'` = 1286). Task blocks carry
  id/query/intent/expected_skill; all candidate-token scans below ran
  over the full 1286 blocks.
- Standards map: 30 ids at HEAD (`grep -c '^  - id:' standards-map.yaml`
  = 30). far-25 at line 16, cs-25 at line 27, both reference-only per
  the all-leaves family convention.
- A pre-existing draft of this task's receipt was found at the target
  path (left by an earlier dispatch of the same task). Its factual
  claims were NOT trusted: every gate below was re-derived FRESH with
  new tool runs at this HEAD, and this file supersedes the draft.
- Prior-wave context read first: the wave-45 task-9 receipt
  (NO_CANDIDATES for the sizing pack) and the wave-46 task-9 receipt
  (1 GO, landing-gear-height-sizing) were consulted only to know which
  veins were previously closed; every claim here stands on fresh
  evidence from this session.

## Verdict

1 ranked GO candidate: vehicle-design/sizing/component-weight-estimation
(the class-II statistical airframe group-weight producer seam: predict
the wing, horizontal tail, vertical tail and fuselage group weights
from planform and body geometry plus design gross weight and design
load factor with published closed-form regression equations, the
producer side of the weight chain that every existing mass-properties
and weight leaf treats as input). Everything else in the family
declines with receipts below. The 40-leaf sizing pack stays saturated
for clean closed-form seams (wave-45 NO_CANDIDATES re-verified FRESH
this session); the landing-gear vein stays closed around the wave-46
addition (all adjacent sub-seams re-grepped zero-owner at this HEAD,
evidence below). Pack placement note: sizing is recommended because
the class-I/class-II sibling weight-estimation already lives in the
sizing pack; a mass-properties placement next to mass-budget is
defensible but secondary.

## Whole-family enumeration (56 leaves, all probed)

- conceptual 5: constraint-analysis, openvsp-geometry,
  payload-range-diagram, sizing-mission-profile, tow-estimation.
- cost-estimation 3: life-cycle-cost, operating-cost, parametric-cost.
- mass-properties 3: cg-envelope, inertia-estimation, mass-budget.
- mdo 3: design-of-experiments, multidisciplinary-optimization,
  surrogate-modeling.
- sizing 40: air-cycle-machine-sizing, aircraft-electrical-load-analysis,
  aircraft-oxygen-system-sizing, apu-fuel-burn-sizing,
  avionics-bay-cooling-sizing, battery-sizing, bleed-air-system-sizing,
  brake-energy-sizing, cabin-outflow-valve-sizing, canard-sizing,
  cargo-compartment-sizing, control-surface-sizing,
  electrical-wire-sizing, emergency-exit-configuration, engine-sizing,
  environmental-control-sizing, fire-protection-sizing,
  fuel-feed-system-sizing, fuel-jettison-sizing, fuel-tank-inerting-sizing,
  fuel-tank-sizing, fuselage-sizing, hydraulic-actuator-sizing,
  hydraulic-system-sizing, ice-protection-sizing, landing-gear-height-sizing,
  landing-gear-layout, landing-gear-retraction-sizing, landing-gear-sizing,
  nacelle-sizing, propeller-sizing, ram-air-turbine-sizing,
  spoiler-sizing, tail-sizing, tire-sizing, v-tail-sizing,
  weight-estimation, window-aperture-sizing, wing-planform-sizing,
  ws-tw-trade.
- structures-integration 2: fuselage-skin-stringer, wing-box-sizing.

## Ranked GO candidate

### 1. vehicle-design/sizing/component-weight-estimation (GO, rank 1)

Predict the four airframe structural group weights at the class-II
level from geometry and design loading: the wing group, horizontal
tail group, vertical tail group and fuselage group, each from a
published closed-form statistical regression on its planform or body
dimensions, sweep, thickness ratio, dynamic pressure, design load
factor and design gross weight, with the group-weight total feeding
the weight and balance chain. Deterministic stdlib arithmetic in the
family convention of the weight-estimation sibling; no tables beyond
the fixed published exponents and constants, no numeric integration,
no vendor data. This leaf is the producer side of the weight
statement: weight-estimation, mass-budget, cg-envelope and
inertia-estimation all consume component weights as given inputs, and
no leaf anywhere in the repo derives those component weights from
geometry.

(a) Zero-owner grep evidence, WHOLE skills/ tree (all 12 families)
plus eval/, run FRESH this session (real output; every grep below
returned zero files, EXIT=1):

```
$ grep -rilE "wing-group-weight|fuselage-group-weight|empennage-group-weight|horizontal-tail-group-weight|vertical-tail-group-weight|group-weight-equation|statistical-group-weight|statistical.weight" skills/ eval/
EXIT=1
$ grep -rilE "class-ii-weight|class.ii.weight|weight-prediction|weight.regression" skills/ eval/
EXIT=1
$ grep -rilE "wing.weight|wing-mass|fuselage.weight|empennage.weight" skills/ eval/
EXIT=1
$ grep -rilE "component-weight" skills/ eval/
EXIT=1
$ grep -inE "component-weight|wing-group|group-weight|statistical-weight|class-ii-weight" eval/hit1-corpus.yaml
(empty, zero of 1286 task blocks)
$ grep -inE "group-weight|group weight|wing-weight|wing weight|statistical-weight|statistical weight" eval/hit1-corpus.yaml
(empty)
```

The only leaf repo-wide whose name carries weight is
vehicle-design/sizing/weight-estimation, and its entire content is
weight-and-balance reduction of GIVEN component weights (fence quotes
below). No leaf in aerodynamics, structures, flight-mechanics,
propulsion or any other family predicts airframe group weights; the
whole-tree greps above prove it. The class-II regression method
tokens (group-weight-equation, statistical-group-weight) have zero
owners anywhere.

(b) Nearest sibling fence quotes (read verbatim at HEAD a4ae6d1e;
every weight consumer and the class-I producer treats component
weights as inputs, none produces them):

- skills/vehicle-design/sizing/weight-estimation/SKILL.md lines 25-28:
  "Use when the task is aircraft weight estimation and weight and
  balance: moments and center of gravity from component weights and
  arms, CG envelope checks, and empty-weight fraction band checks for
  class-I / class-II sizing." Workflow step 1 (line 43): "Collect
  component weights and arms into matching lists." Component weights
  are the INPUT of the only weight-named leaf; its whole functional
  scope is moments, CG, envelope and band checks. Its trigger list
  carries class-i and class-ii tokens, which the build must
  disambiguate (note below).
- skills/vehicle-design/mass-properties/mass-budget/SKILL.md lines
  25-29 and 54-55: builds the budget by "allocating subsystem masses"
  and workflow step 1: "Collect the subsystem mass estimates in kg,
  one entry per subsystem." Its quick reference names the breakdown
  categories (wing, fuselage, empennage, systems) but the rollup,
  growth allowance and margin policy consume given subsystem masses.
- skills/vehicle-design/conceptual/tow-estimation/SKILL.md lines
  31-34 and 41: "Empty and fuel fractions are class-based estimates
  from similar aircraft; the sizing iteration refines them." and
  "W0 = payload / (1 - empty fraction - fuel fraction)." Workflow step
  1: "Collect payload and class-based empty and fuel fractions." The
  class-I fraction iteration works on category bands, not
  geometry-driven group weights.
- skills/vehicle-design/mass-properties/cg-envelope/SKILL.md lines
  32-34 and 54-56: "x_cg = sum(w_i * x_i) / sum(w_i) over the
  components; the same rule applies to the z stations for the
  vertical cg." and step 1: "Collect component weights and stations."
  Weights are inputs to the station sum.
- skills/vehicle-design/mass-properties/inertia-estimation/SKILL.md
  lines 33-44: "Moment of inertia from the radius of gyration: I = m
  * k^2." and workflow step 1: "Collect component masses and radii of
  gyration." Masses are inputs.
- skills/vehicle-design/mdo/multidisciplinary-optimization/SKILL.md
  lines 91-93 (pitfalls): "mass-budget allocates the weight
  statement; MDO consumes the mass estimate as a discipline output
  and couples it to the structural and aerodynamic responses." MDO
  explicitly fences mass PRODUCTION out.
- skills/vehicle-design/structures-integration/wing-box-sizing/SKILL.md
  lines 32-46: sizes box-beam members from closed forms, root bending
  moment M = (2/(3*pi)) * n * W * b, "Spar cap area from the
  box-beam bending relation M = sigma * A * h: A = M / (sigma * h)",
  "Spar web shear flow: q = V / (n_webs * h)". It takes the design
  weight W as input and yields member areas and thicknesses, never a
  wing-group mass; skin, rib and non-optimum structure weight is
  outside its scope.
- skills/vehicle-design/structures-integration/fuselage-skin-stringer
  (router row): skin thickness, hoop and longitudinal stress,
  stringer spacing, frame pitch, panel buckling only; zero mass
  output.

Wave-45 closure note: the wave-45 task-9 receipt closed the
mass-properties vein "at the corpus-demand level" (cg-envelope,
inertia-estimation, mass-budget, weight-estimation). That closure
reasoned from zero corpus demand and did not examine the producer
seam. The wave-46 GO (landing-gear-height-sizing) set the standing
precedent that a genuine seam with zero existing corpus demand is
rankable and brings its own 2 corpus tasks at merge.

(c) Standards-map id exists (grep-verified at HEAD):

```
$ grep -n "id: far-25" standards-map.yaml
16:  - id: far-25
$ grep -n "id: cs-25" standards-map.yaml
27:  - id: cs-25
```

far-25 and cs-25 are the standing reference-only convention of all 56
vehicle-design leaves (verified on disk), used in the weight and
balance certification context of the downstream consumers.

(d) Published deterministic closed-form anchor (summary-only, no text
reproduced): the class-II statistical airframe group-weight prediction
method as presented in Raymer, Aircraft Design: A Conceptual Approach
(weight estimation chapter: wing, horizontal tail, vertical tail and
fuselage group weight regressions on planform area, aspect ratio,
sweep, thickness ratio, dynamic pressure, design load factor and
design gross weight, with fixed published exponents and constants),
with Torenbeek, Synthesis of Subsonic Airplane Design, weight
prediction treatment as the cross-check source and the Gudmundsson and
Sadraey equivalents in the same book family the siblings already
paraphrase. The equations are deterministic closed forms with
published constants, so magnitudes are independently verifiable (a
180-seat transport wing group lands in the established fraction band
of MTOW; the four group totals reconcile against the class-I empty
weight band that weight-estimation already checks). No fabricated
correlations, no vendor data. Anchor books are proprietary-sold, so
the leaf states method and equations in its own notation,
paraphrase-only per the brief 06 convention.

(e) 2 wordable Hit@1 corpus queries carrying DISTINCTIVE hyphenated
tokens that route to this leaf without stealing existing corpus tasks
(verified FRESH: the existing weight-estimation tasks w1 and w2 carry
class-I, empty-weight-fraction-band and weight-and-balance tokens;
the tow-estimation tasks carry takeoff-weight and convergence tokens;
the corpus token scan above shows zero task blocks carrying
wing-group-weight, fuselage-group-weight, group-weight,
statistical-weight or class-ii-weight tokens):

1. "run the component-weight-estimation at class II for the
   transport: evaluate the wing-group-weight regression on the
   planform area, aspect ratio, sweep, thickness ratio and design
   load factor, then the fuselage-group-weight regression on the
   fuselage dimensions, and hand the group-weight totals to the
   balance sheet"
2. "predict the empennage group weights with the statistical-weight
   equations: horizontal-tail-group-weight and
   vertical-tail-group-weight from the tail areas, tail aspect ratios
   and the design gross weight, then roll the component-weight totals
   into the mass-budget"

Build-time fence note: weight-estimation carries the generic trigger
token class-ii for its input-level W and B meaning; the new router
row and guidance bullet must disambiguate (class-II group-weight
PREDICTION from geometry routes to component-weight-estimation;
class-II weight and balance of given component weights stays with
weight-estimation), and a fence line should be added to
weight-estimation ("statistical group-weight prediction from geometry
belongs to the component-weight-estimation sibling").

(f) No generic single-word tag overlap: proposed tags are hyphenated
compounds only: component-weight-estimation, group-weight-equation,
wing-group-weight, fuselage-group-weight,
horizontal-tail-group-weight, vertical-tail-group-weight,
statistical-weight-prediction, class-ii-weight-buildup. Prune generic
single-word tags (weight, mass, estimation, group) since
weight-estimation, mass-budget and tow-estimation already own the
generic weight/mass surface. Family spread: vehicle-design 56 to 57
after landing.

## Landing-gear adjacency after the wave-46 addition (probed fresh)

landing-gear-height-sizing (wave-46, on disk with its gate-3 contract
scripts) owns the vertical ground-line geometry. Adjacent sub-seams
re-grepped zero-owner at this HEAD across the whole family and the
corpus: shimmy 0, gear-walk 0, turning-radius 0, oleo 0, bogie 0,
gear-doors 0, escape-slide 0 (single grep over skills/vehicle-design/
plus eval/hit1-corpus.yaml, EXIT=1). Tail-strike and tail-down
geometry are NOT zero-owner: they belong to landing-gear-layout,
whose fence states it "takes the solved gear heights as given inputs
to its tipback, tail strike clearance angle and lateral turnover
angle checks" (read verbatim). tire-sizing, landing-gear-sizing,
landing-gear-retraction-sizing, brake-energy-sizing and structures
landing-ground-loads close the remaining territory. The landing-gear
vein is closed; no adjacent GO.

## Decline reasons per vein

- Sizing pack (40 leaves): wave-45 NO_CANDIDATES re-verified FRESH.
  Every probed clean closed-form seam resolves to a live owner or a
  documented decline; my fresh adjacency and boundary greps this
  session (landing-gear tokens, tail-strike tokens, weight-prediction
  tokens) found zero new zero-owner seams. The wave-46 +1 closed the
  last landing-gear seam. Saturated.
- Mass properties (3 leaves): consumers (cg-envelope, inertia-
  estimation, mass-budget) plus the class-I/II weight-estimation
  sibling all take component weights as given; the producer seam (the
  rank-1 GO above) is the one open position in the vein. No other
  open position: vertical-cg station values are geometry inputs with
  no closed-form anchor (cg-envelope handles z stations given as
  inputs); gyration-radius catalogs are data heuristics without a
  deterministic published anchor (inertia-estimation owns I = m*k^2
  and the sanity check).
- Conceptual (5 leaves): tow-estimation (class-I fraction iteration),
  sizing-mission-profile, payload-range-diagram, constraint-analysis,
  openvsp-geometry and the ws-tw-trade/constraint-analysis matching
  chart close the class-I and geometry veins. MZFW and operating-
  weight design relations are class-data band relations without a
  deterministic closed form, and tow-estimation owns the class-based
  fraction context. Passenger and baggage weight policy tables have
  no id in the 30-id standards map (map-blocked; no icao or faa-ac
  id).
- Cost estimation (3 leaves): life-cycle-cost, operating-cost and
  parametric-cost close the pack; no corpus surface for new cost
  relations.
- mdo (3 leaves) and structures-integration (2 leaves): pack-internal
  seams closed (surrogate-modeling, design-of-experiments and
  multidisciplinary-optimization split the mdo surface;
  fuselage-skin-stringer and wing-box-sizing split the structural
  sizing surface; wing-box-sizing produces member areas, never group
  mass, per the fence quote in the GO evidence above).
- Standing declines from the wave-45 and wave-46 receipts (high-lift,
  winglet, rotorcraft main rotor, trim-tab, air-induction, oleo
  internals, thrust reverser, windshield/canopy, refuel/defuel/vent,
  APU selection, spin-up/springback/side-load, shimmy,
  steering/turning, gas-spring, crossfeed/scavenge, pump catalog,
  S-duct, control-surface balance weights, product of inertia, wing
  incidence, mechanical control runs, gear doors, deicing boots,
  potable/waste water, escape slide, circuit breakers, LCN/ACN, wing
  fuel volume, propeller governor, FSII, smoke detection, rain
  repellent, cabin air distribution, static wicks, tire creep, window
  pitch, frame spacing, seat track, cargo tie-down, trim air, thermal
  relief, feel systems, aft-body upsweep, dihedral, lightning zonal,
  radome, pylon): nothing in the family changed except the wave-46 GO
  (git history confirms the only family commit since wave-45 is
  landing-gear-height-sizing), so these stand as recorded in their
  receipts; my fresh boundary greps this session are consistent with
  them (all landing-gear and tail boundary tokens resolve to owners
  or the declines above).
- Boundary topics owned OUTSIDE the family (no GO): second-segment
  and OEI climb (flight-mechanics oei-climb-gradient plus ws-tw-trade
  and constraint-analysis climb constraints), design dive speed
  (flight-test-operations flutter-testing), takeoff and landing field
  length (flight-mechanics takeoff and landing performance plus the
  ws-tw-trade constraint chart), sweep and taper geometry
  (wing-planform-sizing plus the aero wing-planform-design leaf).

## Standards-map check

30 ids present in standards-map.yaml (grep-verified at HEAD):
arinc-429, arinc-664, arp4754a, arp4761a, as9100, as9102, asme-y14-5,
cmh-17, cs-25, do-160, do-178c, do-254, do-330, ecss, far-107, far-25,
far-29, far-33, itar-ear, mil-std-1553, mil-std-1797a, mmpsd, msg-3,
naca-tn-902, naca-tr-824, nas-410, rtca-do-185, rtca-do-229,
rtca-do-260b, sep-2640. No icao, no faa-ac, no sae statistical-weight
id (payload-weight-policy and LCN/ACN seams stay map-blocked). The
rank-1 GO uses far-25 and cs-25 reference-only per the all-leaves
family convention.

## Method note

All greps and reads above were read-only runs at HEAD a4ae6d1e (skills
content identical to brief commit a544f421 per git diff). Corpus scans
(1286 task blocks) ran over eval/hit1-corpus.yaml. Family enumeration
and router parity re-verified by ls and grep. The pre-existing draft
receipt at this path was superseded by the fresh evidence in this
file. No repo file was modified except this receipt. This receipt
contains no em dashes and no machine-local absolute paths.
