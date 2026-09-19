---
name: q6015-radiation-analysis-report-deliverable
description: "Review the radiation analysis report deliverable for content and traceability. Use when ECSS-Q-ST-60-15C Annex B has to be applied to that report: confirm it carries the analysed configuration, the environment inputs, a section per radiation effect, the applied margins, the mitigation decisions, the test evidence and the parts-list cross-reference, then take each analysis entry and require a margin against its stated requirement, a named mitigation decision behind every shortfall, and a real dated test reference rather than a placeholder or evidence dated after the report itself. Trigger: ecss, q-st-60-15c-annex-b, radiation-analysis-report-content, applied-margin-traceability, mitigation-decision-record, radiation-test-evidence-reference, placeholder-evidence-detection."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-radiation-analysis-report-deliverable, q-st-60-15c-annex-b, radiation-analysis-report-content, applied-margin-traceability, mitigation-decision-record, radiation-test-evidence-reference, placeholder-evidence-detection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Analysis Report Deliverable (space-systems/ecss/q6015-radiation-analysis-report-deliverable)

Use when the task is the analysis report of ECSS-Q-ST-60-15C Annex B —
deciding whether the document that records what the radiation
programme concluded actually carries the analyses, the margins, the
decisions and the evidence behind them, entry by entry.

## Domain quick reference

- The report is the deliverable the programme is judged on later, so
  it is graded on traceability rather than on the conclusion. A
  correct conclusion nobody can re-derive is worth very little at the
  next review, at a design change, or at a recurrence.
- Its sections follow the work: what configuration was analysed, what
  environment inputs were read, one section for each radiation effect
  analysed, the margins applied, the decisions taken, the test
  evidence supporting them, and the cross-reference back to the parts
  list that says the analysis set covers the hardware.
- An entry is a part and an effect. It carries a margin and the
  requirement that margin was held to, and without both there is
  nothing to grade — the entry is reported as incomplete rather than
  graded against an assumed requirement.
- Where the margin did not meet the requirement, the report has to
  say what was done. A part changed, shielding added, circuit
  mitigation applied, lot acceptance testing imposed, a waiver
  requested, an operational workaround adopted: naming the decision is
  what turns a shortfall into a closed item.
- Evidence is a reference with a date. A placeholder in that field is
  worse than an empty one, because it reads as traceability at a
  glance and survives review, and it is reported as its own finding
  for that reason.
- Evidence dated after the report did not exist when the conclusion
  was drawn. Either the report was signed early or the reference
  points at the wrong test; both are worth knowing.
- An entry for an effect the report has no section for means the
  analysis was done and not reported. The cross-check between entries
  and sections catches the document that grew out of step with the
  work behind it.

## Workflow

1. Validate the report: an ISO report date, a non-empty list of known
   and unique sections, and a non-empty list of entries with no part
   and effect repeated.
2. Validate each entry: a part reference, a known effect, a margin and
   a positive margin requirement when given, a mitigation decision
   from the known set when given, and a well-formed evidence record.
3. Compare the declared sections with the required set and list what
   is missing, keeping the ratio so partial progress is visible.
4. For each entry, check its effect's section is actually in the
   report.
5. Require both a margin and a requirement; report the entry and stop
   grading it when either is absent.
6. Compare margin with requirement, letting an exact equality pass
   under a named relative tolerance, and require a named mitigation
   decision behind every shortfall.
7. Require a test evidence reference that is neither absent nor a
   placeholder, carrying a date that is not after the report date.
8. Report the missing sections, the per-entry findings, the two
   completeness ratios, the worst margin-over-requirement ratio and
   one verdict.

## Pitfalls

- Grading the report on whether its conclusion is right. The
  conclusion is not the deliverable; the trail that supports it is.
- Accepting "to be determined" in an evidence field. It is the single
  most survivable defect in a report of this kind, because it looks
  populated in every summary view.
- Grading an entry against an assumed requirement when the report did
  not state one. The assumption becomes the record.
- Treating a shortfall as closed because it is described. A shortfall
  is closed by a named decision, not by a paragraph acknowledging it.
- Overlooking evidence dated after the report. The date ordering is
  the cheapest check in the deliverable and it catches both an early
  signature and a mis-pointed reference.
- Reporting section coverage without cross-checking the entries. A
  report can carry every required heading and still contain an
  analysis whose section was never written.
- Failing an entry whose margin lands exactly on its requirement. It
  met it; the equality is settled inside the comparison.

## Behavior contract (gate 3)

The report and entry validation, required-section comparison with its
ratio, entry-to-section cross-check, margin and requirement
completeness, shortfall-to-decision rule at exact equality, evidence
reference, placeholder and date-ordering checks, the worst margin
ratio and the aggregation are exercised by the gate 3 contract test:
scripts/test_q6015_radiation_analysis_report_deliverable.py against
scripts/q6015_radiation_analysis_report_deliverable_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6015_radiation_analysis_report_deliverable.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
