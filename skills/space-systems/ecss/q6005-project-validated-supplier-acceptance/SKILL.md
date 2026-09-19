---
name: q6005-project-validated-supplier-acceptance
description: "Assess the acceptance of a hybrid built by a maker validated for one programme only, under ECSS-Q-ST-60-05C clause 12.3: validate the programme validation record and the build it is read against, decide whether the validation reaches this build on programme, technology, hybrid type and date, assemble the production acceptance steps the build owes with the additions a first lot and an enhanced reliability level bring, name what is still outstanding, and keep an out-of-scope validation separate from an incomplete test campaign. Use when accepting hybrids from a project-validated supplier. Trigger: ecss, q-st-60-05c, project-validated-hybrid-supplier, hybrid-validation-programme-scope, hybrid-production-acceptance-steps, hybrid-first-production-lot-steps, hybrid-validation-validity-window."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-project-validated-supplier-acceptance, project-validated-hybrid-supplier, hybrid-validation-programme-scope, hybrid-production-acceptance-steps, hybrid-first-production-lot-steps, hybrid-validation-validity-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Project-Validated Supplier Acceptance (space-systems/ecss/q6005-project-validated-supplier-acceptance)

Use when the task is accepting hybrids from a manufacturer that was
validated for a single programme rather than holding an approved
production line, under ECSS-Q-ST-60-05C clause 12.3 — whether that
validation reaches the build in front of you, and what the build owes on
top of ordinary acceptance testing.

## Domain quick reference

- A project validation is a statement about one programme's parts made
  on one process at one time. It is not a weaker version of line
  approval that can be stretched; nothing about a second programme
  follows from it, however similar the part looks.
- Scope has four independent edges and they fail differently.
  Programme, technology, hybrid type and the validity window each cut
  the validation off, and a build can be inside three of them and
  outside the fourth. Naming only the first failing edge sends the
  supplier to fix the wrong thing.
- The validity window is not administrative. A validation earned on a
  process characterised two years ago says nothing about the process
  running today, which is why an expired validation is out of scope
  rather than merely overdue for renewal.
- Being in scope buys less here than an approved line buys. The
  project-validated route carries production acceptance steps on every
  build — full electrical acceptance on every unit, environmental
  acceptance on the lot, construction analysis, the internal visual
  record and a delivery review — because there is no monitored line
  history standing behind the batch.
- The first production lot off the validated process owes more than the
  ones after it. The validation demonstrated the process; the first lot
  demonstrates that this build ran it, which is what the witnessed
  operations and the extended burn-in are for.
- An out-of-scope validation and an incomplete test campaign are not the
  same refusal. More testing closes the second and cannot close the
  first: a build outside the validated scope needs a validation
  extension or a different supplier, not another run through the oven.

## Workflow

1. Validate the validation record — programme, technology, covered
   hybrid types, and a window whose expiry is not before its start —
   and the build request read against it.
2. Test all four scope edges and collect every failing one, so a
   supplier one edge short is told which edge.
3. Treat the window edges as inclusive: a build on the first or the last
   day of validity is inside it.
4. Assemble the owed production acceptance steps: the base set for every
   project-validated build, plus the first-lot additions where this is
   the first lot, plus the enhanced-level additions where the build sits
   at that level.
5. Compare the steps performed against the steps owed, matching names
   insensitively to case and separator so a differently punctuated
   record still counts, and list what is outstanding.
6. Return accept only when the validation covers the build and nothing
   is outstanding, keeping the coverage reasons and the outstanding
   steps as separate lists in the report.

## Pitfalls

- Reusing a project validation on the next programme because the part
  number and the process sheet are unchanged. The scope is the
  programme, and that is the one thing that did change.
- Reading an expired validation as a paperwork renewal. The evidence it
  rests on has aged out with it, and a build made after expiry was made
  on an uncharacterised process.
- Reporting the first scope failure and stopping. Programme, technology,
  type and date are independent, and a supplier told only about the
  programme will come back still outside the type list.
- Dropping the production acceptance steps because the maker is now
  validated. The steps exist precisely because there is no line
  monitoring behind the batch; validation is what lets the maker build
  at all, not what replaces acceptance.
- Treating the first production lot like a repeat build. The validation
  characterised the process, not this run of it, and the extra steps
  are the only evidence that the two match.
- Closing an out-of-scope finding by running more tests. No test in the
  acceptance set changes which programme the validation was granted
  against.

## Behavior contract (gate 3)

The validation-record and build-request validation, the four scope
edges, the assembly of the owed production acceptance steps, the
outstanding-step comparison and the accept/refuse disposition are
exercised by the gate 3 contract test:
scripts/test_q6005_project_validated_supplier_acceptance.py against
scripts/q6005_project_validated_supplier_acceptance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_project_validated_supplier_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
