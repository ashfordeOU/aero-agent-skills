---
name: e2008-bus-bar-visual-inspection
description: "Screen a solar-array bus bar for the conditions that carry no allowance under ECSS-E-ST-20-08C clause 5.5.3.2.11: separate the not-tolerated findings - solder bridged across a design gap, a cracked bar, a lifted run, an opening filled solid - from the graded ones, turn a bridging call into a residual isolation gap and a blocked opening into the fraction of the opening still clear, scale splash, void, thin-fillet and contamination limits by the zone they sit in, and return accept, rework or reject with the not-tolerated identifiers named separately. Use when a bus bar has been examined and the record needs a disposition that a rework or a scrap decision can rest on. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-11, solar-array-bus-bar-inspection, bus-bar-solder-bridging-screen, bus-bar-blocked-opening-check, bus-bar-conductor-isolation-gap, not-tolerated-bus-bar-defects."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bus-bar-visual-inspection, solar-array-bus-bar-inspection, bus-bar-solder-bridging-screen, bus-bar-blocked-opening-check, bus-bar-conductor-isolation-gap, not-tolerated-bus-bar-defects, bus-bar-solder-splash-limits]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Bus Bar Visual Inspection (space-systems/ecss/e2008-bus-bar-visual-inspection)

Use when the task is the bus bar examination of ECSS-E-ST-20-08C
clause 5.5.3.2.11 -- the short list of bus bar conditions that are not
tolerated at all, sat next to the ordinary graded defects, and turned
into a disposition that a rework or a scrap decision can rest on.

## Domain quick reference

- The bus bar is the current path off the string. Everything the
  clause refuses is refused because it changes that path: a bridge
  puts continuity where the design needs isolation, a crack or a
  lifted run takes the path away, and a filled opening removes the
  clearance or the relief the opening was cut for.
- The screen has two halves and they must not be run with the same
  rule. A not-tolerated finding is decided by presence: there is no
  size below which it passes, so measuring it more carefully cannot
  change the answer. A graded finding is decided by measurement
  against a limit that the zone scales.
- Bridging is not the same question as encroachment. What is measured
  is the design gap between adjacent conductors less the solder spread
  from both sides. A residual gap of zero or less is a bridge and is
  refused; a residual gap that is positive but under the isolation
  minimum is solder creeping toward a bridge, and that is reworkable
  while the conductors are still apart.
- A blocked opening is graded on what stayed clear, not on what filled
  in. A nearly clear opening still does its job; an opening clear only
  in part can have the obstruction drawn back off the land; an opening
  filled solid is refused because clearing that much solder puts more
  heat into the bar than the surrounding joints survive.
- Where a graded defect sits changes its limit. A termination pad and
  the land around an opening carry tighter limits than an open
  conductor run, because splash and residue there sit on the feature
  the bar was made for.
- The bar verdict is the worst of its findings, but the not-tolerated
  identifiers are reported apart from the verdict. A reviewer reading
  a reject needs to know whether it came from a measurement that could
  be argued or from a condition that cannot.
- A clean bar still produces a record. The examination is the
  evidence, and an absent record is not the same as an absent defect.

## Workflow

1. Open the record against a bus bar identifier. A survey with no
   traceable identifier cannot be dispositioned, because the rework
   record has nothing to attach to.
2. Categorize every indication by kind and zone. Reject an
   unrecognized kind or zone rather than defaulting it to a
   neighbouring one and inheriting a limit that does not apply.
3. Route each indication to the half of the screen that governs it:
   presence for the not-tolerated kinds, measurement for the graded
   ones.
4. For a bridging call, take the design gap less the solder spread.
   Refuse a residual of zero or less; rework a positive residual under
   the isolation minimum; accept the rest.
5. For an opening, take the clear fraction against the opening area.
   Accept a nearly clear opening, rework a partly filled one, refuse
   one filled past the rework fraction.
6. For splash, voids, a thin fillet and contamination, scale the
   accept and rework limits by the zone factor and disposition on the
   measured area.
7. Close with the bar verdict, the not-tolerated identifiers listed
   apart, and the re-inspection duty a rework creates.

## Pitfalls

- Dispositioning a bridge by how large it is. The finding is the
  continuity, not the area; a bridge measured carefully is still a
  bridge and no zone factor reaches it.
- Treating encroaching solder as a bridge. The conductors are still
  apart, the residual gap is positive, and refusing the bar scraps a
  part that reflow would have saved.
- Grading a blocked opening on the obstructed area. Two openings of
  different sizes with the same blob in them are not the same finding;
  what governs is the fraction that stayed clear.
- Applying the conductor-run limit on a termination pad. The same
  splash there sits on the feature the bar exists to serve, and the
  limit that governs it is the tightened one.
- Reporting only a verdict. A reject from a measurement and a reject
  from a not-tolerated condition read the same on a summary line and
  lead to completely different recovery decisions.
- Comparing a measurement with a scaled limit by bare arithmetic. The
  limit is a product of a criteria value and a zone factor, so a
  measurement exactly on the limit can evaluate a few units in the
  last place above it; the comparison absorbs that representation
  error while the limit stays untouched.

## Behavior contract (gate 3)

The not-tolerated versus graded split, the residual isolation gap, the
clear-opening fraction, the zone-scaled area limits and the bar rollup
are exercised by the gate 3 contract test:
scripts/test_e2008_bus_bar_visual_inspection.py against
scripts/e2008_bus_bar_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bus_bar_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
