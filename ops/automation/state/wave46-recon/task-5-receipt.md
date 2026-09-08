# WAVE-46 PROPULSION PROBE RECEIPT (task-5, whole-family FRESH)

- Repo: the local AeroSkills repo at ~/AeroSkills, HEAD `45931c16` (verified
  `git rev-parse HEAD`; `git status --porcelain` empty). Read-only probe: the
  one write is this receipt under ops/automation/state/wave46-recon/.
- Family doctrine (wave-46 brief item 6, propulsion): yielding — wave-45 +2
  (mpd-thruster under electric/, hydrazine-monopropellant-thruster under
  rocket/); scramjet CLOSED DEFINITIVELY (do NOT re-open); wave-39/43/44
  declines stood (drag loss, PPT, resistojet, pressurant, ablative,
  turboshaft / engine-matching / axial-stage); probe FRESH with receipts,
  only clean closed-form / station-level producers.
- Baseline read first: ops/automation/state/wave45-recon/task-3-receipt.md
  (wave-45 whole-family propulsion probe). No candidate below reopens a
  decline row, a closed vein, or a standing stay row of that receipt.
- Corpus baseline: eval/hit1-corpus.yaml = 1266 tasks, of which 100 target
  propulsion leaves; verified exactly 2 tasks per leaf across all 50 leaves
  (expected_skill grep + `sort | uniq -c` parity, no leaf with != 2).
- Standards map: 30 ids in standards-map.yaml (grep '^  - id:' = 30);
  candidate ids grep-verified below (ecss at line 94, far-33 at line 193).

## Verdict

2 GO candidates, both on seams that NO wave-39..45 receipt, leaf plan, or
builder kit ever adjudicated (verified: zero mentions of hydrogen-peroxide /
H2O2 monopropellant, and zero of reciprocating / Otto-cycle / piston-engine
powerplant content in any ops/automation/state wave file). Both are clean
deterministic station-level producers in the established family shapes
(hydrazine-monopropellant-thruster sibling; engine prime-mover bookkeeping),
both zero-owner tree-wide and in the corpus, both with a published
closed-form anchor and an existing standards-map id.

## Whole-family enumeration (50 leaves, all probed)

`find skills/propulsion -name SKILL.md` returns 51 files = 50 leaves + 1
family router; router table rows (grep '^| propulsion/') = 50, parity
confirmed at HEAD:

```
axial-compressor (6): axial-compressor-stage, compressor-map,
  multi-stage-compressor, polytropic-efficiency, turbine-blade-cooling,
  turbine-stage
combustion (1): cea-rocket-combustion
electric (4): electrothermal-thruster, gridded-ion-thruster,
  hall-thruster, mpd-thruster
engine-airframe (1): engine-airframe-integration
gas-turbine-cycle (10): afterburner-cycle, brayton-optimum-pressure-ratio,
  combustor-design, gas-turbine-cycle, intercooled-cycle,
  propelling-nozzle, real-cycle-effects, regenerative-cycle,
  subsonic-inlet-recovery, turbojet-cycle
ramjet (2): ramjet-cycle, ramjet-inlet
rocket (17): cold-gas-thruster, combustion-chamber-design,
  hybrid-rocket-motor, hydrazine-monopropellant-thruster, injector-design,
  nozzle-area-ratio-selection, nozzle-design, propellant-selection,
  rocket-engine-cycle, rocket-gravity-loss, rocket-nozzle-divergence-loss,
  rocket-nozzle-flow-separation, rocket-sizing, rocket-staging,
  solid-rocket-motor, thrust-chamber-cooling, thrust-vector-control
turbofan (5): bypass-ratio-trade, mixed-flow-exhaust, turbofan-cycle,
  turbofan-design-point, turbofan-off-design
turbomachinery (2): centrifugal-compressor, rocket-turbopump
turboprop (2): free-turbine, turboprop-cycle
```

## Ranked GO candidates

