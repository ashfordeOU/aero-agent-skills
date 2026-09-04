---
name: ndt-personnel-qualification
description: "Use when you must track the qualification and certification status of nondestructive testing personnel: compute recertification due date from certification date and interval, compute the near-vision examination due date from the last vision exam, judge certification currency versus the current date, evaluate upgrade eligibility from held training hours, experience months and passed examination versus required thresholds, and validate that a Level I operator works under a Level II or III supervisor. Produces recertification due date, vision due date, currency, upgrade and supervision verdicts. Trigger: ndt personnel qualification, NAS 410, certification currency, recertification due date, vision examination, upgrade eligibility."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: nas-410
    reference-only: true
gated: false
domain: manufacturing-quality
pack: ndt
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [ndt-personnel-qualification, nas-410, certification-currency, recertification-due, vision-examination, level-progression, ndt-certification]
  version: 0.1.0
  author: AeroSkills
---

# NDT Personnel Qualification (manufacturing-quality/ndt/ndt-personnel-qualification)

Use when you must track the qualification and certification status of
nondestructive testing personnel: due dates, currency verdicts, upgrade
eligibility and supervision compliance that gate an NDT personnel
qualification record. This leaf computes the certification-governance
mechanics only, in pure Python stdlib, deterministic, no RNG. NAS 410 is
referenced, never reproduced: its training-hour and experience tables are
gated, so every threshold is a function argument backed by
paraphrase-safe documented defaults. It pairs with
manufacturing-quality/ndt/ndt-method-selection for method choice and with
the method execution leaves, which carry the physics and procedure of
each technique.

## Domain quick reference

- Recertification due date: certification date plus the recertification
  interval in calendar months, day clamped to the target month end.
  Documented default RECERT_INTERVAL_MONTHS_DEFAULT = 36 months, the
  norm for NAS-410-style recertification; overridable by argument.
- Vision examination due date: last near-vision examination date plus
  the vision interval, same month-add and clamp rule. Documented default
  VISION_INTERVAL_MONTHS_DEFAULT = 12 months, the annual near-vision
  norm; overridable by argument.
- Certification currency: one of current, recert-due (today after the
  recertification due date), vision-due (today after the vision due
  date), recert-and-vision-due (both). Overdue means strictly after the
  due date; due on the date itself is still current. Recertification
  expiry is checked before vision expiry.
- Level progression: i, ii, iii. An upgrade is eligible only to the
  level immediately above the current level, and only when held training
  hours meet the required hours, held experience months meet the
  required months, and the examination is passed. Hours and months
  thresholds come from arguments, never from embedded tables.
- Supervision rule: a Level I operator must work under a Level II or III
  supervisor; a Level II or III operator may work independently.

## Workflow

1. Read the personnel record: certification date, last near-vision
   examination date, current date, operator and supervisor levels.
2. Compute recert_due_date(cert_date_iso) and
   vision_due_date(last_vision_iso) with the default intervals, or pass
   interval arguments when the employer applies different periods.
3. Judge currency with certification_status(cert_date_iso,
   recert_due_iso, vision_due_iso, today_iso) and confirm the verdict
   matches the due dates versus today.
4. Check the pairing with supervision_valid(operator_level,
   supervisor_level); a Level I under a Level I supervisor fails.
5. When an upgrade is under evaluation, call
   upgrade_eligible(current_level, target_level, held_hours,
   required_hours, held_months, required_months, exam_passed) with the
   thresholds supplied by the qualified procedure, never from memory of
   a standard table.
6. For a one-call record verdict use qualification_review(...), which
   returns certification_status, recert_due_date_iso, vision_due_date_iso,
   supervision_ok and upgrade_eligible (None when no upgrade_inputs are
   given).
7. Confirm the deterministic checks with the contract test
   scripts/test_ndt_personnel_qualification.py.

## Worked example

UT Level II operator certified 2023-06-15, last near-vision examination
2026-02-01, today 2026-09-04, working under a Level III supervisor, with
an upgrade toward Level III under evaluation. Real module outputs:

- recert_due_date("2023-06-15") -> "2026-06-15" (36 calendar months,
  mid-month day preserved), so the operator is recertification-overdue
  by 2026-09-04.
- vision_due_date("2026-02-01") -> "2027-02-01" (12 months), not yet
  due.
- certification_status("2023-06-15", "2026-06-15", "2027-02-01",
  "2026-09-04") -> "recert-due".
