# WAVE-45 STRUCTURES EXTENSION-PROBE RECEIPT (task-10, whole-family FRESH)

- Repo: the local AeroSkills repo at git HEAD 5cc8fef3 (verified via git rev-parse; HEAD re-checked after all reads).
- Scope: ENTIRE structures family, 59 leaves, probed fresh. Enumerated first with `find skills/structures -mindepth 3 -name SKILL.md` = 59 (composites 12, damage-tolerance 4, fatigue 7, fem 24, loads 4, materials 6, thermal-structures 2). Read-only except this receipt; no git add/commit/push, no edits to skills/, eval/, docs/, Makefile scripts, ops/automation briefs or standards-map.yaml.
- Baseline: wave-44 +2 (statically-indeterminate, restrained-warping, both fem, re-verified on disk at this HEAD) used the wave-43 reserves; wave-42 +3. Family is deep; probe limited to clean solid-mechanics/instability/loads gaps.
- Standards map: 30 ids (`grep '^  - id:'` = 30); candidate ids grep-verified below.

## Verdict

2 ranked GO candidates, both wave-44-style next siblings whose owning leaves hand the seam off in their own fence text:

1. structures/fem/inelastic-column-buckling: the yield-anchored Johnson parabola (Euler-Johnson tangent column strength curve) for general solid, round, tube and extruded columns in the intermediate slenderness band. buckling-analysis computes only the elastic Euler arm and its own workflow says "fall back to a Johnson parabola or test data" without implementing it; crippling-analysis computes the Johnson arm anchored on the local crippling stress of formed sheet stiffeners only and states it is "never on the solid-section yield", with extruded and machined sections out of scope. The whole solid-column inelastic allowable is owned by nobody.
2. structures/damage-tolerance/walker-forman-crack-growth: the mean-stress (R-ratio) and K_c-limited crack growth rate equations that extend the Paris law. crack-growth is strictly Paris constant-amplitude with zero R-ratio, Walker or Forman content anywhere in the structures tree; the fatigue pack mean-stress content (goodman-diagram) is S-N infinite-life (Goodman/Gerber/Soderberg/Haigh), a different domain from da/dN.

Everything else in the family declines with receipts below. This keeps structures 59 -> 61 after landing, matching the wave-44 structures pattern (+2).

## Ranked GO candidate 1: structures/fem/inelastic-column-buckling

Deterministic closed form for the inelastic column: given material (E, F_cy), section (A, I, radius of gyration), effective length factor K and length, compute lambda = K*L/r, the Euler-Johnson tangent transition lambda_t = sqrt(2*pi^2*E/F_cy), the Johnson parabola arm F_col = F_cy*(1 - F_cy*lambda^2/(4*pi^2*E)) for lambda below lambda_t, the Euler arm pi^2*E/lambda^2 above it, the column capacity P_col = F_col*A and the margin against the applied load, with the regime classification (johnson / euler) and the tangency check at lambda_t where both arms return F_cy/2. The equation family is identical in shape to the Johnson arm crippling-analysis already implements, re-anchored from F_cc on sigma_y.

(a) Zero-owner grep evidence, whole skills/ tree (read-only terminal runs):

```
$ grep -rn -i -E "johnson|inelastic|column[- ]strength" skills/ --include=SKILL.md
skills/structures/fem/buckling-analysis/SKILL.md:70:  the capacity (Johnson or test-data range).
skills/structures/fem/buckling-analysis/SKILL.md:122:  unconservative, so fall back to a Johnson parabola or test data.
skills/structures/fem/crippling-analysis/SKILL.md:3: ...run the Johnson-Euler interaction that anchors the stiffener column curve on the local crippling stress...
skills/structures/fem/crippling-analysis/SKILL.md:59: - Johnson-Euler interaction anchored on the crippling allowable...
skills/structures/fem/crippling-analysis/SKILL.md:63:  F_col = F_cc * (1 - F_cc * lambda**2 / (4 * pi**2 * E)) (Johnson arm)
```

- No leaf computes a Johnson arm anchored on the material yield. The only inelastic/tangent-modulus hit in the whole tree is ramberg-osgood (materials pack, stress-strain curve definition, no column content). Corpus scan of eval/hit1-corpus.yaml for johnson-parabola, inelastic-column, column-strength, intermediate-slenderness, stubby-column tokens: zero hits (no existing task to steal, two new tasks get written at build).