### GO-1 (rank 1): propulsion/rocket/hydrogen-peroxide-monopropellant-thruster (suggested leaf name: hydrogen-peroxide-monopropellant-thruster)

Hydrogen peroxide monopropellant thruster station model, the direct chemical
sibling of the wave-45 hydrazine leaf: catalytic decomposition of H2O2 over a
silver catalyst bed, 2 H2O2(l) -> 2 H2O(g) + O2(g) exothermic, adiabatic
decomposition (chamber) temperature from the Hess-law energy balance at a
documented peroxide concentration (water dilution), then frozen-composition
isentropic expansion of the steam/oxygen product mixture to vacuum exhaust
velocity and vacuum specific impulse, propellant mass flow at the thrust
point, with published decomposition-temperature and impulse bands reported
reference-only. Deterministic closed form, stdlib-only, no tables.

(a) Zero-owner greps, whole skills/ + eval/ tree at HEAD (real output):
- `grep -rniE 'peroxide' skills/ eval/` -> 0 files (the word "peroxide"
  appears nowhere in the repo; the only spelling present is the formula).
- `grep -rn 'H2O2' skills/` -> 1 file:
  `skills/propulsion/rocket/propellant-selection/SKILL.md:31:  (RP-1, H2O2), hypergolic (MMH/UDMH with NTO or IRFNA, ignites on`
  H2O2 appears once, as a storable BIPROPELLANT oxidizer example inside a
  propellant-family classification bullet; no decomposition or thruster
  station content anywhere.
- `grep -rniE 'silver[- ]catalyst|electrospray|field[- ]emission|feep'
  skills/ eval/` -> 0 files.
- Corpus eval/hit1-corpus.yaml: 'peroxide' 0 tasks, 'H2O2' 0 tasks,
  'hydrazine' 9 lines (2 route to the hydrazine leaf, rest are router-leaf
  comment headers and space-systems tank rows). 'monopropellant' appears
  only in hydrazine-thruster / rocket-engine-cycle / space-systems tank
  contexts.

(b) Sibling fences (quoted at HEAD). The wave-45 hydrazine leaf is
hydrazine-specific end to end — Use when + constants + triggers:
- hydrazine-monopropellant-thruster: "Use when the task is sizing and
  assessing a hydrazine monopropellant thruster for spacecraft reaction
  control: liquid hydrazine decomposes catalytically over a catalyst bed..."
  and its strict boundary: "The boundary is strict: this leaf is the
  decomposition station math, not a feed cycle model, not a nozzle hardware
  sizer, not a tank sizer and not an attitude control law." Its energy
  balance is N2H4-specific (primary decomposition releasing 111.8833 kJ per
  mole fed; ammonia-dissociation fraction); its tags are
  hydrazine-monopropellant-thruster / catalytic-decomposition /
  ammonia-dissociation-fraction / monopropellant-rcs /
  decomposition-temperature. Nothing in the leaf models a different
  monopropellant chemistry.
- propellant-selection (line 25-31): propellant families bullet lists
  "storable (RP-1, H2O2)" — classification/trade content only; the leaf's
  own domain is families, density impulse, O/F bulk density and mass
  fraction, not thruster decomposition stations.
- rocket-engine-cycle (line 30): "(LOX/RP-1, LOX/LH2, N2O4/MMH,
  monopropellant hydrazine). It covers the feed system only." — feed-cycle
  bookkeeping, and only hydrazine is named as its monopropellant reference.
- cold-gas-thruster: "a high pressure inert gas plenum, often nitrogen...
  The boundary is strict: this leaf is the gas thruster flow and blowdown
  model, not a tank structural sizer and not an attitude control law." —
  inert gas only; no catalytic chemistry.
- electrothermal-thruster: heats a working gas (NH3, N2, H2 or He) with
  electrical power — "this leaf only heats propellant, so it neither
  accelerates charged beams nor uses extraction electrode assemblies";
  chemical decomposition heat release is a different energy source and is
  unclaimed.
