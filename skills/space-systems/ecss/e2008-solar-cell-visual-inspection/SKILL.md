---
name: e2008-solar-cell-visual-inspection
description: "Screen the solar cells of an inspected coupon against the defect quantity limits of ECSS-E-ST-20-08C clause 5.5.3.2.8: tally every observation by kind on each cell, compute how many cells across the coupon carry each kind, and disposition the result on how often a defect turned up rather than on how large it was — a per-cell allowance for every kind, a coupon-wide affected-cell fraction, a total across all kinds that catches the cell inside each one, and a completeness check that holds the coupon open while any cell carries no record. Use when a coupon has been examined and the counts need grading. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-8, solar-cell-defect-quantity-limits, solar-cell-per-cell-defect-allowance, solar-cell-per-coupon-affected-fraction, coupon-cell-inspection-completeness."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-solar-cell-visual-inspection, solar-cell-defect-quantity-limits, solar-cell-per-cell-defect-allowance, solar-cell-per-coupon-affected-fraction, coupon-cell-inspection-completeness, solar-cell-coupon-defect-tally]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Solar Cell Visual Inspection (space-systems/ecss/e2008-solar-cell-visual-inspection)

Use when the task is the solar cell screen of ECSS-E-ST-20-08C clause
5.5.3.2.8 -- grading the cells of an inspected coupon on how many
defects of each kind they carry, and keeping the coupon open until
every cell has been looked at.

## Domain quick reference

- This clause counts. A sizing rule asks how big one mark is; a
  quantity rule asks how many turned up and on how many cells, and a
  coupon can fail it while every individual defect sits comfortably
  inside its own dimensional limit.
- Two allowances run at once and they answer different questions. The
  per-cell allowance bounds how many occurrences of a kind one cell
  may carry. The coupon allowance bounds what fraction of the
  inspected cells may carry that kind at all, and it is the one that
  catches a process drifting across the whole coupon.
- Occurrences and affected cells are not the same number. Three chips
  on one cell is a cell problem; one chip on each of three cells is a
  handling or process problem, and rolling the two together hides
  whichever one is actually happening.
- A kind whose per-cell allowance is zero is not permitted at any
  quantity. A cracked cell is the standing example: one occurrence
  takes the cell out of the accept band, and a coupon fraction that
  permits some of it contradicts the per-cell rule rather than
  relaxing it.
- A total across all kinds sits above the per-kind allowances for the
  cell that passed every one of them and is nevertheless covered in
  marks, and the same idea applies at coupon level to the fraction of
  cells carrying anything at all.
- Counts read off a short record set understate every allowance. The
  coupon stays open while any declared cell has no record, whatever
  the inspected ones showed.

## Workflow

1. Take the declared cell count for the coupon and the inspection
   records. Reject a record set larger than the declared count, and
   report the shortfall when it is smaller.
2. Tally each cell by defect kind, rejecting an unrecognised kind or a
   repeated defect identifier before anything is graded.
3. Compare each kind on the cell with its per-cell allowance; an
   overrun inside the review margin refers, an overrun past it
   rejects, and a zero-allowance kind rejects on its first occurrence.
4. Apply the all-kinds total to the cell that stayed inside every
   individual allowance.
5. Roll the cells up: occurrences and affected-cell counts per kind,
   the affected fraction against the coupon allowance, and the
   fraction of cells carrying anything at all.
6. Report the worst verdict, the cells that are not accepted, the
   kinds over their coupon allowance, and the completeness flag. The
   coupon closes only when the record set is complete.

## Pitfalls

- Grading the coupon on the worst single defect. The clause is a
  counting rule, and the coupon that fails it is usually the one where
  nothing individually looked serious.
- Adding occurrences and affected cells into one number. They separate
  a bad cell from a bad process, and the merged figure identifies
  neither.
- Treating a zero allowance as a very small one. A kind that is not
  permitted at any quantity has no review band to fall into.
- Reading a fraction off an incomplete record set. Twelve clean cells
  out of a declared twenty is not an eighty per cent pass, it is an
  unfinished inspection.
- Letting a project limit set carry a coupon fraction for a kind it
  permits none of on a single cell. The two allowances have to agree
  before either is applied.
- Comparing a counted number of cells with a derived allowance by bare
  arithmetic. The allowance is a product of a declared fraction and a
  counted cell total, so a count sitting exactly on it can evaluate a
  few units in the last place above it; the comparison absorbs that
  representation error while the allowance stays untouched.

## Behavior contract (gate 3)

The per-kind tally, per-cell and coupon quantity allowances, the
all-kinds totals, the zero-allowance rule and the coupon completeness
rollup are exercised by the gate 3 contract test:
scripts/test_e2008_solar_cell_visual_inspection.py against
scripts/e2008_solar_cell_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_solar_cell_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
