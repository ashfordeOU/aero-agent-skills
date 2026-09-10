---
name: e1002-sw-tools
description: "Use when a software tool (simulation code, FEM solver, thermal/analysis package) is being used to generate verification-by-analysis evidence under ECSS-E-ST-10-02C and needs a qualification check before its output is accepted: was the tool validated, is it under configuration control, are the analysis conditions inside its validated domain, and does a safety-critical use have an independent cross-check, consistent with the tool/model validation principle of E-ST-10 §5.3.4. Trigger: software tool qualification, verification by analysis, analysis tool validation, tool configuration control, validated domain, independent check, e1002, e-st-10-02, ecss."
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
  tags: [ecss, e-st-10-02c, verification-by-analysis, software-tool-qualification, configuration-control, validated-domain]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Software Tool Qualification for Verification by Analysis (space-systems/ecss/e1002-sw-tools)

Use when the task is qualifying a software tool used to produce
verification-by-analysis evidence under ECSS-E-ST-10-02C, before that
tool's output is accepted into the verification close-out record.

## Domain quick reference

- ECSS-E-ST-10-02C clause 5.2.6.5 requires that software tools used
  for verification by analysis be qualified for that use, consistent
  with the general tool/model validation principle of ECSS-E-ST-10C
  clause 5.3.4 (analysis methods, tools and models are validated
  before use, within a stated domain of applicability).
- Qualification rests on four checks: the tool has been validated
  (against reference cases, benchmarks, or correlated test data); the
  specific tool version is under configuration control for the
  analysis campaign (an unfrozen tool can drift mid-campaign); the
  actual analysis conditions fall inside the tool's validated domain
  (parameter ranges, physics assumptions the validation covered); and,
  for a safety-critical or high-consequence use, an independent
  cross-check exists (alternate tool, hand calculation, or
  code-to-code comparison).
- A tool that fails any earlier check is not qualified for that use
  regardless of how the later checks would have come out -- the
  checks are a precedence chain, not independent votes.
- This leaf qualifies the tool for one analysis use; classifying the
  tool into a qualification category (A/B/C/D) is the sibling
  e1002-tools-general leaf, and validating analysis methods/tools/
  models in general (not software-specific) is the sibling
  e10-analysis-tools-models leaf.

## Workflow

1. For each software tool use supporting a verification-by-analysis
   case, capture: whether the tool itself has been validated, whether
   the version in use is under configuration control, the tool's
   validated domain (per-parameter ranges it was validated over), and
   the actual analysis conditions (per-parameter values used in this
   run).
2. Check the analysis conditions against the validated domain: any
   parameter used in the analysis that is missing from the validated
   domain or falls outside its range is out-of-domain for this use.
3. Determine qualification status by precedence: not validated ->
   not qualified; validated but not configuration-controlled ->
   qualified pending configuration control; validated and controlled
   but out-of-domain -> qualified out of domain; validated, controlled,
   in-domain, safety-critical without an independent check -> qualified
   pending independent check; otherwise -> qualified.
4. Build the qualification record for the full set of tool uses feeding
   an analysis report or the Design Justification File, and identify
   every use whose status is anything other than qualified.
5. Route every non-qualified use back to disposition (re-validate the
   tool, freeze its configuration, re-run inside the validated domain,
   or add an independent check) before its output is accepted as
   verification-by-analysis evidence in the VCD close-out.

## Pitfalls

- Accepting analysis output from a tool that is validated in general
  but was run outside the domain (parameter range, assumptions) the
  validation actually covered.
- Treating "validated" and "configuration controlled" as the same
  check -- a validated tool whose version drifts mid-campaign is no
  longer known-good for the campaign's results.
- Skipping the independent-check requirement for a safety-critical
  analysis because the tool itself is otherwise qualified.
- Letting one non-qualified tool use quietly ride along inside an
  otherwise-qualified analysis report instead of flagging it for
  disposition.

## Behavior contract (gate 3)

The domain-check, qualification-precedence, record-building, and
acceptance logic is exercised by the gate 3 contract test:
scripts/test_e1002_sw_tools.py against
scripts/e1002_sw_tools_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_sw_tools.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
