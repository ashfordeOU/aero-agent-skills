---
name: q6012-design-review-general-conduct
description: "Assess whether a microwave design review was validly convened and properly closed out. Use when the task is the conduct half of ECSS-Q-ST-60-12C clause 7.3.1 rather than the technical content: measure the convening notice lead time against the required minimum, test the attendee roster for quorum over the mandatory roles, confirm the chair sits outside the design team under review, validate every register entry for a consistent open or closed state with a recognised disposition, age the open entries against the response time their severity earns, and report the closure ratio with the weighted open load. Trigger: ecss, q-st-60-12c-clause-7-3-1, microwave-design-review-conduct, design-review-convening-notice-lead-time, design-review-attendance-quorum, design-review-chair-independence, design-review-finding-closure-register."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-design-review-general-conduct, microwave-design-review-conduct, design-review-convening-notice-lead-time, design-review-attendance-quorum, design-review-chair-independence, design-review-finding-closure-register]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC — Design Review General Conduct (space-systems/ecss/q6012-design-review-general-conduct)

Use when the task is the clause 7.3.1 conduct question of ECSS-Q-ST-60-12C:
a microwave design review is being convened, or has been held, and the
question is how it was called, who was in the room, and whether the entries
it raised were recorded and closed — not whether the circuit itself is right.

## Domain quick reference

- Notice lead time is a competence condition, not an administrative one. The
  reviewers who are supposed to arrive having read the data package can only
  do that if the package reached them far enough ahead, so a review called on
  two days notice has attendees present and preparation absent.
- Quorum is defined over roles, not headcount. Four people who are all RF
  designers do not cover product assurance or the foundry interface, and a
  roster is only a quorum when every mandatory role is actually represented.
- Chair independence is what separates a review from a walkthrough. A chair
  drawn from the design team under review cannot adjudicate a finding against
  their own work, so the chair flag and the design-team flag on one person is
  a conduct finding in its own right.
- A finding register entry has exactly two consistent states. Open means no
  closure day and no disposition; closed means a closure day at or after the
  day it was raised plus a named disposition saying what was decided. Anything
  else is a record defect and is refused rather than interpreted.
- Severity buys response time, not exemption. A major entry earns a short
  response window and a minor one a longer window; the closure ratio says how
  much of the register is shut, and the weighted open load says how much of
  what remains actually matters.
- Conduct and close-out are separate verdicts. A review can be flawlessly
  convened and still carry an overdue register, and a properly closed register
  does not retrospectively fix a review that never had a quorum.

## Workflow

1. Compute the notice lead time from the convening day to the review day and
   refuse a notice issued after the review it announces.
2. Validate the roster: a non-empty list, one chair at most, boolean role
   flags, and a named person for every role even when the person is the role.
3. Test quorum by walking the mandatory role list against the roles present,
   and name each absent role rather than reporting a count.
4. Resolve the chair and check the chair sits outside the design team; an
   unchaired roster is refused, not treated as independent.
5. Validate each register entry into a consistent open or closed state, refuse
   a duplicate identifier, and treat an absent register as empty.
6. Age the open entries to the as-of day, compare each against the response
   time its severity earns, and collect the entries past it.
7. Compute the closure ratio and the severity-weighted open load, compare the
   ratio with the required value under a named tolerance, and report the two
   verdicts separately: conducted properly, and closed out.

## Pitfalls

- Counting heads for quorum. A crowded room missing the product-assurance role
  is not a quorum, and a roster summary that reports attendance as a number
  hides exactly the absence the check exists to find.
- Letting one person hold the chair and a design-team seat. The record then
  shows both an independent chair and a designer present, and the conflict is
  invisible unless the flags are checked together on the same record.
- Accepting a closed entry with no disposition. "Closed" on its own says the
  row was shut, not what was decided, and a register full of those cannot be
  audited later or reopened on a repeat defect.
- Reading an overdue register as a conduct failure. The review may have been
  convened and quorate exactly as required; merging the two verdicts sends the
  corrective action to the wrong owner.
- Dating a closure before the day the entry was raised. That is a transcription
  defect, and silently reordering the two days turns a data-quality problem
  into a plausible-looking turnaround figure.
- Widening the required closure ratio to make an exact-equality case pass. An
  equality at the limit is a representation question, handled by the tolerance
  inside the comparison; the required value stays as specified.

## Behavior contract (gate 3)

The notice lead time, roster and quorum validation, chair independence,
register state validation, ageing against severity response times and the
conduct and close-out verdicts are exercised by the gate 3 contract test:
scripts/test_q6012_design_review_general_conduct.py against
scripts/q6012_design_review_general_conduct_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6012_design_review_general_conduct.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
