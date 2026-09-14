---
name: q6013-class-3-evaluation-overview
description: "Evaluate whether the reduced evaluation behind a commercial part proves it suitable at the lowest assurance class under clause 6.2.3.1 of ECSS-Q-ST-60-13C: retain or drop each campaign element by the extent it was actually taken, spend the dropped weight against a reduction allowance set by the declared environment, refuse any reduction of the irreducible elements, credit manufacturer data and part-family similarity at the fraction each earns, and return the retained fraction with one campaign verdict. Use when a reduced evaluation plan, justification or report decides whether a commercial part may enter a lowest-assurance design. Trigger: ecss, q-st-60-13c, q6013-class-3-evaluation-overview, reduced-evaluation-campaign, class-3-reduction-allowance, irreducible-evaluation-element, lowest-assurance-part-suitability."
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
  tags: [ecss, q-st-60-eee-scope, q-st-60-13c, q6013-class-3-evaluation-overview, reduced-evaluation-campaign, class-3-reduction-allowance, irreducible-evaluation-element, lowest-assurance-part-suitability, evaluation-element-extent]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components — Class 3 Evaluation Overview (space-systems/ecss/q6013-class-3-evaluation-overview)

Use when the task is clause 6.2.3.1 of ECSS-Q-ST-60-13C: the reduced
evaluation that has to prove a commercial part suitable when it is used at
the lowest assurance class. This leaf grades the reduction itself -- how much
of the campaign was left unproven, and whether the programme was entitled to
leave it there.

## Domain quick reference

- The lowest assurance class does not delete the evaluation, it shrinks it.
  The element set is the same set; what moves is how far each element was
  taken, and the campaign is graded on the distance between the two.
- Every element carries a weight -- its share of the suitability argument --
  and an extent. The extent retains a fraction of that weight: a full run
  retains all of it, a reduced run most, manufacturer-published data half, a
  same-family similarity argument about a third, an omission nothing. What is
  not retained is dropped weight, and dropped weight is the thing being
  budgeted.
- The budget is a reduction allowance, and it is set by the environment the
  part has to survive, not by the schedule. A benign environment buys a large
  reduction, a severe one buys almost none. A campaign that spends past its
  allowance is over-reduced however defensible each individual element looked
  on its own.
- Two elements sit outside the allowance entirely: the manufacturer assessment
  and the construction and technology review. They answer who built the part
  and what it actually is, and every other element is read in their light, so
  no allowance reaches them.
- The radiation suitability review is gated rather than irreducible. It may be
  reduced while the declared environment stays benign and not otherwise, which
  makes the environment declaration a load-bearing input rather than a label.
- An omission carrying a rationale and a silent one are not the same event.
  The first is a decision the programme can defend and re-open; the second is
  an element nobody thought about, so it blocks.
- An element nobody mentioned is omitted silently. The full element set is
  graded every time, so a thin declaration cannot shrink the campaign it is
  measured against.

## Workflow

1. Name the part type, the environment severity it is declared against, and
   the extent reached on each campaign element.
2. Reject the declaration before grading when an element name, an extent or a
   severity is unrecognised, when an element is declared twice, or when the
   part identifier is blank.
3. Expand the declaration to the full element set, grading anything not
   mentioned as a silent omission.
4. Convert each extent into retained and dropped weight, and raise the finding
   the extent carries -- similarity credit, manufacturer-data credit, reduced
   extent, reasoned omission or silent omission.
5. Apply the two structural rules: any reduction of an irreducible element
   blocks, and a reduced radiation suitability review blocks outside a benign
   environment.
6. Compare the total dropped weight against the reduction allowance for the
   declared severity, absorbing representation error at the boundary with a
   named tolerance rather than by widening the allowance.
7. Name the verdict -- over-reduced on a blocking finding or an exceeded
   allowance, conditional while any finding stands, sufficient only when
   neither is true -- and carry the retained fraction and the findings with it.

## Pitfalls

- Reading the retained fraction as a score and calling a high number a pass.
  It says how much of the argument survived; the allowance says whether the
  programme was entitled to drop the rest.
- Budgeting the reduction against the schedule instead of the environment. The
  allowance exists because a benign environment tolerates an unproven element
  and a severe one does not.
- Letting a large allowance reach the manufacturer assessment or the
  construction and technology review. Those two are what make the rest of the
  campaign readable at all.
- Reducing the radiation suitability review under an environment that was
  never declared benign, usually because the declaration was filled in after
  the evaluation was planned.
- Treating a silent omission as a reasoned one because the element was clearly
  unnecessary. If the rationale is not written down there is nothing to review
  when the environment moves.
- Accepting manufacturer-published data as equivalent to a run on the part
  type. It is worth half the weight precisely because it describes the
  catalogue part rather than the part the programme will fly.
- Stopping at the first blocking finding, so the next reduction round
  discovers the next block instead of repairing both at once.

## Behavior contract (gate 3)

The element weighting, extent retention, severity allowance, irreducible and
environment-gated rules, dropped-weight budget, retained fraction and campaign
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_evaluation_overview.py against
scripts/q6013_class_3_evaluation_overview_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_evaluation_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
