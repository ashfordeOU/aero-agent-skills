---
name: q7031-paint-material-control
description: "Verify that a paint, primer or hardener batch is under the material control ECSS-Q-ST-70-31C expects before it is mixed: confirm the batch record carries its traceability items, turn manufacture date and declared shelf life into an expiry and the days left at the intended use date, charge logged over-temperature storage against that remaining life, screen the declared total mass loss and condensable figures against the vacuum outgassing limits, and close on one release, retest or reject disposition. Use when a tin is drawn from stores or a batch is reviewed for a coating operation. Trigger: ecss, q-st-70-31c, paint-batch-traceability, paint-shelf-life-remaining, paint-storage-excursion-penalty, paint-outgassing-screening, paint-batch-disposition."
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
  tags: [ecss, q-st-70-31c-paint-application, q-st-70-31c, q7031-paint-material-control, paint-batch-traceability, paint-shelf-life-remaining, paint-storage-excursion-penalty, paint-outgassing-screening, paint-batch-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paints — Paint Material Control (space-systems/ecss/q7031-paint-material-control)

Use when the task is the materials clause of ECSS-Q-ST-70-31C as it applies to
the tin rather than the item: what a paint, primer, thinner or hardener batch
has to carry, how long it stays usable, what storage does to that life, and
what outgassing evidence has to exist before any of it reaches hardware.

## Domain quick reference

- Traceability is a gate, not a paperwork preference. A batch without its batch
  number, manufacture date, certificate of conformity, outgassing data
  reference and storage record cannot be dispositioned at all, because there is
  nothing to disposition against. That is a reject, not an expired-batch
  question.
- Shelf life is declared from manufacture, not from receipt. A batch that sat
  six months at a distributor arrives with six months already spent, so the
  expiry is computed from the manufacture date and compared against the date
  the material will actually be mixed.
- Storage temperature buys or spends shelf life. Time spent above the declared
  storage ceiling advances the cure and thickening reactions, so an excursion
  log converts into a penalty in days against the remaining life rather than
  being filed as a note.
- Outgassing evidence comes from the vacuum outgassing screening of
  ECSS-Q-ST-70-02C, and the two figures that decide it are the total mass loss
  and the collected volatile condensable material. They fail independently: a
  material can lose very little mass overall and still deposit enough
  condensable film to disqualify it near an optic.
- Recovered mass loss is a subset of total mass loss, so a record where it
  exceeds the total is an inconsistent record and is refused rather than
  screened.
- Expiry is not automatically the end. An unopened batch inside a bounded
  retest window can be re-qualified by test; past that window it is spent.

## Workflow

1. Check the batch record against the required traceability items; any item
   absent or blank closes the assessment at reject.
2. Convert manufacture date plus declared shelf life into the expiry date,
   clamping a day-of-month that does not exist in the target month.
3. Compute days remaining at the intended use date, refusing a use date that
   precedes manufacture.
4. Convert each logged storage excursion above the declared ceiling into
   kelvin-hours and charge the resulting penalty against the remaining days.
5. Screen the declared outgassing figures against their limits, reporting each
   metric separately and absorbing representation error at the limit with a
   named tolerance.
6. Close with one disposition: reject on missing traceability, on an outgassing
   failure or past the retest window; retest on recent expiry or a storage
   penalty; release otherwise.

## Pitfalls

- Dating shelf life from goods-in. The life was spent from manufacture, and
  dating it from receipt silently extends every batch by its time in transit
  and distribution.
- Logging a storage excursion and releasing on the nominal expiry anyway. The
  excursion is only worth recording if it moves the usable date, which is why
  it converts into days rather than into a comment.
- Screening on total mass loss alone. The condensable figure is the one that
  decides whether the material may sit near an optical or thermal control
  surface, and it fails independently of the total.
- Treating an expired batch as scrap without asking whether it was opened. An
  unopened batch inside the retest window is a test decision; an opened one, or
  one well past the window, is not.
- Accepting a record whose recovered mass loss exceeds its total mass loss.
  That is an internally inconsistent data sheet, and screening it produces a
  verdict about numbers nobody measured.

## Behavior contract (gate 3)

The traceability check, calendar-clamped expiry, remaining-life computation,
storage-excursion penalty, outgassing screening and the batch disposition are
exercised by the gate 3 contract test:
scripts/test_q7031_paint_material_control.py against
scripts/q7031_paint_material_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7031_paint_material_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
