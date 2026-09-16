---
name: q6013-class-1-alert-handling
description: "Use when a supplier alert, errata sheet, change notice or discontinuance notice arrives and the project must show which lots it touches. Assess a manufacturer alert or errata notice against the highest-assurance (class 1) commercial EEE parts a project holds, under ECSS-Q-ST-60-13C clause 4.5.3: match the named part numbers, resolve each holding date code into an ordinal and test it against the inclusive affected range, escalate a lot whose date code is unreadable instead of reading it as unaffected, derive the quarantine, retrofit or in-service action each holding state earns, and count acknowledgement and disposition working days against the deadlines the category sets. Trigger: ecss, q-st-60-13c, manufacturer-alert-handling, commercial-eee-errata, affected-date-code-range, alert-acknowledgement-deadline, lot-quarantine-action, class-1-commercial-part."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-alert-handling, class-1-commercial-eee-part, manufacturer-alert-screening, commercial-eee-errata-notice, affected-date-code-range, alert-response-working-days]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Alert and Errata Handling (space-systems/ecss/q6013-class-1-alert-handling)

Use when the task is the alert step of ECSS-Q-ST-60-13C clause 4.5.3 for
a commercial EEE part procured to the highest assurance class — turning a
manufacturer alert, errata sheet or change notice into a screened,
actioned and time-stamped response over the lots the project actually
holds.

## Domain quick reference

- A commercial part has no obligation to tell its user anything, so the
  alert channel is the only warning the project gets. Subscribing to it
  is half the control; the other half is showing, per alert, which of
  the project's lots it reached and what happened to them.
- An alert names part numbers and a date-code window, not lots. The
  project holds lots. Screening is therefore a two-part test: the part
  number matches what the alert names, and the lot's date code falls
  inside the named window. Both bounds of that window are inclusive — a
  lot sitting exactly on the first or last affected week is affected.
- Date codes are four digits, a two-digit year and a week. They do not
  compare as strings once the year rolls over: week 53 of one year is
  numerically larger than week 02 of the next, so the test resolves each
  code into an ordinal before comparing.
- A lot with no readable date code is not an unaffected lot. It is a lot
  whose status is unknown, and the only honest outcome is escalation for
  date-code recovery from the receipt record. Reading a blank field as a
  clear result is how an alert is closed over parts it actually hit.
- Where the parts are decides what is owed. Stock and kits can be
  quarantined immediately; parts already soldered need a retrofit
  assessment; parts already delivered need an in-service assessment
  owed to the customer, which is the most expensive branch and the one
  that must never be discovered late.
- The response has two clocks, both in working days from receipt of the
  alert: acknowledgement, which is short and depends on the alert
  category, and disposition, which is longer. An alert with no
  disposition recorded is still running against its clock.

## Workflow

1. Validate the alert: a known category, at least one affected part
   number, and a date-code range that is not inverted. Normalise part
   numbers to a single case so a supplier's lower-case listing still
   matches the stores record.
2. Resolve the range bounds and every holding's date code into ordinals.
   A code that is not four digits, or whose week sits outside 1 to 53,
   is unreadable and is handled as unscreenable, not rejected silently.
3. Screen each holding: no part-number match ends it; a match with a
   readable code in range makes it affected; a match with no readable
   code makes it unscreenable.
4. Derive each affected holding's action from its state — quarantine
   stock, quarantine kit, retrofit assessment, in-service assessment —
   and give every unscreenable holding the date-code recovery action.
5. Count working days from receipt to acknowledgement, and from receipt
   to disposition, excluding weekends. When a step has not happened,
   count to the assessment date instead, so an open item keeps accruing.
6. Compare both counts with the deadlines the category earns and raise a
   finding for each breach.
7. Report the affected and unscreenable quantities separately, the union
   of actions, the response timing and every finding. The alert is
   closeable only when nothing is unscreenable, both clocks are inside
   their deadlines and the disposition is actually recorded.

## Pitfalls

- Screening on part number alone and quarantining the whole holding. The
  date-code window is the reason the alert is bounded; ignoring it
  scraps good stock and buries the lots that matter.
- Comparing date codes as strings. The comparison only works inside one
  year; across a year boundary it silently inverts and clears exactly
  the lots at the edge of the window.
- Treating a missing date code as outside the range. An absent value is
  unknown, not clear, and the lot has to be escalated until the receipt
  record supplies the code.
- Counting calendar days against a working-day deadline. It makes an
  on-time response look late over a holiday weekend and hides a genuinely
  late one, and it puts the project's own record at odds with the
  supplier's.
- Stopping the disposition clock because the alert was acknowledged.
  Acknowledgement closes only the first clock; an alert with no recorded
  disposition is still open and still accruing working days.
- Forgetting the delivered branch. Parts already with the customer are
  the ones an alert is most expensive to miss, and they are the least
  visible in a stores-oriented inventory extract.

## Behavior contract (gate 3)

The alert validation, date-code parsing and ordinal range test, holding
screening, action derivation, working-day counting and deadline
comparison are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_alert_handling.py against
scripts/q6013_class_1_alert_handling_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6013_class_1_alert_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
