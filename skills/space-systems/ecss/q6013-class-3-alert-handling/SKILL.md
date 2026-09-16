---
name: q6013-class-3-alert-handling
description: "Use when an alert or errata notice reaches a thinly traced class 3 parts stock. Evaluate a manufacturer alert and the watch that caught it for commercial EEE parts held at the lowest assurance class under ECSS-Q-ST-60-13C clause 6.5.3: grade the subscribed alert sources against the mandatory set and the watch review interval, resolve each holding's traceability grade into a screening resolution, read a holding with no readable date code as presumed affected rather than cleared, derive the corrective response each holding state and criticality earns, and count acknowledgement and corrective working days against the category deadlines. Trigger: ecss, q-st-60-13c-clause-6-5-3, class-three-commercial-eee-alert-watch, alert-source-coverage-floor, traceability-screening-resolution, presumed-affected-holding-rule, alert-corrective-response-window."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-3-alert-handling, class-three-commercial-eee-alert-watch, alert-source-coverage-floor, traceability-screening-resolution, presumed-affected-holding-rule, alert-corrective-response-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Alert Handling (space-systems/ecss/q6013-class-3-alert-handling)

Use when the task is clause 6.5.3 of ECSS-Q-ST-60-13C at the lowest
assurance class: an alert or errata notice has arrived, and it has to become
a screened, actioned and time-stamped response over parts the project may
not be able to trace -- starting with whether the watch that caught it was
a watch at all.

## Domain quick reference

- The watch is graded before any single alert is. An alert handled well
  proves nothing about the alerts nobody subscribed to, so the source
  coverage and the review interval are read first and reported beside the
  screening result.
- Two channels are not optional even here: the manufacturer notice service
  and the agency alert system. A watch missing one of them is not a thin
  watch, it is an absent one, and the remaining sources do not substitute.
- An alert that arrives through a source the watch does not subscribe to is
  a finding in its own right, however well it was handled. It was caught by
  luck, and luck does not have a coverage figure.
- What the project can show about a holding decides what a screening result
  is worth. A lot-traced or date-code-bearing holding screens definitively;
  a holding known only by part number screens presumptively; an untraced
  holding does not screen at all.
- The presumption runs toward affected, not away from it. A holding whose
  part number matches and whose date code cannot be shown has no evidence
  excluding it, and nothing at this class licenses an exclusion nobody can
  demonstrate. It is carried as presumed affected and counted separately
  from the confirmed ones, so the presumption stays visible.
- An untraced holding is a different failure from a presumed-affected one.
  It cannot even be matched to the alert by part number, so the response is
  traceability recovery rather than quarantine, and the alert cannot be
  closed while one exists.
- Criticality decides whether a presumption is good enough to act on. At or
  below the criticality floor the holding is escalated for traceability
  recovery instead of taking the routine response, because a critical item
  should not be retained or scrapped on a guess in either direction.
- Where the parts are decides what is owed. Stock and kits can be
  quarantined immediately; assembled hardware needs a retrofit assessment;
  delivered hardware needs an in-service assessment owed to the customer,
  which is the most expensive branch and the one discovered late most often.
- Date codes are four digits, a two-digit year and a week, and they do not
  compare as strings once the year rolls over. Week 53 of one year is
  numerically larger than week 02 of the next, so each code is resolved into
  an ordinal before the inclusive range test.
- The response has two clocks, both in working days from receipt:
  acknowledgement, which is short and set by the alert category, and
  corrective action, which is longer. An alert with no corrective action
  recorded is still running against its clock.

## Workflow

1. Grade the watch: the subscribed sources against the mandatory set and the
   coverage floor under a named tolerance, and the calendar days since the
   last review against the review interval, with an age equal to the
   interval still inside it.
2. Validate the alert: a recognised category and source, at least one
   affected part number, a date-code range that is not inverted, and a
   receipt date. An unknown key is refused rather than ignored.
3. Resolve every holding's traceability grade into a screening resolution
   before testing anything, because the resolution decides which of the
   verdicts the holding can reach.
4. Screen each holding. An untraced holding is unscreenable; a
   non-matching part number ends it; a match with a readable date code takes
   the inclusive range test; a match with no readable or resolvable date
   code is presumed affected.
5. Derive each holding's corrective response from its verdict, its state and
   its criticality, escalating an unscreenable holding and a presumed
   affected critical item for traceability recovery.
6. Count working days from receipt to acknowledgement and to corrective
   action, excluding weekends, counting to the assessment date where a step
   has not happened so an open item keeps accruing.
7. Compare both counts with the deadlines the category earns, and report the
   affected, presumed-affected and unscreenable quantities separately.
8. Close on the first blocking condition in order -- watch inadequate,
   holdings untraceable, acknowledgement late, corrective action late --
   then on presumption where any holding was presumed affected, and only
   otherwise on a clean close.

## Pitfalls

- Grading the alert and not the watch. An alert response is only as good as
  the channel that delivered it, and a programme subscribed to one source
  has no way to know what it missed.
- Reading a missing date code as outside the affected range. An absent value
  is unknown, not clear, and at this class it means the lot cannot be
  excluded rather than that it was.
- Folding the presumed-affected lots into the confirmed count. They are the
  ones a later traceability recovery can still move, and merging the two
  figures hides both the exposure and the way to reduce it.
- Treating an untraced holding as merely a presumed-affected one. It cannot
  be matched to the alert at all, so quarantining it answers a question
  nobody has asked yet.
- Acting on a presumption for a critical item. The criticality floor exists
  because scrapping good parts and retaining bad ones are both expensive
  there, and the recovery is cheaper than either.
- Comparing date codes as strings. The comparison only works inside one
  year; across a year boundary it silently inverts and clears exactly the
  lots at the edge of the window.
- Counting calendar days against a working-day deadline. It makes an on-time
  response look late over a long weekend and hides a genuinely late one.
- Stopping the corrective clock because the alert was acknowledged.
  Acknowledgement closes only the first clock; an alert with no recorded
  corrective action is still open and still accruing.
- Forgetting the delivered branch. Parts already with the customer are the
  ones an alert is most expensive to miss, and they are the least visible in
  a stores-oriented inventory extract.

## Behavior contract (gate 3)

The watch grading across source coverage and review interval, the alert
validation, date-code parsing and ordinal range test, traceability
resolution, holding screening including the presumed-affected and
unscreenable branches, corrective response derivation, the acknowledgement
and corrective working-day counts against their deadlines and the closing
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_alert_handling.py against
scripts/q6013_class_3_alert_handling_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6013_class_3_alert_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
