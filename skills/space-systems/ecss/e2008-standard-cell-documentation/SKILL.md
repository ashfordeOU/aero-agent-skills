---
name: e2008-standard-cell-documentation
description: "Assess the data sheet a standard solar cell is delivered with under ECSS-E-ST-20-08C clause 10.2.3, grading identification, calibration and uncertainty budget as three blocks rather than one list: name every required field the sheet leaves unreported, keep a reported zero apart from an empty box, reduce each budget component by its distribution and sensitivity, recompute the combined and expanded uncertainty from those components and compare them with the figures printed, then report a dominant term or a budget with no type A evidence as observations rather than failures. Use when a standard cell record must be shown fit to support another calibration. Trigger: ecss, e-st-20-08c, standard-solar-cell-data-sheet, standard-cell-calibration-conditions, standard-cell-uncertainty-budget-recomputation, reference-cell-identification-record, calibration-coverage-factor-check."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-standard-cell-documentation, standard-solar-cell-data-sheet, standard-cell-calibration-conditions, standard-cell-uncertainty-budget-recomputation, reference-cell-identification-record, calibration-coverage-factor-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Array — Standard Cell Documentation (space-systems/ecss/e2008-standard-cell-documentation)

Use when the task is clause 10.2.3 of ECSS-E-ST-20-08C -- the data
reported for a standard cell: which cell it is, what value it was
assigned and under what conditions, and the uncertainty budget standing
behind that value. A standard cell is only as useful as the sheet that
travels with it, because everything calibrated against it inherits both
the value and the budget.

## Domain quick reference

- The sheet holds three blocks and they are graded separately.
  Identification says which physical object this is; calibration says
  what value was assigned and under which spectrum, irradiance,
  temperature, day, laboratory and method; the budget says how well
  that value is known. A sheet complete in two blocks and hollow in the
  third scores well on a flat field count and is still unusable.
- An absent field is unknown, not zero. A cell temperature of 0 C is a
  reported measurement; an empty temperature box is a hole in the
  sheet, and a grader that treats emptiness as a number turns the hole
  into a value nobody took. Emptiness covers a blank string and an
  empty list as well as an absent key.
- A calibration value without its conditions does not transfer. The
  same cell reads differently under a different reference spectrum or
  at a different junction temperature, so the conditions are required
  fields and not annotations.
- The budget is recomputed, never read. Each component is reduced to a
  standard uncertainty by the divisor its assumed distribution implies
  -- one for normal, the root of three for rectangular, of six for
  triangular, of two for u-shaped -- and scaled by its sensitivity.
  Those are combined as a root sum of squares and widened by the stated
  coverage factor.
- A printed combined uncertainty that does not follow from the printed
  components is the finding worth having. It is either a typing error
  or a term the reader cannot see, and both matter before the cell is
  used to calibrate anything else.
- A component carrying most of the variance, and a budget with no type A
  term at all, are legitimate in a particular setup. They are reported
  as observations rather than defects, because they change what a
  reviewer looks at next without making the sheet wrong.

## Workflow

1. Take the record apart into its three declared blocks and reject an
   unknown block rather than ignoring it -- a field filed under a name
   nobody grades is a field nobody reads.
2. Walk the required fields of each block and name every one the sheet
   leaves unreported, keeping a reported zero apart from an empty box.
3. Report completeness per block and for the sheet as a whole, so a
   hollow block cannot hide behind two full ones.
4. Check the assigned value is a positive current and the calibration
   day is a real calendar day, reporting a malformed day as its own
   finding rather than dropping it.
5. Reduce every budget component by its distribution divisor and
   sensitivity, combine them, widen by the coverage factor, and compare
   both figures with what the sheet prints.
6. Note a dominant component and an absent type A term, then withhold
   the complete verdict on the defects alone, leaving the observations
   as reading for the reviewer.

## Pitfalls

- Counting fields across the whole sheet. One ratio over three blocks
  lets a full identification block carry an empty budget, which is the
  one block nothing downstream can reconstruct.
- Defaulting an empty field to zero. It makes the sheet look complete,
  and it quietly asserts a measurement -- a zero correction, a zero
  uncertainty term -- that nobody performed.
- Reading the printed combined uncertainty. It is the number most
  likely to have been carried over from a previous sheet, and it is the
  one number the components themselves can check.
- Combining components without their divisors. A rectangular term
  entered at its half-width overstates its contribution by about
  seventy percent, and an over-large budget rejects good cells as
  surely as a small one accepts bad ones.
- Treating a dominant component as a failure. A budget can properly be
  led by its primary reference; what matters is that the reviewer is
  told, so the effort goes where the variance is.
- Comparing a recomputed uncertainty with a printed one by bare
  arithmetic. The recomputation is a square root of a sum of quotients
  and the sheet quotes a rounded figure, so the difference is graded
  against a stated tolerance and the comparison absorbs the last-place
  representation error rather than failing a sound sheet.

## Behavior contract (gate 3)

The block decomposition, reported-against-empty field rule, per-block
and whole-sheet completeness, calibration value and day checks,
distribution divisors and sensitivity scaling, root-sum-of-squares
combination, coverage-factor expansion, printed-against-recomputed
comparison, dominant-component share and the type A observation are
exercised by the gate 3 contract test:
scripts/test_e2008_standard_cell_documentation.py against
scripts/e2008_standard_cell_documentation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_standard_cell_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