- space-systems propellant-tank-sizing (lines 69, 95): hydrazine appears
  only as a density/volume tank-sizing example ("Hydrazine monopropellant
  tank: mass 100 kg, density 1008 kg/m3"), never as a thruster station.

(c) Standards-map id (grep-verified): `grep -n 'id: ecss'
standards-map.yaml` -> line 94 `  - id: ecss`, exists; ecss reference-only
is the standing convention of the whole rocket RCS pack (cold-gas-thruster,
hydrazine-monopropellant-thruster, rocket-engine-cycle all carry it).

(d) Published deterministic anchor (summary only): hydrogen peroxide
catalytic decomposition 2 H2O2(l) -> 2 H2O(g) + O2(g), exothermic, standard
enthalpies of formation (H2O2(l) -187.8 kJ/mol, H2O(g) -241.8 kJ/mol) giving
about -54 kJ per mole of H2O2 fed; adiabatic decomposition temperature from
the product sensible-heat balance at a documented concentration (water
dilution raises the product mass and caps the temperature), published
decomposition temperatures in the ~900-1100 K class for 85-98% peroxide;
then frozen isentropic expansion of the steam/oxygen mixture to the vacuum
exhaust velocity and specific impulse, with published peroxide-thruster
vacuum Isp in the ~150-190 s class reported reference-only, never enforced.
Source family: rocket propulsion textbooks (Sutton Rocket Propulsion
Elements monopropellant coverage; Humble liquid-propellant reference) plus
the published silver-catalyst H2O2 monopropellant thruster literature. Same
model shape as the hydrazine sibling leaf: concentration (like the ammonia
dissociation fraction) is a documented input, so the model is closed form
and deterministic; band checks are advisory only.

(e) Two wordable Hit@1 corpus queries with distinctive hyphenated tokens:
1. "size the hydrogen-peroxide-monopropellant-thruster for the 1 N
   spacecraft reaction control duty: the peroxide-decomposition chamber
   temperature from the catalytic energy balance of H2O2 at the 90 percent
   concentration with the water dilution, then the vacuum exhaust velocity
   and specific impulse of the steam-oxygen product mixture through the
   nozzle"
2. "run the peroxide-decomposition energy balance for the
   hydrogen-peroxide-thruster design point: adiabatic decomposition
   temperature and frozen-mixture expansion to vacuum specific impulse at
   the 85 and the 98 percent concentration limits, with the
   silver-catalyst-bed band check for the monopropellant RCS thruster"
Tokens hydrogen-peroxide-monopropellant-thruster, peroxide-decomposition,
steam-oxygen product mixture, silver-catalyst-bed, hydrogen-peroxide-
thruster exist on no router row and in no corpus task today, so Hit@1 is
clean. The hydrazine leaf's owned tokens (hydrazine-decomposition,
ammonia-dissociation-fraction, catalytic-decomposition, monopropellant-rcs,
catalyst-bed) are deliberately avoided; 'decomposition-temperature' tags on
the hydrazine leaf are not reused.

(f) Tag discipline: distinctive hyphenated compounds only
(hydrogen-peroxide-monopropellant-thruster, peroxide-decomposition,
steam-oxygen-mixture, silver-catalyst-bed,
concentration-limited-decomposition). No generic single-word tags (no bare
thruster, peroxide-as-word, catalyst, impulse) and no hydrazine-leaf token
reuse.

### GO-2 (rank 2): propulsion/reciprocating/piston-engine-cycle (suggested leaf name: piston-engine-cycle)

Reciprocating aircraft (general-aviation) powerplant station math: air-
standard Otto cycle thermal efficiency from the compression ratio and
specific-heat ratio, four-stroke engine bookkeeping from indicated mean
effective pressure, displacement and crankshaft speed to indicated power,
brake power at the mechanical efficiency, and brake specific fuel
consumption from the fuel flow and brake power, with published GA brake
thermal efficiency / BSFC bands reported reference-only. Placement note for
the planner: this is the one GO requiring a NEW pack directory
(propulsion/reciprocating/) plus a router group row and guidance line;
mechanical, but flag for the leaf-plan gate. It is the aircraft-engine
prime-mover slot that no turbine/rocket/electric leaf claims.

