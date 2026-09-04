# Wave-31 leaf spec: internal-quality-audit (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/internal-quality-audit/
- Pack: as9100 (siblings: calibration-control, corrective-action,
  counterfeit-prevention, document-control, fod-control,
  measurement-systems-analysis, nonconformance-control, quality,
  risk-management, statistical-process-control, supplier-control). The quality
  leaf maps an audit FOCUS AREA to aerospace clauses and shapes the auditor's
  evidence plan; corrective-action owns the 8D closure of a nonconformance.
  Neither owns the internal audit PROGRAM itself: scheduling audits by risk,
  auditor independence and competence rules, audit sampling, nonconformity
  classification, and closure verification. This leaf fills the audit-program
  gap (grep receipt at prep: no audit schedule/auditor independence content).
- Standards ids: as9100 (reference-only). Ledger Standard: as9100.
- Family: manufacturing-quality

## Claim

Plan and score an internal quality audit program under an AS9100-style quality
management system: compute the audit due date from the last audit date, the
base interval, and the process risk category; check auditor independence and
competence for an assigned audit scope; size the record sample from the lot
size and the confidence level; classify an audit finding as an opportunity for
improvement, minor nonconformity, or major nonconformity from the impact and
the containment need; and verify that a corrective action response closes the
finding. Produces the audit schedule, the auditor assignment verdict, the
sample size, the finding classification, and the closure verdict that gate an
internal audit program.

Does NOT do: map audit focus areas to aerospace clauses (quality owns the
clause mapping and evidence plan); run the 8D corrective action record
(corrective-action owns CAPA closure); supplier audits (supplier-control owns
external provider control); first article inspection (the as9102 leaves own
FAI); document control (document-control). This leaf is the audit program
mechanics only: schedule, independence, sampling, classification, closure.

## Model (implement exactly)

Module constants:
- BASE_INTERVAL_MONTHS = 12.0 (default audit interval).
- RISK_MULTIPLIERS = {"low": 1.5, "medium": 1.0, "high": 0.5} (high-risk
  processes are audited more often, so the interval is shorter).

Functions (pure stdlib):
- audit_due_date(last_audit_date_iso, risk_category,
  base_interval_months=BASE_INTERVAL_MONTHS) -> str: due date ISO string =
  last date + base_interval * RISK_MULTIPLIERS[risk_category] months
  (calendar months, day clamped to the month end). ValueError if the date is
  malformed or risk_category not in RISK_MULTIPLIERS. Use only the stdlib
  datetime and calendar modules.
- auditor_independent(auditor_name, audit_area, independence_ok=True) ->
  dict: {independent: bool, reason} where independent is False when the
  auditor_name matches the audit_area owner name passed in the audit scope
  (the function receives auditor_name, area_owner_name, and checks they
  differ, plus the independence_ok flag for a declared conflict). Returns
  {independent, reason}.
- auditor_competent(qualifications, audit_scope_areas, required_areas) ->
  bool: True when every required area appears in the auditor's qualification
  list (case-insensitive substring match). ValueError if required_areas is
  empty.
- audit_sample_size(lot_size, confidence_level=0.95) -> int: square-root
  sample size rounded up: ceil(sqrt(lot_size)) scaled by the confidence
  factor (1.0 at 0.95, 1.2 at 0.99, 0.8 at 0.90); at least 1.
  ValueError if lot_size < 1 or confidence_level outside [0.5, 0.999].
- classify_finding(impact_severity, containment_required, systemic) -> str:
  "major" when impact_severity >= 4 or containment_required; "minor" when
  impact_severity >= 2; else "ofi" (opportunity for improvement); systemic
  True escalates minor to major. ValueError if impact_severity not in 1-5.
- verify_closure(corrective_action_taken, root_cause_stated,
  effectiveness_check) -> bool: True only when all three are truthy.
- internal_audit_review(last_audit_date_iso, risk_category, lot_size,
  auditor_name, area_owner_name, required_areas, qualifications,
  impact_severity, containment_required, systemic,
  corrective_action_taken, root_cause_stated, effectiveness_check,
  base_interval_months=BASE_INTERVAL_MONTHS,
  confidence_level=0.95) -> dict: convenience chain returning {due_date,
  interval_months, auditor_independent, auditor_competent, sample_size,
  finding_classification, closure_verified}.

## Worked example

Last audit 2026-03-15, risk category high (interval multiplier 0.5 -> 6
months), lot size 400 records at 95% confidence, auditor "A. Chen" vs area
owner "B. Lopez", required areas ["calibration", "corrective action"],
qualifications ["calibration", "corrective action", "document control"],
impact severity 3 with containment required and systemic False.

Deterministic anchors (run your module, take the printed values as the assert
targets, then CHECK the magnitude bounds):
- due date about 2026-09-15 (6 calendar months after 2026-03-15).
- interval_months 6.0.
- auditor_independent True (auditor differs from the owner, no conflict).
- auditor_competent True (both required areas are qualified).
- sample_size in 15-25 (ceil(sqrt(400)) = 20 at 0.95).
- finding classification "major" (containment required escalates).
- closure_verified True when all three inputs are set.
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: malformed date, unknown risk category, empty required_areas,
  lot_size < 1, confidence outside [0.5, 0.999], impact_severity outside 1-5.
- audit_due_date clamps month-end correctly (2026-01-31 + 1 month ->
  2026-02-28).
- auditor_independent False when auditor_name equals area_owner_name or when
  independence_ok is False.
- classify_finding: severity 5 -> major; severity 1 -> ofi; severity 3
  systemic -> major; severity 2 not systemic -> minor.
- verify_closure False when any input is missing.
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-internal-quality-audit.yaml)

Query 1 (copy verbatim):
  "schedule an internal-quality-audit under as9100: compute the audit-schedule due date from the risk category and check auditor-independence for the assigned scope"
  intent: "manufacturing-quality; as9100 internal audit scheduling and independence"
  expected_skill: "manufacturing-quality/as9100/internal-quality-audit"
Query 2 (copy verbatim):
  "classify an internal-quality-audit finding with the finding-classification rules and verify the closure-verification of the corrective action for an aerospace quality management system"
  intent: "manufacturing-quality; as9100 audit finding classification and closure"
  expected_skill: "manufacturing-quality/as9100/internal-quality-audit"
Task ids: w31-internal-quality-audit-1 and -2.

Forbidden tokens that belong to siblings: do NOT use eight-discipline, 8D,
CAPA, root cause investigation steps (corrective-action), clause mapping,
focus area scoring (quality), FAI, first article (as9102), supplier approval
(supplier-control), document master list (document-control).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must plan and score an internal quality
audit program under an AS9100-style quality management system:" and include
the outputs listed in the Claim. First tag: internal-quality-audit.
Additional tags only: audit-schedule, auditor-independence,
audit-sample-size, finding-classification, closure-verification. NEVER single
generic words (audit, quality, finding, schedule, sample). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.
