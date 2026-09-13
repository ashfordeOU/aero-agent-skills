---
name: e2006-secondary-arc-description
description: "Use when identify which family a secondary-arc on a photovoltaic solar-array belongs to and how far the clause-7 provisions of ECSS-E-ST-20-06C reach: separate a non-sustained flashover of stored surface-charge from a temporary-sustained and a permanent-sustained arc using the event duration and how it ended, determine whether an array site (cell-to-cell-gap, string-to-string-gap, cell-interconnect, coverglass-edge, array-bus-bar) is plasma-exposed and generator-fed enough for the provisions to reach it, evaluate the arc-sustaining threshold potential from string-current, conductor-gap and site-condition, and size the capacitive flashover-energy against the site damage-limit. Trigger: ecss, e-st-20-electrical-scope, e2006-secondary-arc-description, secondary-arc-phenomenology, sustained-arc, non-sustained-arc, arc-sustaining-threshold, string-to-string-gap, flashover-energy, primary-discharge-trigger."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-secondary-arc-description, secondary-arc-phenomenology, sustained-arc, non-sustained-arc, arc-sustaining-threshold, string-to-string-gap, flashover-energy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Secondary Arc Description (space-systems/ecss/e2006-secondary-arc-description)

Use when the task is the ECSS-E-ST-20-06C clause 7.1 description of
secondary arcs on a photovoltaic array -- what separates a sustained arc
from a non-sustained one, and which parts of the array the clause 7
provisions actually govern.

## Domain quick reference

- A secondary arc is the second stage of a two-stage event. The primary
  event is an electrostatic discharge at a triple-junction, which
  produces a short-lived local plasma. The secondary arc is what happens
  next: if the generator can drive current through that plasma between
  two conductors at different potentials, the discharge continues after
  the primary event has finished.
- Three families follow from how the event ends. A non-sustained arc is
  a flashover of the stored surface-charge that stops on its own once
  that charge is spent, typically within a millisecond, with the
  generator never taking it over. A temporary-sustained arc is fed by
  the generator after the primary event and then extinguishes on its
  own. A permanent-sustained arc continues until the string is
  disconnected or the bus is removed, and normally destroys the site.
  Any event that ends by external action belongs to the permanent
  family regardless of how long the record is.
- The clause 7 provisions reach a site only where all of the conditions
  hold: the site is an exposed array surface (cell-to-cell-gap,
  string-to-string-gap, cell-interconnect, coverglass-edge, panel-edge
  conductor, array-bus-bar rather than an encapsulated harness or an
  equipment interior), ambient plasma can reach it to trigger the
  primary event, the potential across the site is above the
  arc-sustaining floor, and the generator behind the site can supply a
  current able to feed an arc.
- The arc-sustaining threshold is a decreasing function of available
  string-current -- a high-current string sustains an arc at a much
  lower gap potential than a low-current one -- and is corrected for
  the conductor-gap width and for site condition. A contaminated gap
  and, far more strongly, a carbonized-track from a previous event both
  lower the potential at which an arc keeps burning.
- A non-sustained flashover still deposits the capacitive energy stored
  at the site (half the site capacitance times the square of the
  potential). That energy is compared against a site damage-limit; it is
  the quantity that decides whether "non-sustained" also means
  "harmless".
- Clause 7.1 is descriptive: its output is the family of each event, the
  applicability of the provisions per site, and the provisions a
  credible sustained arc imposes -- not a qualification verdict, which
  belongs to the campaign clauses.

## Workflow

1. For each recorded discharge event, read the duration and the
   termination. An externally terminated event is permanent-sustained; a
   self-terminated event within the flashover duration is non-sustained;
   a longer self-terminated event is temporary-sustained. Reject an
   unrecognized termination before categorising.
2. For each adjacent-conductor pair on the array, decide whether the
   clause 7 provisions apply: array surface, plasma access, potential
   above the arc-sustaining floor, and enough string-current to feed an
   arc. A pair failing any one of those is recorded with the reason,
   not silently dropped.
3. For each applicable pair, evaluate the arc-sustaining threshold from
   the string-current, then correct it for the conductor-gap width and
   the site condition.
4. Compare the pair potential against that corrected threshold. At an
   exact-equality boundary the arc is credible: absorb the
   representation error in the comparison rather than reading a
   borderline pair as safe.
5. Where the pair is not credible for a sustained arc, size the
   capacitive flashover-energy and compare it against the site
   damage-limit.
6. Aggregate per section: the section is clear only when no pair is
   credible for a sustained arc and no recorded event fell in a
   sustained family; otherwise emit the provisions each finding
   imposes.

## Pitfalls

- Reading "the arc stopped" as non-sustained. An arc that stopped
  because the string was disconnected is a permanent-sustained arc; the
  distinguishing fact is who ended it, not that it ended.
- Judging the sustaining threshold from potential alone. The threshold
  falls steeply with available string-current, so a parallel-string
  section can sustain an arc at a potential a single string could not.
- Applying the provisions to an encapsulated harness or an equipment
  interior because the potentials look similar. Clause 7 addresses
  exposed array surfaces where ambient plasma can trigger the primary
  event.
- Treating a previously arced site as pristine. A carbonized-track
  markedly lowers the sustaining threshold, so a site that passed once
  can become credible after the first event.
- Treating non-sustained as harmless without sizing the stored energy.
  The capacitive flashover still deposits energy at the site, and a
  large site capacitance can carry it past the damage-limit.
- Widening the threshold to make a borderline pair pass. A pair sitting
  exactly on the threshold is credible for a sustained arc; only the
  floating-point representation error belongs in the comparison.

## Behavior contract (gate 3)

The event categorisation, provision-applicability decision,
arc-sustaining threshold interpolation, gap and site-condition
correction, flashover-energy sizing and section aggregation are
exercised by the gate 3 contract test:
scripts/test_e2006_secondary_arc_description.py against
scripts/e2006_secondary_arc_description_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_secondary_arc_description.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
