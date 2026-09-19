---
name: e2040-design-verification-phase-review
description: "Determine whether the gate ECSS-E-ST-20-40C clause 5.4.6 puts at the end of the design and verification phase may release detailed design: check every required deliverable was presented in a released state rather than merely named, fold action severities and hold the phase on an open critical one, weigh open major actions against the tolerance the board set, separate a mandatory exit criterion that is unmet from one nobody assessed, and compare the criteria met against the threshold so a value landing exactly on it passes. Use when a phase review is prepared, held or minuted. Trigger: ecss, e-st-20-electrical-scope, design-verification-phase-review, phase-gate-verdict, review-action-severity, exit-criterion-assessment, required-deliverable-state."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-design-verification-phase-review, design-verification-phase-review, phase-gate-verdict, review-action-severity, exit-criterion-assessment, required-deliverable-state, detailed-design-release]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Design and Verification Phase Review (space-systems/ecss/e2040-design-verification-phase-review)

Use when the task is the gate duty of ECSS-E-ST-20-40C clause 5.4.6 --
deciding whether the design and verification phase is closed and the
detailed design phase may start, and saying on what grounds, because
the grounds are what the next phase is built on.

## Domain quick reference

- Three things carry the gate: the deliverables the review required,
  the actions it raised, and the exit criteria it set. A verdict
  reached from any one of them alone is the failure this check exists
  for -- a board that sees a complete deliverable list closes a phase
  whose exit criteria nobody assessed.
- A deliverable has a state, not just a presence. A required document
  presented as a draft has been shown, not delivered, and the next
  phase will build on something still moving. Presented and released
  are different findings and both have to be visible.
- Action severity decides whether work continues. An open critical
  action holds the phase whatever else is clean. Open major actions
  are weighed against the tolerance the board set, and minor ones ride
  along with the verdict rather than blocking it.
- An exit criterion nobody assessed is not a criterion that failed,
  and it is certainly not one that passed. Folding the unassessed in
  with the failed hides how much of the gate was actually looked at;
  folding them in with the passed closes a phase on silence.
- The verdict has three outcomes, and the middle one carries weight:
  proceed, proceed with actions, and repeat the review. Collapsing the
  middle into proceed loses the actions; collapsing it into repeat
  stops a phase that is genuinely closeable.
- Criteria coverage is a fraction. A threshold met exactly is met, so
  the comparison absorbs representation error: a three-in-four landing
  on a 0.75 threshold is a pass, and a strict comparison against a
  computed division is what reopens a phase that is exactly on target.

## Workflow

1. Resolve the required deliverables and what the review was shown,
   folding each state onto released, draft or absent. Refuse a
   repeated identifier or an unknown key as an input defect.
2. Report every required deliverable never presented, and separately
   every one presented in a state below released.
3. Resolve the actions: unique identifier, severity folded onto
   critical, major or minor, and status folded onto open or closed.
4. Resolve the exit criteria, keeping met, unmet and unassessed
   distinct, and report every mandatory criterion in either of the
   last two states.
5. Compute the fraction of criteria assessed as met and compare it
   against the threshold, absorbing representation error.
6. Derive the verdict: repeat the review on an open critical action, a
   missing or unreleased required deliverable, a mandatory criterion
   not met, or open major actions past the tolerance; proceed with
   actions when only tolerated open actions remain; proceed otherwise.

## Pitfalls

- Closing the gate on the deliverable list. Every document can be on
  the table with the exit criteria unassessed, and the phase closes on
  paperwork rather than on the state of the design.
- Accepting a draft as a delivery. The next phase reads it, the
  document moves, and nothing in the minutes records that what was
  approved is not what was later used.
- Counting an unassessed exit criterion as passed. Silence becomes
  agreement, and the criterion nobody looked at is reliably the one
  that mattered.
- Collapsing proceed-with-actions into one of its neighbours. Folding
  it into proceed drops the actions the board attached to the release;
  folding it into repeat stops a phase that only needed them tracked.
- Comparing a computed criteria fraction against its threshold with a
  strict inequality. A three-in-four division landing on 0.75 can sit
  a unit in the last place below it and reopen a phase that is exactly
  on target.

## Behavior contract (gate 3)

The deliverable, action and criterion resolution, severity and state
folding, unassessed-criterion separation, criteria-threshold
comparison and the three-way verdict are exercised by the gate 3
contract test:
scripts/test_e2040_design_verification_phase_review.py against
scripts/e2040_design_verification_phase_review_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_design_verification_phase_review.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
