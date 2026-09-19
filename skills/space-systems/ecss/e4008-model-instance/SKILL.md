---
name: e4008-model-instance
description: "Validate a model Instance against the seven normative items of ECSS-E-ST-40-08C clause 4.2.2.2. Use when a simulation assembly is reviewed instance by instance: confirming the name is a legal identifier that no sibling already uses, requiring a description, resolving the model definition against the catalogue, confirming every declared field is bound by a supplied value or a declared default, range- and type-checking each bound value, resolving every mandatory reference onto a path that exists in the assembly, and confirming the resulting hierarchy path is occupied once. Reports the seven items separately so a partial review is auditable. Trigger: ecss, e-st-40-08c, simulation-model-instance, model-instance-field-binding, model-instance-path-uniqueness, model-definition-catalogue-resolution, model-instance-reference-resolution, simulation-assembly-instance-review."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-model-instance, simulation-model-instance, model-instance-field-binding, model-instance-path-uniqueness, model-definition-catalogue-resolution, model-instance-reference-resolution, simulation-assembly-instance-review]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling Platform — Model Instance (space-systems/ecss/e4008-model-instance)

Use when the task is the Instance requirements of ECSS-E-ST-40-08C
clause 4.2.2.2 -- grading one occurrence of a model definition inside a
simulation assembly against the seven items the clause carries, and
saying which of the seven a given instance actually satisfies.

## Domain quick reference

- An Instance is an occurrence, not a model. The model definition lives
  in the catalogue and says what fields and references exist; the
  instance says what this particular copy is called, where it sits, and
  what its fields and references are set to. Every one of the seven
  items is a question about the instance, answerable from the assembly
  data without running anything.
- The seven items, in the order this skill grades them: a legal
  identifier unique among siblings; a description; a model definition
  that resolves in the catalogue; every declared field bound; every
  bound value fitting its declared type and range; every mandatory
  reference resolved; and a hierarchy path that only one instance
  occupies.
- The name rule is two rules. An identifier that the platform cannot
  parse cannot address anything, and an identifier that a sibling
  already uses makes the containing scope ambiguous. Both fail the same
  item, for different reasons, and the finding says which.
- A field is bound either by a supplied value or by a default the
  definition declares. Those are equally valid, and the distinction is
  still worth recording: a defaulted field is a decision nobody in this
  assembly made, which is exactly the kind of thing a review wants
  listed.
- A value supplied for a field the definition never declared is a
  finding too. It is usually a rename that only landed on one side, and
  the platform will drop it silently.
- References resolve onto absolute instance paths. A mandatory
  reference left empty and a reference pointing at a path no instance
  occupies are different defects: the first is unfinished configuration,
  the second is a stale path, and only the second survives a build.
- Definition resolution gates three of the seven items. Without a
  definition there are no declared fields and no declared references, so
  the binding, typing and reference items are reported as not assessable
  rather than as satisfied.

## Workflow

1. Take the assembly's instance list and the model catalogue. Build the
   set of paths the assembly declares, so a reference to an instance
   defined later in the list still resolves.
2. For each instance, check the name against the identifier rule and
   against the sibling names already placed under the same parent.
3. Require a non-empty description, and resolve the named model
   definition in the catalogue. Stop the field and reference items here
   when the definition is absent.
4. Bind the fields: for each declared field take the supplied value, or
   the declared default, and record the field as missing when neither
   exists. Type- and range-check whatever was bound, including a
   default, and list values supplied against undeclared fields.
5. Resolve the references the definition declares, separating a missing
   mandatory reference from a target path nothing occupies.
6. Form the instance path from the parent and the name, and mark the
   uniqueness item against the instances already placed, not against the
   whole declared set.
7. Report each item with its own verdict and finding, count the
   satisfied items out of seven, and roll the assembly up to one
   verdict.

## Pitfalls

- Grading the instance as compliant because the simulator built. A
  build tolerates a defaulted field, an undeclared extra value and an
  undocumented instance; the clause does not, and none of those show up
  until the run gives an answer nobody can explain.
- Treating a defaulted field as a bound field with no further comment.
  It is bound, and it is also a value this assembly never chose, which
  is why the binding result keeps the two lists apart.
- Accepting a relative reference target. A path that does not start at
  the root resolves differently depending on which scope reads it, and
  that is precisely the ambiguity the path rule exists to remove.
- Judging path uniqueness against the whole declared set. Every path in
  the set matches itself, so the check has to run against the instances
  already placed, or a clean assembly reports every instance as a
  duplicate of itself.
- Reporting a single overall verdict and nothing else. The clause has
  seven items and a review is expected to say which ones are met, so a
  bare compliant or non-compliant loses the information the next
  reviewer needs.
- Letting a boolean stand in for an integer field. Python treats a
  boolean as an integer, so a field meant to hold a count silently
  accepts a flag unless the check rejects the boolean type explicitly.

## Behavior contract (gate 3)

The identifier rule, path construction, field declaration validation,
value typing and range checks, default and missing-field binding,
reference resolution, the seven-item grading and the assembly roll-up
are exercised by the gate 3 contract test:
scripts/test_e4008_model_instance.py against
scripts/e4008_model_instance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e4008_model_instance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
