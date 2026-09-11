---
name: e1012-principles
description: "Use when assess radiation effects on space components or systems
  under ECSS-E-ST-10-12C §4 evaluation framework: identify which radiation effect
  types apply (total ionising dose, displacement damage, single-event effects,
  enhanced low dose rate sensitivity), determine the evaluation activities required
  for the current project phase from the stage-activity table, validate
  parameter-unit pairs against the §4 parameter table, and verify evaluation
  completeness before phase closure. The framework spans phase A concept screening
  through phase F end-of-life verification, with cross-references to ECSS-E-ST-10-04C
  for the radiation environment inputs. Trigger: ecss, e-st-10-12c,
  radiation-effects, total-ionising-dose, displacement-damage, single-event-effects,
  eldrs, radiation-hardness-assurance, evaluation-activities, project-phase."
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
  tags: [ecss, e-st-10-12c, radiation-effects, total-ionising-dose, displacement-damage, single-event-effects, eldrs, radiation-hardness-assurance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Evaluation — Principles and Framework (space-systems/ecss/e1012-principles)

Use when the task is applying the §4 evaluation framework of
ECSS-E-ST-10-12C -- identifying which radiation effect types apply to
a component, looking up which evaluation activities are required for
the current project phase, validating parameter-unit pairs from the
§4 table, and checking that the evaluation is complete before
proceeding to the next phase.

## Domain quick reference

- §4 groups radiation effects by physical mechanism into four
  categories: total ionising dose (TID -- cumulative charge deposited
  in a material, expressed in rad(Si) or Gy(Si)), displacement damage
  (DD -- cumulative atomic lattice disruption from non-ionising energy
  loss, expressed as NIEL dose), single-event effects (SEE -- effects
  caused by a single energetic particle, covering upsets, latchup,
  transients, functional interrupts, and hard errors), and enhanced
  low dose rate sensitivity (ELDRS -- a bipolar-device variant of TID
  where damage accumulates more severely at low dose rates than at the
  high rate used in standard TID tests). A component may be susceptible
  to more than one category simultaneously; each susceptible category
  must be treated independently.
- The stage-activity table (Table 4-1 paraphrase) maps project phases
  to required evaluation activities: phase A (concept) requires
  environment scoping and preliminary sensitivity screening; phase B
  (definition) adds an environment estimate, technology screening, a
  preliminary shielding study, and a candidate component list; phase
  C/D (design and qualification) requires a detailed environment
  specification, component-level radiation analysis, shielding
  analysis, a radiation test programme, qualification evidence, and
  radiation design margin verification; phase E (utilisation) requires
  in-flight monitoring, anomaly radiation assessment, and residual
  margin verification; phase F (disposal) requires end-of-life dose
  verification. An activity listed for a phase cannot be deferred to
  the next phase without a documented tailoring decision.
- The parameter-unit table (Table 4-2 paraphrase) constrains which
  units are accepted for each radiation parameter: TID uses rad(Si),
  Gy(Si), or krad(Si); NIEL dose uses MeV/g or MeV·cm²/g; LET
  threshold uses MeV·cm²/mg; saturation cross-section uses cm²,
  cm²/device, or cm²/bit; event rate uses events/device/s,
  events/bit/s, or upsets/day; ELDRS sensitivity dose uses rad(Si)
  or Gy(Si). Using a non-listed unit is a finding, not a preference.

## Workflow

1. For each component under review, list every radiation effect type
   suspected to be applicable. Map each type to its category (TID,
   DD, SEE, ELDRS) using the §4 effect-type register; flag any type
   that does not map to a known category before proceeding.
2. Identify the current project phase (A, B, C/D, E, or F). Look up
   the set of required evaluation activities for that phase from the
   stage-activity table. Record the set as the target.
3. Collect the list of evaluation activities already performed or
   planned for the current phase. Compute the gap: required activities
   minus performed activities. A non-empty gap is a finding; each
   missing activity must be scheduled or a tailoring record raised.
4. For each radiation parameter in the evaluation record, confirm the
   parameter name appears in the §4 parameter table and that the unit
   used is one of the accepted units for that parameter. A parameter
   outside the table or with a non-listed unit is a finding.
5. Aggregate findings across all three dimensions (effect-type
   categorisation, activity gaps, parameter-unit issues) per component.
   A component is evaluation-compliant for the current phase only when
   all three finding lists are empty.
6. Cross-reference the radiation environment inputs (environment
   estimates, fluence spectra, dose-depth curves) to ECSS-E-ST-10-04C;
   flag any environment input that lacks a traceable source standard.

## Pitfalls

- Treating ELDRS as a sub-type of TID that needs no separate activity
  -- a bipolar device may pass a standard high-dose-rate TID test but
  fail in service because the low-dose-rate test was never run; the
  evaluation framework requires ELDRS to be addressed as a distinct
  susceptibility when the technology applies.
- Carrying forward phase B activity records to satisfy phase C/D
  requirements without documenting the update -- phase C/D activities
  (detailed environment specification, radiation test programme) have
  higher fidelity requirements than their phase B counterparts and
  are not interchangeable.
- Reading "no activity gap" as "no radiation risk" -- the stage-
  activity table records procedural completeness, not compliance margin;
  a component can have all activities complete and still have
  insufficient margin when the analysis results are reviewed.
- Accepting a non-listed unit as a minor notation difference -- the
  §4 parameter table establishes the accepted units for inter-team
  traceability; a parameter recorded in a non-listed unit cannot be
  compared directly against a budget or test result expressed in the
  listed unit without a documented conversion that itself may carry
  uncertainty.

## Behavior contract (gate 3)

The effect-type categorisation, stage-activity lookup, parameter-unit
validation, and evaluation-completeness gap logic is exercised by the
gate 3 contract test: scripts/test_e1012_principles.py against
scripts/e1012_principles_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_principles.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
