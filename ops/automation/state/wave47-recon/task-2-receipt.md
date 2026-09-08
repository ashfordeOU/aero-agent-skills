# WAVE-47 PROPULSION PROBE RECEIPT (task-2, whole-family FRESH)

- Repo: the AeroSkills repo, probed FRESH at HEAD `a4ae6d1e` (verified
  `git log --oneline -1` = "Wave-47: close-out must auto-update
  products-state (FIX)"). The brief commit `a544f421` is HEAD's parent;
  `git show --stat a4ae6d1e` touches only ops/automation/wave47-brief.md
  (5 insertions, 1 deletion) — zero skill/eval/corpus/standards edits
  between the brief commit and HEAD, so the family probed is identical at
  both. Working tree clean apart from the untracked wave47-recon receipt
  dir. Read-only probe: the one write is this receipt.
- Scope (wave-47 brief item 3): ENTIRE propulsion family, 52 leaves / 11
  packs, probed FRESH because wave-46 added two leaves (rocket
  hydrogen-peroxide-monopropellant-thruster; NEW pack reciprocating with
  piston-engine-cycle). Scramjet CLOSED DEFINITIVELY, not re-opened (scramjet
  token = 0 files under skills/ at HEAD). Wave-39/43/44/46 declines stood
  unless a wave-46 leaf moved a seam — each standing row re-verified at HEAD
  with fresh owner greps, not memory (battery below).
- Leaf inventory at HEAD (52): axial-compressor 6, combustion 1, electric 4,
  engine-airframe 1, gas-turbine-cycle 10, ramjet 2, reciprocating 1 (wave-46
  NEW pack), rocket 18 (incl. wave-46 peroxide), turbofan 5,
  turbomachinery 2, turboprop 2. Router parity: `grep -c '^| propulsion/'`
  skills/propulsion/SKILL.md = 52 == 52 leaves.
- Corpus eval/hit1-corpus.yaml: 1286 tasks; `grep -c 'expected_skill:
  "propulsion/'` = 104 == 52 x 2; distinct full leaf targets
  (`grep -o 'expected_skill: "propulsion/[a-z-]*/[a-z-]*"' | sort -u |
  wc -l`) = 52 — full parity, every leaf carries its 2 tasks.
- Standards map: 30 ids (`grep '^  - id:' standards-map.yaml` = 30);
  candidate id grep-verified below.
- Baseline receipts read first: wave46-recon/task-5-receipt.md (whole-family
  FRESH at 45931c16: ranked peroxide GO-1 + piston-engine-cycle GO-2, both
  LANDED) and the wave-47 brief. No candidate below reopens a decline row, a
  closed vein, or a standing stay row of that receipt.

## Verdict

**1 GO candidate**: `propulsion/reciprocating/diesel-cycle` — the
compression-ignition (CI) air-standard Diesel-cycle sibling inside the
wave-46 reciprocating pack, on the seam wave-46 GO-2 opened but never
adjudicated (that GO's Otto leaf is explicitly spark-ignition; the CI
prime-mover slot is unowned, unmentioned in every ops/automation state file
from wave-39..46, zero in tree and corpus). Full (a)-(f) gate evidence
below, every gate re-run FRESH at HEAD this probe.

**1 quality finding (planner attention, NOT a GO)**: corpus task
`w46-piston-engine-cycle-2` asks for "brake-horsepower at altitude from the
sea-level rating with the density-ratio power lapse" but the landed
piston-engine-cycle module has NO altitude/lapse function (function list
verified at HEAD: otto_efficiency, isentropic_temperature_ratio,
indicated_power, brake_power, brake_specific_fuel_consumption,
bsfc_lb_per_hp_hr, fuel_flow_from_bsfc, indicated/brake_thermal_efficiency,
volumetric_fuel_flow, ga_band_verdict, piston_engine_cycle). The task
over-claims its bound leaf and its wording blocks any standalone piston
altitude leaf (token collision) — fix in place (task wording or an in-leaf
density-ratio lapse extension) in a maintenance wave, NOT as a new leaf.

Everything else in the family declines below with fresh evidence.

## GO-1 (rank 1): propulsion/reciprocating/diesel-cycle
(suggested leaf name: diesel-cycle)

Compression-ignition aircraft powerplant station math: air-standard Diesel
cycle thermal efficiency from compression ratio, specific-heat ratio and
cutoff ratio (constant-pressure heat-addition model), isentropic
compression temperature ratio, cutoff-ratio identity rc = 1 + q_in/(cp*T2),
then the same four-stroke indicated/brake power + specific-fuel-consumption
bookkeeping as the wave-46 Otto leaf but on Jet-A (kerosene) with the
published CI aircraft-engine BSFC band, reported reference-only. Model shape
= hydrazine/peroxide precedent: sibling in the same pack duplicating the
station shell with a genuinely different core model (constant-pressure vs
constant-volume heat addition), documented inputs, no empirical maps.
Placement mechanical: the reciprocating pack dir already exists (no NEW-pack
flag); planner adds one router row + one guidance bullet at close-out.

(a) Zero-owner greps, whole skills/ + eval/ tree at HEAD (real output, all
rc=1 / zero files):
- `grep -rliE 'diesel' skills/ eval/` -> 0 files (word absent repo-wide).
- `grep -rliE 'compression[- ]ignition' skills/ eval/` -> 0 files.
- `grep -rliE 'cutoff[- ]ratio' skills/ eval/` -> 0 files.
- `grep -rliE 'scaveng|supercharg|turbocharg|wankel|port[- ]timing' skills/
  eval/` -> 0 files (neighboring reciprocating veins, see declines).
- Adjudication history: `grep -rliE 'diesel|compression[- ]ignition|
  two[- ]stroke|supercharg' ops/automation/` -> hits ONLY this wave-47
  receipt itself; zero mentions in any wave-39..46 state file, leaf plan, or
  brief. The CI slot inside the reciprocating pack was never probed,
  declined, or planned before wave-47.
- 'reciprocat' owners in skills/ SKILL.md files = exactly 2: the
  piston-engine-cycle leaf and the family router. No other family/pack
  claims reciprocating-engine content.

(b) Sibling fences (quoted at HEAD). The wave-46 Otto leaf is
spark-ignition/constant-volume end to end and never computes a
constant-pressure heat-addition cycle:
- piston-engine-cycle description: "...the air-standard Otto cycle thermal
  efficiency from the compression ratio and the specific-heat ratio, the
  four-stroke indicated power from the indicated mean effective pressure...
  brake specific fuel consumption..." — Otto is the only cycle in the
  model; trigger list leads with piston-engine-cycle, air-standard-otto-cycle.
- piston-engine-cycle Domain quick reference: "This is the ideal efficiency
  ceiling of the spark-ignition cycle, not a real-cycle prediction." — the
  leaf self-identifies as spark-ignition cycle math.
- Function list (scripts/piston_engine_cycle_logic.py) has no Diesel /
  constant-pressure / cutoff-ratio / compression-ignition function; fuel
  constants are avgas only (AVGAS_DENSITY_KG_PER_M3 720.0,
  AVGAS_LHV_J_PER_KG 43.5e6) — no Jet-A constant exists anywhere in the leaf.
- Family router row 93 (piston-engine-cycle): trigger set is
  piston-engine-cycle, air-standard-otto-cycle, mean-effective-pressure,
  brake-specific-fuel-consumption, reciprocating-engine-powerplant,
  four-stroke-powerplant — no CI wording on the row.
- Family router guidance line ~150: reciprocating questions are "air-standard
  Otto cycle efficiency at the compression ratio, four-stroke indicated
  power from mean effective pressure and displacement, brake power at
  mechanical efficiency, brake specific fuel consumption" routed to
  piston-engine-cycle — Otto-only, no compression-ignition wording anywhere.
- Piston leaf boundary (lines 144-149) defers all shaft-power-to-thrust work:
  "propulsion/turboprop/free-turbine: the turboshaft power-turbine...";
  "propulsion/turboprop/turboprop-cycle: propeller (Froude) efficiency and
  shaft-power-to-thrust bookkeeping once a prime mover, turbine or
  reciprocating, delivers shaft power." — the pack's prime-mover station is
  the piston leaf; CI is its unowned sibling slot.

(c) Standards-map id (grep-verified): `grep -n 'id: far-33'
standards-map.yaml` -> line 193, exists. 14 CFR Part 33 historically covers
reciprocating AND turbine aircraft engines, including certified
compression-ignition aircraft diesels (Centurion/AE300 class); far-33
reference-only, gated false = the exact standing convention of the wave-46
piston leaf (same pack, STANDARDS-REF).

(d) Published deterministic anchor (numbers recomputed at HEAD with python3,
none taken from memory): air-standard Diesel cycle thermal efficiency
eta = 1 - (1/r^(gamma-1)) * ((rc^gamma - 1)/(gamma*(rc - 1))), r = compression
ratio, rc = cutoff ratio (constant-pressure heat addition 2->3); standard
air-standard-cycles textbook treatment. Isentropic compression temperature
ratio T2/T1 = r^(gamma-1); cutoff-ratio identity rc = T3/T2 =
1 + q_in/(cp*T2). Magnitudes computed: r = 17, rc = 2.2, gamma = 1.4 ->
eta = 0.6136842121; rc = 2.0 -> 0.6230571224; rc = 2.5 -> 0.6003309854
(efficiency falls as rc grows, correct constant-pressure-addition
signature); T2/T1 = 3.1058435016, T2 = 894.95 K from 288.15 K. Contrast with
the Otto leaf's own ceiling: r = 8.5 -> 0.5751531234 and the same r = 17
Otto ceiling 0.6780262755 — the two cycles are genuinely different models the
Otto leaf cannot produce. Worked four-stroke point: IMEP 1.8e6 Pa, V_d
2.0e-3 m3, 2300 rpm -> P_i = 69000 W = 92.53 hp (PLAN, one power stroke per
two revs); P_b at eta_m 0.86 = 59340 W = 79.58 hp; fuel flow 3.9e-3 kg/s
Jet-A (LHV 43.2 MJ/kg) -> BSFC 0.2366 kg/(kW h) = 0.38897 lb/(hp h) (1 lb/
(hp h) = 0.608277 kg/(kW h)), inside the published CI aircraft-engine band
~0.35-0.42 lb/(hp h); band endpoints: 0.36 lb/(hp h) = 0.21898 kg/(kW h) ->
brake thermal efficiency 0.3806, 0.42 -> 0.25548 kg/(kW h) -> 0.3262
(eta_b = 3.6e6/(b * LHV)); eta_i 0.4095 > eta_b 0.3522 = 0.86 x 0.4095,
ordering consistent, all below the ideal Diesel ceiling 0.6137. Band checks
reference-only, never enforced — same convention as the Otto leaf's
ga_band_verdict (SI avgas band 0.40-0.55 lb/(hp h) is a DIFFERENT published
band, further proving the models differ).

(e) Two wordable Hit@1 corpus queries, distinctive hyphenated tokens all
zero-owner tree-wide and in the corpus today (per (a)):
1. "run the air-standard-diesel-cycle for the compression-ignition aircraft
   engine at the 17 to 1 compression ratio: the diesel-cycle efficiency from
   the cutoff-ratio constant-pressure heat-addition model and the
   compression temperature ratio, then the brake-horsepower from the
   mean-effective-pressure and the displacement and the specific fuel
   consumption of the jet-a-fueled diesel powerplant at the cruise rating
   with the published compression-ignition band check"
2. "compare the compression-ignition diesel-cycle ideal efficiency against
   the spark-ignition otto ceiling at the same 16 to 1 compression ratio:
   the air-standard-diesel-cycle cutoff-ratio sensitivity from 2 to 2.5 and
   the jet-a-fuel brake specific fuel consumption band for the
   compression-ignition aircraft powerplant"
Tokens diesel-cycle, air-standard-diesel-cycle, compression-ignition,
cutoff-ratio, jet-a-fuel(ed) sit on no router row and in no corpus task
today, so Hit@1 is clean. The Otto leaf's owned lead triggers
(air-standard-otto-cycle, piston-engine-cycle as a lead, four-stroke-
powerplant, avgas) are kept out of the lead position; bare "specific fuel
consumption" phrasing appears only as filler, never leading — same pattern
as the wave-46 peroxide queries against hydrazine.

(f) Tag discipline: distinctive hyphenated compounds only (diesel-cycle,
air-standard-diesel-cycle, compression-ignition, cutoff-ratio,
constant-pressure-heat-addition, jet-a-fuel-cycle). No bare generic tags
(no bare engine, fuel, cycle, ignition, ratio) and no reuse of the Otto
leaf's owned tokens (air-standard-otto-cycle, four-stroke-powerplant,
avgas) or turbine SFC tags.