(b) Quoted sibling fences:

buckling-analysis (skills/structures/fem/buckling-analysis/SKILL.md), the global Euler column owner:
- line 68-70: "If lambda > lambda_1 the column is slender and Euler governs; if lambda < lambda_1 the material yields first and Euler overpredicts the capacity (Johnson or test-data range)."
- workflow step 7, line 119-122: "Classify the column: compute lambda_1 = pi * sqrt(E / sigma_y) with transition_slenderness(E, yield_strength). If lambda > lambda_1, Euler governs and Pcr is the capacity; if not, Euler is unconservative, so fall back to a Johnson parabola or test data."

The leaf's deliverable is the classification flag only; the fallback computation is handed off, never implemented.

crippling-analysis (skills/structures/fem/crippling-analysis/SKILL.md), the formed-stiffener owner:
- Related leaves, lines 196-200: "structures/fem/buckling-analysis: the GLOBAL column Euler load of the same member with the end-condition effective length factor and the yield-based transition; this leaf takes lambda = K*L/r as an input and anchors its Johnson curve on the local crippling stress, never on the solid-section yield."
- Pitfalls, lines 241-244: "Anchoring the Johnson curve on sigma_y: the stiffener short-column curve anchors on the LOCAL crippling allowable F_cc (the lambda-tending-to-0 limit), so using sigma_y in the parabola overstates short stiffeners whose section cripples before it yields."
- Pitfalls, lines 250-253: "extruded, machined or fiber-reinforced sections, elevated temperature, fastener bearing or pull-through of the attachments, and corner radii (flat widths only) are out of scope for this closed form."

Net fence: crippling is formed-sheet stiffeners anchored on F_cc; buckling-analysis is the elastic Euler arm with a yield transition flag; the yield-anchored inelastic parabola for whole solid/extruded/tube columns sits between them and belongs to neither. The in-repo John letter hit at crippling line 199 ("never on the solid-section yield") is the fence, not an owner.

(c) Standards-map id exists (grep-verified): far-25 at line 16 and cs-25 at line 27 of standards-map.yaml. Both are the standing fem pack reference-only ids (buckling-analysis, crippling-analysis, plate-buckling all carry far-25 + cs-25 reference-only), compliance STANDARDS-REF, gated false.

(d) Published deterministic anchor: Johnson's parabolic column formula, the Euler-Johnson tangent column strength curve with the transition at lambda_t = sqrt(2*pi^2*E/F_cy) where the parabola meets the Euler arm at F_cy/2. Standard aerospace treatments: Bruhn, Analysis and Design of Flight Vehicle Structures, column analysis chapter (Johnson parabola interpolation between the yield stress and the Euler curve); Niu, Airframe Structural Design, column allowable curves; Timoshenko and Gere, Theory of Elastic Stability (inelastic columns); Roark's Formulas for Stress and Strain, columns chapter. The identical Johnson-arm equation family is already used in-repo by crippling-analysis (line 63), which grounds the form and its tangency behavior. Public engineering science, paraphrase only, no reproduced tables.

(e) 2 wordable Hit@1 corpus queries with distinctive hyphenated tokens (checked against the existing bka1/bka2 tasks of buckling-analysis, which carry euler critical buckling load, effective length factor, slenderness ratio, Pcr, cantilever column, elastic instability, radius of gyration tokens; no johnson/parabola/inelastic/intermediate-slenderness/column-strength overlap, so no theft in either direction):

1. "run the inelastic-column-buckling check of the 7075-T6 solid round actuator rod with the johnson-parabola column-strength-curve: at the intermediate-slenderness of 55 below the euler-johnson-tangent transition the allowable falls between the yield anchor and the euler arm, so compute the parabola stress and the margin against the applied axial load"
2. "determine the stubby-column-allowable of the 2024-T3 extruded tube compression member in the johnson-parabola range: the inelastic-column-buckling stress at effective slenderness 40 where the euler stress overpredicts, tangent to the euler arm at the column-strength-curve transition"

