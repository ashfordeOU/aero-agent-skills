# WAVE-46 STRUCTURES EXTENSION PROBE RECEIPT (task-11, whole-family FRESH)

- Repo: the local AeroSkills repo at git HEAD 45931c16 (verified `git log
  --oneline -3` first line: "45931c16 fix(audit): move BRANDING_REPOS to
  module scope"; HEAD re-checked after all reads).
- Scope: ENTIRE structures family, 61 leaves (LARGEST family), probed
  FRESH at this HEAD. Read-only probe: no writes to skills/, eval/,
  standards-map.yaml, scripts/, Makefile, or ops/automation briefs. One
  write only: this receipt (ops/automation/state/wave46-recon/).
- Enumeration: `find skills/structures -mindepth 3 -name SKILL.md` = 61
  files. Pack census: composites 12, damage-tolerance 5, fatigue 7, fem
  25, loads 4, materials 6, thermal-structures 2. Family router
  (skills/structures/SKILL.md) parity 61 rows confirmed.
- Doctrine (wave46-brief.md item 12): structures probed LAST because
  wave-43/44/45 reserves are USED (statically-indeterminate,
  restrained-warping, inelastic-column-buckling, walker-forman-crack-
  growth). All four are on disk at this HEAD and own their seams
  (re-verified below). Wave-45 declines re-verified FRESH with new
  greps; the two ranked GOs below were never adjudicated by any
  wave-41..45 receipt, spec, or leaf plan (grep-verified zero mentions
  of their content in all wave4* recon files and leaf plans).
- Standards map: 30 ids (grep '^  - id:' = 30); candidate ids
  grep-verified below.
- Corpus baseline: eval/hit1-corpus.yaml = 1266 tasks (raw substring
  scans used throughout; zero-demand refers to current tasks, each GO
  leaf carries two new tasks at build per wave doctrine).

## Verdict

2 ranked GO candidates, both deterministic closed-form seams whose
owning leaves hand the case off in their OWN fence text, both never
adjudicated in wave-41..45:

1. structures/fem/elliptical-hertz-contact: the general Hertz elliptical
   contact patch between bodies with UNEQUAL principal radii (ball in a
   conforming groove/raceway, crossed unequal cylinders) - the
   eccentricity solve and elliptic-integral semi-axes a != b and peak
   pressure p0 = 3P/(2*pi*a*b). hertzian-contact-stress covers the
   circular-patch (equal-radius) and line-contact (strip) degeneracies
   only and says in its own text (line 50-52): "Unequal crossed radii
   give the general elliptical patch of the Hertz elliptic integrals,
   out of scope here." The wave-43 spec (wave43-specs/hertzian-contact-
   stress.md lines 131-135) repeats the carve-out. Zero owner
   tree-wide, zero corpus tasks on the elliptical tokens.
2. structures/materials/crack-tip-plasticity-correction: the Irwin
   plastic-zone radius and effective-crack-length small-scale-yielding
   correction (r_p, a_eff = a + r_p, K_eff, plane-stress vs
   plane-strain zone, Dugdale strip-yield zone) that sits between the
   LEFM leaves (fracture-toughness, crack-growth, walker-forman) and
   net-section yield. fracture-toughness QUOTES the plastic-zone-derived
   ASTM E399 size rule 2.5*(K/sigma_ys)**2 but never computes r_p or
   a_eff; walker-forman declares scope "linear-elastic small-scale-
   yielding conditions" with no correction. This is the deterministic
   Irwin/Dugdale correction, NOT the empirical Elber closure / da/dN
   threshold slice wave-45 declined (that decline stands, re-verified).
   Materials pack was not in wave-45's GO/decline coverage; the seam was
   never adjudicated (grep of wave43-45 recon + specs + leaf plans:
   zero hits for dugdale / plastic-zone / effective-crack).

Everything else in the family declines with receipts below. Wave-45
declines table (16 rows) and closed-veins list re-verified fresh and
standing. Family remains at 61 -> 63 if both land.

## Ranked GO candidate 1: structures/fem/elliptical-hertz-contact

