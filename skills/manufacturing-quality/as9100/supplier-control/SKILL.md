---
name: supplier-control
description: "Use when you must control externally provided processes, products, and services: classify the supplier risk from part criticality and quality and delivery history, derive the required controls (on-site audit, monitoring frequency, delegated verification, flow-down), and check the supplier record for evaluation, approved supplier list, monitoring, re-evaluation, and flow-down completeness before approving the supplier. Produces the risk class, the control set, and the approval verdict that gate purchase release. Trigger: supplier evaluation, approved supplier list, flow down, external provider, supplier monitoring."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [supplier-control, external-provider, approved-supplier-list, flow-down, supplier-evaluation, supplier-monitoring, as9100, procurement-control]
  version: 0.1.0
  author: AeroSkills
---

# Supplier Control (manufacturing-quality/as9100/supplier-control)

Use when the task is controlling externally provided processes,
products, and services under AS9100 clause 8.4: supplier evaluation,
risk-based controls, requirement flow-down, performance monitoring and
re-evaluation, and the approved supplier list.

## Domain quick reference

- AS9100 clause 8.4 requires control of externally provided processes,
  products, and services (paraphrase): evaluate prospective suppliers
  before first use, define the required controls from risk and
  criticality, flow down applicable requirements (customer,
  regulatory, and special requirements), monitor performance, and
  re-evaluate suppliers periodically.
- Supplier risk class rule: criticality drives the class, history
  adjusts it. A critical part is always 'critical'. A major part with
  a quality or delivery score below 70 is 'high', otherwise 'medium'.
  A standard part with both scores at 90 or above is 'low', both at
  70 or above is 'medium', otherwise 'high'. Scores are 0..100,
  higher is better.
- Required controls by risk class: critical gets an on-site audit and
  quarterly monitoring; high gets an on-site audit and semi-annual
  monitoring; medium gets annual monitoring; low gets biennial
  monitoring. Delegated verification (the supplier verifies its own
  output) is allowed only for medium and low risk classes.
- Flow-down of requirements applies to every externally provided item:
  flow_down_required is True for all risk classes.
- A complete supplier record covers evaluation, approved supplier list
  membership, performance monitoring, periodic re-evaluation, and
  flowed-down requirements. A record missing any of the five is
  incomplete and the supplier is not approved.

## Workflow

1. Collect the part criticality (critical, major, standard) and the
   supplier quality and delivery history scores (0..100).
2. Classify the supplier risk with supplier_risk_class().
3. Derive the required controls with required_controls(): on-site
   audit, monitoring frequency, delegated verification, flow-down.
4. Flow down the customer, regulatory, and special requirements to
   the supplier and record the flow-down.
5. Check the record with supplier_record_complete(): evaluation,
   approved list, monitoring, re-evaluation, flow-down.
6. Gate the approval with approval_verdict(): a complete record
   approves, the critical class is approved-critical, an incomplete
   record is not approved. Only approved suppliers stay on the
   approved supplier list.

## Pitfalls

- Letting history downgrade a critical part: a critical part is always
  a critical-class supplier, whatever the scores. supplier_risk_class()
  enforces this rule order.
- Delegating verification to a critical or high risk supplier:
  delegated verification is allowed only for medium and low classes.
- Shipping without re-evaluation: a record missing periodic
  re-evaluation is incomplete regardless of the other four checks.
- Treating flow-down as optional: requirements (customer, regulatory,
  special) are flowed down for every externally provided item; the
  record is incomplete without it.
- Approving off-list suppliers: approved supplier list membership is a
  hard check; a supplier not on the list is not approved.

## Behavior contract (gate 3)

The risk classification, controls, record completeness, and approval
logic is exercised by the gate 3 contract test:
scripts/test_supplier_control.py against
scripts/supplier_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_supplier_control.py

## Compliance

- Standards referenced, not reproduced: AS9100 text is proprietary
  (IAQG/SAE); this skill uses name and paraphrase only. The purchase
  link is recorded in standards-map.yaml (as9100 entry).
- compliance: STANDARDS-REF, gated: false; the standard is listed
  reference-only.
