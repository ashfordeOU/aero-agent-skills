---
name: q40-safety-analysis-report
description: "Produce the safety analysis report of ECSS-Q-ST-40C clause 7.5 to its Annex D data requirement: hold the section order, validate each hazard report for severity, causes, controls and a verification behind every control, trace each cause back to a FMEA/FMECA failure mode or a fault-tree basic event, expose the critical items no hazard report covers, and derive a status from the content so a hazard declared closed on an unverified control is caught. Use when the report is compiled, updated after an analysis run, or reviewed for closure. Trigger: ecss, q-st-40c-annex-d, ecss-safety-analysis-report, hazard-report-data-requirement, hazard-cause-traceability, fmeca-to-hazard-report-link, fault-tree-basic-event-trace."
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
  tags: [ecss, q-st-40c-safety-assurance-scope, q40-safety-analysis-report, ecss-safety-analysis-report, hazard-report-data-requirement, hazard-cause-traceability, fmeca-to-hazard-report-link, fault-tree-basic-event-trace]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Safety Analysis Report (space-systems/ecss/q40-safety-analysis-report)

Use when the task is clause 7.5 of ECSS-Q-ST-40C with the Annex D data
requirement: the safety analysis report is being compiled or reviewed, and its
hazard reports have to carry the outputs of the hazard analysis, the
FMEA/FMECA and the fault tree rather than restate them.

## Domain quick reference

- The report is an integration, not a fourth analysis. Its hazard reports are
  where the hazard analysis, the FMEA/FMECA and the fault tree meet, so every
  cause named in a hazard report points at a failure mode or a basic event
  that some analysis actually produced.
- A cause with no reference is the common defect. It reads as complete prose
  and traces to nothing, which is why an absent reference is graded exactly
  like a reference to an output that does not exist.
- Traceability runs both ways. Causes tracing to analyses is one direction;
  the critical items the FMECA raised and no hazard report covers is the
  other, and only the second one finds the hazard nobody wrote up.
- A control is not a control until something verifies it. The verification
  reference is what separates an intention recorded in the report from a
  provision the reviewer can go and check.
- Status is derived, not declared. No controls is open, controls with a gap
  in their verification is controlled, and fully verified controls is closed;
  a declared status stronger than the content supports is a finding, while a
  more conservative declaration is accepted as the author's judgement.
- Section order is part of the data requirement. A reviewer reads many of
  these reports, and a section that has moved -- or vanished -- costs more
  time than the content in it.

## Workflow

1. Validate the submitted section list against the required order, reporting
   both the sections missing and a set printed out of order.
2. Validate each hazard report: known keys only, a non-empty title, a known
   severity, at least one cause, no repeated cause or control, and no
   verification naming a control the report does not list.
3. Trace every cause to the supplied failure modes and basic events; a cause
   with no reference, or one pointing at an output not supplied, is untraced.
4. Collect the controls with no verification behind them.
5. Derive the hazard report's status from its own content and compare it with
   any status declared, reporting only an over-declaration.
6. Take the critical items list and report every entry no hazard report names
   as a cause.
7. Roll up: the report is closable only when every hazard report derives
   closed, and the findings carry section gaps, untraced causes, unverified
   controls, over-declared statuses and uncovered critical items.

## Pitfalls

- Accepting prose causes. A cause written out in full but pointing at no
  analysis output is the same gap as a dangling reference, and it is graded
  the same way.
- Tracing only forwards. Every cause can trace cleanly while a critical item
  the FMECA raised has no hazard report at all.
- Taking the declared status. The content is the evidence; a hazard declared
  closed over a control nobody verified is the failure this check exists for.
- Penalising a conservative declaration. An author calling a closed hazard
  controlled is exercising judgement, not making an error, and flagging it
  trains people to declare closure.
- Treating section order as cosmetic. It is part of the data requirement and
  the only reason a reviewer can find the residual risk without reading the
  whole report.

## Behavior contract (gate 3)

The section order and gap detection, the hazard report validation and its
unknown-key, duplicate and dangling-verification refusals, the cause
traceability against failure modes and basic events, the unverified-control
collection, the derived-versus-declared status rule, the uncovered critical
item check and the closure roll-up are exercised by the gate 3 contract test:
scripts/test_q40_safety_analysis_report.py against
scripts/q40_safety_analysis_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_safety_analysis_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
