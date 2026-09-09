# WAVE-49 PROPULSION PROBE RECEIPT (task-4, whole-family FRESH)

- Repo: the AeroSkills repo at ~/AeroSkills, probed FRESH at HEAD
  `9c2b3fe4` (verified `git rev-parse HEAD`; `git log --oneline -1` =
  "ops: stage wave-49 brief (655 baseline, daylight gate 11:45 UTC)").
  Working tree clean apart from this untracked receipt dir (`git status
  --short` shows only `?? ops/automation/state/wave49-recon/`). Read-only
  probe: the one write is this receipt.
- Baseline re-verified at HEAD: 655 leaves, 86 packs, 12 families, 1326
  corpus tasks (eval/hit1-corpus.yaml), 30 standards-map ids, 667 SKILL.md
  = 655 leaves + 12 family routers (all counted from disk this probe:
  `find skills -mindepth 3 -name SKILL.md` = 655; depth-2 routers = 12;
  `find skills -name SKILL.md | wc -l` = 667; `find skills -mindepth 2
  -maxdepth 2 -type d` = 86 packs).
- Scope (wave-49 brief item 5): ENTIRE propulsion family, 54 leaves / 11
  packs, probed FRESH because wave-48 landed ONE leaf
  (reciprocating/dual-cycle). Scramjet CLOSED DEFINITIVELY, not re-opened.
  Focus: reciprocating/station-level producers only; check what remains
  after dual-cycle lands (engine-performance station models, turbomachinery
  stage-level, gas-turbine off-design, propellers, inlets/nozzles, cycle
  analysis). Wave-48 receipt read in full first
  (ops/automation/state/wave48-recon/task-2-receipt.md).
- Family diff wave-48 probe HEAD (92d84a48) to wave-49 HEAD (9c2b3fe4),
  restricted to skills/: exactly the dual-cycle landing (3b9bddfb: leaf
  SKILL.md + logic + test + eval fragment) and the wave-48 close
  (97b98aca). Since the wave-48 close state (5b112816), the ONLY repo
  change is the staged brief (git diff 5b112816 HEAD --stat = 1 file, the
  brief). No other ownership change anywhere in the family; every decline
  row below was re-probed FRESH at HEAD with real greps, not from memory.
- Census at HEAD (54 leaves / 11 packs): axial-compressor 6, combustion 1,
  electric 4, engine-airframe 1, gas-turbine-cycle 10, ramjet 2,
  reciprocating 3 (piston-engine-cycle Otto + diesel-cycle Diesel +
  dual-cycle Sabathe/dual), rocket 18, turbofan 5, turbomachinery 2,
  turboprop 2. Router parity (`grep -c '^| propulsion/'
  skills/propulsion/SKILL.md`) = 54 == 54. Corpus parity: 108 propulsion
  tasks == 54 x 2; 54 distinct expected_skill targets == 54 tree leaves
  (comm on sorted lists: zero orphans each way); every leaf has exactly 2
  tasks; dual-cycle's own 2 tasks are eval/hit1-corpus.yaml ids
  w48-dual-cycle-1/-2 (lines 5867, 5871).

## Verdict

**NO_CANDIDATES.** The wave-48 GO (dual-cycle) landed and completed the
reciprocating air-standard cycle triad (Otto / Diesel / dual), exactly the
condition under which the wave-48 receipt instructed the planner to declare
that triad COMPLETE. Every remaining seam in the family, re-probed FRESH at
HEAD with tree-wide and corpus greps this probe, is either owned by an
existing leaf ([b] sibling fence), corpus-absent with no deterministic
closed-form anchor beyond an owned model ([d][c]), or closed
definitively (scramjet). No new zero-owner, corpus-absent, sibling-clear
skill-leaf candidate exists at HEAD. Full decline rows with fresh evidence
below; the previously open piston altitude-lapse quality finding remains an
in-place fix, NOT a new leaf.

## Focus seams (wave-49 brief item 5), fresh at HEAD

