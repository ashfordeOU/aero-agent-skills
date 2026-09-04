# Wave-32 leaf spec: ndt-personnel-qualification (manufacturing-quality, ndt pack)

- Path: skills/manufacturing-quality/ndt/ndt-personnel-qualification/
- Pack: ndt. Siblings: ndt-method-selection (method decision table),
  ultrasonic-inspection, eddy-current-inspection, radiographic-
  inspection, magnetic-particle-inspection, liquid-penetrant-
  inspection, etc. (method execution leaves).
- Standards id: nas-410 (reference-only; gated - never hardcode the
  proprietary training-hour or experience tables; every threshold is a
  function argument with paraphrase-safe documented defaults). Ledger
  Standard: nas-410.
- Family: manufacturing-quality

## Claim

Track the qualification and certification status of nondestructive
testing (NDT) personnel: compute the recertification due date from the
certification date and the recertification interval, compute the vision
examination due date from the last near-vision examination and the
vision interval, judge an individual's certification currency from the
recertification and vision due dates against the current date, evaluate
upgrade eligibility from the current level, the held training hours,
the held experience months, the required hours and months for the
target level and the passed examination, and validate the supervision
rule that a Level I operator must work under a Level II or III
supervisor. Produces the recertification due date, the vision due date,
the currency verdict, the upgrade-eligibility verdict and the
supervision verdict that gate an NDT personnel qualification record.

Does NOT do: selecting the NDT method for an application
(ndt-method-selection owns the method decision table - do not extend
it); the physics or procedure of a specific technique
(ultrasonic-inspection etc. own method execution); process
requalification triggered by personnel change
(special-processes/special-process-qualification owns process
requalification); reproducing NAS 410 training-hour or experience
tables (gated; thresholds are arguments).  This leaf computes the
certification-governance mechanics only.

## Model (implement exactly)

Constants (paraphrase-safe documented defaults; each is overridable by
argument because the underlying standard tables are gated):
- RECERT_INTERVAL_MONTHS_DEFAULT = 36 (months; documented norm for
  NAS-410-style recertification).
- VISION_INTERVAL_MONTHS_DEFAULT = 12 (months; documented annual
  near-vision norm).
- LEVELS = ("i", "ii", "iii").

Functions (pure stdlib datetime/arithmetic, no randomness):

- recert_due_date(cert_date_iso, interval_months =
  RECERT_INTERVAL_MONTHS_DEFAULT) -> ISO due date: cert date plus the
  interval in calendar months with day clamped to month end.
  ValueError on malformed date or interval <= 0.
- vision_due_date(last_vision_iso, interval_months =
  VISION_INTERVAL_MONTHS_DEFAULT) -> ISO due date, same month-add and
  clamp rule.
- certification_status(cert_date_iso, recert_due_iso, vision_due_iso,
  today_iso) -> one of "current", "recert-due" (today > recert_due),
  "vision-due" (today > vision_due), "recert-and-vision-due" (both).
  Order of checks: expired on recert first, then vision; combine when
  both overdue.  ValueError on malformed dates.  (cert_date is
  informational context for the record; the verdict is driven by the
  due dates vs today.)
- upgrade_eligible(current_level, target_level, held_hours,
  required_hours, held_months, required_months, exam_passed) -> bool:
  True when current_level is the level immediately below target_level
  in LEVELS AND held_hours >= required_hours AND held_months >=
  required_months AND exam_passed.  ValueError on levels not in
  LEVELS, target_level == current_level (use the level above), a gap
  larger than one level (must be the immediate next level), negative
  hours/months.
- supervision_valid(operator_level, supervisor_level) -> bool: True
  when operator_level == "i" and supervisor_level in ("ii", "iii"),
  OR operator_level in ("ii", "iii") (Level II/III operators may work
  independently).  ValueError on unknown levels.
