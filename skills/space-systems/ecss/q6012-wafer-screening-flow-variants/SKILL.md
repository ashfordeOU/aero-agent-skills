---
name: q6012-wafer-screening-flow-variants
description: "Determine which screening and acceptance measurement sequence a procurement situation calls for under ECSS-Q-ST-60-12C clause 10.2.2, then grade a proposed flow against it. Use when wafers or die arrive already screened by the supplier, or from a process previously approved, and the question is which stages may be dropped and which order still has to hold. Selects one variant from the procurement facts, refuses a combination no variant covers, and separates a missing stage from an inverted evidence pair, since an alternative sequence is acceptable only where it preserves the pairs the evidence rests on. Trigger: ecss, q-st-60-12c-clause-10-2-2, wafer-screening-flow-variant, screening-acceptance-sequence, supplier-screened-wafer-procurement, pre-post-stress-drift-pair, reduced-screening-flow-selection."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-wafer-screening-flow-variants, q-st-60-12c-clause-10-2-2, wafer-screening-flow-variant, screening-acceptance-sequence, supplier-screened-wafer-procurement, pre-post-stress-drift-pair, reduced-screening-flow-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wafer Level Screening — Flow Variants (space-systems/ecss/q6012-wafer-screening-flow-variants)

Use when the task is ECSS-Q-ST-60-12C clause 10.2.2: the screening and
acceptance measurement sequence is not one flow but several, and which one
applies is decided by how the parts were procured rather than by preference.

## Domain quick reference

- The variant is selected, not chosen. Wafers or separated die, screened by
  the supplier or not, a process already approved or a first lot — those
  facts pick exactly one reference sequence, and a buyer who picks a
  different one has changed the procurement, not the paperwork.
- A combination no variant covers is refused rather than approximated.
  Separated die that nobody screened at wafer level cannot be brought back
  to a wafer flow, and quietly routing it to the fullest sequence produces a
  programme that cannot be executed on the parts in hand.
- A flow is graded on content and constraints, never position by position.
  Stages genuinely free to run in either order may, so an alternative
  sequence that carries every required stage and inverts nothing is the
  variant, however it was written down.
- The ordering constraints are where the evidence lives. A measurement
  before the stress and a measurement after it are a drift pair; the same
  two measurements taken in the other order are two unrelated datasets, and
  nothing downstream can recover the difference.
- Constraints narrow to the stages present. A reduced variant that never
  runs a pre-stress measurement is not held to the pairs that mention one,
  which is what makes a reduced flow assessable at all rather than
  permanently short.
- A stage beyond the variant is an addition, not a defect. A buyer may run
  more than the minimum; the finding is worth reporting so the cost is
  visible, but it does not make the flow the wrong variant.
- Missing and inverted are different dispositions. An omitted stage leaves
  an incomplete programme that needs work added; an inverted pair leaves a
  complete programme that needs re-sequencing, and often no new hardware.

## Workflow

1. State the procurement facts: delivery form, whether the supplier screened
   the material, and whether the process was previously approved. Refuse a
   non-boolean flag rather than reading it as true.
2. Select the variant from those facts, and stop with an explicit refusal
   where the combination has no variant.
3. Normalise the proposed flow: known stages only, no blanks, no repeats. A
   repeated stage is an input defect, because it makes an order ambiguous.
4. Difference the proposal against the variant's stage set in both
   directions — what it omits, and what it adds — and carry the stage
   coverage fraction alongside.
5. Narrow the ordering constraints to the pairs whose two stages are both in
   this flow, then report every pair the proposal runs the wrong way round.
6. Report whether a drift pair survives the order: a pre-stress measurement,
   the stress, and a post-stress measurement, in that sequence.
7. Close with a ranked disposition — incomplete where a stage is absent,
   reorder-required where only the order is wrong, equivalent otherwise.

## Pitfalls

- Defaulting an uncovered procurement to the longest flow. It reads as
  conservative and produces a sequence the parts cannot support, which is
  discovered at the stress step and not before.
- Grading a proposal by comparing it element by element with the reference.
  Stages that are free to swap then read as defects, and a correct flow is
  sent back for a change that buys nothing.
- Applying every ordering constraint to a reduced variant. Pairs that
  mention a stage the variant never runs make the flow permanently
  non-compliant against a rule it was never under.
- Moving a measurement across the stress to save a setup. The pair is the
  evidence; both measurements still exist afterwards, and neither of them
  says anything about drift.
- Treating an extra stage as a deviation to be removed. Running more than
  the minimum is a cost decision, and rejecting it confuses budget with
  compliance.
- Reporting one verdict for a missing stage and an inverted pair. They go to
  different owners — one adds work to the programme, the other re-sequences
  work already planned.

## Behavior contract (gate 3)

Situation and stage validation, variant selection from the procurement facts
including the refusal of an uncovered combination, the stage difference in
both directions, the coverage fraction, constraint narrowing, inverted pair
detection, drift pair survival and the ranked disposition are exercised by
the gate 3 contract test:
scripts/test_q6012_wafer_screening_flow_variants.py against
scripts/q6012_wafer_screening_flow_variants_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_wafer_screening_flow_variants.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
