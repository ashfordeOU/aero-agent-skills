---
name: q60-class-2-alert-handling
description: "Assess an alert, errata sheet or manufacturer advisory against the class 2 EEE parts a programme has already selected, under ECSS-Q-ST-60C clause 5.5.3: match each declared-list entry on part number, manufacturer and date-code window together, derive the action the severity and the procurement stage jointly earn rather than the stage alone, score every match so a queue is worked in the order the hardware needs, decide whether the part approval itself reopens, fan the advisory out to the other programmes holding the same selection, and count acknowledgement working days. Use when an advisory lands on a selected class 2 part. Trigger: ecss, q-st-60c, class-2-eee-advisory, class-2-date-code-window-match, class-2-severity-stage-action, class-2-advisory-impact-score, class-2-advisory-acknowledgement-deadline."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c, q60-class-2-alert-handling, class-2-eee-part, class-2-eee-advisory, class-2-date-code-window-match, class-2-severity-stage-action, class-2-advisory-impact-score]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Alert and Advisory Handling (space-systems/ecss/q60-class-2-alert-handling)

Use when the task is the alert step of ECSS-Q-ST-60C clause 5.5.3 for an EEE
part procured to the intermediate assurance class — turning an incoming alert,
errata sheet or manufacturer advisory into a prioritised action list over the
selections the programme has already made, plus the acknowledgement record that
shows it was handled in time.

## Domain quick reference

- A class 2 part number is the weakest of the three identity axes. The same
  generic number is second-sourced by other manufacturers and built over many
  date codes, so applicability is a three-axis test: part number, manufacturer
  when the advisory names one, and the date-code window when it gives one.
- An entry whose date code is unknown is not an entry the advisory misses. It
  is an entry nobody can rule in or out, and it has to be reported as such
  rather than quietly dropped from the match list.
- The action comes from the severity and the stage together. A stage-only table
  gives a typographic erratum the same weight as a withdrawal and stops a build
  for it; the same table gives a withdrawal on a flying part a note.
- Advisories arrive faster than they can be worked. Scoring severity, stage and
  affected quantity into one integer is what turns a pile into a queue, and
  integer arithmetic is what makes two people agree on the order.
- Reopening the part approval is a severity decision, not a stage decision, and
  it only bites when something actually matched. An advisory over a part the
  programme does not hold reopens nothing.
- An advisory acted on by one project only is an advisory half handled. The
  same selection in another programme carries the same exposure.
- The acknowledgement clock runs in working days from receipt and keeps
  accruing while the advisory sits unacknowledged.

## Workflow

1. Validate the advisory: severity, the part number and manufacturer it names,
   the date-code window it applies over, and the date it reached the project.
2. Test every declared-list entry on all three axes and keep the reason each
   ruled-out entry was ruled out, including an unknown date code.
3. Derive the action each matched entry earns from the severity and the stage
   together, from record-and-monitor through to stopping a build.
4. Score each match from severity, stage and affected quantity, band the score,
   and order the queue by it.
5. Decide whether the severity reopens the part approval, and report the share
   of the programme's holding the advisory actually reaches.
6. Fan the advisory out to the other programmes holding the same selection,
   excluding the one that raised it.
7. Count acknowledgement working days from receipt against the deadline the
   severity earns, whether or not the advisory has been acknowledged.

## Pitfalls

- Matching on part number alone. A second-source part carrying the same generic
  number is swept in, and hardware that was never at risk is quarantined.
- Ignoring the date-code window. The advisory covers the weeks the fault was
  built in, and applying it to every date code turns a contained problem into a
  programme-wide stop.
- Dropping an entry whose date code is unknown. It is the entry most likely to
  be the affected one, because nobody has looked.
- Driving the action from the stage alone. The stage says what can still be
  done about it; the severity says whether anything should be.
- Reopening the part approval on an advisory that matched nothing. The approval
  stands until the programme actually holds an affected part.
- Treating an unacknowledged advisory as inside its window. The deadline runs
  from receipt, not from the day somebody opens the file.

## Behavior contract (gate 3)

The date-code parsing and window test, the three-axis applicability test, the
severity-and-stage action table, the impact score and its bands, the affected
fraction, the reapproval decision, the dissemination list, the working-day
acknowledgement clock and the assembled triage are exercised by the gate 3
contract test: scripts/test_q60_class_2_alert_handling.py against
scripts/q60_class_2_alert_handling_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q60_class_2_alert_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
