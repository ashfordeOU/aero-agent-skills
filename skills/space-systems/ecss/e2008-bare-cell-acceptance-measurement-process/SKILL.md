---
name: e2008-bare-cell-acceptance-measurement-process
description: "Perform the bare-cell current recording of ECSS-E-ST-20-08C clause 7.3.2.2.2 so the two numbers survive the bench: read the irradiance and cell temperature the run sat at, check both against the standard illumination bands, confirm the load was held at the test voltage the drawing states, correct each short-circuit and on-load current back to reference irradiance and reference temperature, convert to current density, and catch a cell reporting more current on load than at short circuit. Use when a bare-cell acceptance run has to be made under a stated illumination. Trigger: ecss, e-st-20-08c-clause-7-3-2-2-2, bare-cell-short-circuit-current-recording, bare-cell-current-at-stated-test-voltage, standard-illumination-irradiance-correction, bare-cell-temperature-coefficient-correction, bare-cell-current-density, bare-cell-load-setpoint-tolerance."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-acceptance-measurement-process, bare-cell-short-circuit-current-recording, bare-cell-current-at-stated-test-voltage, standard-illumination-irradiance-correction, bare-cell-temperature-coefficient-correction, bare-cell-current-density, bare-cell-load-setpoint-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Bare Cell Acceptance Measurement Process (space-systems/ecss/e2008-bare-cell-acceptance-measurement-process)

Use when the task is clause 7.3.2.2.2 of ECSS-E-ST-20-08C -- recording,
for each bare cell under standard illumination, the current at short
circuit and the current at the on-load test voltage the drawing states.
The run is short and the record is what makes it worth anything: the
conditions the currents were taken under travel with them, or the
numbers cannot be compared with a drawing value or with the next bench.

## Domain quick reference

- The illumination is the measurement. A photovoltaic current is very
  nearly proportional to the irradiance falling on the cell, so a bench
  sitting a few per cent off the reference irradiance shifts every
  current it records by about the same few per cent, uniformly and
  invisibly.
- Correcting back to the reference irradiance is therefore arithmetic,
  not judgement: the reading scales by the ratio of reference to
  measured irradiance. What is not optional is recording the irradiance
  it was taken at, because the correction cannot be reconstructed
  afterwards from the current alone.
- Cell temperature matters in the other direction and by much less.
  Short-circuit current rises slowly as the cell warms and the bandgap
  narrows, so a warm cell reads high and the correction divides that
  rise back out. It needs the cell's own coefficient; a neighbour's
  coefficient is a different cell's property.
- The two currents are taken at two different points. The short-circuit
  current is the terminals shorted; the second is the load held at the
  voltage the drawing states. A setpoint that drifted off that voltage
  returns a current from a different point on the curve, and nothing in
  the number itself shows it.
- Current density, not current, is what compares across cell sizes. A
  larger cell gives more current for the same quality of material, so
  the illuminated area belongs in the record beside the two readings.
- One internal check catches the mislabelled or swapped channel: no
  cell delivers more current on load than it does with its terminals
  shorted, so a record that says otherwise is a wiring finding and not
  a cell finding.

## Workflow

1. Validate the conditions policy first: reference irradiance and its
   tolerance, reference cell temperature, the temperature band, and the
   load setpoint tolerance. An inverted band, or a reference
   temperature outside the band it anchors, is refused rather than used.
2. Read the irradiance and cell temperature the run sat at. A bench
   with no irradiance on record, or a reading taken with no cell
   temperature, is a record defect and is refused.
3. Check both against their bands before converting anything, and close
   on invalid conditions when either fails. Report both failures when
   both are present, so the bench is not repaired one finding at a time.
4. Read the stated on-load test voltage. When the drawing states none,
   close immediately -- the second current has no defined point on the
   curve to be taken at.
5. Compare the load setpoint against the stated voltage. A setpoint
   exactly on the tolerance is admissible; the comparison tolerance
   absorbs representation error rather than widening the requirement.
6. For each presented cell, read both currents, the temperature
   coefficient and the illuminated area, rejecting a duplicate cell
   identifier. Correct each current to reference irradiance and then to
   reference temperature, and derive the short-circuit current density.
7. Average the corrected currents over the presented cells and report
   that average even when the run is invalid, so the defect and the
   number it would have produced stay visible together.
8. Close on one verdict: illumination conditions invalid, test voltage
   not stated, test voltage setpoint off, cell readings inconsistent,
   or bare-cell currents recorded.

## Pitfalls

- Quoting a raw bench current as the cell's current. Without the
  irradiance correction it is a property of the lamp as much as of the
  cell, and two benches will not agree.
- Recording the corrected current and discarding the measured one. The
  correction cannot be audited or redone under a revised coefficient
  once the raw reading is gone, so both belong in the record.
- Applying a single temperature coefficient across a mixed lot. The
  coefficient is a property of the cell technology, and carrying one
  cell's value onto another quietly biases the whole population.
- Letting the load setpoint float to whatever the supply settled at.
  The stated voltage is the definition of the second reading; a
  setpoint a few tens of millivolts away is a different measurement
  wearing the same name.
- Comparing currents across cells of different area. The larger cell
  wins every time on current and may be the poorer material; the
  comparison belongs in current density.

## Behavior contract (gate 3)

The policy validation, illumination and temperature band checks, the
irradiance and temperature corrections and their composition, the
current density, the load setpoint tolerance, the short-circuit
consistency check, the corrected means and the process verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_acceptance_measurement_process.py against
scripts/e2008_bare_cell_acceptance_measurement_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_bare_cell_acceptance_measurement_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
