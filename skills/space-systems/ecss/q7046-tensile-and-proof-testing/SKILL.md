---
name: q7046-tensile-and-proof-testing
description: "Compute the proof load and the minimum ultimate tensile load a threaded fastener owes from its thread stress area and property class, then judge the measured results against them. Use when a fastener lot has been pulled on a tensile machine and someone has to say whether it passed: size the stress area from the nominal diameter and pitch, take the proof and ultimate stresses from the property class with its diameter split, check the permanent set left after the proof load, and separate a genuine strength failure from a test invalidated by a fracture in the grips or at the head fillet. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-proof-load-testing, fastener-tensile-acceptance-load, fastener-thread-stress-area, fastener-permanent-set-limit, fastener-fracture-location-acceptance."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-tensile-and-proof-testing, fastener-proof-load-testing, fastener-tensile-acceptance-load, fastener-thread-stress-area, fastener-permanent-set-limit, fastener-fracture-location-acceptance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Tensile and Proof Load Testing (space-systems/ecss/q7046-tensile-and-proof-testing)

Use when the task is the tensile and proof-load part of the testing
clause of ECSS-Q-ST-70-46: turning a nominal thread and a property
class into the two loads a fastener has to survive, and turning a
machine reading into an accept, a reject or a repeat.

## Domain quick reference

- Both acceptance loads come from the same geometry. The thread stress
  area is formed from the nominal diameter reduced by a fixed multiple
  of the pitch; it is neither the nominal shank area nor the minor
  diameter area, and using either of those moves the acceptance load by
  several percent in the unconservative direction.
- The proof load and the minimum ultimate load are different tests with
  different verdicts. The proof load is a non-destructive check that the
  fastener does not yield: it is applied, held and released, and the
  fastener passes only when the length it returns to is within the
  permanent-set limit of the length it started at. The tensile test is
  destructive and asks only what load the fastener broke at.
- Property class fixes both stresses, and for the common carbon-steel
  class the proof stress steps with diameter. A class table without that
  diameter split quietly under-states the proof load of the larger sizes.
- Where the fracture happened decides whether the number means anything.
  A break in the free threaded length or the plain shank is a valid
  result. A break inside the grips is an artefact of the fixture and
  invalidates the test, so the specimen is replaced rather than counted
  as a failure. A break at the head-to-shank fillet or in the thread
  run-out is a real defect verdict even when the load reached was high.
- Acceptance at the limit is a representation question. A breaking load
  that lands on the minimum ultimate load passes, and it must pass on
  every machine, so the comparison carries a named relative tolerance
  instead of a bare strict inequality.
- A lot is judged on its worst valid specimen, not on the mean. Averaging
  lets one strong specimen carry a weak one, which is the opposite of
  what a minimum-strength requirement says.

## Workflow

1. Validate the geometry: positive nominal diameter, positive pitch, and
   a pitch small enough against the diameter that the stress area stays
   positive. A non-positive area is an input error, not a zero load.
2. Form the thread stress area from diameter and pitch.
3. Take the proof stress and the minimum ultimate stress from the
   property class, applying the diameter split where the class has one.
   Refuse an unlisted class rather than defaulting to the weakest.
4. Multiply each stress by the stress area to get the proof load and the
   minimum ultimate load in newtons.
5. Judge each proof test: the applied load must reach the required proof
   load, and the permanent set measured after release must stay within
   the limit. Both conditions carry the tolerance; neither is relaxed.
6. Judge each tensile test: categorize the fracture location first, set
   an in-grip break aside as invalid, then compare the breaking load
   with the minimum ultimate load.
7. Roll the specimens up: report the worst valid specimen, the count of
   invalid specimens to be repeated, and refuse a verdict on a set with
   no valid specimen left in it.

## Pitfalls

- Using the shank area instead of the thread stress area. The thread is
  where the fastener breaks, and the shank area over-states the
  acceptance load so a weak lot reads as strong.
- Reading the proof test as a load test only. A fastener that took the
  load and came back longer has yielded; the permanent set is the result
  and the load alone is not.
- Counting an in-grip fracture as a failure. That specimen tested the
  fixture, and recording it as a strength failure argues a good lot into
  a reject.
- Accepting a head-fillet fracture because the load was high. The load
  reached says nothing about a defect that put the break outside the
  threaded length.
- Comparing a computed load with a strict inequality. The stress area is
  a float and the boundary case lands on it; the comparison needs the
  named tolerance or the same lot passes on one machine and fails on
  another.
- Judging the lot on the mean breaking load. The requirement is a
  minimum, so the worst valid specimen is the one that answers it.

## Behavior contract (gate 3)

The stress-area geometry, the property-class stresses with their
diameter split, proof-load and ultimate-load derivation, the
permanent-set check, fracture-location handling and the lot roll-up are
exercised by the gate 3 contract test:
scripts/test_q7046_tensile_and_proof_testing.py against
scripts/q7046_tensile_and_proof_testing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_tensile_and_proof_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
