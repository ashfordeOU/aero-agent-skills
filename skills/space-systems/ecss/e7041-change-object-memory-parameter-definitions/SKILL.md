---
name: e7041-change-object-memory-parameter-definitions
description: "Validate and apply a change to the object memory parameter definitions an application holds, under ECSS-E-ST-70-41C clause 6.20.5.3. Use when a ground request re-points named parameters at new object memory locations: resolving every named parameter against the definition store, refusing a request that names one twice, checking the target memory is declared, keeping each new binding wholly inside that memory extent and on its alignment unit, refusing a fixed definition and a settable parameter aimed at read-only memory, and returning a per-instruction verdict that leaves the store untouched when the change would break it. Trigger: ecss, e-st-70-41-packet-utilization-scope, object-memory-parameter-definition-change, on-board-parameter-management-service, object-memory-extent-check, object-memory-alignment-unit, fixed-parameter-definition."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-change-object-memory-parameter-definitions, object-memory-parameter-definition-change, on-board-parameter-management-service, object-memory-extent-check, object-memory-alignment-unit, fixed-parameter-definition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Change Object Memory Parameter Definitions (space-systems/ecss/e7041-change-object-memory-parameter-definitions)

Use when the task is the definition-changing request of
ECSS-E-ST-70-41C clause 6.20.5.3 -- re-pointing on-board parameters at
new places in an object memory, with the seven normative items that
clause places on the request and on the store it leaves behind.

## Domain quick reference

- An object memory parameter definition is a binding, not a value. It
  says which memory a parameter lives in, the bit offset it starts at
  and the type that fixes its width and decoding.
- The binding is changed because the memory moves, not because the
  parameter did. A patched software image relocates the word a
  parameter was reading, and re-pointing the definition is how the
  parameter survives the patch instead of silently reading a neighbour.
- An instruction naming a parameter the store does not hold is
  refused and reported. Creating a definition is a different request,
  so a change that would have to invent one is an error, not a create.
- A request that names one parameter twice is malformed. The two
  instructions would race for a single binding and the order that won
  would depend on the implementation.
- The target memory has to be declared. An undeclared identifier is
  not an empty memory, it is an unknown one, and a binding into it
  cannot be range-checked at all.
- Extent and alignment are both checked, and they fail differently. A
  binding that runs past the end reads outside the memory; a binding
  off the alignment unit may not be readable in one access at all.
- A definition can be fixed. Some parameters are pinned by the
  on-board software itself, and their bindings are refused rather
  than accepted and quietly ignored.
- A settable parameter needs somewhere to write. Re-pointing one into
  a memory the application exposes read-only turns every later set
  into a failure at a point far away from the request that caused it.

## Workflow

1. Normalize the definition store and reject a duplicate parameter
   identifier, a negative offset or an undeclared type outright.
2. Normalize the declared object memories, then check the store is
   already consistent against them; an inconsistent baseline is an
   error, not a thing to change on top of.
3. Normalize the request into an ordered instruction list and reject
   an empty request or a repeated parameter identifier as malformed.
4. Decide each instruction on its own: parameter held, definition
   re-definable, target memory declared, access compatible with a
   settable parameter, and the new binding in extent and aligned.
5. Build the candidate store by substituting only the accepted
   bindings, leaving every untouched definition exactly as it was.
6. Re-check the candidate store as a whole before returning it, and
   set the verdict to accepted, partially accepted or rejected from
   the split between applied and refused instructions.

## Pitfalls

- Applying the instructions in place as they are decided. A later
  refusal then leaves a half-changed store that no request describes.
- Checking the extent against the old width after a type change. A
  widening change fits the old footprint and runs past the new one.
- Treating an undeclared memory as an empty one. The binding is then
  accepted against a range of zero, or against no range at all.
- Silently de-duplicating a repeated parameter identifier. The ground
  believes both instructions took effect and only one did.
- Ignoring alignment because the binding is in extent. A misaligned
  word can straddle an access boundary and read as two half words.
- Accepting a settable parameter into read-only memory because the
  read path works. The failure then surfaces on the next set command
  rather than on the change that caused it.

## Behavior contract (gate 3)

The store and memory normalization, request normalization, the
per-instruction extent, alignment, access and re-definability checks,
the candidate-store substitution and the whole-store re-check are
exercised by the gate 3 contract test:
scripts/test_e7041_change_object_memory_parameter_definitions.py
against
scripts/e7041_change_object_memory_parameter_definitions_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_change_object_memory_parameter_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
