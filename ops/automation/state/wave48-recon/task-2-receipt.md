# WAVE-48 PROPULSION PROBE RECEIPT (task-2, whole-family FRESH)

- Repo: the AeroSkills repo at ~/AeroSkills, probed FRESH at HEAD
  `92d84a48` (verified `git log --oneline -1` = "ops: stage wave-48 brief
  (planning only — daylight dispatch 10:00 CEST)"). Working tree clean
  apart from this untracked receipt dir (git status before/after shows
  only `?? ops/automation/state/wave48-recon/`). Read-only probe: the one
  write is this receipt.
- Baseline re-verified at HEAD: 645 leaves, 86 packs, 12 families, 1306
  corpus tasks (eval/hit1-corpus.yaml), 30 standards-map ids, 657 SKILL.md
  = 645 leaves + 12 family routers (all counted from disk this probe:
  `find skills -mindepth 3 -name SKILL.md` = 645; family routers at depth
  2 = 12; 645 + 12 = 657).
- Scope (wave-48 brief item 3): ENTIRE propulsion family, 53 leaves / 11
  packs, probed FRESH because wave-47 landed ONE leaf
  (reciprocating/diesel-cycle). Scramjet CLOSED DEFINITIVELY, not re-opened
  (scramjet token still 0 files under skills/ at HEAD). Focus seams per
  brief: reciprocating/station-level producers only.
- Baseline receipts read first: wave47-recon/task-2-receipt.md (whole-family
  FRESH at a4ae6d1e: ranked diesel-cycle GO-1, LANDED in commit 034b9218)
  and wave46-recon/task-5-receipt.md (whole-family FRESH at 45931c16:
  peroxide GO-1 + piston-engine-cycle GO-2, both landed). Wave-46 task-2
  receipt is the AVIONICS probe — propulsion's wave-46 file is task-5, read
  above. Every standing decline row below was re-probed FRESH at HEAD with
  real greps, not taken from memory.
- Family diff wave-47 HEAD (a4ae6d1e) to wave-48 HEAD (92d84a48),
  restricted to skills/: exactly the diesel-cycle landing (034b9218: leaf
  SKILL.md + logic + test + 2 corpus tasks) and the router row/guidance
  edit in the wave-47 close (d9ddab35: +1 router row, +1 guidance line).
  No other ownership change anywhere in the family.
- Census at HEAD (53 leaves / 11 packs): axial-compressor 6, combustion 1,
  electric 4, engine-airframe 1, gas-turbine-cycle 10, ramjet 2,
  reciprocating 2 (piston-engine-cycle Otto + diesel-cycle Diesel), rocket
  18, turbofan 5, turbomachinery 2, turboprop 2. Router parity
  (`grep -c '^| propulsion/' skills/propulsion/SKILL.md`) = 53 == 53.
  Corpus parity: 106 propulsion tasks == 53 x 2, 53 distinct full targets;
  piston and diesel leaves 2 tasks each (w47-diesel-cycle-1/-2 verbatim).

## Verdict

**1 GO candidate (strong, not conditional):**
`propulsion/reciprocating/dual-cycle` — the air-standard dual (Sabathe /
limited-pressure / mixed heat-addition) cycle, the third member of the
classic air-standard reciprocating-cycle triad whose first two members the
wave-46/47 GOs landed as piston-engine-cycle (Otto, constant-volume heat
addition) and diesel-cycle (Diesel, constant-pressure heat addition). The
dual cycle models the high-speed compression-ignition aircraft-diesel class
(premixed constant-volume ignition phase followed by diffusion
constant-pressure phase) with BOTH heat-addition laws; it was NEVER
adjudicated in any wave-39..47 receipt, leaf plan, or builder kit (zero
mentions of dual-cycle / sabathe / limited-pressure-cycle anywhere in
ops/, verified by grep — the sole history hit is an unrelated
"limited pressure ratio" phrase inside a wave-24 rocket spec, a false
positive). It is zero-owner tree-wide and in the corpus, has a published
deterministic closed-form anchor with verified limit behavior (alpha->1
recovers the Diesel formula, rho->1 recovers the Otto formula), carries the
standing far-33 reference-only convention of the pack, and passes the
deterministic Hit@1 sim with margins 8.5 and 14.5 over the diesel sibling
plus a zero-theft audit over ALL 1306 corpus tasks (0 flips).

**1 standing quality finding, still open (planner attention, NOT a GO):**
wave-47 flagged corpus task w46-piston-engine-cycle-2 ("brake-horsepower at
altitude from the sea-level rating with the density-ratio power lapse") as
over-claiming its bound leaf: the landed piston-engine-cycle module still
has NO altitude/lapse function at HEAD (function list re-read this probe:
otto_efficiency, isentropic_temperature_ratio, indicated/brake power, bsfc
family, thermal efficiencies, volumetric_fuel_flow, ga_band_verdict,
piston_engine_cycle — no lapse). Corpus wording unchanged at HEAD
(verbatim re-read). Fix in place (task wording or an in-leaf density-ratio
lapse extension) in a maintenance wave; still NOT a new leaf (token
collision on the bound task stands re-verified).

Everything else in the family declines below with fresh evidence at HEAD.

## GO-1 (rank 1): propulsion/reciprocating/dual-cycle
(suggested leaf name: dual-cycle; sibling in the existing reciprocating
pack, no NEW-pack flag)

High-speed compression-ignition aircraft powerplant station math under the
air-standard dual (Sabathe / limited-pressure) cycle: the mixed heat
addition is modeled as a constant-volume phase (pressure ratio alpha)
followed by a constant-pressure phase (cutoff ratio rho), thermal efficiency
from the compression ratio, gamma, alpha and rho, the isentropic
compression temperature ratio and state temperatures through the two heat
additions, then the same four-stroke indicated/brake power + BSFC bookkeeping
as the two pack siblings on Jet-A with the published reference-only
compression-ignition band verdict. Model shape = the exact diesel-cycle GO
precedent (wave-47): sibling in the same pack duplicating the station shell
with a genuinely different core heat-addition model — this one is the
textbook model for HIGH-SPEED direct-injection CI engines, i.e. precisely
the automotive-derived Centurion/AE300-class aircraft diesels the diesel
leaf already cites, where the pure constant-pressure Diesel idealization is
the slow-speed limit. Placement mechanical: planner adds one router row +
one guidance bullet at close-out.

(a) Zero-owner greps, whole skills/ + eval/ tree at HEAD (real output, all
zero files):
- `grep -rliE 'dual[- ]cycle' skills/ eval/` -> 0 files.
- `grep -rliE 'sabathe' skills/ eval/` -> 0 files (also 0 for the accented
  spelling variants check note: no 'sabathe' anywhere).
- `grep -rliE 'limited[- ]pressure' skills/ eval/` -> 0 files.
- `grep -rliE 'air-standard-dual-cycle|mixed-heat-addition|
  pressure-ratio-of-heat-addition' skills/ eval/` -> 0 files (all proposed
  tags zero-owned, individually verified).
- Corpus: `grep -icE 'dual-cycle|sabathe|limited-pressure|
  mixed-heat-addition' eval/hit1-corpus.yaml` -> 0 (rc=1). No corpus task
  routes on any dual-cycle token.
- Adjudication history: `grep -rniE 'dual-cycle|sabathe|limited-pressure-
  cycle' ops/` -> sole hit is the wave-24 rocket-engine-cycle spec's
  unrelated "limited pressure ratio" phrase (read and classified this
  probe); zero mentions in wave-39..48 briefs, receipts, leaf plans or
  builder kits. The dual-cycle seam was never proposed, declined or planned.
- Reciprocal token check against the pack siblings' owned sets: the Otto
  leaf's owned triggers (air-standard-otto-cycle, four-stroke-powerplant,
  avgas-class band) and the Diesel leaf's owned triggers
  (air-standard-diesel-cycle, diesel-cycle-efficiency,
  compression-ignition-powerplant, cutoff-ratio as a lead, jet-a-fuel-cycle)
  are not reused as lead tokens in the proposed description or queries
  (sim-verified below).

(b) Sibling fences (quoted verbatim at HEAD). Neither landed sibling models
a mixed (constant-volume THEN constant-pressure) heat addition; both
self-describe a SINGLE heat-addition law:
- piston-engine-cycle domain quick reference: "Air-standard Otto thermal
  efficiency: eta = 1 - 1/r^(gamma-1), with r the compression ratio (r > 1)
  and gamma the specific-heat ratio ... This is the ideal efficiency ceiling
  of the spark-ignition cycle, not a real-cycle prediction." — constant-
  volume heat addition only; the leaf is spark-ignition end to end.
- diesel-cycle domain quick reference: "Air-standard Diesel thermal
  efficiency (constant-pressure heat addition): eta = 1 - (1/r^(gamma-1)) *
  ((rc^gamma - 1)/(gamma * (rc - 1))) ... This is the ideal efficiency
  ceiling of the compression-ignition cycle, not a real-cycle prediction."
- diesel-cycle verification text: "As rc approaches 1 the Diesel efficiency
  approaches the same-r constant-volume Otto ceiling 1 - 1/r^(gamma-1),
  showing the two air-standard cycles share a common limit" — the leaf
  itself counts exactly TWO air-standard cycles in the pack's map (Otto and
  Diesel) and claims no mixed/dual model; the dual cycle appears nowhere in
  either leaf.
