# WAVE-49 VEHICLE-DESIGN FAMILY PROBE RECEIPT (task-1, whole-family FRESH)

- Repo: the AeroSkills repo (local checkout; same tree as
  company-ops/aero-agent-skills). Probe HEAD: 9c2b3fe4 ("ops: stage
  wave-49 brief (655 baseline, daylight gate 11:45 UTC)"), verified via
  git log --oneline -1. Working tree clean before and after; the only
  write of this probe is this receipt.
- Scope: ENTIRE vehicle-design family probed FRESH at wave-49 HEAD.
  Read-only probe: no git writes, no edits to skills/, eval/,
  standards-map.yaml, scripts/, docs/, ops/automation briefs. One write
  only: this receipt.
- Prior receipt read in full first:
  ops/automation/state/wave48-recon/task-4-receipt.md (wave-48
  vehicle-design probe, HEAD 92d84a48). Its two ranked GOs -
  vehicle-design/sizing/landing-gear-weight-estimation and
  vehicle-design/sizing/fuel-system-weight-estimation - LANDED in
  wave-48; this probe re-verifies every wave-48 decline FRESH at the new
  HEAD and probes the seams the two landings newly fence.
- Family delta since wave-48: +2 leaves =
  skills/vehicle-design/sizing/landing-gear-weight-estimation and
  skills/vehicle-design/sizing/fuel-system-weight-estimation (SKILL.md
  + scripts on disk, 2 corpus rows each:
  w48-landing-gear-weight-estimation-1/2,
  w48-fuel-system-weight-estimation-1/2 in eval/hit1-corpus.yaml,
  verified below).

## Census (fresh at HEAD 9c2b3fe4)

- find skills/vehicle-design -mindepth 3 -name SKILL.md = 59 leaves
  (family router skills/vehicle-design/SKILL.md at -mindepth 1 is the
  +1 router file). Packs: conceptual 5, cost-estimation 3,
  mass-properties 3, mdo 3, sizing 43, structures-integration 2 = 59.
- vehicle-design router table rows = 59 = leaves (parity, grep '^|
  vehicle-design/' = 59). Router guidance bullets 180-181 fence the two
  new weight leaves against the gear and fuel design surfaces.
- eval/hit1-corpus.yaml: 1326 task blocks parsed (1326/1326).
  vehicle-design inventory: 120 rows over 59 distinct targets,
  set-identical to the 59 disk leaves (0 orphans, 0 unserved, script
  check). Family fully corpus-served; any GO adds its own 2 tasks at
  merge per wave convention.
- Repo baseline: 655 leaves, 86 packs, 12 families, 1326 corpus tasks,
  30 standards ids in standards-map.yaml (grep '^  - id:' = 30).

## Verdict: NO_CANDIDATES

The two wave-48 GOs landed and closed the last open class-II group
weight producer seams in the weight chain (landing gear group, fuel
system group). Every seam the wave-49 brief names as the family's
growth area was probed FRESH at this HEAD: wing-group-weight (OWNED by
the wave-47 component-weight-estimation four-group claim),
systems-weight and fixed-equipment weight (ZERO owners, ZERO corpus,
standing band-data decline re-verified), CG-envelope (OWNED by
mass-properties/cg-envelope), the two new leaves' fenced variants
(kneeling and reciprocating-installation gear, avgas and
non-integral-tank fuel: ZERO real corpus demand, GA side map-blocked,
no far-23 id), configuration and layout variants (canard group weight
and V-tail group weight: zero-owner but zero anchor and zero corpus,
geometry seams owned by canard-sizing and v-tail-sizing),
structural-loads interface (V-n envelope OWNED by
structures/loads/gust-maneuver-loads; design load factor is a given
input to wing-box-sizing and constraint-analysis), and performance
sizing (takeoff and landing field length, climb and balanced field
OWNED in flight-mechanics performance plus the VD matching chart
leaves). No zero-owner + corpus-absent + unfenced + anchored candidate
found. No GO this wave.

## Seam receipts (all evidence fresh at HEAD 9c2b3fe4)

| Candidate seam (brief-named) | Fresh evidence this session | Verdict / reason |
|---|---|---|
| wing-group-weight as a standalone leaf | OWNED: skills/vehicle-design/sizing/component-weight-estimation/SKILL.md line 3 claims the four airframe structural groups with the wing-group-weight regression as its first equation; tags line 18 include wing-group-weight; corpus rows w47-component-weight-estimation-1/2 (corpus lines 5753-5778) route wing-group-weight and fuselage-group-weight language to it | OWNED; no seam |
| systems-weight / fixed-equipment class-II predictor | ZERO owners in skills/ (grep systems-weight-estimation, fixed-equipment-weight, equipment-group-weight, systems group weight = 0 files) and ZERO corpus rows (same tokens = 0); wave-48 declined as band-data heuristic with the class-I fraction surface split across tow-estimation, weight-estimation and mass-budget; nothing changed in that surface since (only the two group-weight GOs landed) | DECLINE (standing wave-48 decline re-verified FRESH) |
| CG-envelope | OWNED: skills/vehicle-design/mass-properties/cg-envelope/SKILL.md (derives cg station, checks operating cg against forward and aft limits, tests points against the envelope polygon); corpus serves it | OWNED; no seam |
| kneeling-gear and reciprocating-installation gear weight variants (fenced out of the new landing-gear leaf) | The new leaf (line 61) states "kneeling-gear and reciprocating-engine variants are outside this leaf's claim" (K_mp and K_np factors folded into the leading constants at 1.0). Corpus real demand: kneeling = 0 rows (the single grep hit is a false positive in a wave-46 leaf-list comment listing propulsion reciprocating leaves, not a gear task); skills/ tree-wide kneeling-gear weight owners = 0 | DECLINE (zero demand, factor-variant of an equation the sibling already implements; no separate corpus pull) |
| avgas / general-aviation fuel system weight (specific weight 5.87 fenced out of the new fuel leaf) | The new fuel leaf (line 181) fences the aviation gasoline value 5.87 out of its JP-4/Jet-A 6.55 claim. Corpus avgas / general-aviation fuel weight / bladder-tank demand = 0; skills/ GA fuel weight owners = 0; standards-map.yaml has NO far-23 id (30-id map: far-25, far-29, far-33 only) | DECLINE (zero demand + map-blocked for GA certification framing) |
| non-integral / bladder tank fuel system weight | Corpus 0, skills owners 0 (same battery as above); no clean closed-form anchor distinct from the integral-tank Torenbeek method the sibling implements | DECLINE (zero demand, no distinct anchor) |
| canard group weight (canard-config airframe group mass) | ZERO owners tree-wide (grep canard group weight / canard group mass over skills/ + eval/ = 0 files); corpus canard rows are the w29-canard-sizing-1/2 geometry and stall-precedence tasks only; canard-sizing owns the area and trim surface; no published canard group regression distinct from the horizontal-tail form in the map-standard book set the siblings paraphrase | DECLINE (zero corpus, no clean distinct anchor) |
| V-tail group weight | v-tail-sizing (wave-41) owns the equivalent-area conversion of the V-tail to horizontal and vertical tail requirements; component-weight-estimation's tail regressions then apply to those equivalent areas, so the weight identity is split across the two siblings with no distinct published V-tail regression; corpus v-tail rows route to v-tail-sizing geometry only | DECLINE (split identity, zero corpus, no distinct anchor) |
| structural-loads interface (V-n envelope, design load factor selection, gust and maneuver lines) | OWNED outside the family: skills/structures/loads/gust-maneuver-loads/SKILL.md line 3 claims V-n diagram construction, corner point at VA, gust lines at VB/VC/VD, FAR 25.337 limit maneuvering load factor and FAR 25.341 discrete gust per its tags; wing-box-sizing and component-weight-estimation take the load factor n as a given input (wing-box-sizing line 32) | OWNED (structures family); no seam |
| landing gear strut length producer (input to the new weight leaf) | Strut lengths L_m and L_n are design geometry inputs to the landed regression; landing-gear-height-sizing produces gear heights and landing-gear-layout takes heights as given; corpus demand for a strut-length selection leaf = 0 | DECLINE (input geometry, zero demand) |
| control-surface / flight-control-system group weight | wave-46/48 declines re-verified FRESH: control-surface-sizing owns areas, hinge moments and deflections; corpus control-surface rows route there; FCS group weight tokens = 0 owners, 0 corpus | DECLINE (standing) |
| takeoff / landing field length and climb sizing seams | OWNED in flight-mechanics/performance (takeoff-performance, landing-performance, balanced-field-length, climb-performance, oei-climb-gradient) plus FTO performance determination leaves and the VD matching chart (constraint-analysis, ws-tw-trade) which consume them as constraints; corpus routes field-length tasks to FM and FTO leaves (corpus lines 1217-1223, 2075-2079, 4964-4968) | OWNED (flight-mechanics / FTO); no seam |
| stall speed producer (input to the new gear regression V_s term) | Split-owned across aerodynamics/high-lift/high-lift-systems (V_stall = sqrt(2 W / (rho S CLmax)), line 52), flight-mechanics landing and takeoff performance (V_s from wing loading, landing-performance line 32), FTO v-speeds and stall-speed-determination; no VD standalone seam with corpus pull | DECLINE (split-owned) |
| three-surface / tandem / box-wing / blended-wing configuration sizing | ZERO owners (skills/ hits only in systems-engineering-safety certification-basis prose and canard-sizing), corpus = 0 rows; no deterministic closed-form anchor in the map-standard conceptual design book set | DECLINE (zero demand, zero anchor) |
| OWE / zero-fuel weight / MZFW relations | ZERO owners, ZERO corpus (fresh grep); class-data band relations without a deterministic closed-form anchor; wave-47 decline re-verified | DECLINE (standing) |

## Closed veins (re-verified fresh at HEAD 9c2b3fe4)

- Weight chain: four airframe structural group regressions (wave-47
  component-weight-estimation), landing gear group (wave-48), fuel
  system group (wave-48), installed engine weight (engine-sizing W_eng
  = T_SL / (T/W)_eng), class-I fraction iteration (tow-estimation),
  moments and CG and band checks (weight-estimation), subsystem rollup
  (mass-budget), CG polygon (cg-envelope), inertia (inertia-estimation).
  Consumers take component weights as given; every producer position
  the wave-47 spec fence named (landing gear, fuel, installed engines)
  is now landed or owned. Systems and fixed equipment stay closed under
  the band-data decline. Closed.
- Landing gear design: layout angles and fractions, static loads and
  stroke, retraction mechanism and bay stowage, vertical ground line
  and heights, tires, brakes, certification reaction families, gear
  group weight all owned. Spin-up/springback, shimmy, steering, oleo
  internals, kneeling and reciprocating variants stay closed (zero
  corpus, zero anchor or factor-variant). Closed.
- Fuel system: volume and ullage, feed hydraulics to NPSH, jettison,
  inerting, APU burn, fuel system group weight all owned. Vent, refuel,
  crossfeed, scavenge, avgas and bladder variants stay closed. Closed.
- Structural loads: V-n envelope and gust and maneuver load factors are
  structures-family owned (gust-maneuver-loads); landing ground load
  reaction families are structures-owned (landing-ground-loads). The
  VD structures-integration pack (fuselage-skin-stringer,
  wing-box-sizing) consumes loads as given. Closed.
- Performance sizing: field length, climb, balanced field, energy
  height owned in flight-mechanics and FTO; the VD matching chart
  (constraint-analysis, ws-tw-trade) owns the constraint surface.
  Closed.
- Corpus note: 120 vehicle-design-targeted tasks serve all 59 leaves
  (2 per leaf, 2 extras); no existing task points into any gap probed
  above; every decline above is backed by a fresh zero-owner and
  zero-corpus scan at this HEAD.

## Standards-map check

30 ids present in standards-map.yaml (grep-verified at HEAD): arinc-429,
arinc-664, arp4754a, arp4761a, as9100, as9102, asme-y14-5, cmh-17,
cs-25, do-160, do-178c, do-254, do-330, ecss, far-107, far-25, far-29,
far-33, itar-ear, mil-std-1553, mil-std-1797a, mmpsd, msg-3,
naca-tn-902, naca-tr-824, nas-410, rtca-do-185, rtca-do-229,
rtca-do-260b, sep-2640. No far-23, no icao, no faa-ac id (the avgas and
GA-framed seams stay map-blocked). The two landed GOs carry far-25 and
cs-25 reference-only per the family convention; no candidate this wave
requires a new id.

## Method note

All greps and reads above were read-only runs at HEAD 9c2b3fe4.
Corpus scans covered all 1326 task blocks (id/query/intent/
expected_skill); the set-identity check (120 vehicle-design rows over
59 distinct targets against 59 disk leaves) was a script run in the
session temp dir. Family enumeration and router parity re-verified by
find and grep. Wave-48 receipt read in full first; every wave-48
decline named there was re-derived FRESH where the brief names the
seam, and the wave-46/47 standing declines were spot re-verified with
the same zero-owner zero-corpus batteries. No repo file modified except
this receipt. This receipt contains no em dashes and no machine-local
absolute paths.
