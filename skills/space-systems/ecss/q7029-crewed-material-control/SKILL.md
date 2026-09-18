---
name: q7029-crewed-material-control
description: "Determine whether an offgassing-tested material may be installed in a crew compartment, and at what mass, under ECSS-Q-ST-70-29. Use when a tested material is being taken into the ECSS-Q-ST-70C selection and the ECSS-Q-ST-70-01C contamination control. Turn each specific yield and the installed mass into the concentration it contributes to the sealed free volume, ratio every contribution against its allowable, sum the ratios into one mixture index, invert the relation for the mass the compartment can carry, name the binding compound, grade the selection evidence and the report's standing, and close with approved, approved-with-mass-limit or not-approved. Trigger: ecss, q-st-70-29, q-st-70c, crew-compartment-offgassing-mixture-index, crew-compartment-material-mass-limit, crew-compartment-smac-ratio, crew-compartment-binding-compound, crew-compartment-selection-evidence-link, offgassing-report-revalidation."
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
  tags: [ecss, q-st-70-29-offgassing-determination, q-st-70-29, q7029-crewed-material-control, crew-compartment-offgassing-mixture-index, crew-compartment-material-mass-limit, crew-compartment-smac-ratio, crew-compartment-binding-compound, crew-compartment-selection-evidence-link, offgassing-report-revalidation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Crew-Compartment Material Control (space-systems/ecss/q7029-crewed-material-control)

Use when the task is the interface side of ECSS-Q-ST-70-29: taking an offgassing
result out of the laboratory and into the crew-compartment material selection it
exists to serve, alongside the ECSS-Q-ST-70C selection record and the
ECSS-Q-ST-70-01C contamination control. This leaf grades one material against
one compartment, not the test that produced the numbers.

## Domain quick reference

- An offgassing yield is specific, and a compartment is a volume. Neither number
  means anything alone: the same material is harmless as a connector seal and
  unacceptable as a wall lining, because what the crew breathes is mass times
  yield divided by free volume.
- The crew breathes the mixture. Ten compounds each at a fifth of their own
  allowable are not ten passes; they are twice the allowable burden, which is
  why the ratios are summed into one index rather than checked one at a time.
- An index above unity is a mass statement, not a refusal. The relation is
  linear in installed mass, so inverting it returns the mass at which the index
  reaches unity, and the answer to an over-index material is usually less of it
  rather than none of it.
- The compound that binds is rarely the one with the largest yield. A small
  release against a very low allowable sets the limit long before a large
  release against a generous one, so the binding compound is named explicitly
  and not inferred from the yield table.
- The report is evidence with a shelf life. An offgassing result describes the
  formulation and process that were tested; a resin change, a new cure schedule
  or a different supplier lot leaves the report describing a material that is no
  longer the one going into the vehicle.
- The report is also not a selection on its own. It has to be tied to the
  material selection approval and the contamination control the compartment runs
  under, or nothing downstream can find out that this material was assessed.

## Workflow

1. Validate the compartment free volume, the installed mass, and one record per
   reported compound carrying its specific yield and its allowable.
2. Convert each yield and the installed mass into a compartment concentration,
   then into a ratio against that compound's allowable.
3. Sum the ratios into the mixture index. A ratio or index landing exactly on
   unity is counted as inside by a named tolerance, not by moving the allowable.
4. Invert the same relation for the mass at which the mixture reaches unity, and
   name the compound whose own allowable is reached at the lowest mass.
5. Grade the evidence: the offgassing report, the selection approval, the
   contamination control plan, the declared materials entry, the age of the
   report against its revalidation interval, and any formulation change.
6. Rank findings by severity and close with one disposition: approved for the
   crew compartment, approved with a mass limit, or not approved.

## Pitfalls

- Quoting a yield as though it were a verdict. A specific yield is a property of
  the material; the compartment concentration is a property of the installation,
  and only the second can be compared with an allowable.
- Checking compounds one at a time. A material can clear every single allowable
  and still put the mixture index above unity, and that is the common case for a
  polymer releasing a family of related compounds.
- Refusing an over-index material outright. The relation is linear, so the
  useful answer is the mass the compartment can carry, which usually keeps the
  material in the design at a reduced area.
- Assuming the largest yield is the binding compound. The limit is set by the
  smallest ratio of allowable to yield, which routinely belongs to a trace
  compound with a very low allowable.
- Reusing a report across a formulation change. The test measured the material
  that existed on the test date; a process or supplier change puts a different
  material behind the same part number.
- Treating the selection approval and the contamination control plan as
  paperwork around the result. They are what makes the result findable at
  assembly, and their absence is a gap in control, not in filing.

## Behavior contract (gate 3)

The compartment concentration, the allowable ratio, the mixture index, the
combined and single-compound mass limits, the binding compound, the evidence
gaps, the report revalidation and formulation-change findings and the selection
disposition are exercised by the gate 3 contract test:
scripts/test_q7029_crewed_material_control.py against
scripts/q7029_crewed_material_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7029_crewed_material_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
