---
name: fracture-control-reviews
description: "Use when prepare fracture-control inputs for a safety or project review milestone under ECSS-E-ST-32C §5.3: determine which FCI list maturity level is required for each milestone (SRR through AR), verify that all required fracture-control deliverables are present before the review gate, confirm that open action items from previous reviews are closed, and check that the fracture control plan, fracture analysis, and NDE procedures meet the required completeness for the milestone. Trigger: ecss, e-st-32-structures-scope, fracture-control-reviews, fci-list, project-reviews, safety-reviews, review-readiness, nde, action-items."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control-reviews, fci-list, project-reviews, safety-reviews, review-readiness, nde]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture-Control Inputs to Safety and Project Reviews (space-systems/ecss/fracture-control-reviews)

Use when the task is preparing and verifying the fracture-control inputs
that must be submitted at each safety and project review milestone under
ECSS-E-ST-32C §5.3 — from the System Requirements Review (SRR) through
the Acceptance Review (AR).

## Domain quick reference

- ECSS-E-ST-32C §5.3 requires that fracture-control information be
  provided at each project review milestone. The exact set of required
  deliverables scales with design maturity: early reviews accept
  preliminary outputs, while later reviews demand final, verified, or
  accepted products. Submitting an under-mature deliverable — e.g. a
  draft FCI list at CDR instead of a final list — is a gate-failure
  finding.
- The Fracture-Critical Item (FCI) list is the central tracking document.
  Its maturity progresses through five levels: preliminary (SRR), draft
  (PDR), final (CDR), verified (QR), and accepted (AR). At each
  milestone the submitted FCI list must meet or exceed the level required
  for that gate.
- Required deliverables per milestone:
  - **SRR**: draft fracture control plan, preliminary FCI list, draft
    fracture criteria.
  - **PDR**: baselined fracture control plan, draft FCI list, preliminary
    fracture analysis, baselined fracture criteria.
  - **CDR**: approved fracture control plan, final FCI list, final
    fracture analysis, draft NDE procedures, fracture test plan, and
    closure of all CDR-predecessor action items.
  - **QR**: verified FCI list, final fracture analysis, NDE results,
    fracture test results, test-analysis correlation, closure of prior
    action items.
  - **AR**: accepted FCI list, fracture summary report, NDE acceptance
    records, dispositioned waivers, closure of prior action items.
- Open action items from a previous review must be formally closed before
  the current review gate can be passed. An unresolved action item is a
  blocking finding.

## Workflow

1. Identify the target review milestone (SRR, PDR, CDR, QR, or AR) and
   retrieve the required fracture-control input set for that milestone.
   Reject any milestone identifier not in the standard sequence.
2. Determine the FCI list maturity level required for the milestone.
   Compare it against the maturity level of the FCI list currently
   available. If the available level is below the required level, flag a
   maturity shortfall and identify how many maturity steps are needed.
3. For each required deliverable in the milestone input set, confirm
   whether it is available. Record present and missing items separately.
4. If the milestone is CDR or later, confirm that the item
   `previous_review_actions_closed` is in the available set. An absent
   closure record is an automatic blocking finding regardless of other
   deliverable status.
5. Determine review readiness: the gate passes only when every required
   deliverable is present (missing set is empty) and the FCI list maturity
   meets the requirement. Any shortfall produces a non-ready result with
   an explicit list of gaps.
6. Report the readiness verdict, the list of missing inputs, the FCI
   maturity comparison, and the index of the milestone in the
   SRR→PDR→CDR→QR→AR sequence so that predecessor and successor
   milestones can be identified.

## Pitfalls

- Submitting a deliverable that exists but at an insufficient maturity
  level and counting it as present — the maturity check is separate from
  the presence check; a draft FCI list does not satisfy the CDR
  requirement for a final FCI list.
- Treating a missing fracture control plan as acceptable at early
  milestones because no analysis exists yet — even at SRR a draft plan
  is required to establish the programme framework.
- Carrying an open action item from a previous review into the current
  review gate without a formal closure record — the standard requires
  closure before the gate, not at the gate.
- Using a single pass/fail flag without recording which specific inputs
  are missing — the review board needs an itemised gap list to assign
  responsible engineers and set closure dates.

## Behavior contract (gate 3)

The milestone required-inputs, FCI maturity, readiness-check, and
action-item closure logic is exercised by the gate 3 contract test:
scripts/test_fracture_control_reviews.py against
scripts/fracture_control_reviews_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fracture_control_reviews.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
