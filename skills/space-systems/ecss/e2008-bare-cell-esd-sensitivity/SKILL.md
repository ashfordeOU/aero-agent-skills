---
name: e2008-bare-cell-esd-sensitivity
description: "Use when sensitive cells are handled, packed or stored and the control set needs grading: group the cells by withstand voltage against the stated discharge model, grade every obliged control inside its own resistance band rather than merely present, check the packing shields rather than only dissipates, measure the storage envelope and the shelf life already spent, and turn residual charge into the voltage it delivers. Assess whether the handling and storage regime applied to electrostatic-discharge-sensitive bare solar cells keeps them under the voltage they survive, per ECSS-E-ST-20-08C clause 7.9.2. Trigger: ecss, e-st-20-08c, clause-7-9-2, bare-cell-esd-sensitivity-band, bare-cell-esd-protected-area-controls, bare-cell-esd-ground-path-resistance-band, bare-cell-esd-shielding-packaging, bare-cell-esd-storage-envelope."
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
  tags: [ecss, e-st-20-08-bare-solar-cell-scope, e2008-bare-cell-esd-sensitivity, e-st-20-08c-clause-7-9-2, bare-cell-esd-sensitivity-band, bare-cell-esd-protected-area-controls, bare-cell-esd-ground-path-resistance-band, bare-cell-esd-shielding-packaging, bare-cell-esd-storage-envelope]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells -- ESD-Sensitive Handling (space-systems/ecss/e2008-bare-cell-esd-sensitivity)

Use when the task is clause 7.9.2 of ECSS-E-ST-20-08C: a bare cell has
been judged sensitive to electrostatic discharge, and whether the way it
was handled, packed and stored actually kept the voltage it could see
below the voltage it is known to survive.

## Domain quick reference

- Sensitivity is derived, not declared, and it is derived against a named
  discharge model. The same withstand figure means a different band under
  a human-body, a charged-device and a machine model, because each one
  injects charge differently. A charged-device figure read as a
  human-body figure moves a cell whole bands down the ladder and every
  control obligation is then drawn from the wrong row, so the model is
  required rather than defaulted.
- The band drives the obligation, and the more sensitive bands inherit
  what the less sensitive ones owe and add to it. An ionizer is owed only
  where an insulator cannot leave the area at all; asking for it
  everywhere is as wrong as never asking.
- A control that is present and a control that works are different
  statements. A wrist strap is graded by its ground-path resistance, and
  that band has a floor as well as a ceiling: above the ceiling it is
  fitted and is not a ground; below the floor it is a personnel-safety
  defect rather than a better ground. A control can therefore fail by
  being too good a conductor, which a maximum-only check never sees.
- A control the band does not oblige is not evidence for one it does. An
  ionizer running in a moderate-band area does not pay for the wrist
  strap nobody wore.
- Packaging is graded on what it does to an external field, not on its
  own conductivity. Dissipative and conductive packing bleed their own
  charge and do not shield; only shielding packing carries a cell outside
  the protected area, and insulative packing charges by contact and is
  never a protection anywhere.
- Storage is a slow accumulation rather than an event. Humidity below the
  envelope tribocharges harder on every movement; humidity above it
  invites condensation and corrosion; and shelf life is consumed by
  elapsed days whether or not anything was ever observed.
- The arithmetic runs after the checklist, not instead of it. The
  residual charge a handling step leaves becomes a voltage into the cell
  through its own capacitance, and a complete, fully in-band control set
  can still deliver more than the cell survives once the required margin
  factor is applied.

## Workflow

1. Validate the withstand voltage and require the discharge model it was
   measured against; refuse an absent or unrecognized model rather than
   assuming the commonest one.
2. Group the cell into its sensitivity band from that model's own band
   table, and read off the controls the band obliges.
3. Grade each obliged control: a presence-only control on its stated
   presence, a ground-path control on its measured resistance against
   both ends of its band, refusing a bare yes where a measurement is
   owed.
4. Name any stated control the band does not oblige, so an unowed control
   cannot silently cover a missing one.
5. Decide the packing against where the cell travels: shielding to leave
   the protected area, dissipative or conductive inside it only,
   insulative never.
6. Measure the storage envelope on humidity and temperature at both ends
   and report the fraction of the declared shelf life already spent.
7. Convert the residual charge into the voltage it would deliver through
   the cell capacitance, compare it with the withstand voltage divided by
   the required margin factor, and report the achieved factor alongside
   the required one.
8. Accept only when the finding list is empty, and report per arm so a
   sound control set with a charge shortfall is visible as exactly that.

## Pitfalls

- Reading a withstand voltage without its discharge model. The number
  alone is not a sensitivity, and defaulting the model silently rewrites
  the whole control obligation.
- Grading controls on presence. A fitted strap with a broken ground path
  is present in every photograph and is not a ground.
- Treating the resistance band as a maximum. The floor is a
  personnel-safety limit, so a near-zero path is a defect and not an
  improvement.
- Letting an unowed control stand in for an owed one. A control set is
  graded against what the band asks for, not against how much equipment
  is in the room.
- Reading dissipative packing as protective. Bleeding its own charge is
  not shielding an external field, and the difference only matters at the
  moment the cell leaves the area.
- Treating storage as uneventful. Nothing observed is not the same as
  nothing accumulated, and shelf life runs on the calendar.
- Stopping at the checklist. A complete, in-band control set can still
  leave more charge than the cell survives, and only the voltage
  conversion shows it.
- Relaxing the required margin factor to pass a marginal case. The factor
  is stated; the comparison reports the achieved factor and lets the
  shortfall be seen.

## Behavior contract (gate 3)

The per-model sensitivity band tables, the band-driven control catalogue
with its inheritance, the presence-versus-resistance grading with both
ends of each ground-path band, the unowed-control finding, the packaging
decision against where the cell travels, the storage envelope and
shelf-life fraction, the charge-to-voltage conversion through the cell
capacitance and the margin-factor comparison, and the aggregated regime
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_esd_sensitivity.py against
scripts/e2008_bare_cell_esd_sensitivity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_esd_sensitivity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
