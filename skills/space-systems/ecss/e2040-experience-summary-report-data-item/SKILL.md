---
name: e2040-experience-summary-report-data-item
description: "Audit a device experience summary report against the required contents of ECSS-E-ST-20-40C Annex I when the development effort closes. Use when the closing report has to carry the lessons the project paid for in a form the next one can act on: confirm each lesson states an observation, a cause, a recommendation and an owner, trace every anomaly raised during development to the lesson that captures it, compute the severity-weighted traceability the report achieves, form the occurrence-by-impact-by-detection priority index of each lesson, rank them, and name the anomalies that closed with nothing written down. Trigger: ecss, e-st-20-40-device-scope, e2040-experience-summary-report-data-item, development-anomaly-traceability, lesson-record-completeness, lesson-priority-index, uncaptured-anomaly-detection, experience-summary-drd."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-experience-summary-report-data-item, development-anomaly-traceability, lesson-record-completeness, lesson-priority-index, uncaptured-anomaly-detection, experience-summary-drd]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Experience Summary Report Data Item (space-systems/ecss/e2040-experience-summary-report-data-item)

Use when the task is the required contents of the device experience
summary report of ECSS-E-ST-20-40C Annex I -- the closing record of what
the development effort learned, written so that the next device does
not pay for the same lesson twice.

## Domain quick reference

- A **lesson** is a complete record or it is an anecdote. It needs four
  parts: what was observed, what caused it, what should be done
  differently, and who owns doing it. A lesson with an observation and
  no cause names a symptom; one with a recommendation and no owner
  names an intention.
- The report's coverage is measured against the **anomaly history**,
  not against the length of the lessons section. Every anomaly raised
  during development either produced a lesson or closed with nothing
  written down, and the second case is the one the report exists to
  make visible.
- Traceability is **severity-weighted**. Capturing nine cosmetic
  anomalies and missing the one that cost a redesign is not ninety
  percent traceability of anything a reader cares about.
- A lesson's **priority index** is the product of three whole indices:
  how often the condition occurred, how much it cost when it did, and
  how hard it was to detect before it bit. Detection belongs in the
  product because a cheap fault nobody can see coming outranks an
  expensive one that announces itself.
- Ranking is on the index, and a tie is broken by identifier so two
  runs of the same report produce the same order. An unstable order in
  a closing document is a small defect that destroys a reader's trust
  in the rest of it.

## Workflow

1. Check the report's section list against the required contents and
   name each absent section.
2. Validate the anomaly history: identifier, a severity index inside
   the recognized scale, and the development phase the anomaly was
   raised in. Reject a duplicate identifier rather than letting one
   entry mask another.
3. Validate every lesson: identifier, the three whole indices behind
   its priority, and the four narrative parts, any of which may be
   absent and each of which is then reported as an incompleteness.
4. Resolve each lesson's anomaly links against the history and reject a
   link to an anomaly the history does not carry.
5. Compute the severity-weighted traceability as the captured anomaly
   severity over the total anomaly severity, and list the anomalies no
   lesson captures.
6. Form the occurrence-by-impact-by-detection priority index of each
   lesson and rank the lessons by descending index, breaking ties on
   the identifier.
7. Report the traceability against the required level, the incomplete
   lessons, the uncaptured anomalies and the highest-priority lesson as
   separate findings.

## Pitfalls

- Counting lessons as evidence of learning. The count says how much was
  written; only the trace from the anomaly history says how much was
  captured.
- Weighting every anomaly the same. Severity weighting is what stops a
  long tail of trivial entries from burying the one anomaly that
  changed the design.
- Leaving a recommendation without an owner. It reads as an action and
  behaves as a wish, and it will be closed at the next review as
  already covered.
- Dropping detection difficulty from the priority index. Two
  conditions with the same cost rank identically until you ask which
  one would be seen coming, and the invisible one is the one that
  repeats.
- Ordering the lessons only by index. Equal indices then order
  differently on each run, and a reader comparing two printings of the
  same report finds a difference that means nothing.

## Behavior contract (gate 3)

The section check, anomaly-history and lesson validation, link
resolution, severity-weighted traceability, uncaptured-anomaly
detection, priority-index formation and the stable ranking are
exercised by the gate 3 contract test:
scripts/test_e2040_experience_summary_report_data_item.py against
scripts/e2040_experience_summary_report_data_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_experience_summary_report_data_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
