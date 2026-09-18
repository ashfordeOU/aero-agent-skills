---
name: q1009-major-escalation
description: "Prepare a major nonconformance for submission to the customer review board under ECSS-Q-ST-10-09 clause 5.2.2.5, which the supplier may never dispose of on its own authority. Use when a departure has been categorized major and its analysis package has to leave the supplier inside the agreed window. Checks the report reference against the programme identifier pattern so the customer can track it to closure, tests the package against the larger set a deciding board needs rather than an informed one, confirms the internal signatures that make the package the supplier's own, and counts the submission window in working days past weekends and declared shutdowns. Trigger: ecss, q-st-10-09, major-nonconformance-escalation, customer-review-board-submission, ncr-reference-pattern, submission-package-completeness, submission-working-day-window, internal-approval-signatures."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-major-escalation, major-nonconformance-escalation, customer-review-board-submission, ncr-reference-pattern, submission-package-completeness, submission-working-day-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Major Escalation (space-systems/ecss/q1009-major-escalation)

Use when the task is the internal half of ECSS-Q-ST-10-09 clause 5.2.2.5
— everything a supplier does with a major departure it cannot dispose
of: assemble the package, sign it, and get it to the customer board
inside the window.

## Domain quick reference

- A major departure is not the supplier's to settle. The internal board
  still meets, still analyses and still proposes, but the decision
  belongs to the customer board, so the supplier's whole output at this
  step is a submission — and a submission is judged on completeness and
  timeliness, not on how good the proposal is.
- The submission package is deliberately larger than a minor
  disposition's file. The customer board is being asked to decide, not
  to be informed, so it receives the evidence for the severity category
  itself, the cause analysis, the consequence assessment, the
  higher-level impact statement, the proposed disposition, the
  justification behind it, the supporting analysis or test evidence and
  the corrective-action proposal. Arriving without the severity evidence
  invites the board to re-open the categorization first.
- The reference identifier is not a formality. The customer board minutes
  against it, actions hang off it and closure is claimed against it; a
  free-form reference becomes untrackable the moment two people write it
  differently, so the programme pattern is enforced at the point of
  submission rather than discovered at closure.
- The internal signatures are what make the package the supplier's own
  position rather than one engineer's opinion. Product assurance,
  design engineering and programme management each sign something
  different: that the process was followed, that the technical content
  holds, that the programme consequences are accepted.
- The window is counted in working days, and working days skip weekends
  and declared shutdowns. Counting calendar days makes every submission
  look later than it is and turns an August factory closure into a
  finding against the supplier.
- Being on the deadline is being on time. An exclusive comparison at the
  boundary manufactures a late submission out of a compliant one.

## Workflow

1. Validate the report reference against the programme pattern and
   normalise its case, so the same departure cannot enter the customer's
   system twice under two spellings.
2. Test the package against the major submission set. A flag present but
   false counts as missing — it is a question that was asked and
   answered no.
3. Test the internal approvals. An unknown approver is an input error,
   not an extra signature: the set is fixed because each signature
   covers a different question.
4. Compute the deadline by advancing the agreed number of working days
   from the detection day, skipping weekends and every declared
   non-working day.
5. Compute the working days actually used and what remains, and when the
   submission falls past the deadline, report by how many working days
   rather than by how much wall-clock time.
6. Report readiness only when the reference is valid, the package is
   complete, every signature is in and the window is still open; name
   each failing item separately, because each has a different owner.

## Pitfalls

- Submitting the proposed disposition without the evidence for the
  severity category. The customer board then spends the meeting
  re-deciding whether the departure was major at all, and the
  disposition question is deferred to the next one.
- Sending the package before the internal signatures are in, on the
  argument that the customer needs it quickly. The supplier has then
  submitted a position it has not agreed internally, and a retraction
  costs more than the days saved.
- Counting the window in calendar days. It compresses a ten-working-day
  window to about seven and a half calendar weeks' worth of pressure in
  the wrong direction, and reports compliant submissions as late.
- Ignoring declared shutdowns. A submission spanning a factory closure
  is scored against days nobody was there to work.
- Treating an on-deadline submission as late. The deadline day is inside
  the window; an exclusive comparison at the boundary invents a finding.
- Letting the reference be free text because everyone knows which
  departure it is. They do until the programme has two hundred of them
  and the closure claim cannot be matched to the submission.

## Behavior contract (gate 3)

The reference-pattern validation, the submission-package and
internal-approval completeness checks, the working-day arithmetic past
weekends and declared shutdowns, the deadline derivation, the
on-deadline boundary and the overall readiness verdict are exercised by
the gate 3 contract test: scripts/test_q1009_major_escalation.py against
scripts/q1009_major_escalation_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q1009_major_escalation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
