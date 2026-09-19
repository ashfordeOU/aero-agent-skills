---
name: e4008-field-value-requirements
description: "Determine whether each field value a simulation configuration supplies is applicable to the field it addresses, under ECSS-E-ST-40-08 clause 5.2.2.2. Use when the task is resolving field paths on an instance's declared type: walking nested structures and array subscripts, refusing a path that stops on a structure or runs past a declared multiplicity, rejecting a field the type does not publish or that is an output or constant rather than settable, checking the value against the field's primitive type and inclusive bounds, and catching a second assignment to an address already written. Trigger: ecss, e-st-40-08, configuration-field-value, field-path-resolution, array-multiplicity-subscript, field-access-settability, field-value-type-conformance, duplicate-field-assignment."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-field-value-requirements, configuration-field-value, field-path-resolution, array-multiplicity-subscript, field-access-settability, duplicate-field-assignment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling Platform — Field Value Requirements (space-systems/ecss/e4008-field-value-requirements)

Use when the task is the field-value check of ECSS-E-ST-40-08 clause
5.2.2.2 -- deciding whether a value the configuration writes into an
instance can actually be written there, and saying why not when it
cannot.

## Domain quick reference

- The clause carries one obligation, not one test. Applicability is the
  conjunction of path resolution, publication, settability, subscript
  range, type conformance, bound conformance and address uniqueness;
  each has a different repair, so the reason is reported alongside the
  verdict.
- A field path is a grammar, not a string. It alternates names and
  subscripts, and the three shapes that look right and are not are a
  path that stops on a structure, a path that names an array without a
  subscript, and a path that subscripts a scalar.
- Publication and access are separate gates. An unpublished field is
  invisible to the configuration entirely; a published output or
  constant field is visible and still not writable. Reporting both as
  "no such field" sends the reviewer looking for a typing mistake that
  is not there.
- Subscripts are bounded by the declared multiplicity, and the bound is
  exclusive on the index because the indices run from zero. An index
  equal to the multiplicity is the off-by-one that most often survives.
- Booleans are not integers. An integer field handed a boolean compares
  equal to zero or one and will silently take it unless the type test
  excludes it.
- Declared bounds are inclusive. A value sitting exactly on a minimum
  or maximum is compliant, and a strict comparison turns it red for a
  representation reason rather than an engineering one.
- Two elements of the same array are two addresses. Grading duplicates
  on the field name alone rejects a perfectly legal element-by-element
  initialisation.

## Workflow

1. Build the type registry once, refusing a duplicate type, a duplicate
   field, an unknown field type, a multiplicity below one or an
   unrecognised access kind -- an unsound registry cannot support the
   resolution step.
2. Parse the field path into its ordered steps before touching the
   registry, so a malformed path is reported as a path defect rather
   than as a missing field.
3. Walk the steps from the instance's declared type, tracking whether
   the current field still owes a subscript, and stop at the first step
   that cannot be taken.
4. Confirm the resolved field is published, then that its access is one
   the configuration may write.
5. Check the value's primitive type, then its allowed set, then its
   inclusive numeric bounds, in that order.
6. Form the canonical address from the root type and the normalised
   path, and refuse it when an earlier assignment already took it.
7. Report per-assignment records plus a document roll-up naming how
   many assignments were applicable and what each inapplicable one
   needs.

## Pitfalls

- Matching the field by name only. A nested field of the same name
  under a different structure is a different address, and name matching
  both binds the wrong field and mis-detects duplicates.
- Treating an unpublished field and a non-settable field as the same
  finding. One is a catalogue visibility question, the other a design
  question about who owns the value.
- Allowing an index equal to the multiplicity. Indices are zero-based,
  so the last legal subscript is one below the declared count.
- Comparing a value against a bound before checking its type. The
  comparison either raises or coerces, and the reported defect is then
  the wrong one.
- Rejecting a second assignment because the field name repeats. Two
  subscripts of one array are two distinct addresses and both are
  legal.
- Using strict inequalities on inclusive bounds. A value that should
  equal a bound can land a few representation units away from it.

## Behavior contract (gate 3)

Path parsing, type-registry construction, nested and subscripted
resolution, publication and access gating, primitive-type and inclusive
bound conformance, canonical addressing and duplicate detection are
exercised by the gate 3 contract test:
scripts/test_e4008_field_value_requirements.py against
scripts/e4008_field_value_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_field_value_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
