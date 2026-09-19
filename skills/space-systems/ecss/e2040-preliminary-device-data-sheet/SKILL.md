---
name: e2040-preliminary-device-data-sheet
description: "Draft the early device data sheet ECSS-E-ST-20-40C clause 5.4.5 puts in front of readers outside the development: group every characteristic, demand a unit on every numeric figure so a bare number cannot travel, hold each figure inside the range the sheet itself declares while letting a value landing exactly on a bound stay inside, refuse a figure called confirmed while its basis is still an estimate or a simulation, demand a plain description an outside reader can act on, and report the mandatory groups the sheet never filled instead of reading silence as nothing to say. Use when a preliminary data sheet is written or reviewed. Trigger: ecss, e-st-20-electrical-scope, preliminary-device-data-sheet, device-characteristic-group, preliminary-figure-maturity, characteristic-unit-discipline, declared-range-bound-check."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-preliminary-device-data-sheet, preliminary-device-data-sheet, device-characteristic-group, preliminary-figure-maturity, characteristic-unit-discipline, declared-range-bound-check, outside-reader-description]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Preliminary Device Data Sheet (space-systems/ecss/e2040-preliminary-device-data-sheet)

Use when the task is the early publication duty of ECSS-E-ST-20-40C
clause 5.4.5 -- producing or checking the short summary of device
characteristics that goes to readers who are not inside the
development, and who therefore cannot ask what a figure meant.

## Domain quick reference

- The audience is the whole point. The reader is designing something
  around this device and has no access to the model, the simulation
  log or the engineer. Every entry has to carry enough on its own
  line: a group, a figure, a unit, a range and a sentence.
- A numeric figure with no unit is the defect this check exists for. It
  reads fine in the sheet, it survives being copied into somebody
  else's budget, and it is wrong by whatever factor the reader
  assumed. Dimensionless figures carry a unit of 1 rather than nothing,
  so an absent unit always means an omission.
- The sheet declares its own ranges, so the figures can be checked
  against them without any outside source. A figure outside its
  declared range is either the wrong figure or the wrong range, and
  both have to be seen before the sheet leaves.
- A figure landing exactly on a declared bound is inside it. The bound
  is the commitment, so the comparison absorbs representation error: a
  value computed as a third landing on a third is within range, and a
  strict comparison is what rejects a compliant sheet.
- Maturity has to match the basis. At this phase almost everything is
  preliminary, and a figure called confirmed while it rests on an
  estimate or a simulation tells the outside reader it may be designed
  against. That is the one statement in the sheet that cannot be
  withdrawn later.
- A mandatory group nobody filled is reported as a gap, never read as
  nothing to say. The outside reader cannot distinguish a device with
  no environmental limits from a sheet whose environmental section was
  not written.

## Workflow

1. Resolve every characteristic: a unique name, a group folded onto a
   recognised one, a value, a unit, an optional declared range, a
   maturity and a basis. Refuse a repeated name or an unknown key as
   an input defect.
2. Report a numeric figure carrying no unit, counting a dimensionless
   figure as carrying the unit 1.
3. Check each numeric figure against its declared range, treating a
   value on a bound as inside and reporting only a genuine excursion.
4. Report a figure whose maturity is confirmed while its basis is an
   estimate or a simulation.
5. Report a characteristic with no plain description, since the
   outside reader has nothing else to read.
6. Report every mandatory group the sheet left empty.
7. Compute group completeness over the mandatory groups and compare it
   against the threshold, absorbing representation error and never
   widening the threshold itself.

## Pitfalls

- Publishing a bare number. It leaves the sheet correct and arrives in
  somebody else's budget scaled by whatever they assumed, and the
  error surfaces only at integration.
- Rejecting a figure that sits exactly on its declared bound. The bound
  is the commitment, and a strict comparison against a computed figure
  fails a sheet that is exactly on specification.
- Calling a simulated figure confirmed. The outside reader designs
  against it, and the word cannot be taken back once the sheet has
  been distributed.
- Reading an empty mandatory group as nothing to declare. The reader
  cannot tell an absent limit from an unwritten section, and will
  assume whichever one suits the design.
- Writing an entry that only the development team can read. An entry
  with no plain description is not published information; it is a note
  the authors already understood.

## Behavior contract (gate 3)

The characteristic resolution, group and maturity folding, unit
discipline, declared-range bound check with exact landings inside,
maturity-against-basis check, description requirement and the
group-completeness comparison are exercised by the gate 3 contract
test: scripts/test_e2040_preliminary_device_data_sheet.py against
scripts/e2040_preliminary_device_data_sheet_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_preliminary_device_data_sheet.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
