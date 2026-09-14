---
name: e2008-cell-surface-finish-test
description: "Evaluate the finish a bare solar cell contact surface presents for qualification under ECSS-E-ST-20-08C clause 7.5.11: confirm the profile trace is long enough and self-consistent before any roughness figure is believed, validate the examined anomaly population, and judge the surface on mean deviation, peak-to-valley height, the largest single anomaly, the contact area anomalies occupy and a severity-weighted demerit score, returning a compliant, marginal or non-compliant grade alongside how much of each limit was used up. Use when a profile trace and an anomaly list are about to qualify a cell contact surface. Trigger: ecss, e-st-20-08c-clause-7-5-11, bare-cell-contact-surface-finish, solar-cell-contact-roughness-trace, cell-contact-anomaly-demerit-score, contact-surface-anomaly-area-fraction, bare-cell-metallisation-finish-grade."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e-st-20-08c-clause-7-5-11, e2008-cell-surface-finish-test, bare-cell-contact-surface-finish, solar-cell-contact-roughness-trace, cell-contact-anomaly-demerit-score, contact-surface-anomaly-area-fraction, bare-cell-metallisation-finish-grade]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Cell Surface Finish Test (space-systems/ecss/e2008-cell-surface-finish-test)

Use when the task is clause 7.5.11 of ECSS-E-ST-20-08C -- the
qualification examination of the finish that the contact surfaces of a
bare solar cell present. The surface in question is the face an
interconnect is welded or soldered onto and the face a bond has to wet,
so the question is not how much metal is there but what the top of it
looks like.

## Domain quick reference

- Two unrelated kinds of evidence arrive under one heading. A profile
  trace reduces the texture to roughness parameters; an examination of
  the surface returns discrete anomalies. Neither substitutes for the
  other: a contact can be beautifully smooth and carry a void where the
  weld lands, and it can be visibly clean and far too rough to wet.
- The trace is checked before it is believed. The mean deviation cannot
  exceed the peak-to-valley height, and a peak-to-valley height only
  just above it is not a smooth surface -- it is a trace too short, too
  heavily filtered, or taken somewhere other than the contact.
- Anomalies are not equal. A stain and a flake off the metallisation
  are both anomalies and only one of them removes contact area, so a
  severity weight rides with the kind.
- Three anomaly measures are carried because they catch three different
  failures: the largest single anomaly catches one big fault, the
  occupied area fraction catches many small ones, and the
  severity-weighted demerit score catches a population of severe faults
  that is small in total area.
- The result is reported as how much of each limit was used up, not as
  a bare pass. A surface sitting at ninety per cent of every limit is
  inside all of them and is not the same evidence as one at a tenth,
  which is what the marginal grade exists to say.
- An observation that looked for a kind and found none is kept in the
  record with a count of zero. Dropping it makes an examination that
  checked for voids indistinguishable from one that never looked.
- The same anomaly kind recorded twice is two rows that should be one.
  Combining them is the examiner's call, not the reduction's, so the
  duplicate is refused.

## Workflow

1. Take the inspected contact area, the trace length and the two
   roughness parameters, and name the contact the trace came off.
2. Check the trace can carry a judgement at all -- long enough, and a
   peak-to-valley height far enough above the mean deviation -- and
   stop there if it cannot. An inadequate examination is neither an
   acceptance nor a rejection.
3. Validate the anomaly population: a known kind, a whole count, a
   positive area behind any non-zero count, and no kind recorded twice.
4. Reduce the population three ways -- largest single anomaly, occupied
   area as a fraction of the inspected area, and the severity-weighted
   demerit score.
5. Express each measure as the share of its limit it uses, and take the
   grade from the worst share: over the limit is non-compliant, inside
   the marginal band is marginal, below it is compliant.
6. Close with a verdict where an inadequate trace outranks a rejection,
   and where a marginal grade is accepted and said out loud rather than
   quietly passed.

## Pitfalls

- Believing a roughness figure without checking the trace behind it. A
  peak-to-valley height barely above the mean deviation produces the
  flattest, most reassuring numbers in the whole data set.
- Judging the anomaly population on area alone. A handful of flakes off
  the metallisation occupies almost nothing and is the most serious
  finding the examination can return.
- Judging it on count alone. That treats a stain on the surface and a
  void under the weld site as the same event.
- Dropping a zero-count observation. The record then cannot tell a
  surface that was examined for voids from one that never was, and the
  gate over it stays green either way.
- Reporting a pass without how close it was. A contact at ninety per
  cent of every limit passes, and it is the one that will not pass next
  lot, which is why the marginal grade is carried.
- Confusing this with the contact thickness measurements. How deep the
  metal is and how evenly it is laid are separate clauses with separate
  limits; this one is about the face that metal presents.

## Behavior contract (gate 3)

Policy validation, anomaly validation and severity weighting, the total
and largest anomaly areas, the occupied area fraction, the demerit
score, trace consistency and length adequacy, the per-limit utilisation
and the compliant, marginal and non-compliant grades behind the final
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_cell_surface_finish_test.py against
scripts/e2008_cell_surface_finish_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_cell_surface_finish_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
