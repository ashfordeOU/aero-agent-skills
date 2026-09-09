# WAVE-48 STRUCTURES EXTENSION-PROBE RECEIPT (task-5, whole-family FRESH)

- Repo: the local AeroSkills repo (home-relative ~/AeroSkills). Probe HEAD
  verified: `git log --oneline -1` = 92d84a48 ("ops: stage wave-48 brief
  (planning only — daylight dispatch 10:00 CEST)"), `git rev-parse HEAD` =
  92d84a4807aceb8de148f05cb1ff6270608fedd5. Working tree clean except the
  untracked ops/automation/state/wave48-recon/ receipts dir (task-0..task-4
  sibling receipts on disk when this probe ran; task-5 is this file).
- Scope: ENTIRE structures family (LARGEST family, 65 leaves, 7 packs),
  probed FRESH, read-only. One write only: this receipt.
- Leaf count re-verified at HEAD: `find skills/structures -mindepth 3 -name
  SKILL.md | wc -l` = 65; router parity `grep -c '^| structures/'
  skills/structures/SKILL.md` = 65. Pack census: composites 13,
  damage-tolerance 5, fatigue 7, fem 26, loads 4, materials 8,
  thermal-structures 2 (= 65). Wave-47 added
  composites/unidirectional-lamina-micromechanics and
  materials/creep-stress-relaxation; BOTH on disk at this HEAD owning
  their seams (re-verified below) — the only family state change since
  the wave-46 whole-family receipt.
- Corpus baseline parsed FRESH at HEAD: eval/hit1-corpus.yaml = 1306 task
  blocks; standards map 30 ids (`grep -c '^  - id:'` each); far-25 line
  16, cs-25 line 27, mmpsd line 160, cmh-17 line 281. Whole-repo leaf
  count 645.
- Prior-wave context read FIRST: wave-47 structures receipt
  (ops/automation/state/wave47-recon/task-5-receipt.md) and wave-46
  structures receipt (wave46-recon/task-11-receipt.md), both in full;
  wave-45 task-10 decline rows read for the standing list. Every gate
  below was re-derived FRESH this session at this HEAD.
- Extension-trigger context: wave-48 primary pool from tasks 0-4 = 7 GO
  (task-0 flight-mechanics NO_CANDIDATES, task-1 avionics 1, task-2
  propulsion 1, task-3 gnc-autonomy 3, task-4 vehicle-design 2), below
  the ~12 viability line — this structures probe runs as the first
  extension tier per the wave-48 brief.

## Verdict

2 ranked GO candidates, both deterministic closed-form PRODUCER seams in
the composites pack (a leaf whose sibling consumers take its output as a
GIVEN workflow input — the wave-46/47 producer pattern), both never
adjudicated in any wave-41..47 receipt, spec, or leaf plan (grep-verified
zero hits below):

1. **structures/composites/honeycomb-core-micromechanics** (GO, rank 1,
   strong): predict the equivalent mechanical properties of an aerospace
   hexagonal honeycomb core from cell geometry + foil material — relative
   density of the hexagonal cell with double-thickness vertical walls
   rho*/rho_s = (t/l)(h/l+2)/(2 cos(theta)(h/l+sin(theta))) (regular
   hexagon h/l=1, theta=30 deg: (2/sqrt(3))(t/l)), out-of-plane stabilized
   compressive modulus E3 = E_s * rho*/rho_s, out-of-plane shear closed
   forms G13/G_s = (t/l) cos(theta)/(h/l+sin(theta)) and G23/G_s =
   (t/l)(h/l+sin(theta))/((h/l)^2 cos(theta)(2h/l+1)), in-plane
   cell-wall-bending moduli, and core density. sandwich-panels (the
   panel-level owner) collects "core modulus Ec, core shear modulus
   Gc" as GIVEN inputs at workflow step 1 and compares Gc/rho bands only
   for core SELECTION; nobody derives core properties from cell geometry.
   Same producer-seam pattern as the wave-47 GO-1.
2. **structures/composites/laminate-bending-stiffness** (GO, rank 2,
   CONDITIONAL): assemble the FULL classical-lamination-theory stiffness
   of a ply stack — A in-plane, B bending-extension coupling
   (B_ij = (1/2) sum Qbar_ij,k (z_k^2 - z_{k-1}^2)) and D bending
   (D_ij = (1/3) sum Qbar_ij,k (z_k^3 - z_{k-1}^3)) — for symmetric AND
   unsymmetric laminates. laminate-stiffness builds only "the A matrix for
   a symmetric laminate" (its desc, verbatim) and has NO B or D function;
   the consumer laminate-plate-buckling fixes "the CLT bending stiffness
   terms D11, D22, D12 and D66 (N m) of the laminate" as workflow-step-1
   INPUTS and says laminate-stiffness provides "the laminate stiffness
   synthesis that feeds the D terms" — an expectation the built leaf
   cannot satisfy: the implicit hand-off (wave-46/47 doctrine). Flagged
   CONDITIONAL because the wave-47 micromechanics spec FORBIDDEN TOKENS
   list assigns "abd-matrix ... classical-lamination-theory" vocabulary to
   laminate-stiffness; strict vein adjudication may hold the CLT line
   (wave-47 creep-stress-relaxation conditional precedent, which landed at
   build).

Everything else probed this session declines below; the wave-45 (16-row),
wave-46 (22-row) and wave-47 fresh decline rows re-verified STANDING — the
only family state change since wave-46 is the +2 wave-47 leaves, whose
seams are disjoint from every decline row (both re-verified on disk
below). 65 leaves is genuinely thinning: two never-adjudicated producer
seams (one strong, one conditional) is the honest yield of this
whole-family FRESH pass.

## Ranked GO candidate 1: structures/composites/honeycomb-core-micromechanics

Hexagonal-cell equivalent-property prediction (formula detail in the
Verdict item 1): given the cell geometry (wall thickness t, edge length l,
cell height h, cell angle theta, double-thickness vertical walls), the
foil properties (E_s, G_s, rho_s) and the cell size, compute relative
density, out-of-plane compressive modulus E3, out-of-plane shear moduli
G13/G23 (ribbon and transverse), in-plane cell-wall-bending moduli and
core density — exactly the properties sandwich-panels consumes as its
given Ec/Gc inputs. Stdlib arithmetic only; no datasheet tables reproduced
(Hexcel/CMH-17 bands referenced only).

(a) Zero-owner grep evidence, WHOLE skills/ tree (all 12 families) plus
eval/, run FRESH this session:

```
$ grep -rilE "gibson|cell-wall|relative-density|hexagonal-cell" skills/ --include=SKILL.md
(no output — zero files; no leaf predicts core properties from cell geometry)
$ grep -ril "honeycomb" skills/ --include=SKILL.md
skills/structures/composites/laminate-hygrothermal-response/SKILL.md
skills/structures/composites/sandwich-panels/SKILL.md
```
The only honeycomb content in the tree: sandwich-panels (panel-level
ANALYSIS, core props as given inputs, core SELECTION honeycomb vs foam)
and one incidental related-leaf line in laminate-hygrothermal-response;
material-selection carries zero hits. Corpus scans:
```
$ grep -icE "gibson|cell-wall|relative-density|foil-thickness|cell-size" eval/hit1-corpus.yaml
0   (zero of 1306 task blocks)
$ grep -c "honeycomb" eval/hit1-corpus.yaml
2   (sandwich-panels core-SELECTION tasks — the owned slice)
```
Adjudication-history scan: grep -rilE "gibson|honeycomb|cellular" over
ops/automation/state/wave4*-recon/, wave4*-leaf-plan.md, wave4*-specs/ =
zero hits — NEVER adjudicated in wave-41..47. The wave-45/46 "sandwich
additions" declines (metallic faces, insert loads, dimpling) were
empirical CMH-17 table content, a different slice; standing.

(b) Nearest sibling fences (quoted verbatim at this HEAD):
- sandwich-panels workflow step 1 (lines 62-65): "1. Collect the
  configuration: face modulus Ef and poisson ratio nu, face thickness t,
  core thickness c, core modulus Ec, core shear modulus Gc, and the loads
  (moment M, shear V, or distributed load q over span L)." — the core
  moduli are COLLECTED INPUTS; the leaf never derives them.
- sandwich-panels domain (lines 56-58): "Core selection: honeycomb wins on
  specific shear stiffness (Gc/rho, typically 3-10x foam)..." and workflow
  step 7 (lines 77-79): "Select the core type with select_core:
  weight-critical flat panels favor honeycomb, [foam for] impact- or
  moisture-critical or contoured parts." — Gc/rho is compared as a given
  band, never predicted from geometry.
- Producer-pattern precedent in-pack: unidirectional-lamina-micromechanics
  related-leaves (lines 154-157): laminate-stiffness "consumes E1, E2,
  nu12 and G12 as workflow step 1 inputs...; this leaf produces those four
  constants, it never assembles stiffness matrices." The honeycomb core
  leaf is the same relationship to sandwich-panels' step-1 Ec/Gc inputs.
No composites leaf in the 13-leaf pack predicts core properties; the
wave-45 pack closure was per-seam coverage and this seam is not in it
(cell-geometry closed forms are deterministic, unlike the empirical
declined sandwich additions).
(c) Standards-map id exists (grep-verified): cmh-17 at line 281, far-25
line 16, cs-25 line 27. Sibling precedent: micromechanics carries cmh-17;
sandwich-panels carries far-25 + cs-25 (all reference-only, gated false).
cmh-17 is the natural id (CMH-17 vol. 6 core conventions).

(d) Published deterministic anchor: Gibson & Ashby, Cellular Solids:
Structure and Properties, 2nd ed., CUP 1997, ch. 4 "Honeycomb materials":
hexagonal-cell relative-density closed form with double-thickness vertical
walls, E3 = E_s (rho*/rho_s), and the out-of-plane shear closed forms
G13/G23 quoted above; regular-hexagon reductions rho*/rho_s =
(2/sqrt(3))(t/l), G13 = G23 = G_s (rho*/rho_s)/2. Deterministic geometry
arithmetic only; Hexcel/CMH-17 core property bands are reference context,
never reproduced tables. Magnitudes verifiable: regular-hex aluminum core
with t/l = 0.02 gives rho*/rho_s = 0.0231, so a 5056 foil (E_s ~ 72 GPa,
rho_s ~ 2640 kg/m^3) predicts E3 ~ 1.66 GPa and core density ~ 61 kg/m^3 —
order-of-magnitude inside the published mid-density 1/8-inch 5056 core
band (magnitude-gate convention per wave-47).

(e) 2 wordable Hit@1 corpus queries, sim-verified with the deterministic
token router (router_eval.py replication; weights in the method note) over
the REAL 657-file index plus the hypothetical candidate:
1. "predict the equivalent-core-properties of the 3.2 mm cell 5056
   aluminum honeycomb core with 0.038 mm foil thickness for the sandwich
   panel: the relative-density, the out-of-plane stabilized compressive
   modulus and the out-of-plane shear moduli from the gibson-ashby
   hexagonal-cell closed forms with the double-thickness vertical cell
   walls and the foil modulus and density inputs for the core-shear
   margin"
   -> honeycomb-core-micromechanics 37.5 vs sandwich-panels 29.5, margin
   8.0 (strong)
2. "compute the honeycomb-core shear modulus G13 and G23 and the core
   density of the 1-8 inch cell 7075 foil core from the cell geometry, the
   cell-wall thickness to edge-length ratio and the foil shear modulus by
   the hexagonal-cell closed forms, the equivalent-core-properties the
   sandwich-panels workflow collects as given inputs"
   -> honeycomb-core-micromechanics 28.5 vs sandwich-panels 17.5, margin
   11.0 (strong)
ZERO-THEFT audit over all 1306 corpus tasks with both candidates in the
index: 0 displacements; the 2 existing honeycomb corpus tasks stay owned
by sandwich-panels.

(f) Tag set, all hyphenated compounds, none duplicating an existing tag
string (composites-pack union checked; wave-47 spec fenced bare "core-
shear, face-wrinkling, sandwich" analysis vocabulary to sandwich-panels —
these are the cell-geometry producer compounds, disjoint):
honeycomb-core-micromechanics, hexagonal-honeycomb-cell,
gibson-ashby-closed-forms, equivalent-core-properties,
out-of-plane-shear-modulus, stabilized-compressive-modulus,
relative-density, double-thickness-cell-walls, core-density-prediction.
Build-time fence note: add one routing bullet to sandwich-panels pointing
cell-geometry / core-property-prediction questions at this leaf
(wave-45 routing-line precedent).

## Ranked GO candidate 2: structures/composites/laminate-bending-stiffness (CONDITIONAL)

As in Verdict item 2: full-CLT stack synthesis (A/B/D matrices from
per-ply rotated stiffness and ply z coordinates), reporting the
D11/D22/D12/D66 terms laminate-plate-buckling takes as given, equivalent
laminate engineering constants of symmetric balanced stacks, and the B
coupling check for unsymmetric stacks.

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/, FRESH:
```
$ grep -rl "D66" skills/ --include=SKILL.md
skills/structures/composites/laminate-plate-buckling/SKILL.md
   (the ONLY hit is the CONSUMER — no leaf computes D66)
$ grep -rilE "bending-extension|coupling-stiffness|z-cubed|unsymmetric-laminate" skills/ --include=SKILL.md
(no output — zero files)
$ grep -inE "d-matrix|D11|ABD" eval/hit1-corpus.yaml
line 4901: "compute the laminate-plate-buckling critical compression load of
the composite skin panel from the clt d-matrix with half-wave mode minimization"
   (the d-matrix is a GIVEN input there; nothing in the corpus computes a D or B matrix)
```
Adjudication-history scan: grep -rilE "d-matrix|abd|laminate-bending|D11"
over wave4*-recon/ and wave4*-leaf-plan.md = zero meaningful hits (wave48
task-3 "D11-feedthrough" is gnc control theory; wave40 cargo "LD11" is an
LD-11 container); only the wave-47 micromechanics SPEC vocabulary list
mentions abd-matrix — evidence for the conditional flag below.

(b) Nearest sibling fences (quoted verbatim at this HEAD):
- laminate-stiffness desc (line 3): "...build the ply stiffness from the
  material constants, rotate it to the ply angle, and assemble the A
  matrix for a symmetric laminate. Produces the ply stiffness, the rotated
  stiffness with coupling terms, and the laminate A matrix..." Its
  workflow (lines 42-47) implements only ply_stiffness,
  rotated_ply_stiffness, laminate_a_matrix — no B or D function exists;
  tags pin it: laminate-a-matrix, symmetric-laminate.
- laminate-plate-buckling workflow step 1 (lines 60-62): "1. Fix the
  panel inputs: the load-direction length a, the width b, and the CLT
  bending stiffness terms D11, D22, D12 and D66 (N m) of the laminate."
  and its body (lines 30-32): "...with structures/composites/
  laminate-stiffness for the laminate stiffness synthesis that feeds the
  D terms..." — the consumer ATTRIBUTES the D synthesis to
  laminate-stiffness, which cannot produce it: the implicit hand-off
  (wave-46 GO-2 / wave-47 GO-1 pattern).
- laminate-first-ply-failure (symmetric balanced in-plane only, per its
  desc: "recover the mid-plane strains of a symmetric balanced laminate
  from its in-plane compliance") and laminate-hygrothermal-response
  (in-plane CTE/CME vein) neither need nor own B/D.

(c) Standards-map id exists (grep-verified): cmh-17 line 281; far-25 line
16, cs-25 line 27 — composite-pack convention (laminate-stiffness carries
far-25 + cs-25; micromechanics sibling carries cmh-17; all
reference-only, gated false).

(d) Published deterministic anchor: Jones, Mechanics of Composite
Materials, 2nd ed., ch. 2 (CLT ABD assembly); Herakovich, Mechanics of
Fibrous Composites, ch. 5. Exact closed-form arithmetic on the ply stack
geometry — the same identity class as the A assembly laminate-stiffness
implements; no empirical content, no tables. Magnitude check: the
isotropic reduction reproduces D = E t^3/(12(1-nu^2)), the convention
laminate-plate-buckling uses in its sanity check.

(e) 2 wordable Hit@1 queries, sim-verified with the deterministic router
(real index + hypothetical candidate):
1. "compute the laminate d-matrix bending stiffnesses D11 D22 D12 and D66
   of the 8-ply carbon-epoxy stack from the rotated ply stiffnesses and
   the ply z-coordinate z-cubed thickness integrals by classical lamination
   theory, the laminate-bending-stiffness inputs the laminate plate
   buckling analysis takes as given"
   -> top1 laminate-bending-stiffness 37.0, top2 laminate-plate-buckling
   24.0, margin 13.0 (strong)
2. "assemble the full clt stiffness of the unsymmetric laminate stack: the
   in-plane a-matrix, the bending-extension coupling b-matrix and the
   bending d-matrix from the ply stack geometry, and the equivalent
   laminate bending stiffness of the symmetric angle-ply for the
   laminate-bending-response check"
   -> top1 laminate-bending-stiffness 24.0, top2 sandwich-panels 11.0,
   margin 13.0 (strong)
ZERO-THEFT audit over all 1306 corpus tasks with both candidates in the
index: 0 displacements (all existing laminate tasks keep their top-1).

(f) Tag set, all hyphenated compounds, no existing-tag duplication
(laminate-stiffness tags: composite-laminate, classical-lamination-theory,
ply-stiffness, laminate-a-matrix, symmetric-laminate, composites — no
collision):
laminate-bending-stiffness, clt-abd-matrices, laminate-d-matrix,
bending-extension-coupling, unsymmetric-laminate-analysis,
laminate-bending-response, d11-d22-d12-d66,
equivalent-laminate-bending-stiffness.
CONDITIONAL flag rationale (fresh evidence): the wave-47 micromechanics
spec FORBIDDEN TOKENS list (unidirectional-lamina-micromechanics.md lines
494-499) assigns "abd-matrix, classical-lamination-theory ... any claim
that computes the ply or laminate stiffness from the constants
(laminate-stiffness owns the stiffness assembly...)" to laminate-stiffness;
a reviewer holding the vein line strictly may decline this as same-vein or
order an extend-laminate-stiffness instead (mirror of the wave-47
creep-stress-relaxation conditional, which landed at build).
Counter-evidence: laminate-stiffness as BUILT (and desc/tag-pinned) cannot
express B or D — no functions, symmetric-A-only contract, and its own
consumer mis-attributes the D synthesis to it.

## Declines probed FRESH this session (receipts, gate letters)

| Candidate seam | Gate(s) | One-line reason (fresh evidence at this HEAD) |
|---|---|---|
| Fatigue/damage-tolerance crack-growth LIFE integration (Paris da/dN closed-form integration) | b | OWNED, not a gap: damage-tolerance/crack-growth desc line 3 "project the cycles to grow the crack from the initial detectable size to the critical size"; workflow steps 3-4: "Project the extension over the cycle block with crack_growth_per_cycle. Estimate the crack growth life with cycles_to_grow." (lines 53-57); Y = 1.12 edge-crack convention (domain lines 31-33); 13 corpus blocks route crack-growth tokens inside the pack |
| Structural joints (generic bolted/riveted/adhesive) | b | OWNED comprehensively: metallic-fastener-joints desc line 3 "split the applied load into the per-fastener share of a symmetric bolt or rivet pattern... resolve an eccentric bolt group by the polar moment method"; lug-joint-analysis (round-end axial family), composite-bolted-joints, adhesive-bonded + peel-stress-bonded own the rest; wave-45 prying/weld/gusset + Huth + oblique-lug rows re-verified STANDING (Huth = empirical fits; prying/weld = Shigley-class; fresh corpus scan: torque-tension/preload-torque analysis tokens = 0 of 1306, only manufacturing-quality as910x/9103 process hits in skills/) |
| Classical lamination theory at the A-matrix level | b | OWNED: laminate-stiffness (desc line 3 verbatim in GO-2 above) builds ply Q, rotates, assembles A of symmetric laminates; the genuinely absent slice is the B/D/unsymmetric synthesis = rank-2 GO, not a separate decline |
| Plates/shells closed-form additions (plate bending, biaxial/pure-bending buckling, plate vibration, external-pressure cylinders) | b/d | OWNED + standing: fem/plate-buckling owns the flat-plate k-coefficient family incl. shear and combined compression-shear with effective width; laminate-plate-buckling the orthotropic energy-method family; cylindrical-shell-buckling the NASA SP-8007 curved-shell family (axial/bending/ovalization); wave-44 plate-bending, wave-45 pure-bending/biaxial + external-pressure, wave-46 plate-vibration declines re-verified STANDING (coefficient-table content + 0 demand; fresh corpus scan: plate-bending tokens = 0 of 1306) |
| Aeroelastic divergence / flutter / control-surface reversal | b | OWNED OUTSIDE this family: the aerodynamics family's aeroelasticity pack is on disk at this HEAD (divergence-speed, flutter-speed-prediction, aeroelastic-gust-response, sears-function-gust-lift, added-mass-coefficients-potential-flow under skills/aerodynamics/aeroelasticity/); not a structures seam (wave-47 row re-verified fresh) |
| Lamina STRENGTH micromechanics (constituent -> lamina allowables) | a/d/vein | No clean deterministic closed-form identity: matrix-dominated modes (transverse tension, ILSS) are interface + coupon-test content — cmh17-allowables' contract is A/B-basis statistics on coupon data; a longitudinal-ROM-only leaf is a half-leaf; fresh greps zero: "fiber.*strength.*volume|sigma.*fu|rosette|rosen" = 0 files, 0 corpus blocks; vein-adjacent to the on-disk micromechanics leaf, whose Related-leaves (lines 158-159) hand strength USAGE to failure-criteria and whose tag constituent-property-prediction covers the constituent vein |
| Elastic bolted-joint tension/preload analysis (T = K D F torque-tension, joint stiffness load sharing, separation) | b/d | Shigley-class machine-design content, 0 aerospace analysis corpus demand (torque-tension tokens = 0 of 1306); swept by the standing wave-45 prying-action decline row; elevated-temperature preload RETENTION is now OWNED by the on-disk materials/creep-stress-relaxation (desc line 3: "the retained-preload fraction after the hold... for bolted joints, spring preloads and interference-fit fasteners"); metallic-fastener-joints is shear-mode-only |
| All other wave-45/46/47 decline rows (Timoshenko shear beams, torsional-flexural & lateral-torsional buckling, structural shear-lag, multiaxial fatigue criteria, Gerber/Soderberg, EPFM J/CTOD/R-curve, Elber/da-dN threshold, Huth flexibility, n-cell torsion, closed-cell restrained warping, sandwich global buckling/dimpling/inserts/metallic faces, stiffened-panel wide column, plate pure-bending/biaxial, external-pressure cylinders, plate bending, plate vibration, prying/weld/gusset, oblique lugs, Saint-Venant solid torsion, determinate beam deflection, beam-on-elastic-foundation, grillage/ring-frame, stress-concentration/hoop, creep-fatigue, thermal rings/frames/transients, pressure cabin barrel, sonic/acoustic fatigue, tangent-modulus column, Clapeyron 3-moment, secant-formula, laminate notched strength/CAI/impact) | standing | STANDING: family state change since the wave-46 receipt = the +2 wave-47 leaves only, both ON DISK owning exactly their adjudicated seams (below); no decline row's seam is touched by either; spot greps this session found zero counter-evidence |

## Closed veins and wave-47 GO seams (fresh re-verification)

- unidirectional-lamina-micromechanics (wave-47 GO-1, on disk) owns the
  constituent -> lamina-constant seam (ROM E1/nu12/density, Halpin-Tsai
  E2/G12, Voigt-Reuss/Hashin-Shtrikman bands); Related-leaves fence
  (lines 154-166) hands assembly to laminate-stiffness and strength USAGE
  to failure-criteria; it stops at density.
- creep-stress-relaxation (wave-47 GO-2, on disk) owns the fixed-strain
  Norton relaxation seam (retained-preload fraction / retention-margin
  contract; desc line 3 closed form).
- Wave-46 GO seams closed on disk: elliptical-hertz-contact (hertzian
  carve-out "Unequal crossed radii give the general elliptical patch of
  the Hertz elliptic integrals, out of scope here" still present);
  crack-tip-plasticity-correction (fracture-toughness still quotes the
  E399 2.5*(K/sigma_ys)^2 rule without computing the zone).
- Pack coverage per wave-45/46 receipts re-verified on disk at this HEAD
  across composites (13), damage-tolerance (5), fatigue (7), loads (4),
  materials (8), fem (26), thermal-structures (2). The honeycomb-core
  seam (GO-1) and the laminate B/D seam (GO-2) are the two
  never-adjudicated producer slices this pass found.

## Standards-map check

30 ids present. GO-1 and GO-2 reference existing ids only: cmh-17 (line
281), far-25 (line 16), cs-25 (line 27) — the standing composite-pack
reference-only convention (STANDARDS-REF, gated false, as carried by
unidirectional-lamina-micromechanics and laminate-stiffness). No new ids
invented.

## Method note

All greps and scans were read-only; none touched the repo beyond reading.
Helper script kept to /tmp (w48_router_sim.py, real output above); no repo
file modified; git HEAD remained 92d84a48 throughout; git status
before/after shows only the untracked wave48-recon receipts. Enumeration,
pack census, router parity, corpus baseline and standards-map ids
re-derived at this HEAD. Full texts read from disk at this HEAD: both
wave-47 GO leaves, laminate-stiffness, laminate-plate-buckling,
laminate-hygrothermal-response, sandwich-panels, crack-growth,
metallic-fastener-joints, random-vibration-analysis, creep-stress-
relaxation, the wave-45/46/47 structures receipts and the wave-47
micromechanics spec. The Hit@1 sim replicates scripts/router_eval.py
exactly (tag 3 / name 2 / desc 1 / body 0.5, verbatim-phrase bonus 4,
tie-break path asc) over the real 657-file index plus the hypothetical
candidates: margins 8.0/11.0 (GO-1), 13.0/13.0 (GO-2), 0-theft over all
1306 corpus tasks. Raw substring scans over eval/hit1-corpus.yaml used
for every corpus claim; zero-demand refers to current tasks, each GO leaf
adds two at build per wave doctrine. Receipt sanitized: no machine-local
absolute paths.
