---
name: e4008-validation-rules
description: "Validate the body of a simulator exchange file against the rules of ECSS-E-ST-40-08C clause 5.7.2.2. Use when the task is running the structural pass over each entry for required fields, declared types and smuggled-in extra fields, then the referential pass over the whole file for identifier uniqueness, references that resolve to an entry of the kind the field expects, and cycles in the parent, base and link graph, keeping a structurally broken entry out of the reference graph and saying so rather than dropping it. Grades a file against the two normative items. Trigger: ecss, e-st-40-08c, exchange-file-validation-pass, exchange-file-structural-validation, exchange-file-referential-integrity, duplicate-exchange-identifier, unresolved-entry-reference, exchange-reference-cycle."
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
  tags: [ecss, e-st-40-08-simulation-scope, e4008-validation-rules, exchange-file-validation-pass, exchange-file-structural-validation, exchange-file-referential-integrity, unresolved-entry-reference, exchange-reference-cycle]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Infrastructure — Validation Rules (space-systems/ecss/e4008-validation-rules)

Use when the task is the validation rules of ECSS-E-ST-40-08C clause
5.7.2.2 -- what a reader checks in an exchange file once its format
declaration has been accepted. The clause carries two normative items,
one that can be decided entry by entry and one that needs the whole
file in hand, and they are run and reported as two separate passes.

## Domain quick reference

- Structural validation is local. Each entry declares a kind, and the
  kind fixes which fields are required, which are optional and what
  type each field holds. Nothing outside that set may appear: an extra
  field is a producer writing into a format the reader does not share.
- Referential validation is global. Identifiers have to be unique
  across the whole file, every reference has to resolve, and a
  reference has to land on an entry of the kind the field expects --
  a link pointing at a type rather than a model resolves and is still
  wrong.
- The two passes run in that order and the order matters. A
  structurally broken entry has no trustworthy identifier and no
  trustworthy reference fields, so resolving against it manufactures
  findings that disappear once the real defect is fixed.
- An excluded entry is reported as excluded. Dropping it quietly makes
  the reference pass look cleaner than the file is, and the next reader
  hits the same defect with no warning.
- The parent, base and link references form a graph, and the graph has
  to be acyclic. A model that is its own ancestor resolves at every
  individual reference and only fails when something walks the chain.
- A duplicate identifier is not a merge. The second entry is refused
  rather than overwriting the first, because a reference written before
  the duplicate appeared meant the first one.
- A type check on a numeric field has to exclude booleans. A period of
  True is an integer to the language and nonsense to the schedule.

## Workflow

1. Run the structural pass entry by entry: resolve the kind, refuse an
   unknown one outright, then check required fields, undeclared fields
   and the type of each value present.
2. Record which entry positions failed structure; they are the ones the
   reference pass will exclude.
3. Build the identifier table from the structurally sound entries only,
   refusing a duplicate rather than letting the later entry win.
4. Resolve every reference field of every sound entry: report an
   identifier no entry declares, and separately report one that
   resolves to an entry of the wrong kind.
5. Build the reference graph from the references that both resolved and
   matched their expected kind, and walk it for cycles, naming every
   identifier taking part rather than just the first one found.
6. Report the exclusions explicitly as a finding of the reference pass.
7. Grade the two items separately so a file with a structural defect
   and a referential one gets both verdicts in a single run.

## Pitfalls

- Running one merged validation pass. A missing required field then
  produces an unresolved-reference finding as well, and the report
  points at the wrong entry.
- Resolving references against entries that failed structure. Every
  finding it produces is downstream of a defect already reported, and
  they all vanish when that one is fixed.
- Dropping the excluded entries without saying so. The reference pass
  reports clean on a file that was only partly validated.
- Letting a duplicate identifier overwrite the first entry. References
  written against the first now silently point at the second, and
  nothing in the file says the target changed.
- Checking that a reference resolves and stopping there. A link whose
  source points at a type is resolvable and still meaningless, and the
  defect surfaces as a type error deep inside the simulator.
- Checking only the direct parent for a self-reference. A three-step
  parent cycle passes every single-hop check and only shows up when the
  tree is walked.
- Accepting a boolean where a positive integer is required. It passes
  an integer type check in most languages and configures a schedule
  period of one tick.

## Behavior contract (gate 3)

Identifier validation, per-kind structural schemas, undeclared-field
and type checking, the structural pass, exclusion of unsound entries,
identifier uniqueness, reference resolution, expected-kind matching,
cycle detection over the reference graph and the two-item grading are
exercised by the gate 3 contract test:
scripts/test_e4008_validation_rules.py against
scripts/e4008_validation_rules_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e4008_validation_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