Deterministic closed form for the general (non-circular) Hertz patch:
given the load P, the equivalent elastic modulus E* and the principal
curvatures of both bodies (convex positive, concave negative, flat
infinite), form the per-plane curvature sums A, B and the difference
parameter; solve the standard Hertz eccentricity relation involving the
complete elliptic integrals K(e), E(e) (deterministic bisection +
AGM evaluation, in-repo precedent: ramberg-osgood inverts by bisection,
beam-vibration bisects characteristic roots); then the contact-ellipse
semi-axes a and b, the peak pressure p0 = 3P/(2*pi*a*b), the elliptic
patch area and the yield-limit load against the p0_yield convention of
the circular and strip arms. It is the wave-43 hertzian leaf's own
general case: ball-in-groove and raceway conforming contacts (the
canonical rolling-element application), crossed unequal cylinders,
ellipsoid pairs - all excluded from the circular/line leaf.

(a) Zero-owner grep evidence, WHOLE skills/ tree:

```
$ grep -rniE "elliptical[- ]contact|hertz elliptic|elliptic[- ]integral|conforming[- ]groove|raceway[- ]groove|contact[- ]ellipse" skills/ --include=SKILL.md
skills/structures/fem/hertzian-contact-stress/SKILL.md:50:  Unequal crossed radii give the general elliptical patch of the Hertz
skills/structures/fem/hertzian-contact-stress/SKILL.md:51:  elliptic integrals, out of scope here.
```
(Only the hertzian leaf mentions the general case, and only to exclude
it; nothing anywhere computes an elliptical patch. All other
"elliptic/bearing/raceway" tree hits are orbit-mechanics ellipses or
lug/bolt "bearing stress" in unrelated leaves.)

(b) Nearest sibling fence (quoted, skills/structures/fem/hertzian-
contact-stress/SKILL.md lines 46-52):

"Crossed cylinders at right angles have the per-plane curvature sum
A + B = (1/r1 + 1/r2)/2; the patch is circular only for equal radii
r1 = r2 = r, where A + B = 1/r, exactly the sphere-on-flat closed form
with Re = r (point_patch with re = r, never the sphere-pair 1/r1 +
1/r2 sum, which would halve the patch radius). Unequal crossed radii
give the general elliptical patch of the Hertz elliptic integrals,
out of scope here."

Wave-43 spec (wave43-specs/hertzian-contact-stress.md lines 131-135,
158-159): "general elliptical patches of unequal crossed principal
radii, which need the Hertz elliptic integrals ... Unequal crossed
radii give an elliptical patch, the general Hertz elliptic-integral
case, which is out of scope." The owning leaf names the missing case in
its own text and hands it off; no other leaf owns it. Same pattern as
the wave-45 GO precedent (buckling-analysis hands the Johnson fallback
off in its workflow text).

(c) Standards-map id exists (grep-verified): far-25 at line 16 and
cs-25 at line 27 of standards-map.yaml - the standing fem pack
reference-only ids (hertzian-contact-stress carries far-25 reference-
only, compliance STANDARDS-REF, gated false).

(d) Published deterministic anchor: Hertz, "On the contact of elastic
solids", 1881 (general elliptical solution); Johnson, Contact
Mechanics, Cambridge University Press, ch. 4 (elliptical contacts:
curvature sums, eccentricity from complete elliptic integrals,
semi-axes and peak pressure); Roark's Formulas for Stress and Strain,
contact-stress tables (elliptical patch case); Harris, Rolling Element
Bearing Analysis (ball-in-groove raceway contact as the canonical
elliptical-patch application). The circular and strip arms the in-repo
leaf already implements are the equal-curvature degeneracies of the
same theory. Public engineering science, paraphrase only, no
reproduced tables.

(e) 2 wordable Hit@1 corpus queries with distinctive hyphenated tokens
(checked against eval/hit1-corpus.yaml: zero raw hits for any token
below, including the hertzian tasks w43-hertzian-contact-stress-1/2
which carry hertz-contact-patch / contact-pressure-ellipse / ball-in-
socket tokens for the CIRCULAR patch and elliptic pressure PROFILE - no
overlap with the elliptical PATCH tokens, so no theft in either
direction):