(f) No generic single-word tag overlap: proposed tags are hyphenated compounds only, none duplicating an existing tag string: inelastic-column-buckling, johnson-parabola, column-strength-curve, intermediate-slenderness, euler-johnson-tangent, yield-anchored-johnson, stubby-column-allowable. Distinct from buckling-analysis tags (euler-buckling, critical-buckling-load, slenderness-ratio, effective-length-factor) and crippling tags (crippling-analysis, johnson-euler-interaction, shape-constant-method). Build-time fence note (wave precedent): add one line to buckling-analysis step 7 pointing the fallback to this leaf, matching how crippling-analysis already fences its Johnson arm.

## Ranked GO candidate 2: structures/damage-tolerance/walker-forman-crack-growth

Deterministic closed form for the stress-ratio-affected crack growth rate: Walker equivalent range dK_bar = dK/(1-R)^(1-gamma) with the material gamma exponent and rate da/dN = C*(dK_bar)^m, the Forman equation da/dN = C*(dK)^m/((1-R)*K_c - dK) that captures the terminal acceleration as the peak stress intensity approaches fracture toughness K_c, and the crack extension over a stated cycle block at a constant or piecewise R, producing the R-corrected rate table, the Forman-vs-Paris rate ratio and the block extension feeding the damage tolerance life.

(a) Zero-owner grep evidence, whole skills/ tree:

```
$ grep -rn -i -E "forman|walker|r[- ]ratio" skills/ --include=SKILL.md
(no hits in skills/structures; the only walker hits in the whole tree are
space-systems/orbit-mechanics/walker-delta-constellation, an unrelated t/p/f
constellation geometry leaf)
```

crack-growth (skills/structures/damage-tolerance/crack-growth/SKILL.md, 88 lines) covers stress intensity K = Y*sigma*sqrt(pi*a), the Paris law da/dN = C*(dK)^m and cycles-to-critical projection only; no stress ratio R, no mean-stress term, no K_c-limited form anywhere in its text or tags. Whole-tree grep for inelastic-adjacent and R-ratio content in structures: only goodman-diagram, which is S-N infinite-life (see declines). Corpus scan for forman, walker, r-ratio-correction, mean-stress-crack-growth tokens: zero hits except the walker-delta constellation tasks (w36-walker-delta-constellation-1/2), a different token space, so no theft.

(b) Quoted sibling fences:

crack-growth domain quick reference, lines 34-36: "The Paris law da/dN = C * (dK)^m relates the crack growth rate to the stress intensity range; C and m are material constants fitted from da/dN testing." The leaf's entire scope is the constant-amplitude Paris projection (workflow steps 1-5: stress intensity, Paris rate, per-cycle extension, cycles to grow). No R-ratio correction and no K_c acceleration term exist in the leaf, so the mean-stress and toughness-limited extensions are outside its implemented family. crack-growth sits in the FAR-25.571 damage tolerance context (its lines 40-41), the same certification frame the new leaf inherits.

Cross-pack fence: goodman-diagram (fatigue pack) description states it computes "the modified Goodman, Gerber, and Soderberg allowable amplitudes from the endurance limit, ultimate strength, and yield strength" for infinite-life S-N checks. That is the mean-stress correction of the stress-life domain; the Walker and Forman equations correct the da/dN crack growth rate domain (LEFM), which no fatigue leaf touches (stress-life-curve line 32 hands mean-stress corrections to goodman-diagram; strain-life-fatigue line 146-147 assumes fully reversed loading and hands mean-stress effects away).

(c) Standards-map id exists (grep-verified): far-25 at line 16 and cs-25 at line 27, the standing damage-tolerance pack reference-only ids (crack-growth, residual-strength, widespread-fatigue-damage all carry far-25 + cs-25), compliance STANDARDS-REF, gated false. The FAR-25.571 damage tolerance basis is referenced, not reproduced.

