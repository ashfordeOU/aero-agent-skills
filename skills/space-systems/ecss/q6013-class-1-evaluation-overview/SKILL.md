---
name: q6013-class-1-evaluation-overview
description: "Use when an evaluation plan, heritage justification or evaluation report decides whether a part may enter a design. Evaluate whether the evaluation campaign behind a commercial part meets clause 4.2.3.1 of ECSS-Q-ST-60-13C at Class 1: grade the state of every campaign element the clause owes, from manufacturer assessment and construction analysis through radiation, endurance, environmental and electrical characterisation to assembly compatibility, test each heritage claim against manufacturer, part number, assembly site, process-change and validity rules, weight the credit into a coverage fraction, and return the outstanding elements with one campaign verdict. Trigger: ecss, q-st-60-13c, q6013-class-1-evaluation-overview, commercial-part-evaluation-campaign, evaluation-element-coverage, evaluation-heritage-admissibility, commercial-part-evaluation-verdict."
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
  tags: [ecss, q-st-60-eee-scope, q-st-60-13c, q6013-class-1-evaluation-overview, commercial-part-evaluation-campaign, evaluation-element-coverage, evaluation-heritage-admissibility, commercial-part-evaluation-verdict, mandatory-evaluation-element]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components — Class 1 Evaluation Overview (space-systems/ecss/q6013-class-1-evaluation-overview)

Use when the task is clause 4.2.3.1 of ECSS-Q-ST-60-13C: the evaluation that
has to stand behind a commercial part before it is used at the highest
assurance class, taken as one campaign rather than as a stack of individual
tests. This leaf grades the campaign on what it covers and what it owes.

## Domain quick reference

- The campaign is a set of elements, and each element supplies a share of the
  assurance. Weighting them is what lets an incomplete campaign be ranked, but
  the fraction is never a pass mark: complete means every element covered.
- Three elements are load-bearing. The manufacturer assessment, the
  construction analysis and the radiation evaluation each answer a question
  nothing else in the campaign answers, so neither a waiver nor a similarity
  argument buys them. They are graded to zero when either is attempted.
- The state of an element fixes the credit it earns. Performed on the part
  type itself is full credit. A heritage claim is full credit only when the
  claim survives. Similarity to another part type is partial credit and a
  finding. An approved waiver keeps its credit but never buys silence. A plan,
  an unjustified waiver and an absent element all earn nothing.
- A heritage claim stands only when the same manufacturer, the same part
  number and the same assembly site are behind it, no process change has been
  notified since, and the evidence is inside its validity period. Every rule
  that fails is reported, because each names a different repair: a different
  site is recoverable by an audit, a notified process change is not.
- An element nobody mentioned is absent, not excused. The campaign is graded
  against the full element set every time, so a silent declaration cannot
  shrink the campaign it is measured against.
- A campaign with full coverage but open waivers is not the same as a clean
  one. It gets its own verdict so the open actions travel with the part.

## Workflow

1. Name the part type under evaluation and collect what each campaign element
   declares: its state, and for a heritage state the claim behind it.
2. Reject the declaration before grading when an element name or a state is
   unrecognised, when an element is declared twice, or when a heritage state
   carries no claim.
3. Expand the declaration to the full element set, grading anything not
   mentioned as absent.
4. Grade each element to a credit. Test every heritage claim against all five
   admissibility rules at once and keep the list of the ones that failed.
5. Apply the mandatory-element rule: a waiver or a similarity argument on a
   load-bearing element takes its credit to zero and raises a finding.
6. Take the weighted credit over the total weight as the coverage fraction,
   and rank the elements short of full credit heaviest first.
7. Name the verdict -- incomplete while anything is outstanding, open actions
   when coverage is full but findings remain, complete only when neither is
   true -- and carry the findings with it.

## Pitfalls

- Reading the coverage fraction as a score and calling a high number a pass.
  It ranks what is outstanding; it never closes a campaign.
- Letting a similarity argument carry the radiation evaluation or the
  construction analysis. Those are exactly the elements where the differences
  between two part types live.
- Accepting a heritage claim on the part number alone. Same number, different
  assembly site is the usual way a commercial part changes underneath a
  programme without anything on the datasheet moving.
- Treating an old but otherwise perfect heritage record as good forever. The
  validity period exists because the process behind it drifts.
- Grading only the elements the declaration happened to list, so an element
  nobody thought about never appears as missing.
- Closing out a campaign whose waivers were approved and forgetting that the
  approvals are themselves open actions against the part.
- Confusing a planned element with a performed one because the plan is
  detailed. A schedule earns no credit.

## Behavior contract (gate 3)

The element weighting, state credit, heritage admissibility rules, mandatory
element rule, coverage fraction, outstanding ranking and campaign verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_1_evaluation_overview.py against
scripts/q6013_class_1_evaluation_overview_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_1_evaluation_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
