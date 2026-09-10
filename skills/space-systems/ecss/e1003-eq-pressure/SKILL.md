---
name: e1003-eq-pressure
description: "Use when running equipment structural-integrity-under-pressure tests under ECSS-E-ST-10-03C: run the leak, proof pressure, pressure cycling, design burst and burst tests on pressurized space segment equipment, derive which of these tests apply from the test campaign and the item's service profile, select whether burst margin is demonstrated by a physical burst test or a design burst analysis depending on whether the article can be sacrificed, sequence a destructive burst test last, and evaluate each test's pass/fail criteria before declaring the item's pressure-test set complete. Trigger: pressure test, leak test, proof pressure, proof pressure test, pressure cycling, design burst, burst test, MEOP, burst factor, structural integrity under pressure, e-st-10-03, ecss, e-st-10c."
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
  tags: [ecss, e-st-10c, e-st-10-03c, pressure-test, leak-test, proof-pressure, pressure-cycling, burst-test, equipment-testing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Equipment Pressure Tests (space-systems/ecss/e1003-eq-pressure)

Use when the task is running the structural-integrity-under-pressure
test family on a piece of pressurized space segment equipment under
ECSS-E-ST-10-03C: leak, proof pressure, pressure cycling, design
burst, and burst.

## Domain quick reference

- ECSS-E-ST-10-03C clause 5.5.3 groups the tests that demonstrate a
  pressurized equipment item's structural integrity: a leak test (no
  detrimental leakage), a proof pressure test (structural margin
  demonstrated nondestructively, holding a pressure above MEOP -
  maximum expected operating pressure - without damage), a pressure
  cycling test (fatigue life demonstrated over repeated
  pressurization/depressurization for equipment in cyclic service),
  and a burst-margin demonstration.
- The burst-margin demonstration is done one of two mutually exclusive
  ways, chosen by whether the tested article can be sacrificed: a
  dedicated qualification article (never flown) gets a physical burst
  test, pressurized to actual failure; a flight article (protoflight
  or acceptance, which must remain usable afterward) instead gets a
  design burst analysis, a nondestructive margin calculation against
  the required burst factor.
- The physical burst test is destructive, so it can only be the last
  test performed on that article - nothing else can follow it, and an
  article is never subjected to both a physical burst test and a
  design burst analysis.
- Non-pressurized equipment is out of scope for this test family
  entirely; the numeric pressure levels, hold times and cycle counts
  come from the item's qualification/acceptance/protoflight baseline
  (sibling leaves e1003-eq-qual / e1003-eq-acceptance /
  e1003-eq-protoflight), not from this leaf.

## Workflow

1. For the equipment item, capture whether it is pressurized, whether
   it sees cyclic pressurization in service, the test campaign
   (qualification, acceptance, protoflight), and the article's
   disposition (dedicated qualification article that may be
   sacrificed, or a flight article that must survive testing).
2. Derive the required test set: nothing for non-pressurized
   equipment; leak and proof pressure for every pressurized item;
   pressure cycling added when the item is in cyclic service; and
   either burst (dedicated qualification article) or design burst
   (flight article) for the burst-margin demonstration.
3. If tests have already been performed, validate the order: reject
   any sequence where burst is not the last test, or where both burst
   and design burst appear on the same article.
4. Evaluate each performed test against its pass/fail rule: leak rate
   at or below the maximum allowable; proof pressure held at or above
   the required level with no anomaly (deformation, leak, damage);
   cycling completed to the required cycle count with no failure;
   design burst's predicted burst pressure at or above the required
   burst factor times MEOP; burst's actual achieved burst pressure at
   or above the required burst factor times MEOP.
5. Mark each required test closed, failed, or open (not yet
   performed); the item's pressure-test set is only complete when
   every required test is closed - list any open or failed test rather
   than assuming completion.

## Pitfalls

- Running a physical burst test on a flight (protoflight/acceptance)
  article instead of the nondestructive design burst analysis -
  destroys hardware that must remain usable.
- Scheduling any test after a physical burst test - the article no
  longer exists as a structurally intact test object once burst.
- Skipping the pressure cycling test for equipment that sees repeated
  pressurization in service just because the campaign is acceptance
  rather than qualification.
- Declaring the pressure-test set complete while a required test is
  still open or has failed rather than being closed.

## Behavior contract (gate 3)

The test-applicability, burst-method-selection, sequencing, and
pass/fail evaluation logic is exercised by the gate 3 contract test:
scripts/test_e1003_eq_pressure.py against
scripts/e1003_eq_pressure_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_eq_pressure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