(a) Zero-owner greps, whole skills/ + eval/ tree at HEAD (real output):
- `grep -rniE 'reciprocat' skills/ eval/` -> 0 files
- `grep -rniwE 'otto' skills/` -> 0 files (whole word, case-insensitive)
- `grep -rniE 'bsfc|brake[- ]specific' skills/ eval/` -> 0 files
- `grep -rniE 'mean[- ]effective|imep|bmep' skills/ --include='SKILL.md'`
  -> 0 files (one non-SKILL.md false positive in a systems-engineering
  test script, substring of 'TimePlanning')
- 'piston' tree hits classify fully non-engine: aerodynamics hypersonic-
  piston-theory + its cross-references (surface-pressure analogy),
  vehicle-design hydraulic-actuator-sizing / hydraulic-system-sizing
  (actuator 'piston area'), manufacturing ultrasonic-inspection (circular
  piston transducer near field). Corpus 'piston' tasks are the same three
  classes (hypersonic piston theory x2, hydraulic actuators x2); 'otto'
  corpus hits are the 'bottom' substring of flat-bottom-hole tasks (2).
- Corpus: 'reciprocat' 0, 'otto' word 0, 'bsfc' 0, 'mean-effective' 0,
  'spark-ignition' 0, 'four-stroke' 0, 'avgas'/'Lycoming' 0 tasks.

(b) Sibling fences (quoted at HEAD):
- Family router skills/propulsion/SKILL.md top: "Use when a task concerns
  aircraft or rocket propulsion: guide the router to the propulsion
  pack..." with a Domain paragraph enumerating gas turbine and turbofan
  cycle analysis, rocket sizing/nozzle/propellant, ramjet, axial
  compressor — every listed engine class is turbine, rocket, ramjet or
  electric; no reciprocating content.
- free-turbine: "Use when the task is free-turbine sizing, power-turbine
  matching, turboprop shaft power, or turboshaft cycle estimates." — the
  shaft-power turbine slot; a piston engine is not a turbine and is not
  claimed.
- turboprop-cycle: propeller (Froude) efficiency, thrust from shaft power,
  static thrust, equivalent shaft power — the turbine-driven-propeller
  powerplant slot; its shaft power is an input from the turbine side.
- engine-airframe-integration: "installed thrust from uninstalled gross
  thrust minus intake momentum (ram) drag, nacelle and pylon drag, and
  bleed and accessory power extraction losses" — installed-behavior
  bookkeeping for turbine engines; no prime-mover thermodynamics.
- vehicle-design propeller sizing and flight-mechanics performance leaves
  consume engine shaft power / thrust as inputs and produce none of the
  thermodynamic or mechanical bookkeeping of any engine class.
- No other family anywhere in skills/ holds an engine-cycle producer
  (tree-wide pack scan: only cross-cutting 'power-analysis' (numerics),
  avionics power-input (do-160), space-systems power-thermal-budget — none
  engine mechanics).

(c) Standards-map id (grep-verified): `grep -n 'id: far-33'
standards-map.yaml` -> line 193 `  - id: far-33`, exists; far-33 (aircraft
engines airworthiness, which has historically covered reciprocating and
turbine aircraft engines) is already the family router's own reference-only
id, matching convention.

