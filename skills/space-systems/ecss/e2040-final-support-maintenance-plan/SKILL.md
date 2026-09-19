---
name: e2040-final-support-maintenance-plan
description: "Evaluate whether the definitive device Support and Maintenance Plan can be agreed at delivery. Use when an ECSS-E-ST-20-40C clause 5.8.3 plan is being settled: resolve which commitments the device type actually owes, measure each against the contracted post-delivery support period, report the shortfall in months, find the shortest commitment that caps the whole plan, weigh the technology obsolescence horizon and treat a declared mitigation as what lifts that cap, check the agreed anomaly response time, and return agreed, agreed-with-shortfall or not-agreeable. Refuses an unknown commitment, an unrecognised mitigation and a negative coverage. Trigger: ecss, e-st-20-40c, device-support-maintenance-plan, post-delivery-support-period, support-commitment-shortfall, device-obsolescence-horizon, obsolescence-mitigation-declaration, anomaly-response-time-commitment."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-final-support-maintenance-plan, device-support-maintenance-plan, post-delivery-support-period, support-commitment-shortfall, device-obsolescence-horizon, obsolescence-mitigation-declaration, anomaly-response-time-commitment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Final Support and Maintenance Plan (space-systems/ecss/e2040-final-support-maintenance-plan)

Use when the task is the support and maintenance agreement of
ECSS-E-ST-20-40C clause 5.8.3 — settling the definitive plan for keeping an
ASIC, FPGA or IP core supportable after it has been delivered, and deciding
whether what the supplier has offered can actually be agreed.

## Domain quick reference

- The owed commitment set follows the device type. An IP core is
  delivered as design data, so there is no test equipment to retain and
  no spares to hold; demanding either of a soft deliverable produces a
  finding that will be struck out, and accepting the soft set for a
  packaged part hides a real gap.
- A plan is only as long as its shortest commitment. Ten years of
  database retention is worth nothing if the tool licence that can read
  that database expires in six, so the binding constraint is found and
  named rather than averaging the commitments together.
- A commitment that was never made is not a short commitment. An absent
  item leaves nothing to rely on at all, so it collapses the effective
  support period rather than reducing it proportionally.
- The obsolescence horizon and the commitment lengths are different
  quantities. A horizon inside the support period always needs a
  mitigation, but a declared mitigation — a last-time buy, an
  alternative source, a retarget, extended storage — is what stops that
  horizon from capping the plan. The exposure stays visible either way.
- Response time is a rate, not a duration, and is checked against its
  own contracted maximum. A slow agreed response is a shortfall in the
  service level, not a reason the plan cannot be agreed at all.

## Workflow

1. Normalise the device type and derive the owed commitment set from it.
2. Validate each commitment: an unrecognised name, a negative coverage,
   a non-boolean agreement flag, a duplicate declaration, or an
   anomaly-response commitment stating no response time is refused.
3. Compare each owed commitment with the contracted support period and
   record the shortfall in months; treat coverage exactly equal to the
   period as covered, absorbing representation error with a named
   tolerance.
4. Separately collect the owed commitments that are absent and the
   declared commitments the device type does not owe.
5. Find the binding constraint — the shortest live commitment — and the
   months it caps the plan to.
6. Compare the obsolescence horizon with the support period; if the
   horizon falls inside it, record the exposure, and let a declared
   mitigation lift the cap while leaving the exposure reported.
7. Compare the agreed anomaly response time with the contracted maximum
   and return the gap in days.
8. Return the effective support period, the coverage ratio against what
   was asked, and a disposition: not-agreeable when coverage falls
   short, a commitment is absent or one is unagreed; agreed-with-
   shortfall when only service-level items miss; agreed otherwise.

## Pitfalls

- Averaging the commitment lengths into a single support figure. The
  plan is governed by its minimum, and an average hides exactly the item
  that will fail first.
- Treating an absent commitment as a zero-length one and carrying on.
  Nothing downstream can be relied on, which is a different answer from
  a short but real commitment.
- Demanding spares or test equipment of an IP core. The applicability
  step exists to stop that, and skipping it inverts the finding.
- Reading a declared obsolescence mitigation as making the exposure go
  away. It removes the cap on the plan; the horizon is still inside the
  support period and still has to be visible to the customer.
- Refusing the whole plan over a slow anomaly response. That is a
  service-level shortfall and belongs in the middle disposition, not the
  refusal.
- Widening the support period so an exactly-equal commitment passes. An
  equality at the limit is a representation question, handled by the
  named tolerance inside the comparison.

## Behavior contract (gate 3)

Device-type applicability, commitment validation, per-commitment shortfall
in months, binding-constraint selection, obsolescence horizon and mitigation
handling, anomaly response-time comparison, the effective support period and
the three-way disposition are exercised by the gate 3 contract test:
scripts/test_e2040_final_support_maintenance_plan.py against
scripts/e2040_final_support_maintenance_plan_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_final_support_maintenance_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
