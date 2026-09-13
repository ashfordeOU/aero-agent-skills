---
name: e2008-sca-coverglass-defects
description: "Determine whether every coverglass on a solar cell assembly leaves the bare cell surface completely covered under ECSS-E-ST-20-08C clause 6.4.3.1.5: take the signed glass overhang on each cell edge once the placement offset has been taken off it, separate a glass too small for the cell from a large enough glass laid off-centre, read each edge chip through the overhang it consumed, hold a shortfall inside the placement tolerance as indeterminate rather than covered, and return accept, rework, refer-for-review or reject with the uncovered area and the unexamined glasses named apart. Use when a coverglassed assembly has been examined and the coverage statement needs geometry behind it. Trigger: ecss, e-st-20-08c, clause-6-4-3-1-5, sca-coverglass-complete-coverage, bare-cell-surface-exposure, coverglass-placement-overhang, coverglass-edge-chip-overhang-consumption, undersized-coverglass-detection."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-coverglass-defects, e-st-20-08c, sca-coverglass-complete-coverage, bare-cell-surface-exposure, coverglass-placement-overhang, coverglass-edge-chip-overhang-consumption, undersized-coverglass-detection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Coverglass Defects (space-systems/ecss/e2008-sca-coverglass-defects)

Use when the task is clause 6.4.3.1.5 of ECSS-E-ST-20-08C: confirming that the
coverglass fitted to a cell covers the bare cell surface completely. The
clause is not asking how good the glass looks; it is asking whether any part
of the cell has been left out from under it.

## Domain quick reference

- The screen is geometry before it is defect work. A coverglass is a
  rectangle laid over a cell rectangle, and the answer lives in the signed
  overhang on each of the four edges once the placement offset has been taken
  off it. A positive overhang is glass standing proud; a negative one is a
  strip of bare cell.
- An offset does not lose overhang, it moves it. Extra margin on one edge is
  exactly the margin missing from the opposite one, which is why a glass that
  looks generously oversized in the fixture can still run short.
- Three outcomes come out of the same geometry and they are different
  findings. Square and large enough is complete coverage with margin. Large
  enough but off-centre is incomplete coverage that a lift and re-lay
  recovers. Smaller than the cell on an axis is the wrong part: no placement
  covers it and no re-lay helps.
- An edge chip in the glass is read through the overhang, not through its own
  size. The same chip is nothing on an edge with margin to give and an
  exposure on an edge that had none, so the chip is subtracted from the
  overhang at its own edge before anything is decided.
- A chip on an edge the placement already left short must not be charged
  twice. What it adds is the strip beyond the shortfall that was already
  counted, over the chip's own length.
- A shortfall smaller than the placement measurement tolerance is not a
  covered cell and it is not an exposed one either. It is an indeterminate
  record, and it is reported as such instead of being rounded into whichever
  answer the reader wanted.
- Covered with no margin is still a finding. An overhang under the declared
  minimum survives this inspection and not the next handling step.
- A glass nobody looked at is not a covered cell. The assembly stays open
  until every declared coverglass carries a record.

## Workflow

1. Take the cell and glass outlines and the placement offset, and derive the
   signed overhang on all four edges.
2. Ask the part question first: is the glass at least as large as the cell on
   both axes? If not, name the short axes and reject; nothing downstream can
   recover it.
3. Take the covered rectangle as the cell less the shortfall on each edge,
   and the uncovered area as what is left of the cell.
4. Per edge chip, subtract the ingress from the overhang at its own edge,
   then credit only the exposure beyond what the placement had already left
   short over that length.
5. Sort the shortfalls: beyond the tolerance is an exposure, inside it is
   indeterminate, a positive overhang under the minimum is a thin margin.
6. Disposition: rework a misplaced but adequate glass, reject one that has
   exposed more of the cell than a re-lay can be risked over, refer a thin or
   indeterminate margin, accept the rest.
7. Close with the assembly verdict, the uncovered area and its fraction, the
   glasses that are not covering, and the count of declared glasses with no
   record.

## Pitfalls

- Screening the glass for defects and never checking where it sits. A
  flawless coverglass laid 0.8 mm off-centre leaves a bare strip the whole
  length of an edge, and no defect criterion in the record will see it.
- Reading an overhang as a distance and not as a signed quantity. The sign is
  the entire finding; an absolute value turns an exposure into a margin.
- Calling a misplaced glass and an undersized glass the same reject. One is
  recovered by lifting and re-laying, the other is the wrong part number on
  the bench.
- Grading an edge chip on its own size. What decides it is the overhang that
  edge had to give, and the same chip is benign on one edge and an exposure
  on the opposite one.
- Adding a chip exposure to a placement exposure on the same edge without
  taking the overlap out. The strip is counted twice and the assembly is
  scrapped on arithmetic.
- Rounding an unmeasurable shortfall into coverage. It is not known to be
  covered, and a confident pass here is exactly the record that never gets
  revisited.
- Passing a cell that is covered with zero margin. The clause is satisfied at
  the moment of inspection and nothing is left for handling, cure shrinkage
  or the next placement check.
- Comparing an overhang with a bound by bare arithmetic. Every overhang is a
  difference of halved dimensions plus a signed offset, so one that should
  land exactly on a bound can evaluate a few units in the last place under
  it; the comparison absorbs that representation error while the bound stays
  untouched.

## Behavior contract (gate 3)

The signed per-edge overhang, the covered and uncovered areas, the undersized
versus misplaced split, the chip-through-overhang rule with its overlap
credit, the indeterminate band and the per-assembly completeness rollup are
exercised by the gate 3 contract test:
scripts/test_e2008_sca_coverglass_defects.py against
scripts/e2008_sca_coverglass_defects_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e2008_sca_coverglass_defects.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
