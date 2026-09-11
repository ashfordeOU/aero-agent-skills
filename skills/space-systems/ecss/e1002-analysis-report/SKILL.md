---
name: e1002-analysis-report
description: "Use when determine whether an analysis report actually verifies its requirement under ECSS-E-ST-10-02 clause 5.3.2.2: confirm the analysis was run against the design baseline under verification rather than a superseded model, confirm every case the requirement's envelope demands was analysed and flag cases that drifted outside it, confirm each case carries a verdict and that a case not run states why, and roll the case results up to a requirement verdict. Trigger: ecss, e-st-10-02c, analysis-report, verification-by-analysis, case-coverage, model-baseline, envelope, verdict-rollup."
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
  tags: [ecss, e-st-10-02c, analysis-report, verification-by-analysis, case-coverage, model-baseline, verdict-rollup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Analysis Report as Evidence (space-systems/ecss/e1002-analysis-report)

Use when the task is to decide whether an analysis report discharges its
requirement under ECSS-E-ST-10-02 clause 5.3.2.2. The report's own content
is a separate question (Annex S); this is the verification question --
right baseline, whole envelope, sound roll-up.

## Domain quick reference

- Three things a content check cannot see decide whether an analysis
  verifies anything: was it run on the design actually being verified,
  did it cover the whole envelope the requirement demands, and does the
  case-by-case result roll up soundly.
- An analysis run on a superseded model configuration is evidence about
  a design that no longer exists. It can be immaculate and still verify
  nothing.
- An unstated baseline and a superseded one are different failures. The
  first is unrecorded and might be right; the second is known-wrong.
  Reporting them identically hides which one you have.
- Envelope coverage is checked against the requirement's required case
  list, not against the analysis's own matrix. A matrix is complete
  with respect to itself by construction; the question is whether it
  covers what the requirement asks.
- A case analysed outside the required envelope is reported but is not a
  defect. Extra coverage is welcome; a matrix that has quietly drifted
  away from the requirement is worth seeing.
- Case verdicts roll up severity-ordered: one failure fails the
  requirement, any case not run leaves it incomplete, only an all-pass
  matrix verifies it.
- A case not run needs a reason, because "enveloped by the launch case"
  and "we ran out of time" are both common and close very differently.
- Passing every case analysed is not verification if a required case was
  never analysed. The verdict can read pass while the requirement stays
  unverified, which is exactly why coverage is a separate check.

## Workflow

1. Confirm the report names the model baseline and that it matches the
   design baseline under verification.
2. Check each analysis case for a verdict, and a not-run case for its
   reason; reject duplicate case identifiers.
3. Compare the analysed cases against the requirement's required
   envelope; report each required case with no analysis.
4. Report analysed cases lying outside the required envelope.
5. Roll the case verdicts up to the requirement under the severity
   ordering.
6. The requirement is verified only when the roll-up passes and no
   finding stands.

## Pitfalls

- Accepting an analysis whose model predates the last design change.
  The numbers are right about the wrong article.
- Judging coverage from the analysis matrix instead of the
  requirement's envelope, which is circular and always passes.
- Reading an all-pass verdict as verification while a required case was
  never run. The roll-up only speaks about cases that exist.
- Treating a case outside the envelope as a defect and forcing its
  removal, losing coverage that cost real effort.
- Leaving a not-run case unexplained, so a deliberate enveloping
  argument is indistinguishable from a gap.
- Letting two cases share an identifier, so one verdict overwrites
  another in the roll-up.

## Behavior contract (gate 3)

The baseline-match, envelope-coverage, extraneous-case, case-verdict and
severity-ordered roll-up logic is exercised by the gate 3 contract test:
scripts/test_e1002_analysis_report.py against
scripts/e1002_analysis_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_analysis_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