(d) Published deterministic anchor (summary only): air-standard Otto cycle
thermal efficiency eta = 1 - 1/r^(gamma-1) from compression ratio r and
specific-heat ratio gamma; four-stroke indicated power from mean effective
pressure, displacement and crankshaft speed (indicated power = IMEP x
displacement x half the revolution rate, the classic PLAN bookkeeping of
aircraft powerplant texts), brake power at a documented mechanical
efficiency; brake specific fuel consumption from fuel flow over brake
power, cross-checked against published GA brake-thermal-efficiency bands
(~0.25-0.30 class, BSFC ~0.4-0.55 lb/hp-hr class for carbureted and
fuel-injected four-stroke aircraft engines) reported reference-only, never
enforced. Worked closed-form anchor: r = 8.5, gamma = 1.4 -> eta = 0.575;
IMEP 900 kPa, 4.0 L displacement, 2700 rpm -> about 81 kW indicated, 0.85
mechanical efficiency -> about 69 kW brake. IMEP/BMEP and mechanical
efficiency are documented inputs (same documented-input convention as the
electrothermal and hydrazine leaves); no empirical engine maps.

(e) Two wordable Hit@1 corpus queries with distinctive hyphenated tokens:
1. "size the piston-engine-cycle for the 180 horsepower four-stroke
   aircraft powerplant at 2700 rpm: the air-standard-otto-cycle thermal
   efficiency at the 8.5 to 1 compression ratio, indicated power from the
   mean-effective-pressure and the displacement, brake power at the 0.85
   mechanical efficiency, and the brake-specific-fuel-consumption at the
   cruise rating"
2. "analyze the reciprocating-engine powerplant altitude bookkeeping for
   the general-aviation aircraft: otto-cycle efficiency from the
   compression ratio, brake-horsepower at altitude from the sea-level
   rating with the density-ratio power lapse, and the specific-fuel-
   consumption band check for the four-stroke piston engine"
Tokens piston-engine-cycle, air-standard-otto-cycle, mean-effective-
pressure, brake-specific-fuel-consumption, reciprocating-engine, four-
stroke, brake-horsepower appear on no router row and in no corpus task
today, so Hit@1 is clean; turboprop/turbofan SFC and off-design
density-ratio tokens are deliberately not reused. 'compression-ratio' is
kept only inside longer distinctive tokens to avoid any pressure-ratio
ambiguity with axial-compressor rows.

(f) Tag discipline: distinctive hyphenated compounds only
(piston-engine-cycle, air-standard-otto-cycle, mean-effective-pressure,
brake-specific-fuel-consumption, reciprocating-engine-powerplant,
four-stroke-powerplant). No generic single-word tags (no bare engine,
power, fuel, efficiency, ratio) and no reuse of turbine SFC or
hypersonic-piston tokens.

## Declines table