1. "compute the elliptical-contact-patch semi-axes of the 12.7 mm ball
   in the 15.875 mm groove-radius raceway under 4.45 kN radial load:
   solve the hertz-elliptic-integrals eccentricity from the unequal
   principal curvature sum and difference, then the contact-ellipse
   major and minor semi-axes, the maximum contact pressure and the
   yield-limit margin"
2. "find the elliptical-contact-patch of crossed unequal cylinders with
   25 mm and 40 mm radii at right angles under 2 kN: the elliptic-
   integral eccentricity, the contact-ellipse semi-axes, the peak
   pressure p0 = 3P/(2 pi a b) of the general hertz solution and the
   subsurface von Mises check against the yield strength"

(f) No generic single-word or existing-tag overlap: proposed tags are
hyphenated compounds only, none duplicating an existing tag string
(hertzian tags: hertzian-contact-stress, hertz-contact-patch,
contact-pressure-ellipse, subsurface-shear-stress, contact-yield-limit-
load, equivalent-contact-modulus):
elliptical-hertz-contact, elliptical-contact-patch, hertz-elliptic-
integrals, ball-in-groove-contact, conforming-raceway-contact,
crossed-unequal-cylinders, contact-ellipse-eccentricity. Build-time
fence note: add one routing bullet to the hertzian leaf / family router
pointing unequal-crossed-radii and ball-in-groove questions at this
leaf, matching the wave-45 routing-line precedent.

## Ranked GO candidate 2: structures/materials/crack-tip-plasticity-correction

Deterministic closed form for the small-scale-yielding correction to
linear-elastic K: Irwin plastic-zone radius (plane stress r_p =
(1/2*pi)*(K/sigma_ys)**2 convention, reduced plane-strain zone), the
effective crack length a_eff = a + r_p, the corrected stress intensity
K_eff at a_eff, the Dugdale strip-yield zone size, the LEFM-validity
ratio that gates when the Paris/Forman/Walker rate laws and the
K_IC-based critical crack remain valid, and the corrected K versus
elastic-K ratio. Sits between the owned LEFM leaves and net-section
yield; feeds crack-growth life near K_c and residual-strength sizing
when the applied stress approaches the flow stress.

(a) Zero-owner grep evidence, WHOLE skills/ tree:

```
$ grep -rniE "plastic[- ]zone|dugdale|strip[- ]yield|effective[- ]crack|small[- ]scale[- ]yielding correction|r_p" skills/ --include=SKILL.md
(no leaf computes a plastic-zone radius, an effective crack length or a
strip-yield model anywhere in skills/; walker-forman mentions
"small-scale-yielding conditions" only as its scope statement)
```
Whole-tree scan for j-integral, ctod, epfm, tearing modulus: zero hits.

(b) Nearest sibling fences (quoted):
- walker-forman (skills/structures/damage-tolerance/walker-forman-crack-
  growth/SKILL.md lines 41-47): "...the Walker exponent gamma in (0, 1],
  linear-elastic small-scale-yielding conditions, material constants C,
  m, C_F, gamma and K_c given (no da/dN test-data fitting). No
  crack-closure (Elber) corrections, no threshold, no spectrum cycle
  counting..." - the rate leaves declare small-scale-yielding scope and
  correct nothing.
- fracture-toughness (skills/structures/materials/fracture-toughness/
  SKILL.md lines 51-56): "Plane-strain validity (ASTM E399 test
  context): a valid K_IC test requires specimen thickness B and crack
  size a both >= 2.5 * (K_IC / sigma_ys) ** 2..." - the leaf QUOTES the
  plastic-zone-derived size rule (the 2.5 factor IS the small-scale-
  yielding requirement) but never computes the zone size or the
  effective crack; the correction itself is owned by nobody.