- qualification_review(cert_date_iso, last_vision_iso, today_iso,
  operator_level, supervisor_level, recert_interval_months =
  RECERT_INTERVAL_MONTHS_DEFAULT, vision_interval_months =
  VISION_INTERVAL_MONTHS_DEFAULT, upgrade_inputs=None) -> dict
  {certification_status, recert_due_date_iso, vision_due_date_iso,
  supervision_ok, upgrade_eligible (None when upgrade_inputs is
  None)}.  upgrade_inputs: dict with keys {target_level, held_hours,
  required_hours, held_months, required_months, exam_passed}.  All
  ValueErrors propagate.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

UT Level II operator certified 2023-06-15, last near-vision exam
2026-02-01, today 2026-09-04, working under a Level III supervisor.
Recert interval 36 months, vision interval 12 months.  Upgrade inputs
toward Level III: held 600 training hours, required 700, held 20
months experience, required 24, exam not yet passed (exam_passed
False).

Run your module and take the real outputs as assert targets, then check
the magnitude bounds:
- recert_due_date "2026-06-15" (36 months from 2023-06-15) - so the
  operator is recertification-overdue by 2026-09-04.
- vision_due_date "2027-02-01" (12 months from 2026-02-01) - not yet
  due.
- certification_status "recert-due" (today 2026-09-04 > recert_due
  2026-06-15; vision not yet due).
- supervision_valid("ii", "iii") True (Level II may work
  independently; the Level III supervisor is also valid for a Level I
  operator).
- upgrade_eligible("ii", "iii", 600, 700, 20, 24, False) False (hours,
  months and exam all short).
- upgrade_eligible("ii", "iii", 720, 700, 26, 24, True) True.
- A Level I operator with a Level II supervisor: supervision_valid
  ("i", "ii") True; with a Level I supervisor: False.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: malformed date; interval <= 0; negative hours or months;
  level not in LEVELS; upgrade target == current level; upgrade target
  more than one level above current.
- Due-date clamping: 2026-01-31 + 1 month -> 2026-02-28; 2024-01-31 ->
  2024-02-29 (leap year); 2023-06-15 + 36 months -> 2026-06-15.
- certification_status truth table: current within window;
  recert-due after recert date; vision-due after vision date only;
  recert-and-vision-due after both.
- upgrade_eligible requires ALL of hours, months and exam; the
  immediate-level rule (i->ii allowed, i->iii raises ValueError).
- supervision_valid truth table for all level pairs.
- Determinism: no RNG, run-to-run identical.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-ndt-personnel-qualification.yaml)

Query 1 (copy verbatim):
  "compute the recertification due date and vision examination due date and judge the certification currency of an NDT inspector against the current date"
  intent: "manufacturing-quality; NDT personnel certification currency and due dates"
  expected_skill: "manufacturing-quality/ndt/ndt-personnel-qualification"
Query 2 (copy verbatim):
  "evaluate the level upgrade eligibility and the supervision rule for an NDT technician from the held training hours experience months and passed examination"
  intent: "manufacturing-quality; NDT personnel level progression and supervision"
  expected_skill: "manufacturing-quality/ndt/ndt-personnel-qualification"
Task ids: w32-ndt-personnel-qualification-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must track the qualification and
certification status of nondestructive testing personnel:" and include
the outputs in the Claim. First tag: ndt-personnel-qualification.
Additional tags ONLY: nas-410, certification-currency,
recertification-due, vision-examination, level-progression,
ndt-certification. NEVER single generic words (ndt, personnel,
qualification, certification, inspection, level). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): method selection, technique
selection, decision table (ndt-method-selection); ultrasonic,
eddy-current, radiographic, penetrant, magnetic-particle physics and
procedure tokens (the method execution leaves); process
requalification (special-process-qualification). The word "level" is
allowed only as certification level (Level I/II/III) - never as a
generic token.

Tags: [ndt-personnel-qualification, nas-410,
certification-currency, recertification-due, vision-examination,
level-progression, ndt-certification]

Sibling-citation lines for Related leaves:
manufacturing-quality/ndt/ndt-method-selection,
manufacturing-quality/ndt/ultrasonic-inspection (and other method
leaves cite nas-410 in frontmatter; this leaf owns the personnel
certification layer), manufacturing-quality/special-processes/
special-process-qualification (process requalification on personnel
change), manufacturing-quality/as9100/document-control (certification
records).

Ledger Standard: nas-410.
