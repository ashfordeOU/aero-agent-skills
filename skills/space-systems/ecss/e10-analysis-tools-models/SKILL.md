---
name: e10-analysis-tools-models
description: "Use when validate the analysis methods, tools and models behind a space system analysis before its results are used, under ECSS-E-ST-10C clause 5.3.4: decide whether a tool qualifies by heritage reuse or must be correlated, compute its correlation error against independently derived reference data, compare that error against the acceptance tolerance set by the analysis criticality, and aggregate every tool review into a single verdict on whether the analysis is valid. Trigger: ecss, e-st-10-system-scope, analysis-tools, model-qualification, tool-correlation, heritage-reuse, domain-of-applicability, analysis-criticality."
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
  tags: [ecss, e-st-10-system-scope, analysis-tools, model-qualification, tool-correlation, heritage-reuse, analysis-criticality]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Analysis Tools and Models (space-systems/ecss/e10-analysis-tools-models)

Use when the task is to establish that the analysis methods, tools and
models of ECSS-E-ST-10C clause 5.3.4 are qualified before their
results are relied on -- deciding per tool whether heritage covers the
present use, and correlating the tool against independent reference
data when it does not.

## Domain quick reference

- A tool's qualification basis is decided from two independent facts,
  not one: whether the tool is heritage, and whether its domain of
  applicability (physics regime, parameter range) has been confirmed
  for *this* analysis. Only the pair (heritage, domain confirmed)
  earns heritage reuse. A heritage tool pushed outside its confirmed
  domain is treated exactly like a new tool -- it must be correlated.
- Correlation error is the relative difference between the tool's
  prediction and an independently derived reference value (test data
  or a validated benchmark method), expressed as a percent of the
  reference. A zero reference value makes percent error undefined and
  is an input error, not a finding.
- The acceptance tolerance is set by the criticality of the analysis,
  not by the tool: a high-criticality analysis admits a narrow
  correlation error, a low-criticality one a wide band. The same tool
  and the same correlation error therefore pass in one analysis and
  fail in another.
- A tool on a correlation basis is qualified only when both the
  correlation error and the tolerance are on record. Missing
  correlation data is an input error -- a tool cannot be quietly
  passed for want of evidence.
- An analysis is valid only when every tool backing it is qualified.
  Each tool is reviewed exactly once; a repeated tool identifier is an
  input error, and an analysis with no reviewed tool has nothing
  qualifying it at all.

## Workflow

1. Collect every analysis tool and model whose output feeds the
   engineering decision, each with a unique identifier.
2. For each tool, determine the qualification basis from its heritage
   flag and the confirmation of its domain of applicability for this
   analysis.
3. For a tool on a heritage-reuse basis, record it as qualified and
   move on -- no correlation is required.
4. For a tool requiring correlation, take the acceptance tolerance
   from the analysis criticality, compute the correlation error
   against the reference value, and compare the two.
5. Aggregate the per-tool verdicts; the analysis is valid only when
   the issue list is empty, and each exceeded tolerance is reported
   against the tool that caused it.

## Pitfalls

- Reading "heritage tool" as sufficient on its own -- heritage earns
  reuse only inside the domain the heritage record actually covers, so
  a flight-proven tool applied to a new regime still needs correlation.
- Applying one fixed correlation tolerance across the programme -- the
  tolerance follows the criticality of the analysis being supported,
  so the acceptance band must be re-derived per analysis.
- Passing a correlation-basis tool whose error or tolerance was never
  captured. Absent evidence is not weak evidence; the review must stop
  rather than assume the tool is fine.
- Computing percent correlation error against a zero reference and
  reporting the result as a large-but-finite error -- the quantity is
  undefined and must be rejected at the input.
- Averaging correlation errors across the tools behind an analysis. A
  single tool outside its tolerance invalidates the analysis; good
  agreement elsewhere does not compensate for it.

## Behavior contract (gate 3)

The qualification-basis, tolerance, correlation-error, per-tool verdict
and aggregation logic is exercised by the gate 3 contract test:
scripts/test_e10_analysis_tools_models.py against
scripts/e10_analysis_tools_models_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e10_analysis_tools_models.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
