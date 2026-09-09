# WAVE-48 VEHICLE-DESIGN FAMILY PROBE RECEIPT (task-4, whole-family FRESH)

- Repo: local AeroSkills repo at ~/AeroSkills, git HEAD 92d84a48 (verified
  `git log --oneline -1`: "ops: stage wave-48 brief (planning only -
  daylight dispatch 10:00 CEST)"). Working tree clean at probe start and
  end except the wave48-recon receipts directory (git status --porcelain:
  1 untracked entry, this receipt).
- Scope: ENTIRE vehicle-design family, 57 leaves, probed FRESH at wave-48
  HEAD. Read-only probe: no writes to skills/, eval/, standards-map.yaml,
  scripts/ or briefs. One write only: this receipt.
- Family leaf count verified: `find skills/vehicle-design -mindepth 3
  -name SKILL.md` = 57 (conceptual 5, cost-estimation 3, mass-properties
  3, mdo 3, sizing 41, structures-integration 2). Router parity
  re-verified: `grep -c '^| vehicle-design/' skills/vehicle-design/SKILL.md`
  = 57. Wave-47 GO vehicle-design/sizing/component-weight-estimation
  verified on disk (corpus tasks w47-component-weight-estimation-1/-2
  present in eval/hit1-corpus.yaml). Wave-46 GO
  landing-gear-height-sizing verified on disk.
- Corpus baseline: eval/hit1-corpus.yaml = 1306 tasks (yaml parse
  recovered 1306/1306). Router sim indexed 657 SKILL.md under skills/
  (645 leaves + 12 family routers) with the same loader and scoring as
  scripts/router_eval.py (tags 3, name 2, desc 1, body 0.5, verbatim
  phrase bonus 4, tie-break path asc). Baseline gate check at this HEAD:
  0 failures of 1306 (100 percent Hit@1).
- Standards map: 30 ids at HEAD (`grep '^  - id:' standards-map.yaml` =
  30); candidates use far-25 and cs-25 reference-only per the standing
  vehicle-design family convention.
- Prior-wave context read FIRST: wave-47 vehicle-design receipt
  (ops/automation/state/wave47-recon/task-4-receipt.md, HEAD a4ae6d1e, 1
  GO component-weight-estimation) and wave-46 task-9 receipt
  (ops/automation/state/wave46-recon/task-9-receipt.md, HEAD 45931c16,
  1 GO landing-gear-height-sizing, full decline tables). Every wave-45/46
  decline named there was re-verified FRESH at this HEAD; each stands or
  is re-opened with fresh evidence below. The wave-45 task-9 receipt
  (sizing pack NO_CANDIDATES) was consulted for the closed-veins
  inventory only.

## Verdict

2 ranked GO candidates, both in the sizing pack beside the wave-47 GO,
both producer-side class-II statistical group-weight seams that the
wave-47 component-weight-estimation spec explicitly fenced out of its
four-airframe-group claim ("non-airframe group weights (landing gear,
installed engines, systems, fuel, fixed equipment): the four airframe
structural groups are the whole claim", verbatim from the wave-47 spec
in ops/automation/state/wave47-specs/component-weight-estimation.md):

1. vehicle-design/sizing/landing-gear-weight-estimation (GO, rank 1):
   class-II statistical landing gear group weight regression, main and
   nose gear group masses from design landing weight, ultimate landing
   load factor and gear geometry; producer of the gear weight that
   landing-gear-retraction-sizing takes as a given input.
2. vehicle-design/sizing/fuel-system-weight-estimation (GO, rank 2):
   class-II fuel system group weight regression (tankage, plumbing,
   pump hardware mass) from total fuel weight and tank arrangement;
   producer of the hardware mass the fuel chain leaves unproduced.

Everything else declines with fresh evidence below: the landing-gear
DESIGN surface (layout, static loads, retraction, height, tires,
brakes) is fully owned, class-I fraction territory stays closed under
tow-estimation and weight-estimation ownership, and the sizing
matching iteration surface stays split-owned (ws-tw-trade,
constraint-analysis, tow-estimation).

## Whole-family enumeration (57 leaves, all probed)

- conceptual 5: constraint-analysis, openvsp-geometry,
  payload-range-diagram, sizing-mission-profile, tow-estimation.