- diesel-cycle function list (read at HEAD, scripts/diesel_cycle_logic.py):
  diesel_efficiency(compression_ratio, cutoff_ratio, gamma), isentropic
  temperature ratio, compression/cutoff/expansion temperatures,
  heat_addition_j_per_kg, indicated_power, brake_power, bsfc family,
  ci_band_verdict, diesel_cycle — NO pressure-ratio (alpha) parameter
  exists anywhere in the module; the mixed heat addition cannot be produced.
  The piston module's function list likewise has no alpha input.
- Family router guidance (verbatim): "Compression-ignition powerplant
  questions (air-standard Diesel cycle efficiency at the compression ratio
  and cutoff ratio, diesel state points, brake specific fuel consumption of
  a compression-ignition engine) route to the reciprocating diesel-cycle
  sub-skill; spark-ignition Otto-cycle questions stay with piston-engine-
  cycle." — only the two existing cycles are routed; no limited-pressure /
  dual / mixed wording on any router row (rows re-read at HEAD, lines
  93-94).

(c) Standards-map id (grep-verified): `grep -n 'id: far-33'
standards-map.yaml` -> line 193, exists. 14 CFR Part 33 historically covers
reciprocating AND turbine aircraft engines including certified
compression-ignition aircraft diesels; far-33 reference-only, gated false =
the exact standing STANDARDS-REF convention of both reciprocating siblings.

