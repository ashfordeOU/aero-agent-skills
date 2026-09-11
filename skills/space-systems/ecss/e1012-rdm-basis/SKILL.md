---
name: e1012-rdm-basis
description: "Use when define the radiation design margin (RDM) requirement basis for a spacecraft component from the mission radiation environment specification (ECSS-E-ST-10-12C §5.1.1): take the total ionising dose, proton fluence, and electron fluence from the environment model, apply the minimum RDM factor to each parameter to derive the required component withstand level, verify the factor meets the ECSS minimum threshold, and flag any component whose radiation tolerance falls short of the required level. Trigger: ecss, e-st-10-system-scope, e-st-10-12c, radiation-design-margin, rdm, total-ionising-dose, proton-fluence, electron-fluence."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-12c, radiation-design-margin, rdm, total-ionising-dose, proton-fluence, electron-fluence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Radiation Design Margin Basis (space-systems/ecss/e1012-rdm-basis)

Use when the task is to define the radiation design margin (RDM)
requirement basis for a spacecraft component under ECSS-E-ST-10-12C
§5.1.1 — taking the mission radiation environment specification,
applying the minimum RDM factor, and verifying that the component's
radiation tolerance satisfies the derived requirement.

## Domain quick reference

- The RDM approach converts the mission radiation environment
  specification into a component-level withstand requirement by
  multiplying each environment parameter by the RDM factor. A component
  is compliant when its rated tolerance meets or exceeds this derived
  level.
- Three parameters drive the basis: total ionising dose (TID, krad),
  proton fluence (cm⁻²), and electron fluence (cm⁻²). Each is treated
  independently because they map to different damage mechanisms (TID
  governs cumulative oxide charge trapping; proton and electron fluence
  govern bulk displacement damage and also contribute to TID).
- ECSS-E-ST-10-12C §5.1.1 requires a minimum RDM factor of 2.0 for the
  TID basis. The same factor is conventionally applied to particle
  fluences to maintain consistency across the margin derivation. An RDM
  factor below 2.0 is not admissible and must be rejected before the
  required levels are computed.
- A component with no tolerance on record for a required parameter is
  treated as non-compliant (open finding) — the absence of a withstand
  value is itself a gap in the margin basis, not a pass.

## Workflow

1. Obtain the mission radiation environment specification: confirm that
   values for total ionising dose, proton fluence, and electron fluence
   are present, positive, and carry consistent units. Reject the input
   if any value is missing, zero, or negative.
2. Select the RDM factor. Confirm it is ≥ 2.0; reject any factor below
   the ECSS minimum before proceeding.
3. Compute the required withstand level for each parameter:
   required = environment_value × RDM_factor. Record the required
   levels as the component's radiation requirement baseline.
4. For each parameter, compare the component's rated radiation tolerance
   against the required level. A tolerance that equals or exceeds the
   required level passes; one that falls short generates a finding
   noting the shortfall.
5. Flag any parameter for which no component tolerance is on record. The
   absence of a tolerance value is an open finding in the margin basis.
6. Aggregate findings across all three parameters. The component's RDM
   basis is closed (compliant) only when every parameter has a passing
   result and no open findings remain.

## Pitfalls

- Applying the RDM factor after comparing the component tolerance
  against the raw environment value — the factor must be applied to the
  environment first to derive the requirement; comparing against the
  unscaled environment value understates the margin requirement and
  produces a false pass.
- Using a factor below 2.0 because the component catalogue shows a
  higher intrinsic margin — ECSS-E-ST-10-12C §5.1.1 sets the minimum
  factor at the requirement derivation step regardless of the
  component's actual rating; the factor is a programme control tool,
  not a measurement of the component.
- Treating a missing tolerance entry as "no data, therefore no finding"
  — a missing tolerance means the margin basis for that parameter is
  incomplete, which is a finding that must be resolved before the
  component can be accepted.
- Mixing TID units (krad vs. Mrad) or fluence conventions (total vs.
  equivalent 1 MeV neutron fluence) between the environment
  specification and the component datasheet — validate that both sides
  of each comparison share the same unit and particle energy reference
  before the numbers are compared.

## Behavior contract (gate 3)

The environment validation, RDM factor checking, required-level
computation, and component compliance logic are exercised by the gate 3
contract test: scripts/test_e1012_rdm_basis.py against
scripts/e1012_rdm_basis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_rdm_basis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