## Quality finding (planner attention, NOT a GO)

- Corpus task w46-piston-engine-cycle-2 (verified at HEAD, task block ~line
  5731): query = "...reciprocating-engine powerplant altitude bookkeeping...
  brake-horsepower at altitude from the sea-level rating with the
  density-ratio power lapse, and the specific-fuel-consumption band check
  for the four-stroke piston engine", bound to
  propulsion/reciprocating/piston-engine-cycle. The leaf's module computes
  no altitude lapse — it is a single-point sea-level bookkeeping model
  (function list verified (b)). The query over-claims its bound leaf.
  Recommend a maintenance-wave fix inside piston-engine-cycle (task wording
  or an in-leaf density-ratio lapse extension), not a new leaf — a
  standalone altitude leaf would cannibalize the bound task's routing tokens
  and the Otto leaf's boundary never says "sea level only".

## Declines table (whole family, fresh probes at HEAD)

| Seam probed | Verdict | One-line reason (owner / anchor, fresh at HEAD) |
|---|---|---|
| scramjet + scramjet-adjacent | CLOSED DEFINITIVELY | Not re-probed per brief; scramjet token = 0 files under skills/; wave-40/41/46 closure stands |
| diesel-cycle (reciprocating CI) | **GO-1** | See above — the one clean producer |
| two-stroke / port-timing / scavenging (fresh, never adjudicated) | DECLINE | Charging/scavenging quality is empirical delivery-vs-trapping chart data, no deterministic closed-form law; two-stroke SI shares the Otto ceiling the piston leaf already owns; no distinct standards-map anchor beyond far-33 |
| spark-ignition "bookkeeping" extension (fresh) | DECLINE | Volumetric efficiency and MBT/ignition timing are engine-specific empirical maps; mixture stoichiometry/FAR is owned by gas-turbine-cycle combustor-design station math (desc verified: "stoichiometric fuel-air-ratio from the fuel carbon and hydrogen mass fractions..."); thin composition |
| piston-engine altitude / power lapse / supercharger / critical altitude (fresh) | DECLINE | Corpus task w46-piston-engine-cycle-2 already binds "density-ratio power lapse ... at altitude" wording to piston-engine-cycle (quality finding — fix in place); supercharger drive crosses into axial-compressor compressor-map (surge, corrected flow) and turbomachinery centrifugal-compressor (impeller, slip factor/Wiesner — owner verified); no explicit altitude fence on the Otto leaf, so an altitude leaf would cannibalize a bound task |
| piston propeller-engine matching (fresh) | DECLINE | Owned by composition: turboprop-cycle owns propeller (Froude) efficiency + shaft-power-to-thrust bookkeeping and the piston leaf itself defers to it ("once a prime mover, turbine or reciprocating, delivers shaft power"); vehicle-design/sizing/propeller-sizing owns geometry/advance-ratio; engine-airframe-integration owns installed thrust-drag bookkeeping |
| wankel / rotary prime mover (fresh) | DECLINE | Air-standard ceiling reduces to the owned Otto model; engine-specific geometry empirics; token cannibalization of piston-engine-cycle; zero corpus, no distinct standards anchor |
| HAN / nitromethane / other monopropellant chemistries (standing) | DECLINE | Wave-46 row stands: catalyst/energetics research-grade, no deterministic published anchor; hydrazine + peroxide leaves own the catalytic station chemistry (both descs verified at HEAD) |
| catalyst-bed pressure drop / bed sizing (fresh, peroxide seam) | DECLINE | Peroxide leaf owns the silver-catalyst-bed band verdict; bed loading kg/(m2 s) is empirical range data; Ergun single-equation station too thin and cannibalizes the silver-catalyst-bed token |
| electric-pump feed cycle (fresh, rocket seam) | DECLINE | rocket-engine-cycle owns feed-cycle taxonomy and the pump-power balance (desc verified: "compare pressure-fed against the pump-fed gas-generator, staged-combustion, and expander cycles... compute the pump discharge pressure, the oxidizer and fuel pump powers, the turbine drive power and the cycle power balance"); an electric drive swaps turbine for motor+battery bookkeeping that belongs to power-system leaves — composition, no unowned deterministic propulsion station |
| ullage / settling / pressurant feed-side (standing + fresh) | DECLINE | space-systems/subsystems/propellant-tank-sizing owns the ullage volume station (owner verified); rocket-engine-cycle owns feed cycles; settling is trajectory (gnc); wave-46 pressurant row stands |
| cryogenic boil-off (fresh) | DECLINE | propellant-selection owns storability trade; tank-side heat-leak belongs to space-systems tank/thermal leaves; no propulsion station |
| ignition delay / hypergolic ignition (fresh) | DECLINE | Ignition delay is measured property data (ms), not closed-form station math; no anchor |
| ablative / radiation-only nozzle cooling (standing + fresh) | DECLINE | thrust-chamber-cooling owns regenerative + film cooling (Bartz owner verified); radiative equilibrium wall temperature is a composition needing its heat-flux input; ablative empirics row (wave-46) stands |
| remaining rocket chamber/ballistics/turbopump/TVC seams (re-verified STAY) | DECLINE | Unchanged owners at HEAD: combustion-chamber-design (c*, L*, contraction, thrust coefficient), solid-rocket-motor + hybrid-rocket-motor (burn rate, regression rate, Pc equilibrium, grain geometry), rocket-turbopump (NPSH, suction specific speed — owner verified), nozzle leaves (area ratio, separation, divergence), injector-design, thrust-vector-control |
| turboshaft / engine-matching / axial-stage (standing) | DECLINE | free-turbine owns the turboshaft/power-turbine slot (desc verified: "free-turbine sizing, power-turbine matching, turboprop shaft power, or turboshaft cycle estimates"); wave-43 engine-matching closure stands; axial-compressor-stage + multi-stage-compressor own stage math (velocity triangles, flow coefficient, degree of reaction owners verified) |
| gas-turbine-cycle / turbofan / turboprop extra parameters (standing) | DECLINE | No pack changed since wave-46; bypass-ratio-trade + turbofan-design-point own fan-pressure-ratio trades (owners verified); turbofan-off-design, real-cycle-effects, afterburner/intercooled/regenerative leaves own the trades; combined-cycle variants compose existing leaves |
| electric propulsion remainder (PPT, pulsed arc, FEEP/electrospray, RF ion, resistojet standalone) (standing) | DECLINE | Token battery at HEAD: pulsed plasma / FEEP / electrospray / field emission = 0 files anywhere in skills/ (closed on anchor absence, wave-46 closure stands); mechanism map complete for clean closed-form classes; resistojet/arcjet owned by electrothermal-thruster (owner verified) |
| ramjet combustor FAR / multi-shock intakes / scramjet-adjacent (standing) | DECLINE | Compositions of ramjet-cycle / ramjet-inlet (normal-shock owner verified) / subsonic-inlet-recovery / aerodynamics shock leaves; scramjet vein closed |

