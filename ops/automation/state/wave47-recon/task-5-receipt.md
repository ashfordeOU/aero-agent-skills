# WAVE-47 STRUCTURES EXTENSION-PROBE RECEIPT (task-5, whole-family FRESH)

- Repo: the local AeroSkills repo (home-relative ~/AeroSkills). Probe HEAD
  verified `git log --oneline -1` = a4ae6d1e ("Wave-47: close-out must
  auto-update products-state (FIX)"), `git rev-parse HEAD` =
  a4ae6d1eebf231bc729179626805f78f26c01039. The wave-47 dispatch baseline
  a544f421 is HEAD's direct parent; `git diff --name-only a544f421..HEAD`
  touches only ops/automation/wave47-brief.md (ops-only FIX), so the skill
  tree probed is byte-identical at both commits. Working tree clean at
  probe start; the wave47-recon receipts dir is the only untracked state.
- Scope: ENTIRE structures family (LARGEST family, 63 leaves, 7
  sub-packs), probed FRESH, read-only. No writes to skills/, eval/,
  standards-map.yaml, scripts/, Makefile, or ops/automation briefs. One
  write only: this receipt.
- Leaf count re-verified at HEAD: `ls skills/structures/*/*/SKILL.md` = 63
  and `find skills/structures -mindepth 3 -name SKILL.md | wc -l` = 63.
  Pack census: composites 12, damage-tolerance 5, fatigue 7, fem 26,
  loads 4, materials 7, thermal-structures 2. Family router parity
  re-verified: `grep -c '^| structures/' skills/structures/SKILL.md` = 63.
  Wave-46 added elliptical-hertz-contact (fem) and
  crack-tip-plasticity-correction (materials) = the new sibling fences
  this probe re-checks around every candidate.
- Corpus baseline parsed FRESH at HEAD: eval/hit1-corpus.yaml = 1286 task
  blocks (`grep -c '^  - id:'` = 1286). Raw substring scans used
  throughout; zero-demand refers to current tasks (each GO leaf carries
  two new tasks at build per wave doctrine).
- Standards map: 30 ids (`grep -c '^  - id:' standards-map.yaml` = 30).
  far-25 line 16, cs-25 line 27, mmpsd line 160, cmh-17 line 281.
- Prior-wave context read first (wave-45 task-10 and wave-46 task-11
  structures receipts) only to know which veins carry standing declines;
  every gate below was re-derived FRESH this session at this HEAD.
  Wave-46 task-11 added elliptical-hertz-contact (rank-1 GO then) and
  crack-tip-plasticity-correction (rank-2 GO then); both are ON DISK at
  this HEAD and own their seams (re-verified below).
- Extension-trigger context: wave-47 primary pool from tasks 0-4 = 8 GO
  (flight-mechanics 1, avionics 1, propulsion 1, gnc-autonomy 4,
  vehicle-design 1), below the ~12 viability line, so this structures
  extension probe runs per the wave-47 brief pool-drop rule.

## Verdict

2 ranked GO candidates, both deterministic closed-form producer-side
seams NEVER adjudicated in any wave-41..47 recon receipt, spec, or leaf
plan (grep-verified zero token hits below):

1. **structures/composites/unidirectional-lamina-micromechanics** (GO,
   rank 1, strong): predict the unidirectional lamina engineering
   constants from the fiber and matrix CONSTITUENT properties and the
   fiber volume fraction - longitudinal modulus and Poisson ratio by the
   rule of mixtures, transverse modulus and in-plane shear modulus by the
   Halpin-Tsai closed forms with the standard shape factors, density by
   rule of mixtures, with closed-form Voigt/Reuss and Hashin-Shtrikman
   bounds as the sanity band. Every existing composites leaf consumes the
   lamina constants as GIVEN inputs (laminate-stiffness workflow step 1:
   "Collect ply engineering constants E1, E2, nu12, G12"); nobody
   anywhere derives them from constituents. Same producer-seam pattern as
   the wave-47 task-4 GO (component-weight-estimation: the producers of
   what every consumer leaf treats as input).
2. **structures/materials/creep-stress-relaxation** (GO, rank 2,
   CONDITIONAL): the Norton-law fixed-total-strain stress-relaxation
   closed form sigma(t) = [sigma_0^(1-n) + (n-1)*A*E*t*exp(-Q/(R*T))]^(1/(1-n))
   for the decay of a preloaded stress at elevated temperature (bolted
   joint preload retention, spring preload, interference-fit relaxation).
   creep-rupture (the vein owner) is constant-stress-only - its
   accumulated-strain model eps_c(t) = eps_dot*t cannot answer a decaying
   -stress question - and never fences relaxation. Flagged CONDITIONAL
   because wave-46 framed creep-rupture as owning "the elevated-
   temperature vein": adjudication may hold the vein-ownership line
   against a same-vein sibling (compare the wave-47 task-3 rank-4
   conditional precedent). Deterministic anchor and all other gates are
   clean; drop it if the pool does not need it.

Everything else probed this session declines with fresh reasons below;
the wave-45 (16-row) and wave-46 (22-row) decline tables and their
closed-veins lists re-verified STANDING (the only family state change
since wave-46 is the +2 wave-46 leaves, whose seams are disjoint from
every decline row). The family at 63 leaves is genuinely thinning: two
never-adjudicated producer seams is the honest yield of a whole-family
FRESH pass.

## Ranked GO candidate 1: structures/composites/unidirectional-lamina-micromechanics

Predict unidirectional lamina elastic constants from constituent
properties: given fiber modulus Ef, matrix modulus Em, Poisson ratios
nuf, num, in-plane fiber shear modulus Gf, matrix shear modulus Gm, and
fiber volume fraction Vf (and densities/CTEs for the weight/hygrothermal
uses), compute the lamina engineering constants - longitudinal modulus
E1 = Vf*Ef + (1-Vf)*Em and Poisson ratio nu12 = Vf*nuf + (1-Vf)*num by
the rule of mixtures (Voigt), transverse modulus E2 and in-plane shear
modulus G12 by the Halpin-Tsai closed forms with the standard circular-
fiber shape factors xi_E2 = 2 and xi_G12 = 1 (eta = (Mr - 1)/(Mr + xi)
with Mr the constituent modulus ratio, E2/Em = (1 + xi*eta*Vf)/(1 -
eta*Vf)), density by rule of mixtures, and the Voigt/Reuss and
Hashin-Shtrikman closed-form bounds on E2 and G12 as the verifiable
envelope the prediction must fall inside. Stdlib arithmetic only, no
tables beyond the fixed published shape factors, no test-data fitting.
This leaf is the producer side of the lamina-constant chain: the whole
CLT stack (laminate-stiffness, laminate-first-ply-failure,
failure-criteria, laminate-plate-buckling, laminate-hygrothermal-
response) and the allowables stack (cmh17-allowables: "derive
laminate-level allowables from lamina allowables") take lamina constants
and lamina allowables as GIVEN; no leaf anywhere derives them from
constituent properties.

(a) Zero-owner grep evidence, WHOLE skills/ tree (all 12 families) plus
eval/, run FRESH this session (real output; every grep returned zero
files/zero lines, no leaf anywhere computes constituent-level lamina
prediction):

```
$ grep -rilE "halpin|micromechanic|rule.of.mixture|fiber.volume.fraction|constituent.properties|voigt.bound|reuss.bound" skills/
(no output - zero files)
$ grep -inE "halpin|micromechanic|rule.of.mixture|fiber.volume.fraction|constituent.properties" eval/hit1-corpus.yaml
(no output - zero of 1286 task blocks)
$ grep -rilE "micromechanic|halpin|rule.of.mixture" ops/automation/state/wave4*-recon/ ops/automation/state/wave47-recon/
(no output - NEVER adjudicated in any wave-4x recon, spec, or leaf plan)
$ grep -inE "fiber.{0,40}matrix|matrix.{0,40}fiber|volume.fraction" eval/hit1-corpus.yaml
(no output except one manufacturing-quality CT-scan porosity task - different domain)
```

The only composite-property computations anywhere in skills/ are
laminate-stiffness (CLT from GIVEN constants) and cmh17-allowables
(A/B-basis statistics from coupon TEST data, "lamina allowables" as
given inputs); cross-family scan of space-systems and cross-cutting for
composite/lamina/fiber content returns only export-control-awareness and
numerical-integration (incidental mentions, no owner).

(b) Nearest sibling fences (quoted, at this HEAD):
- laminate-stiffness desc: "build the ply stiffness from the material
  constants, rotate it to the ply angle..." and workflow step 1, body
  line: "1. Collect ply engineering constants E1, E2, nu12, G12." The
  constants are INPUTS; the leaf's Domain quick reference states "A ply
  has orthotropic stiffness in material axes: Q11, Q12, Q22, Q66 from
  the engineering constants" - derivation of those engineering constants
  from fiber/matrix is neither produced nor fenced, it is simply absent
  (the implicit hand-off the wave-46 GO-2 pattern admits).
- cmh17-allowables desc: "...derive laminate-level allowables from
  lamina allowables..." - lamina allowables are inputs; its input
  boundary is coupon test data, not constituent properties.
- material-selection (materials pack) body: "Representative band values
  (verify against MMPDS, AMS, or CMH-17 before design use; MMPDS
  design-value tables are never reproduced" - property VALUES are given
  reference bands, no prediction machinery.
No composites leaf in the 12-leaf pack (wave-45 coverage list:
sandwich/adhesive/peel/bolted/scarf/delamination/laminate-stiffness/FPF/
criteria/hygrothermal/plate-buckling/allowables) touches constituent-
level prediction; wave-45's pack closure was per-seam coverage, and this
seam is not in it.

(c) Standards-map id exists (grep-verified): cmh-17 at line 281 of
standards-map.yaml; far-25 line 16 and cs-25 line 27. Composite sibling
precedent for STANDARDS-REF reference-only blocks: cmh17-allowables
carries mmpsd + far-25 reference-only; laminate-stiffness carries far-25
reference-only; compliance STANDARDS-REF, gated false. cmh-17 is the
natural reference id (constituent and lamina property data conventions).

(d) Published deterministic anchor: Jones, Mechanics of Composite
Materials, 2nd ed., ch. 3 "Elastic Behavior of Unidirectional Composites"
(rule-of-mixtures E1/nu12/density, Halpin-Tsai E2/G12 with the standard
xi = 2 and xi = 1 circular-fiber shape factors); Halpin & Tsai, "Effects
of Environmental Factors on Composite Materials", AFML-TR-67-423 (1969);
Hashin, "Analysis of Properties of Fiber Composites with Anisotropic
Constituents", J. Appl. Mech. 46 (1979) (closed-form bounds); Daniel &
Ishai, Engineering Mechanics of Composite Materials (composite-cylinder
assemblage, worked T300/5208 and E-glass/epoxy examples). Magnitudes
verifiable: T300 carbon (Ef ~ 230 GPa) / 5208 epoxy (Em ~ 3.45 GPa) at
Vf = 0.60 gives E1 = 0.6*230 + 0.4*3.45 ~ 139 GPa by ROM and E2 ~ 9-10
GPa by Halpin-Tsai inside the Hashin bounds - the textbook worked-example
check. Rule-of-mixtures arm is exact; Halpin-Tsai is the published
closed form with fixed standard shape factors (in-repo precedent for
published semi-empirical constants: ramberg-osgood exponents, crippling
form factors, Johnson parabola all land as deterministic leaves). Public
engineering science, paraphrase only, no reproduced tables.

(e) 2 wordable Hit@1 corpus queries with distinctive hyphenated tokens
(checked against eval/hit1-corpus.yaml: zero raw hits for any token
below; the 85 existing lamina-token corpus tasks are CLT tasks starting
from given constants - e.g. w4x laminate-stiffness tasks "rotate the
lamina stiffness matrix...", "compute the laminate in-plane A matrix...
using the rotated ply-stiffness" - no constituent-prediction overlap, no
theft in either direction):

1. "predict the unidirectional-lamina stiffness properties of the
   T300/5208 ply at 0.60 fiber-volume-fraction by the rule-of-mixtures
   longitudinal modulus and Poisson ratio and the halpin-tsai transverse
   and in-plane shear moduli from the fiber and matrix constituent
   properties, then verify the transverse modulus against the
   hashin-shtrikman bounds"
2. "compute the E1, E2 and G12 lamina engineering constants of an
   E-glass-epoxy unidirectional ply from the fiber and matrix moduli,
   the fiber-volume-fraction and the standard halpin-tsai shape factors,
   and report the voigt-reuss bound band the transverse modulus must
   fall inside for the laminate-stiffness chain"

(f) No generic single-word or existing-tag overlap: proposed tags are
hyphenated compounds, none duplicating an existing tag string (checked
against the full composites-pack tag union: a-basis, ply-stiffness,
classical-lamination-theory, composite-lamina, laminate-a-matrix, etc. -
no halpin/rule-of-mixture/volume-fraction/micromechanic tag exists
anywhere):
unidirectional-lamina-micromechanics, rule-of-mixtures, halpin-tsai-
equations, fiber-volume-fraction, constituent-property-prediction,
voigt-reuss-bounds, hashin-shtrikman-bounds. Build-time fence note: add
one routing bullet to laminate-stiffness pointing constituent-level /
fiber-volume-fraction / "lamina constants from fiber and matrix"
questions at this leaf (wave-45 routing-line precedent).

## Ranked GO candidate 2: structures/materials/creep-stress-relaxation (CONDITIONAL)

Deterministic closed form for stress relaxation at fixed total strain in
a Norton-law creeping material: given the initial (preload) stress
sigma_0, the temperature T, the Norton constants A, n, Q and the elastic
modulus E, the relaxed stress after hold time t is
sigma(t) = [sigma_0^(1-n) + (n-1)*A*E*t*exp(-Q/(R*T))]^(1/(1-n)) for
n != 1 (closed-form integral of the d(sigma)/dt = -E*A*sigma^n*
exp(-Q/(R*T)) rate law), with the relaxed-stress fraction sigma/sigma_0,
the retained-preload margin and the time to relax to a fraction of the
preload. Sits beside creep-rupture (constant-stress rate/rupture) as the
fixed-strain sibling: preloaded bolted joints, spring preload and
interference-fit fasteners at elevated temperature.

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/, run FRESH
(real output, zero matches anywhere):

```
$ grep -rinE "stress.relaxation|creep.relaxation|preload.*relax" skills/ --include=SKILL.md
(no output - no leaf computes a relaxation)
$ grep -inE "stress.relaxation|creep.relaxation|preload.*decay" eval/hit1-corpus.yaml
(no output - zero of 1286 task blocks)
$ grep -rilE "stress.relaxation|creep.relaxation" ops/automation/state/wave4*-recon/
(no output - NEVER adjudicated in wave-41..47 recon)
```

(b) Nearest sibling fence (quoted, creep-rupture body at this HEAD):
"This leaf does NOT cover cyclic endurance (the structures/fatigue pack
owns cyclic life methods), constrained-expansion thermal stress, or
statistically based tensile design values (structures/materials/mmpsd-
allowables)." No relaxation carve-out exists because the model cannot
express one: the entire creep-rupture machinery is constant-stress
("Accumulated creep strain: eps_c(t) = eps_dot_c * t over the service
time (steady-state only...)"; workflow step 5 accumulates at the fixed
stress). A decaying-stress preload-retention question has no function in
creep-rupture's contract - the implicit hand-off, same pattern as the
wave-46 GO-2 (fracture-toughness quotes the plastic-zone size rule but
never computes the zone). CONDITIONAL flag: wave-46's decline row framed
creep-rupture as owning "the elevated-temperature vein"; a reviewer
holding the vein-ownership line strictly would decline this as a
same-vein sibling despite the distinct governing equation. Rank 2,
usable only if the pool needs it after GO-1 and the task-3-style
conditional passes adjudication.

(c) Standards-map id exists (grep-verified): mmpsd line 160, far-25 line
16 - the exact reference-only pair creep-rupture carries at this HEAD
(mmpsd + far-25, STANDARDS-REF, gated false).

(d) Published deterministic anchor: Norton-Bailey creep-rate law with
the constant-total-strain relaxation integral in the standard creep
treatments (Finnie & Heller, Creep of Engineering Materials, relaxation
chapter; Penny & Marriott, Design for Creep, ch. on stress relaxation;
ASME elevated-temperature design literature - relaxation of preload in
bolted joints at temperature). Deterministic closed-form algebra only;
no empirical tables. Magnitudes verifiable: with the creep-rupture
leaf's own default alloy constants (A = 2.0e-47, n = 7.0, Q = 360000
J/mol, E ~ 2.1e11 Pa) a 200 MPa preload at 600 C relaxes to roughly a
third of its initial value after ~10^4 s - a checkable order of
magnitude.

(e) 2 wordable Hit@1 corpus queries with distinctive tokens (checked
against eval/hit1-corpus.yaml: zero raw hits; the existing creep corpus
tasks w25-creep-rupture-1/2 carry larson-miller-parameter, norton-creep-
law, rupture-life tokens for the CONSTANT-stress life/margin question -
no relaxation tokens, no overlap in either direction):

1. "compute the creep-stress-relaxation of the 200 MPa bolt preload held
   at 600 C for 10000 seconds with the norton-relaxation closed form:
   the relaxed stress from the fixed-strain rate-law integral, the
   retained-preload fraction and the preload-retention margin"
2. "find the stress-relaxation time for the titanium fastener preload to
   decay to 80 percent of its initial value at the elevated temperature
   with the norton-power-law relaxation equation, and report the
   remaining preload after the design hold time"

(f) No generic single-word or existing-tag overlap (checked against the
materials-pack tag union - creep-rupture tags: creep-rupture,
norton-creep-law, steady-state-creep-rate, larson-miller-parameter,
monkman-grant, rupture-life, stress-rupture, accumulated-creep-strain,
time-to-one-percent-creep, elevated-temperature):
creep-stress-relaxation, norton-relaxation-closed-form, preload-retention,
fixed-strain-creep-relaxation, relaxed-stress-fraction, elevated-
temperature-preload. Build-time fence note: add one routing line to
creep-rupture pointing preload-decay / fixed-strain relaxation questions
at this leaf.

## Declines probed FRESH this session (receipts)

| Candidate seam | One-line reason (fresh evidence at this HEAD) |
|---|---|
| Sonic / acoustic fatigue | No separated deterministic anchor: the SDOF random-response machinery incl. the Miles equation is OWNED by loads/random-vibration-analysis (its desc computes g-rms, Miles equation, 3-sigma, equivalent static load factor); PSD-to-damage is OWNED by fatigue/random-vibration-fatigue (Rayleigh/Dirlik); acoustic fatigue is the composition of those owned leaves under an empirical acoustic-environment PSD - same no-new-physics decline class as wave-46's pressurization fatigue; 0 corpus demand for sonic/acoustic tokens (only acoustic-emission NDT in manufacturing-quality, unrelated) |
| Creep-fatigue / cyclic creep interaction | Wave-46 decline re-verified FRESH: creep-rupture owns the elevated-temperature vein and self-declares "does NOT cover cyclic endurance"; interaction laws are empirical fit content, no deterministic closed-form anchor; 0 corpus demand |
| Tangent-modulus (Engesser) inelastic column | Wave-45 decline re-verified: variant of the landed inelastic-column-buckling (Johnson arm = the deterministic published form); iterative E_t search has no closed-form parabola anchor; 0 demand |
| Continuous-beam 3-moment (Clapeyron) | Wave-44 GO leaf statically-indeterminate owns it: wave-45 closed-veins list line "statically-indeterminate (Clapeyron/Hardy-Cross/slope-deflection); do not reopen" re-verified at this HEAD |
| Secant-formula / eccentrically loaded column | OWNED, not a gap: beam-column-analysis implements the secant-formula peak-stress traverse (tag secant-formula, workflow step 4) and corpus tasks w?-secant route to it (corpus line 5084 verified) |
| Aeroelastic divergence / flutter / control-surface reversal | OWNED outside structures: aerodynamics family carries the aeroelasticity pack (divergence-speed, flutter-speed-prediction, aeroelastic-gust-response, added-mass-coefficients-potential-flow) at this HEAD; not a structures seam |
| Laminate notched strength (Whitney-Nuismer) / composite CAI / impact | Wave-45/46 declines re-verified: notched-laminate strength was the "reopening a just-closed pack vein" decline; CAI/impact empirical with no closed-form anchor; bird-strike owns the certification impact energy vein |
| Creep relaxation as UNCONDITIONAL GO | See rank-2 GO: deterministic anchor is clean but the wave-46 "creep-rupture owns the elevated-temperature vein" frame makes same-vein adjudication a real risk - ranked conditional, not unconditional |
| All other wave-45/46 decline rows (Timoshenko shear beams, torsional-flexural buckling, structural shear-lag, multiaxial fatigue criteria, plate vibration, sandwich global buckling/dimpling/inserts, Huth fastener flexibility, n-cell torsion, closed-cell restrained warping, external-pressure cylinders, plate pure-bending/biaxial buckling, stiffened-panel wide column, prying/weld/gusset, Gerber/Soderberg, EPFM J/CTOD/R-curve, Elber/da-dN threshold, thermal rings/frames/transients, pressure cabin barrel, oblique lugs, Saint-Venant solid torsion, determinate beam deflection, lateral-torsional buckling, beam-on-elastic-foundation, plate bending, grillage/ring-frame, stress-concentration/hoop, creep-fatigue) | STANDING, re-verified at this HEAD: the only family change since the wave-46 whole-family receipt is the +2 wave-46 leaves (elliptical-hertz-contact, crack-tip-plasticity-correction), both ON DISK at this HEAD owning exactly their adjudicated seams; no wave-46 decline row's seam is touched by either new leaf, and no wave-43..47 recon doc, spec, or leaf plan ever proposed any row above as a GO |

## Closed-veins notes (fresh re-verification)

- Wave-46 closed-veins list re-verified standing at this HEAD; the two
  wave-46 GOs own their seams (elliptical-hertz-contact: hertzian-contact-
  stress line 50-52 carve-out "Unequal crossed radii give the general
  elliptical patch of the Hertz elliptic integrals, out of scope here"
  still present; crack-tip-plasticity-correction: fracture-toughness still
  quotes the ASTM E399 2.5*(K/sigma_ys)**2 rule without computing r_p).
- Composites pack (12 leaves), fatigue pack (7), loads pack (4), S-N /
  epsilon-N / Goodman / rainflow / Miner / notch, pressure dome/barrel/
  interference, thermal expansion/buckling, certification impact,
  materials static/multiaxial/creep, Euler-Johnson columns, crippling,
  flat-plate buckling, curved-shell SP-8007, two-cell torsion, Hertz
  circular/line contact, LEFM fracture family: OWNED, per wave-45/46
  receipts re-verified on disk at this HEAD.

## Method note

All greps and scans above were read-only terminal/search_files runs;
none touched the repo beyond reading. Helper work kept to /tmp
(w47_st_inv.sh, w47_st_fences.sh); no repo file modified; git HEAD
remained a4ae6d1e throughout. Enumeration, pack census, router parity,
corpus baseline and standards-map ids re-derived at this HEAD. The full
texts of laminate-stiffness, cmh17-allowables, material-selection,
creep-rupture, random-vibration-analysis, random-vibration-fatigue,
beam-column-analysis and the wave-45/46 structures receipts were read
from disk. Raw substring scans over eval/hit1-corpus.yaml (1286 blocks)
used for every corpus claim; zero-demand refers to current tasks, each
GO leaf adds two at build per wave doctrine.
