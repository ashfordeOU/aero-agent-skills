---
name: q6005-hermetic-leak-testing
description: "Verify the fine and gross seal integrity evidence behind a hermetic hybrid package under ECSS-Q-ST-60-05C clause 10.3.7. Use when the task is banding the allowable leak rate on internal cavity volume, modelling what the instrument reads from bomb pressure, bomb time, dwell and tracer molecular weight, recovering the equivalent air leak rate numerically from that reading, refusing a reading past the turning point where one number answers to two seals, and ordering the gross test after the fine one it cannot replace. Trigger: ecss, q-st-60-05c, hybrid-hermetic-seal-integrity, fine-leak-fixed-method-reading, hermetic-cavity-volume-reject-limit, tracer-bomb-pressure-time-product, fine-leak-dwell-window, gross-leak-test-sequence."
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
  tags: [ecss, q-st-60-05-hybrid-scope, q6005-hermetic-leak-testing, hybrid-hermetic-seal-integrity, fine-leak-fixed-method-reading, hermetic-cavity-volume-reject-limit, tracer-bomb-pressure-time-product, gross-leak-test-sequence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Screening — Hermetic Leak Testing (space-systems/ecss/q6005-hermetic-leak-testing)

Use when the task is the seal integrity screen of ECSS-Q-ST-60-05C
clause 10.3.7 — showing that a sealed hybrid still holds the atmosphere
it was closed with, and that the fine and gross tests behind that claim
were run under conditions their readings actually depend on.

## Domain quick reference

- The limit belongs to the cavity, not to the instrument. The same
  physical leak empties a small cavity quickly and a large one slowly,
  so the allowable rate is banded on internal free volume. One house
  limit is necessarily wrong at one end of the range, and it is wrong
  in the unsafe direction for the small parts.
- The instrument does not read the leak rate. In the fixed method the
  unit is pressurized in a tracer atmosphere, removed, and measured, so
  the reading is the tracer that got in during the bomb and has not yet
  got back out. Bomb pressure, bomb time, cavity volume, dwell before
  measurement and the molecular weight of the tracer all sit between
  the seal and the number on the screen.
- Recovering the seal from the reading is the work. The relation has no
  closed inverse, so it is solved numerically, and it is not monotonic:
  past a turning point a larger hole empties the cavity during the
  dwell faster than the bomb filled it, and the reading falls again.
  Above that point one reading answers to two seals, and the honest
  output is that the fine test cannot say which — not the tighter of
  the two.
- The bomb is a pressure acting for a time. A short bomb at high
  pressure and a long one at low pressure are not interchangeable, and
  a cavity that was never charged reads clean whatever its seal does.
- The dwell is part of the measurement. Tracer starts leaving the
  moment the unit comes out of the bomb, and a leaking part left on the
  bench long enough reads as a good one. The window is a requirement,
  not a convenience.
- The gross test is not a coarser fine test, it is the test for the
  regime the fine test is blind to. It also wets the part, so it runs
  second. A fine-only result on a package with a large hole is a pass
  the method cannot support.

## Workflow

1. Validate each unit record: identifier, tracer, test order, cavity
   volume, bomb pressure and time, dwell, the measured tracer rate and
   the gross test outcome. An unknown tracer, an unknown test order, a
   negative dwell and a non-positive volume, pressure, time or reading
   are input errors.
2. Read the allowable equivalent air leak rate from the cavity volume
   band before looking at any measurement.
3. Compute the turning point for these conditions, so the reading is
   known to be resolvable before it is resolved.
4. Recover the equivalent air leak rate from the reading by bisecting
   the rising branch, and report it absent rather than zero when the
   reading sits above what the conditions can resolve.
5. Bound the conditions the reading depends on: the bomb pressure-time
   product against its minimum, and the dwell against the measurement
   window, absorbing each boundary with a named tolerance.
6. Grade the recovered rate against the cavity limit, and grade the
   gross test separately: performed at all, performed in the right
   order, and free of an indication.
7. Aggregate the batch: accepted and rejected units, the units whose
   readings could not be resolved, and the worst recovered rate any
   resolvable unit in the batch carries.

## Pitfalls

- Applying one leak rate limit to every package. A rate that is a
  pinhole in a large cavity empties a small one, and the small parts
  are the ones the single limit lets through.
- Reading the instrument as if it reported the seal. Without the bomb
  conditions and the dwell the number means nothing, and two units with
  the same reading can have very different seals.
- Resolving a reading above the turning point to the tighter of its two
  answers. That is the wide-open part being recorded as the good one,
  and it is the exact case the gross test exists to catch.
- Cutting the bomb short and keeping the same acceptance limit. An
  undercharged cavity has little tracer to give back, so the part reads
  clean for a reason that has nothing to do with its seal.
- Measuring late. A leaking cavity empties during the dwell, so the
  units measured at the end of a long queue systematically read better
  than the ones measured first.
- Skipping the gross test because the fine test passed, or running it
  first. The fine test cannot see the holes the gross test is for, and
  a part wetted by the gross test is no longer a clean fine test
  subject.

## Behavior contract (gate 3)

The volume-banded limit, the fixed-method reading, the dwell retention
factor, the turning point and the numerical recovery of the equivalent
air leak rate, the bomb and dwell condition checks, the gross test
sequence checks and the batch aggregation are exercised by the gate 3
contract test: scripts/test_q6005_hermetic_leak_testing.py against
scripts/q6005_hermetic_leak_testing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_hermetic_leak_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
