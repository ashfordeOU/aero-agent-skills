---
name: q6005-hybrid-validation-process-overview
description: "Map a hybrid manufacturer validation programme onto the path ECSS-Q-ST-60-05 clause 6.1 lays out: hold its purpose - demonstrated, repeatable capability inside a declared technology scope - and order the stages from request and documentation review through audit, validation vehicle build, evaluation testing and validation review to the surveillance that keeps a granted validation alive. Use when a validation plan is drafted or reviewed, when a supplier asks what the path costs in stages, or when a programme stalls and the next executable stage has to be named. Reports ordering violations, unmet prerequisites, completion and planned duration. Trigger: ecss, q-st-60-05c-clause-6-1, hybrid-manufacturer-validation-path, hybrid-validation-purpose, hybrid-validation-stage-ordering, hybrid-validation-prerequisites, hybrid-validation-surveillance."
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
  tags: [ecss, q-st-60-eee-scope, q6005-hybrid-validation-process-overview, hybrid-manufacturer-validation-path, hybrid-validation-purpose, hybrid-validation-stage-ordering, hybrid-validation-prerequisites, hybrid-validation-surveillance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Manufacturer Validation Path (space-systems/ecss/q6005-hybrid-validation-process-overview)

Use when the task is the clause 6.1 overview of ECSS-Q-ST-60-05: a hybrid
supplier is going through manufacturer validation and the question is what
the activity is actually for and what route it runs. This is the stage
before any individual test report matters — it is the shape of the
programme, its ordering, and the point at which each objective of the
purpose is finally evidenced.

## Domain quick reference

- The purpose is not paperwork. Validation exists to show that this maker
  can build hybrids of a declared technology repeatably, on the line
  described in its own documentation, and to leave a baseline behind that
  later surveillance can be measured against. Four objectives carry that:
  capability demonstrated on hardware, process documentation confirmed
  against the line as audited, a technology scope fixed at the grant, and
  a surveillance baseline set.
- Each objective is evidenced by exactly one stage, which is why the path
  is not reorderable to taste. Capability is evidenced by the evaluation
  testing, not by the plan that promised it; the documentation is
  confirmed by the audit, not by its own cover sheet.
- The path runs: validation request, documentation review, manufacturer
  audit, validation vehicle definition, validation vehicle build,
  evaluation testing, validation review, validation granted, and then
  surveillance. Audit and vehicle definition both follow the documentation
  review and can run alongside each other; the vehicle build waits on both
  of them, which is the one place a plan most often goes wrong.
- Surveillance is the single stage outside the mandatory set: a validation
  can be granted without it, but the granted validation then has no
  baseline keeping it true, so the objective stays owed.
- A validation is granted for a technology scope, not for a company. A
  hybrid whose construction sits outside the scope the grant names is not
  covered by that validation, however current the certificate is.
- The stage-count question a supplier asks first — how long is this — is
  answered from the nominal working days of the stages the plan actually
  names, so a plan that drops a stage shows a shorter path and a missing
  mandatory stage at the same time.

## Workflow

1. Validate the proposed plan: every entry has to be a stage on the path,
   named once. An unknown stage name is an input error, not a custom step.
2. Test the ordering against each stage's prerequisites. A prerequisite
   placed later is a violation, and a prerequisite absent from the plan
   altogether is the same violation, reported the same way.
3. List the mandatory stages the plan leaves out, separately from the
   ordering findings, because the two have different repairs.
4. From the stages complete, name the next executable stage — the first
   one whose prerequisites are all done — and report the completion as a
   share of the whole path.
5. Report which objectives of the purpose are still owed, tied to the
   stage that would evidence each.
6. Where a granted scope and a requested technology are both given, test
   coverage and raise a finding when the build sits outside the scope.
7. Sum the nominal duration of the stages named, so the plan's own cost is
   visible next to its gaps.

## Pitfalls

- Reading the path as a checklist of names. The prerequisites are the
  content; a plan containing every stage in the wrong order fails the same
  way a plan missing one does.
- Starting the validation vehicle build on the strength of the definition
  alone. It waits on the audit as well, and that is the ordering violation
  that shows up most often in a drafted plan.
- Treating a granted validation as a property of the manufacturer. It is
  granted against a technology scope, and a construction outside that
  scope needs its own coverage.
- Dropping surveillance because the grant is already in hand. The grant
  without a surveillance baseline leaves the fourth objective owed, and
  the completion figure says so.
- Reporting completion from the plan rather than from the stages actually
  done. A plan is an intention; the completion share and the next stage
  are both read off what is finished.
- Answering the duration question from a plan that has already lost a
  stage. The shorter total and the missing mandatory stage are reported
  together for that reason.

## Behavior contract (gate 3)

The stage lookup, plan validation, prerequisite ordering, next-stage
selection, completion share, objective status, nominal duration and
technology-scope coverage are exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_validation_process_overview.py against
scripts/q6005_hybrid_validation_process_overview_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_hybrid_validation_process_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