1. Reciprocating remainder after dual-cycle. The three air-standard
   reciprocating cycles now OWN the pack (piston-engine-cycle Otto
   constant-volume, diesel-cycle Diesel constant-pressure, dual-cycle
   mixed Sabathe with the alpha/rho heat-addition split). Re-probed
   candidates, all 0 files in skills/ + eval/, all corpus 0 (fresh greps):
   two-stroke/port-timing/scavenging (only false positive: the word
   "trapping" inside manufacturing-quality/ndt/thermography logic, a
   thermal-context false hit — classified, not a propulsion token);
   wankel/rotary-engine; atkinson/miller/over-expansion (automotive
   powertrain cycles, wave-48 [d][c] row stands); opposed-piston /
   free-piston (never adjudicated before wave-49, probed fresh: 0 files,
   0 corpus — over-expansion/uniflow scavenging identity reduces to owned
   two-stroke-scavenging empirics + Otto/Diesel ceilings, no distinct
   standards anchor). Piston altitude/power-lapse remains an OPEN QUALITY
   FINDING, fix in place: corpus task w46-piston-engine-cycle-2 (line
   5742, verbatim re-read) still binds "brake-horsepower at altitude from
   the sea-level rating with the density-ratio power lapse" to
   piston-engine-cycle, and the piston module function list re-read at
   HEAD (grep 'def ' scripts/piston_engine_cycle_logic.py) still has NO
   altitude/lapse function — wave-47/48 finding stands OPEN; same check on
   the diesel module (function list re-read): no lapse function either.
   NOT a new leaf (token collision on the bound task). Wave-48
   recommendation stands: declare the reciprocating air-standard triad
   COMPLETE.
2. Engine-performance station models. Probed fresh: 'engine-deck',
   'thrust-lapse', 'rating-table', 'performance-map', 'engine-performance-
   model', 'station-model' — zero unowned producers. Owners verified at
   HEAD: turbofan-off-design (corrected flow/spool, altitude thrust, ram
   drag, cruise SFC, throttle rating), engine-airframe-integration
   (installed thrust, intake momentum drag, bleed, thrust-drag
   bookkeeping), vehicle-design/sizing/engine-sizing (sea-level static
   thrust from T/W, ISA density-ratio lapse to top of climb — cross-family
   owner of the lapse identity), gas-turbine-cycle leaves own the
   cycle-level station chains. Corpus: thrust-lapse token routes only to
   vehicle-design engine-sizing and flight-mechanics point-mass tasks;
   no corpus task routes to an unowned engine-performance station.
3. Turbomachinery stage-level. Owners verified at HEAD unchanged:
   axial-compressor-stage + multi-stage-compressor + polytropic-efficiency
   (compressor stage math, velocity triangles, reaction, reheat factor),
   turbine-stage (axial turbine: stage loading, flow coefficient,
   reaction, blade row losses — desc re-read quotes "single axial turbine
   stage"), centrifugal-compressor (radial stage: impeller tip speed,
   Wiesner slip factor, work input coefficient), rocket-turbopump, plus
   free-turbine power-turbine matching in turboprop. Fresh candidates
   probed: radial-inflow/centrifugal-turbine stage, vaned diffuser, scroll
   volute — 0 files in skills/ + eval/, corpus 0; radial/centrifugal
   turbine station math is empirical map/geometry territory already fenced
   by centrifugal-compressor (radial-stage impeller math) and free-turbine
   (power-turbine wording); wave-43 engine-matching closure stands; no
   distinct deterministic identity, no corpus demand.
4. Gas-turbine off-design (non-turbofan). turbofan-off-design owns the
   corrected-flow/rating bookkeeping (desc re-read). Turbojet off-design
   was DECLINED wave-46 [needs component-map matching — the closed
   wave-43 engine-matching vein]; engine-matching/component-map coupling
   CLOSED. Fresh: no unowned off-design station producer; corpus 0 for any
   turbojet-off-design token.