(d) Published deterministic anchor: Walker, K., "The Effect of Stress Ratio During Crack Propagation and Fatigue for 2024-T3 and 7075-T6 Aluminum", ASTM STP 462, 1970, pp. 1-14 (Walker equivalent stress intensity dK_bar = dK/(1-R)^(1-gamma)); Forman, R.G., Kearney, V.E., Engle, R.M., "Numerical Analysis of Crack Propagation in Cyclic-Loaded Structures", ASME Journal of Basic Engineering, 1967 (da/dN = C*(dK)^n/((1-R)*K_c - dK)). Both are deterministic closed-form rate equations, standard practice in aerospace damage tolerance tooling (AFGROW-class rate descriptions), pure algebra with no tables and no proprietary text.

(e) 2 wordable Hit@1 corpus queries with distinctive hyphenated tokens (checked against the existing cg1/cg2 tasks of crack-growth, which carry paris law, crack-growth, stress-intensity range, damage-tolerance tokens; both queries below keep walker/forman/r-ratio tokens in the lead and avoid the paris-law and damage-tolerance token strings, so cg1/cg2 and the goodman-diagram tasks keep routing to their owners):

1. "estimate the walker-forman-crack-growth rate of the 2024-T3 fuselage panel at stress ratio R = 0.35: apply the walker-equation equivalent delta-k with the gamma exponent and the forman-equation rate with the kc-limited denominator, then the crack extension over the 2000-cycle block"
2. "compute the walker-equation equivalent delta-k and the forman-equation rate for the growing crack at stress ratio R = -0.4 with the r-ratio-correction gamma exponent, and report the walker-forman crack extension over the block so the kc-limited acceleration near fracture toughness is captured"

(f) No generic single-word tag overlap: proposed tags are hyphenated compounds only, none duplicating an existing tag string (crack-growth owns crack-growth, paris-law, stress-intensity, damage-tolerance, fatigue-crack, fracture-mechanics): walker-forman-crack-growth, walker-equation, forman-equation, r-ratio-correction, equivalent-delta-k, kc-limited-growth, stress-ratio-crack-growth. Build-time fence note: add one routing line to crack-growth pointing R-ratio and K_c-limited rate questions at this leaf (aperiodic-server-scheduling precedent from wave-44).

## Declines table

| Candidate seam | One-line reason |
|---|---|
| Tangent-modulus (Engesser) refined inelastic column | Variant of the rank-1 GO: iterative E_t search with no closed-form parabola anchor; the Johnson arm is the deterministic published form and the crippling in-repo precedent |
| Multi-cell torsion with 3+ cells | torsion-shear-flow owns the Bredt-Batho multi-cell method through the two-cell system (desc and line 38); n-cell is a same-family generalization of an owned method, no new physics |
| Restrained warping of closed single-cell sections | restrained-warping (wave-44) owns the non-uniform torsion equation family for the open I-beam; the closed-cell extension adds continuity machinery on top of an owned seam, 0 corpus demand |
| Stiffened panel overall instability / wide column | 0 corpus demand; 4-way fence: crippling-analysis owns the stringer column curve, plate-buckling owns effective width, vehicle-design fuselage-skin-stringer and wing-box-sizing own the conceptual stiffened-shell closure |
| External pressure (hoop) buckling of cylinders | cylindrical-shell-buckling owns the SP-8007 curved-shell family for airframe load cases (axial, bending, ovalization); external pressure collapse is a pressure-hull loading, 0 airframe corpus demand |
| Plate buckling in pure bending / biaxial compression | plate-buckling owns the k-coefficient family including shear and combined compression-shear; the bending-gradient k is a coefficient-table extension, wave-44 declined plate bending for 0 demand + coefficient tables |
| Sandwich additions (metallic faces, insert loads) | sandwich-panels owns face/core/wrinkling/deflection sizing; insert and impact allowables are empirical CMH-17 table content, no deterministic closed-form anchor |
| Bolted/riveted prying action, weld groups, gussets | metallic-fastener-joints owns symmetric and eccentric polar-moment groups with shear, bearing, net-section and shear-out modes; prying/weld-group content is Shigley machine design with no aerospace corpus demand, welding-qualification (manufacturing-quality) owns the weld process side |
| Gerber/Soderberg beyond Goodman | goodman-diagram already computes modified Goodman, Gerber and Soderberg Haigh amplitudes (desc line 3, tags gerber, soderberg), owned |
| da/dN threshold and crack closure (Elber) | empirical small-crack content with no deterministic closed form; the clean R-ratio and K_c slice is the rank-2 GO |
| Impact: hail, FOD, composite compression-after-impact | bird-strike owns the certification impact energy vein; composite impact allowables are empirical CAI content, no closed-form anchor |
| Thermal stress of restrained rings/frames, transient gradients | thermal-stress-analysis and thermal-buckling own the restrained-expansion family; rings/frames are statically-indeterminate ring machinery (wave-44 declined grillage/ring-frame), transient needs conduction |
| Pressure cabin barrel hoop/longitudinal membrane | vehicle-design fuselage-skin-stringer owns the hoop and longitudinal membrane stresses and the conceptual skin-stringer closure; pressure-bulkhead owns the dome, shrink-fit-analysis owns the Lame cylinder |
| Transverse/oblique-loaded lugs | lug-joint-analysis owns the round-end axial lug family with the e/D governing-mode sweep; an oblique load adds an efficiency factor to the same three failure modes, 0 corpus demand |
| Solid non-circular Saint-Venant torsion constants | torsion-shear-flow owns the torsion-constant family (solid polar J, thin open rectangles, built-up opens); bar-rectangle coefficients are Roark table lookups, not a computation family |
| Determinate beam deflection methods | statically-indeterminate owns slope-deflection and moment distribution with the deflection deliverable; simple determinate deflection routes to beam-frame-analysis and the vehicle-design consumers, no unowned demand |

