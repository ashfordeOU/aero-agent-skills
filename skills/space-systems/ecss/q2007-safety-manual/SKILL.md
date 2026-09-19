---
name: q2007-safety-manual
description: "Maintain the safety manual of a space test centre under ECSS-Q-ST-20-07C clause 5.9.3: confirm it carries the hazard inventory, controls, responsibilities, emergency plans and the working chapters that hang off them; parse and order issue.revision identifiers so a chapter ahead of the manual is caught as an uncontrolled update; grade the review currency, the hazard-register changes that postdate issue, the acknowledged fraction of controlled copies and the withdrawal of superseded ones. Use when a centre safety manual, its chapter list or its distribution record has to be assessed or revised. Trigger: ecss, q-st-20-07c, test-centre-safety-manual, safety-manual-chapters, manual-issue-revision-control, controlled-copy-acknowledgement, obsolete-copy-withdrawal, hazard-register-staleness."
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
  tags: [ecss, q-st-20-test-centre-scope, q2007-safety-manual, test-centre-safety-manual, safety-manual-chapters, manual-issue-revision-control, controlled-copy-acknowledgement, hazard-register-staleness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Safety Manual Content and Update Control (space-systems/ecss/q2007-safety-manual)

Use when the task is the safety-manual step of ECSS-Q-ST-20-07C clause 5.9.3
— deciding whether the manual holds what the centre's people need at the
moment they need it, and whether the copy in their hands is the one the
centre thinks it issued.

## Domain quick reference

- The manual has two failure modes and they are independent: it can be
  incomplete, and it can be out of control. A complete manual whose chapters
  were revised without approval is worse than an incomplete one, because it
  reads as authoritative.
- The content owed is the hazard inventory, the controls that hold those
  hazards, who is responsible for what, and the emergency plans. Around
  those sit the working documents that make them usable at the bench: the
  permit-to-work scheme, the training requirements and the incident
  reporting route.
- Issue and revision are two different things. A new issue is a re-approval
  of the document; a revision is a change inside the issue. Ordering them
  correctly matters because that ordering is the only way to see a chapter
  that moved ahead of the manual it lives in, which is the signature of an
  uncontrolled update.
- Currency has two clocks. The review interval says the manual is looked at;
  the hazard register says the manual is right. A change to the hazards
  after the manual's issue day makes the content stale whatever the review
  interval says, and it is the clock that is usually missed.
- A controlled copy is only controlled once its receipt is acknowledged. The
  acknowledged fraction is the real measure of distribution, and a copy
  unacknowledged is a copy at an unknown revision.
- Withdrawal of the superseded copies is the other half of distribution, and
  the half that is skipped. A superseded copy left at the bench does not
  merely fail to help; it actively states the wrong control.

## Workflow

1. Parse the manual's own issue.revision identifier, refusing anything that
   is not written issue then revision, so the ordering that follows is
   well founded.
2. Check the chapter set against the chapters the manual owes and name the
   absent ones rather than counting them.
3. Validate each chapter: a non-empty name, a parseable revision, at least
   one page, and an approval.
4. Compare each chapter's revision with the manual's; a chapter ahead of the
   manual is an uncontrolled update and a finding, a chapter behind it is
   normal.
5. Grade the review currency as current, due or overdue on exact integer day
   arithmetic from the issue day and the review interval.
6. List the hazard-register change days that postdate the issue day; any of
   them makes the content stale, independently of the review clock.
7. Compute the acknowledged fraction of the controlled copies against the
   required fraction with a named tolerance, and confirm the superseded
   copies were withdrawn.
8. Call the manual controlled only when the finding list is empty.

## Pitfalls

- Ordering revisions as strings. "B.10" sorts before "B.2" as text, and a
  two-letter issue sorts before a one-letter one, so a chapter that moved
  ahead of its manual is invisible to a string comparison.
- Reading a chapter at a higher revision than the manual as simply the
  newest content. It is the opposite: the chapter changed without the manual
  being re-approved, so nothing guarantees the rest of the manual agrees
  with it.
- Grading currency on the review interval alone. The review clock says the
  manual was looked at on schedule; a hazard change after the issue day says
  the content no longer matches the facility.
- Counting copies issued as copies distributed. Distribution closes on the
  acknowledgement, and an unacknowledged copy is at an unknown revision.
- Issuing the new revision without withdrawing the superseded one. Two
  revisions in circulation is the condition under which someone follows the
  control that was removed.
- Widening a required acknowledgement fraction to make an exact-equality
  case pass. An equality at the limit is a representation question, handled
  by the tolerance inside the comparison; the requirement stays as
  specified.

## Behavior contract (gate 3)

The revision parsing and ordering, chapter completeness and validation,
ahead-of-manual detection, review-currency arithmetic, hazard-staleness
listing, acknowledgement fraction and overall control verdict are exercised
by the gate 3 contract test:
scripts/test_q2007_safety_manual.py against
scripts/q2007_safety_manual_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_safety_manual.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
