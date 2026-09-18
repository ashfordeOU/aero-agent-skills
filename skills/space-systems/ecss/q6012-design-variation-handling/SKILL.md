---
name: q6012-design-variation-handling
description: "Assess whether the alternative circuit versions sharing one mask set can be released together, under ECSS-Q-ST-60-12 clause 7.2.2. Use when several MMIC variants are placed on a common wafer or reticle and someone must decide the mask set is buildable: refuse a duplicate variant identifier or a derivation loop, confirm every variant traces to a baseline the mask set itself declares, detect process options that cannot coexist on one wafer, hold a variant whose die carries no distinct marking after dicing, compare each variant site count with the statistical minimum, and grade the reticle field area against its budget before a release verdict. Trigger: ecss, q-st-60-12, mmic-mask-set-variant-handling, mmic-variant-baseline-traceability, mmic-wafer-process-option-conflict, mmic-die-identification-marking, mmic-variant-site-count."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-design-variation-handling, mmic-mask-set-variant-handling, mmic-variant-baseline-traceability, mmic-wafer-process-option-conflict, mmic-die-identification-marking, mmic-variant-site-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMICs — Design Variation Handling (space-systems/ecss/q6012-design-variation-handling)

Use when the task is the design-variation step of ECSS-Q-ST-60-12 clause 7.2.2
— managing the alternative versions of a microwave circuit that are placed
together on one wafer or one mask set, and deciding whether that set can be
released to the foundry as it stands.

## Domain quick reference

- Putting variants on a shared mask set is how a microwave circuit design is
  resolved: several matching networks, device peripheries or bias schemes ride
  one wafer, come back measured under identical process conditions, and the
  comparison between them is the design decision. The variants therefore have
  to be managed as a set, not as independent designs that happen to share a
  run.
- Every variant derives from a baseline, and the baseline has to be on the same
  mask set. A variant whose parent lives on a previous run cannot be compared
  under identical conditions, which was the whole reason for sharing the wafer.
  A derivation that loops back on itself has no root at all and is refused
  rather than resolved by picking a starting point.
- A wafer runs one process flow. Variants that need different process options —
  a thicker metal, a back-side via, a different passivation — cannot share it
  unless the options are declared compatible and can genuinely be run together.
  Two options on one wafer is a build finding, not a scheduling inconvenience.
- After dicing, the only thing that tells two variants apart is what is drawn
  on the die. A variant with no identification marking, and two variants
  sharing one marking, are the same defect: the measured data cannot be
  attributed, so the comparison the mask set exists for cannot be made.
- Site count is a statistics question, not a yield one. A variant placed once
  or twice in the reticle field returns a number with no spread behind it, so
  a minimum site count per variant is part of the mask set being fit for
  evaluation.
- Reticle field area is a hard budget. Sites multiplied by die area is what the
  field has to hold, and a set that overruns has to drop a variant or drop
  sites — deciding which is a design judgement, but the overrun itself is
  arithmetic.

## Workflow

1. Validate every variant: a unique identifier, an optional baseline that is
   not itself, a canonical process option, an optional marking, an integer
   positive site count and a positive die area.
2. Resolve each variant's derivation chain back to a root, reporting the
   variants whose baseline the mask set never declares and the variants caught
   in a loop, by identifier.
3. Gather the declared process options. One option is always buildable; several
   are buildable only when they all sit inside one declared compatible group.
   Report the offending options rather than a bare verdict, so the set can be
   split or the option dropped.
4. List the variants with no identification marking, and separately the
   markings shared by more than one variant, since the repair differs.
5. Compare each variant's site count with the minimum needed for a statistical
   evaluation, raising the minimum where the run is a qualification lot rather
   than a design iteration.
6. Sum sites times die area over the set, compare with the reticle field
   budget, and absorb representation error at the boundary with a named
   tolerance rather than trimming the budget.
7. Release the mask set only when the derivations resolve, the process options
   coexist, every die is identifiable, every variant meets its site minimum and
   the field fits.

## Pitfalls

- Treating the variants as separate designs. They share a process run, so a
  defect in one variant's placement or marking costs the comparison the whole
  run was for, not just that variant.
- Resolving a derivation loop by cutting an edge. The loop says the variant
  history is wrong; cutting an edge invents a lineage nobody reviewed and
  attributes the measured data to the wrong baseline.
- Accepting two process options because the foundry has run both before. Run
  before means run on separate wafers; coexistence on one wafer is a separate
  statement the foundry has to make, and it is what the compatible group
  records.
- Marking variants by position in the reticle. The reticle map is a document
  that goes out of date at the first mask revision, while the marking is drawn
  on the die and survives dicing, storage and re-assembly.
- Reading a high site count on one variant as covering the set. Statistics are
  per variant; a hundred sites of the baseline say nothing about the spread of
  the variant placed twice.
- Fitting the field by shrinking the die area in the budget arithmetic instead
  of in the layout. The number that has to change is the drawn one.

## Behavior contract (gate 3)

The variant validation, duplicate-identifier refusal, derivation-chain
resolution and loop refusal, process-option compatibility, marking gap and
shared-marking detection, site-count minimum, reticle-area budget and the
release verdict are exercised by the gate 3 contract test:
scripts/test_q6012_design_variation_handling.py against
scripts/q6012_design_variation_handling_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6012_design_variation_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
