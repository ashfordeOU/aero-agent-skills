---
name: e2008-cell-contact-thickness-test
description: "Use when measured contact thickness readings are about to release a bare cell lot. Determine whether a bare solar cell lot may be released on the depth of its contact metallisation under ECSS-E-ST-20-08C clause 7.5.10: size the acceptance sample against the lot, validate each measured cell, categorize every reading against the thickness floor and ceiling, hold as indeterminate any reading nearer a limit than the gauge uncertainty rather than counting it a pass, and compute the capability the sample leaves against each limit so a lot that clears on count but not on margin is caught. Trigger: ecss, e-st-20-08c-clause-7-5-10, bare-cell-contact-thickness-acceptance, solar-cell-metallisation-depth-measurement, contact-thickness-lot-release, cell-contact-thickness-guard-band, bare-cell-acceptance-sample-size, contact-thickness-process-capability."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e-st-20-08c-clause-7-5-10, e2008-cell-contact-thickness-test, bare-cell-contact-thickness-acceptance, solar-cell-metallisation-depth-measurement, contact-thickness-lot-release, cell-contact-thickness-guard-band, bare-cell-acceptance-sample-size, contact-thickness-process-capability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Cell Contact Thickness Test (space-systems/ecss/e2008-cell-contact-thickness-test)

Use when the task is clause 7.5.10 of ECSS-E-ST-20-08C -- the
acceptance measurement of metallisation depth on the contacts of bare
solar cells, taken on a sample of a lot before that lot is released.
This is a depth question with a floor and a ceiling. Whether the depth
is the same everywhere along one contact is the qualification
uniformity measurement and carries a different limit set.

## Domain quick reference

- Both limits bite. Too little metal cannot carry the cell current or
  take an interconnect weld; too much adds mass and stiffens the
  contact against a cell it is bonded to across thousands of deep
  thermal cycles. A lot fails at either end.
- The sample stands in for the lot, so its size is derived from the lot
  size: a declared fraction with a floor under it, and never more cells
  than the lot holds. A fixed sample of five is the right answer for a
  tray and the wrong answer for a shipment.
- A whole-number product such as a hundred cells at a tenth lands a few
  units in the last place above ten in binary arithmetic, and a bare
  ceiling function then buys an eleventh cell. The rounding carries a
  relative tolerance for that reason.
- Every gauge has an uncertainty, and a reading sitting closer to a
  limit than that uncertainty is consistent with being on either side
  of it. Counting it as a pass moves the gauge error into the lot
  disposition, so conformance is only claimed inside limits pulled in
  by the uncertainty at each end, and a reading in the guard band comes
  back as unplaceable rather than as good.
- A lot can clear both limits on count and still be a lot whose next
  batch does not. The capability index against the nearer limit is what
  says so, and the count of nonconforming cells never will.
- A sample with no resolvable spread is a gauge too coarse to see the
  process, not an infinitely capable process. It is reported as
  unresolved rather than as a very large index.
- One reading per cell. The same cell measured twice is a gauge study,
  and folding it into a lot sample weights that cell against the rest.

## Workflow

1. Name the contact type being measured and take the lot size. Both
   travel with the result, because a bus bar reading does not release a
   grid finger and a sample size means nothing without the lot.
2. Derive the required sample size from the lot and compare it against
   what was actually measured. Stop if the sample is short: an
   undersized sample is not a fail, it is an absent measurement.
3. Validate each measured cell -- a positive finite reading, one
   reading per identifier -- and refuse the sample outright on a bad
   entry rather than dropping it silently.
4. Categorize each reading: outside a limit, inside the guard band at
   either end, or conforming. Keep the two guard-band outcomes distinct
   so the remeasurement is aimed at the right end.
5. Compute the sample mean and spread, and from them the capability
   against each limit, taking the nearer one as the index.
6. Close with a disposition that ranks an inadequate sample above a
   rejection, a rejection above an unplaceable reading, and releases
   only a sample that is complete, conforming and capable.

## Pitfalls

- Judging a reading against a bare limit. The gauge uncertainty belongs
  in the comparison, and leaving it out silently converts instrument
  error into a release decision.
- Treating an unplaceable reading as a pass because it is on the right
  side of the number. It is on the right side of the number by less
  than the instrument can resolve, which is not evidence.
- Releasing a lot on count alone. Every cell can clear the floor by a
  hair and every figure reported will look clean, while the next lot
  off the same line sits under it.
- Reading a sample of identical values as a perfect process. It is
  almost always a gauge whose resolution is coarser than the spread it
  is being asked to measure.
- Fixing the sample size regardless of the lot. The same five cells
  that speak for a tray say almost nothing about a shipment, and the
  gate that checked them stays green either way.
- Carrying an acceptance verdict over to uniformity. A contact can be
  deep enough at every measured cell and still be laid unevenly along
  its own length; that is a different clause and a different limit.

## Behavior contract (gate 3)

Policy validation, lot-derived sample sizing, measurement validation,
guard-banded reading dispositions, the nonconforming and unplaceable
cell lists, sample statistics, the capability indices against each
limit and the ranked lot disposition are exercised by the gate 3
contract test: scripts/test_e2008_cell_contact_thickness_test.py
against scripts/e2008_cell_contact_thickness_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_cell_contact_thickness_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