5. Propellers. Owners verified fresh: turboprop-cycle (propeller/Froude
   efficiency, static thrust, equivalent shaft power, advance ratio, power
   and thrust coefficients — desc re-read), free-turbine (gearbox ratio,
   power-turbine matching, turboshaft wording — router row re-read),
   vehicle-design/sizing/propeller-sizing (propeller GEOMETRY: diameter
   from tip constraint, blade count, chord from solidity/activity factor,
   disk loading, operating point at advance ratio — desc re-read),
   engine-airframe-integration (installed thrust-drag). Propeller
   blade-element/induced-velocity/map tokens: fixed-wing BEMT lives in
   flight-mechanics rotorcraft-blade-element-hover-performance and
   rotorcraft-forward-flight-flapping (rotor, not propeller);
   vehicle-design propeller-sizing owns the fixed-wing geometry slot;
   ducted-fan/shrouded-propeller declined wave-45 (composition). No
   unowned propeller station identity.
6. Inlets/nozzles. subsonic-inlet-recovery owns ram recovery/capture
   area/spillage (desc re-read); ramjet-inlet owns supersonic recovery +
   Kantrowitz starting; aerodynamics oblique-shock + regular-shock-
   reflection own the shock math (cross-family, referenced by ramjet-inlet
   per wave-45 row); propelling-nozzle owns the gas-turbine nozzle station
   (choked/unchoked, throat area, gross thrust); rocket nozzle suite owns
   the rocket side (nozzle-design, area-ratio-selection, divergence-loss,
   flow-separation); mixed-flow-exhaust owns the turbofan mixer. Fresh
   probes: external/mixed-compression multi-shock intakes (0 unowned
   files; corpus tokens route to aerodynamics oblique-shock leaves —
   composition decline wave-45 stands), variable-area nozzle / thrust
   reverser / vectoring nozzle (0 files in propulsion; closed on empirics
   wave-46/47), inlet starting/bleed (0 unowned). No new candidate.
7. Cycle analysis (whole-family sweep). Every air-standard/gas-turbine
   cycle slot is owned: gas-turbine-cycle (Brayton), turbojet-cycle,
   turbofan-cycle + design-point + bypass-ratio-trade, turboprop-cycle,
   ramjet-cycle, real-cycle-effects, afterburner/intercooled/regenerative
   cycles, brayton-optimum-pressure-ratio, and the reciprocating triad
   Otto/Diesel/dual. Fresh probes for unowned cycle classes: ericsson /
   stirling / humphrey / pulsejet / lenoir (0 files, corpus 0 — no
   aircraft anchor, wave-48 [d] style); pulse-detonation / rotating
   detonation (only substring false positives: 'rde' inside "order" in
   manufacturing-quality key-characteristic-management logic — classified;
   0 real files, corpus 0); turbo-compound / power-recovery turbine
   (0 files, corpus 0 — composes owned reciprocating + turbine identities,
   no corpus demand); hydrogen/ammonia/SAF-fueled combustion (0 files,
   corpus 0 — no standards-map id, empirical/fuel-property territory);
   turboshaft-cycle wording owned by free-turbine (corpus ft2 task binds
   "turboshaft ... reduction gearbox ... flow function" to free-turbine,
   line 2013). Scramjet CLOSED DEFINITIVELY: 'scramjet' 0 files under
   skills/ (sole hits are cross-cutting/export-control ITAR/EAR reference
   text, not a propulsion owner) and 0 corpus lines.

## Declines table (whole family, fresh probes at HEAD; gates in brackets)

