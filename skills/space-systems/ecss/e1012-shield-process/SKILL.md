---
name: e1012-shield-process
description: "Use when execute the spacecraft shielding calculation process under
  ECSS-E-ST-10-12C §6.2.1: identify the radiation effects that require quantification
  (TID, DD, SEE proton, SEE heavy-ion), select the appropriate calculation method
  for each effect from the geometry- and effect-dependent method table (slab
  approximation, sector analysis, or Monte Carlo for primary shielding; NIEL-weighted
  fluence for DD; LET-spectrum assessment for heavy-ion SEE), compute the predicted
  dose or fluence behind the combined primary and secondary shielding, and compare
  each result against the component's dose or fluence limit including the radiation
  design margin. Trigger: ecss, e-st-10-system-scope, shielding, radiation shielding,
  TID, displacement damage, SEE, sector analysis, Monte Carlo, radiation design margin,
  primary shielding, secondary shielding."
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
  tags: [ecss, e-st-10-system-scope, shielding, TID, displacement-damage, SEE, sector-analysis, monte-carlo, radiation-design-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Shielding Calculation Process (space-systems/ecss/e1012-shield-process)

Use when the task is executing the shielding calculation process of
ECSS-E-ST-10-12C §6.2.1 — selecting the method, running the calculation
for each applicable radiation effect, and verifying that the predicted
dose or fluence behind the combined primary and secondary shielding
satisfies the component's limit with its radiation design margin.

## Domain quick reference

- §6.2.1 requires that the process be tailored to the effect being
  quantified: TID, displacement damage (DD), proton-induced SEE, and
  heavy-ion SEE each drive a different combination of shielding
  calculation method and quantity computed.
- Method selection follows two tables in the standard (paraphrased here
  as a geometry × effect matrix). For TID and proton-SEE the geometry
  complexity governs the choice: simple geometries allow a slab or
  spherical-shell approximation; moderate geometries call for sector
  analysis (ray-trace angle integration); complex geometries require a
  Monte Carlo particle-transport simulation. For DD the same geometric
  tiers apply but the transport result is weighted by the non-ionising
  energy loss (NIEL) function before comparison against the fluence
  limit. For heavy-ion SEE the LET spectrum at the device location is
  the required output, and bulk shielding thickness has limited effect
  on that spectrum for typical spacecraft wall thicknesses.
- Shielding is split into primary (spacecraft structural shell,
  instrument housing) and secondary (local spot shielding placed
  directly around a sensitive component). Both layers contribute to the
  total areal density seen by the radiation environment.
- The radiation design margin (RDM) is applied by dividing the
  component's dose or fluence limit by the margin factor before
  comparison; an RDM of 2 means the predicted value must not exceed
  half the stated limit.

## Workflow

1. Identify every radiation effect that must be quantified for each
   component: TID from trapped electrons and protons, DD from proton
   and neutron fluence, proton SEE from proton fluence behind shielding,
   and heavy-ion SEE from the LET spectrum at the device. An effect
   with no applicable device sensitivity or no environment contribution
   may be screened out with documented justification; the process still
   records a finding that the effect was assessed.
2. For each (component, effect) pair, categorize the shielding geometry
   as simple, moderate, or complex based on the regularity of the
   surrounding structure and whether the component's view of the
   radiation environment is well-characterized by a small number of
   representative ray directions.
3. Select the calculation method from the effect × geometry matrix
   (sector analysis for TID/moderate, Monte Carlo for TID/complex,
   NIEL-weighted fluence for DD, LET-spectrum for heavy-ion SEE).
   Document the selected method; a change in geometry assessment after
   method selection requires revisiting this step.
4. Obtain the unshielded dose or fluence for the mission orbit and
   duration from the environment model (e.g. AE-8/AP-8, CRÈME,
   SPENVIS output). Confirm that the environment run uses the correct
   orbit, attitude, and solar cycle phase.
5. Apply the primary shielding thickness (spacecraft structure, in
   aluminium-equivalent mm) and the secondary shielding thickness
   (local spot shielding) to attenuate the environment to the predicted
   dose or fluence at the component. For sector analysis this is done
   ray-by-ray and summed; for Monte Carlo it emerges from the
   simulation; for the simplified slab model the total areal density is
   used with an exponential attenuation relation.
6. Apply the radiation design margin: the pass criterion is predicted
   dose or fluence ≤ (limit / RDM). Record a failure for every
   component × effect pair that does not satisfy this criterion.
7. For any failing pair, determine whether adding secondary shielding,
   re-routing the component, or choosing a more radiation-tolerant part
   resolves the exceedance, and re-run the calculation with the revised
   configuration.
8. Aggregate all results into a shielding adequacy summary: total
   component × effect pairs assessed, number passing, number failing,
   and the identity and shortfall of each failure.

## Pitfalls

- Applying the same attenuation model to heavy-ion SEE — heavy ions are
  not substantially attenuated by the shielding thicknesses common in
  spacecraft (a few mm Al-equivalent); shielding reduces proton SEE and
  TID but cannot substitute for part selection or error-correction logic
  for heavy-ion events.
- Omitting secondary shielding from the calculation — if a component
  has local spot shielding that was added specifically to meet its dose
  requirement, excluding it from the areal density underestimates the
  attenuation and may drive unnecessary redesign.
- Using a simple slab model for a component deeply recessed in a complex
  structure — the effective shielding in that geometry is not captured
  by a single total thickness; sector analysis or Monte Carlo is needed
  to represent the angular distribution of shielding correctly.
- Dividing by the RDM after checking the limit instead of before —
  the design limit that the predicted dose must not exceed is limit/RDM,
  not the limit itself; reversing the operation silently removes the
  margin.
- Conflating the TID environment (electron and proton contributions
  combined) with the proton-only fluence used for DD and proton SEE —
  the inputs to each effect calculation are distinct and must be drawn
  from the correct environment model output.

## Behavior contract (gate 3)

The method-selection, attenuation, adequacy-check, and full-process
orchestration logic is exercised by the gate 3 contract test:
scripts/test_e1012_shield_process.py against
scripts/e1012_shield_process_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_shield_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
