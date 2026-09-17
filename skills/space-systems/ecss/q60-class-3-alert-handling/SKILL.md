---
name: q60-class-3-alert-handling
description: "Assess an alert, errata sheet or manufacturer advisory against the class 3 EEE parts a programme has already selected, under ECSS-Q-ST-60C clause 6.5.3: resolve each declared-list entry on part number, manufacturer and date-code range together and let the answer stay three valued, work an entry the records cannot rule out as affected while naming the evidence that would close it, derive the action from severity and procurement stage jointly, move the response into the design where the part can no longer be bought, rank the queue, and count acknowledgement working days. Use when an advisory lands on a selected class 3 part. Trigger: ecss, q-st-60c-clause-6-5-3, class-3-eee-advisory, class-3-indeterminate-applicability, class-3-obsolescence-response-route, class-3-advisory-queue-ranking, class-3-advisory-acknowledgement-deadline."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-3-alert-handling, class-3-eee-advisory, class-3-indeterminate-applicability, class-3-obsolescence-response-route, class-3-advisory-queue-ranking, class-3-advisory-acknowledgement-deadline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Alert and Advisory Handling (space-systems/ecss/q60-class-3-alert-handling)

Use when the task is the clause 6.5.3 step of ECSS-Q-ST-60C: an alert, an
errata sheet or a manufacturer advisory has landed on a part the programme
already selected at the lowest assurance class, and the question is which of
the parts on the declared list it actually reaches, what that earns, and by
when. The hard part at this class is not the action. It is that the records
frequently cannot say whether the advisory reaches a given entry at all.

## Domain quick reference

- Applicability is three valued here, not two. The part number decides first
  and a different one excludes the entry outright. After that a named
  manufacturer or a named date-code range can exclude an entry only when the
  entry records that same field. Where it records nothing, the answer is
  indeterminate, because the records cannot rule the entry out.
- An indeterminate entry is worked as if it applied. That is the safe default
  and, at this class, the common one. What the assessment owes alongside it is
  the specific evidence that would decide it: a goods-in record naming the
  actual manufacturer, or a label record carrying the delivered date code.
- Indeterminate is not the same as urgent. It is worked, but it sits just
  under a confirmed match at the same severity and stage, so a queue never
  puts an unproven entry ahead of a proven one.
- The action comes from severity and procurement stage together. The same
  alert reselects a part still only on paper, holds an order, quarantines
  stock, recalls a kit, or reaches the customer, depending on how far the
  entry had travelled when the advisory arrived.
- Availability decides where the response can be built at all. A part still
  on the market with an approved equivalent is answered from stock; without
  one it earns a last-time buy with added screening; and a part that can no
  longer be bought cannot be answered by procurement, so anything above an
  information notice moves the response into the design.
- One advisory rarely touches one programme. The same commercial part number
  usually sits on several declared lists, and the advisory is fanned out to
  every programme holding it.
- The acknowledgement clock runs in working days from issue and runs shortest
  for a safety alert. An unacknowledged advisory is still accruing.

## Workflow

1. Validate the advisory: an identifier, a part number, a known severity, an
   issue date, and a date-code range given as both ends or neither.
2. Resolve applicability for every declared-list entry on part number,
   manufacturer and date-code range together.
3. Drop the excluded entries. For every remaining entry record whether it is
   confirmed or indeterminate and, if indeterminate, what would close it.
4. Derive the action each entry earns from severity and stage jointly.
5. Choose the supply route from whether the part is still procurable and
   whether an approved equivalent already exists.
6. Score and order the queue so confirmed matches lead, and band the scores.
7. Count the applicability states across the whole list and report the worked
   share as an exact pair as well as a fraction.
8. Count acknowledgement working days against the severity deadline, build the
   dissemination list, and report every finding. The advisory closes only when
   nothing is outstanding and an acknowledgement date exists.

## Pitfalls

- Reading a missing field as an exclusion. An entry that records no
  manufacturer has not been shown to be a second source; it has been shown to
  be untraceable, and it is worked as affected until that changes.
- Recording an entry as indeterminate and stopping there. The assessment owes
  the evidence that would decide it, or nothing ever closes.
- Letting indeterminate entries flood the top of the queue. They are worked,
  but a confirmed match at the same severity and stage is worked first.
- Deriving the action from the stage alone. An alert and a safety alert part
  company exactly at installed hardware, where one assesses the application
  and the other removes the part.
- Purging stock on an obsolete part. Where the part can no longer be bought
  there is no stock to purge into, and the response that actually exists is a
  design change.
- Comparing date codes as strings. A four-digit code is a year and a week, and
  it is compared as that ordered pair against both ends of the window.
- Accepting a date-code range with only one end given. A half-specified window
  silently matches everything or nothing.
- Answering the advisory on the programme that received it and leaving the
  sister programmes holding the same selection unwarned.

## Behavior contract (gate 3)

The advisory validation, date-code parsing and range comparison, three-valued
applicability resolution, closing-evidence derivation, severity-and-stage
action lookup, supply-route selection, queue scoring and banding, exposure
counting and acknowledgement working-day comparison are exercised by the gate
3 contract test: scripts/test_q60_class_3_alert_handling.py against
scripts/q60_class_3_alert_handling_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q60_class_3_alert_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
