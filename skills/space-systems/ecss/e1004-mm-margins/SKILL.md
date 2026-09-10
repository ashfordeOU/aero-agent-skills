---
name: e1004-mm-margins
description: "Use when applying margins to a debris/meteoroid flux prediction and its ballistic-limit damage prediction for an ECSS-E-ST-10-04C space environment specification: compute the margined expected-impact rate from a flux margin factor, compute the margined critical (ballistic-limit) diameter from a diameter margin factor, derive the margined probability of no penetration (PNP), and verify the margin factors used meet the project's minimum conservatism before the PNP is compared against its requirement. Trigger: debris margin, meteoroid margin, MMOD margin, flux margin factor, ballistic limit margin, critical diameter margin, damage prediction margin, probability of no penetration, PNP, margined flux, §10.2.6, E-ST-10-04, ecss, e-st-10c space environment."
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
  tags: [ecss, e-st-10-04c, space-environment, debris, meteoroid, mmod, margins, damage-prediction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Debris/Meteoroid Margin Policy (space-systems/ecss/e1004-mm-margins)

Use when the task is applying margins to a debris/meteoroid (MMOD) flux
prediction and its damage prediction for an ECSS-E-ST-10-04C space
environment specification (clause 10.2.6), ahead of comparing the
margined risk number against its probability-of-no-penetration (PNP)
requirement.

## Domain quick reference

- ECSS-E-ST-10-04C clause 10.2.6 requires that debris/meteoroid flux
  predictions and the damage (penetration) predictions built on them
  carry a stated margin before they are used to demonstrate compliance
  with a mission's MMOD risk requirement -- the raw model output from
  the flux and impact-risk leaves is a best estimate, not a compliance
  number, because the underlying flux and ballistic-limit models carry
  known uncertainty.
- Two margins are applied, and both are needed: a flux margin factor
  (>= 1.0) that scales up the predicted expected-impact rate from the
  debris/meteoroid flux leaves (e1004-debris, e1004-meteoroid) to cover
  flux-model uncertainty, and a diameter margin factor (in the range
  (0, 1]) that derates the ballistic-limit critical diameter from the
  impact-risk leaf (e1004-impact-risk) so that smaller, more numerous
  particles are conservatively counted as damaging.
- The cumulative flux above a given particle diameter is commonly
  approximated locally by a power law (flux ~ diameter^-b); shrinking
  the critical diameter by the diameter margin therefore raises the
  expected-impact rate by (baseline_diameter / margined_diameter)^b,
  using whatever local power-law exponent the mission's flux
  environment specification states for the diameter range of interest.
- The margined expected-impact rate (flux margin x diameter-margin
  uplift) feeds a standard Poisson no-impact-in-service model:
  PNP = exp(-margined_expected_impacts). This PNP is what gets compared
  against the mission's PNP requirement -- never the unmargined PNP.
- This leaf owns only the margin application and the PNP derivation
  from a margined impact rate. It does not own flux model selection
  (e1004-debris, e1004-meteoroid), the ballistic-limit/critical-diameter
  calculation itself (e1004-impact-risk), or the margin factor values
  themselves, which are mission-specific inputs from the project's
  environmental specification.

## Workflow

1. Obtain the baseline (unmargined) expected-impact rate and the
   baseline critical diameter from the flux and impact-risk leaves for
   the mission orbit, exposure duration, and surface area under
   assessment.
2. Obtain the project's flux margin factor (>= 1.0) and diameter margin
   factor (in (0, 1]) from the environmental specification, plus the
   local power-law exponent for the cumulative flux near the baseline
   critical diameter.
3. Apply the flux margin factor to the baseline expected-impact rate.
4. Apply the diameter margin factor to the baseline critical diameter
   to get the margined critical diameter.
5. Derive the margined expected-impact rate by rescaling the
   flux-margined impact rate from the baseline critical diameter to the
   margined critical diameter using the power-law exponent.
6. Derive the margined PNP from the margined expected-impact rate, and
   compare it against the mission's PNP requirement.
7. Before accepting the result, verify the flux margin factor used is
   not below the project's minimum required flux margin, and the
   diameter margin factor used is not above the project's maximum
   allowed (i.e. weakest permitted) diameter margin -- a margin weaker
   than the specified floor understates risk even though the workflow
   still runs.

## Pitfalls

- Applying only one of the two margins (e.g. margining the flux but
  comparing the unmargined critical diameter against it, or vice versa)
  -- clause 10.2.6 margins both the flux and the damage prediction, and
  omitting either one is non-conservative.
- Using a flux margin factor below 1.0 or a diameter margin factor
  above 1.0 -- either direction relaxes the prediction instead of
  adding margin, which defeats the purpose of the step.
- Comparing the unmargined PNP against the requirement because it looks
  more favorable, instead of the margined PNP that clause 10.2.6
  actually requires for compliance demonstration.
- Accepting a project-supplied margin factor that is weaker than the
  project's own stated minimum without flagging it.

## Behavior contract (gate 3)

The margin-application and margined-PNP derivation logic is exercised
by the gate 3 contract test: scripts/test_e1004_mm_margins.py against
scripts/e1004_mm_margins_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_mm_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
