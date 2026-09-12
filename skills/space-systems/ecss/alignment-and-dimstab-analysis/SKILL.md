---
name: alignment-and-dimstab-analysis
description: "Use when determine alignment compliance and dimensional stability for spacecraft structural elements per ECSS-E-ST-32C clauses 4.6.2.19–4.6.2.20: inventory alignment contributors (manufacturing tolerance, thermo-elastic deformation, hygrothermal expansion, load-induced displacement, creep), combine systematic contributors by absolute sum and random contributors by root-sum-square, compare the total against the interface alignment requirement, verify hot-case and cold-case and eclipse thermal coverage, and compute thermo-elastic plus hygrothermal dimensional change per element against its dimensional allowable. Trigger: ecss, e-st-32-structures-scope, alignment, dimensional-stability, thermo-elastic, hygrothermal, alignment-budget."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32-structures-scope, alignment, dimensional-stability, thermo-elastic, hygrothermal, alignment-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Alignment Demonstration and Dimensional Stability (space-systems/ecss/alignment-and-dimstab-analysis)

Use when the task is demonstrating by analysis that spacecraft structural
elements meet their alignment requirements and dimensional stability limits
across the full mission environment, per ECSS-E-ST-32C clauses 4.6.2.19
and 4.6.2.20.

## Domain quick reference

- Clause 4.6.2.19 requires demonstration that each alignment-critical
  interface remains within its alignment requirement under all applicable
  load cases. Contributors to the interface misalignment budget are
  categorized into two combination groups: manufacturing tolerance is
  systematic (always adds, combined by absolute sum) while thermo-elastic
  deformation, hygrothermal expansion, load-induced displacement, and creep
  are independent effects (combined by root-sum-square). The total is the
  systematic sum plus the RSS of the random group, and it must not exceed
  the interface alignment budget.
- The alignment demonstration must cover at minimum three thermal
  environments: hot case, cold case, and eclipse. An analysis that omits
  any of these is incomplete regardless of whether the covered cases pass.
- Clause 4.6.2.20 requires dimensional stability analysis for any element
  whose dimensional change under operational conditions could affect
  performance. The two physical mechanisms are thermo-elastic deformation
  (ΔL = α × L × ΔT) and hygrothermal expansion (ΔL = CME × Δm × L). Both
  contributions are summed conservatively (worst-case phasing) and compared
  against the element's dimensional allowable. The allowable is set by the
  performance requirement of the instrument or subsystem the element
  supports; its absence is itself a finding.
- Composite elements have both a coefficient of thermal expansion (CTE, α)
  and a coefficient of moisture expansion (CME); metallic elements typically
  have negligible CME. Both parameters must come from the material
  data sheet or coupon test results, not from generic reference values,
  because scatter in CTE/CME is a significant contributor to the uncertainty
  in the dimensional change estimate.

## Workflow

1. Identify all alignment-critical interfaces in the structure and document
   the alignment requirement (budget in arcseconds or microradians) for
   each. Flag any interface with no recorded budget before proceeding —
   a missing budget prevents the compliance check.
2. For each interface, list every contributor to misalignment and assign
   it a combination category: manufacturing_tolerance (systematic) or one
   of thermo_elastic, hygrothermal, load_induced, creep (random). Reject
   any contributor whose type cannot be placed in a recognized category.
3. Compute the combined misalignment: sum all systematic contributors
   linearly, then add the root-sum-square of all random contributors.
   Compare the result against the interface budget; record the margin.
4. Check thermal case coverage: confirm that the hot-case, cold-case, and
   eclipse environments are all represented in the load cases supplied for
   the alignment analysis. Flag any missing case as an open action before
   the analysis can be considered complete.
5. For each element subject to dimensional stability assessment, obtain
   the CTE, CME, nominal dimension L, expected temperature excursion ΔT,
   and expected moisture content change Δm. Compute the thermo-elastic
   component (|α × L × ΔT|) and the hygrothermal component (|CME × Δm × L|),
   and sum them to obtain the worst-case total dimensional change.
6. Compare the total dimensional change against the element's allowable.
   Flag an exceedance and record the margin (negative if exceeded). Flag
   a missing or non-positive allowable as a separate finding — it means
   the performance requirement was not captured, which is not a pass.
7. Aggregate interface alignment findings and element dimensional stability
   findings; neither category of finding can be left open at closure.

## Pitfalls

- Applying root-sum-square to manufacturing tolerance and treating the
  result as conservative — manufacturing tolerance is systematic and must
  be added linearly. Combining it statistically understates the worst-case
  misalignment.
- Omitting the hygrothermal contribution for composite elements because
  moisture content change is slow and hard to bound — hygrothermal
  deformation from moisture desorption on-orbit can be comparable in
  magnitude to the thermo-elastic contribution for high-CME materials.
- Treating a single worst-case thermal case as sufficient coverage — clause
  4.6.2.19 requires hot case, cold case, and eclipse; each can govern a
  different interface, and dropping any one hides a potential exceedance.
- Reading an unset alignment budget or dimensional allowable as zero (no
  requirement) and marking the analysis as passed — an absent requirement
  means the requirement has not been captured, which is an open finding,
  not a compliant result.
- Using generic literature CTE/CME values for composite elements instead
  of material data sheet or coupon test values — scatter in these parameters
  can shift the dimensional change estimate enough to change a margin from
  positive to negative.

## Behavior contract (gate 3)

The contributor categorization, alignment budget combination, thermal case
coverage check, thermo-elastic deformation, hygrothermal deformation, and
dimensional stability violation logic are exercised by the gate 3 contract
test: scripts/test_alignment_and_dimstab_analysis.py against
scripts/alignment_and_dimstab_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_alignment_and_dimstab_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the standard and clause
  as anchor only, paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
