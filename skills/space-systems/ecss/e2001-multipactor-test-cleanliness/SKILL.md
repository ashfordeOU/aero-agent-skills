---
name: e2001-multipactor-test-cleanliness
description: "Use when verify that the airborne-particle cleanliness required for multipactor-sensitive RF-hardware is held through assembly, multipactor-testing, delivery and hardware-handling under ECSS-E-ST-20-01C clause 6.1: convert each declared cleanroom-class into a monitored concentration-limit at the sampled particle-size, grade measured airborne-counts against that limit, confirm every lifecycle-phase declares a regime no coarser than the hardware requirement, estimate particulate fall-out onto the exposed critical-gap surfaces over the dwell, and report the containment-controls a phase has not declared. Trigger: ecss, e-st-20-01c, multipactor-test-cleanliness, airborne-particle-count, cleanroom-class-limit, particulate-fall-out, containment-controls, critical-gap-surface."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-test-cleanliness, multipactor-test-cleanliness, airborne-particle-count, cleanroom-class-limit, particulate-fall-out, critical-gap-surface]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Test Cleanliness (space-systems/ecss/e2001-multipactor-test-cleanliness)

Use when the task is the airborne-particle cleanliness control of
ECSS-E-ST-20-01C clause 6.1 -- holding the required particulate regime
across assembly, multipactor-testing, delivery and hardware-handling so
that the critical-gap region of an RF-item is not seeded with the
particles that trigger a premature multipactor discharge.

## Domain quick reference

- A cleanroom-class is a concentration ceiling, not a label. The class
  fixes the permitted airborne count at a reference particle-size and
  the ceiling falls off as the sampled size grows; a count is graded
  against the ceiling recomputed at the size actually sampled, never
  against the class number itself. A numerically larger class is the
  coarser (dirtier) room, so a phase satisfies a requirement when its
  class is at most the required class.
- Clause 6.1 spans the whole lifecycle, not the test bay alone. Four
  phases carry the regime: assembly, multipactor-testing, delivery and
  hardware-handling. Each declares its own class and its own
  containment controls (garment discipline, filtered-air supply,
  particle monitoring, chamber purge, double-bagging, purge-gas fill,
  seal records, tool-cleanliness records). The end-to-end regime is
  only as good as its coarsest declared phase, and a phase with no
  declaration is a gap, not a pass.
- Airborne concentration becomes a surface problem through fall-out.
  Particles settle at a near-constant speed in still air, so the count
  deposited per unit area over a dwell is concentration x settling
  speed x dwell, and the obscuration each particle contributes is the
  area of its own projected disc. That obscuration is what the
  critical-gap allowance is written against; the airborne number alone
  does not answer whether the gap is acceptable after a long exposure.
- A particle bridging or partly bridging the critical gap lowers the
  local breakdown threshold and seeds free electrons, which is why the
  cleanliness requirement is a multipactor requirement and not only a
  workmanship one.

## Workflow

1. Capture the hardware cleanliness requirement as a class plus the
   particle-size the programme samples at, and recompute the
   concentration ceiling at that size.
2. Collect the class declared for each of the four lifecycle phases,
   normalising phase aliases (integration to assembly, shipment to
   delivery, storage to hardware-handling). Reject an unrecognised
   phase and reject the same phase declared twice under two aliases.
3. Grade each phase's measured airborne count against the ceiling for
   that phase's own declared class. Treat a count equal to the ceiling
   as compliant.
4. Flag every phase declaring a class coarser than the requirement and
   every phase with no declaration at all.
5. Estimate fall-out onto the exposed critical-gap surface over the
   dwell the item actually spends open, and compare the resulting
   obscuration against the allowance.
6. For each phase, difference the declared containment controls
   against the controls that phase requires, and report the gaps.
7. Aggregate: the programme is not clause 6.1 compliant until the
   class profile, the counts, the fall-out estimate and the control
   declarations are all clear.

## Pitfalls

- Comparing a measured count against the ceiling for the reference
  particle-size when the programme samples at a larger size -- the
  ceiling is size-dependent and using the reference value passes
  counts that are several times over the real limit.
- Reading a larger class number as a stricter room. The ordering is
  inverted: the requirement is an upper bound on the class number.
- Grading only the test bay and crediting the whole lifecycle. Delivery
  and hardware-handling routinely dominate the accumulated fall-out
  because they last far longer than the chamber time.
- Treating a clean airborne number as a clean surface. A modest
  concentration held over a multi-day dwell can still exceed the
  critical-gap obscuration allowance; the dwell is part of the check.
- Letting an exact-boundary count read as a violation. A ceiling built
  from a power of ten and a count reassembled from partial samples can
  differ by a few units in the last place, so the comparison absorbs
  the representation error rather than widening the ceiling.
- Recording containment controls as free text and never differencing
  them against the required set -- an undeclared control is a finding
  in its own right, independent of any measured count.

## Behavior contract (gate 3)

The concentration-ceiling, measurement-grading, phase-profile,
fall-out and containment-control logic is exercised by the gate 3
contract test: `scripts/test_e2001_multipactor_test_cleanliness.py`
against `scripts/e2001_multipactor_test_cleanliness_logic.py`
(stdlib unittest, offline). Run:
python3 scripts/test_e2001_multipactor_test_cleanliness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
