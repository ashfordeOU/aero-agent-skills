---
name: q6013-class-2-alert-handling
description: "Assess whether a programme flying commercial EEE parts at the intermediate assurance class is really watching the alert channels and answering what arrives, under ECSS-Q-ST-60-13C clause 5.5.3: discount a source whose last confirmed sweep is older than the monitoring interval, admit a delegated subscription only where the delegation is recorded and its forwarding lag is bounded, report plain and credited source coverage against separate floors, refuse a not-applicable disposition carrying no rationale, and run the acknowledgement and disposition clocks in working days from receipt so an unanswered alert keeps accruing. Use when a declared alert-monitoring arrangement has to become a coverage and response verdict. Trigger: ecss, q-st-60-13c-clause-5-5-3, class-two-commercial-eee-alert-monitoring, delegated-alert-subscription-record, alert-source-sweep-staleness, credited-alert-source-coverage, not-applicable-disposition-rationale, alert-response-working-days."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-alert-handling, class-two-commercial-eee-alert-monitoring, delegated-alert-subscription-record, alert-source-sweep-staleness, credited-alert-source-coverage, not-applicable-disposition-rationale, alert-response-working-days]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Alert Handling (space-systems/ecss/q6013-class-2-alert-handling)

Use when the task is the clause 5.5.3 alert duty of ECSS-Q-ST-60-13C at
the intermediate assurance class: a project flies commercial parts whose
manufacturers owe it no warning, and the question is whether the
channels that would carry a warning are being watched, and what happens
to an alert once it lands.

## Domain quick reference

- The duty has two halves and they fail differently. Monitoring fails
  silently — nobody notices a channel nobody reads — while response
  fails loudly, on a clock, in front of the customer. An assessment that
  looks only at the alerts on the desk grades the half that is already
  visible and says nothing about the half that is not.
- The intermediate class differs from the class above by admitting
  delegation. A subscription held by a supplier, a distributor or an
  alert service counts here, which the highest class does not allow, and
  the whole coverage figure turns on whether that delegation was written
  down and how fast the holder forwards.
- A delegated subscription carries a lag the project does not control.
  Bounding that lag is what makes the delegation equivalent to watching
  directly; an unbounded forwarding arrangement is a source in name and
  a gap in practice, so it is discounted rather than credited.
- A subscription nobody has swept recently is not a covered category. A
  live source is one with a confirmed sweep inside the monitoring
  interval; an ancient sweep date is the signature of a mailbox that
  stopped being read when its owner changed role.
- Two coverage figures travel together. The plain figure says how many
  required categories are watched at all; the credited figure weighs a
  delegated category below a direct one, so a programme that outsourced
  its whole alert function reads differently from one that watches, and
  the difference shows before an alert tests it.
- A not-applicable disposition is the cheapest answer and the one most
  often wrong. At this class it is admissible, but only against a
  recorded rationale, because "we do not use that part" is a claim about
  the declared component list that somebody has to be able to re-check.
- Both response clocks run in working days from receipt, and an open
  step accrues to today rather than stopping. An alert acknowledged and
  then forgotten is the shape this catches: the first clock closed, the
  second still running, and nothing on the desk that looks overdue.

## Workflow

1. Validate the monitoring policy: the required source categories, the
   sweep interval, the plain and credited coverage floors, the credit a
   delegated subscription earns, the forwarding bound and the two
   response deadlines. A credited floor above the plain floor is refused
   rather than used.
2. Validate every declared source: a non-blank identifier, no duplicate
   identifier, a recognised category, a known watching mode and a sweep
   date that does not sit after the assessment day. A directly watched
   source carrying a delegation record is an input error.
3. Strike out the sources that cannot count — a delegation nobody
   recorded, a forwarding lag past the bound, a sweep older than the
   interval — and report each reason separately rather than as one
   number.
4. Take the plain coverage over the required categories and the credited
   coverage with the delegation credit applied, name every uncovered
   category, and compare both figures with their floors through a
   tolerance so a coverage landing exactly on a floor reads as met.
5. Validate every alert on the desk and dispose it: an applicable alert
   has to name an action, a not-applicable alert has to carry a
   rationale, and an alert with no disposition at all is undisposed.
6. Count acknowledgement and disposition working days from receipt,
   running an unrecorded step to the assessment day, and raise a finding
   for each deadline passed.
7. Close on one verdict in precedence order: monitoring not established,
   a delegation not recorded, source coverage short, a disposition with
   nothing behind it, a response overdue, or alert handling that meets
   the intermediate class. Report both coverages, the struck-out
   sources, the per-alert clocks and every finding.

## Pitfalls

- Counting a declared subscription as a watched channel. The declaration
  is a list; the sweep date is the evidence, and a category whose only
  source went quiet months ago is uncovered however confidently it
  appears on the chart.
- Crediting a delegated subscription at full weight because it has never
  missed anything. The credit prices the risk of the arrangement, not
  its record to date, and flattening it hides a programme with no
  first-hand channel at all.
- Accepting a delegation because everyone knows who forwards the alerts.
  Without the record there is nobody to hold to the forwarding lag, and
  the arrangement evaporates with the individual who ran it.
- Closing a not-applicable disposition on a verbal check of the parts
  list. The rationale is what a later reviewer re-checks against the
  declared components; with no rationale the cheapest disposition is
  also the least auditable one.
- Stopping the second clock because the alert was acknowledged. An
  acknowledged alert with no disposition is still open and still
  accruing working days, and it is invisible in any report that counts
  only unacknowledged items.
- Counting calendar days against a working-day deadline. It makes an
  on-time answer look late over a long weekend and hides a genuinely
  late one, and it puts the project's record at odds with the source's.

## Behavior contract (gate 3)

The policy validation, source validation, staleness and delegation
screening, the plain and credited coverages against their floors, the
alert disposition reading, the working-day response clocks and the
verdict precedence are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_alert_handling.py against
scripts/q6013_class_2_alert_handling_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_alert_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
