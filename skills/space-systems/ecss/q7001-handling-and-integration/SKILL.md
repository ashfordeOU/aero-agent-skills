---
name: q7001-handling-and-integration
description: "Plan clean handling and integration for exposed flight hardware and grade the plan against a fallout allocation. Use when a sensitive surface is about to be uncovered on the integration floor and the gloves, covers, tooling, orientation and exposure time all have to be settled before the first contact. Converts the airborne concentration and the way the surface faces into an obscuration accumulation rate, computes the uncovered hours the allocation pays for, compares that with the planned open time, sizes the glove pairs the contact count needs, refuses tooling with no cleaning record or an unapproved lubricant, and flags an aperture left open and a surface left facing up. Trigger: ecss, q-st-70-01, clean-handling-practice, particle-fallout-allocation, glove-change-interval, aperture-protective-cover, tooling-cleanliness-record."
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
  tags: [ecss, q-st-70-cleanliness-control-scope, q7001-handling-and-integration, clean-handling-practice, particle-fallout-allocation, glove-change-interval, aperture-protective-cover, tooling-cleanliness-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Control — Handling and Integration (space-systems/ecss/q7001-handling-and-integration)

Use when the task is uncovering flight hardware on an integration floor
— deciding how long the surface may stay open, which way it faces, how
many glove pairs the job consumes, and which tooling is allowed near
it — and then grading that plan against the fallout it will cost.

## Domain quick reference

- Exposure is a budget, not a consequence of the shift length. An
  uncovered sensitive surface accumulates fallout at a rate set by the
  airborne concentration around it, so the hours it may stay open
  follow from the allocation and are known before the cover comes off.
- Orientation is a design variable. A surface facing up collects what
  settles; the same surface turned vertical collects a fraction of it,
  and facing down a small fraction again. Turning the hardware is
  almost always cheaper than finding a cleaner room.
- Gloves are consumables with a contact count. Transfer rises as a pair
  is worn, so the number of pairs the task needs falls out of the
  contacts it makes, and any contact with a non-clean surface ends that
  pair immediately whatever the count says.
- Covers exist to shrink the window. An aperture opened at the start of
  a shift for a task that needs ten minutes spends the whole allocation
  for nothing, and nothing in the record afterwards shows where it
  went, so the open time is planned and compared separately from the
  task time.
- Tooling enters like any other material: with a cleaning record, and
  with a lubricant approved for use near the surface. A clean tool
  carrying an unapproved grease is the commoner failure and the one
  that survives the visual check.
- The model that turns concentration into deposition is declared as one
  coefficient so a reviewer can argue with a single number. A hidden
  chain of factors cannot be argued with and is inherited by the next
  programme regardless of whether it fits.

## Workflow

1. Validate the operation: orientation, obscuration allocation, planned
   task hours, the hours the cover is actually off, the contact count
   and the glove pairs planned.
2. Take the airborne concentration from the area, either declared
   directly or evaluated from the clean-area class at a threshold size.
3. Turn concentration and orientation into an obscuration accumulation
   rate through the declared deposition coefficient.
4. Divide the allocation by that rate to get the uncovered hours the
   budget pays for, treating a particle-free area as unbounded rather
   than as zero.
5. Compare the planned open time with the affordable hours, and
   separately with the task time, so an aperture left open beyond its
   task is a finding of its own.
6. Size the glove pairs from the contact count and the pair life, add
   one pair per contact with a non-clean surface, and compare with what
   was planned.
7. Screen tooling for cleaning records and for lubricants outside the
   approved list, naming each tool.
8. Compare the area class with what the operation requires, and report
   the verdict, the accumulated obscuration, the allocation consumed
   and every finding.

## Pitfalls

- Planning exposure by the shift. The surface is open for eight hours
  because that is how long people were in the room, and the budget it
  spent is discovered at the end-item cleanliness verification.
- Leaving the hardware facing up because that is how it sits on the
  trolley. It is the worst orientation available and it was chosen by
  nobody.
- Counting glove changes by time. A pair is consumed by contacts, and a
  two-hour task with sixty contacts wears out gloves a four-hour task
  with ten does not.
- Timing the cover by the task and not by the aperture. The task took
  ten minutes; the cover was off for the morning; only the ten minutes
  is in the procedure.
- Admitting a tool on how it looks. The missing cleaning record and the
  workshop grease both pass a visual check, and only one of them is
  visible afterwards on the hardware.
- Burying the deposition model in a spreadsheet. The number cannot be
  challenged, and the next programme inherits a coefficient derived for
  a different room.

## Behavior contract (gate 3)

Orientation scaling, the concentration-to-fallout rate through the
declared coefficient, the affordable exposure with its unbounded case,
the open-aperture and facing-up findings, glove-pair sizing including
the non-clean contact rule, tooling cleaning records and lubricant
approval, and the area-class comparison are exercised by the gate 3
contract test: scripts/test_q7001_handling_and_integration.py against
scripts/q7001_handling_and_integration_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_handling_and_integration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
