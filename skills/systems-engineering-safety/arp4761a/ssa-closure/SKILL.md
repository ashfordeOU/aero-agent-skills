---
name: ssa-closure
description: "Use when you must close out the post-implementation safety assessment over the assessed condition set: look up the quantitative probability target per flight hour for the severity class of each assessed condition, compute the per-condition margin of target over predicted with the strict meets verdict, roll the conditions up into the closure-gate verdict with the closed and open counts, the open condition ids and the per-severity-class closure fraction, and roll the safety requirement verification statuses into the verified and open requirement closure list. Produces the severity-target lookup, the per-condition margins, the closure-gate verdict dict and the requirement closure list that gate the close-out statement. Trigger: ssa-closure rollup, closure-gate verdict, post-implementation-safety-verdict margin, condition-margin, requirement-closure-status."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: arp4761a
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [ssa-closure, closure-gate, post-implementation-safety-verdict, requirement-closure-status, condition-margin]
  version: 0.1.0
  author: AeroSkills
---

# SSA Closure (systems-engineering-safety/arp4761a/ssa-closure)

Use when you must close out the post-implementation safety assessment
over the assessed condition set. After the system is implemented, the
analyst-supplied predicted probabilities per flight hour (for example
from updated fault tree runs on the implemented system) are compared
against the quantitative probability target of each condition's
severity class: the per-condition margin of target over predicted and
the strict meets verdict come first, the multi-condition closure rollup
then aggregates every condition into the closure-gate verdict, and the
safety requirement verification statuses roll into the verified/open
requirement closure list that gates the close-out statement. It pairs
with systems-engineering-safety/arp4761a/safety-assessment, whose
sequence runs the SSA after implementation and closes the safety
requirements, and with systems-engineering-safety/arp4761a/functional-
hazard-assessment, which supplies the severity classes and the strict
target rule behind the meets comparison.

## Domain quick reference

- Quantitative probability targets per flight hour by severity class
  (severity_target): catastrophic 1e-9, hazardous 1e-7, major 1e-5,
  minor 1e-3. Only these four classes carry a number to close against;
  "no safety effect" has no quantitative target and is rejected.
- Per-condition margin and strict meets verdict (condition_margin):
  margin = target / predicted_q, meets = predicted_q < target. The
  comparison is strict, so a condition exactly on target (margin 1.0)
  does not meet, mirroring the strict-target rule of the severity
  classification work.
- Closure-gate verdict dict (closure_rollup): total, closed and open
  counts, open_conditions in input order, meets_by_severity with the
  per-severity-class closure fraction closed / total for the classes
  present (ordered catastrophic, hazardous, major, minor), and
  overall_gate CLOSED only when every condition meets its target.
- Requirement closure list (requirement_closure): total, verified and
  open counts plus open_requirements in input order over the
  verification statuses, each "verified" or "open".
- Only post-implementation predicted probabilities are consumed here:
  this leaf does not rate a condition's severity from its effects,
  derive or apportion the safety requirements, plan the assessment
  sequence, or consume observed fleet data from service.

## Workflow

1. Assemble the assessed condition set for the close-out from the
   post-implementation fault tree runs on the implemented system: for
   every assessed condition record its id, severity class and the
   analyst-supplied predicted probability q per flight hour.
2. Look up the quantitative probability target per flight hour for the
   severity class of each condition with severity_target(severity)
   (the severity-class target lookup); a class with no quantitative
   target cannot be closed against a number.
3. Compute the per-condition margin and the strict meets verdict with
   condition_margin(predicted_q, severity) (the per-condition margin
   pass): margin = target / predicted_q, and meets holds only while
   predicted_q stays strictly below the target, so equality fails and
   the margin is exactly 1.0 at the boundary.
4. Roll every assessed condition up with closure_rollup(conditions)
   (the multi-condition closure rollup) into the closure-gate verdict
   dict: the closed and open counts, the open condition ids in input
   order, the per-severity-class closure fraction and overall_gate.
5. Roll the safety requirement verification statuses up with
   requirement_closure(requirements) (the requirement status rollup)
   into the verified/open requirement closure list.
6. Read the close-out (the close-out read): declare the closure-gate
   verdict CLOSED only when open_conditions is empty, pair it with the
   requirement closure list, and keep the close-out open while any
   condition misses its target.
7. Confirm the deterministic checks with the contract test: python3
   scripts/test_ssa_closure.py.

## Worked example

Six assessed conditions on the implemented system, targets per flight
hour (predicted probabilities are analyst-supplied post-implementation
estimates):

- FC-01 catastrophic q = 5e-10 vs target 1e-9: meets True, margin 2.0.
- FC-02 catastrophic q = 2e-9 vs target 1e-9: meets False, margin 0.5.
- FC-03 hazardous q = 3e-7 vs target 1e-7: meets False, margin 0.33333.
- FC-04 hazardous q = 2e-8 vs target 1e-7: meets True, margin 5.0.
- FC-05 major q = 4e-6 vs target 1e-5: meets True, margin 2.5.
- FC-06 minor q = 9e-4 vs target 1e-3: meets True, margin 1.11111.

