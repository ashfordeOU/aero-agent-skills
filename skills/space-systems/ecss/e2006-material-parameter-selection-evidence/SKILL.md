---
name: e2006-material-parameter-selection-evidence
description: "Use when verify that the electrical material properties behind a spacecraft-charging decision rest on measured data under ECSS-E-ST-20-06C clause 6.8.2: categorize each parameter record by provenance (selection-campaign-measurement, maker-declared-measurement, generic-reference-value, unsubstantiated-estimate), check bulk-resistivity, surface-resistivity, relative-permittivity, secondary-emission-yield-peak, photoemission-yield and dielectric-thickness against physically admissible ranges and declared units, confirm the measurement conditions envelope the mission temperature range, compute the dielectric-relaxation constant, and demand a selection-campaign measurement wherever that constant makes the material hold charge across the event. Trigger: ecss, e-st-20-06c, clause-6-8-2, material-parameter-provenance, spacecraft-charging-material-data, bulk-resistivity-evidence, secondary-emission-yield-data, dielectric-relaxation-constant, material-selection-measurement-evidence."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-material-parameter-selection-evidence, material-parameter-provenance, spacecraft-charging-material-data, bulk-resistivity-evidence, secondary-emission-yield-data, dielectric-relaxation-constant]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Material Parameter Selection Evidence (space-systems/ecss/e2006-material-parameter-selection-evidence)

Use when the task is the evidence check of ECSS-E-ST-20-06C clause
6.8.2 -- establishing that the electrical material properties feeding a
spacecraft-charging decision are measured values, declared by the
material maker or obtained during the material selection campaign,
rather than generic or assumed numbers.

## Domain quick reference

- Clause 6.8.2 is a provenance requirement, not a value requirement.
  The same resistivity number is admissible when it comes from a
  sample measurement and inadmissible when it comes from a handbook
  entry for a nominally similar material, because the charging answer
  is only as defensible as the measurement behind it.
- Four provenance categories, ordered: a selection-campaign
  measurement on the flight material, a maker-declared measurement
  with a stated method, a generic reference value, and an
  unsubstantiated estimate or analogy. The first two are evidence;
  the last two are gaps to be closed, and an unfamiliar provenance
  wording is rejected rather than demoted, so it can never pass as
  measured data by default.
- The parameters that drive a surface-charging and internal-charging
  assessment are bulk-resistivity, surface-resistivity,
  relative-permittivity, peak secondary-emission-yield,
  photoemission-yield and dielectric-thickness. Each carries a
  physically admissible range (relative-permittivity below unity is
  not a weak datum, it is an impossible one) and a working unit;
  a value outside the range or in the wrong unit is a dossier defect,
  not a finding to be graded.
- Which parameters a material must carry follows its role: an
  exposed-dielectric-surface needs the full set, a
  conductive-external-coating needs the surface and emission
  parameters, an internal-dielectric needs the bulk parameters and
  thickness.
- The dielectric-relaxation constant tau = eps0 x eps_r x rho says
  how long the material holds deposited charge. When tau reaches a
  significant fraction of the charging-event timescale the material
  drives the result, and its resistivity may then only rest on a
  selection-campaign measurement -- maker-declared data is no longer
  enough for the parameter that dominates the answer.
- Measurement conditions must envelope the mission: resistivity moves
  by orders of magnitude across a thermal range, so data taken only
  at room temperature does not support a cold-case decision.

## Workflow

1. Normalize every parameter name and provenance string onto its
   canonical key, rejecting anything unrecognized.
2. Validate each record: value numeric, finite and inside the
   physically admissible range for that parameter, unit in agreement,
   and a measurement method stated whenever the provenance claims a
   measurement.
3. Grade provenance: measured records are evidence, generic and
   unsubstantiated records are findings that name the parameter.
4. Look up the parameters required by the material's role and report
   any that are absent from the dossier.
5. Check the measurement temperature range envelopes the mission
   range on both the cold and hot side, reporting each shortfall.
6. Where bulk-resistivity and relative-permittivity are both present,
   compute the relaxation constant and raise the provenance demand on
   the resistivity when the material holds charge across the event.
7. Declare the material evidence-sufficient only when every list is
   empty, then roll the materials up into a campaign verdict.

## Pitfalls

- Accepting a handbook value for a flight material because the
  generic family matches -- formulation, filler loading and surface
  treatment move resistivity and emission yield far more than the
  family name suggests.
- Taking a maker datasheet number with no stated measurement method
  as measured evidence; without the method and conditions it is a
  declared number, not a reproducible measurement.
- Grading a value that is physically impossible (relative-permittivity
  under unity, a negative resistivity) as merely weak evidence
  instead of rejecting the record outright.
- Comparing values across mismatched units -- bulk-resistivity in
  ohm-m against a surface-resistivity in ohm-per-square silently
  changes the quantity being judged.
- Using room-temperature data for a cold-case assessment: the
  decision is made where the material is most resistive, which is
  usually outside the measured range.
- Treating maker data as always sufficient. When the relaxation
  constant is comparable to the event timescale, the resistivity is
  the answer, and the clause's selection-campaign measurement is what
  the decision stands on.

## Behavior contract (gate 3)

The parameter normalization, provenance categorization, record
validation, environment-coverage, relaxation-constant and campaign
roll-up logic is exercised by the gate 3 contract test:
scripts/test_e2006_material_parameter_selection_evidence.py against
scripts/e2006_material_parameter_selection_evidence_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_material_parameter_selection_evidence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