(d) Published deterministic anchor (numbers recomputed at HEAD with python3,
none from memory): air-standard dual (Sabathe / limited-pressure) cycle
thermal efficiency
eta = 1 - (1/r^(gamma-1)) * ((alpha*rho^gamma - 1)/((alpha - 1) +
gamma*alpha*(rho - 1))),
r = compression ratio, alpha = pressure ratio of the constant-volume
heat-addition phase (P3/P2), rho = cutoff ratio of the constant-pressure
phase (V4/V3 = T4/T3); standard air-standard-cycles textbook treatment
(Cengel/Boles and Moran-class air-standard cycle coverage; the dual cycle
is the standard model for high-speed direct-injection diesel engines).
Limit identities verified numerically this probe: alpha -> 1 reproduces
the Diesel formula exactly; rho -> 1 reproduces the Otto formula exactly
(both to <1e-9). Magnitudes computed: r = 17, gamma = 1.4 -> Otto ceiling
0.6780262755; Diesel rho = 2.2 -> 0.6136842121; dual alpha = 1.2, rho =
2.2 -> 0.6194912576; alpha = 1.5 -> 0.6243368716; alpha = 2.0 ->
0.6284415661; r = 17, alpha = 1.35, rho = 2.0 -> 0.6316460526. Ordering
Diesel < dual < Otto at fixed r verified — the dual ceiling interpolates
between the two landed siblings' ceilings, a genuinely distinct
deterministic model neither existing module can emit. Same four-stroke PLAN
bookkeeping as the siblings carries the station shell (indicated power =
IMEP x V_d x (rpm/60)/2, brake power at mechanical efficiency, BSFC in
kg/(kW h) and lb/(hp h) through the exact unit bridge, Jet-A constants,
reference-only CI band 0.35-0.42 lb/(hp h) / eta_b 0.3262-0.3806 — same
published class as the diesel leaf's worked example, reported never
enforced).

(e) Two wordable Hit@1 corpus queries, sim-verified by replicating the
deterministic token router from scripts/router_eval.py EXACTLY (hyphen-
preserving tokens, stopword filter, tag weight 3 / name 2 / desc 1 / body
0.5, verbatim-phrase bonus 4, tie-break path asc) over the REAL 657-SKILL.md
index plus the hypothetical dual-cycle leaf (script in /tmp; run this
probe):
1. "run the air-standard-dual-cycle for the high-speed compression-ignition
   aircraft powerplant at the 17 to 1 compression ratio: the dual-cycle
   thermal efficiency from the pressure-ratio-of-heat-addition across the
   constant-volume phase and the cutoff-ratio of the constant-pressure
   phase of the sabathe limited-pressure-cycle, then the indicated power
   from the mean-effective-pressure and the displacement and the brake
   power at the mechanical efficiency on the jet-a fuel"
   -> Hit@1 propulsion/reciprocating/dual-cycle at 40.0; runner-up
   propulsion/reciprocating/diesel-cycle at 31.5; margin 8.5 (strong).
