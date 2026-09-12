---
name: drd-stress-strength
description: "Use when produce a structural stress and strength analysis report
  under ECSS-E-ST-32C Annex K: identify each structural element and its applicable
  load cases (limit, yield, ultimate), apply the required factors of safety, compute
  the margin of safety for every load-case/element pair, flag any negative margin,
  and verify the analysis document package contains all DRD-mandated content items.
  Trigger: ecss, e-st-32-structures-scope, stress-analysis, strength-analysis,
  margin-of-safety, factors-of-safety, structural-elements, drd-stress-strength,
  load-cases, material-allowables."
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
  tags: [ecss, e-st-32-structures-scope, stress-analysis, strength-analysis, margin-of-safety, factors-of-safety, structural-elements, drd-stress-strength, load-cases, material-allowables]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Stress and Strength Analysis DRD (space-systems/ecss/drd-stress-strength)

Use when the task is producing the stress and strength analysis report required
by ECSS-E-ST-32C Annex K — inventorying all structural elements, deriving
design loads from limit loads via factors of safety, computing margins of safety,
flagging negative margins, and confirming the report document contains every
DRD-mandated section.

## Domain quick reference

- ECSS-E-ST-32C Annex K defines the content requirements (DRD) for the stress and
  strength analysis report. The report must cover every structural element
  (primary load path and secondary), address all relevant load cases, and
  demonstrate positive margins of safety under yield and ultimate load conditions.
- Load cases are categorized into three types: **limit** (the maximum expected
  load in service, with statistical basis), **yield** (limit load scaled by the
  yield factor of safety, typically FoS ≥ 1.0 for mature metallic hardware), and
  **ultimate** (limit load scaled by the ultimate factor of safety, typically
  FoS ≥ 1.25 for metallic space hardware; higher values apply to composites or
  lower-heritage designs). Each load case type is checked against the
  corresponding material allowable.
- Margin of safety (MoS) is defined as (allowable stress / design stress) − 1,
  where design stress = limit stress × factor of safety. A MoS of exactly zero is
  the boundary condition; negative MoS is a finding requiring redesign or
  allowable re-justification before the analysis is accepted.
- Material allowables must be traceable to an approved material data sheet or
  handbook entry; A-basis (99% exceedance, 95% confidence) is required for
  single load-path elements, B-basis (90% exceedance, 95% confidence) is
  acceptable for multiple load-path elements.
- Structural elements are categorized by construction type: metallic, composite,
  bonded joint, welded joint, or fastener. Each type may carry different FoS
  requirements and allowable basis rules.

## Workflow

1. Inventory all structural elements to be covered in the analysis; categorize
   each by construction type (metallic, composite, bonded joint, welded joint,
   fastener). Reject any unrecognized element type before it enters the margin
   calculation — an uncategorized element is a documentation gap.
2. For each element, list the applicable load cases by type. Confirm that limit
   loads are defined for every load case; without a limit load, neither a design
   load nor a margin can be computed.
3. Apply the factor of safety for each load case type to convert the limit load
   to the design load: design load = limit load × FoS. Verify the FoS value
   traces to the program-level factor-of-safety document or to ECSS-E-ST-32C
   Table 5 defaults; do not carry forward an untraced FoS.
4. Retrieve the material allowable for the element/load-case combination from the
   approved allowables data sheet. Validate that the allowable is positive and
   that its statistical basis (A or B) is appropriate for the element's load-path
   role.
5. Compute the margin of safety: MoS = (allowable / design stress) − 1. Record
   MoS to at least four significant figures. Flag every pair where MoS < 0 as a
   finding; a MoS exactly at zero is marginal and should be noted with a
   sensitivity comment.
6. Aggregate all element/load-case margins into the summary margin table. Identify
   the governing (minimum) margin per element across all load cases. Any element
   with a negative governing margin must be escalated before the analysis document
   is submitted.
7. Verify the analysis report contains all DRD-mandated sections: scope,
   applicable documents, load cases, material allowables, analysis methods,
   structural element list, margins-of-safety table, and conclusions. A missing
   section is a document compliance gap independent of the numeric margins.

## Pitfalls

- Applying the factor of safety to the allowable instead of to the limit load —
  this inverts the MoS formula and produces an unconservative result that may
  appear positive when the true margin is negative.
- Using B-basis allowables for a single load-path element — A-basis is required
  when there is no redundant load path; using the less conservative basis
  understates structural risk.
- Treating a MoS of zero as a pass without a sensitivity note — a zero margin has
  no reserve and any load increase or allowable scatter drives the element to
  failure; document the sensitivity explicitly.
- Skipping elements categorized as secondary structure — secondary elements can
  become load-carrying under damage or redistribution scenarios; the DRD requires
  coverage of all structural elements.
- Submitting a report with an untraced factor of safety — the FoS must link to an
  approved program document or to the ECSS default table; an analyst-assumed FoS
  without a cited basis is not acceptable for the SSA record.

## Behavior contract (gate 3)

The element categorization, factor-of-safety application, margin-of-safety
computation, negative-margin detection, and DRD completeness logic is exercised
by the gate 3 contract test:
scripts/test_drd_stress_strength.py against scripts/drd_stress_strength_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_drd_stress_strength.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
