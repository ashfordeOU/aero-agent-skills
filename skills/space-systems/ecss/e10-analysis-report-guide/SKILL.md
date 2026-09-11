---
name: e10-analysis-report-guide
description: "Use when assemble an engineering analysis report to the ECSS-E-ST-10C Annex S content guideline so its result can be cited as verification evidence: confirm every required section carries content, confirm each input datum states where it came from, confirm the analysis tool is named with its qualification status, confirm every reported result carries an uncertainty, and confirm a compliance conclusion actually survives its own uncertainty against the limit. Trigger: ecss, e-st-10-system-scope, analysis-report, annex-s-guideline, input-provenance, tool-qualification, result-uncertainty, verification-evidence."
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
  tags: [ecss, e-st-10-system-scope, analysis-report, annex-s-guideline, input-provenance, result-uncertainty, verification-evidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Analysis Report Guideline (space-systems/ecss/e10-analysis-report-guide)

Use when the task is to assemble an engineering analysis report to the
content guideline of ECSS-E-ST-10C Annex S, so that its result can stand
as verification evidence under ECSS-E-ST-10-02 rather than as an opinion.

## Domain quick reference

- The test the whole guideline serves is re-derivability: could a
  competent reader reproduce this result from what the report contains?
  Every required section exists to make that possible, which is why a
  report missing one is not merely shorter -- its result is not evidence.
- An input without a stated source cannot be re-used, so it is a finding
  even when the number itself is correct. Provenance is what separates a
  datum from a recollection.
- The credibility of the result is bounded by the credibility of the
  tool, so the tool is named and its qualification status stated. An
  unstated status and an explicitly unqualified tool are different
  findings: one is an omission, the other a known limitation.
- A result with no uncertainty cannot be compared against a requirement
  at all. It is reported as a gap rather than treated as exact, because
  treating it as exact is precisely the error that produces false
  compliance.
- A "requirement met" conclusion must survive its own uncertainty. If
  the reported value plus its uncertainty crosses the limit, the report
  is claiming compliance on a margin thinner than its own error bar --
  the single most common way an analysis report overstates its result.
- That check applies only to a compliance claim. A "not met" or
  "inconclusive" conclusion needs no such support; it is not asserting
  the margin.
- A negative uncertainty is not a finding but an input error -- the
  quantity is malformed, and the report cannot be graded until it is
  fixed.

## Workflow

1. Check every required section for real content.
2. For each input datum, confirm a source is stated.
3. Confirm the analysis tool is named, then that its qualification
   status is stated and affirmative.
4. For each result, confirm an uncertainty is present and non-negative.
5. If the conclusion claims the requirement is met, confirm every result
   clears its limit with the uncertainty applied unfavourably.
6. The report may be cited as evidence only when no finding stands.

## Pitfalls

- Reporting a best-estimate result with no uncertainty and comparing it
  straight to the limit. The comparison looks decisive and carries no
  information about whether it is.
- Concluding compliance on a margin smaller than the stated uncertainty.
  The report contradicts itself, and a presence-only review passes it.
- Citing an input by value alone. A year later nobody can tell whether
  the load spectrum came from the launcher manual or a colleague.
- Naming the tool without its qualification status, which quietly
  transfers the question of credibility to the reader.
- Applying the conclusion-support check to a non-compliance verdict, and
  generating findings against a report that is correctly reporting a
  failure.
- Treating a negative uncertainty as a conservative value rather than a
  malformed one.

## Behavior contract (gate 3)

The section-completeness, input-provenance, tool-qualification,
result-uncertainty and conclusion-support logic is exercised by the gate
3 contract test: scripts/test_e10_analysis_report_guide.py against
scripts/e10_analysis_report_guide_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e10_analysis_report_guide.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
