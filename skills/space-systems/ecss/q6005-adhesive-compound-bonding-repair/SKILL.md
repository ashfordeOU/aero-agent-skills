---
name: q6005-adhesive-compound-bonding-repair
description: "Assess whether an element may be reattached with bonding compound during permitted corrective work on a hybrid, under ECSS-Q-ST-60-05C clause 10.5.4. Use when a chip or passive has to be re-bonded into an opened unit with adhesive: date the compound against its storage life and the mixed material against its working life, derive the bond line from the dispensed volume and the footprint, interpolate the dwell the cure temperature actually needs, find the mounted elements that cure would overheat, and return permitted, permitted-with-conditions or not-permitted. Trigger: ecss, q-st-60-05c, hybrid-adhesive-bonding-repair, hybrid-bonding-compound-shelf-life, hybrid-adhesive-cure-schedule, hybrid-bond-line-thickness, hybrid-element-reattachment-compound."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-adhesive-compound-bonding-repair, hybrid-adhesive-bonding-repair, hybrid-bonding-compound-shelf-life, hybrid-adhesive-cure-schedule, hybrid-bond-line-thickness, hybrid-element-reattachment-compound]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Adhesive Reattachment During Repair (space-systems/ecss/q6005-adhesive-compound-bonding-repair)

Use when the task is clause 10.5.4 of ECSS-Q-ST-60-05C: sticking an element
back down with bonding compound while a hybrid is open for permitted
corrective work, and deciding beforehand whether the material, the joint and
the cure make that a repair the unit can be delivered with.

## Domain quick reference

- A bonding compound has two clocks and they measure different things. The
  storage life runs from manufacture and ends on a date; the working life
  runs from the moment the material is mixed and ends in minutes. A compound
  can be years inside its storage life and already dead on the bench.
- The bond line is not dispensed, it is implied. What the operator controls
  is the volume that goes down and the footprint it goes under; the thickness
  is the quotient, and it is the thickness the compound was qualified at.
  Starved joints fail in shear and flooded ones fillet out over the
  neighbouring geometry.
- A cure is a temperature and a dwell together, never one of them. The same
  compound reaches the same state in half an hour hot or four hours warm, and
  a schedule that lists points does not authorise the temperatures between
  them — the dwell between two points has to be interpolated, and below the
  coolest point the schedule says nothing at all.
- An under-cure looks finished. The element is held, the unit passes handling
  and the joint reaches its strength and its outgassing behaviour only later,
  or never. The completion ratio is the only thing that separates a cured
  joint from one that merely set.
- The cure is applied to the assembly, not to the joint. Every element
  already on the substrate sits in that oven too, so the repair's cure
  temperature is bounded by the lowest limit in the unit, which may be far
  below what the compound would prefer.
- Conductivity is a design property of the compound, not a detail. A silver
  filled compound under a part that has to float is a short waiting for the
  first thermal cycle, and no cure schedule fixes it.
- The outcome is three-way. A compound a few days from its date is usable
  with a record; one past it is not. Collapsing that distinction either
  scraps good material or puts undated material into flight hardware.

## Workflow

1. Validate the compound: an approved identity, a parsable storage-life date
   and a positive working life. A malformed date is an input error, not an
   expired compound — the two must not be conflated.
2. Date the material twice. Subtract the day of use from the storage-life
   date, and subtract the elapsed mixed time from the working life. Report
   both as signed quantities so how far past is visible, not just that it is.
3. Derive the bond line by scaling the dispensed volume before dividing by
   the footprint, and compare it with the qualified window under a tolerance
   so a nominal joint sitting exactly on a bound is inside it.
4. Size the cure: look the temperature up in the schedule, interpolating
   linearly between tabulated points, holding the hottest dwell above the
   hottest point and refusing outright below the coolest one. Divide the
   applied dwell by that to get the completion ratio.
5. Compare the cure temperature with every already-mounted element's limit
   and collect the ones it passes, naming them individually.
6. Sort the findings: an unapproved or expired compound, a spent working
   life, an uncleaned site, a bond line outside the window, an incomplete
   cure, an overheated neighbour and a conductive compound on a joint that
   must be isolated all block; a compound inside its caution window attaches
   a condition.
7. Return the disposition with every number that produced it, so the repair
   record carries the evidence rather than the verdict alone.

## Pitfalls

- Reading the storage-life date as the only date. The mixed material's
  working life is the clock that actually runs out during a repair, and it is
  measured from a time nobody writes down unless the procedure demands it.
- Dispensing to a volume and calling the bond line nominal. The thickness
  depends on the footprint as much as the volume, and the same dispense under
  a smaller part is a flooded joint.
- Comparing the bond line or the cure completion with a strict inequality. A
  nominal joint lands exactly on a window bound and a nominal cure lands
  exactly on a completion of one; without a tolerance the same repair is
  accepted on one machine and refused on another.
- Extrapolating the cure schedule downward. A schedule that starts at its
  coolest tabulated point says nothing about cooler cures, and inventing a
  dwell for one is guessing at chemistry.
- Checking the cure against the compound and not against the unit. The oven
  heats everything already mounted, and the binding limit is usually some
  small polymer-bodied part nobody thought about.
- Treating a nearly-expired compound the same as an expired one, in either
  direction. One is a recorded condition and the other is a refusal, and
  merging them costs either material or traceability.
- Recording the verdict without the numbers. A repair record that says the
  joint was acceptable cannot be re-examined after a field failure; one that
  carries the bond line, the dwell and the completion ratio can.

## Behavior contract (gate 3)

The compound validation, the storage and working life arithmetic, the bond
line derivation, the interpolated cure schedule and completion ratio, the
neighbourhood temperature check and the three-way disposition are exercised
by the gate 3 contract test:
scripts/test_q6005_adhesive_compound_bonding_repair.py against
scripts/q6005_adhesive_compound_bonding_repair_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_adhesive_compound_bonding_repair.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
