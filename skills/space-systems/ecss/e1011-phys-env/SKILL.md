---
name: e1011-phys-env
description: "Use when assess the physical and psycho-physiological environments relevant to human performance under ECSS-E-ST-10-11C §4.2.1.6: categorize each environment parameter as physical (thermal, acoustic, vibration, lighting, or atmospheric composition) or psycho-physiological (workload, stress, sleep adequacy), verify that all required parameters have been assessed for the applicable mission phase, check each measured or predicted value against its human-performance acceptability bound, flag any parameter that falls outside the acceptable range, and confirm full coverage before closing the environment characterisation. Trigger: ecss, e-st-10-system-scope, e-st-10-11c, physical-environment, psycho-physiological, human-performance, thermal, acoustic, vibration, illuminance, atmospheric-quality."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-11c, physical-environment, psycho-physiological, human-performance, thermal, acoustic, vibration, illuminance, atmospheric-quality]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Physical and Psycho-physiological Environment Characterisation (space-systems/ecss/e1011-phys-env)

Use when the task is the physical and psycho-physiological environment
characterisation required by ECSS-E-ST-10-11C §4.2.1.6 -- categorizing
environment parameters, verifying assessment coverage across all mission
phases, checking each parameter value against its human-performance
acceptability bound, and flagging deficiencies before the characterisation
is declared complete.

## Domain quick reference

- §4.2.1.6 splits the environment into two families: physical parameters
  (thermal: temperature and humidity; acoustic: noise level; vibration:
  whole-body rms acceleration; lighting: illuminance; atmospheric
  composition: oxygen and CO2 partial pressures) and psycho-physiological
  parameters (workload index, stress/fatigue index, sleep adequacy metric).
  Each parameter is categorized into exactly one family before its value
  is checked.
- Each parameter carries an acceptability bound derived from HFE literature
  and applicable standards; a value within [lower_bound, upper_bound] is
  within the range that supports sustained human performance. A value
  outside that range is flagged as an exceedance, regardless of family.
- Coverage is required across all mission phases and operational contexts
  defined in the human-centred design planning document; a parameter not
  yet assessed is a coverage gap, which is itself a finding, not a pass.
- Bounds may be tightened by mission-specific requirements (e.g. a stricter
  CO2 limit for long-duration missions) by overriding the default bounds
  map; the default bounds supplied by this skill are the common HFE
  baseline, not a mission design rule.

## Workflow

1. Inventory every environment parameter relevant to the mission profile
   and categorize each one as physical or psycho-physiological. Reject an
   unrecognized parameter before it enters the assessment.
2. Verify that all required parameters have been assessed; list any
   parameter with no measured or predicted value as a coverage gap.
   Do not treat an uncovered parameter as implicitly acceptable.
3. For each assessed parameter, retrieve the applicable human-performance
   acceptability bound (use the default if no mission-specific bound is
   defined) and check whether the measured or predicted value falls within
   [lower_bound, upper_bound].
4. Flag every parameter whose value lies outside its bound as an
   exceedance; record the parameter name, measured value, and the bound
   that was violated.
5. Aggregate exceedances and coverage gaps into the environment review
   result; the characterisation is acceptable only when both lists are
   empty.
6. Report the full review result to the human-centred design planning
   process for integration into the context-of-use description.

## Pitfalls

- Omitting psycho-physiological parameters from the characterisation and
  treating only the physical environment as complete -- §4.2.1.6 explicitly
  requires both families; a characterisation with no workload, stress, or
  sleep data is an incomplete assessment.
- Using default bounds without checking for mission-specific overrides --
  long-duration or confined-habitat missions routinely impose tighter CO2
  and noise limits than the HFE baseline; applying the default bound in
  those contexts can mask a real exceedance.
- Treating a parameter with no assessed value as within bounds -- an
  unassessed parameter represents an unknown risk, not compliance; the
  correct finding is a coverage gap, not a pass.
- Collapsing all acoustic exceedances into a single "noise problem" flag
  without recording the measured value -- the exact level is needed to size
  the required mitigation and to verify that the corrected design brings the
  value back within bound.

## Behavior contract (gate 3)

The parameter categorization, bounds checking, coverage assessment, and
environment review aggregation logic is exercised by the gate 3 contract
test: scripts/test_e1011_phys_env.py against
scripts/e1011_phys_env_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_phys_env.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