- cost-estimation 3: life-cycle-cost, operating-cost, parametric-cost.
- mass-properties 3: cg-envelope, inertia-estimation, mass-budget.
- mdo 3: design-of-experiments, multidisciplinary-optimization,
  surrogate-modeling.
- sizing 41: air-cycle-machine-sizing, aircraft-electrical-load-analysis,
  aircraft-oxygen-system-sizing, apu-fuel-burn-sizing,
  avionics-bay-cooling-sizing, battery-sizing, bleed-air-system-sizing,
  brake-energy-sizing, cabin-outflow-valve-sizing, canard-sizing,
  cargo-compartment-sizing, component-weight-estimation,
  control-surface-sizing, electrical-wire-sizing,
  emergency-exit-configuration, engine-sizing,
  environmental-control-sizing, fire-protection-sizing,
  fuel-feed-system-sizing, fuel-jettison-sizing,
  fuel-tank-inerting-sizing, fuel-tank-sizing, fuselage-sizing,
  hydraulic-actuator-sizing, hydraulic-system-sizing,
  ice-protection-sizing, landing-gear-height-sizing,
  landing-gear-layout, landing-gear-retraction-sizing,
  landing-gear-sizing, nacelle-sizing, propeller-sizing,
  ram-air-turbine-sizing, spoiler-sizing, tail-sizing, tire-sizing,
  v-tail-sizing, weight-estimation, window-aperture-sizing,
  wing-planform-sizing, ws-tw-trade.
- structures-integration 2: fuselage-skin-stringer, wing-box-sizing.

## Ranked GO candidates

### 1. vehicle-design/sizing/landing-gear-weight-estimation (GO, rank 1)

Predict the landing gear group weight at the class-II level: main and
nose gear group masses from statistical regressions on the design
landing weight, the ultimate landing load factor (1.5 times the limit
landing load factor) and the gear geometry, summed into the gear group
total that feeds the weight statement. Deterministic stdlib arithmetic
in the exact convention of the wave-47 component-weight-estimation
sibling; no tables beyond fixed published exponents and constants.
Every landing-gear sibling sizes loads, geometry or mechanism; none
produces the gear group MASS, and landing-gear-retraction-sizing
consumes gear weight as a GIVEN input (fence quotes below). This leaf
is the missing producer of that input.

(a) Zero-owner grep evidence, WHOLE skills/ tree (all 12 families)
plus eval/, run FRESH this session (script scan over every SKILL.md
and the full 1306-task corpus; every battery returned zero):

```
landing-gear-weight (all hyphen/space variants, incl.
  landing-gear-group-weight, gear-group-weight, main-gear-group-weight,
  nose-gear-group-weight, landing-gear-weight-estimation):
  skills=ZERO, corpus=0
natural-language "gear weight" / "gear mass" / "landing gear weight"
  task lines in corpus: 0
```

The only "gear weight" mentions anywhere in the tree are inside
landing-gear-retraction-sizing, where gear weight W is the given input
to the retraction moment, never an output (see fence quotes). The
wave-47 spec fence (Verdict header) confirms the identity is
deliberately unclaimed, not accidentally so.

(b) Nearest sibling fence quotes (read FRESH at this HEAD, verbatim):

- landing-gear-retraction-sizing (description): "the gear moment about
  the retract pivot from gear weight and CG arm"; workflow step 1:
  "Fix the gear demand: gear weight W and its CG arm d ahead of the
  retract pivot (retraction_moment)." The retraction leaf REQUIRES the
  gear weight as an input and never derives it; its worked example
  fixes "gear weight 14000 N with CG arm 1.10 m" as a given.
- landing-gear-sizing: sizes "static loads over the struts, nose and
  main gear load share from the CG and wheelbase, shock absorber
  stroke, and the tire rating margin"; loads and stroke, never a gear
  group mass output.
- tire-sizing: sizes tire diameter, width, count, pressure, footprint
  from the static load per tire; no gear group mass.
- landing-gear-height-sizing (wave-46 GO): vertical ground line and
  gear heights from clearance constraints; heights feed this candidate
  as geometry inputs.
- landing-gear-layout: angles (tipback, tail strike, lateral turnover)
  and nose gear load fraction band; body: "the fraction is
  dimensionless and layout-level only; strut loads are never computed
  here", let alone gear mass.
