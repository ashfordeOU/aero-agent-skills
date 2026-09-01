---
name: corrective-action
description: "Use when you must drive a corrective action (CAPA) record for a manufacturing nonconformance to closure: run the eight-discipline (8D) problem-solving workflow, check that a containment action is recorded, validate the five-whys root cause chain, and confirm the corrective action and the effectiveness evidence before the record closes. Produces the closure stage verdict, the missing items, and the effectiveness pass or fail that gate the nonconformance closure. Trigger: corrective action, capa record, 8d report, five whys, root cause analysis, containment action, effectiveness verification, problem solving."
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
  tags: [corrective-action, capa-record, 8d-report, five-whys, root-cause-analysis, containment-action, effectiveness-verification, preventive-action, problem-solving]
  version: 0.1.0
  author: AeroSkills
---

# Corrective Action (manufacturing-quality/as9100/corrective-action)

Use when the task is closing a corrective action record for a
manufacturing nonconformance: containment, five-whys root cause
analysis, corrective action, and effectiveness evidence must all be
in place before the record closes per AS9100 practice.

## Domain quick reference

- The closure state machine walks four stages in order: containment,
  root-cause, corrective-action, effectiveness.
- Containment is the immediate action that isolates the effect of a
  nonconformance; a placeholder answer (none, n/a, unknown) does not
  count as a recorded containment.
- The five-whys root cause chain needs at least 3 recorded levels,
  each non-empty and distinct from the previous answer; a repeated
  adjacent answer is circular and fails the chain.
- Corrective action removes the root cause; preventive action
  prevents recurrence. A blank or placeholder corrective action
  cannot close the record.
- Effectiveness evidence must describe an observed result and must
  not restate the root cause text, which would be circular evidence.
- record_status returns one of: containment-missing,
  root-cause-incomplete, corrective-action-missing,
  effectiveness-pending, closed. closure_verdict adds the missing
  items for the current stage.
- AS9100 frames corrective action as the required response that
  closes a nonconformance; the stage machine here is a practical
  summary, not clause text.

## Workflow

1. Record the problem statement as the record problem.
2. Record the containment action and check it with
   containment_ok (no placeholders).
3. Build the five-whys chain and validate it with
   root_cause_chain_ok (depth, empty answers, circularity).
4. Record the corrective action and the preventive action; check
   the corrective action with corrective_action_ok.
5. Record effectiveness evidence and check it with
   effectiveness_evidence_ok against the root cause statement.
6. Call record_status for the stage and closure_verdict for the
   missing items; close only at status closed.

## Pitfalls

- Placeholder answers: none, n/a, na, no, unknown, and not-applicable
  fail containment_ok, corrective_action_ok, and the whys chain.
- Circular why chains: the same answer twice in a row means the
  analysis stopped; the chain needs a new level each time.
- Circular effectiveness evidence: evidence that repeats the root
  cause statement proves nothing and keeps the record pending.
- Closing without effectiveness: a record with containment, whys,
  and corrective action but no evidence stays effectiveness-pending.
- Containment versus corrective action: containment isolates the
  effect, corrective action removes the cause; one does not replace
  the other.
- Missing keys: record_status raises ValueError when problem,
  containment, whys, or corrective_action is absent.

## Behavior contract (gate 3)

The closure stage logic is exercised by the gate 3 contract test:
scripts/test_corrective_action.py against
scripts/corrective_action_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_corrective_action.py

## Compliance

- Standards referenced, not reproduced: AS9100 corrective action is
  summarized as a stage machine and workflow, common aerospace
  problem-solving practice per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
