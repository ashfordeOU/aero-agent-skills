---
name: q6003-device-assurance-report-drd
description: "Evaluate whether a recurring product assurance report for a device development carries the content its DRD demands and can be accepted for the period it covers. Use when an issue of the report has to become an accept or rework verdict under ECSS-Q-ST-60-03C Annex B: refuse a blank section body, judge whether this reporting period abuts the previous one rather than leaving development days unreported or reporting them twice, reconcile every planned assurance activity against a status drawn from the known set, age each open nonconformance and action against the declared response time, and return the disposition with every finding named. Trigger: ecss, q-st-60-03c-annex-b, device-assurance-report-drd, device-report-period-continuity, device-assurance-activity-reconciliation, device-nonconformance-response-ageing, device-assurance-report-section-coverage."
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
  tags: [ecss, q-st-60-03-device-development-assurance-scope, q6003-device-assurance-report-drd, device-report-period-continuity, device-assurance-activity-reconciliation, device-nonconformance-response-ageing, device-assurance-report-section-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Development -- Recurring Product Assurance Report DRD (space-systems/ecss/q6003-device-assurance-report-drd)

Use when the task is the Annex B document requirements definition of
ECSS-Q-ST-60-03C: the product assurance report is issued repeatedly
through a device development, and the question is whether this issue
carries the content the DRD asks for and whether the period it covers
joins cleanly to the one before it.

## Domain quick reference

- A recurring report is a different object from a one-off plan. Its
  content blocks matter, but so does the period it covers, because the
  sequence of issues is what makes the development auditable after the
  fact. A perfect report of the wrong month leaves a month uncovered.
- The nine content blocks are the introduction, the reporting period,
  the activity status, the nonconformance status, the waiver and
  deviation status, the part and material status, the schedule and
  milestone status, the open actions, and the conclusions. A present
  heading with an empty body is absent.
- Consecutive periods abut: this period starts the day after the
  previous one ended. A later start leaves development days no report
  covers; an earlier start reports the same days twice, and the two
  issues can then disagree about them. Both are findings, and they are
  counted in days rather than flagged, because the size is what decides
  whether the gap is re-issued or noted.
- A period that ends before it starts, or a predecessor that ends after
  this period does, are input defects. They mean the dates were taken
  from two different sources, so the check refuses them instead of
  reporting a negative length.
- The report is reconciled against the plan it reports on, in both
  directions. A planned activity with no status is an omission and not
  an implicit pass; an activity reported that no plan contains means the
  report and the plan are on different baselines.
- A status outside the known set -- not started, in progress, completed,
  blocked, descoped -- is refused rather than counted as open, because
  an invented status is how an activity avoids both lists. Descoped is
  neither open nor complete: it left the programme.
- Open nonconformances and open actions are aged from the day they were
  raised to the day the period closes, against the response time the
  plan declared. An item exactly on the response time is inside it; the
  day after is one day overdue. Closed items are never aged.

## Workflow

1. Read the report as section key to body text and run
   missing_report_sections, treating a blank body as an absent key.
2. Run period_continuity on this issue's start and end together with the
   previous issue's closing day, and read gap_days and overlap_days
   rather than a bare boolean.
3. Run activity_reconciliation against the plan's activity list, and
   take the unreported and unplanned lists as separate defects.
4. Age the open nonconformances and the open actions separately with
   overdue_items against the declared response time; keeping the two
   lists apart preserves which register is behind.
5. Combine everything with assess_device_assurance_report_drd; the issue
   is accepted only when the flat findings list is empty.

## Pitfalls

- Judging the report on its sections alone. A structurally perfect issue
  that skips four development days still breaks the audit trail the
  recurring report exists to keep.
- Reading a missing activity status as a pass. An activity that nobody
  reported is an activity nobody can show was done.
- Silently tolerating an invented status word. It excludes the activity
  from the open list and the complete list at once, which is worse than
  either.
- Aging an item that has already been closed. It inflates the overdue
  register and hides the items that are genuinely late.
- Treating an item that lands exactly on the declared response time as
  overdue. The response time is inclusive, and moving that boundary
  changes the register on every report.
- Accepting dates that come from two sources without checking them. A
  predecessor that ends after this period is a bookkeeping defect, not a
  large overlap to be reported.

## Behavior contract (gate 3)

The section coverage, period continuity, activity reconciliation,
open-item ageing and the aggregate report disposition are exercised by
the gate 3 contract test:
scripts/test_q6003_device_assurance_report_drd.py against
scripts/q6003_device_assurance_report_drd_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6003_device_assurance_report_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