| Seam probed | Verdict | Evidence (fresh at HEAD) |
|---|---|---|
| reciprocating air-standard cycle remainder (two-stroke, wankel/rotary, atkinson/miller, opposed-piston/free-piston) | DECLINE [d][c] | All 0 files skills/ + eval/, corpus 0 (fresh greps this probe; thermography "trapping" false positive classified). Two-stroke scavenging/charging is empirical chart data; wankel geometry empirics; atkinson/miller automotive with no aviation anchor; opposed-piston reduces to owned cycle ceilings + uniflow scavenging empirics. Triad Otto/Diesel/dual COMPLETE — declare it so (wave-48 direction) |
| piston altitude / power lapse (wave-47/48 open quality finding) | DECLINE (in-place fix, OPEN) | Corpus w46-piston-engine-cycle-2 (line 5742) still binds density-ratio power lapse to piston-engine-cycle; piston AND diesel module function lists re-read at HEAD — no lapse function in either. Fix in place; NOT a new leaf |
| engine-performance station models / engine deck | DECLINE [b] | turbofan-off-design, engine-airframe-integration, vehicle-design engine-sizing (cross-family lapse owner), gas-turbine-cycle station chains own every station/rating identity; no unowned producer; corpus routes lapse only to owned vehicle-design/FM leaves |
| turbomachinery stage-level extras (radial/centrifugal turbine stage, vaned diffuser, scroll) | DECLINE [b][d] | axial-compressor-stage/turbine-stage/multi-stage/centrifugal-compressor/free-turbine own the stage math; radial turbine station is empirical-map/geometry territory; corpus 0; wave-43 matching closure stands |
| gas-turbine off-design (non-turbofan) | DECLINE [b] | turbofan-off-design owns corrected-flow/rating; turbojet off-design needs component maps — closed wave-43/46 |
| propellers (fixed-wing BEMT, induced velocity, propeller map) | DECLINE [b] | turboprop-cycle (eff/coeff/advance-ratio), vehicle-design propeller-sizing (geometry), free-turbine (gearbox), engine-airframe (installed); rotor BEMT is flight-mechanics rotorcraft-owned; no unowned propeller identity |
| inlets/nozzles (external/mixed compression, variable-area nozzle, thrust reverser, starting/bleed) | DECLINE [b] | subsonic-inlet-recovery + ramjet-inlet + aerodynamics shock leaves + propelling-nozzle + rocket nozzle suite + mixed-flow-exhaust own the stations; variable-area/reverser empirical (closed wave-46/47); composition declines stand |
| cycle analysis extras (ericsson/stirling/humphrey/pulsejet, pulse/rotating detonation, turbo-compound, SAF/hydrogen) | DECLINE [d][c] | 0 files skills/ + eval/, corpus 0 (fresh greps; 'rde' substring false positives classified); no closed-form anchor beyond owned cycles, no corpus demand, no distinct standards id |
| turboshaft wording / free-turbine extras | DECLINE [b] | free-turbine owns power-turbine matching + turboshaft (router row + desc re-read); corpus ft2 binds turboshaft gearbox/flow-function to free-turbine (line 2013) |
| scramjet + scramjet-adjacent | CLOSED DEFINITIVELY | scramjet 0 files under skills/ (export-control reference text only), corpus 0; wave-40/41/46/47/48 closure stands, not re-opened |

## Closed veins (re-verified fresh at HEAD)

- Scramjet and scramjet-adjacent: CLOSED DEFINITIVELY (do not re-open).
- Component engine matching / off-design map coupling: CLOSED (wave-43);
  corrected-flow/rating bookkeeping owned by turbofan-off-design.
- Reciprocating pack map after this probe: piston-engine-cycle (Otto),
  diesel-cycle (Diesel), dual-cycle (Sabathe mixed) — the air-standard
  triad is COMPLETE; remaining reciprocating seams (two-stroke gas
  exchange, rotary geometry, atkinson/miller, opposed-piston) close on
  empirics/scope as tabled. RECOMMENDATION for the planner: record the
  triad-complete declaration at close-out so later waves stop re-mining
  the reciprocating textbook-cycle map (wave-48 direction, now
  executable). Piston altitude-lapse quality finding remains open as an
  in-place fix (task wording or in-leaf density-ratio lapse extension).

## Standards-map check

- 30 ids at HEAD (`grep -c '^  - id:' standards-map.yaml` = 30). No GO,
  so no id consumed; far-33 present at line 193 for reference. Any future
  reciprocating/turbine station leaf would reuse far-33 reference-only
  per pack convention — no new id needed, none invented.

## Method and honesty notes

- Read-only probe: no git writes, no edits to skills/, eval/, scripts/,
  Makefile, standards-map.yaml, or wave briefs; the only repo write is
  this receipt. git status before/after shows only `?? ops/automation/
  state/wave49-recon/`.
- All greps, fence quotes, function lists, parity counts and corpus rows
  executed at HEAD 9c2b3fe4 and quoted from real output; no values taken
  from memory. Substring false positives (thermography "trapping",
  key-characteristic "rde" in "order") were individually classified, not
  counted as hits.
- No machine-local absolute paths anywhere in this file; repo referenced
  only as ~/AeroSkills or repo-relative paths (publish tripwire
  respected).
