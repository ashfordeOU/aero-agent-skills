# WAVE-49 STRUCTURES EXTENSION-PROBE RECEIPT (task-2, whole-family FRESH)

- Repo: the local AeroSkills repo (home-relative ~/AeroSkills). Probe HEAD
  verified: `git log --oneline -1` = 9c2b3fe4 ("ops: stage wave-49 brief
  (655 baseline, daylight gate 11:45 UTC)"), `git rev-parse HEAD` =
  9c2b3fe492cd1fbe6bd9bb0c4c83d159746433df. Working tree clean; the
  untracked ops/automation/state/wave49-recon/ receipts dir (empty at probe
  start) is the only state path. One write only: this receipt.
- Scope: ENTIRE structures family (LARGEST family, 67 leaves, 7 packs),
  probed FRESH, read-only. No writes to skills/, eval/, standards-map.yaml,
  scripts/, Makefile, or ops/automation briefs.
- Leaf count re-verified at HEAD: `find skills/structures -mindepth 3 -name
  SKILL.md | wc -l` = 67; family router at skills/structures/SKILL.md is
  the +1 router (67 rows, `grep -c '^| structures/'` = 67, parity OK). Pack
  census: composites 15, damage-tolerance 5, fatigue 7, fem 26, loads 4,
  materials 8, thermal-structures 2 (= 67). The ONLY family change since
  the wave-48 whole-family receipt is the +2 wave-48 leaves, both ON DISK
  at this HEAD owning their seams: composites/honeycomb-core-micromechanics
  (cell geometry + foil material -> equivalent core props E3/G13/G23,
  relative density; "Produces the equivalent core properties the sandwich
  panel workflow collects as given inputs") and
  composites/laminate-bending-stiffness (B/D by z-squared/z-cubed
  integrals, ABD for symmetric AND unsymmetric stacks, the D11/D22/D12/D66
  terms laminate-plate-buckling takes as given).
- Corpus baseline parsed FRESH at HEAD: eval/hit1-corpus.yaml = 1326 task
  blocks (`grep -c '^  - id:'`); standards map 30 ids (far-25 line 16,
  cs-25 line 27, mmpsd line 160, cmh-17 line 281). Whole-repo leaf count
  667 SKILL.md = 655 leaves + 12 routers.
- Prior-wave context read FIRST in full: wave-48 structures receipt
  (wave48-recon/task-5), wave-47 structures receipt (wave47-recon/task-5),
  wave-49 brief; wave-45/46/47/48 vehicle-design and aerodynamics receipts
  read for the cross-family rows quoted below. Every gate below was
  re-derived FRESH this session at this HEAD.
- Wave-48 verdict note: its 2 GO (honeycomb-core-micromechanics rank-1,
  laminate-bending-stiffness rank-2 CONDITIONAL) both landed at wave-48
  close and now own their seams (re-verified above). Wave-48 also carried
  a build-time fence note ("add one routing bullet to sandwich-panels
  pointing cell-geometry / core-property-prediction questions at this
  leaf") - NOT executed on disk at this HEAD: sandwich-panels SKILL.md has
  zero mentions of honeycomb-core-micromechanics (grep-verified). Router
  rows for both new leaves exist (parity 67), so this is a routing-line
  consistency gap only; flag to the wave-49 build.

## Verdict

2 ranked GO candidates, both never adjudicated in ANY structures-side
receipt (wave-41..48) and both zero-owner + corpus-absent at this HEAD:

1. **structures/composites/laminate-progressive-failure** (GO, rank 1,
   STRONG): march a laminate past first-ply failure to the ultimate load
   by the ply-discount method - at each event degrade the stiffness of the
   ply whose Tsai-Wu index reaches unity (matrix failure zeroes E2/G12,
   fiber failure zeroes E1), reassemble the laminate stiffness, re-apply
   the load resultant, repeat to the last-ply failure. The on-disk sibling
   laminate-first-ply-failure ITSELF declares the seam open: its Pitfalls
   (line ~131) reads "first-ply failure is the first ply event under the
   Tsai-Wu convention; post-FPF load redistribution and delamination
   growth are different leaves" - delamination-growth is on disk
   (energy-based DCB/ENF/B-K), post-FPF load redistribution has NO leaf
   anywhere. Never adjudicated in any wave, spec, or leaf plan (zero token
   hits across ALL ops/automation/state), zero corpus tasks, deterministic
   sequential CLT arithmetic on machinery the siblings already implement.
2. **structures/loads/continuous-turbulence-gust-loads** (GO, rank 2,
   CONDITIONAL): continuous-turbulence PSD gust design loads (von Karman /
   Dryden spectra, gust-response transfer function, response PSD, rms and
   design load per the continuous-turbulence clause). Zero-owner at this
   HEAD: gust-maneuver-loads is discrete 1-cosine only (its desc formula
   n = 1 + (rho0*V_e*a*K_g*U_de)/(2*W/S), tags discrete-gust/1-cosine),
   random-vibration-analysis is SDOF base-excitation equipment screening
   ("deliberately confined to SDOF random vibration response", desc
   verbatim) and claims no gust content. Twice adjudicated FROM the
   aerodynamics side pointing INTO this family (wave-45 task-8 decline:
   "Family home is structures/loads (random-vibration-analysis and
   gust-maneuver-loads own the PSD load machinery)"; wave-46 task-8
   STANDS; wave-45 sears-function spec forbidden vocabulary: "never
   dryden-spectrum, von-karman-spectrum, power-spectral-density (the
   structures loads family)") - an unfulfilled cross-family hand-off: the
   assigned home leaves implement no continuous-turbulence content. Never
   adjudicated by any structures-side receipt. Flagged CONDITIONAL: a
   reviewer holding the wave-45/46 "PSD machinery home" assignment as a
   vein line on random-vibration-analysis may order extend-RV instead, and
   the method borders the aerodynamics aeroelasticity pack's dynamic-gust
   identity (aeroelastic-gust-response is discrete time-domain
   Wagner/Kussner - distinct).

Everything else probed this session declines below; the wave-45 (16-row),
wave-46 (22-row), wave-47 and wave-48 fresh decline rows re-verified
STANDING (the only family state change since wave-46 is the +3/-... +2
wave-47 leaves and the +2 wave-48 leaves, all on disk, none touching any
decline row's seam). 67 leaves is genuinely thinning: one STRONG and one
CONDITIONAL never-adjudicated seam is the honest yield of this
whole-family FRESH pass - consistent with the wave-48 verdict that this
family now yields ~1-2 candidates per FRESH pass at most.

## Ranked GO candidate 1: structures/composites/laminate-progressive-failure

Ply-discount / last-ply failure marching: given the ply stack, the per-ply
engineering constants and the Tsai-Wu allowables (Xt, Xc, Yt, Yc, S), and
the applied in-plane resultants, compute the FPF event with the sibling
convention (Tsai-Wu index in each ply from the A-inverse mid-plane strain
recovery), discount the failed ply (matrix mode: E2, G12, nu12 -> 0;
fiber mode: E1 also -> 0; standard ply-discount reductions), reassemble
the A-matrix, re-apply the load increment, and march event-by-event to the
last-ply-failure ultimate load. Produces the failure sequence, the
degraded laminate stiffness after each event, the progressive load steps
and the ultimate-laminate-load / post-FPF reserve factor. Stdlib arithmetic
only; no test-data fitting.

(a) Zero-owner grep evidence, WHOLE skills/ tree (all 12 families) plus
eval/, run FRESH this session:

```
$ grep -rilE "progressive.{0,30}fail|ply.discount|last.ply" skills/ --include=SKILL.md
(no output - zero files)
$ grep -rilE "load.redistribution|stiffness.degradation|progressive.damage" skills/ --include=SKILL.md
skills/structures/fem/metallic-fastener-joints/SKILL.md
   (bolt-group fastener-pattern redistribution - metallic fastener seam, not laminate;
    the laminate progressive seam has zero files)
$ grep -icE "progressive.{0,30}fail|ply.discount|last.ply|post.?fpf" eval/hit1-corpus.yaml
0   (zero of 1326 task blocks)
$ grep -icE "first.ply" eval/hit1-corpus.yaml
9   (the OWNED slice: first-ply-failure tasks route to laminate-first-ply-failure; no task asks for the march past FPF)
```

Adjudication-history scan (widest net): grep -rilE
"progressive.{0,40}fail|ply.discount|last.ply|post.?fpf" over ALL of
ops/automation/state/ (all waves, incl. every wave4*-specs and
wave4*-leaf-plan) = ZERO hits - never adjudicated anywhere, ever. The
wave-33 FPF spec FORBIDDEN TOKENS list (read at this HEAD) fences only:
"ABD matrix, ply stiffness, laminate stiffness matrix assembly
(laminate-stiffness); hygrothermal, moisture, coefficient of thermal
expansion (laminate-hygrothermal-response); delamination, strain energy
release rate (delamination-growth); single-ply failure from given stresses
(failure-criteria)" - progressive / post-FPF / last-ply vocabulary is
assigned to NOBODY.

(b) Nearest sibling fences (quoted verbatim at this HEAD):
- laminate-first-ply-failure Pitfalls (lines 129-133): "Treating FPF as
  ultimate laminate failure: first-ply failure is the first ply event
  under the Tsai-Wu convention; post-FPF load redistribution and
  delamination growth are different leaves." - the sibling names the seam
  and disclaims it; delamination-growth exists (energy-based), the
  stress-based multi-event redistribution does not. Its desc/tags pin the
  FIRST event only (first-ply-failure-load, critical-ply, reserve-factor,
  laminate-failure-envelope).
- delamination-growth (lines 115-118): "leaf assesses delamination onset
  by energy release rate at the laminate level; stress-based ply failure
  (Tsai-Wu, max stress) belongs to failure-criteria, and metallic
  Paris-law growth to damage-tolerance/crack-growth." - energy-based
  identity; points stress-based ply failure at failure-criteria, which is
  single-ply-index-from-given-stresses only.
- failure-criteria: 3-criteria contract (Tsai-Wu, Tsai-Hill, max-stress
  from GIVEN stresses and allowables; workflow steps 2-4 + failure_verdict;
  tags composite-lamina). No multi-event / stiffness-evolution content.
- laminate-stiffness / laminate-bending-stiffness: stiffness assembly
  only, no strength evolution.

(c) Standards-map id exists (grep-verified): cmh-17 line 281; far-25 line
16; cs-25 line 27. Sibling precedent: FPF carries cmh-17 + far-25
reference-only (STANDARDS-REF, gated false). cmh-17 is the natural id
(CMH-17 vol. 3 laminate-strength methodology conventions).

(d) Published deterministic anchor: ply-discount / last-ply failure
analysis as the standard laminate-strength march in Daniel & Ishai,
Engineering Mechanics of Composite Materials, 2nd ed. (laminate strength
analysis: FPF -> ply discount -> last-ply/ultimate), with the CLT
re-assembly per Jones ch. 2 - the identical identity class the on-disk
FPF and laminate-stiffness leaves implement. Deterministic closure checks:
single-ply reduction is exact (a [0]8 stack under Nx fails at sigma1 =
Nx/t = Xt, so FPF = last-ply = ultimate - the leaf reduces to the FPF
identity); quasi-isotropic CFRP worked-example magnitude: the 90-ply
matrix event (FPF) sits at roughly a third to a fifth of the 0-ply
fiber-failure ultimate load - order-of-magnitude verifiable against the
published QI laminate examples. Magnitude-gate convention per wave-47.

(e) 2 wordable Hit@1 corpus queries, sim-verified with the deterministic
router (router_eval.py replication - tag 3 / name 2 / desc 1 / body 0.5,
phrase bonus 4, tie-break path asc - over the real 667-file index plus the
hypothetical candidate; helper kept to /tmp):
1. "compute the laminate-progressive-failure ultimate load of the
   quasi-isotropic carbon-epoxy stack by the ply-discount-method: at the
   first-ply-failure event degrade the stiffness of the failed ply,
   reassemble the laminate a-matrix, march the load to the next
   sequential-ply-failure event and repeat to the last-ply-failure, and
   report the ultimate-laminate-load and the degraded-laminate-stiffness
   of the post-fpf-load-redistribution analysis"
   -> laminate-progressive-failure 47.0 vs laminate-first-ply-failure
   10.5, margin 36.5 (strong)
2. "find the last-ply-failure load of the cross-ply laminate with the
   ply-discount-method: discount the failed-ply stiffness after each ply
   event, re-assemble the in-plane laminate stiffness and re-apply the
   load resultant until the laminate-progressive-failure march reaches
   the ultimate-laminate-load, and give the per-event failure sequence
   for the progressive-failure-analysis"
   -> laminate-progressive-failure 43.0 vs laminate-first-ply-failure
   11.5, margin 31.5 (strong)
ZERO-THEFT audit over all 1326 corpus tasks with the candidate in the
index: 1326/1326 unchanged (0 displacements; baseline gate5 Hit@1 also
1326/1326 at HEAD, harness equivalence proven).

(f) Tag set, all hyphenated compounds, none duplicating an existing tag
string (auto-audited against the union of all 667 indexed leaves' tags =
NONE):
laminate-progressive-failure, ply-discount-method, last-ply-failure,
ultimate-laminate-load, degraded-laminate-stiffness,
post-fpf-load-redistribution, sequential-ply-failure,
progressive-failure-analysis. Build-time fence note: add one routing row
to laminate-first-ply-failure pointing multi-event / post-FPF /
stiffness-degradation questions at this leaf (its own Pitfall already
names the split) plus one related-leaves row.

## Ranked GO candidate 2: structures/loads/continuous-turbulence-gust-loads (CONDITIONAL)

Continuous-turbulence PSD gust design loads: given the aircraft mass/loading
parameters, the flight speed and the turbulence environment (scale L and
rms gust intensity, or the reference intensity per the certification
clause), form the von Karman spectrum
Phi(Omega) = sigma_w^2 * (L/pi) * (1 + (8/3)(1.339 L Omega)^2) /
(1 + (1.339 L Omega)^2)^(11/6) (Dryden alternative), build the
gust-response transfer function of the airplane (rigid-aircraft vertical
response closed form), compute the response PSD = |H|^2 * Phi_w, integrate
to the rms load response and scale to the design load factor per the
continuous-turbulence design criterion; report the design gust loads and
the turbulence margin feeding the gust-maneuver-loads envelope and
load-spectrum-counting flows. Stdlib arithmetic only; published spectrum
constants only, no reproduced tables.

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/, FRESH:
```
$ grep -rilE "von.karman|continuous.turbulence|tuned.gust" skills/ --include=SKILL.md
skills/structures/fem/plate-buckling/SKILL.md            (von Karman EFFECTIVE-WIDTH constant - unrelated)
skills/aerodynamics/boundary-layer/boundary-layer-theory/SKILL.md  (von Karman momentum integral - unrelated)
skills/aerodynamics/aeroelasticity/sears-function-gust-lift/SKILL.md (frequency-domain gust lift context only)
   - no leaf implements a continuous-turbulence PSD gust-loads method
$ grep -icE "von.karman|continuous.turbulence|tuned.gust|gust.psd|power.spectral.density.{0,30}gust" eval/hit1-corpus.yaml
0   (zero of 1326 task blocks)
```
(b) Nearest sibling fences (quoted verbatim at this HEAD):
- gust-maneuver-loads desc: "compute aircraft structural loads from gust
  and maneuver conditions per FAR 25.341 and FAR 25.337: discrete 1-cosine
  gust load factor n = 1 + (rho0*V_e*a*K_g*U_de)/(2*W/S) ..."; tags
  discrete-gust/1-cosine/gust-alleviation-factor/v-n-diagram. The DISCRETE
  method only; no PSD spectrum content anywhere in the leaf.
- random-vibration-analysis desc: "compute the random vibration response
  of a structure or equipment item to a base-input acceleration power
  spectral density ... The response-level model here is deliberately
  confined to SDOF random vibration response; cycle counting and
  cumulative fatigue damage ... owned by the fatigue pack." - SDOF
  base-excitation equipment qualification; the leaf never claims aircraft
  continuous-turbulence gust loads and names no spectrum family.
- Cross-family hand-off (the seam's origin): wave-45 aerodynamics receipt
  row: "continuous-turbulence PSD gust loads (Dryden / von Karman
  spectra) | Family home is structures/loads (random-vibration-analysis
  and gust-maneuver-loads own the PSD load machinery), not aerodynamics
  section theory"; wave-46 aerodynamics receipt STANDS re-verify; wave-45
  sears-function spec forbidden vocabulary: "never dryden-spectrum,
  von-karman-spectrum, power-spectral-density (the structures loads
  family)". The aerodynamics family fences the vocabulary OUT of itself
  and INTO structures/loads - but the named home leaves implement no such
  content: the same unfulfilled-hand-off pattern as the wave-48
  laminate-plate-buckling consumer expecting D-terms from
  laminate-stiffness (which landed as laminate-bending-stiffness).
- aeroelastic-gust-response (aerodynamics/aeroelasticity, on disk):
  discrete time-domain 1-cosine gust, Wagner/Kussner typical-section
  dynamics - dynamic AEROELASTIC response identity, not the loads-pack
  design-loads PSD method; disjoint.
(c) Standards-map id exists (grep-verified): far-25 line 16, cs-25 line
27 - the loads-pack convention (gust-maneuver-loads carries far-25 +
cs-25 reference-only; STANDARDS-REF, gated false).
(d) Published deterministic anchor: Hoblit, Gust Loads on Aircraft:
Concepts and Applications (continuous-turbulence chapters: von Karman and
Dryden spectral forms with the published scale constants, gust-response
transfer function, response PSD, rms response and the design-intensity
criterion); FAR/CS 25.341(b) continuous-turbulence clause is the
certification framing (reference-only, like the sibling gust leaf). The
rigid-aircraft closed forms are deterministic given the spectrum constants
and the transfer function. Magnitude check: von Karman spectrum with the
standard L integrates to the prescribed sigma_w^2 (Parseval closure) - an
exact self-check; the rms load factor for a typical transport at the
reference turbulence intensity lands in the published design-load-factor
band.
(e) 2 wordable Hit@1 corpus queries, sim-verified with the same
deterministic router (real index + hypothetical candidate):
1. "compute the continuous-turbulence-gust-loads of the transport airplane
   by the power-spectral-density-gust-method with the von-karman-spectrum
   of the vertical gust velocity, the gust-response-transfer-function and
   the rms-load-response, and report the design load factor and
   turbulence-psd ordinates of the continuous-turbulence-design criterion"
   -> continuous-turbulence-gust-loads 42.5 vs buffet-boundary-testing 9.0
   / gust-maneuver-loads 9.0, margin 33.5 (strong)
2. "estimate the design gust loads of the airplane in continuous
   turbulence from the dryden-spectrum input and the
   gust-response-transfer-function: integrate the response power spectral
   density to the rms load factor, scale to the design turbulence
   intensity and report the equivalent discrete-gust velocity the
   gust-maneuver-loads envelope takes as input"
   -> continuous-turbulence-gust-loads 34.0 vs gust-maneuver-loads 19.5,
   margin 14.5 (clear)
ZERO-THEFT audit over all 1326 corpus tasks with both candidates in the
index: 0 displacements.
(f) Tag set, hyphenated compounds, no existing-tag duplication
(auto-audited = NONE): continuous-turbulence-gust-loads,
von-karman-spectrum, dryden-spectrum, turbulence-psd,
gust-response-transfer-function, power-spectral-density-gust-method,
rms-load-response, continuous-turbulence-design. Build-time fence note:
add routing rows to gust-maneuver-loads and random-vibration-analysis
related-leaves pointing continuous-turbulence / spectral-gust questions at
this leaf.
CONDITIONAL flag rationale (fresh evidence): the wave-45/46 aerodynamics
receipts and the sears spec assign the "PSD machinery home" label to
random-vibration-analysis; a reviewer holding that assignment as a vein
line may decline as same-vein or order extend-RV (mirror of the wave-48
laminate-bending-stiffness conditional, which landed at build).
Counter-evidence: RV implements SDOF base-excitation equipment screening
only (desc verbatim above), never aircraft continuous-turbulence gust
loads; gust-maneuver-loads is discrete-only; the family-state change this
probe documents touches no loads-pack leaf.

## Declines probed FRESH this session (receipts)

| Candidate seam | One-line reason (fresh evidence at this HEAD) |
|---|---|
| Composites: sandwich-panel additions (global buckling, dimpling, inserts, metallic faces) | STANDING wave-45/46 declines re-verified: empirical Hexcel/CMH-17 table content, 0 deterministic anchor; fresh corpus: dimpling/inserts/metallic-face/sandwich-global tokens = 0 of 1326; sandwich-panels at this HEAD owns face/core/wrinkling/core-selection; honeycomb-core-micromechanics (wave-48) now produces the core props it consumes |
| Composites: inter-laminar / free-edge stress analysis | 4 tree hits ALL incidental (edge-distance / free-edge shear-flow geometry / one composite-repair mention pointing interlaminar-damage-growth at delamination-growth); corpus 1 hit = shear-center "from the free edge" geometry task, not interlaminar stress; no clean closed-form anchor (free-edge stress field is Pipes-Pagano numerical / FE class); ILSS is coupon A-/B-basis test content in the cmh17-allowables vein; delamination-growth fences the energy-based failure mode |
| Composites: lamina-criteria additions (Hashin 2D fiber/matrix modes, Puck) | Tree 0 / corpus 0, but SAME-VEIN: failure-criteria pins the lamina-criteria contract (Tsai-Wu/Tsai-Hill/max-stress workflow, tags composite-lamina) - a 4th criterion is an extend-failure-criteria change, not a new-leaf seam (wave-47 ABD-vein adjudication precedent) |
| Composites: hygrothermal additions | OWNED: laminate-hygrothermal-response (laminate CTE/moisture swell/cure cooldown, on disk) + cmh17-allowables environmental conditioning/knockdown (desc verified); no fresh seam |
| Metallic structures remaining classic seams (Timoshenko shear beams, lateral-torsional & torsional-flexural buckling, structural shear-lag, stiffened-panel wide column, plate bending/vibration/pure-bending/biaxial, external-pressure cylinders, n-cell torsion, closed-cell restrained warping, Saint-Venant solid torsion, determinate beam deflection, beam-on-elastic-foundation, grillage/ring-frame, stress-concentration/hoop, pressure cabin barrel, thermal rings/frames/transients, secant-formula, Clapeyron 3-moment, tangent-modulus column) | STANDING wave-45/46/47/48 decline rows re-verified at this HEAD; the +2 wave-48 composites leaves touch none; no fresh counter-evidence in any grep this session |
| Joints/fasteners generic + additions (Huth flexibility, torque-tension/preload, prying/weld/gusset, oblique lugs) | OWNED comprehensively (metallic-fastener-joints shear bolt groups, lug-joint-analysis, composite-bolted-joints bearing/bypass, adhesive-bonded Volkersen, peel-stress-bonded Goland-Reissner, composite-repair scarf, shrink-fit, hertzian + elliptical-hertz contact) + standing rows re-verified; Huth = empirical fits, torque-tension = Shigley-class with 0 aerospace corpus demand (wave-45/46 rows) |
| Fatigue/fracture: overload crack-growth RETARDATION (Wheeler / Willenborg) | FRESH: tree 0 real owners (only walker-forman-crack-growth "compressive-mean retardation" language - R-ratio mean correction, different identity), corpus 0, never adjudicated as a structures seam - DECLINE same-vein as the standing Elber/da-dN threshold row: a crack-growth model-family extension beyond the owned Paris/Walker-Forman laws, semi-empirical fitted exponents |
| Fatigue: fretting fatigue | FRESH: tree 0 (only manufacturing-quality acoustic-emission NDT, unrelated), corpus 0, no closed-form anchor (fretting-strength knockdown is empirical S-N content) |
| Fatigue: thermal fatigue / thermo-mechanical fatigue | FRESH: tree 0, corpus 0; empirical interaction content in the standing creep-fatigue decline class; creep-rupture owns the elevated-temperature vein |
| Materials: stress-corrosion cracking (SCC) analysis | Tree 1 file = material-selection corrosion-awareness only; corpus 0; no deterministic closed-form design anchor (test/life-management + MMPDS table content); the only state mention is NDT leak-testing noise in a wave-45 manufacturing-quality receipt |
| Fatigue/damage-tolerance: EPFM J/CTOD/R-curve, Elber/da-dN threshold, multiaxial fatigue criteria, Gerber/Soderberg, sonic/acoustic fatigue, creep-fatigue, crack-growth life integration | STANDING rows re-verified; goodman-diagram desc owns the mean-stress vein incl. Goodman/Gerber/Soderberg lines; crack-growth owns Paris integration (life projection); random-vibration-analysis + random-vibration-fatigue own the PSD-to-damage chain |
| Aeroelastic divergence / flutter / control-surface reversal / dynamic gust response | OWNED OUTSIDE this family: skills/aerodynamics/aeroelasticity/ = 5 leaves on disk at this HEAD (divergence-speed, flutter-speed-prediction, aeroelastic-gust-response, sears-function-gust-lift, added-mass-coefficients-potential-flow); not a structures seam (wave-47/48 rows re-verified fresh); the PSD DESIGN-LOADS slice is GO-2 above, a different identity |
| Landing loads: spin-up / spring-back / side-load dynamic cases, shimmy / gear-walk, oleo / shock-strut internals, nose-gear steering | STANDING vehicle-design rows (wave-45 task-9, wave-46 task-9, wave-47 task-4, wave-48 task-4, read in full): spin-up/springback/side-load DECLINED with "structures landing-ground-loads owns level/braked/tail-down/one-wheel reaction families; corpus 0" (fresh corpus spin-up/spring-back = 0 of 1326; landing-ground-loads desc at this HEAD unchanged: static nose/main-gear reactions, level landing limit inertia, tail-down, one-wheel, braked roll - no dynamic-drop content); shimmy/gear-walk no closed-form anchor; oleo internals = drop-test verification (FAR 25.723, fenced by vehicle-design landing-gear-sizing energy check); nose-gear steering corpus hits route elsewhere. Seam set CLOSED cross-family |
| CLT A-matrix-level, laminate B/D additions, honeycomb-core additions | OWNED / CLOSED: laminate-stiffness (A of symmetric), laminate-bending-stiffness (B/D, wave-48), honeycomb-core-micromechanics (wave-48); any further slice (e.g. curved laminates) has no corpus demand or closed-form anchor |

## Closed-veins notes (fresh re-verification)

- Wave-48 GO seams own their seams on disk at this HEAD (verified in
  Scope): honeycomb-core-micromechanics and laminate-bending-stiffness
  each carry router rows and contract tests; their descs quote the
  consumer hand-off ("the equivalent core properties the sandwich panel
  workflow collects as given inputs"; "the D11 D22 D12 and D66 bending
  terms the laminate plate buckling analysis takes as given inputs").
- FPF-related-laminate-strength chain state: unidirectional-lamina-
  micromechanics (constants from constituents) -> laminate-stiffness (A)
  -> laminate-bending-stiffness (B/D) -> laminate-first-ply-failure (first
  event, Tsai-Wu) -> failure-criteria (single-ply index from given
  stresses). The OPEN end of that chain is the multi-event march = GO-1.
- Loads pack: gust-maneuver-loads (discrete + V-n), landing-ground-loads
  (certification reaction families), random-vibration-analysis (SDOF
  base-excitation), shock-response-spectrum. The OPEN end is the
  continuous-turbulence PSD method = GO-2 (conditional).
- Pack coverage per wave-45/46/47/48 receipts re-verified on disk at this
  HEAD across composites (15), damage-tolerance (5), fatigue (7), fem
  (26), loads (4), materials (8), thermal-structures (2).

## Standards-map check

30 ids present. GO-1 references cmh-17 (+ far-25), GO-2 references far-25
(+ cs-25) - both existing ids under the standing reference-only convention
(STANDARDS-REF, gated false, as carried by FPF and gust-maneuver-loads).
No new ids invented.

## Method note

All greps and scans were read-only; none touched the repo beyond reading.
Helper sim kept to /tmp (w49_st_sim.py): exact router_eval.py replication
(tag 3 / name 2 / desc 1 / body 0.5, verbatim-phrase bonus 4, tie-break
path asc) over the real 667-file index plus both hypothetical candidates;
harness equivalence proven by the baseline gate5 Hit@1 = 1326/1326 at HEAD
with no candidates. Margins: GO-1 36.5/31.5, GO-2 33.5/14.5; zero-theft
1326/1326 for both candidates together; candidate tag sets auto-audited
against the union of all indexed tags (no duplications); desc lengths 893
and 983 chars (<= 1000). Raw substring scans over eval/hit1-corpus.yaml
(1326 blocks) used for every corpus claim; zero-demand refers to current
tasks, each GO leaf adds two at build per wave doctrine. Full texts read
from disk at this HEAD: both wave-48 GO leaves, laminate-first-ply-failure
(desc + pitfalls + related leaves), failure-criteria, delamination-growth,
laminate-stiffness, sandwich-panels, gust-maneuver-loads,
random-vibration-analysis, landing-ground-loads, the wave-33 FPF spec, the
wave-45/46 aerodynamics receipts and sears-function spec, the wave-45/46/
47/48 vehicle-design receipts, and the wave-47/48 structures receipts.
Receipt sanitized: no machine-local absolute paths, no personal data.
