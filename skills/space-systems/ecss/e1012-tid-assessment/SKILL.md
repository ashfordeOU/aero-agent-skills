---
name: e1012-tid-assessment
description: "Use when calculate total ionising dose (TID) damage for spacecraft
  electronic components under ECSS-E-ST-10-12C §7.5: derive the applicable radiation
  damage parameters for each component category (§7.5.1), compute the accumulated
  ionising dose from orbit-specific dose rates and mission duration using an aluminium
  shielding model (§7.5.2), apply the required design margin, and compare each
  component's dose requirement against its TID limit to produce a compliant or
  non-compliant finding. Trigger: ecss, e-st-10-12c, e-st-10-system-scope,
  tid, total-ionising-dose, radiation-damage, dose-calculation, shielding, rha,
  component-assessment."
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
  tags: [ecss, e-st-10-12c, e-st-10-system-scope, tid, total-ionising-dose, radiation-damage, dose-calculation, shielding, rha, component-assessment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — TID Assessment (space-systems/ecss/e1012-tid-assessment)

Use when the task is to calculate total ionising dose (TID) damage for
electronic components under ECSS-E-ST-10-12C §7.5 — deriving radiation
damage parameters (§7.5.1), computing the accumulated ionising dose with
shielding and margin (§7.5.2), and recording a pass/fail finding per component.

## Domain quick reference

- §7.5.1 establishes the radiation damage parameters: each component is
  grouped into a category (standard, rad-tolerant, rad-hard, rad-hardened)
  defined by its maximum TID tolerance in rad(Si). The category is the
  anchor for the dose limit comparison and is derived from the component
  manufacturer's radiation characterisation data, not assumed.
- §7.5.2 defines the ionising dose calculation: the environment model
  provides an orbit- and shielding-dependent dose rate (krad/year behind
  a specified aluminium sphere equivalent). Accumulated TID equals the dose
  rate multiplied by the mission duration; a design margin (typically 2×)
  is then applied to obtain the radiation design requirement for each
  location. The margin accounts for uncertainties in the environment model,
  shielding geometry, and dose enhancement effects.
- The assessment finds a component non-compliant when its dose design
  requirement (TID × margin) exceeds its category limit. A component is
  not automatically compliant simply because no limit was recorded — a
  missing limit is itself a finding requiring resolution before the
  assessment closes.

## Workflow

1. Identify the mission orbit and nominal aluminium shielding thickness
   at each component location. Confirm that a dose rate is available for
   that orbit–shielding pair from the environment analysis; reject
   undefined combinations before proceeding.
2. Derive the radiation damage parameters for each component: assign it
   to a category (standard / rad-tolerant / rad-hard / rad-hardened) from
   its characterisation data and record the associated TID limit in rad(Si).
   Flag any component without a characterised limit as needing resolution.
3. Compute the accumulated TID at each location: multiply the dose rate
   (krad/year) by the mission duration (years) and convert to rad.
4. Apply the design margin to the computed TID to obtain the radiation
   design requirement for each component location.
5. Compare each component's design requirement against its category TID
   limit. Record a compliant or non-compliant finding; do not carry
   forward a component with a missing limit as compliant.
6. Collect all findings per component location; the location is not TID
   compliant until every component at that location produces a compliant
   finding and no limit gaps remain.

## Pitfalls

- Applying the dose rate directly as the TID without multiplying by
  mission duration — the rate is per year, not the total accumulated dose.
- Omitting the design margin before comparing against the limit — comparing
  raw TID to the limit understates the requirement and can produce a false
  pass when the environment and geometry uncertainties are unaccounted for.
- Treating a missing TID limit as equivalent to an unlimited tolerance —
  absence of characterisation data is a gap in the damage parameter set,
  not a licence to proceed.
- Using aluminium shielding thickness as a direct proxy for dose without
  confirming the orbit–shielding lookup is valid — an interpolated or
  extrapolated dose rate outside the environment table's range propagates
  unquantified error into every downstream comparison.

## Behavior contract (gate 3)

The damage-parameter grouping, TID computation, margin application, and
pass/fail assessment logic is exercised by the gate 3 contract test:
scripts/test_e1012_tid_assessment.py against
scripts/e1012_tid_assessment_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_tid_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