- mass-budget: step 1 "Collect the subsystem mass estimates in kg, one
  entry per subsystem"; masses are given inputs, including any gear
  subsystem.
- weight-estimation: step 1 "Collect component weights and arms into
  matching lists"; weights are inputs to the moments and CG reduction.
- component-weight-estimation (wave-47 GO): body "predicting the four
  airframe structural group masses at the class-II level... the wing
  group, the horizontal tail group, the vertical tail group and the
  fuselage group"; landing gear group weight is OUT of its claim
  (Verdict header). A gear group total is a different weight-statement
  line; this candidate produces it.

(c) Standards-map id exists (grep-verified at HEAD):

```
$ grep -n "id: far-25" standards-map.yaml
16:  - id: far-25
$ grep -n "id: cs-25" standards-map.yaml
27:  - id: cs-25
```

far-25 and cs-25 are the standing reference-only convention of the
vehicle-design landing-gear and weight leaves (landing-gear-sizing,
tire-sizing, weight-estimation, component-weight-estimation all carry
both, verified on disk).

(d) Published deterministic closed-form anchor (summary-only, no text
reproduced): the class-II statistical landing gear group weight
prediction in the weight estimation treatment of the conceptual-design
book family the wave-47 sibling already paraphrases: main and nose
landing gear group weight regressions on design landing weight,
ultimate landing load factor and gear strut length terms with fixed
published exponents and constants (Roskam, Airplane Design Vol V
Component Weight Estimation; Raymer weight estimation chapter;
Torenbeek cross-check; books proprietary-sold, paraphrase-only per
brief 06). Deterministic closed forms, no empirical tables, no vendor
catalogs. Magnitude independently verifiable against the class-I empty
weight fraction checks of weight-estimation.

(e) 2 wordable Hit@1 corpus queries, sim-verified by replicating the
scripts/router_eval.py token router EXACTLY over the real 657-SKILL.md
index plus this hypothetical candidate (hyphen-preserving tokens,
stopword filter, tag 3 / name 2 / desc 1 / body 0.5, verbatim-phrase
bonus 4, tie-break path asc). ZERO theft over all 1306 corpus tasks (0
reroutes with the candidate injected; baseline 0 failures without it):

1. "estimate the landing-gear-group-weight at class II with the
   statistical gear-weight regression: main-gear-group-weight and
   nose-gear-group-weight from the design landing weight, the ultimate
   landing load factor and the main and nose gear strut lengths, then
   hand the gear weight total to the mass budget"
   HIT1 landing-gear-weight-estimation 36.0; runner-up
   component-weight-estimation 15.5; margin 20.5.
2. "run the landing-gear-weight-estimation for the tricycle transport:
   predict the landing-gear-group-weight with the
   class-ii-gear-weight-buildup regression so the retraction mechanism
   sizing gets the gear weight input"
   HIT1 landing-gear-weight-estimation 21.5; runner-up
   landing-gear-retraction-sizing 8.5; margin 13.0.

