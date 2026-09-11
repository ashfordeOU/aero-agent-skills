---
name: e1011-assessment-process
description: "Use when run the continuous assessment process for a space system project under ECSS-E-ST-10 clause 4.10.1: categorize each finding by type (observation, action item, non-conformance), evaluate technical performance measures against their thresholds to derive a nominal/marginal/exceeded status, determine closure validity for each finding, compute the overall compliance status across all open findings and measure outcomes, and generate the structured Annex C assessment-report fields. The process applies at every review event across all project phases; open non-conformances and exceeded thresholds both block a compliant outcome. Trigger: ecss, e-st-10-system-scope, continuous-assessment, technical-performance-measure, finding-categorization, review-event, annex-c-report, compliance-status."
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
  tags: [ecss, e-st-10-system-scope, continuous-assessment, technical-performance-measure, finding-categorization, review-event, annex-c-report, compliance-status]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Systems Engineering — Continuous Assessment Process (space-systems/ecss/e1011-assessment-process)

Use when the task is to run the continuous assessment process defined in
ECSS-E-ST-10 clause 4.10.1 — categorizing findings from review events,
evaluating technical performance measures (TPMs) against their threshold
bands, tracking finding closure, and producing the structured Annex C
assessment-report fields.

## Domain quick reference

- Clause 4.10.1 establishes assessment as an ongoing activity that runs at
  every major review event across all project phases (Phase 0 through F).
  At each event the responsible engineer gathers findings and TPM readings,
  evaluates them against criteria, and records the outcome in the Annex C
  report format.
- Findings are categorized into exactly one of three types before they
  enter the tracking register:
  - **observation** — a noted deviation or potential risk that does not
    mandate a corrective action on its own but must be recorded and
    monitored;
  - **action item** — a directed task that must be completed and closed
    before the project can advance past the associated milestone;
  - **non-conformance** — a verified departure from a stated requirement;
    a non-conformance that remains open drives the overall assessment
    status to non-compliant.
- TPMs are the quantitative indicators chosen to track achievement of
  critical technical requirements (e.g., total system mass, power margin,
  link budget margin). Each TPM is evaluated against a threshold boundary
  (maximum or minimum permitted value). A reading within 10 % of the
  boundary is marginal; beyond it is exceeded. An exceeded TPM drives the
  status to at-risk.
- The Annex C report is the normative output format; its required fields
  are: record identifier, event name and date, project phase, scope
  description, finding counts by status (open/closed/waived), the open
  finding identifiers, the TPM status per measure, and the single overall
  status derived from combining finding and measure outcomes.

## Workflow

1. At the start of each review event, assign a unique record identifier
   and record the event name, date (YYYY-MM-DD), project phase, and scope
   description.  Reject any record with an empty identifier, name, or
   scope, or with a date that does not conform to ISO 8601.
2. Inventory every finding raised during or since the previous event.
   For each finding, confirm its type is one of observation / action_item /
   non_conformance (reject any unrecognised type before it enters the
   register).  Record the responsible party; a finding with no responsible
   party cannot be tracked to closure.
3. For each finding whose status is "closed" or "waived", verify closure
   validity: the finding must have a non-empty identifier, a description,
   and a responsible party; a waived finding additionally requires a
   documented rationale.  Flag any gap as a structural defect in the
   record.
4. Collect the current reading for every TPM in scope.  For each TPM,
   determine whether the reading is nominal (comfortably within the
   threshold), marginal (within 10 % of the threshold boundary), or
   exceeded (beyond the boundary), using the max/min threshold type
   appropriate to that measure.
5. Derive the overall assessment status by applying the priority rules:
   - **non_compliant** if any non-conformance finding is open;
   - **at_risk** if any TPM is exceeded, or if any action item is open
     (and no open non-conformance exists);
   - **marginal** if any TPM is marginal (and no higher-priority condition
     applies);
   - **compliant** if all findings are closed or waived and all TPMs are
     nominal.
6. Populate the Annex C report fields.  Confirm that the count of
   measure-status entries matches the count of measures in the record;
   a mismatch is a structural error.  Deliver the report dict for
   archiving or onward review.

## Pitfalls

- Treating a finding with no responsible party as "open but trackable" —
  an unowned finding cannot be driven to closure and represents a gap in
  the assessment governance, not a routine open item.
- Collapsing marginal and exceeded TPMs into a single "at-risk" label and
  losing the distinction — marginal allows the project to proceed with
  monitoring, whereas exceeded triggers active corrective measures; the
  two must remain separate in the register.
- Leaving a waived finding's rationale blank and recording the status as
  waived — a waiver without documented rationale has the same evidential
  weight as no decision at all; the record must be rejected until the
  rationale is supplied.
- Skipping the structural validation step and populating Annex C fields
  directly — validation gates catch empty identifiers, malformed dates,
  unrecognised types, and mismatched measure counts before they propagate
  into the archived report.
- Treating "no findings" as automatically "compliant" — the overall status
  is compliant only when both the finding register and the TPM set are
  explicitly clear; a record with no measures defined cannot confirm TPM
  health.

## Behavior contract (gate 3)

The finding-categorization, TPM-evaluation, closure-validity, overall-
status, Annex-C generation, and record-validation logic is exercised by
the gate 3 contract test:
scripts/test_e1011_assessment_process.py against
scripts/e1011_assessment_process_logic.py (stdlib unittest, offline). Run:

```
python3 scripts/test_e1011_assessment_process.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
