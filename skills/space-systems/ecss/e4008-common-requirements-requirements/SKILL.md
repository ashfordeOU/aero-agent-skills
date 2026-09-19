---
name: e4008-common-requirements-requirements
description: "Validate the five obligations every element of a simulation-platform configuration carries under ECSS-E-ST-40-08 clause 5.1.2. Use when the task is walking a configuration document element by element: confirming each name is a well-formed identifier and not a reserved word, that it is unique inside its own parent scope rather than merely unique somewhere in the file, that its reference resolves to a path the model catalogue publishes, that the kind it declares agrees with the kind the resolved target actually is, and that its uuid is well-formed and used once. Trigger: ecss, e-st-40-08, simulation-configuration-common-requirements, configuration-element-identifier, parent-scope-name-uniqueness, model-catalogue-reference-resolution, declared-kind-target-agreement, configuration-element-uuid-uniqueness."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-common-requirements-requirements, simulation-configuration-common-requirements, configuration-element-identifier, parent-scope-name-uniqueness, model-catalogue-reference-resolution, configuration-element-uuid-uniqueness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling Platform — Common Configuration Requirements (space-systems/ecss/e4008-common-requirements-requirements)

Use when the task is the common-requirements screen of ECSS-E-ST-40-08
clause 5.1.2 -- the five obligations that apply to every element of a
simulation configuration whatever kind of element it happens to be, run
before any kind-specific clause is opened.

## Domain quick reference

- The five items are independent and are graded independently: a
  well-formed identifier, uniqueness inside the parent scope, a
  reference that resolves in the model catalogue, a declared kind that
  agrees with the resolved target, and a uuid that is well-formed and
  used once. An element can satisfy four and fail one; reporting it as
  a bare "fail" hides which repair is owed.
- Identifier well-formedness is a character rule plus a reserved-word
  rule. A name may match the pattern and still be refused because the
  configuration language keeps the word for its own structure, so the
  pattern check alone is not the item.
- Scope uniqueness is per parent, not per document. Two siblings named
  the same are ambiguous even in a document that holds no other copy,
  and the same name under two different parents is perfectly legal. A
  document-wide name set therefore both over-reports and under-reports.
- Reference resolution and kind agreement are two items, not one. A
  reference that resolves to the wrong sort of target -- a field path
  where a model was declared -- passes resolution and fails agreement,
  and that is the mis-wiring that survives review most often.
- The uuid item is a pair of conditions: the 8-4-4-4-12 hexadecimal form
  and a single use across the configuration. A duplicated uuid is not a
  cosmetic clash; it makes two elements indistinguishable to anything
  that keys on it.

## Workflow

1. Build the catalogue index once from the published entries, refusing
   a catalogue that publishes the same path twice; an ambiguous index
   cannot support the resolution item.
2. Walk the elements in document order, carrying a per-scope name set
   and a document-wide uuid set so uniqueness is decided from what has
   already been seen rather than from a second pass.
3. Grade the identifier first. When it is malformed, record the scope
   item as ungraded-and-failed rather than silently passing it: a name
   that is not an identifier cannot be shown unique.
4. Resolve the reference, then compare the declared kind against the
   resolved kind. When resolution failed, the kind item fails too, with
   a finding that names the unresolved path rather than the kind.
5. Normalise the uuid to lower case before the uniqueness test so a
   case difference is not read as two distinct identifiers.
6. Sum the satisfied items per element and across the document, and
   report the ratio alongside the findings so a nearly clean document
   is distinguishable from a wholly ungraded one.

## Pitfalls

- Testing name uniqueness against the whole document. It reports legal
  cross-scope reuse as a defect and can still miss a sibling clash when
  scopes are flattened inconsistently; the parent scope is the unit.
- Collapsing resolution and kind agreement into one verdict. The two
  failures have different repairs -- a wrong path versus a wrong
  declaration -- and merging them sends the reviewer to the wrong file.
- Passing the scope item for an element whose name never parsed. An
  unparsed name is absent, not unique, and marking it clean inflates
  the satisfied count on exactly the elements that need attention.
- Comparing uuids with case sensitivity. The same identifier written in
  two cases is one identifier, and treating it as two lets a real
  duplicate through.
- Reporting a single boolean for the element. The clause carries five
  items; the per-item record is what tells the reviewer whether one
  repair or five are owed.

## Behavior contract (gate 3)

Identifier and reserved-word validation, uuid form and uniqueness,
catalogue index construction, reference resolution, declared-kind
agreement, per-scope name uniqueness and the document-level roll-up are
exercised by the gate 3 contract test:
scripts/test_e4008_common_requirements_requirements.py against
scripts/e4008_common_requirements_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_common_requirements_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