- The wave-45 decline "da/dN threshold and crack closure (Elber)" was
  empirical small-crack content and STANDS; Irwin/Dugdale corrections
  are deterministic closed forms, a different slice, never adjudicated
  (grep of wave43/44/45 recon receipts, specs, and leaf plans for
  dugdale, plastic-zone, effective-crack, strip-yield: zero hits).

(c) Standards-map id exists (grep-verified): far-25 at line 16, cs-25
at line 27, mmpsd at line 160. Materials siblings (fracture-toughness)
carry mmpsd reference-only; damage-tolerance leaves carry far-25 +
cs-25 reference-only. Compliance STANDARDS-REF, gated false.

(d) Published deterministic anchor: Irwin, "Analysis of stresses and
strains near the end of a crack traversing a plate", J. Applied
Mechanics 1957 (plastic-zone radius and effective crack length);
Dugdale, "Yielding of steel sheets containing slits", J. Mech. Phys.
Solids 1960 (strip-yield model); Broek, Elementary Engineering Fracture
Mechanics; Anderson, Fracture Mechanics: Fundamentals and Applications
(small-scale-yielding corrections); the ASTM E399 validity rule the
in-repo fracture-toughness leaf already quotes is the same plastic-zone
criterion. Deterministic closed-form algebra and special functions
only, no empirical tables.

(e) 2 wordable Hit@1 corpus queries with distinctive hyphenated tokens
(checked against eval/hit1-corpus.yaml: zero raw hits for any token
below; the crack-growth and walker-forman tasks carry paris-law,
delta-k, equivalent-delta-k, kc-limited tokens - no overlap with the
plastic-zone/effective-crack token space, no theft in either
direction):

1. "compute the irwin-plastic-zone radius and the effective-crack-
   length correction for the 5 mm edge crack in 7075-T6 at 180 MPa:
   the small-scale-yielding ratio of the plastic zone to the crack
   size, the corrected stress intensity K_eff at the effective crack
   and the LEFM-validity verdict"
2. "apply the dugdale-strip-yield model to the center crack loaded to
   90 percent of the flow stress: the strip-yield plastic-zone size,
   the effective-crack-length corrected stress intensity and the
   k-eff to elastic-K ratio when the small-scale-yielding limit is
   exceeded"

(f) No generic single-word or existing-tag overlap: proposed tags are
hyphenated compounds only, none duplicating an existing tag string
(fracture-toughness tags: fracture-toughness, kic, stress-intensity-
factor, critical-crack-size, plane-strain, fast-fracture, damage-
tolerance):
crack-tip-plasticity-correction, irwin-plastic-zone, effective-crack-
length, dugdale-strip-yield-model, small-scale-yielding-check,
k-eff-correction, plastic-zone-radius. Build-time fence note: add one
routing line to fracture-toughness and crack-growth pointing
plastic-zone / effective-crack / small-scale-yielding questions at this
leaf.

## Declines table (fresh receipts; wave-45 declines re-verified)

