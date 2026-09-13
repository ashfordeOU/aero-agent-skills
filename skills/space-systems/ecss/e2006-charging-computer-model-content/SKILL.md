---
name: e2006-charging-computer-model-content
description: "Use when verify that a spacecraft-charging computer model offered as design-acceptance evidence carries the physical content required by ECSS-E-ST-20-06C clause 6.8.4: confirm the simulation represents ambient-electron-collection and ambient-ion-collection, photoemission on sunlit-surfaces, secondary-electron-emission by electrons and by ions, electron-backscatter, surface-conduction and bulk-conduction in dielectrics, radiation-induced-conductivity under penetrating-radiation, illumination-geometry and wake-shadowing geometry, and any active-plasma-source current; confirm each represented effect carries its material-parameter set, that the current-balance solution closes on the floating-potential, and that the integration-step resolves the charging-time-constant. Trigger: ecss, e-st-20-electrical-scope, e2006-charging-computer-model-content, spacecraft-charging-model, charging-simulation-content, secondary-electron-emission, photoemission-current, radiation-induced-conductivity, current-balance-closure."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-charging-computer-model-content, spacecraft-charging-model, charging-simulation-content, secondary-electron-emission, photoemission-current, radiation-induced-conductivity, current-balance-closure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Computer Model Content (space-systems/ecss/e2006-charging-computer-model-content)

Use when the task is judging whether a spacecraft-charging simulation is
complete enough to carry design acceptance under ECSS-E-ST-20-06C clause
6.8.4 -- which physical effects the model represents, whether each one is
backed by a material-parameter set, and whether the numerical solution
actually closes.

## Domain quick reference

- Clause 6.8.4 governs model CONTENT, not model accuracy. A charging
  simulation used as acceptance evidence must represent every current
  that can reach or leave a surface in the declared environment. A model
  that omits an applicable effect is incomplete evidence regardless of
  how well it reproduces one test point.
- The current families are: environment-current (ambient-electron and
  ambient-ion collection from the plasma spectrum), emission-current
  (photoemission on illuminated surfaces, secondary-electron-emission
  driven by impacting electrons, secondary-electron-emission driven by
  impacting ions, electron-backscatter), charge-transport (surface-
  conduction, bulk-conduction and radiation-induced-conductivity inside
  dielectrics), geometry (illumination-geometry, and wake-shadowing
  geometry where a ram/wake structure exists), external-current (an
  active-plasma-source such as an electric-propulsion neutraliser or a
  plasma-contactor), and numerical (the current-balance solution for
  the floating-potential, and time-dependent integration where the
  analysis covers an eclipse-entry or substorm-onset transient).
- Applicability is configuration-driven. Photoemission and
  illumination-geometry are mandatory only for a configuration that
  sees sunlight; the conduction effects only where a dielectric is
  present; radiation-induced-conductivity only where that dielectric
  also sees penetrating-radiation; wake-shadowing geometry and
  ion-driven secondary-electron-emission only in a flowing-plasma
  regime such as a low-altitude orbit; time-dependent integration only
  for a transient analysis.
- Every represented emission or transport effect needs its own measured
  or referenced parameter set (photoelectron saturation current density,
  secondary-emission peak yield and peak energy, backscatter yield,
  surface and bulk resistivity, relative permittivity, the
  radiation-induced-conductivity coefficient and exponent). A named
  effect with no parameters behind it is a declaration, not model
  content.
- The current-balance residual must vanish at the converged
  floating-potential. The residual is a signed sum of collected and
  emitted currents, so it is compared against a tolerance scaled to the
  largest individual current, absorbed with a relative tolerance rather
  than an exact zero test.
- The integration-step of a transient run must be a small fraction of
  the charging-time-constant (surface capacitance times potential
  divided by net current density); a step that equals or exceeds that
  constant cannot resolve the charging transient it claims to predict.

## Workflow

1. Read the configuration: orbital regime, sunlit or eclipsed, presence
   of dielectric surfaces, presence of penetrating-radiation, presence
   of an active-plasma-source, and whether the analysis is transient.
   Reject an unrecognized regime or a non-boolean flag before the
   assessment starts.
2. Derive the required effect set from that configuration, then compare
   it against the effects the model declares. Anything required and
   absent is a content finding; anything declared but not required is
   recorded as extra scope, not as a fault.
3. For each declared effect that carries a parameter contract, check
   the parameter set exists and every value sits inside its physical
   range. A missing parameter and an out-of-range parameter are both
   findings.
4. Sum the converged current set and test the residual against a
   tolerance scaled to the largest contributing current; a residual
   outside that tolerance means the floating-potential solution did not
   close and the predicted potential is not evidence.
5. For a transient analysis, compute the charging-time-constant from
   surface capacitance, predicted potential and net current density,
   and confirm the integration-step is at or below the permitted
   fraction of it.
6. Aggregate: the model supports design acceptance only when the
   required-effect list, the parameter list, the balance check and the
   step check are all clear.

## Pitfalls

- Treating the effect list as fixed. A model that carries photoemission
  in a permanently-eclipsed configuration is not wrong, but a model
  without wake-shadowing geometry in a flowing-plasma regime is
  incomplete -- the required set follows the configuration.
- Accepting a named effect with an empty parameter set. Clause 6.8.4
  evidence needs the emission and transport coefficients behind each
  effect; a secondary-emission model with no peak yield and no peak
  energy computes nothing.
- Testing the current-balance residual against exact zero. The residual
  is a sum of signed currents spanning several decades, so a physically
  closed solution can land a few units in the last place away from
  zero; scale the tolerance to the largest current instead of widening
  the engineering criterion.
- Reading a converged potential as validated physics. Convergence says
  the solver closed on the currents it was given; if an applicable
  current family was never represented, the solution converges on the
  wrong problem.
- Choosing an integration-step from run-time convenience. A step above
  the charging-time-constant smears the eclipse-entry transient that
  the differential-charging conclusion rests on.

## Behavior contract (gate 3)

The configuration validation, required-effect derivation, parameter
range checking, current-balance closure and integration-step logic are
exercised by the gate 3 contract test:
scripts/test_e2006_charging_computer_model_content.py against
scripts/e2006_charging_computer_model_content_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_charging_computer_model_content.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