## Closed veins list

- Elastic Euler column family: OWNED (buckling-analysis); ends at the yield-transition classification and hands the inelastic fallback off (fence quoted above)
- Formed-stiffener crippling, inter-rivet buckling, F_cc-anchored Johnson-Euler: OWNED (crippling-analysis, wave-43)
- Flat-plate buckling under compression and shear, combined interaction, effective width: OWNED (plate-buckling)
- Curved unstiffened shell axial/bending/ovalization with SP-8007 knockdown: OWNED (cylindrical-shell-buckling)
- Single- and two-cell closed torsion plus open-section restrained warping: OWNED (torsion-shear-flow, restrained-warping wave-44)
- Sandwich, adhesive bonded, peel, bolted composite, scarf repair, delamination, laminate stiffness/FPF/criteria/hygrothermal/plate-buckling, allowables: OWNED (composites pack, 12 leaves)
- S-N and epsilon-N fatigue incl. Goodman/Gerber/Soderberg/Haigh, rainflow spectra, Miner, notch sensitivity: OWNED (fatigue pack)
- da/dN Paris constant-amplitude, residual strength, WFD/MSD/MED screening: OWNED (damage-tolerance pack); R-ratio and K_c-limited rate extension is the only open slice (rank-2 GO)
- Pressure dome, barrel membrane, interference cylinders: OWNED (pressure-bulkhead, vehicle-design fuselage-skin-stringer, shrink-fit-analysis)
- Restrained thermal expansion and critical-temperature-rise buckling: OWNED (thermal-stress-analysis, thermal-buckling)
- Certification impact: OWNED (bird-strike)
- Wave-44 declines stand re-verified: lateral-torsional buckling (0 demand), beam-on-elastic-foundation (0 demand), plate bending (0 demand + coefficient tables), grillage/ring-frame (iterative machinery), stress-concentration/hoop (owned: notch-sensitivity, shrink-fit, pressure-bulkhead)
- Wave-44 GO leaves remain on HEAD and own their seams: statically-indeterminate (Clapeyron/Hardy-Cross/slope-deflection), restrained-warping (bimoment/warping stress); do not reopen

## Method note

All greps and scans above were read-only terminal/search_files runs. Helper scripts written to /tmp only (dump_fm.py, dump_fm2.py, fence_map.py, corpus_scan.py, dump_full.py); no repo file was modified and git HEAD remained 5cc8fef3 throughout. The 59-leaf enumeration, the fem/composites/damage-tolerance/fatigue descriptions, the crippling-analysis, buckling-analysis, crack-growth, goodman-diagram and vehicle-design fuselage-skin-stringer texts were read in full from disk at this HEAD. Corpus scans used raw substring search over eval/hit1-corpus.yaml; zero-demand findings refer to current tasks, and each GO leaf carries two new tasks at build time per wave doctrine.