| Candidate seam | One-line reason (fresh evidence) |
|---|---|
| Timoshenko shear-deformable beam / shear-deflection of short beams | 0 corpus demand; Euler-Bernoulli arms own beam response (beam-frame, beam-vibration); no explicit owner fence hands shear deformation off; wave-44 declined adjacent beam extensions on 0 demand (beam-on-elastic-foundation) |
| Torsional-flexural (twist) buckling of open-section columns | 0 corpus demand; wave-44 declined lateral-torsional buckling on 0 demand (same instability family, stands re-verified); restrained-warping owns the warping-constant machinery (Cw/J) and calls the channel/Z extension "outside this contract" |
| Notched-laminate strength / Whitney-Nuismer characteristic distance | composites pack declared OWNED closed vein wave-45 (12 leaves); cmh17-allowables owns the open-hole knockdown at allowable level (empirical factor 0.95); 0 corpus demand for point-stress/average-stress tokens; reopening a just-closed pack vein |
| Structural shear-lag (tension splices / stiffened-panel load introduction) | "shear-lag" tokens in corpus route to adhesive-bonded-joints (Volkersen bondline shear-lag - different phenomenon); wave-45 declined stiffened-panel/wide-column closure 4-way (vehicle-design owns conceptual closure); 0 demand for structural shear-lag-factor tokens |
| Multiaxial fatigue criteria (Sines/Findley/Crossland) | fatigue pack declared OWNED closed vein wave-45; criteria are empirical-constant fits needing biaxial S-N data; no in-repo deterministic anchor; 0 corpus demand |
| Plate natural frequencies / plate vibration | modal-analysis (2-DOF) + beam-vibration (continuous members) own the vibration slice; plate frequency parameters are coefficient tables (wave-44 declined plate bending on coefficient-table + 0-demand grounds); 0 corpus demand |
| Sandwich global buckling / face dimpling (intracell) | sandwich-panels owns face/core/wrinkling/deflection incl. shear term; dimpling/global-buckling additions are CMH-17 empirical cell-geometry content; wave-45 declined sandwich additions; 0 corpus demand |
| Creep-fatigue / cyclic creep interaction | creep-rupture owns the elevated-temperature vein and self-declares "does NOT cover cyclic" content; interaction laws are empirical fit content with no deterministic anchor; 0 corpus demand |
| Fastener flexibility / multi-row load distribution (Huth model) | metallic-fastener-joints + composite-bolted-joints own joint load paths; Huth flexibility coefficients are empirical fits; wave-45 declined prying/weld/gusset additions; 0 corpus demand |
| General multi-cell torsion beyond two cells | wave-45 decline re-verified: torsion-shear-flow owns the Bredt-Batho multi-cell method through the two-cell system; n-cell is a same-family generalization, no new physics; 0 corpus demand |
| Closed-single-cell restrained warping | wave-45 decline re-verified: restrained-warping owns the non-uniform torsion family for open I; closed-cell extension is continuity machinery on an owned seam; 0 corpus demand |
| External pressure (hoop) buckling of cylinders | wave-45 decline re-verified: cylindrical-shell-buckling owns SP-8007 axial/bending/ovalization; pressure collapse is pressure-hull content; 0 airframe corpus demand |
| Plate buckling pure bending / biaxial | wave-45 decline re-verified: plate-buckling owns the k-coefficient family incl. shear + combined; bending-gradient k is a coefficient-table extension; 0 demand |
| Stiffened panel overall instability / wide column | wave-45 decline re-verified 4-way fence (crippling-analysis, plate-buckling, vehicle-design fuselage-skin-stringer, wing-box-sizing); 0 corpus demand |
| Sandwich additions (insert loads, metallic faces) | wave-45 decline re-verified: CMH-17 empirical table content, no deterministic closed-form anchor |
| Bolted/riveted prying, weld groups, gussets | wave-45 decline re-verified: metallic-fastener-joints owns the group methods; Shigley machine-design content; 0 aerospace corpus demand |
| Gerber/Soderberg beyond Goodman | wave-45 decline re-verified: goodman-diagram already computes modified Goodman, Gerber and Soderberg Haigh amplitudes (owned) |
| EPFM J-integral / CTOD / R-curve tearing (elastic-plastic fracture) | Declined: J-integral is a path/domain integral needing numeric contour evaluation (numeric-integration-only content, violates hard rule); CTOD and R-curves are empirical test-data fits per material/thickness with no clean published closed-form anchor usable stdlib-only; the deterministic small-scale-yielding slice (Irwin/Dugdale effective-crack) is the rank-2 GO above, and fracture-toughness already owns the K_IC/E399 plane-strain frame |
| da/dN threshold + Elber crack closure | wave-45 decline re-verified: empirical small-crack content, no deterministic closed form; the deterministic R-ratio/K_c slice is OWNED by walker-forman at this HEAD; the deterministic Irwin/Dugdale correction is rank-2 GO above, not this decline |
| Impact: hail, FOD, composite CAI | wave-45 decline re-verified: bird-strike owns the certification impact energy vein; CAI is empirical; 0 closed-form anchor |
| Thermal rings/frames/transients | wave-45 decline re-verified: thermal-stress-analysis + thermal-buckling own the restrained-expansion family; transient needs conduction; 0 demand |
| Pressure cabin barrel hoop/longitudinal membrane | wave-45 decline re-verified: vehicle-design fuselage-skin-stringer owns the barrel membrane + conceptual closure; pressure-bulkhead owns the dome; shrink-fit owns the Lame cylinder |
| Transverse/oblique-loaded lugs | wave-45 decline re-verified: lug-joint-analysis owns the round-end axial family; oblique adds an efficiency factor to the same three modes; 0 corpus demand |
| Solid non-circular Saint-Venant torsion constants | wave-45 decline re-verified: torsion-shear-flow owns the torsion-constant family; bar-rectangle coefficients are Roark table lookups, not a computation family |
| Determinate beam deflection methods | wave-45 decline re-verified: statically-indeterminate owns slope-deflection/moment distribution; determinate deflection routes to beam-frame-analysis and vehicle-design consumers |