closure_rollup over the six conditions returns total 6, closed 4,
open 2, open_conditions [FC-02, FC-03], meets_by_severity
catastrophic 0.5, hazardous 0.5, major 1.0, minor 1.0, and
overall_gate OPEN: two conditions miss their targets, one in each of
the two highest severity classes, so the close-out stays open.
requirement_closure over five requirements with REQ-1 to REQ-3
verified and REQ-4, REQ-5 open returns total 5, verified 3, open 2,
open_requirements [REQ-4, REQ-5].

## Verification

- Confirm severity_target spot values: catastrophic 1e-9, hazardous
  1e-7, major 1e-5, minor 1e-3.
- Confirm the worked margins: condition_margin(5e-10,
  "catastrophic") = meets True, margin 2.0; (2e-9, "catastrophic") =
  meets False, margin 0.5; hazardous, major and minor anchors at
  0.33333, 5.0, 2.5 and 1.11111 within 1e-6.
- Confirm the strict boundary: condition_margin(1e-3, "minor") gives
  meets False with margin exactly 1.0, while 9.999e-4 meets.
- Confirm the worked rollup totals and open_conditions, the per-class
  fractions, and that all-meeting sets close the gate while
  all-failing sets stay open with open equal to total.
- Confirm meets_by_severity lists only severity classes present in the
  input, in catastrophic, hazardous, major, minor order, and that the
  rollup dict keys are exactly the documented set.
- Confirm the rejections: severity strings outside the four classes
  (including "no safety effect", "none", "Severe", empty and padded
  strings), a non-positive predicted_q, an empty condition list, a
  condition missing its id, and requirement statuses outside
  {"verified", "open"} all raise ValueError, while an empty
  requirement list rolls up to zeros.
- Run the contract test offline: python3
  scripts/test_ssa_closure.py (32 tests, deterministic).

## Related leaves

- systems-engineering-safety/arp4761a/safety-assessment: the process
  umbrella whose workflow runs the SSA after implementation and closes
  the safety requirements; it fixes the FHA-to-SSA sequence and the
  assessment scope, not the closure math.
- systems-engineering-safety/arp4761a/functional-hazard-assessment:
  owner of the severity classes and the strict-target rule; this leaf
  consumes, never re-derives, the class of each condition.
- systems-engineering-safety/arp4761a/preliminary-system-safety-
  assessment: the proposed-architecture analytical argument whose
  requirements this SSA close-out confirms on the implemented system.
- systems-engineering-safety/arp4754a/requirements-traceability and
  systems-engineering-safety/arp4754a/configuration-management: their
  closure work maps requirements to design and verification artifacts
  and is not a safety verdict over the assessed conditions.
- systems-engineering-safety/continued-airworthiness/in-service-
  safety-assessment: field-data review that compares observed fleet
  rates; the predicted rates closed here feed that later phase.

## Pitfalls

- Closing a condition whose severity class carries no quantitative
  target: "no safety effect" has no number per flight hour to close
  against, and severity_target rejects it.
- Using a non-strict comparison: a condition sitting exactly on its
  target shows margin 1.0 and does not meet, per the strict-target
  rule, so equality must fail.
- Declaring the close-out while conditions are still open: the
  closure-gate verdict stays OPEN whenever open_conditions is
  non-empty, one missed catastrophic condition included.
- Rolling requirements with statuses other than verified or open: an
  unclosable status raises instead of silently disappearing from the
  requirement closure list.
- Reading a single condition's margin as the overall verdict: the
  closure-gate verdict is the multi-condition rollup over the assessed
  condition set, and the close-out read pairs it with the requirement
  closure list.
- Feeding proposed-architecture predicted probabilities into the
  close-out: only post-implementation estimates from the implemented
  system close the SSA.
- Substituting the arp4754a closure of requirements against design and
  verification artifacts for the safety verdict: that closure is a
  traceability record, not a verdict over the assessed conditions.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ssa_closure.py

The test covers the severity-target spot values and the exact-string
rejections, the worked margins 2.0 and 0.5 within 1e-12 and 0.33333,
5.0, 2.5, 1.11111 within 1e-6, the strict-target boundary identity at
equality (meets False, margin 1.0 exactly) with 9.999e-4 meeting, the
margin identity target / predicted_q, monotonicity of meets in
predicted_q, the worked rollup totals with open_conditions [FC-02,
FC-03] in input order, per-severity-class closure fractions 0.5, 0.5,
1.0, 1.0, the all-meeting CLOSED and all-failing OPEN rollups, the
presence and ordering of severity classes in meets_by_severity, the
identity that closed plus open balances the totals per class, the gate
equivalence with empty open_conditions, the requirement rollup anchors
verified 3 and open 2 with [REQ-4, REQ-5], the valid empty requirement
list, the exact documented dict keys, and the ValueError rejection of
every non-physical input listed in the spec.

## Compliance

- Standards referenced, not reproduced: ARP4761A is a SAE standard
  (sae.org/standards); the severity probability targets per flight
  hour are summarized by name and magnitude only, per standards-map
  yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
