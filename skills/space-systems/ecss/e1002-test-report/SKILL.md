---
name: e1002-test-report
description: "Use when produce or review a verification test report against the ECSS-E-ST-10-02 clause 5.3.2.1 and Annex C Document Requirements Definition: confirm the report identifies the article, its configuration, the facility and the test procedure by revision, confirm the cited revision is the one actually run, confirm every test objective carries its own verdict, confirm each observed discrepancy is linked to a raised nonconformance, and aggregate the objective verdicts under a severity ordering. Trigger: ecss, e-st-10-02c, test-report, annex-c-drd, test-objectives, procedure-revision, discrepancy, nonconformance-link, measured-data."
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
  tags: [ecss, e-st-10-02c, test-report, annex-c-drd, test-objectives, procedure-revision, discrepancy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Test Report DRD (space-systems/ecss/e1002-test-report)

Use when the task is to produce or check the test report of
ECSS-E-ST-10-02 clause 5.3.2.1 and Annex C -- the record that turns a
test run into verification evidence against a specific article, a
specific facility and a specific procedure revision.

## Domain quick reference

- The report cites the test procedure *by revision*, and the cited
  revision must be the one actually executed. This is not a
  typographic class of defect: with the wrong revision the report
  describes a test that was not run, and every conclusion in it is
  attributed to the wrong method.
- An absent revision and a mismatched revision are handled by different
  checks, so a blank field is reported once as missing identification
  rather than twice.
- Identification is what lets data be attributed at all: article,
  configuration, facility, procedure and revision. Data that cannot be
  attributed to a specific article in a specific state is not evidence
  about anything.
- Every test objective carries its own verdict. A report is not a pass
  because most objectives passed -- each objective was written because
  it had to be demonstrated.
- An objective marked not performed needs a reason. Without one, the
  reader cannot distinguish a deliberate descope from an omission, and
  those close very differently.
- Overall verdict is severity ordered: any failure fails the report;
  otherwise anything not performed leaves it incomplete; only an
  all-pass set passes.
- A discrepancy with no nonconformance raised against it is an
  observation nobody is obliged to close. Linking it is what puts it
  into a process that ends in a disposition.
- Summarized results need a reference to the recorded data. Re-analysis
  is what makes test data evidence rather than testimony.

## Workflow

1. Check the identification fields; report each that is absent.
2. Compare the cited procedure revision against the revision actually
   run and report a mismatch.
3. For each objective, confirm a verdict is recorded, and that a
   not-performed objective carries its reason; reject duplicate
   objective identifiers.
4. For each discrepancy, confirm a nonconformance reference is present.
5. Confirm the measured data reference is present.
6. Aggregate the objective verdicts under the severity ordering.
7. The report is acceptable only when it passes and no finding stands.

## Pitfalls

- Citing the procedure without its revision, or carrying the revision
  from the plan rather than from what the operators actually ran.
- Reporting an overall pass because the failing objective was "minor".
  Severity belongs in the disposition of the nonconformance, not in the
  arithmetic of the verdict.
- Marking an objective not performed and leaving the reason to the
  reader, who cannot tell a descope from a miss.
- Recording a discrepancy in narrative text with no nonconformance
  raised. It reads as disclosed and enters no process.
- Presenting summarized results with no pointer to the recorded data,
  which makes independent re-analysis impossible.
- Letting two objectives share an identifier, so one verdict silently
  overwrites another in any downstream roll-up.

## Behavior contract (gate 3)

The identification, procedure-revision, objective-verdict,
discrepancy-linkage, data-reference and severity-ordered aggregation
logic is exercised by the gate 3 contract test:
scripts/test_e1002_test_report.py against
scripts/e1002_test_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_test_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