| Seam probed | Verdict | One-line reason (owner / anchor) |
|---|---|---|
| scramjet-cycle (standing) | CLOSED DEFINITIVELY | Not re-probed per brief; wave-40/41 closure: no verified Rayleigh energy-bookkeeping anchor; duct math owned by aerodynamics rayleigh-flow |
| scramjet-adjacent veins (isolator, dual-mode) | CLOSED DEFINITIVELY | Same closure; do not re-open |
| drag loss (standing) | DECLINE | Installed and ram-drag bookkeeping owned by engine-airframe-integration; capture/spillage owned by subsonic-inlet-recovery |
| PPT, pulsed plasma thruster (standing) | DECLINE | Pulsed ablation discharge lacks a clean deterministic closed-form anchor |
| pulsed vacuum-arc thruster (fresh) | DECLINE | Same pulsed-ablation vein as PPT: ablated mass per pulse is empirical, no deterministic anchor |
| resistojet / arcjet as standalone leaves (standing) | DECLINE | electrothermal-thruster owns both operating points ("Use when the task is resistojet or arcjet performance analysis") |
| electrospray / FEEP (fresh, never adjudicated) | DECLINE | Emission mass flow from field evaporation is empirical; no clean closed-form anchor and no standards-map id; corpus zero |
| RF/microwave ion thruster variant (fresh) | DECLINE | Beam extraction physics is the gridded-ion-thruster slot (Kaufman); ionization coupling is empirical; thin differentiation |
| pressurant / feed-side (standing) | DECLINE | rocket-engine-cycle owns feed cycles; space-systems propellant-tank-sizing and vehicle-design fuel-feed own tank/pressurant rows |
| ablative cooling (standing) | DECLINE | Empirical char-material data, no standards-map anchor; thrust-chamber-cooling owns regenerative and film cooling |
| turboshaft (standing) | DECLINE | free-turbine owns the shaft-power slot incl. turboshaft wording |
| engine-matching / component-map coupling (standing) | DECLINE | Not closed form; compressor-map / off-design / stage leaves own the pieces (wave-43 closure) |
| axial-stage / stage-count extension (standing) | DECLINE | axial-compressor-stage and multi-stage-compressor own stage math |
| ramjet combustor heat addition with FAR (standing) | DECLINE | Composes ramjet-cycle (FAR -> total temperature ratio) and aerodynamics rayleigh-flow; no new producer |
| external-compression multi-shock intake (standing) | DECLINE | Composes ramjet-inlet (recovery, Kantrowitz, starting) and aerodynamics oblique-shock relations; token cannibalization risk |
| bell / parabolic nozzle contour geometry (standing) | DECLINE | Rao percent-length contours rest on empirical chart data, no published deterministic law (wave-43 fabrication-risk precedent) |
| aerospike / dual-bell / expansion-deflection nozzles (fresh) | DECLINE | Same closed vein as bell contour: base-pressure and mode-transition modeling are empirical; no deterministic closed form |
| rocket ballistic range / trajectory (standing) | DECLINE | gnc impact-point-prediction owns ballistic range; rocket-staging / rocket-sizing own the staging math |
| ducted fan / shrouded propeller (standing) | DECLINE | Momentum-theory pieces owned across turboprop-cycle, vehicle-design propeller-sizing, ram-air-turbine-sizing; shroud augmentation empirical |
| extra turbofan/turbojet cycle parameters (standing) | DECLINE | bypass-ratio-trade owns BPR/specific-thrust/TSFC trade; turbofan-off-design owns ratings; no unowned cycle-parameter producer |
| supersonic pitot intake for turbojet aircraft (standing) | DECLINE | ramjet-inlet owns normal-shock pitot recovery and Kantrowitz at flight Mach; subsonic-inlet-recovery owns the subsonic side |
| turbopump NPSH / suction-specific-speed / cavitation (re-verified STAY) | DECLINE | rocket-turbopump owns it end to end: "assess the suction performance with the available net positive suction head and the suction specific speed, and judge the cavitation margin against the suction specific speed limit" |
| chamber L* / chamber volume / contraction ratio / thrust coefficient (re-verified STAY) | DECLINE | combustion-chamber-design owns them: "the characteristic velocity, the throat area, the thrust coefficient, the contraction ratio, the chamber volume from L-star" |
| solid grain geometry / web / burn-area neutrality (re-verified STAY) | DECLINE | solid-rocket-motor owns: "Grain geometry: the web is the thickness of propellant consumed... burn time is web / r. For a tubular grain the inner-bore burn area is pi * D_inner * L" plus progressive/neutral/regressive verdict |
| centrifugal slip factor / work input (re-verified STAY) | DECLINE | centrifugal-compressor owns the Wiesner slip-factor correlation and Euler work input |
| cold-gas blowdown incl. adiabatic variant (re-verified STAY + fresh variant) | DECLINE | cold-gas-thruster owns blowdown (isothermal time constant, pressure history, total impulse); an adiabatic-blowdown sibling would cannibalize its plenum/blowdown/choked-flow tokens (wave-45 explicitly avoided them) |
| monopropellant alternates: HAN / nitromethane (fresh) | DECLINE | No clean published deterministic closed-form anchor in standard texts; catalyst and energetics remain research-grade; corpus zero |
| warm-gas RCS (fresh) | DECLINE | Composition of electrothermal heating + cold-gas nozzle; thin, no new producer |
| rocket Pc-from-thrust closure (fresh) | DECLINE | Thin algebra composing nozzle-design and combustion-chamber-design (Pc = mdot c*/At); no new station |
| real-turbojet specific-thrust-with-losses (fresh) | DECLINE | real-cycle-effects owns real SFC and component-loss temperatures; turbojet-cycle owns ideal thrust; composition (wave-45 cycle-parameter closure) |
| turbojet off-design (fresh) | DECLINE | Needs component-map matching — the closed engine-matching vein; turbofan-off-design owns corrected-flow/rating bookkeeping |
| afterburning turbofan / combined intercool-regenerate-reheat cycles (fresh) | DECLINE | Each variant composes existing dedicated leaves (mixed-flow-exhaust, afterburner-cycle, intercooled-cycle, regenerative-cycle); no unowned producer |
| nuclear-thermal / pulsejet / rotating-detonation (fresh, never adjudicated) | DECLINE | No deterministic closed-form anchor (reactor and detonation coupling not station algebra), no standards-map id, zero corpus; exotic slots stay closed |
| thrust reverser (fresh) | DECLINE | Reverser effectiveness is measured/empirical; no clean deterministic anchor |

