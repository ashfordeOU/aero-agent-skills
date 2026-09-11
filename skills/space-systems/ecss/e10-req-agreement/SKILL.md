---
name: e10-req-agreement
description: "Use when drive the customer and supplier sign-off loop on a technical requirements specification under ECSS-E-ST-10C clause 5.2.3.7: determine who must sign, check each party's recorded review against the specification's current baseline revision, separate a stale agreement from an open comment and from a party that has not responded, flag a review left open beyond the agreed review period, and decide whether the specification is agreed. Trigger: ecss, e-st-10-system-scope, requirements-agreement, sign-off, customer-approval, supplier-approval, baseline-revision, stale-agreement, overdue-review."
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
  tags: [ecss, e-st-10-system-scope, requirements-agreement, sign-off, baseline-revision, stale-agreement, overdue-review]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Requirements Agreement (space-systems/ecss/e10-req-agreement)

Use when the task is to bring a technical requirements specification
to recorded agreement between the customer and every contributing
supplier under ECSS-E-ST-10C clause 5.2.3.7, before the specification
is used as a baseline.

## Domain quick reference

- The signatory set is every listed party, and it is valid only if at
  least one of them holds the customer role. A supplier-only loop
  cannot close an agreement, so the absence of a customer is rejected
  at the input rather than reported as an outstanding signature.
- Agreement is held against a revision, not against the document. A
  party that agreed to an earlier revision has a stale agreement and
  must re-confirm; the record is not cleared, but it no longer counts.
- Four party states are distinguished and each needs different action:
  agreed at the current revision, stale agreement, open comment, and
  no response at all. Collapsing them into "not agreed" loses the
  difference between chasing a signature and dispositioning a comment.
- A party with no review record is pending, exactly as if it had
  opened a review and said nothing. The loop tracks required
  signatories, so silence is a state, not an absence.
- Being overdue is an additional finding layered on an unsettled
  state, not a state of its own. Only an open comment or a pending
  party can be overdue; a stale agreement is not chased against the
  review clock because the elapsed time is measured on a review that
  has not been reopened.
- The elapsed time runs from the day the review was opened to the
  assessment day. A review opened after the assessment day is an input
  error, not a negative duration.
- The specification is agreed only when no required signatory carries
  a violation. There is no majority and no quorum.

## Workflow

1. Validate each party's role and confirm at least one customer is
   present; derive the required signatory set.
2. For each required signatory, take its review record, treating a
   missing record as pending.
3. Resolve the party's state against the specification's current
   revision: agreed, stale agreement, open comment or pending.
4. For an unsettled state, compute the days elapsed since the review
   was opened and compare against the agreed review period.
5. Collect the per-party violations and the state map; the
   specification is agreed only when the violation list is empty.

## Pitfalls

- Counting an agreement recorded against an earlier revision as
  current. The specification moved; the party has not seen what it is
  now being held to.
- Merging "commented" and "silent" into one not-agreed bucket. One
  needs a disposition and a re-issue, the other needs a reminder.
- Treating overdue as a terminal state that replaces the party's
  review state. It is an extra finding on top, and the underlying
  state still determines what must happen next.
- Chasing a stale agreement against the review clock. The elapsed time
  belongs to a review that has not been reopened at the new revision.
- Closing the loop on the customer's signature alone while a
  contributing supplier is still pending, or on the suppliers while no
  customer is on the party list at all.
- Accepting a review opened after the assessment day. That is a data
  error in the register, and reporting it as zero days pending buries
  it.

## Behavior contract (gate 3)

The role validation, signatory derivation, review-state,
days-pending, per-signatory violation and specification-level
agreement logic is exercised by the gate 3 contract test:
scripts/test_e10_req_agreement.py against
scripts/e10_req_agreement_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_req_agreement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