2. "analyze the sabathe-cycle limited-pressure-cycle operating point of the
   high-speed compression-ignition aircraft engine: the air-standard-dual-
   cycle thermal efficiency from the pressure-ratio-of-heat-addition across
   the constant-volume phase and the cutoff-ratio across the constant-
   pressure phase of the mixed heat-addition model, and the jet-a fuel
   brake-specific-fuel-consumption band check for the dual-cycle powerplant"
   -> Hit@1 propulsion/reciprocating/dual-cycle at 41.5; runner-up
   propulsion/reciprocating/diesel-cycle at 27.0; margin 14.5 (strong).
Both lead queries keep the siblings' owned trigger tokens out of the lead
position (diesel-cycle / air-standard-diesel-cycle / otto-cycle appear only
in body/desc filler or not at all), the wave-46/47 query pattern.
ZERO-THEFT AUDIT: adding the hypothetical dual-cycle leaf to the real index
and re-scoring ALL 1306 corpus tasks -> PASS, 0 flips: no existing task
changes its expected top-1 (both w47-diesel tasks still Hit@1 at
diesel-cycle; both w46-piston tasks still Hit@1 at piston-engine-cycle).
The dual leaf's own two spec-time corpus tasks would supply its 2-task
parity at build time (the wave-47 diesel precedent: GO with zero prior
corpus demand).

(f) Tag discipline: distinctive hyphenated compounds only (dual-cycle,
air-standard-dual-cycle, sabathe-cycle, limited-pressure-cycle,
mixed-heat-addition, pressure-ratio-of-heat-addition). No bare generic tags
(no bare cycle, heat, addition, pressure, ratio, ignition) and no reuse of
the siblings' owned tokens (air-standard-otto-cycle, four-stroke-powerplant,
air-standard-diesel-cycle, diesel-cycle-efficiency, compression-ignition-
powerplant, cutoff-ratio as a lead, jet-a-fuel-cycle). All proposed tags
grep-verified zero-owned tree-wide and corpus-wide (a).

## Declines table (whole family, fresh probes at HEAD; gates in brackets)