## Closed veins

- Scramjet and scramjet-adjacent analysis: CLOSED DEFINITIVELY (do not
  re-open). Supersonic inlet station math owned by ramjet-inlet; subsonic
  ram recovery/capture/spillage owned by subsonic-inlet-recovery.
- Heat-addition duct flow: aerodynamics rayleigh-flow owns thermal choking
  and Rayleigh-line ratios.
- Component engine matching / off-design map coupling: CLOSED (wave-43);
  not closed form.
- Pulsed ablation electric propulsion (PPT and pulsed vacuum-arc) and
  field-emission electrospray/FEEP: no deterministic closed-form anchor;
  closed.
- Electric propulsion mechanism map is now complete for clean closed-form
  classes: electrothermal (resistojet + arcjet), gridded electrostatic
  (Kaufman), crossed-field electrostatic (hall), self-field electromagnetic
  (mpd). Remaining EP classes close on anchor absence, not ownership.
- Empirical nozzle geometry and altitude-compensation contours (Rao bell,
  aerospike base pressure, dual-bell transition): closed on fabrication
  risk; rocket-nozzle-divergence-loss owns the bookkeeping factors.
- Rocket feed systems and pressurization: rocket-engine-cycle plus
  space-systems propellant-tank-sizing plus vehicle-design fuel-feed rows.
- Rocket chamber/ballistics ownership is dense: combustion-chamber-design
  (c*, L*, contraction, thrust coefficient), solid-rocket-motor (burn
  rate, Pc equilibrium, grain geometry, neutrality), rocket-turbopump
  (head, NPSH, suction specific speed, cavitation), thrust-chamber-cooling
  (Bartz, regenerative/film), nozzle leaves (area ratio, separation,
  divergence), TVC leaf.
- Turbine cycle-parameter trades and combined-cycle variants: owned or
  compositions of dedicated leaves; closed.
- Monopropellant station chemistry: hydrazine owned (wave-45); hydrogen
  peroxide open and ranked GO-1; other monopropellant chemistries closed on
  anchor absence.
- Aircraft engine prime movers: turbine classes all owned (turbojet,
  turbofan + off-design, free-turbine/turboshaft, turboprop, ramjet);
  reciprocating GA powerplant open and ranked GO-2.

## Read-only verification note

Probe performed read-only except this single receipt file. No git writes
(git status clean before and after), no edits to skills/, eval/, docs/,
Makefile, scripts/, standards-map.yaml, or wave briefs. All greps and fence
quotes above were executed at HEAD 45931c16 and quoted from real output;
standards-map ids verified by grep at lines 94 (ecss) and 193 (far-33).
All decline rows re-verified at HEAD against leaf descriptions and domain
quick-reference text, not taken from memory.
