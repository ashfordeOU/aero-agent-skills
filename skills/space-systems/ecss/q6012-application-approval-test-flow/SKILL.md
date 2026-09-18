---
name: q6012-application-approval-test-flow
description: "Build the ordered evaluation test flow that earns a microwave die its application approval, and decide whether that flow can be run at all. Use when an ECSS-Q-ST-60-12C clause 8.2 approval programme has to be laid out: resolve the declared dependencies into one deterministic execution order, reject a cycle instead of silently dropping a step, cut that order into sample groups ending at the step that consumes their samples, add the group demands into a total, take elapsed time from the longest chain rather than the sum, and report a step standing downstream of a destructive one, a missing mandatory evaluation, or an evidence order the flow inverts. Trigger: ecss, q-st-60-12c-clause-8-2, application-approval-test-flow, evaluation-step-ordering, destructive-step-sample-conflict, evaluation-sample-group-sizing, approval-flow-critical-path."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-application-approval-test-flow, q-st-60-12c-clause-8-2, application-approval-test-flow, evaluation-step-ordering, destructive-step-sample-conflict, evaluation-sample-group-sizing, approval-flow-critical-path]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Die Application Approval -- Evaluation Test Flow (space-systems/ecss/q6012-application-approval-test-flow)

Use when the task is the evaluation flow of ECSS-Q-ST-60-12C clause 8.2:
the tests and procedures that have to be run, in the order that makes
their results mean something, before an application approval can be
granted for a microwave die.

## Domain quick reference

- The flow is evidence, and order is part of it. A characterisation taken
  before a stress carries nothing on its own; it is the same samples
  characterised again afterwards that turn a pair of measurements into a
  drift. Listing the right tests in the wrong order produces a programme
  that runs and proves nothing.
- Dependencies are declared per step, and the execution order is derived
  from them rather than from the order somebody typed. A declared sequence
  number only breaks ties between steps that are genuinely free to run in
  either order, so the same flow always yields the same programme.
- A dependency cycle is an input error, not a scheduling problem. Dropping
  the steps that cannot be reached would leave a shorter flow that still
  looks runnable, which is the failure worth refusing loudly.
- Some steps consume the samples they run on. Nothing on those samples can
  follow, so a step declared downstream of a destructive one is a flow that
  cannot be executed as written -- and the block propagates, because
  everything downstream of the blocked step is equally stranded.
- Samples are counted by group, not by step. A group runs its sequence on
  one set of parts and ends at the destructive step that consumes them, so
  the group needs its largest single demand and separate groups add. Summing
  every step's demand over-orders parts; taking the largest across the whole
  flow under-orders them.
- Elapsed time is the longest dependency chain, not the sum of durations.
  Branches that run beside the life test cost nothing in schedule, and a
  schedule built by addition hides which step is actually worth shortening.
- Coverage is a separate question from order. A mandatory evaluation the
  flow never declares is a gap, and an evidence pair the flow inverts is a
  gap even when every declared dependency is satisfied.

## Workflow

1. Normalise every declared step: a unique name, a resolvable predecessor
   list with no self-reference, a boolean destructive flag, a positive
   sample demand and a non-negative duration. Reject a predecessor the flow
   never declares rather than ignoring it.
2. Derive the execution order from the dependencies with the declared
   sequence used only as a tie-break, and refuse a cycle by naming the steps
   it runs through.
3. Walk the order and cut sample groups, closing a group at each
   destructive step, then size each group by its largest single demand and
   add the groups into a total.
4. Trace the transitive successors of every destructive step; each one is a
   step whose samples have already been consumed.
5. Take the flow duration from the longest chain through the dependency
   graph, so the critical step is visible.
6. Check coverage independently: the mandatory evaluations the flow must
   contain, and the order pairs the evidence itself demands.
7. Close with a disposition -- executable only when nothing is missing,
   nothing is stranded, no evidence pair is inverted and the sample total
   is met.

## Pitfalls

- Reading the declared list as the run order. The list is an inventory; the
  order comes from the dependencies, and the two agree only by accident.
- Placing a destructive step early because it is quick. Every step that
  needs those samples afterwards is stranded, and the flow reads as
  complete right up to the moment the parts are gone.
- Summing the sample demand of every step. Steps inside one group run on
  the same parts, so the sum buys hardware the programme never needs and
  hides the group that is genuinely short.
- Taking the largest demand across the whole flow instead of per group.
  That is the opposite error and orders too few parts, which surfaces only
  once a destructive step has already consumed a group.
- Adding durations into a schedule. Parallel branches do not add, and the
  addition disguises which single step sets the delivery date.
- Treating a satisfied dependency graph as a covered programme. A flow can
  be perfectly ordered and still omit a mandatory evaluation, or satisfy
  every declared dependency while inverting a pair the evidence needs.

## Behavior contract (gate 3)

The step and flow validation, the deterministic order with its tie-break
and cycle refusal, the destructive-successor trace, sample-group cutting
and sizing, the longest-chain duration, mandatory coverage and evidence
order, and the runnability disposition are exercised by the gate 3 contract
test: scripts/test_q6012_application_approval_test_flow.py against
scripts/q6012_application_approval_test_flow_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_application_approval_test_flow.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
