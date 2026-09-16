---
name: e2008-sca-front-contact-defects
description: "Use when a front contact has been inspected and the result needs grading. Evaluate whether the front contact metallisation of a solar cell assembly is free of interruptions and delamination under ECSS-E-ST-20-08C clause 6.4.3.1.7: walk each gridline and busbar out from its feed point, work out what metallisation is still tied to a terminal once a break is placed, roll the orphaned gridlines up into the current collection the cell has lost, add the delaminated metallisation the clause permits none of, and refuse to call a cell clean on a short record set or on an inspection too coarse to see the break it is looking for. Trigger: ecss, e-st-20-08c, clause-6-4-3-1-7, solar-cell-front-contact-continuity, front-contact-metallisation-interruption, front-contact-metallisation-delamination, gridline-busbar-feed-topology, front-contact-collection-loss-fraction."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-front-contact-defects, solar-cell-front-contact-continuity, front-contact-metallisation-interruption, front-contact-metallisation-delamination, gridline-busbar-feed-topology, front-contact-collection-loss-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- SCA Front Contact Defects (space-systems/ecss/e2008-sca-front-contact-defects)

Use when the task is the front contact screen of ECSS-E-ST-20-08C clause
6.4.3.1.7 -- holding the metallisation on the illuminated face of a
solar cell assembly free of interruptions and of delamination, and
saying what a break already found has cost.

## Domain quick reference

- A break matters for where it sits, not for how wide it is. A hairline
  interruption and a visibly missing millimetre of the same gridline
  orphan the same metallisation, because what is lost is everything on
  the far side of the break from the feed point.
- The busbar and the gridline are not peers. A gridline break costs the
  span beyond it on that one line; a busbar break costs every gridline
  whose feed point sits beyond it, so the cheapest-looking defect on the
  cell can be the one that takes a whole region out of collection.
- Delamination is not a milder interruption. Lifted metallisation may
  still conduct on the day it is found, so a continuity reading passes
  it; the clause permits none of it because the bond, not the circuit,
  is what has already gone.
- Delamination sitting over an interruption is worth naming separately.
  The lifted metallisation there is open as well as unbonded, and the
  two records describe one piece of damage rather than two.
- An absent record is not a clean one. A conductor list shorter than the
  declared one leaves the cell open however continuous the recorded
  conductors were.
- An inspection that cannot resolve the break it is looking for cannot
  support a statement that there is none. Detection capability is a
  precondition for an accept, not a caveat on it.
- A defect actually found closes the case on its own. Incompleteness and
  coarse resolution block an accept; they never soften a reject, because
  positive evidence of a break does not need a better instrument.

## Workflow

1. Validate the detection policy first: the break size that has to be
   visible must be a real positive length, or an accept means nothing.
2. Read each conductor record, grouping its defects into interruptions
   and delaminations and refusing an unrecognised kind, a repeated
   defect identifier or a position past the conductor end.
3. Work out the span of each conductor still tied to its feed point --
   the stretch between the nearest break below it and the nearest above,
   and nothing at all when a break sits on the feed point itself.
4. Resolve the topology: a gridline is live only when its own feed point
   falls inside the connected span of the busbar it meets. Reject a
   gridline that names a busbar the cell does not have.
5. Total the gridline length that stopped collecting, referred to the
   gridline length the cell started with, and the delaminated length
   against the metallisation as a whole.
6. Close on one verdict: reject on any interruption or delamination,
   inspection-incomplete on a short record set, detection-insufficient
   on an inspection too coarse, accept only when none of those hold.

## Pitfalls

- Grading a break by its width. Width is the easiest thing to measure
  and the least informative; the position relative to the feed point is
  what decides the cost.
- Treating every conductor as equivalent when totalling the damage. One
  busbar break beyond the terminal can outweigh breaks on several
  gridlines, and a count of interruptions hides that entirely.
- Letting a continuity reading stand in for the delamination check. The
  circuit can be closed across metallisation that has already lifted.
- Reading a collection loss off a partial conductor list. Unrecorded
  conductors contribute nothing to the loss and everything to the doubt.
- Accepting a cell because nothing was seen, without asking what the
  inspection could have seen. A clean reading from an instrument coarser
  than the required feature size is not a result.
- Comparing a feed position with a connected span by bare arithmetic. A
  feed point landing exactly on the end of a span can evaluate a few
  units in the last place outside it, so the comparison absorbs that
  representation error while the span itself stays untouched.

## Behavior contract (gate 3)

The detection policy validation, the connected-span computation, the
gridline and busbar feed topology, the collection-loss rollup, the
delamination total and the verdict precedence are exercised by the gate
3 contract test: scripts/test_e2008_sca_front_contact_defects.py
against scripts/e2008_sca_front_contact_defects_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_sca_front_contact_defects.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
