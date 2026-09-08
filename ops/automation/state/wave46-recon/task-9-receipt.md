# WAVE-46 VEHICLE-DESIGN EXTENSION PROBE RECEIPT (task-9, whole-family FRESH)

- Repo: the local AeroSkills repo at git HEAD 45931c16 (verified `git log
  --oneline -1` first line: "45931c16 fix(audit): move BRANDING_REPOS to
  module scope"). HEAD is clean.
- Scope: ENTIRE vehicle-design family, 55 leaves (largest-last tier),
  probed FRESH at current HEAD. Read-only probe: no writes to skills/,
  eval/, standards-map.yaml, scripts/, Makefile, or ops/automation briefs.
  One write only: this receipt (ops/automation/state/wave46-recon/).
- Corpus baseline: eval/hit1-corpus.yaml = 1266 task blocks (regex parse
  recovered 1266/1266; helper script in the session temp dir). 112 tasks
  target vehicle-design leaves and they cover all 55 distinct leaves
  (2 per leaf with 2 extras), so the family is fully corpus-served at
  HEAD and every candidate must stand on its own two new tasks at merge.
- Standards map: 30 ids in standards-map.yaml (grep '^  - id:' = 30,
  verified at HEAD); candidate id grep-verified below.
- Doctrine (wave46-brief.md item 9): the smaller-family viable pool sits
  below ~12 after tasks 0-8 (flight-mechanics +1, avionics +1, propulsion
  +2, rest NO_CANDIDATES), so the vehicle-design extension probe runs
  under the pool-drop rule. Wave-45 task-9 receipt (NO_CANDIDATES with
  receipts) was read first; every named decline was re-verified FRESH and
  stands unless re-opened below with fresh evidence.
- Cross-wave check: the ranked GO below appears in NO wave-43/44/45
  receipt, leaf plan, or builder kit, and in NO wave-46 task-0..8 receipt
  (grep of ops/automation/state wave43-46 recon files and leaf plans for
  gear-height / static-ground-line / gear-height-selection tokens returns
  zero hits; the only ops file matching ground-clearance is the wave-42
  landing-gear-layout spec, which uses heights as inputs, quoted below),
  so ranking it does not reopen any closed or declined item.

## Verdict

1 ranked GO candidate: vehicle-design/sizing/landing-gear-height-sizing
(the vertical gear geometry seam: static ground line and main/nose gear
heights selected from ground-clearance constraints, the tail cone
rotation clearance and the nacelle/propeller clearances at the level and
rotated attitudes). Everything else in the family declines with receipts
below. Vehicle-design at 55 is the densest family in the repo, but this
one landing-gear vertical-geometry seam is genuinely open: zero owner
tree-wide and zero corpus demand, a published closed-form anchor in the
same conceptual-design book set the sibling landing-gear-layout leaf
already paraphrases, and the existing standards-map id far-25
(reference-only, family convention). The family corpus is saturated, so
this candidate adds its own 2 corpus tasks at merge per wave convention.

## Whole-family enumeration (55 leaves, all probed)

`find skills/vehicle-design -mindepth 3 -name SKILL.md` returns 55 files
at this HEAD. Router parity: `grep -c "^| vehicle-design/" \
skills/vehicle-design/SKILL.md` = 55.

- conceptual 5: constraint-analysis, openvsp-geometry,
  payload-range-diagram, sizing-mission-profile, tow-estimation.
- cost-estimation 3: life-cycle-cost, operating-cost, parametric-cost.
- mass-properties 3: cg-envelope, inertia-estimation, mass-budget.
- mdo 3: design-of-experiments, multidisciplinary-optimization,
  surrogate-modeling.
- sizing 39: air-cycle-machine-sizing, aircraft-electrical-load-analysis,
  aircraft-oxygen-system-sizing, apu-fuel-burn-sizing,
  avionics-bay-cooling-sizing, battery-sizing, bleed-air-system-sizing,
  brake-energy-sizing, cabin-outflow-valve-sizing, canard-sizing,
  cargo-compartment-sizing, control-surface-sizing, electrical-wire-sizing,
  emergency-exit-configuration, engine-sizing, environmental-control-sizing,
  fire-protection-sizing, fuel-feed-system-sizing, fuel-jettison-sizing,
  fuel-tank-inerting-sizing, fuel-tank-sizing, fuselage-sizing,
  hydraulic-actuator-sizing, hydraulic-system-sizing, ice-protection-sizing,
  landing-gear-layout, landing-gear-retraction-sizing, landing-gear-sizing,
  nacelle-sizing, propeller-sizing, ram-air-turbine-sizing, spoiler-sizing,
  tail-sizing, tire-sizing, v-tail-sizing, weight-estimation,
  window-aperture-sizing, wing-planform-sizing, ws-tw-trade.
- structures-integration 2: fuselage-skin-stringer, wing-box-sizing.

## Ranked GO candidate

### 1. vehicle-design/sizing/landing-gear-height-sizing (GO, rank 1)

Select the vertical landing gear geometry of a tricycle-gear aircraft at
the conceptual level: from the clearance constraints (the tail cone
lowest point must keep its ground clearance through the design rotation
attitude about the main gear contact, and the nacelle and propeller
lowest points must keep their minimum clearances at the level and
rotated attitudes), solve the required static ground line and the
corresponding main gear height, set the nose gear height so the cabin
waterline is level over the wheelbase, and report the clearance margins
and the height verdict. Deterministic stdlib trigonometry and statics in
the exact family convention of the landing-gear-layout sibling; no
empirical tables, no numeric integration, no vendor data. The layout
leaf takes every height as a given input and computes angles; this leaf
is the inverse, computing the heights from the required clearances. It
sits in sizing/ next to landing-gear-sizing (loads and stroke),
landing-gear-layout (angles and stations), and
landing-gear-retraction-sizing (mechanism), none of which touch the
vertical ground-line geometry.

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/ (real
output, EXIT=1 = no files):

```
$ grep -rilE "landing[- ]gear[- ]height|static[- ]ground[- ]line|main[- ]gear[- ]height|nose[- ]gear[- ]height|tail[- ]cone[- ]clearance|gear[- ]height[- ]selection|ground[- ]line[- ]height" skills/ eval/ --include="*.md" --include="*.py" | grep -v __pycache__
EXIT=1
```

Landing-gear-layout logic inventory (scripts/landing_gear_layout_logic.py)
is exactly five functions, all angle or load-fraction computations with
heights as inputs: tipback_angle(h_cg, x_mg, x_cg_aft),
tail_strike_clearance_angle(h_tail_contact, x_tail, x_mg),
lateral_turnover_angle(h_cg, track),
lateral_turnover_tricycle_angle(h_cg, x_cg, x_mg, x_ng, track),
nose_gear_static_load_fraction(x_cg, x_mg, x_ng). No function anywhere
derives a gear height or a static ground line from a clearance
requirement. Corpus token scan over all 1266 task blocks for
gear-height, static-ground-line, height-selection, ground-line,
main-gear-height, nose-gear-height, gear-height-selection: zero tasks
(empty scan).

(b) Nearest sibling fence quotes (read at HEAD, verbatim):

- skills/vehicle-design/sizing/landing-gear-layout/SKILL.md lines 30-37:
  "It pairs with vehicle-design/sizing/landing-gear-sizing, which sizes
  the strut loads and landing energy once the layout is fixed, and takes
  the CG travel limits as given inputs from
  vehicle-design/mass-properties/cg-envelope." The layout leaf also takes
  the vertical geometry as given: its workflow step 1 fixes "the tail cone
  lowest point station x_tail and contact height h_tail_contact, the CG
  height h_cg" as inputs, and the tail strike identity it implements is
  the angle check z(theta) = h_tail_contact * cos(theta) - a * sin(theta)
  vanishing at tan(theta_ts) = h_tail_contact / a. The height that makes
  that contact height adequate at the required rotation attitude is never
  solved.
- skills/vehicle-design/sizing/landing-gear-sizing/SKILL.md (scope):
  "static loads over the struts, nose and main gear load share from the
  CG and wheelbase, shock absorber stroke, and the tire rating margin"
  plus "FAR-25.723 / CS-25.723 shock absorption verification is a drop
  test; this module provides the sizing-level energy check only." No
  vertical geometry content.
- skills/vehicle-design/sizing/landing-gear-retraction-sizing/SKILL.md
  "Related leaves": "vehicle-design/sizing/landing-gear-sizing: the
  static strut demand at touchdown, the nose and main gear CG split and
  the shock absorber stroke; it sizes the gear before the mechanism, this
  leaf sizes how the gear retracts." Mechanism territory only.
- skills/vehicle-design/sizing/propeller-sizing/SKILL.md (pitfall,
  lines 132-137): "Sizing the diameter without the ground clearance: a
  large diameter that meets the blade-tip bound can still strike the
  ground in the takeoff attitude; run ground_clearance_check before
  fixing the diameter." That check is the propeller installation
  clearance at a GIVEN hub height (its worked anchor: "2.0 m diameter at
  1.6 m hub height gives 0.6 m of clearance"), not the aircraft gear
  height derivation.
- The aft-body geometry angle seam is separately owned: fuselage-sizing
  carries the aft-body upsweep check (corpus task fuselage-sizing-2
  "check the aft-body upsweep angle for the cargo door" routes there),
  which does not reach the gear height that sets the ground clearances.

(c) Standards-map id exists (grep-verified):

```
$ grep -n "id: far-25" standards-map.yaml
16:  - id: far-25
$ grep -n "id: cs-25" standards-map.yaml
27:  - id: cs-25
```

far-25 and cs-25 are the standing vehicle-design landing-gear family
convention (landing-gear-layout, landing-gear-sizing and
landing-gear-retraction-sizing all carry far-25 and cs-25 reference-only,
verified on disk), so the GO uses the same reference-only framing.

(d) Published closed-form anchor (summary-only, no standard text
reproduced): the conceptual-design landing gear vertical layout method:
gear height and static ground line are set so the tail cone clears the
ground at the required takeoff rotation attitude with margin and the
nacelle/propeller lowest points keep their clearances at the level and
rotated attitudes, with the nose gear height following from the level
waterline over the wheelbase. This is standard conceptual design
methodology as presented in Raymer, Aircraft Design: A Conceptual
Approach (landing gear chapter), Gudmundsson, General Aviation Aircraft
Design (landing gear design chapter), Sadraey, Aircraft Design: A
Systems Engineering Approach (landing gear chapter), and Torenbeek,
Synthesis of Subsonic Airplane Design, the same book family the sibling
landing-gear-layout leaf already paraphrases (its "standard conceptual
design methodology (name and paraphrase only)"). The computation is
deterministic trig geometry, chapter-continuous with the existing leaf,
no tables, no empiricism, no numeric integration. The minimum-clearance
values are design requirements given as inputs, exactly as the layout
leaf takes ROTATION_REF_DEG and the nose-fraction band as its reference
constants, so no fabricated-correlation risk.

(e) 2 wordable Hit@1 corpus queries carrying DISTINCTIVE hyphenated
tokens that route to this leaf without stealing existing corpus tasks
(the corpus scan shows zero tasks carrying landing-gear-height,
static-ground-line, tail-cone-clearance, or gear-height tokens; the
w42-landing-gear-layout tasks carry tipback-angle, lateral-turnover and
tail-strike-clearance-angle tokens; w43-vmu-determination carries
measured rotation-limit-speed tokens; propeller tasks carry
propeller-diameter, ground-clearance and blade-tip tokens; none carry the
height-selection tokens, so no theft):

1. "check the landing-gear-height of the tricycle transport at the
   conceptual level: solve the static-ground-line from the tail-cone
   clearance at the design rotation attitude and compute the
   main-gear-height and the nose-gear-height that level the cabin
   waterline over the wheelbase"
2. "select the landing-gear-height-sizing for the nosewheel aircraft:
   derive the required static-ground-line from the tail-cone-clearance
   margin at the rotation reference, then verify the nacelle ground
   clearance at the level and rotated attitudes and report the height
   verdict"

(f) No generic single-word tag overlap: proposed tags are hyphenated
compounds only: landing-gear-height-sizing, static-ground-line,
main-gear-height-selection, nose-gear-height-selection,
tail-cone-clearance, rotation-clearance-margin, waterline-leveling.
Prune generic single-word tags (gear, height, landing, clearance) since
the router rows for landing-gear-sizing, landing-gear-layout and
propeller-sizing already own the generic landing-gear and
ground-clearance surface (propeller-sizing carries the live tag
ground-clearance; do not reuse it). Build-time notes (wave-45 lesson):
add a fence line to landing-gear-layout ("gear height selection and the
static ground line from clearance constraints belong to the height-sizing
sibling"), a router row in skills/vehicle-design/SKILL.md beside the
landing-gear rows, and 2 corpus tasks at merge with the hyphenated
tokens above. Family spread: vehicle-design 55 to 56 after landing.

## Wave-45 declines re-verified FRESH at HEAD 45931c16 (all STAND)

| Wave-45 declined seam | Fresh re-verification evidence at this HEAD | Verdict |
|---|---|---|
| high-lift/flap sizing | aerodynamics/high-lift/high-lift-systems still owns flap clmax and slat/leading-edge increments; corpus flap/slat demand routes to aero leaves, 0 vehicle-design demand | Decline stands |
| winglet sizing | aerodynamics/wing-design/winglet-design still owns span-extension and induced-drag machinery | Decline stands |
| rotorcraft main-rotor sizing | flight-mechanics/performance/rotorcraft-main-rotor-sizing owns disk loading, solidity (corpus w42 tasks) | Decline stands |
| trim-tab sizing | fresh grep trim-tab/balance-tab/servo-tab/geared-tab/tab-hinge = 0 owners in skills/, 0 corpus hits; control-surface-sizing covers aileron/elevator/rudder area, hinge moment, deflection only | Decline stands |
| air-induction/inlet-duct sizing | 0 owners as a vehicle-design seam; nacelle-sizing owns inlet capture/highlight, bleed-air-system-sizing owns fixed-Mach duct diameter; S-duct corpus surface routes to aero fanno/rayleigh duct flow (w43-rayleigh-flow-1), not a VD air-induction seam | Decline stands |
| deep oleo/shock-strut internals | fresh grep oleo/shock-strut/gas-spring = 0 owners, 0 corpus; landing-gear-sizing fences the FAR-25.723 drop test out and gives the energy-level stroke only | Decline stands |
| thrust-reverser sizing | fresh grep thrust-reverser/reverser: corpus 0; the only skills/ owners are msg3-maintenance-analysis and development-assurance-levels (maintenance-task and hazard-list mentions, not sizing) | Decline stands |
| windshield/canopy aperture | fresh grep: the single canopy corpus hit is w21-entry-descent-landing-2 (space parachute canopy), not an aircraft windshield; window-aperture-sizing owns the flat circular pressurized pane; windshield heat 0 | Decline stands |
| refuel/defuel/fuel-vent | fresh grep refuel/defuel = 0 corpus (the two skills/ hits are a flying-qualities mention, not a fuel function); vent-line/surge-tank 0 owners 0 corpus; fuel-feed-system-sizing owns the vent-pressure term in its NPSH chain | Decline stands |
| full APU selection | fresh grep apu-selection/auxiliary-power-unit-selection = 0 owners, 0 corpus; apu-fuel-burn-sizing owns the burn-at-load-point only, full selection stays a vendor catalog | Decline stands |
| landing-gear spin-up/springback/side-load cases | fresh grep spin-up/springback = 0 corpus; structures/loads/landing-ground-loads owns the level/braked/tail-down/one-wheel reaction families | Decline stands |
| shimmy / gear-walk | fresh grep shimmy/gear-walk = 0 owners, 0 corpus; no clean closed-form anchor in the map-standard book set | Decline stands |
| nose-gear steering / turning-radius geometry | fresh grep steering-angle/turning-radius/nose-wheel-steering = 0 owners, 0 corpus; landing-gear-layout owns CG-envelope angles and does not reach steering kinematics | Decline stands |
| oleo gas-spring polytropic sizing | fresh grep oleo/gas-spring = 0 corpus; landing-gear-sizing owns stroke = v^2 / (2 n g) | Decline stands |
| multi-wheel bogie / articulated load sharing | tire-sizing owns per-tire load split, landing-gear-sizing the strut split; no separated corpus surface | Decline stands |
| fuel crossfeed / collector / scavenge | fresh grep crossfeed/scavenge = 0 owners, 0 corpus; fuel-feed-system-sizing owns the feed chain to NPSH | Decline stands |
| fuel pump selection beyond boost pump | fuel-feed-system-sizing owns boost pump pressure rise and power; full catalog selection is vendor data | Decline stands |
| S-duct / buried-inlet duct loss | fresh corpus S-duct surface is the aero w43-rayleigh-flow-1 duct-flow task; duct machinery owned (bleed-air fixed-Mach precedent); propulsion engine-airframe-integration owns installed losses | Decline stands |
| control-surface mass-balance weights | fresh grep mass-balance/balance-weight: corpus 0; the only skills/ mass-balance owners are propulsion cycle and rocket balance checks, not control surfaces; flutter balance is aero territory | Decline stands |
| product-of-inertia / principal-axis rotation | fresh grep: corpus 0; owners are gnc attitude-dynamics and structures shear-center, different demand class; inertia-estimation owns I = m k^2 and parallel-axis at the needed level | Decline stands |
| wing incidence / rigging angle | fresh grep wing-incidence/rigging-angle/incidence-angle = 0 owners, 0 corpus; aero wing-planform-design owns the geometry-side washout/stall sequencing | Decline stands |
| mechanical flight-control runs | fresh grep pushrod/control-cable/bellcrank = 0 real owners, 0 real corpus hits (the 4 corpus tokens are statistical process-control "control run" matches in cusum-ewma tasks); actuation chain owned by hydraulic-actuator-sizing and control-surface-sizing | Decline stands |
| gear doors / gear-bay fairing | gear-bay corpus surface is w35-landing-gear-retraction-sizing-2 (bay stowage fit) routing to the retraction leaf; doors stay fairing geometry without a closed-form anchor | Decline stands |
| pneumatic deicing boot / fluid deicing | fresh grep deicing-fluid/de-icing-fluid/type-i-fluid/pneumatic-boot = 0 owners, 0 corpus; ice-protection-sizing owns the thermal protection sizing | Decline stands |
| potable water / waste water | fresh grep potable/waste-water/toilet/galley: corpus 0; the electrical-load-analysis hits are galley electrical consumers, not water sizing | Decline stands |
| escape slide / evacuation system | fresh grep evacuation/escape-slide: corpus 0; emergency-exit-configuration owns exit geometry and credit rules; slide length is a sill-height correlation, not clean closed form | Decline stands |
| thrust-reverser / cascade geometry | corpus 0 and blocker-door/cascade turning is vendor geometry without a map-standard anchor | Decline stands |
| APU air inlet / exhaust duct | fresh grep apu-inlet/apu-exhaust = 0 owners, 0 corpus; duct machinery owned by the bleed-air fixed-Mach precedent; apu-fuel-burn-sizing owns the APU load chain | Decline stands |

## Fresh declines this probe (seams never named in the wave-45 receipt, one-line reasons)

| Candidate seam | One-line reason |
|---|---|
| circuit-breaker / protective-device sizing next to electrical-wire-sizing | 0 corpus demand; breaker ratings are standard-size vendor catalogs with no map-standard id in the 30-id map (no AS50881/SAE id), fabricated-catalog risk |
| LCN/ACN pavement classification | 0 corpus demand; no ICAO id in the 30-id standards map, pavement classification is table-gated, map-blocked |
| wing fuel volume check seam | Concept owned: corpus w25 fuel-tank tasks route usable-fuel-volume versus wing-box tank capacity to fuel-tank-sizing |
| propeller governor sizing | 0 corpus demand; constant-speed governor design is propulsion/FM control machinery, no clean closed-form anchor in the vehicle-design book set |
| fuel system icing inhibitor (FSII) dosing | 0 corpus demand; additive proportioning is a fuel-spec lookup with no map id |
| cargo smoke detection / engine fire detection loop | 0 corpus demand; detector coverage and loop length are not clean closed form; fire-protection-sizing owns the extinguishing agent side |
| rain repellent / windshield wipers | 0 corpus demand; no closed-form anchor in the map-standard book set |
| cabin air distribution ducting | 0 corpus demand; duct-flow machinery already owned by bleed-air-system-sizing (fixed-Mach duct precedent); distribution architecture is not station-level deterministic |
| static wicks / antenna count and placement | 0 corpus demand; no deterministic sizing method in the map-standard book set |
| tire creep / blowout protection | 0 corpus demand; no closed-form anchor; tire-sizing owns dimensions, pressure and footprint |
| cabin window spacing / window pitch | 0 corpus demand; window pitch follows frame pitch and seat layout, no clean closed-form anchor; window-aperture-sizing owns the pane stress side |
| fuselage frame spacing | Owned: corpus fss1/fss2 route frame-pitch from the column-buckling length to fuselage-skin-stringer |
| seat track / overhead bin sizing | 0 corpus demand; layout heuristic, no deterministic anchor |
| cargo tie-down / restraint fitting layout | 0 corpus demand; fitting layout is not clean closed form, no map-standard method |
| pressurization trim air seam | Owned: bleed-air-system-sizing rolls up "pressurization trim flow" as a fixed consumer |
| hydraulic thermal relief valve | 0 corpus demand; the cabin pressure-relief valve surface is owned by cabin-outflow-valve-sizing (8.9 psi clamp) and is a different system; hydraulic relief is not clean closed form |
| elevator artificial feel / tab feel | 0 corpus demand; flight-control feel is FTO structural-coupling-test-adjacent and FM territory, no clean anchor |
| tail cone / aft-body upsweep angle | Owned: corpus fuselage-sizing-2 routes the aft-body upsweep check to fuselage-sizing |
| wing dihedral / washout selection | Owned on both sides: openvsp-geometry takes them as parametric inputs, aerodynamics wing-planform-design owns the geometry side |
| lightning protection zonal analysis | Owned: avionics do160 lightning-protection leaf plus corpus demand routes there |
| radome structural/thermal sizing | Owners in structures (bird-strike) and aero (stagnation-flow boundary layer, corpus w41 task); no vehicle-design home and no clean seam |
| engine mount / pylon | Owned: propulsion engine-airframe-integration (corpus w16-engine-airframe-integration-2 pylon drag task) plus nacelle-sizing pylon bookkeeping |
| landing gear height seam alternative reads (three-point attitude, tail-down gear) | Subsumed by the rank-1 GO above; the vertical-geometry family is one seam, not several |

## Closed veins (fresh confirmations)

- Landing gear: stations, track and the three layout angles
  (landing-gear-layout, heights as given inputs), loads and stroke
  (landing-gear-sizing), mechanism and locks and bay stowage
  (landing-gear-retraction-sizing), tires (tire-sizing), brakes
  (brake-energy-sizing), certification reaction families (structures
  landing-ground-loads), and the measured vmu tail strike check (FTO
  vmu-determination). The one remaining clean sub-seam, the vertical
  ground-line geometry from clearance constraints, is the rank-1 GO
  above; spin-up/springback/shimmy/steering/oleo-internals stay closed
  with zero demand.
- Fuel system: volume and ullage, feed loss and NPSH with boost pump,
  jettison rate and mast split, inerting washout, APU burn all owned;
  vent/refuel/crossfeed/scavenge/pump-catalog seams add no corpus
  surface.
- Systems sizing: the 39-leaf sizing pack plus the conceptual, cost,
  mass-properties, mdo and structures-integration packs leave no clean
  closed-form seam this probe could find beyond the ranked GO; the
  fresh-declines rows above document every seam examined this wave.
- Corpus note: 112 vehicle-design-targeted tasks serve all 55 leaves, so
  this probe adds no existing-corpus demand counter-evidence; the GO
  brings its own 2 corpus tasks at merge.

## Standards-map check

30 ids present in standards-map.yaml (verified by grep at HEAD):
arinc-429, arinc-664, arp4754a, arp4761a, as9100, as9102, asme-y14-5,
cmh-17, cs-25, do-160, do-178c, do-254, do-330, ecss, far-107, far-25,
far-29, far-33, itar-ear, mil-std-1553, mil-std-1797a, mmpsd, msg-3,
naca-tn-902, naca-tr-824, nas-410, rtca-do-185, rtca-do-229,
rtca-do-260b, sep-2640. No icao, no as50881, no sae ids (LCN/ACN and
breaker seams stay map-blocked). The rank-1 GO uses far-25 and cs-25
reference-only per the landing-gear family convention.

## Method note

All greps and scans above were read-only terminal/search_files runs at
HEAD 45931c16. Helper scripts lived in the session temp dir (corpus
parser recovered 1266/1266 task blocks with id, query, intent and
expected_skill, so every token-demand count is a complete-file scan).
Family enumeration and router parity re-verified by find and grep. No
repo file was modified except this receipt. This receipt contains no em
dashes and no machine-local absolute paths.
