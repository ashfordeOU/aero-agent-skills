---
name: e4008-field-link
description: "Evaluate the field links of an SMP Level-2 assembly artefact against ECSS-E-ST-40-08C clause 5.2.7.4: resolve the source onto a readable output or state field and the target onto a writeable input or state field, require identical primitive datatypes because a link copies rather than converts, require identical array shape, refuse a second writer into one target field, and refuse a field linked to itself. The driven-field set the configuration check needs is returned, and a dataflow cycle is raised as an ordering advisory. Use when a value never propagates or two writers fight over one field. Trigger: ecss, e-st-40-08c, smp-level-2, assembly-field-link, field-direction-rule, field-datatype-match, single-writer-field-target, field-link-dataflow-cycle."
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
  tags: [ecss, e-st-40-08c-smp-level-2, e4008-field-link, smp-assembly-artefact, assembly-field-dataflow, field-link-direction-rule, field-link-datatype-match, single-writer-field-target]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SMP L2 — Field Link (space-systems/ecss/e4008-field-link)

Use when the task is a field link of an SMP Level-2 assembly artefact per
ECSS-E-ST-40-08C clause 5.2.7.4 — copying one component's field into another's
every time the assembly applies its data flow — and the question is whether the
copy is admissible and unambiguous.

## Domain quick reference

- A field link is a copy, not an expression. Nothing is scaled, converted or
  combined on the way across, which is why a source and target of different
  primitive datatypes is a defect rather than a widening.
- Direction decides which end a field may occupy. An output or a state field
  holds a value the model produced, so it can be read; an input or a state
  field is consumed by the model, so it can be written. A state field is the
  only one that may sit at either end.
- Array shape is part of the type. A three-element vector and a four-element
  quaternion are both arrays of the same primitive and are not
  interchangeable, so the shapes are compared element count by element count,
  with an unset shape meaning scalar.
- One target, one writer. Two links into the same field produce a value that
  depends on the order the assembly applies them, and that order is not a
  property either link declares — which is what makes the second writer a
  defect rather than a race to be tuned.
- The accepted links define the driven-field set, and that set is the input to
  the component-configuration check: a field written every step must not also
  carry a configured value, because the configured value would not survive the
  first propagation.
- A cycle through field links is legal in structure and awkward in behaviour:
  the propagated values depend on application order rather than on the links
  themselves, so it is surfaced as an advisory instead of a rejection.

## Workflow

1. Resolve the source endpoint onto a declared field and require its direction
   to be readable; resolve the target endpoint and require it to be writeable,
   naming the direction in the finding so the repair is obvious.
2. Refuse a link whose two endpoints are the same field, and refuse one whose
   endpoints sit on the same instance unless the assembly permits self-links.
3. Compare the primitive datatypes for identity and reject any pair that would
   need a conversion.
4. Compute the array shape of both ends, treating an unset dimension list as
   scalar, and compare the shapes as tuples.
5. Record the writer of each target field and reject a second link into a
   target that already has one, naming the link that claimed it.
6. Emit the sorted driven-field set so the configuration check can refuse a
   configured value on a linked field.
7. Walk the instance-level dataflow graph of the accepted links and report any
   cycle as an ordering advisory alongside the findings.

## Pitfalls

- Allowing a widening datatype pair. It looks harmless in a review and makes
  the assembly depend on a conversion that the copy semantics do not provide.
- Comparing only the number of dimensions. Two one-dimensional arrays of
  different extents pass a rank check and then truncate or overrun on copy;
  the extents themselves have to match.
- Treating an unset dimension list as an array of one. A scalar field and a
  one-element array are different shapes, and conflating them lets a scalar
  drive an array target.
- Accepting a second writer because both links are individually valid. Nothing
  in either link is wrong; the defect exists only in their combination, so it
  is invisible to any check that grades one link at a time.
- Grading the configuration block and the field links separately. A field with
  both a configured value and an incoming link looks correct in each artefact;
  the driven-field set is what makes the conflict visible.
- Failing an assembly for a dataflow cycle. The cycle is an order dependency,
  not an invalid link, and rejecting it outright blocks legitimate feedback
  structures that the schedule resolves.

## Behavior contract (gate 3)

The direction-checked endpoint resolution, datatype identity, array-shape
comparison, single-writer rule, self-link handling, driven-field export and
cycle detection are exercised by the gate 3 contract test:
scripts/test_e4008_field_link.py against
scripts/e4008_field_link_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e4008_field_link.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
