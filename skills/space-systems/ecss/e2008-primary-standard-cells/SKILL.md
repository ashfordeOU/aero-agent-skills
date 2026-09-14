---
name: e2008-primary-standard-cells
description: "Verify that the calibrated reference cells setting a simulator's illumination level satisfy ECSS-E-ST-20-08C clause 10.2.1: confirm each primary standard cites a recognised traceable calibration route and a certificate still valid on the test day, match the single-junction or component standard to the junction it sets, cover every junction of a multijunction article, carry the certificate current across to the temperature the standard is actually at, and hold the residual level error inside tolerance with its sign. Use when a simulator level is being set from primary standards, or an as-run setting has to be defended. Trigger: ecss, e-st-20-08c-clause-10-2-1, primary-standard-reference-cell, component-cell-junction-coverage, reference-cell-calibration-validity, simulator-illumination-level-setting, reference-cell-temperature-correction."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-primary-standard-cells, primary-standard-reference-cell, component-cell-junction-coverage, reference-cell-calibration-validity, simulator-illumination-level-setting, reference-cell-temperature-correction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Primary Standard Cells (space-systems/ecss/e2008-primary-standard-cells)

Use when the task is clause 10.2.1 of ECSS-E-ST-20-08C -- the calibrated
single junction or component reference cells a simulator's illumination
level is set against, and whether a level set from them can be defended.

## Domain quick reference

- A primary standard is a calibration, not a cell. What makes it primary
  is the route the certificate names -- a space-flown, high-altitude
  aircraft, balloon or world-radiometric-reference calibration -- so a
  reference cell citing a vendor datasheet, or carrying no certificate
  reference at all, has a number written on it and nothing behind it.
- The certificate has a life. A standard in date on the day of the test
  is what matters, not one that was in date when the campaign was
  planned, so the validity is judged against the test date and a
  certificate close to lapsing is said aloud while it still passes.
- The junction has to match. A multijunction article is current limited
  by whichever junction sees least of its own part of the spectrum, so a
  single-junction standard sets one lamp channel and leaves the others
  where they happened to be. Every required junction gets a standard
  representing it, and a junction with none is named.
- Temperature moves the target, not the reading. The certificate fixes
  the short-circuit current at a reference temperature, so the value the
  standard should read while it sits warmer or colder is the certificate
  value carried across by its own coefficient. Set the lamp to the bare
  certificate value at the wrong temperature and the whole coefficient
  times the offset lands in the illumination level.
- The residual error is a deliverable, not a leftover. Every performance
  measurement taken afterwards inherits it, and it carries a sign: a
  level set two per cent high and one set two per cent low bias every
  later result in opposite directions.
- A standard offered for a junction nobody asked about is reported as
  unused rather than silently counted, because it usually means the
  article's junction list and the standards drawer disagree.

## Workflow

1. Validate the standard cell policy first: the level error tolerance,
   the certificate validity in days, the window inside which a validity
   counts as marginal and the residual error band. A marginal window
   wider than the validity itself, or a marginal band wider than the
   tolerance, is refused rather than used.
2. Read every offered standard: non-blank identifier, no duplicate
   identifier, a named junction, a certificate reference, a calibration
   route, an ISO calibration date, a positive calibrated current and a
   finite temperature coefficient.
3. Judge traceability before anything else. A standard whose route is
   not a recognised primary one, or whose certificate reference is
   blank, closes the assessment -- name every such standard, not the
   first found.
4. Judge the certificate validity against the test date. A calibration
   dated after the test is a record defect and is refused outright; a
   lapsed one closes the assessment; one inside the marginal window
   passes with an advisory.
5. Match the standards to the junctions the article needs set. A missing
   junction closes the assessment; a standard for no required junction
   is reported as unused.
6. For each as-set record, carry the certificate current across to the
   temperature the standard was at, take the signed level error against
   that corrected target, and hold every one inside tolerance.
7. Close on one verdict: traceability not established, calibration
   expired, junction coverage incomplete, level out of tolerance, or
   level set -- reporting the worst residual error and its sign beside
   it.

## Pitfalls

- Setting the lamp so the standard reads its certificate current while
  the cell sits well off the reference temperature. It is the single
  most common way a correctly calibrated standard produces a wrong
  illumination level.
- Setting a multijunction article from one standard. The junctions that
  were never set are exactly the ones that can limit the article, and
  the setting looks clean because nothing measured them.
- Reading a certificate number as traceability. The route is what makes
  the standard primary; the number only identifies the paperwork.
- Judging validity against the planning date. Campaigns slip, and a
  certificate that was in date in the schedule is regularly out of date
  on the bench.
- Collapsing the residual error into a pass. It has a sign and it biases
  every measurement taken afterwards in one direction.
- Comparing a derived error fraction against its tolerance by bare
  arithmetic. Both sides are floats that can land a unit in the last
  place either side of the bound, so the comparison absorbs that while
  the tolerance itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, standard cell record validation with duplicate
rejection, the traceable-route test, the certificate age and validity
against the test date, the marginal validity advisory, the junction
coverage with missing and unused standards, the temperature-corrected
target current, the signed level error, the worst setting and the
illumination verdict are exercised by the gate 3 contract test:
scripts/test_e2008_primary_standard_cells.py against
scripts/e2008_primary_standard_cells_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_primary_standard_cells.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
