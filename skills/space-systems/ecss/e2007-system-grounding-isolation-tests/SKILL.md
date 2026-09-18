---
name: e2007-system-grounding-isolation-tests
description: "Validate a spacecraft grounding architecture against the isolation and continuity measurements taken at assembly under ECSS-E-ST-20-07C clause 5.3.9. Use when a bonding and isolation record has to be reconciled with the diagram it was drawn from: match every measured pair to a declared one, assess each bond against its category limit, refuse a milliohm reading taken with a two-wire instrument, separate a degraded isolation from a pair that measured as a short, confirm the isolation test voltage, and hold each power domain to exactly one structure reference. Trigger: ecss, e-st-20-07c, grounding-isolation-measurement, bonding-continuity-measurement, bond-resistance-category-limit, single-point-structure-reference, isolation-test-voltage, four-wire-bond-measurement, unintended-ground-loop."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-system-grounding-isolation-tests, grounding-isolation-measurement, bonding-continuity-measurement, single-point-structure-reference, four-wire-bond-measurement, unintended-ground-loop]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — System Grounding Isolation Tests (space-systems/ecss/e2007-system-grounding-isolation-tests)

Use when the task is the grounding verification of ECSS-E-ST-20-07C
clause 5.3.9 -- the isolation and continuity measurements made while
the vehicle is being assembled, which are what turns a grounding
diagram into a grounding architecture that actually exists.

## Domain quick reference

- The architecture is a set of node pairs with an intent, and each
  intent has its own measurement. A bonded pair is a continuity
  measurement held under a resistance limit; an isolated pair is an
  isolation measurement held above a floor at a stated test voltage.
  The same instrument cannot serve both ends of that range.
- Bond limits are set by category, not by taste. A lightning path, a
  structure bond, a unit chassis bond, a shield termination and a
  signal reference are held to different values because they carry
  different currents for different reasons, and quoting one figure for
  all of them is how a lightning path ends up qualified on a chassis
  limit.
- A two-wire reading contains the lead resistance of the instrument.
  For a bond in the milliohms that lead resistance is larger than the
  quantity being measured, so the reading is not a loose bond or a
  tight one -- it is not a measurement. Those joints need a four-wire
  method.
- Isolation fails in two distinct ways and they need different
  responses. A pair that reads well below the floor but far above a
  short is a leakage path -- contamination, a damaged standoff. A pair
  that reads near zero is a connection: the architecture has an extra
  bond in it, and the diagram, not the joint, is what has to change.
- An isolation figure without its test voltage is not evidence. The
  resistance of a contaminated or partly damaged barrier depends on the
  voltage it is measured at, and a reading taken well under the
  required voltage flatters it.
- A measured pair the architecture never declared is as much a finding
  as a declared pair nobody measured. The first is a connection nobody
  designed; the second is a joint nobody confirmed.
- Single-point discipline is checked per power domain. No structure
  reference leaves the domain floating; more than one closes the ground
  loop the single-point architecture was drawn to prevent.

## Workflow

1. Validate the declared architecture: node pairs, intent, bond
   category on every bonded pair and on no isolated pair, power domain
   where one applies. Reject an unknown intent or category, a pair that
   joins a node to itself, or a repeated pair.
2. Validate the assembly measurements: pair, resistance, measurement
   method, test voltage where one applies. Reject a negative
   resistance, an unknown method, or a repeated pair.
3. Reconcile the two sets: report every declared pair with no
   measurement, and every measured pair the architecture never
   declared.
4. For each bonded pair, compare the reading with its category limit
   under the named resistance tolerance, and flag a reading taken with
   a two-wire method on a limit finer than that method can resolve.
5. For each isolated pair, separate the two failure modes -- a reading
   near zero is an unintended connection, a reading between there and
   the floor is degraded isolation -- and check that the test voltage
   was recorded and reached the minimum.
6. Group the declarations by power domain and hold each to exactly one
   bonded structure reference.
7. Report every pair with its intent, category, reading and method, the
   non-compliant pairs, and the finding list.

## Pitfalls

- Reading a milliohm bond with a two-wire meter. The number that comes
  back is mostly lead resistance, and it is usually accepted because it
  happens to sit under the limit.
- Holding every bond to one resistance figure. The categories exist
  because a lightning path and a signal reference do different jobs;
  one figure either fails half the joints or passes the wrong ones.
- Treating a near-zero isolation reading as a bad measurement. It is a
  connection, and the architecture has to be corrected rather than the
  reading repeated until it is higher.
- Accepting an isolation figure with no test voltage behind it. The
  barrier resistance moves with the applied voltage, so an unstated
  voltage makes the figure unfalsifiable.
- Measuring only what the architecture declared. The pair nobody drew
  is exactly the one that closes a ground loop, and a measurement plan
  built solely from the diagram can never find it.
- Letting a power domain acquire a second structure reference during
  integration. Each one looks harmless on its own; together they are
  the loop the single-point architecture existed to avoid.

## Behavior contract (gate 3)

The declaration and measurement validation, pair reconciliation,
continuity grading against the category limits, two-wire resolution
refusal, isolation floor and short separation, test-voltage check and
single-point structure-reference check are exercised by the gate 3
contract test:
scripts/test_e2007_system_grounding_isolation_tests.py against
scripts/e2007_system_grounding_isolation_tests_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_system_grounding_isolation_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
