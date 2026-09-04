---
name: internal-quality-audit
description: "Use when you must plan and score an internal quality audit program under an AS9100-style quality management system: compute the audit due date from the last audit date, the base interval and the process risk category, check auditor independence and competence for the assigned audit scope, size the record sample from the lot size and confidence level, and categorize an audit finding by impact severity, containment need and systemic spread. Produces the audit schedule, the auditor assignment verdict, the sample size, the finding classification, and the closure verdict that gate an internal audit program. Trigger: internal-quality-audit, audit-schedule, auditor-independence, audit-sample-size, finding-classification, closure-verification."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: as9100
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [internal-quality-audit, audit-schedule, auditor-independence, audit-sample-size, finding-classification, closure-verification]
  version: 0.1.0
  author: AeroSkills
---

# Internal Quality Audit Program (manufacturing-quality/as9100/internal-quality-audit)

Use when the task is planning and scoring an internal quality audit
program under an AS9100-style quality management system: scheduling
audits by process risk, checking auditor independence and competence
for the assigned scope, sampling records, categorizing findings, and
verifying closure of corrective action responses. This leaf implements
the audit program mechanics in pure Python, stdlib only, with no
randomness. It pairs with manufacturing-quality/as9100/quality, which
maps audit focus areas to AS9100 clauses and shapes the auditor
evidence plan, and with manufacturing-quality/as9100/corrective-action,
which owns the corrective action response record. AS9100 is referenced,
not reproduced; the model below is the leaf audit program methodology.

## Domain quick reference

- Audit interval: base_interval_months (12.0 default) times the risk
  multiplier, RISK_MULTIPLIERS = {low: 1.5, medium: 1.0, high: 0.5}.
  High risk processes are audited more often, so the interval is
  shorter. The due date is the last audit date plus that span in
  calendar months with the day clamped to the target month end, so a
  high risk audit 6 months after 2026-03-15 is due 2026-09-15.
- Auditor independence: the auditor must not be the area owner, and no
  conflict may be declared for the assignment.
- Auditor competence: every required area must appear in the auditor
  qualification list (case insensitive substring match).
- Record sampling: n = ceil(sqrt(lot_size) * factor), factor 1.0 at
  0.95 confidence, 1.2 at 0.99, 0.8 at 0.90, interpolated between the
  anchors, at least 1 record.
- Finding ladder: impact severity 4-5 or containment required gives a
  major nonconformity; severity 2-3 gives minor, and systemic spread
  escalates minor to major; severity 1 is an opportunity for
  improvement.
- Closure verdict: the corrective action response closes the finding
  only when the corrective action taken, the root cause statement and
  the effectiveness check are all present.
- Confidence bounds: lot sizes below 1, confidence outside [0.5,
  0.999] and severity outside 1-5 are rejected with ValueError.

## Workflow

1. Schedule the audit: audit_due_date(last_audit_date_iso,
   risk_category, base_interval_months) returns the due date ISO
   string, with the risk multiplier shortening high risk intervals.
2. Check the assignment: auditor_independent(auditor_name,
   area_owner_name, independence_ok) returns {independent, reason}.
3. Check the qualifications: auditor_competent(qualifications,
   audit_scope_areas, required_areas) is True when every required area
   is covered by the qualification list.
4. Size the sample: audit_sample_size(lot_size, confidence_level)
   returns the number of records to pull from the lot.
5. Categorize each finding: classify_finding(impact_severity,
   containment_required, systemic) returns major, minor or ofi.
6. Verify the response: verify_closure(corrective_action_taken,
   root_cause_stated, effectiveness_check) gates the finding closed.
7. Chain the whole review: internal_audit_review(...) returns the
   schedule, interval, independence and competence verdicts, sample
   size, finding category and closure verdict in one dict.
8. Confirm the deterministic checks with the contract test
   scripts/test_internal_quality_audit.py.

## Worked example

Last audit 2026-03-15 on a high risk process (multiplier 0.5 gives a
6 month interval), 400 records at 95% confidence, auditor A. Chen
against area owner B. Lopez, required areas [calibration, corrective
action] with matching qualifications, impact severity 3 with
containment required and no systemic spread. Running the module prints:

- due_date "2026-09-15" (6.0 calendar months, the about-2026-09-15
  bound holds).
- interval_months 6.0.
- auditor_independent True (auditor differs from the owner, no
  conflict).
- auditor_competent True (both required areas are qualified).
- sample_size 20 (ceil(sqrt(400)) = 20 at 0.95, inside the 15-25
  bound).
- finding_classification "major" (containment required escalates).
- closure_verified True (all three response elements are set).

## Verification

- audit_due_date clamps month ends: 2026-01-31 plus 1 month gives
  2026-02-28, and 2024-01-31 gives 2024-02-29 in the leap year.
- Malformed dates, unknown risk categories, empty required area lists,
  lot sizes below 1, confidence outside [0.5, 0.999] and impact
  severity outside 1-5 all raise ValueError.
- auditor_independent is False when the auditor name matches the owner
  name (case insensitive) or when a conflict is declared.
- audit_sample_size(400) is 20 at 0.95, 24 at 0.99 and 16 at 0.90.
- classify_finding: severity 5 or containment required gives major;
  severity 2-3 systemic gives major; severity 2-3 alone gives minor;
  severity 1 gives ofi.
- verify_closure is False when any of the three elements is missing.
- Determinism: no RNG anywhere, run-to-run identical output.
- Run the contract test offline: python3
  scripts/test_internal_quality_audit.py (30 tests, deterministic).

## Related leaves

- manufacturing-quality/as9100/quality: maps audit focus areas to
  AS9100 clauses and shapes the evidence plan for each focus area.
- manufacturing-quality/as9100/corrective-action: owns the corrective
  action response record that this leaf gates on closure.
- manufacturing-quality/as9100/calibration-control: the calibration
  records an audit may sample.
- manufacturing-quality/as9100/nonconformance-control: disposition of
  product records an audit finds nonconforming.
- manufacturing-quality/as9100/supplier-control: external provider
  audits belong to supplier control, not to this internal audit leaf.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_internal_quality_audit.py

The test covers risk-based scheduling with month end clamping, the
independence rule including declared conflicts, competence against the
required areas, the sample size formula at the confidence anchors,
the finding ladder with systemic and containment escalation, closure
verification, the worked example outputs inside the spec magnitude
bounds, exact result keys, ValueError rejection of every non-physical
input, and run-to-run determinism.

## Compliance

- Standards referenced, not reproduced: AS9100 is a commercial SAE
  standard; the audit program equations above are the leaf audit
  program methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
