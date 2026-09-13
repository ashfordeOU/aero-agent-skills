---
name: e2008-sca-flatness-test-process
description: "Compute the maximum deflection of a completed solar cell assembly resting unclamped on an optically flat reference surface under ECSS-E-ST-20-08C clause 6.4.3.17.2: validate the footprint, the flat and every probe reading, refer the readings to the seating plane the assembly actually rests on, take the largest standoff as the deflection, guard band it with the flat residual and probe uncertainty in quadrature, and report how much of the footprint and its edge bands the pattern reached before any number is quoted. Use when running or auditing a cell assembly flatness measurement. Trigger: ecss, e-st-20-08c, clause-6-4-3-17-2, sca-flatness-measurement-run, optical-flat-reference-seating, sca-maximum-deflection-standoff, sca-flatness-probe-pattern-coverage, sca-deflection-uncertainty-guard-band."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-sca-flatness-test-process, sca-flatness-measurement-run, optical-flat-reference-seating, sca-maximum-deflection-standoff, sca-flatness-probe-pattern-coverage, sca-deflection-uncertainty-guard-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Flatness Test Process (space-systems/ecss/e2008-sca-flatness-test-process)

Use when the task is to run or audit the flatness measurement of
ECSS-E-ST-20-08C clause 6.4.3.17.2 — laying the completed assembly on an
optically flat reference surface, reading the standoff across it, and turning
those readings into a maximum deflection a disposition can be made on.

## Domain quick reference

- The optical flat is the datum, and gravity is the fixture. The assembly is
  laid on the flat unclamped; it settles onto whichever points are lowest and
  the rest of it stands off by the amount it is bowed or twisted. Clamping it
  measures the clamp.
- A probe zero is arbitrary, so a raw reading is not a deflection. The
  assembly touches the flat where the reading is smallest, so every reading is
  referred to that smallest one before the largest standoff can be called the
  deflection. A constant offset in the probe then changes nothing.
- Where the pattern goes decides what the number means. A bow stands off most
  at the edges and corners, which is exactly where a convenient pattern stops,
  so a deflection read from the middle of the footprint is a statement about
  the middle of the footprint.
- Coverage is two separate questions. Whether the pattern spread across the
  whole footprint and whether it reached the edge band are different failures
  with different causes, so they are reported separately rather than rolled
  into one score.
- A point on the far corner of the footprint belongs to the last cell, not to
  one past it. The grid index is clamped at the edge so a legitimate corner
  reading is never refused.
- The reference and the probe each carry an error. Combined in quadrature they
  guard band the deflection, so what goes downstream already carries its own
  uncertainty instead of collecting it later.
- The floor edges are part of the floor. A coverage fraction landing exactly on
  its floor passes; the comparison absorbs representation error rather than
  moving the floor.
- Coverage is sentenced before the deflection is believed, and the subgroup
  floor is sentenced before either. A well covered run of two samples still
  cannot speak for the lot.
- This clause measures; it does not accept. Comparing the deflection with the
  limiting value for the geometry belongs to the acceptance criteria clause.

## Workflow

1. Validate the assembly footprint: a positive length and width in millimetres.
2. Validate the reference surface: a non-negative flat residual and a
   non-negative probe uncertainty, both declared.
3. Validate every probe reading — on the footprint in both axes, a
   non-negative standoff, no repeated probe point, and enough readings to
   define a seating plane at all.
4. Refer the readings to the seating plane by subtracting the smallest of
   them, then take the largest result as the maximum deflection and record
   where on the footprint it sits.
5. Combine the flat residual and the probe uncertainty in quadrature and add
   the result to the deflection for the guard-banded value.
6. Compress the footprint into a grid, record which cells the pattern reached,
   and compare the covered fraction with the floor.
7. Check the four edge bands separately and name the ones the pattern never
   reached.
8. Repeat per sample, refuse a repeated sample identifier, then close on one
   run verdict — undersized, coverage short, or valid — with the worst
   guard-banded deflection and every per-sample finding attached.

## Pitfalls

- Quoting the largest raw reading as the deflection. It carries the probe zero,
  so it changes when somebody re-datums the gauge and the assembly has not
  moved at all.
- Clamping or holding the assembly down to steady it. The reading then reports
  how hard it was held, and a bowed assembly reads flat.
- Reading a comfortable interior pattern. Every cell can be reached while the
  corners that carry the bow are never touched, which is why the edge bands are
  a separate check rather than a consequence of cell coverage.
- Refusing a reading taken exactly on the far edge of the footprint. It is a
  legitimate corner point; the grid index belongs to the last cell.
- Treating the optical flat as perfect. Its residual is part of the number, and
  ignoring it quietly tightens every downstream comparison.
- Adding the flat residual and the probe uncertainty arithmetically. They are
  independent, so quadrature is the combination and a linear sum inflates the
  guard band.
- Believing a deflection from a run that fell short on coverage. The unread
  part of the footprint is where the standoff usually is, so coverage is
  sentenced first.
- Sentencing an undersized subgroup on the samples it happened to carry. The
  sampling floor is a separate condition with its own verdict.

## Behavior contract (gate 3)

The footprint, reference and reading validation, the seating plane referral,
the maximum deflection and its guard band, the cell and edge band coverage,
the per-sample findings and the subgroup run verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_sca_flatness_test_process.py against
scripts/e2008_sca_flatness_test_process_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_sca_flatness_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
