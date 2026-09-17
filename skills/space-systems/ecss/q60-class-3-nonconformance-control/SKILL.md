---
name: q60-class-3-nonconformance-control
description: "Manage the nonconformance and failure control system a programme runs over its class 3 EEE parts under ECSS-Q-ST-60C clause 6.5.2: split each report between the supplier and the programme from where it surfaced and what function the part sits in, categorize it minor, major or critical, derive the dispositions that category opens and refuse a use-as-is on a critical one, set the failure analysis depth from the mechanism, widen containment to the coarsest identity the receipt records actually support, and count response working days. Use when a class 3 part fails, is found out of specification, or repeats a failure mode across deliveries. Trigger: ecss, q-st-60c-clause-6-5-2, class-3-eee-nonconformance, class-3-report-ownership-split, class-3-containment-scope-widening, class-3-analysis-depth-selection, class-3-assurance-class-upgrade-review."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-3-nonconformance-control, class-3-eee-nonconformance, class-3-report-ownership-split, class-3-containment-scope-widening, class-3-analysis-depth-selection, class-3-assurance-class-upgrade-review]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Nonconformance and Failure Control (space-systems/ecss/q60-class-3-nonconformance-control)

Use when the task is the nonconformance and failure control step of
ECSS-Q-ST-60C clause 6.5.2 for an EEE part procured at the lowest assurance
class. The system is the same system the higher classes run, but it is
operating on parts that were never lot-screened and are frequently identified
only by a date code, so the decisions it has to make are different ones.

## Domain quick reference

- The first decision is not the grade, it is who owns the report. A finding
  raised at or before goods-in, on a part in an uncritical function, with an
  effect short of out-of-specification, can stay inside the supplier's own
  control system with its outcome recorded against the delivery. Anything
  past goods-in is the programme's, whatever it looks like.
- The category is read from three inputs together, never the effect alone:
  what the part did, how late it surfaced, and what the function would lose.
  A cosmetic finding at unit test is major because of where it was found; a
  paperwork finding stays minor however late it arrives.
- Critical is a real category here and it closes a door. A class 3 part
  carrying a critical finding has no use-as-is route: it goes back, it is
  scrapped, or it is replaced by a part bought at a higher assurance class.
  Accepting it as it stands is the disposition a schedule reaches for and the
  one this clause removes.
- A major use-as-is survives only with an application-level justification
  alongside the board signature. The justification is about the circuit the
  part sits in, not about the part.
- Analysis depth is a decision, not a default. A one-off handling mark owes
  nothing; a lot-related or major finding owes construction analysis; a
  design-related mechanism, a critical report or a mode that has already
  repeated owes a full root cause.
- Containment follows the records, not the shelf. The scope is the finest
  identity the receipt records actually support, which at this class is often
  the date code and sometimes only the part number. An unknown mechanism is
  contained one step wider than a known lot-related one, because nothing
  screened the neighbouring units either.
- Two occurrences of one mode inside the rolling window are already
  systematic at this class. What that escalates is not the unit: it is the
  question of whether the part should have been bought at this class at all.
- The response clock runs in working days from raising and runs shortest for
  a critical report. A report with no recorded response is still accruing.

## Workflow

1. Validate the report: the unit and part number it names, a known effect,
   detection point, function criticality, mechanism and identity depth, a
   positive quantity and a raising date.
2. Decide ownership, then categorize the report from effect, detection point
   and function criticality together.
3. Derive the dispositions the category opens, and for a proposed one the
   records it earns; list any record not yet held.
4. Count occurrences of the same mode on the same part number inside the
   rolling window and set the recurrence verdict.
5. Set the analysis depth from mechanism, category and that verdict, and check
   an analysis is referenced whenever one is owed.
6. Derive the containment scope from identity depth and mechanism, then build
   the held unit set from the programme inventory on that scope's axis.
7. Count response working days from raising to response, or to the assessment
   date while the report is open, and compare with the category deadline.
8. Report ownership, category, dispositions, analysis depth, containment,
   recurrence, escalation and every finding. The report closes only when
   nothing is outstanding and a response date exists.

## Pitfalls

- Treating a class 3 report as a stores problem because the part was cheap.
  Ownership is decided from where it surfaced and what it sits in, and a part
  past goods-in is the programme's report whatever it cost.
- Grading on the effect alone. A cosmetic finding on a part already in a unit
  under test is major, and reading it as minor lets it close without the parts
  control board ever seeing it.
- Signing a use-as-is on a critical finding. There is no such route at this
  class, and a disposition outside the category is a finding, not a choice.
- Accepting a major use-as-is on the part's own data. The justification this
  disposition earns is an application one, about the circuit the part sits in.
- Containing by shelf or by batch paperwork that does not exist. Where the
  records reach only the date code, the date code is the containment scope,
  and where they reach only the part number, all stock of it is suspect.
- Dispositioning an unknown mechanism at the same width as a known one. The
  unknown case is the wider one, because nothing rules the neighbours out.
- Reading each report as an isolated event. At this class two occurrences of
  one normalised mode inside the window already put the assurance class the
  part was bought at, not the unit, on the table.
- Counting calendar days against a working-day limit, and stopping the count
  while a report is merely under investigation.

## Behavior contract (gate 3)

The report validation, ownership split, categorization, disposition and record
derivation, analysis depth selection, containment scope widening, containment
set construction, rolling-window recurrence counting and response working-day
comparison are exercised by the gate 3 contract test:
scripts/test_q60_class_3_nonconformance_control.py against
scripts/q60_class_3_nonconformance_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_nonconformance_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
