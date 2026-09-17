---
name: q6013-parts-approval-document-drd
description: "Determine whether a parts approval document is ready to go to the customer under the data item of ECSS-Q-ST-60-13C Annex D. Use when a commercial part has been selected and the programme must obtain agreement before it may be procured: refuse a submission with no reference or issue, check the part identity, the intended application, the operating environment, the evaluation and radiation evidence, the reliability basis, the risk assessment, the mitigation and the procurement plan each point at something readable, weigh the evidence held against the risk the application carries, and report the disposition it earns. Trigger: ecss, q-st-60-13c-annex-d, parts-approval-document-drd, commercial-part-customer-agreement-submission, parts-approval-evidence-sufficiency, parts-approval-risk-index, parts-approval-conditional-disposition."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-parts-approval-document-drd, commercial-part-customer-agreement-submission, parts-approval-evidence-sufficiency, parts-approval-risk-index, parts-approval-conditional-disposition, commercial-part-application-environment-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components — Parts Approval Document DRD (space-systems/ecss/q6013-parts-approval-document-drd)

Use when the task is the Annex D data item of ECSS-Q-ST-60-13C: a
commercial part has been chosen, and the document asking the customer to
agree to it has to be graded before it is sent — on what it contains and
on whether what it contains carries the risk it is asking about.

## Domain quick reference

- The document is a request, not a report. It asks the customer to
  accept a part that would otherwise not be permitted, so the data item
  fixes the blocks the request has to carry: the part identity and
  manufacturer, the intended application and quantity, the operating
  environment and mission profile, the evaluation and test evidence, the
  radiation evidence, the reliability and failure-rate basis, the risk
  assessment, the mitigation and controls, and the procurement and
  traceability plan.
- A block with no reference behind it is not submitted. Each block has
  to point at something a reviewer can read, so a present flag with a
  blank reference is an unsupported block and the covered share falls
  accordingly.
- Evidence is weighed, not counted. Each evidence-bearing block carries
  a strength between nothing and complete, and the submission's evidence
  is the weighted mean across them, so a thorough radiation campaign
  does not pay for an absent reliability basis.
- The bar moves with the risk. The application criticality and the
  environment severity combine into a risk index, and the evidence the
  submission has to reach rises with it: the evidence that approves a
  part in a benign housekeeping circuit does not approve the same part
  on a single-string function in a high-dose orbit.
- A shortfall the mitigation closes is a condition, not a refusal. A
  submission a little short of the bar but carrying a mitigation the
  customer can check earns a conditional recommendation, which is the
  answer the data item exists to make possible; a shortfall wider than
  the allowance is not conditional, it is unsupported.

## Workflow

1. Validate the data-item policy first: the minimum content coverage,
   the evidence a zero-risk application demands, the span that the risk
   index adds to it, the shortfall a condition may close, and whether a
   mitigation is required when the submission is short. A base plus span
   demanding more than complete evidence is refused rather than used,
   because no submission could then pass.
2. Validate the submission identity: a non-blank document reference, a
   non-blank issue label, the part identifier, and a recognised
   application criticality and operating environment. An absent
   submission, or one with a blank reference or issue, closes the
   assessment on document not submitted.
3. Validate every content block: a recognised block name, no duplicate
   block, a boolean present flag, an evidence reference that may be
   blank but is then read as absent, and a strength between nothing and
   complete. Take the covered share over the required blocks and name
   the absent and unsupported ones.
4. Take the risk index as the product of the criticality weight and the
   environment weight, then the required evidence as the base plus the
   span scaled by that index.
5. Take the held evidence as the weighted mean strength over the
   evidence-bearing blocks, counting an unsupported block as nothing,
   and take the shortfall as what the requirement exceeds it by.
6. Read the mitigation block: it counts only when it is present,
   referenced and carries some strength of its own.
7. Close on one disposition in order: document not submitted, content
   coverage short, evidence insufficient for the risk, mitigation not
   proposed, approval recommended with conditions, or approval
   recommended. Report the coverage, the risk index, the required and
   held evidence and the shortfall alongside it.

## Pitfalls

- Grading the evidence before the contents. A submission missing the
  operating environment cannot have its evidence weighed against a risk
  index it never declared, so coverage is settled first.
- Counting evidence blocks instead of weighing them. Four present blocks
  at a quarter strength each are not the same submission as two complete
  ones, and a count cannot tell them apart.
- Applying one evidence bar to every part. The same commercial part in a
  housekeeping circuit and on a single-string payload function is two
  different requests, and the bar is what separates them.
- Reading a conditional recommendation as an approval. The condition is
  the mitigation, and a mitigation block with no strength behind it is
  the case the data item refuses rather than conditions.
- Reporting a bare disposition. The risk index, the required evidence
  and the shortfall are what the customer's answer turns on, and the
  disposition word carries none of them.

## Behavior contract (gate 3)

The policy validation, submission identity validation, content block
validation and coverage, the risk index, the risk-scaled evidence
requirement, the weighted evidence strength, the shortfall, the
mitigation test and the approval disposition are exercised by the gate 3
contract test: scripts/test_q6013_parts_approval_document_drd.py against
scripts/q6013_parts_approval_document_drd_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_parts_approval_document_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
