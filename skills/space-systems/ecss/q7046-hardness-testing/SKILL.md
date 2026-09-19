---
name: q7046-hardness-testing
description: "Evaluate a set of hardness readings taken on a threaded fastener lot against the band its property class allows, on whichever scale the reading came off. Use when hardness numbers have come back from the lab and someone has to say whether the lot was heat treated correctly: convert the readings onto one scale by interpolating the tabulated curve, confirm the indentation was valid for the section it was put in, compare the spread against the band, and separate a core hardness fault from a decarburized or over-carburized surface. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-hardness-band, fastener-hardness-scale-conversion, fastener-surface-versus-core-hardness, fastener-decarburization-check, fastener-indentation-validity."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-hardness-testing, fastener-hardness-band, fastener-hardness-scale-conversion, fastener-surface-versus-core-hardness, fastener-decarburization-check, fastener-indentation-validity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Hardness Testing (space-systems/ecss/q7046-hardness-testing)

Use when the task is the hardness part of the testing clause of
ECSS-Q-ST-70-46: deciding whether a lot of fasteners sits inside the
hardness band its property class allows, on a reading that may have
come off a Vickers, Rockwell or Brinell machine.

## Domain quick reference

- The band has a floor and a ceiling, and the ceiling matters as much
  as the floor. Too soft means the heat treatment did not reach the
  strength the class promises; too hard means low ductility and, in a
  plated fastener, a raised susceptibility to delayed failure under
  sustained load.
- Readings only compare on one scale. A Rockwell number and a Vickers
  number are different measurements of different indenters and only map
  onto each other through a tabulated curve for the material family.
  That curve is interpolated between its points, never extrapolated
  past its ends: outside the tabulated span the relation changes shape,
  so the correct response is to refuse the conversion.
- An indentation is only a hardness measurement if the material under
  it was thick enough to contain it. The Vickers diagonal follows from
  the load and the hardness itself, so the minimum section is a
  function of both, not a fixed number; a reading taken on a thin
  thread crest with a heavy load measures the anvil as much as the part.
- Brinell has a ceiling of its own. Above roughly the mid-400s in
  Vickers the ball indenter flattens, so a Brinell reading on a hard
  fastener is not a valid measurement at all.
- Surface and core are two results, not one. The surface may be softer
  than the core when carbon was lost during heat treatment, or harder
  when it was picked up; both are process faults, and both are found by
  the difference rather than by either number alone.
- A wide spread within one lot is a finding even when every reading
  sits inside the band. It says the furnace load was not uniform, and
  the next lot from the same furnace may not be as lucky.

## Workflow

1. Validate the scale and the readings: at least three readings, every
   one a positive number. A single reading is a data point, not a lot
   result.
2. Convert every reading to the common scale by interpolating the
   tabulated curve, refusing any reading outside its span rather than
   extending the curve to reach it.
3. Confirm the method was valid for the part: the load is one the scale
   supports, the section is thicker than the indentation it has to
   contain, and the scale itself is usable at that hardness.
4. Take the band for the property class and compare the minimum and the
   maximum converted reading against its floor and ceiling, absorbing
   representation error at the boundary with a named tolerance rather
   than by widening the band.
5. Compute the spread across the readings and raise a uniformity
   finding when it exceeds the allowance, separately from the band
   verdict.
6. Where a surface and a core reading are both available, take their
   difference and report carbon loss or carbon pick-up by name.
7. Give one verdict, and let it say which of the three things failed:
   the band, the method, or the surface condition.

## Pitfalls

- Comparing a Rockwell reading directly with a Vickers band. The numbers
  are not on the same axis, and the comparison silently passes lots that
  the band excludes.
- Extending the conversion curve past its tabulated ends to keep an
  outlying reading in the set. That invents data at exactly the reading
  the lot will be judged on.
- Treating the minimum section as a constant. It follows from the load
  and the hardness through the indentation size, so a load that is
  valid on a shank is not automatically valid on a thread crest.
- Averaging the readings and judging the mean. The band applies to every
  reading; a mean inside the band can hide one that is outside it.
- Reading a soft surface as a soft lot. A decarburized skin over a
  correctly hardened core is a surface process fault with a different
  remedy, and it is only visible in the difference.
- Passing a lot with a wide spread because every reading fits. The
  spread is evidence about the furnace, and it belongs in the report
  whatever the band verdict is.

## Behavior contract (gate 3)

The band table, the interpolated scale conversion with its refusal
outside the tabulated span, indentation and section validity, the
spread allowance, the surface-versus-core difference and the combined
verdict are exercised by the gate 3 contract test:
scripts/test_q7046_hardness_testing.py against
scripts/q7046_hardness_testing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7046_hardness_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