Neither query steals: corpus gear tasks route on strut-load, stroke,
tipback, retraction-actuator and tire tokens, none on
gear-group-weight tokens. Build-time fence note: retraction-sizing
should gain a line ("landing gear group weight prediction from design
landing weight and load factor belongs to the
landing-gear-weight-estimation sibling; this leaf takes the gear
weight as a given input") and one router row in
skills/vehicle-design/SKILL.md beside the landing-gear rows.

(f) No generic single-word tag overlap: proposed tags are hyphenated
compounds only: landing-gear-weight-estimation, landing-gear-group-
weight, main-gear-group-weight, nose-gear-group-weight,
gear-group-weight-regression, class-ii-gear-weight-buildup. Prune
generic single-word tags (gear, weight, landing, mass) since
landing-gear-sizing, tire-sizing and weight-estimation own the generic
surface. Family spread: vehicle-design 57 to 58 after landing.

### 2. vehicle-design/sizing/fuel-system-weight-estimation (GO, rank 2)

Predict the fuel system group weight at the class-II level: the
hardware mass of the fuel system (tanks, plumbing, pumps, valves)
from the total fuel weight and the tank arrangement, via a published
closed-form regression with fixed exponents and constants, producing
the fuel-system group mass that feeds the weight statement and the
mass-budget rollup. The five fuel leaves size volume, feed hydraulics,
jettison rate, inerting washout and APU burn; none produces the fuel
SYSTEM hardware mass, and the wave-47 spec fence names "fuel" among
the non-airframe group weights outside component-weight-estimation's
claim (Verdict header).

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/, run FRESH
this session (every battery zero):

```
fuel-system-weight variants (fuel-system-group-weight,
  fuel-system-weight-estimation, tank-group-weight): skills=ZERO,
  corpus=0
natural-language "fuel system weight" / "fuel-system weight" task
  lines in corpus: 0
fixed-equipment-weight / systems-weight-estimation /
  equipment-weight-estimation / group-weight-fraction:
  skills=ZERO, corpus=0
```

(b) Nearest sibling fence quotes (read FRESH at this HEAD, verbatim):

- fuel-tank-sizing (description): "converting the fuel mass into a
  fuel volume with the fuel density, adding the ullage allowance to
  get the required tank volume, and checking that volume against the
  volume available in the wing and fuselage tanks." Fuel MASS in, tank
  VOLUME out; its tags (fuel-mass, fuel-volume, usable-fuel, ullage)
  mean the fuel carried, never tank hardware mass.
- fuel-feed-system-sizing: feed line velocity, Reynolds number, Darcy
  loss, NPSH and boost pump power; hydraulics and power, never a fuel
  system group mass.
- fuel-jettison-sizing: dumpable fuel MASS (the fuel) and jettison
  rate to the 15-minute landing weight rule; no hardware mass.
- mass-budget: step 1 "Collect the subsystem mass estimates in kg";
  fuel system subsystem mass would be a given input to it.
- component-weight-estimation (wave-47 GO): its wing regression takes
  the in-wing fuel MASS as an input term and its spec fence names the
  fuel weight group as OUT of the four-group claim (Verdict header).
  The fuel SYSTEM hardware group is neither its input nor its output.
- engine-sizing owns the installed-engine weight producer (W_eng =
  T_SL / (T/W)_eng, engine-weight tag, corpus esg2), so "installed
  engines" is NOT an open seam; this candidate is scoped to the fuel
  system group only.

(c) Standards-map id exists: far-25 (line 16) and cs-25 (line 27),
grep-verified at HEAD, reference-only per the fuel-family convention
(fuel-tank-sizing, fuel-feed-system-sizing, fuel-jettison-sizing all
carry both).

(d) Published deterministic closed-form anchor (summary-only, no text
reproduced): the fuel system group weight regression in the weight
estimation / component weight estimation treatments of the same
conceptual-design book family (Roskam Vol V fuel system weight
regression on total fuel weight and tank count; Raymer and Torenbeek
cross-checks), deterministic closed form with fixed published
exponents and constants, no empirical tables, no vendor catalogs.
Magnitude independently verifiable against the class-I empty weight
fraction checks of weight-estimation.

(e) 2 wordable Hit@1 corpus queries, sim-verified with the same exact
router replication over the real index plus BOTH hypothetical
candidates (margins include cross-candidate competition); zero theft
over all 1306 tasks:

1. "estimate the fuel-system-group-weight for the weight statement
   with the statistical fuel system weight regression from the total
   fuel weight and roll the fuel-system-group-weight into the mass
   budget"
   HIT1 fuel-system-weight-estimation 16.0; runner-up
   component-weight-estimation 9.0; margin 7.0.
2. "run the fuel-system-weight-estimation at class II: compute the
   fuel-system-group-weight with the
   class-ii-fuel-system-weight-buildup regression from the total fuel
   weight for the tank and plumbing group mass"
   HIT1 fuel-system-weight-estimation 25.0; runner-up
   component-weight-estimation 9.5; margin 15.5.

Neither query steals: the fuel corpus tasks route on fuel-volume,
ullage, NPSH, feed-line, jettison-rate, inerting and APU tokens,
none on fuel-system-group-weight tokens. Build-time notes: one router
row in skills/vehicle-design/SKILL.md beside the fuel rows and one
fence line in fuel-tank-sizing ("fuel system hardware group weight
prediction belongs to the fuel-system-weight-estimation sibling; this
leaf converts the fuel mass to volume").

(f) No generic single-word tag overlap: proposed tags are hyphenated
compounds only: fuel-system-weight-estimation,
fuel-system-group-weight, fuel-system-weight-regression,
class-ii-fuel-system-weight-buildup, tank-group-weight-estimation.
Prune generic single-word tags (fuel, weight, system, tank, pump)
since fuel-tank-sizing and fuel-feed-system-sizing own the generic
fuel surface. Family spread: vehicle-design 58 to 59 if both ranked
GOs land.

## Decline reasons per vein (fresh evidence at this HEAD)

| Seam probed | Fresh evidence (this HEAD) | Gate(s) | Verdict |
|---|---|---|---|
| landing-gear layout / static loads / retraction / height / tires / brakes design | owned: landing-gear-layout (angles, load fraction band), landing-gear-sizing (static strut loads, stroke), landing-gear-retraction-sizing (mechanism, locks, bay stowage), landing-gear-height-sizing (ground line), tire-sizing (dims, pressure, footprint), brake-energy-sizing (rejected-takeoff energy), structures/loads/landing-ground-loads (certification reaction families) | b, seam | DECLINE (design surface fully owned; only open position is rank-1 group-weight producer) |
| landing-gear spin-up/springback/side-load dynamic cases | vehicle-design zero; structures landing-ground-loads owns level/braked/tail-down/one-wheel reaction families; corpus 0 | seam | DECLINE (standing, structures-owned) |
| shimmy / gear-walk | fresh grep: skills=ZERO, corpus=0 | d, e | DECLINE (no clean closed-form anchor in map-standard book set) |
| oleo / shock-strut internals | fresh grep: skills=ZERO (vehicle-design), corpus=0; landing-gear-sizing fences "FAR-25.723 / CS-25.723 shock absorption verification is a drop test; this module provides the sizing-level energy check only" | d, e | DECLINE (standing) |
| nose-gear steering / turning-radius | fresh grep: vehicle-design steering/turning-radius ZERO; corpus steering hits (7) route to FTO vmcg, gnc CMG/midcourse, space ADCS, msg3 | d, e | DECLINE (standing) |
| systems-weight fractions (generic class-II systems predictor) | category fraction tables are empirical band data without a single deterministic anchor (fails d); class-I fraction context owned by tow-estimation (fuel/empty fraction iteration) and weight-estimation (empty-weight fraction band checks); mass-budget owns the rollup policy | b, d | DECLINE (band-data heuristic, split-owned fraction surface) |
| wing-loading / thrust-loading matching iteration | split-owned: ws-tw-trade (binding constraint, minimum T/W at given W/S, corpus wt1/wt2), constraint-analysis (feasible region, corpus w19), tow-estimation (convergence of the sizing iteration) | b, seam | DECLINE (split-owner; a loop leaf would steal all three) |
| installed-engine / nacelle group weight | engine-sizing owns the engine weight producer verbatim W_eng = T_SL/(T/W)_eng (engine-weight tag, corpus esg2); nacelle-sizing owns nacelle geometry and drag, framing nacelle weight only as the loop term feeding engine-sizing ("the nacelle weight and drag feed the engine selection"); identity split across three leaves, zero corpus for a nacelle group mass | b, e, seam | DECLINE (engine weight owned; nacelle group mass has no clean single owner or corpus pull) |
| brake group hardware mass | brake-energy-sizing owns rejected-takeoff energy and heat sink; corpus 0 for brake mass; systems-weight-fraction decline applies | d, e | DECLINE |
| escape slide / evacuation | vehicle-design evacuation content only in emergency-exit-configuration (exit geometry and credit rules); corpus 0; slide length is a sill-height correlation, not clean closed form | d, e | DECLINE (standing) |
| trim-tab | fresh grep: skills=ZERO, corpus=0; control-surface-sizing owns aileron/elevator/rudder area, hinge moment, deflection only | d, e | DECLINE (standing) |
| thrust reverser | fresh grep: skills=ZERO (VD), corpus=0 | d, e | DECLINE (standing) |
| winglet | VD skills ZERO; corpus 11 hits all route aerodynamics winglet-design | seam | DECLINE (aero-owned) |
| high-lift / flap | VD skills ZERO; corpus 42 hits route aerodynamics high-lift-systems and FM rotorcraft leaves | seam | DECLINE (aero/FM-owned) |
| windshield / canopy aperture | VD skills ZERO (only ice-protection context mention); corpus canopy hit (1) is the space parachute canopy, not aircraft | d, e | DECLINE (standing) |
| refuel / defuel / fuel vent | fresh grep: skills=ZERO, corpus=0; fuel-feed-system-sizing owns the vent-pressure term in its NPSH chain | d, e | DECLINE (standing) |
| LCN / ACN pavement classification | fresh grep: skills=ZERO, corpus=0; no icao id in the 30-id standards map | c, d | DECLINE (map-blocked, standing) |
| gear doors / gear-bay fairing | retraction-sizing owns bay stowage fit (wheel plus folded strut envelope verdict); doors are fairing geometry without a closed-form anchor | d, seam | DECLINE (standing) |
| pneumatic / fluid deicing boots | ice-protection-sizing owns the thermal protection side; corpus 0 for boot hardware | d, e | DECLINE (standing) |
| potable/waste water, rain repellent, static wicks, circuit breakers, fuel crossfeed/scavenge, pump catalog, propeller governor, FSII, cargo tie-down, seat track, cabin air distribution, trim air, thermal relief, feel systems | fresh greps re-verified: each ZERO owners in vehicle-design and ZERO corpus (potable 0/0, crossfeed 0/0, refuel 0/0 as tabled; others per wave-46 table re-grepped) | c/d/e | DECLINE (standing declines re-verified FRESH; no family change since wave-46 except the two GOs) |

## Closed veins (reaffirmed FRESH at wave-48 HEAD)

- Landing gear design: layout angles and load fractions, static loads
  and stroke, retraction mechanism and bay stowage, vertical ground
  line and heights, tires, brakes, certification reaction families all
  owned; the only open landing-gear position is the group-weight
  producer (rank-1 GO). Spin-up/springback, shimmy, steering, oleo
  internals stay closed (zero owners, zero corpus).
- Fuel system: volume and ullage, feed hydraulics to NPSH, jettison
  rate, inerting washout, APU burn all owned; fuel SYSTEM hardware
  mass is the one open position (rank-2 GO). Vent/refuel/crossfeed/
  scavenge/pump catalog stay closed.
- Weight chain: four airframe structural group weights produced by
  component-weight-estimation (wave-47); moments, CG, envelope and
  class-I/II band checks in weight-estimation; subsystem rollup in
  mass-budget; class-I takeoff weight fraction iteration in
  tow-estimation. Consumers take component weights as given; the two
  ranked GOs are the producer positions the wave-47 spec fence left
  open.
- Matching chart: ws-tw-trade + constraint-analysis + tow-estimation
  split the W/S-T/W constraint, feasible-region and convergence
  surface. Closed.
- Corpus note: 116 vehicle-design-targeted tasks serve all 57 leaves
  (2 per leaf, 2 extras); no existing task points into either GO gap;
  each GO brings its own 2 corpus tasks at merge.

## Standards-map check

30 ids present in standards-map.yaml (grep-verified at HEAD): arinc-429,
arinc-664, arp4754a, arp4761a, as9100, as9102, asme-y14-5, cmh-17,
cs-25, do-160, do-178c, do-254, do-330, ecss, far-107, far-25, far-29,
far-33, itar-ear, mil-std-1553, mil-std-1797a, mmpsd, msg-3,
naca-tn-902, naca-tr-824, nas-410, rtca-do-185, rtca-do-229,
rtca-do-260b, sep-2640. No icao, faa-ac or sae id (LCN/ACN and
payload-weight-policy seams stay map-blocked). Both ranked GOs use
far-25 and cs-25 reference-only per the family convention.

## Method note

All greps and reads above were read-only runs at HEAD 92d84a48.
Evidence helpers ran in the session temp dir: corpus parser (1306/1306
task blocks recovered), the whole-tree zero-owner battery over every
SKILL.md plus the full corpus, the standing-decline re-verification
battery, and the router sim replicating scripts/router_eval.py scoring
exactly (657 SKILL.md indexed; baseline 0/1306 failures; candidates
injected one at a time and together; 0 thefts in every configuration).
Family enumeration and router parity re-verified by find and grep.
Prior receipts read first (wave-47 task-4, wave-46 task-9, wave-45
task-9 for context). No repo file modified except this receipt. No em
dashes, no machine-local absolute paths.
