---
name: q2007-management-system
description: "Implement the quality and safety management system a space test centre owes under ECSS-Q-ST-20-07 clause 5.1, and say whether the one in place is doing its job. Use when a test centre is being audited or stood up and the system behind its test services has to be assessed: refuse a system never established, take the declared scope against the services actually offered, measure documented-process coverage of every service in scope, catch a process covering a scoped service without an approval or past its review age, test whether the continual-improvement loop closes its actions and verifies their effectiveness, and say whether the management review is current. Trigger: ecss, q-st-20-07-clause-5-1, test-centre-management-system-scope, test-centre-documented-process-coverage, test-centre-continual-improvement-loop, test-centre-management-review-currency."
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
  tags: [ecss, q-st-20-07-test-centre-quality-and-safety-scope, q2007-management-system, q-st-20-07-clause-5-1, test-centre-management-system-scope, test-centre-documented-process-coverage, test-centre-continual-improvement-loop, test-centre-management-review-currency, test-centre-process-approval-state]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test-Centre Quality and Safety — Management System (space-systems/ecss/q2007-management-system)

Use when the task is clause 5.1 of ECSS-Q-ST-20-07: the test centre
establishes and keeps one quality and safety management system, and the
question is whether that system names everything the centre sells,
documents how each of those services is run, and keeps improving.

## Domain quick reference

- Scope is taken against the services the centre actually offers, not
  against the scope statement reading back to itself. A scope graded
  against its own wording is complete by construction; a service the
  centre performs and the scope never names is outside the system while
  customers are being invoiced for it.
- The reverse case is not the same defect. A scope naming a service the
  centre does not offer is over-declared paperwork, an advisory, not a
  service running uncontrolled.
- A service in scope is covered when an approved process describes it. A
  draft process covering a scoped service is a plan to cover it, and it
  is a worse finding than a bare coverage shortfall because the centre
  is running the service today against wording nobody signed.
- A withdrawn process is not in use and is not carried as an approval
  defect; it simply stops covering whatever it used to cover.
- Continual improvement is a loop, not a register. An action raised and
  never closed leaves the loop open, and an action closed with its
  effectiveness never verified is a closure word rather than an
  improvement. Whether verification is demanded is a centre policy, so
  the closure fraction is taken under that policy rather than assumed.
- Management review is the cadence holding the other three honest. A
  review older than the declared interval means the system is running
  with nobody standing over it, which is a real finding but the last one
  in the order: a scope gap or an unsigned process is worse than a late
  review.

## Workflow

1. Validate the system policy first: the process coverage the centre
   owes, the improvement closure it owes, the process and management
   review intervals, and whether effectiveness verification is demanded.
   A process review interval shorter than the management review interval
   is refused rather than used.
2. Validate the system record: recognised process states, an approval
   day behind every approved process, whole non-negative day numbers, no
   process or action registered twice, and no review or closure dated
   after the assessment day.
3. Take the scope gaps against the services offered, and the scope
   overreach the other way; carry the overreach as an advisory.
4. Take documented-process coverage over the services that are both
   offered and in scope, naming the uncovered ones, and separately name
   the draft processes covering a scoped service.
5. Take the approved processes past their review age as advisories.
6. Take the continual-improvement closure under the policy, naming the
   open actions and the closures whose effectiveness was never verified.
7. Test the management review against its interval, absorbing
   representation error at the boundary with a named tolerance rather
   than by relaxing the required fraction.
8. Close on one verdict in order: system absent, scope incomplete,
   process approval broken, process coverage insufficient, improvement
   loop stalled, management review stale, or system established. Report
   the coverage, the closure, the named services and the named processes
   alongside it.

## Pitfalls

- Grading the scope against the scope statement. It agrees with itself
  every time; only the list of services the centre actually performs can
  find the service that was left out.
- Counting a draft process as coverage. The service is being performed
  now, against wording nobody approved, which is why it ranks above a
  plain coverage shortfall rather than below it.
- Reading an empty scope as full coverage. Zero services in scope
  divided by zero is not one; an unscoped centre has no coverage at all
  and the assessment says so.
- Treating a closed improvement action as a verified one. Closure and
  effectiveness are two separate facts, and a loop full of unverified
  closures looks healthy on a count and has improved nothing.
- Relaxing the required coverage so an exact-equality case passes. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the required value stays as declared.

## Behavior contract (gate 3)

The policy validation, process and action validation, the scope gaps and
overreach, documented-process coverage, the unapproved processes in use,
the review ages, the continual-improvement closure, the management
review currency and the ordered verdict are exercised by the gate 3
contract test: scripts/test_q2007_management_system.py against
scripts/q2007_management_system_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_management_system.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
