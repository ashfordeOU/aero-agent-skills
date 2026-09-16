---
name: q60-class-1-nonconformance-control
description: "Use when a class 1 part fails, is found out of specification, or repeats a failure mode across lots. Manage the nonconformance and failure control system a programme runs over its highest-assurance (class 1) EEE parts, under ECSS-Q-ST-60C clause 4.5.2: grade each report from its effect, its reach into built hardware and its safety consequence, derive the dispositions that grade allows and the signatures each disposition earns, decide when a failure analysis is owed rather than optional, impound every sibling lot sharing the failing wafer lot or date code, and detect a failure mode that has recurred often enough to be systematic. Trigger: ecss, q-st-60c, class-1-eee-nonconformance, failure-review-board-disposition, sibling-lot-impound, systematic-failure-mode-recurrence, nonconformance-closure-working-days, failure-analysis-trigger."
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
  tags: [ecss, q-st-60c-eee-components-scope, q60-class-1-nonconformance-control, class-1-eee-part, eee-nonconformance-grading, failure-review-board-disposition, sibling-lot-impound, systematic-failure-mode-recurrence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Nonconformance and Failure Control (space-systems/ecss/q60-class-1-nonconformance-control)

Use when the task is the nonconformance and failure control step of
ECSS-Q-ST-60C clause 4.5.2 for an EEE part procured to the highest
assurance class — turning one report on one lot into a graded,
dispositioned, contained and time-bounded programme-level record.

## Domain quick reference

- A class 1 part carries the programme's reliability case. A report
  against one is therefore never a stores problem; it is an input to the
  reliability argument, and the control system exists so that the same
  evidence reaches the board, the customer and the next project.
- The grade drives everything downstream, so it is decided first and from
  three inputs, not one: what the part did, how far the affected parts
  had already travelled, and whether safety is in the loop. An effect at
  or past out-of-specification is major on its own; so is any effect at
  all once the parts are inside assembled or delivered hardware, because
  the escape is the severity.
- Dispositions are not a free menu. A minor report can be repaired only
  by rework; a major one opens the repair route but pays for it with the
  board's signature, and accepting a major report as it stands is the
  only disposition that also owes the customer a signature.
- A failure analysis is owed whenever the mechanism is unknown and
  matters: always for a functional failure, and for any major report that
  is not purely a paperwork finding. Dispositioning before the mechanism
  is known is how a lot escape becomes a fleet problem.
- Containment follows origin, not location. Sibling lots sharing the
  failing wafer lot or date code are suspect by construction and are
  impounded with the failing lot, even when they sit in another store or
  another project.
- One report is an event; the same failure mode on the same part number
  three times inside a rolling year is a systematic problem that has
  outgrown project-level handling and belongs to the corrective action
  board.
- The closure clock runs in working days from raising, and it runs
  shorter for a major report. A report with no recorded closure is still
  accruing against that clock.

## Workflow

1. Validate the report: the lot and part number it names, a known effect
   and reach, a positive quantity and a raising date.
2. Grade it from effect, reach and safety relevance.
3. Derive the allowed dispositions for that grade and, if one is
   proposed, the signatures it earns; list any signature not yet present.
4. Decide whether a failure analysis is owed and whether one is
   referenced.
5. Build the containment set from the programme inventory by matching
   part number plus wafer lot or date code.
6. Count occurrences of the same failure mode on the same part number
   inside the rolling window and decide whether the mode is systematic.
7. Count closure working days from raising to closure, or to the
   assessment date while the report is open, and compare with the
   deadline the grade sets.
8. Report the grade, the containment set, the recurrence verdict, the
   escalation level and every finding. The report closes only when
   nothing is outstanding and a closure date exists.

## Pitfalls

- Grading on the effect alone. A cosmetic finding on parts already
  soldered into flight hardware is a major report, and treating it as
  minor lets it close without the board ever seeing it.
- Letting the project sign an acceptance of a major report. That is the
  one disposition the customer has to countersign, and it is exactly the
  one a schedule-pressed project reaches for.
- Dispositioning a functional failure before the mechanism is known. The
  analysis is what tells you whether the neighbouring lots are suspect;
  skipping it makes the containment set look empty.
- Containing by location. Impounding the shelf the failing lot sat on
  misses the sibling lot kitted into another model last month, which
  shares the wafer lot and therefore the defect.
- Reading each report as an isolated event. Recurrence is only visible
  when the failure mode and part number are normalised and counted over
  a rolling window; a lower-case variant of the same mode text hides it.
- Counting calendar days against a working-day closure limit, and
  stopping the count when a report is merely under investigation. An
  open report keeps accruing.

## Behavior contract (gate 3)

The report validation, grading, disposition and signature derivation,
failure-analysis decision, sibling-lot containment, recurrence window
counting and closure working-day comparison are exercised by the gate 3
contract test:
scripts/test_q60_class_1_nonconformance_control.py against
scripts/q60_class_1_nonconformance_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_nonconformance_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
