---
name: e7041-set-parameter-values
description: "Execute and grade the parameter setting request of ECSS-E-ST-70-41C clause 6.20.4.2. Use when a ground request carries new values for named on-board parameters: resolving each identifier against the application process that holds it, refusing a value that does not fit the parameter's representation or engineering domain, refusing a write to a read-only parameter, applying every sound instruction even when a sibling is refused, failing the request at start only when nothing is applicable, resolving a parameter named twice in one request by last-writer-wins with a finding, and carrying applied and refused totals a receiver can check the outcome against. Trigger: ecss, e-st-70-41-packet-utilization-scope, on-board-parameter-setting, parameter-set-value-domain-refusal, read-only-parameter-write-refusal, parameter-set-outcome-accounting."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-set-parameter-values, on-board-parameter-setting, parameter-set-value-domain-refusal, read-only-parameter-write-refusal, parameter-set-outcome-accounting]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Set Parameter Values (space-systems/ecss/e7041-set-parameter-values)

Use when the task is the parameter setting request of ECSS-E-ST-70-41C
clause 6.20.4.2 -- writing new values into the on-board parameters a
request names, with the seven normative items that clause places on
the request and its outcome.

## Domain quick reference

- The request carries instructions, not identifiers: each one pairs a
  parameter identifier with the value to write. Reporting takes names
  alone; setting cannot.
- An identifier resolves inside one application process, so the
  request says which process it is addressing and an identifier held
  by another process does not resolve.
- Three separate refusals sit on one instruction and they are not
  interchangeable. The parameter may not exist, the parameter may be
  read-only, or the value may not fit. An operator needs to know
  which one it was, because the fix differs each time.
- A value must fit the representation AND the engineering domain.
  Checking one and not the other lets through a value the other would
  have caught, and a set request is the point where that becomes a
  spacecraft state rather than a bad report.
- Instructions are independent. One refusal does not withdraw the
  ones that already applied, because a request that half-applies and
  says so is more useful than one that silently rolls back.
- A request where nothing is applicable fails at start. Nothing is
  written and the failure is reported once, rather than as an empty
  success.
- A parameter named twice in one request is a ground defect. The last
  instruction wins so the outcome is deterministic, and the collision
  is raised so the operator finds out.
- The store is not mutated in place. A new store is returned, so the
  caller keeps the pre-request state to compare against.

## Workflow

1. Normalize the store first: each parameter carries an application
   process, an identifier, a representation, an optional bounded
   domain, an access mode and a current value. Reject a repeated
   identifier inside one process.
2. Normalize the instruction list: reject a non-list, reject an
   instruction that is not an identifier-and-value pair, and reject an
   empty request rather than treating it as a no-op success.
3. Collapse a parameter named more than once, keeping the last
   instruction, and record the collision.
4. Resolve each instruction against the store scoped to the named
   application process, keeping request order.
5. Refuse an instruction that resolves to nothing, one that addresses
   a read-only parameter, and one whose value falls outside the
   parameter's effective domain -- each with its own distinct reason.
6. Fail the request at start when no instruction survives, and write
   nothing in that case.
7. Apply the surviving instructions into a new store, leaving the
   original untouched, and record the previous value beside the new
   one for each write.
8. Compute applied and refused totals from the recorded outcomes,
   check them against the instruction count, and close with the
   verdict.

## Pitfalls

- Collapsing the three refusal reasons into one rejection code. The
  operator cannot tell a typo from a protected parameter from a value
  the subsystem will not survive.
- Checking the value against the representation only. A value the
  hardware can hold but the subsystem cannot survive is written.
- Checking the value against the engineering limits only. A value
  inside the limits but outside the representation truncates on the
  way down and lands as something else.
- Rolling back applied writes when a later instruction is refused.
  The spacecraft is left in a state no ground record predicts.
- Treating an empty instruction list as a successful no-op. Nothing
  was written and the outcome says success.
- Applying both instructions when a parameter is named twice. The
  final value depends on iteration order, and two runs of the same
  request can leave different states.
- Mutating the store in place. The caller loses the pre-request state
  and cannot say what the request actually changed.
- Writing a read-only parameter because the check was left to the
  definition-time review. The set path is where it bites.

## Behavior contract (gate 3)

The store normalization, instruction normalization, duplicate
collapse, scoped resolution, the three distinct refusals, nothing-
applicable failed start, independent application into a new store,
previous-value recording, outcome totals and their accounting check
are exercised by the gate 3 contract test:
scripts/test_e7041_set_parameter_values.py against
scripts/e7041_set_parameter_values_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_set_parameter_values.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
