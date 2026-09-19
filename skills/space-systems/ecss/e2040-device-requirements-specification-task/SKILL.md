---
name: e2040-device-requirements-specification-task
description: "Determine whether the definition-phase task of ECSS-E-ST-20-40C clause 5.2.2 has actually produced a complete device requirement set: trace every device requirement up to a source requirement that exists, demand a justification on each derived line rather than a parent, trace every mandatory source requirement back down to at least one device line, count the requirements still carrying an open marker against the budget the project allows, report a content area left unpopulated, and say whether the set can be baselined. Use when a device requirement set is being produced or reviewed in the definition phase. Trigger: ecss, e-st-20-40-device-scope, device-requirements-specification-task, parent-requirement-coverage, derived-requirement-justification, orphan-device-requirement, open-item-tbd-budget, requirement-set-baseline-readiness."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-device-requirements-specification-task, device-requirements-specification-task, parent-requirement-coverage, derived-requirement-justification, orphan-device-requirement, open-item-tbd-budget, requirement-set-baseline-readiness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Requirements Specification Task (space-systems/ecss/e2040-device-requirements-specification-task)

Use when the task is the definition-phase duty of ECSS-E-ST-20-40C
clause 5.2.2 -- producing the complete requirement set for the device,
and judging completeness by what the set traces to rather than by how
many lines it has.

## Domain quick reference

- Completeness is a two-way property. Every device requirement has to
  come from somewhere, and every mandatory source requirement has to
  end up somewhere. Checking only the first direction produces a set
  that is perfectly traceable and silently missing whole capabilities.
- Requirements arrive by three routes. An allocated one carries a
  source requirement it refines, a derived one carries no parent and
  owes a justification instead, and a heritage one carries the
  configuration it was inherited from. The route decides what the line
  has to show, so an unrecognised route is an input defect.
- A derived requirement with no justification is the most expensive
  line in the set. Nothing above it constrains it, so it survives
  every review that reads top-down and it is the one that turns out to
  be a designer's preference rather than a need.
- A parent identifier that names nothing in the source set is worse
  than no parent at all: the line looks traced, and the trace resolves
  to a requirement that was deleted or renumbered upstream.
- Open markers are budgeted, not banned. A definition-phase set is
  expected to carry some, so the figure to report is the fraction of
  the set still open against the fraction the project allows.
- A content area declared for the device and left with no requirement
  in it is unpopulated, not satisfied. The empty area is the one that
  gets noticed in the design phase, when changing it is expensive.
- Coverage and open-item fractions land exactly on their bounds. The
  comparison absorbs the representation error of a division rather
  than failing a set that is precisely on budget.

## Workflow

1. Resolve the source set: unique identifiers, each marked mandatory or
   not. Refuse a repeated identifier rather than silently folding it.
2. Resolve the device set: unique identifiers, a recognised origin, a
   recognised content area, the parents named, and the statement.
3. Report every allocated requirement with no parent, and every parent
   identifier that names nothing in the source set.
4. Report every derived requirement carrying no justification, and
   every heritage requirement naming no heritage configuration.
5. Trace downward: report each mandatory source requirement that no
   device requirement points at, and compute the coverage fraction over
   the mandatory source set.
6. Count the device requirements still carrying an open marker, compute
   the fraction, and compare it against the budget, absorbing
   representation error.
7. Report the declared content areas left unpopulated, then decide
   whether the set is ready to be baselined.

## Pitfalls

- Reading traceability in one direction only. Upward tracing catches
  invented requirements; only downward tracing catches the source
  requirement nobody implemented, and that is the omission that
  survives to qualification.
- Letting a derived requirement stand on its statement alone. Derived
  means nothing above it justifies it, so the justification is the
  whole of its authority, and a set full of unjustified derived lines
  cannot be negotiated with the customer.
- Treating a dangling parent identifier as a trace. The line reads as
  allocated, and the identifier resolves to nothing after the upstream
  renumbering that nobody propagated.
- Banning open markers outright in the definition phase. The honest
  set records what is not yet known; a set with none of them usually
  replaced the unknowns with guesses that now read as requirements.
- Comparing an open-item fraction against its budget with a strict
  inequality. A one-in-five division landing on a 0.2 budget can sit a
  unit in the last place above it and fail a set that is exactly on
  budget.

## Behavior contract (gate 3)

The source and device set validation, origin folding, upward and
downward traceability, dangling-parent detection, open-marker counting
against budget, unpopulated-area reporting and baseline verdict are
exercised by the gate 3 contract test:
scripts/test_e2040_device_requirements_specification_task.py against
scripts/e2040_device_requirements_specification_task_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_requirements_specification_task.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