## Closed veins list (re-verified at this HEAD)

- Elastic Euler column family + Johnson inelastic arm: OWNED
  (buckling-analysis, inelastic-column-buckling wave-45 on disk)
- Formed-stiffener crippling, inter-rivet, F_cc-anchored Johnson-Euler:
  OWNED (crippling-analysis)
- Flat-plate buckling compression/shear/combined + effective width:
  OWNED (plate-buckling)
- Curved unstiffened shell axial/bending/ovalization SP-8007: OWNED
  (cylindrical-shell-buckling)
- Single/two-cell closed torsion + open-section restrained warping:
  OWNED (torsion-shear-flow, restrained-warping)
- Hertz point (circular) and line (strip) contact: OWNED
  (hertzian-contact-stress); the general ELLIPTICAL patch is rank-1 GO
  (never adjudicated; wave-43 spec carve-out was a leaf-scope
  statement, not a family decline)
- LEFM fracture: K_IC + E399 validity, Paris, residual strength, R-ratio
  /K_c (walker-forman), WFD/MSD/MED: OWNED; the deterministic
  plastic-zone/effective-crack correction is rank-2 GO (never
  adjudicated; wave-45's Elber/threshold decline was empirical content
  and stands)
- Composites pack (12 leaves), fatigue pack (7), loads pack (4), S-N
  and epsilon-N fatigue, Goodman family, rainflow, Miner, notch:
  OWNED per wave-45; re-verified on disk
- Pressure dome/barrel/interference, thermal expansion/buckling,
  certification impact, materials static/multiaxial/creep: OWNED
- Wave-44 declines stand re-verified: lateral-torsional buckling
  (0 demand), beam-on-elastic-foundation (0 demand), plate bending
  (0 demand + coefficient tables), grillage/ring-frame (iterative
  machinery), stress-concentration/hoop (owned: notch-sensitivity,
  shrink-fit, pressure-bulkhead)

## Method note

All greps and scans above were read-only search_files/terminal runs.
Helper scripts written to /tmp only (w46_st_dump.py, w46_st_battery.py,
w46_st_pass2.py, w46_st_fences.py); no repo file modified; git HEAD
remained 45931c16 throughout. The 61-leaf enumeration, all pack
descriptions, and the full texts of hertzian-contact-stress,
fracture-toughness, crack-growth, residual-strength, walker-forman-crack-
growth, restrained-warping, torsion-shear-flow, shear-center-analysis,
buckling-analysis, crippling-analysis, inelastic-column-buckling,
beam-frame-analysis, beam-vibration, sandwich-panels, metallic-fastener-
joints, lug-joint-analysis, plastic-collapse-analysis and the wave-45 GO
leaves were read in full from disk at this HEAD. Prior-adjudication
checks: grep of ops/automation/state/wave42..45 recon receipts, specs,
and leaf plans for every ranked candidate's content tokens returned zero
hits. Corpus scans used raw substring search over eval/hit1-corpus.yaml;
zero-demand findings refer to current tasks, and each GO leaf carries
two new tasks at build time per wave doctrine. Receipt is sanitized: no
machine-local absolute paths.