- supervision_valid("ii", "iii") -> True (a Level II operator may work
  independently; the Level III supervisor is also valid for a Level I
  operator); supervision_valid("i", "i") -> False.
- upgrade_eligible("ii", "iii", 600, 700, 20, 24, False) -> False
  (hours, months and examination all short); upgrade_eligible("ii",
  "iii", 720, 700, 26, 24, True) -> True.
- qualification_review("2023-06-15", "2026-02-01", "2026-09-04", "ii",
  "iii", upgrade_inputs={"target_level": "iii", "held_hours": 600,
  "required_hours": 700, "held_months": 20, "required_months": 24,
  "exam_passed": False}) -> {"certification_status": "recert-due",
  "recert_due_date_iso": "2026-06-15", "vision_due_date_iso":
  "2027-02-01", "supervision_ok": True, "upgrade_eligible": False}.
- Clamp checks: 2026-01-31 plus 1 month -> 2026-02-28; 2024-01-31 plus
  1 month -> 2024-02-29 (leap year).

## Verification

- Confirm recert_due_date("2023-06-15") returns "2026-06-15" and that
  2026-01-31 plus one month clamps to "2026-02-28", with 2024-01-31
  clamping to "2024-02-29".
- Confirm certification_status is current when today precedes both due
  dates, recert-due after the recertification date only, vision-due
  after the vision date only, and recert-and-vision-due after both.
- Confirm upgrade_eligible requires every one of hours, months and the
  examination, and that the immediate-level rule holds: i to ii is
  allowed, i to iii raises ValueError.
- Confirm the supervision truth table: (i, ii) and (i, iii) valid,
  (i, i) invalid, Level II and III operators valid with any supervisor
  level.
- Confirm every malformed date, interval <= 0, negative hours or months,
  and level outside i/ii/iii raises ValueError.
- Run the contract test offline: python3
  scripts/test_ndt_personnel_qualification.py (35 tests, deterministic,
  exits 0).

## Related leaves

- manufacturing-quality/ndt/ndt-method-selection: chooses the NDT method
  for an application; this leaf owns the personnel certification layer
  over that choice.
- manufacturing-quality/ndt/ultrasonic-inspection and the other method
  execution leaves in the ndt pack (eddy-current-inspection,
  radiographic-inspection, magnetic-particle-inspection,
  liquid-penetrant-inspection, and siblings) cite nas-410 in their
  frontmatter and own the physics and procedure of each method.
- manufacturing-quality/special-processes/special-process-qualification:
  owns requalification of a process when personnel change.
- manufacturing-quality/as9100/document-control: houses the
  certification records this leaf's verdicts update.

## Pitfalls

- Flagging an operator on the due date itself: currency is judged
  strictly after the due date (due on the date is still current), so
  a recertification dated today does not make the record
  recert-due.
- Reporting a single overdue reason without checking both clocks:
  expiry of the recertification is checked before vision expiry, and
  an operator past both due dates is recert-and-vision-due, not
  recert-due.
- Reconstructing NAS-410 thresholds from memory: the standard's
  training-hour and experience tables are gated and never embedded,
  so hours/months requirements must come from the calling procedure's
  arguments (backed by the paraphrase-safe documented defaults), never
  from a remembered table.
- Evaluating a skipped-level upgrade: eligibility runs only to the
  level immediately above the current one, so i to iii raises
  ValueError rather than scoring.
- Passing an upgrade on partial evidence: eligibility requires the
  held training hours, the held experience months and the passed
  examination together — the worked example fails on hours, months
  and exam all short at once.
- Certifying a Level I to work alone or under another Level I: a
  Level I operator must work under a Level II or III supervisor,
  while Level II and III operators are valid with any supervisor
  level — supervision_valid(\"i\", \"i\") is False.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ndt_personnel_qualification.py

The test covers the worked-example outputs (recertification due
2026-06-15, vision due 2027-02-01, verdict recert-due), calendar-month
day clamping including leap February, the certification-status truth
table, upgrade eligibility requiring all of hours, months and the
examination plus the immediate-level rule, the supervision truth table,
the qualification_review dict contract, determinism across runs, and
ValueError rejection of malformed dates, non-positive intervals,
negative hours or months and unknown levels.

## Compliance

- Standards referenced, not reproduced: NAS 410 governs NDT personnel
  qualification; its training-hour and experience tables are gated and
  never embedded here. Every threshold is a function argument with the
  paraphrase-safe documented defaults (36-month recertification norm,
  12-month annual near-vision norm).
- compliance: STANDARDS-REF, gated: false.
