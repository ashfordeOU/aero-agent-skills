---
name: q7026-crimp-inspection
description: "Evaluate a finished crimp against its dimensional and visual acceptance limits. Use when completed crimps have to be dispositioned and a characteristic may simply not have been read: grade height and width against their own two-sided bands, size the flash extruded at the die parting line, confirm a bell mouth is formed and inside its length band where the contact calls for one, count the strands that can be seen, check the insulation grip closed on the jacket, and hold an unread characteristic at review rather than letting it pass. Trigger: ecss, q-st-70-26-crimping, crimp-height-and-width-band, crimp-die-flash-limit, crimp-bell-mouth-length-band, crimp-strand-visibility-count, crimp-unread-characteristic-review."
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
  tags: [ecss, q-st-70-26-crimping, q7026-crimp-inspection, crimp-height-and-width-band, crimp-die-flash-limit, crimp-bell-mouth-length-band, crimp-strand-visibility-count, crimp-unread-characteristic-review]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Crimp Inspection (space-systems/ecss/q7026-crimp-inspection)

Use when the Quality clause of ECSS-Q-ST-70-26 is the task at the
inspection bench: dispositioning finished crimps on the characteristics
that can be read from the outside, and separating the ones that failed
from the ones that were never read.

## Domain quick reference

- A finished crimp is not adjustable, so inspection decides whether the
  joint stays in the harness. Nothing here improves a crimp; it only
  finds the ones that have to come off.
- An unread characteristic is not a passing one. A crimp with no width
  measurement and no flash measurement is not an accepted crimp with two
  blanks on the sheet, it is a crimp whose closure nobody verified, and
  it sits at review until somebody reads it.
- Height and width are the same closure seen on two axes. A height
  inside the band with a width outside it is a barrel that rolled in the
  nest instead of closing, and the height alone cannot see that.
- Height fails in two opposite directions. Below the band the barrel was
  driven into the strands and cut them; above it the barrel never closed
  and the joint is mechanical rather than a cold weld.
- Flash is material that left the joint. The section it came out of is
  gone from the crimp and the edge it leaves is loose metal geometry
  inside a sealed assembly, so it is graded even when the height passes.
- The bell mouth carries the strain relief that no dimension shows. Its
  absence is a finding on a contact that calls for one, and an over-long
  flare is a different finding: the flare has eaten into the gripped
  length.
- Not every contact carries a bell mouth requirement. A splice barrel
  graded against a flare band it was never designed to have fails for a
  reason that belongs to the inspector, not the part.
- Strand visibility is design-dependent. Where a window or an exposed
  conductor end lets the strands be counted, a shortfall is a rejection;
  where the design hides them, the same shortfall cannot be resolved
  from outside and the crimp goes to review, not to acceptance.

## Workflow

1. Validate the limits table: two-sided height, width and bell mouth
   bands whose maxima are not below their minima, a flash limit, a
   bell mouth requirement flag and a positive strand count.
2. Take the entry for the contact in hand, refusing an untabulated part
   rather than borrowing a neighbour's limits.
3. Grade height and width separately against their own bands, and
   report which side each fell on and where inside the band it sits.
4. Grade the flash against its limit and the bell mouth against its
   band, taking the no-requirement case as an explicit statement rather
   than a silent pass.
5. Count the visible strands against the strand count, and split the
   shortfall by whether the design lets them be seen at all.
6. Check the insulation grip closed on the jacket.
7. Take the worst of the six, name every check sitting at that level,
   list the characteristics that were never read, and roll the
   population up with the crimps that carry an unread characteristic
   named separately from the ones that failed.

## Pitfalls

- Recording a blank as a pass. A characteristic with no reading is the
  most common way a rejectable crimp is accepted, because the summary
  counts findings and a blank produces none.
- Measuring height and skipping width. Height alone passes a barrel
  that rolled in the nest and closed on a diagonal.
- Reading height as a single-sided limit. A check written one way round
  passes every barrel that never closed on the bundle.
- Treating flash as cosmetic. It is section that left the joint and an
  edge left behind in the assembly.
- Grading a splice barrel against a bell mouth band. A contact with no
  flare requirement has no flare to measure, and the finding belongs to
  the inspection setup.
- Accepting an absent bell mouth because every dimension passed. The
  dimensions do not see the load path the flare carries.
- Turning a strand shortfall on a blind contact into an acceptance
  because it could not be counted. The shortfall was observed; what is
  missing is the means to resolve it.
- Rolling a population up on the failure count alone. A lot with forty
  accepted crimps and twelve unread characteristics is not a lot with
  forty accepted crimps.
- Comparing a height, a width, a flash or a flare length with its limit
  by bare arithmetic. A value specified to land exactly on the limit can
  evaluate a few units in the last place past it after a unit
  conversion, so the comparison absorbs that representation error while
  the limit stays untouched.

## Behavior contract (gate 3)

The limits table validation and its refusal of an untabulated contact,
the separate two-sided height and width grading, the flash limit, the
bell mouth band including the not-required and not-read cases, the
strand visibility count with its blind-contact split, the insulation
grip check, the unread-characteristic review outcome, the per-crimp
worst disposition and the population rollup that names unread and failed
separately are exercised by the gate 3 contract test:
scripts/test_q7026_crimp_inspection.py against
scripts/q7026_crimp_inspection_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7026_crimp_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
