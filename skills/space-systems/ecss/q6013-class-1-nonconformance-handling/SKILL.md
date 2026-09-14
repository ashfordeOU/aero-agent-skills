---
name: q6013-class-1-nonconformance-handling
description: "Evaluate and disposition a nonconformance raised against a highest-assurance (class 1) commercial EEE part lot under ECSS-Q-ST-60-13C clause 4.5.2: categorize the finding major or minor from its effect on safety, interchangeability and specified limits, time the written report against the deadline that category earns, derive the authorities that must concur, refuse a use-as-is or repair disposition while the root cause is open or the mechanism is lot-related, and size containment across the whole receiving lot. Use when a class 1 commercial part fails incoming inspection, lot acceptance, board test or system test and the report, disposition and lot containment must be defended. Trigger: ecss, q-st-60-13c, commercial-eee-nonconformance, class-1-commercial-part, nonconformance-disposition, use-as-is-concurrence, lot-related-containment, nonconformance-reporting-deadline."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-nonconformance-handling, class-1-commercial-eee-part, commercial-eee-nonconformance-disposition, use-as-is-concurrence, lot-related-failure-containment, nonconformance-reporting-deadline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Nonconformance Handling (space-systems/ecss/q6013-class-1-nonconformance-handling)

Use when the task is the nonconformance step of ECSS-Q-ST-60-13C clause
4.5.2 for a commercial EEE part procured to the highest assurance class —
turning a failure found on a class 1 lot into a reported, categorized,
concurred and contained disposition rather than a note in a test log.

## Domain quick reference

- A commercial part bought to the highest assurance class carries the
  same nonconformance obligations as a space-grade part: the value of
  the class is the reporting and disposition trail, not the part price.
  A finding that is closed informally has spent the class and kept none
  of it.
- The category of the finding, not its symptom, sets the clock. A
  finding that touches safety, interchangeability, a specified limit or
  mission reliability is major and is reported within a day; everything
  else is minor and is reported within the working week. The clock runs
  from detection, not from the review meeting that discussed it.
- A lot-related mechanism behaves differently from an isolated one. An
  isolated defect concerns the parts that failed; a mechanism shared by
  the whole date-code lot concerns every part of that lot, including
  every part that was never inspected. Those uninspected parts are the
  population the containment exists for.
- Detection stage matters twice. It grades a lot-related mechanism up to
  major once the finding has escaped the part-level screens and surfaced
  at board or system test, and it decides whether a part can be sent
  back to its supplier at all — a part still soldered into an assembly
  cannot be returned until it is removed.
- Two dispositions leave a non-conforming part in the build: use-as-is
  and repair. Both reach the customer and the design authority, whatever
  the category, because both change what the delivered hardware is
  against its drawing. Use-as-is additionally needs an understood
  mechanism — an open root cause is an unbounded risk, not a small one.

## Workflow

1. Validate the record: a non-empty lot identity, a known detection
   stage, a known proposed disposition, inspected and failed quantities
   that fit inside the lot size, and a report time at or after the
   detection time. A report filed before the detection it reports is an
   input error, not a fast response.
2. Categorize the finding. Collect every effect that makes it major and
   keep the reasons, so the category can be defended later; a
   lot-related mechanism that surfaced at or beyond board-assembly test
   is graded up on escape alone.
3. Derive the reporting deadline from the category and compare the
   elapsed hours with it under a named tolerance, so a report filed
   exactly on the deadline is on time and a representation error never
   creates a late finding.
4. Derive the concurrence set from the category and the disposition:
   the review board always, the customer for a major finding or for any
   disposition that leaves a non-conforming part installed, the design
   authority for use-as-is and repair, procurement for a return.
5. Decide whether the proposed disposition is permitted. Refuse
   use-as-is on an open root cause, on a lot-related mechanism and on a
   safety effect; refuse repair and rework without a qualified
   procedure; refuse a return of a part still installed. Scrap always
   closes the finding.
6. Size the containment. For a lot-related mechanism report the whole
   receiving lot and call out the uninspected remainder explicitly; for
   an isolated mechanism report the failed parts only. Report the
   observed failure fraction over the inspected sample, not over the lot.
7. Report the category and its reasons, the reporting assessment, the
   concurrence set, the permitted-or-refused disposition, the
   containment scope and every finding that blocks closure.

## Pitfalls

- Starting the reporting clock at the review meeting. The deadline runs
  from detection; a finding that sat in a test log for three days is
  already late when the board first sees it.
- Dispositioning use-as-is to avoid re-work while the root cause is
  still open. An unknown mechanism cannot be bounded to the parts that
  failed, so the disposition is not supportable however small the
  measured deviation looks.
- Containing only the parts that failed when the mechanism is shared by
  the lot. The uninspected remainder of the lot is exactly the
  population at risk, and reporting it as zero because nothing was
  measured there converts an unknown into a false pass.
- Reading the observed failure fraction as a lot failure rate. It is a
  sample statistic over the inspected quantity; treating it as the lot
  rate understates a lot-related mechanism and overstates an isolated one.
- Letting a minor category carry a use-as-is disposition to the review
  board alone. The category sets the reporting clock; the disposition
  sets who has to agree, and a part left non-conforming in the build
  reaches the customer whatever its category.
- Returning a part to its supplier while it is still installed. The
  return is only a disposition once the part is physically removed and
  the assembly has its own repair route.

## Behavior contract (gate 3)

The record validation, severity categorization, reporting-clock
assessment, concurrence derivation, disposition permission rules and
containment sizing are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_nonconformance_handling.py against
scripts/q6013_class_1_nonconformance_handling_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_nonconformance_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