| Seam probed | Verdict | Evidence (fresh at HEAD) |
|---|---|---|
| scramjet + scramjet-adjacent | CLOSED DEFINITIVELY | Not re-probed per brief; scramjet token 0 files under skills/; wave-40/41/46/47 closure stands |
| two-stroke / port-timing / scavenging (wave-47 decline) | DECLINE [d] | Re-verified: 'two-stroke' 0, 'scaveng' 0, 'port-timing' 0, 'trapping-effic/delivery-ratio' 0 files in skills/ + eval/; corpus 0. Charging/scavenging quality is empirical delivery-vs-trapping chart data, no deterministic closed-form law; two-stroke SI shares the Otto ceiling (diesel leaf's limit note counts exactly two air-standard cycles); no anchor beyond far-33. Wave-47 row stands, fresh greps |
| rotary / Wankel prime mover (wave-47 decline) | DECLINE [d] | Re-verified: 'wankel' 0, 'trochoid' 0, 'rotary-engine' 0 files in skills/ + eval/; corpus 0. Air-standard ceiling reduces to the owned Otto model; geometry (epitrochoid housing, eccentricity) is empirical config; token cannibalization of piston-engine-cycle; no distinct standards anchor. Stands |
| atkinson / miller over-expansion cycles (fresh, never adjudicated) | DECLINE [d][c] | Re-verified fresh: 'atkinson' 0, 'miller-cycle' 0 files in skills/ + eval/; corpus 0. Over-expansion air-standard identities exist (deterministic) but the class has no aircraft-engine application and no aviation standards anchor — these are automotive powertrain cycles; family scope is aircraft/rocket propulsion (router Domain enumerates turbine/rocket/ramjet/electric/reciprocating AIRCRAFT powerplants); no corpus demand. Thin aviation relevance vs the dual cycle (same textbook family, real aircraft-diesel class) |
| piston altitude / power lapse / supercharger / critical altitude (wave-47 decline + open quality finding) | DECLINE (in-place fix) | Re-verified at HEAD: corpus task w46-piston-engine-cycle-2 still binds "brake-horsepower at altitude ... density-ratio power lapse" to piston-engine-cycle (verbatim re-read); piston module still has NO altitude/lapse function (function list re-read) — the wave-47 quality finding stands OPEN; fix in place, NOT a new leaf. 'supercharg' hits only the corpus task itself; 'turbocharg' 0 files in skills/ + eval/. Supercharger drive crosses into axial-compressor compressor-map (surge, corrected flow) and turbomachinery centrifugal-compressor (impeller, slip factor/Wiesner) — owners verified at HEAD |
| piston propeller-engine matching (wave-47 decline) | DECLINE [b] | Re-verified fences at HEAD: turboprop-cycle owns propeller (Froude) efficiency, "the thrust delivered from the shaft power at the flight speed ... the advance ratio and the power and thrust coefficients at the propeller speed" (tags: advance-ratio, power-coefficient, thrust-coefficient); piston/diesel "Related leaves" both defer shaft-power-to-thrust bookkeeping "once a prime mover, turbine or reciprocating, delivers shaft power" to turboprop-cycle; vehicle-design/sizing/propeller-sizing owns geometry ("derive the propeller diameter from the blade-tip constraint and the ground clearance, select the blade count and the blade chord from the solidity and the activity factor"); engine-airframe-integration owns installed thrust-drag. Matching = composition, no unowned station identity |
| turbofan bypass-ratio cycle station producer (wave-48 focus probe) | DECLINE [b] | Re-verified at HEAD: bypass-ratio-trade owns "the thrust split between the fan and core streams, the specific thrust, and the thrust-specific fuel consumption across candidate bypass ratios, and weigh them against the fan pressure ratio trend"; turbofan-cycle owns bypass ratio from flows, propulsive efficiency, net/specific thrust; turbofan-design-point owns the two-stream station chain "0-2-13-2.5-3-4-4.5-5-9/19 ... from the overall pressure ratio, the turbine-inlet temperature, the bypass ratio and the fan pressure ratio"; turbofan-off-design owns corrected-flow/rating bookkeeping. No unowned deterministic bypass-ratio identity remains |
| compressor-turbine matching at station level (wave-48 focus probe) | DECLINE [b] | Re-verified: engine/component/spool-matching tokens live only in owned leaves — free-turbine ("free-turbine sizing, power-turbine matching, turboprop shaft power, or turboshaft cycle estimates"), turbofan-off-design (fan/core matching verdict), turbojet-cycle; axial-compressor-stage + multi-stage-compressor + turbine-stage own stage math (velocity triangles, degree of reaction — descs re-read); wave-43 engine-matching closure stands; not closed form without maps |
| intake station models (subsonic/supersonic) | DECLINE [b] | subsonic-inlet-recovery owns "the ram recovery ratio from free-stream Mach ... the capture area for the engine mass flow at flight speed and density, and the capture verdict against the intake highlight, spillage"; ramjet-inlet owns the supersonic side ("diffuser total pressure recovery at the flight Mach number from the isentropic limit or from the normal shock standing at the cowl lip ... the Kantrowitz starting criterion"). Mixed/external-compression tokens 0 files; wave-46 composition decline stands |
| combustor station models | DECLINE [b] | combustor-design owns the gas-turbine combustor station end to end ("stoichiometric fuel-air-ratio from the fuel carbon and hydrogen mass fractions, the operating fuel-air-ratio ... the equivalence ratio, the combustion efficiency, the heat release ... and the temperature rise"); cea-rocket-combustion owns rocket combustion; ramjet-cycle owns ramjet FAR -> total-temperature-ratio; aerodynamics rayleigh-flow owns duct heat-addition. No unowned combustor station producer |
| nozzle station models | DECLINE [b] | propelling-nozzle owns the gas-turbine nozzle station ("decide the choked or unchoked regime from the nozzle pressure ratio against the critical ratio 1.851, size the throat area ... gross thrust with the pressure term"); rocket nozzles owned (nozzle-design, nozzle-area-ratio-selection, divergence-loss, flow-separation, thrust-chamber-cooling); mixed-flow-exhaust owns the turbofan mixer station. Variable-area nozzle / thrust-reverser tokens: measured/empirical (wave-46/47 closure); thrust-vector-control owns the rocket TVC slot |
| turboshaft / turboprop-propeller / axial-stage extras (standing) | DECLINE [b] | free-turbine owns power-turbine matching + turboshaft wording; axial-compressor-stage / multi-stage-compressor / turbine-stage own stage math; no pack changed since wave-46 except the reciprocating additions (which do not touch these) |
| gas-turbine-cycle / turbofan / turbojet extra parameters (standing) | DECLINE [b] | real-cycle-effects, afterburner/intercooled/regenerative cycles, brayton-optimum-pressure-ratio, mixed-flow-exhaust, bypass-ratio-trade, turbofan-off-design own every parameter trade; combined variants compose dedicated leaves |
| rocket remainder (chamber/ballistics/turbopump/TVC/monopropellant/nozzle/feed) (standing) | DECLINE [b] | Re-verified owners at HEAD unchanged: combustion-chamber-design (c*, L*, contraction, thrust coefficient), solid/hybrid motor leaves (burn rate, grain, Pc), rocket-turbopump (NPSH, suction specific speed), hydrazine + hydrogen-peroxide leaves (catalyst chemistry), nozzle leaves, injector-design, thrust-vector-control, rocket-engine-cycle (feed cycles), thrust-chamber-cooling (Bartz, regenerative/film); HAN/nitromethane wave-46 row stands (research-grade, no anchor); electric-pump / ullage / cryogenic / ignition-delay rows stand (owners re-verified) |
| electric propulsion remainder (standing) | DECLINE [d] | Mechanism map complete for closed-form classes (electrothermal, gridded-ion, hall, mpd); PPT/FEEP/pulsed-arc tokens 0 files; closed on anchor absence, wave-46 closure stands |
| ramjet-adjacent (FAR heat addition, multi-shock intakes) (standing) | DECLINE [b] | ramjet-cycle owns FAR -> total-temp-ratio; rayleigh-flow owns heat-addition duct math; ramjet-inlet + oblique-shock relations own intake recovery; scramjet vein closed |

## Closed veins (re-verified fresh at HEAD)

- Scramjet and scramjet-adjacent: CLOSED DEFINITIVELY (token absent from
  skills/ entirely; do not re-open).
- Component engine matching / off-design map coupling: CLOSED (wave-43);
  corrected-flow/matching verdict bookkeeping owned by turbofan-off-design.
- Pulsed ablation EP + field-emission electrospray: closed on anchor
  absence (wave-46).
- Empirical nozzle geometry / altitude-compensation contours: closed on
  fabrication risk (wave-43/46).
- Rocket feed/pressurization/chamber/ballistics: owned set dense and
  unchanged (wave-46 rows re-verified).
- Reciprocating pack map after this probe: piston-engine-cycle owns Otto
  (spark-ignition, constant-volume); diesel-cycle owns Diesel
  (compression-ignition, constant-pressure); dual-cycle ranked GO-1 for the
  mixed heat-addition (high-speed CI) slot; altitude lapse is an in-place
  extension of piston-engine-cycle (open quality finding). RECOMMENDATION
  for the planner: after dual-cycle lands, declare the reciprocating
  air-standard cycle triad COMPLETE (Otto/Diesel/dual) so later waves do
  not keep re-mining the reciprocating textbook-cycle map; remaining
  reciprocating seams (two-stroke gas exchange, rotary geometry, atkinson/
  miller) close on empirics/scope as tabled.

## Standards-map check

- 30 ids at HEAD (`grep '^  - id:' standards-map.yaml` = 30). GO-1 uses the
  existing far-33 id (line 193), reference-only, gated false — the pack's
  standing convention; NO new id invented (reference-only conventions per
  sibling conventions).

## Method and honesty notes

- Read-only probe: no git writes, no edits to skills/, eval/, scripts/,
  Makefile, standards-map.yaml, or wave briefs; the only repo write is this
  receipt. git status before and after shows only `?? ops/automation/state/
  wave48-recon/`.
- All greps, fence quotes, function lists and corpus rows executed at HEAD
  92d84a48 and quoted from real output; no values taken from memory; all
  anchor numbers recomputed with python3 this probe.
- Router sim: exact replication of scripts/router_eval.py scoring (read
  from source this probe), over the real 657-SKILL.md index plus one
  hypothetical dual-cycle leaf, for the two proposed queries AND the full
  1306-task zero-theft audit (0 flips). Sim scripts live in /tmp only
  (w48_prop_sim2.py, w48_prop_q2.py); no repo file was modified.
- No machine-local absolute paths anywhere in this file; repo referenced
  only as ~/AeroSkills or repo-relative paths.
