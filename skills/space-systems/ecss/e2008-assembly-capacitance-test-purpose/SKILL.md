---
name: e2008-assembly-capacitance-test-purpose
description: "Determine what a capacitance measurement on the strings of a photovoltaic assembly must deliver to characterise the dynamic electrical behaviour ECSS-E-ST-20-08C clause 5.5.3.5.1 is concerned with: combine the per-cell capacitance through the series string and the parallel strings into one assembly value, derive the displacement current, stored charge and switching time constant it drives, then check the planned bridge frequency lands inside the meter range and the measurement bias stands in for the working point. Use when scoping or reviewing a solar-array string capacitance characterisation. Trigger: ecss, e-st-20-08c, clause-5-5-3-5-1, solar-array-string-capacitance, photovoltaic-assembly-dynamic-behaviour, assembly-displacement-current-transient, capacitance-bridge-frequency-range, array-switching-time-constant."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-assembly-capacitance-test-purpose, solar-array-string-capacitance, photovoltaic-assembly-dynamic-behaviour, assembly-displacement-current-transient, capacitance-bridge-frequency-range, array-switching-time-constant]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Assembly Capacitance Test Purpose (space-systems/ecss/e2008-assembly-capacitance-test-purpose)

Use when the task is to state and defend why the capacitance of a
photovoltaic assembly's strings is measured under ECSS-E-ST-20-08C
clause 5.5.3.5.1 -- which dynamic electrical behaviours the number
feeds, whether the assembly carries enough capacitance for any of them
to matter, and whether the planned bridge measurement can actually
produce a value that describes the working point.

## Domain quick reference

- A solar cell is a large-area junction, so it is also a capacitor.
  Under steady illumination that is invisible; it only shows up when
  something changes -- a shunt regulator switching, an arc striking, a
  plasma sheath moving, a transient injected into the harness -- and
  each of those is a behaviour that needs the number in advance.
- Geometry decides the value. Cells in series divide the per-cell
  capacitance and strings in parallel multiply it, so a long string of
  a high-capacitance cell can end up with less assembly capacitance
  than a short one. Neither the cell datasheet nor the string count
  alone gives the figure the behaviours respond to.
- The measurement's whole output is three derived quantities: the
  displacement current a step in the working point pushes, the charge
  held and available to feed a switch or an arc, and the time constant
  the assembly presents to the source impedance it works into. Each is
  linear in the assembly capacitance, so an error in it propagates
  straight through to all three.
- Junction capacitance moves with bias. A value measured at zero bias
  is a correct measurement of a different operating point, and using it
  for a regulator that works at a hundred volts substitutes one number
  for another without any warning in the record.
- A bridge measures an impedance, not a capacitance. At the planned
  frequency the string has to present an impedance the meter can
  actually resolve; too low a frequency puts a small capacitance
  outside the range entirely and the reading is instrument noise.
- A capacitance too small to move any of the three quantities does not
  earn the measurement, however many behaviours are declared, and a
  declared behaviour with nothing planned is a distinct outcome from a
  planned measurement that cannot see the value.

## Workflow

1. Validate the characterisation policy first: significance trigger,
   meter impedance range and bias-offset allowance. A range whose
   ceiling is not above its floor is refused rather than used.
2. Group the declared dynamic behaviours, rejecting an unrecognised one
   rather than ignoring it, and map each to the quantity the
   capacitance measurement feeds it. Append the shared characterisation
   objective whenever any behaviour is present.
3. Combine the per-cell capacitance through the series count and the
   parallel string count into the assembly capacitance, and keep the
   single-string value alongside it -- the bridge measures a string,
   the behaviours respond to the assembly.
4. Derive the displacement current at the declared step rate, the charge
   stored at the working point, and the time constant into the declared
   source resistance. These are reported whatever the verdict, because
   they are what the number was wanted for.
5. Decide whether the characterisation is required at all: a declared
   behaviour present and an assembly capacitance at or above the
   significance trigger. A value landing exactly on the trigger earns
   the measurement; the comparison tolerance absorbs representation
   error and the trigger does not move.
6. When it is required and a measurement is planned, compute the string
   impedance at the planned frequency, check it against the meter range,
   and check the measurement bias stands close enough to the working
   point to describe it.
7. Close on one verdict: characterisation not required, measurement not
   planned, measurement inadequate, or dynamic behaviour characterised
   -- reporting every inadequacy found, not only the first.

## Pitfalls

- Quoting the cell capacitance as the assembly capacitance. The series
  division alone can be an order of magnitude, and the parallel
  multiplication pulls the other way, so the cell figure is almost never
  the one the regulator or the discharge analysis needs.
- Measuring at zero bias for convenience. It is a valid measurement of
  an operating point the assembly never works at, and nothing in the
  resulting number says so.
- Picking the bridge frequency from habit. The impedance the meter sees
  falls with frequency, so a frequency chosen for a different article
  can put this one below the meter floor or above its ceiling.
- Reporting a capacitance without the quantities it was wanted for. The
  displacement current, the stored charge and the time constant are the
  reason the measurement exists; the farad value on its own leaves every
  downstream analysis to redo the same arithmetic.
- Treating a declared behaviour as sufficient reason to test. A
  capacitance below the significance trigger cannot move any of the
  three quantities enough to matter, and the exposure buys nothing.

## Behavior contract (gate 3)

The policy validation, series and parallel capacitance combination, the
displacement current, stored charge and time constant, the bridge
impedance and range check, the bias representativeness check, the
behaviour inventory and objective mapping, and the purpose verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_assembly_capacitance_test_purpose.py against
scripts/e2008_assembly_capacitance_test_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_assembly_capacitance_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
