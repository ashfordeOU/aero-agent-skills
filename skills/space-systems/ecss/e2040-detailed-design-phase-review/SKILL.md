---
name: e2040-detailed-design-phase-review
description: "Evaluate whether the detailed design phase review ECSS-E-ST-20-40C 5.5.6 defines can close before layout activities start: resolve the deliverables the review was called on, pair every review item discrepancy with its severity and disposition so an unresolved major blocks the gate whichever minor ones were closed around it, register the actions carried forward with an owner and a due milestone, and reach a pass, pass-with-actions or fail verdict. Use when a detailed design gate is being prepared or its outcome argued. Trigger: ecss, e-st-20-electrical-scope, detailed-design-phase-review, review-item-discrepancy-disposition, major-discrepancy-blocking, review-action-registration, design-gate-verdict, layout-start-authorisation."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-detailed-design-phase-review, detailed-design-phase-review, review-item-discrepancy-disposition, major-discrepancy-blocking, review-action-registration, design-gate-verdict, layout-start-authorisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Detailed Design — Phase Review (space-systems/ecss/e2040-detailed-design-phase-review)

Use when the task is the gate duty of ECSS-E-ST-20-40C 5.5.6 -- saying
whether detailed design can be declared closed, and whether layout
activities may start on the device, from the deliverables, the
discrepancies and the actions the review actually produced.

## Domain quick reference

- The verdict follows from the record, not from the meeting. Three inputs
  settle it: the deliverables the review was called on, the discrepancies
  raised against them, and the actions carried out.
- A deliverable that was never issued has not been reviewed, however
  thoroughly it was discussed. A deliverable issued as a draft is worse:
  the gate would close on something the project has not committed to.
- Severity and disposition only mean something as a pair. A major
  discrepancy left open blocks the gate whatever the surrounding minor
  ones did, and a rejected discrepancy is resolved even though it was
  never agreed.
- A discrepancy accepted with an action has to name an action the review
  actually registered. An accepted discrepancy pointing at nothing is the
  common way a finding leaves a review and is never worked again.
- An action with no owner cannot be worked and an action with no due
  milestone cannot be carried to a gate, so both are reported even when
  the gate otherwise passes.
- A closure fraction landing exactly on its threshold is a pass. The
  comparison absorbs representation error instead of failing a review
  that is precisely on target.
- Three verdicts exist. Carried actions mean pass-with-actions, not pass,
  and not fail.

## Workflow

1. Resolve the deliverables: unique identifiers, a recognised state and
   whether each is required at this gate.
2. Resolve the discrepancies: unique identifiers, a folded severity and
   disposition, the deliverable each is raised against and the action
   each accepted one names.
3. Resolve the actions: unique identifiers, owner, due milestone and open
   or closed state.
4. Report every required deliverable that is not issued, and every one
   reviewed as a draft. Both block the gate.
5. Report every major discrepancy that is neither closed nor rejected.
   Each one blocks the gate on its own.
6. Report accepted discrepancies naming no action or an unregistered one,
   discrepancies raised against a deliverable the review was not called
   on, and actions with no owner or no due milestone.
7. Compute the closure fraction, compare it with the threshold absorbing
   an exact landing, then reach the verdict and say whether layout may
   start.

## Pitfalls

- Reading the closure percentage as the gate. A review can close ninety
  per cent of its discrepancies and still be held by the single major one
  that is left open.
- Counting a rejected discrepancy as unresolved. It is dispositioned, the
  gate does not wait for it, and treating it as open fails reviews that
  are complete.
- Accepting a discrepancy with an action nobody registered. The finding
  then leaves the review with a disposition and no owner, and reappears
  at the next gate as a surprise.
- Passing a gate on a draft deliverable. The device team reviews one
  document and layout starts against another.
- Failing a review whose closure fraction lands exactly on its threshold.
  A two-in-three division can sit a unit in the last place below the
  figure it was compared with.

## Behavior contract (gate 3)

The severity and disposition folding, deliverable state handling,
blocking-discrepancy detection, action registration, closure arithmetic
with exact threshold landings and the three-way verdict are exercised by
the gate 3 contract test:
scripts/test_e2040_detailed_design_phase_review.py against
scripts/e2040_detailed_design_phase_review_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_detailed_design_phase_review.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