## Closed veins (unchanged from wave-46 at HEAD)

- Scramjet and scramjet-adjacent: CLOSED DEFINITIVELY (token absent from
  skills/ entirely).
- Component engine matching / off-design map coupling: CLOSED (wave-43).
- Pulsed ablation EP + field-emission electrospray: closed on anchor absence.
- Empirical nozzle geometry / altitude-compensation contours: closed on
  fabrication risk.
- Rocket feed systems and pressurization: rocket-engine-cycle +
  propellant-tank-sizing + fuel-feed rows own it.
- Reciprocating pack map after this probe: piston-engine-cycle owns the Otto
  (spark-ignition) GA powerplant station; diesel-cycle is ranked GO-1 for the
  CI slot; altitude lapse is an in-place extension of piston-engine-cycle
  (quality finding); all other reciprocating veins closed on ownership or
  anchor absence.

## Read-only verification note

Probe performed read-only except this single receipt file. No git writes, no
edits to skills/, eval/, standards-map.yaml, scripts/, Makefile, or wave
briefs. All greps and fence quotes executed at HEAD a4ae6d1e and quoted from
real output; standards-map id far-33 grep-verified at line 193; corpus
parity 104 = 52 x 2 with 52 distinct full targets verified; all anchor
numbers computed with python3 this probe (no values taken from memory, no
machine-local absolute paths in this file). Decline rows re-verified at HEAD
against leaf/router text via the token-owner battery above; unchanged seams
cite the standing wave-46 receipt rows by reference.
