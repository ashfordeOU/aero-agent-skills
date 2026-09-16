---
name: q60-class-1-alert-handling
description: "Use when an advisory lands on a part already on the declared components list. Evaluate an alert, errata sheet or manufacturer advisory against the class 1 EEE parts a programme has already selected, under ECSS-Q-ST-60C clause 4.5.3: match the advisory to declared-list entries, place each entry at its procurement stage, derive the action that stage earns from deselection through to an in-orbit impact statement, decide whether the part approval itself is invalidated and must be re-approved, fan the advisory out to every other programme holding the same selection, and count acknowledgement working days against the severity deadline. Trigger: ecss, q-st-60c, class-1-eee-advisory, declared-component-list-impact, part-approval-revalidation, procurement-stage-action, cross-programme-advisory-dissemination, advisory-acknowledgement-deadline."
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
  tags: [ecss, q-st-60c-eee-components-scope, q60-class-1-alert-handling, class-1-eee-part, declared-component-list-impact, eee-part-approval-revalidation, procurement-stage-advisory-action, cross-programme-advisory-dissemination]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Alert and Advisory Handling (space-systems/ecss/q60-class-1-alert-handling)

Use when the task is the alert step of ECSS-Q-ST-60C clause 4.5.3 for an
EEE part procured to the highest assurance class — turning an incoming
alert, errata sheet or manufacturer advisory into a stage-by-stage
action list over the selections the programme has already made, plus the
acknowledgement record that shows it was handled in time.

## Domain quick reference

- An advisory arrives against a part number. The programme does not hold
  part numbers; it holds selections at different stages of their life.
  The whole job is mapping one into the other and doing it before the
  next build step moves a part further down the list.
- The manufacturer qualifies the match. A generic part number from a
  second source is a different device with a different process, and
  sweeping it into the advisory's scope scraps good parts and hides the
  real ones. When the advisory names no manufacturer, every source
  matches, and that is the wider, more expensive case.
- What an entry earns follows entirely from where it had reached. A part
  only selected can be swapped for an alternative at no cost. Ordered
  stock is held. Received stock is quarantined and re-verified. A part
  already in build raises a nonconformance and a retrofit assessment,
  and a part already delivered or flying owes a written impact statement
  the customer will read.
- An advisory can invalidate the part approval rather than just the lot.
  Anything touching safety, reliability or continued availability puts
  the approval back on the table once the part has been bought, which
  means a re-approval, not a note in the file.
- Dissemination is half the clause. The same selection usually sits in
  more than one programme, and an advisory acted on by the receiving
  project alone leaves the sister project holding suspect parts it has
  never heard about.
- Acknowledgement runs in working days from receipt and the deadline
  tightens with severity. An advisory nobody has acknowledged is still
  accruing against that clock.

## Workflow

1. Validate the advisory: a known severity, at least one part number, a
   receipt date and the programme that received it.
2. Match every declared-list entry on part number, and on manufacturer
   too when the advisory names one.
3. For each matched entry, read its procurement stage and attach the
   action that stage earns.
4. Decide per entry whether the part approval must be re-issued, and
   flag any entry that owes a re-approval without an approval reference
   to re-issue.
5. Scan the wider portfolio for the same selection in other programmes
   and build the dissemination list, excluding the originator.
6. Count acknowledgement working days from receipt to acknowledgement,
   or to the assessment date while it is open, and compare with the
   severity deadline.
7. Report the impacted entries, the union of actions, the re-approval
   list, the dissemination list, the timing and every finding.

## Pitfalls

- Matching on part number alone when the advisory names a manufacturer.
  Second-source devices share numbers and share nothing else; the match
  has to carry the manufacturer or it is the wrong set of parts.
- Assuming a missing manufacturer field narrows the scope. An advisory
  with no manufacturer named is wider, not narrower, and every source of
  that part number is in scope until shown otherwise.
- Acting only on stock. The entries still at selection are the cheapest
  to fix and the easiest to miss, because they are not in any store
  system yet.
- Treating an advisory as a lot problem when it is an approval problem.
  A withdrawal or a safety advisory undermines the justification the
  selection rests on, and closing it without re-approving leaves an
  unjustified part in the declared list.
- Closing the advisory inside the receiving project. The sister
  programme sharing the selection is the one that will fly the suspect
  part, and it only finds out if the dissemination list is built.
- Counting calendar days against a working-day acknowledgement limit,
  and stopping the count because the advisory is under assessment. It is
  acknowledged or it is still running.

## Behavior contract (gate 3)

The advisory validation, declared-list matching with and without a named
manufacturer, procurement-stage action derivation, part re-approval
decision, cross-programme dissemination and acknowledgement working-day
comparison are exercised by the gate 3 contract test:
scripts/test_q60_class_1_alert_handling.py against
scripts/q60_class_1_alert_handling_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_1_alert_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
