---
name: e4008-property-value-requirements
description: "Evaluate the property values a simulation configuration supplies against the five obligations of ECSS-E-ST-40-08 clause 5.2.3.2. Use when the task is grading accessor-based initialisation on a model instance: confirming the property is declared and published, that its access kind actually offers a setter rather than being read-only, that the value matches the declared type and then the declared allowed set or inclusive range, and that the property takes exactly one value and is not also written through the field that backs it, which would leave the applied order undetermined. Trigger: ecss, e-st-40-08, configuration-property-value, property-access-kind, property-setter-availability, property-value-type-conformance, property-constraint-range, property-backing-field-conflict."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-property-value-requirements, configuration-property-value, property-access-kind, property-setter-availability, property-constraint-range, property-backing-field-conflict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling Platform — Property Value Requirements (space-systems/ecss/e4008-property-value-requirements)

Use when the task is the property-value check of ECSS-E-ST-40-08 clause
5.2.3.2 -- deciding whether a value the configuration pushes through a
model's accessor pair is one the model will accept, and which of the
five obligations it misses when it is not.

## Domain quick reference

- A property is not a field with a longer name. It is reached through
  an accessor pair, it carries an access kind of its own, and it may be
  backed by a field the same configuration can write directly. Those
  three differences are what the clause grades.
- The access kinds are read-only, write-only and read-write, and only
  the last two expose a setter. A read-only property is a legitimate
  published surface -- it is simply not a configuration target, and the
  backing field's own access does not change that.
- Write-only is writable. Treating "not readable" as "not configurable"
  refuses exactly the properties -- seeds, keys, one-shot trims -- that
  exist to be set once at configuration and never read back.
- Type conformance is graded before the constraint. A value of the
  wrong type cannot be compared with a bound, so the constraint item is
  left alone once the type item has failed and one defect stays one
  finding.
- Booleans are not integers, and an integer is an acceptable value for
  a floating-point property. Getting the first wrong lets a mis-wired
  value through; getting the second wrong reds a legal configuration.
- Configuring a property and its backing field in the same document is
  the ambiguity the fifth item exists for. Both writes are individually
  legal and the resulting initial state depends on which is applied
  last, which is not something the configuration determines.
- Declared numeric bounds are inclusive on both ends.

## Workflow

1. Build the property table once, refusing a duplicate property, an
   unsupported type or an unrecognised access kind; an unsound table
   cannot support the declaration item.
2. Look the property up and treat an unpublished one exactly as an
   undeclared one for the first item -- but record that every later
   item is ungraded rather than passed, so the satisfied count does not
   credit checks that never ran.
3. Grade the access kind against the writable set, independently of
   whether the value itself is any good.
4. Check the value's type, and only if it conforms, its allowed set and
   then its inclusive numeric or length bound.
5. Grade single-assignment and backing-field conflict together as the
   fifth item: a repeated property, or a property whose backing field
   also appears in the configuration's field writes.
6. Roll the per-property records up into a satisfied count over five
   items per assignment, so a document with one read-only target is
   distinguishable from one that is wired wrong throughout.

## Pitfalls

- Refusing a write-only property. It has a setter and no getter, which
  is precisely the configuration case.
- Reading the backing field's access instead of the property's. The
  setter may validate, clamp or reject where a direct field write would
  not, so the property's own access kind is the one that governs.
- Crediting the later items on an undeclared property. Nothing about
  its type or constraints was checked, and a satisfied count of four
  out of five on a property that does not exist is a false green.
- Reporting a type mismatch and a constraint breach for one value. The
  second is a consequence of the first, and the duplicate inflates the
  finding count.
- Letting both a property value and its backing field stand. Each looks
  correct alone; the defect only exists in the pair.
- Grading inclusive bounds with strict comparisons. A value that should
  sit exactly on a bound can land a few representation units away.

## Behavior contract (gate 3)

Property-table construction, access-kind resolution, writable-access
selection, type conformance, allowed-set and inclusive-bound checking,
repeated-assignment detection, backing-field conflict detection and the
five-item roll-up are exercised by the gate 3 contract test:
scripts/test_e4008_property_value_requirements.py against
scripts/e4008_property_value_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_property_value_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
