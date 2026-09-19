---
name: q7026-wire-stripping-and-prep
description: "Verify a stripped wire end against the crimping preparation requirements before the contact goes on. Use when conductors have been stripped for a high-reliability crimp and each end needs a disposition: compare the exposed length with the band for its own gauge, count nicked strands and severed strands against their separate allowances, read birdcaging, contamination and insulation damage, refuse a solder-tinned conductor and a stripping method outside the qualified set, offer rework only where wire length remains, then roll the lot up. Trigger: ecss, q-st-70-26-crimping, crimp-wire-strip-length-band, crimp-strand-nick-allowance, crimp-conductor-birdcage-check, crimp-tinned-conductor-refusal, crimp-strip-tool-calibration."
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
  tags: [ecss, q-st-70-26-crimping, q7026-wire-stripping-and-prep, crimp-wire-strip-length-band, crimp-strand-nick-allowance, crimp-conductor-birdcage-check, crimp-tinned-conductor-refusal, crimp-strip-tool-calibration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Wire Stripping and Preparation (space-systems/ecss/q7026-wire-stripping-and-prep)

Use when the Preparation clause of ECSS-Q-ST-70-26 is the task: deciding
whether a stripped conductor is fit to be crimped, before any contact is
placed on it and before any tool closes.

## Domain quick reference

- A crimp is a cold weld, so every defect that will ever limit the joint
  is already in the wire end before the tool closes. Nothing downstream
  inspects the strands that the blade cut, because the barrel hides
  them.
- Strip length is a two-sided band, not a target. Short leaves the
  barrel part-filled, so the compression the die applies lands on fewer
  strands than the band assumed. Long leaves bare conductor between the
  insulation and the barrel, unsupported by either.
- Every number here is per gauge. The strip band, the strand count and
  both damage allowances move with the wire, so an end is only ever
  compared with its own gauge entry, and a gauge the table skips has no
  band. The entry between two tabulated neighbours is not their average.
- Nicked and severed strands are different losses and carry different
  allowances. A nick is a stress raiser that work-hardens and parts
  under vibration months later; a severed strand is conductor that the
  joint never receives at all.
- Birdcaging and contamination are recoverable, and insulation damage
  and tinning are not. A birdcaged bundle can be re-laid and a dirty
  conductor cleaned, but damage on the insulation that stays in the
  harness and solder inside the crimp zone both travel with the wire.
- A solder-tinned conductor is not crimped. Solder creeps under the
  sustained barrel pressure and the joint that measured correctly at
  inspection relaxes into a resistive contact in service.
- Rework has a length cost. Cutting an end back and stripping it again
  consumes wire, so an end can be recoverable in principle and
  unrecoverable in this harness because the routed length is gone.
- An unqualified stripping method or a lapsed tool calibration voids the
  measurements rather than failing the wire. The end may be perfect; the
  record is not evidence.

## Workflow

1. Validate the gauge table: a two-sided strip band whose maximum is not
   below its minimum, a positive strand count and two damage allowances
   that stay below it. An allowance that reaches the strand count is not
   an allowance.
2. Take the entry for the end's own gauge, refusing an untabulated gauge
   rather than interpolating a band between its neighbours.
3. Grade the exposed length against the band, report which side it fell
   on and where inside the band it sits, and decide rework against
   reject on the wire margin that a re-strip needs.
4. Count the strands in the bundle against the gauge, then the nicked
   and the severed against their own allowances. Refuse a bundle count
   that disagrees with the gauge and damage totals larger than the
   bundle, because both mean the record is inconsistent.
5. Read the conductor form and cleanliness: birdcaging and contamination
   into rework, insulation damage and tinning into rejection.
6. Check the stripping method against the qualified set and the tool
   calibration against its due date; a tool due today is still current.
7. Take the worst of the four checks, name every check sitting at that
   level, prefix each finding with the check it came from, and roll the
   lot up with its accepted, rework and rejected counts plus the ends
   the record never covered.

## Pitfalls

- Treating strip length as a minimum. An over-long strip passes every
  downward check and leaves unsupported bare conductor where the harness
  flexes.
- Carrying one strip band across a mixed-gauge loom. The band that fills
  the heavier barrel overfills or underfills the lighter one.
- Interpolating a band for a gauge the table skips. Two tabulated
  neighbours do not imply the entry between them, and the joint would be
  graded against a number nobody accepted.
- Merging nicked and severed strands into one damage count. They fail by
  different mechanisms on different timescales and the allowances are
  deliberately different sizes.
- Reading birdcaging as cosmetic. A bundle that does not enter the
  barrel round is compressed unevenly, and the strands on the open side
  never reach the wall.
- Accepting a tinned conductor because the crimp measures correctly. The
  measurement is taken before the solder has crept.
- Offering rework without checking the wire that is left. An end that
  can be re-stripped in the abstract cannot always be re-stripped in a
  harness whose routed length is already cut.
- Reporting an end disposition from a tool whose calibration has lapsed.
  The wire may be sound; the numbers are not evidence about it.
- Comparing a strip length with a band edge, or a calibration interval
  with its due date, by bare arithmetic. A value specified to land
  exactly on the limit can evaluate a few units in the last place past
  it after a unit conversion, so the comparison absorbs the
  representation error while the limit stays untouched.

## Behavior contract (gate 3)

The gauge table validation and its refusal of an untabulated gauge, the
two-sided strip length grading with its rework margin, the separate
nicked and severed strand allowances, the conductor form and cleanliness
reading, the stripping method and calibration check, the per-end worst
disposition and the lot rollup with its completeness flag are exercised
by the gate 3 contract test:
scripts/test_q7026_wire_stripping_and_prep.py against
scripts/q7026_wire_stripping_and_prep_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7026_wire_stripping_and_prep.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
