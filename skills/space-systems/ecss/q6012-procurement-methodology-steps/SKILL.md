---
name: q6012-procurement-methodology-steps
description: "Validate the working method a buyer declares for acquiring microwave dies, step by step, against the methodology of ECSS-Q-ST-60-12C clause 10.1.2. Use when a procurement plan is reviewed before the first enquiry goes out: confirm every mandated step is declared, build the pass and fail branches into a graph, report a step no path can reach from the entry, hold a step that offers no route for the case where it fails, refuse a branch pointing at a step that was never declared, check each step names the record it produces and consumes one produced earlier, and score the method maturity. Trigger: ecss, q-st-60-12c-clause-10-1-2, die-procurement-methodology-steps, buyer-method-step-graph, method-fail-route-completeness, method-step-record-coverage, method-precondition-ordering, method-maturity-score."
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
  tags: [ecss, q-st-60-microwave-die-scope, q6012-procurement-methodology-steps, buyer-method-step-graph, method-fail-route-completeness, method-step-record-coverage, method-precondition-ordering, method-maturity-score]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Buyer Procurement Methodology (space-systems/ecss/q6012-procurement-methodology-steps)

Use when the task is the method step of ECSS-Q-ST-60-12C clause 10.1.2
— grading the working method a buyer has written down for acquiring a
microwave die: the steps, what each one produces and consumes, and
where the method goes when a step passes and when it does not.

## Domain quick reference

- The method is a graph, not a list. Each step carries a pass branch
  and a fail branch, so the declared order of the steps on the page is
  only one of the paths through it, and grading the page order alone
  says nothing about what happens on the day a step fails.
- The mandated steps run: define the requirement, survey the sources,
  issue the enquiry, evaluate the offers, place the order, monitor
  fabrication, witness acceptance, receive and verify, and disposition
  the delivery. A step not declared is not a shortcut; it is a stage
  of the acquisition nobody has said how to perform.
- A branch may leave the method entirely, but only at one of two
  terminals: the acquisition completes, or it is abandoned. A branch
  naming anything else is pointing at a step that does not exist, and
  it is the most common defect in a method written straight into prose.
- A step with no fail route is the defect this grading exists for. A
  method that can only succeed has no method for the case that matters
  — the offer that does not meet the specification, the wafer lot that
  does not pass acceptance — and that is where the buyer needs it.
- Records are what make the method auditable. Each step names the
  record it produces, and a step that consumes a record must consume
  one an earlier step on the pass chain produced; consuming a record
  produced later is an ordering fault even when both steps exist.
- Reachability is separate from coverage. A step can be declared, fully
  specified and still unreachable because no branch points at it; such
  a step reads as covered on a checklist and never runs.

## Workflow

1. Validate each declared step: a recognised step name, no step
   declared twice, branch targets folded to a canonical spelling, and
   the produced and consumed record names read as text.
2. Build the step map and fix the entry — the first step declared,
   unless the declaration names one explicitly.
3. Walk the pass branches from the entry to get the pass chain, and
   report a chain that revisits a step instead of reaching a terminal.
4. Walk both branches from the entry to get the reachable set, and
   report every declared step outside it.
5. Report each branch naming neither a declared step nor a terminal,
   and each step offering no fail route.
6. Report each step producing no record, and each consumed record no
   declared step produces; then, along the pass chain, report a step
   whose consumed record is only produced at or after its own place.
7. Score the maturity as the mean of step coverage, reachability,
   fail-route completeness and record coverage, and return sound,
   gapped, or unworkable when a branch dangles, a step is unreachable
   or the pass chain loops.

## Pitfalls

- Grading the written order and calling it the method. The order on
  the page is the pass path only; the fail branches are where an
  incomplete method actually bites, and they are invisible in a list.
- Letting a branch name a step nobody declared. The method looks
  complete right up to the moment that branch is taken, and then there
  is no next step at all — which is why it is treated as unworkable
  rather than as a gap.
- Accepting a step with no fail route because failure is unlikely.
  Acceptance witnessing and incoming verification exist precisely for
  the unlikely case; a missing fail route there is the whole risk.
- Counting a declared step as a covered step. Declared and reachable
  are different properties, and a checklist that only counts
  declarations passes a method with an orphan step in it.
- Checking only that a consumed record exists somewhere. A record
  produced later on the pass chain is not available when the consuming
  step runs, so existence has to be tested against position too.

## Behavior contract (gate 3)

The step validation, graph construction, pass chain walk and loop
detection, reachability, dangling branch and fail-route reporting,
record production and precondition ordering checks, the four-component
maturity score and the sound / gapped / unworkable verdict are
exercised by the gate 3 contract test:
scripts/test_q6012_procurement_methodology_steps.py against
scripts/q6012_procurement_methodology_steps_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_procurement_methodology_steps.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
