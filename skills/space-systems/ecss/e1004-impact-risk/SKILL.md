---
name: e1004-impact-risk
description: "Use when running a meteoroid/space-debris impact risk assessment for a space element under ECSS-E-ST-10-04C clause 10.2.5: combine the cumulative damaging flux from each contributing particle population at the ballistic-limit critical diameter, turn it into an expected impact count over the exposed area and mission duration, and compute the probability of no penetration (PNP) and probability of damage via the Annex J Poisson method, checking the result against the mission's PNP acceptance requirement. Distinct from the sibling e1004-debris and e1004-meteoroid leaves, which select and evaluate the flux models this leaf consumes, and from the sibling e1004-mm-margins leaf, which applies design margins to flux or damage predictions rather than running the probability calculation itself. Trigger: ecss, e-st-10-04c, impact risk, damage probability, probability of no penetration, pnp, annex j, meteoroid debris risk, ballistic limit, space environment."
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
  tags: [ecss, e-st-10-04c, space-environment, meteoroid, debris, impact-risk, annex-j, pnp]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Impact Risk Assessment (space-systems/ecss/e1004-impact-risk)

Use when the task is running the meteoroid/space-debris impact risk
assessment for a space element under ECSS-E-ST-10-04C clause 10.2.5:
turning per-population damaging flux into a probability of no
penetration (PNP) and probability of damage via the Annex J method,
and checking the result against the mission's PNP requirement.

## Domain quick reference

- ECSS-E-ST-10-04C clause 10.2.5 requires an impact risk assessment
  once the damaging flux at the element's ballistic-limit critical
  diameter is known: the flux is converted into a probability of
  penetration/damage over the mission, per the Annex J method.
- Each contributing particle population (debris, meteoroid background,
  meteoroid streams) evaluated at the same critical diameter has a
  cumulative flux (impacts/m^2/year); independent populations sum
  linearly into a total damaging flux.
- The expected number of damaging impacts is N = total_flux *
  exposed_area * mission_duration.
- Annex J treats impacts as a Poisson process: probability of no
  penetration Po = exp(-N); probability of one or more damaging
  impacts, Pd = 1 - Po.
- An element meets its risk-acceptance requirement only when Po is at
  or above the mission's minimum acceptable PNP; otherwise the
  shortfall (requirement - Po) drives further mitigation (shielding,
  reduced exposed area, added margin) upstream of this leaf.
- A system built from independently-assessed elements (panels,
  subsystems) has a system-level PNP equal to the product of the
  element PNPs, under the independence assumption used by the Annex J
  method.
- This leaf does not select or run the debris/meteoroid flux models
  (siblings e1004-debris, e1004-meteoroid) and does not apply design
  margins to flux or damage predictions (sibling e1004-mm-margins); it
  consumes already-selected, already-margined flux values and runs the
  probability calculation and requirement check.

## Workflow

1. Determine the critical diameter for the element (from the
   ballistic-limit equation for its shielding/structure) and collect
   the cumulative damaging flux at that diameter from each
   contributing population (debris, meteoroid background, meteoroid
   streams).
2. Sum the per-population fluxes into a total damaging flux for the
   element.
3. Compute the expected number of damaging impacts N over the
   element's exposed area and mission duration.
4. Compute the probability of no penetration (Po = exp(-N)) and the
   probability of damage (Pd = 1 - Po).
5. Compare Po against the mission's PNP acceptance requirement for the
   element; if Po falls short, record the shortfall and flag the
   element for mitigation (added shielding, reduced exposed area,
   reorientation) or margin review before proceeding.
6. When assessing a system of multiple independently-assessed elements,
   combine their individual PNPs multiplicatively to get the
   system-level PNP, and check that combined value against the
   system-level requirement.

## Pitfalls

- Summing fluxes evaluated at different critical diameters (each
  element/shielding configuration has its own ballistic-limit
  diameter; fluxes must be compared at the same diameter before
  summing).
- Treating Pd (probability of damage) as the PNP, or comparing it
  against a PNP-style requirement without inverting it first.
- Averaging element PNPs instead of multiplying them when rolling up
  to a system-level result (independence assumes multiplication, not
  averaging).
- Applying design margin inside this leaf's calculation instead of
  margining the input flux upstream (sibling e1004-mm-margins) so the
  probability step stays a pure flux-to-probability conversion.
- Reporting a shortfall as met because Po is close to the requirement;
  the check is a strict Po >= pnp_requirement comparison.

## Behavior contract (gate 3)

The flux-combination, expected-impact, probability, requirement-check,
and system-PNP-rollup logic is exercised by the gate 3 contract test:
scripts/test_e1004_impact_risk.py against
scripts/e1004_impact_risk_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_impact_risk.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
