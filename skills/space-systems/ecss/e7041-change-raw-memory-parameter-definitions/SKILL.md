---
name: e7041-change-raw-memory-parameter-definitions
description: "Validate and apply the raw memory parameter definition changes of ECSS-E-ST-70-41C clause 6.20.5.2. Use when a request re-points on-board parameters at different memory: resolving each named raw memory parameter, refusing a memory area the memory management service does not hold, refusing a region that runs past the end of its area, refusing a base address that breaks the area's access alignment, refusing a length that disagrees with the width the parameter's representation needs, applying every sound change while leaving the definitions a refusal touched untouched, raising newly overlapping definitions as a hazard, and carrying applied and refused totals. Trigger: ecss, e-st-70-41-packet-utilization-scope, raw-memory-parameter-definition, raw-memory-region-bounds-check, raw-memory-access-alignment, raw-memory-parameter-overlap-hazard."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-change-raw-memory-parameter-definitions, raw-memory-parameter-definition, raw-memory-region-bounds-check, raw-memory-access-alignment, raw-memory-parameter-overlap-hazard]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Change Raw Memory Parameter Definitions (space-systems/ecss/e7041-change-raw-memory-parameter-definitions)

Use when the task is the raw memory parameter definition change of
ECSS-E-ST-70-41C clause 6.20.5.2 -- re-pointing on-board parameters at
different memory areas and offsets, with the seven normative items
that clause places on the request and its outcome.

## Domain quick reference

- A raw memory parameter is not a value the service stores. It is a
  window onto memory: a memory area, a base address inside it, and a
  length. Changing the definition changes where the window looks.
- That is what makes the change dangerous. Nothing about the value
  changes, so nothing about the value catches a bad window; only the
  geometry can be checked, and it must be checked before the change
  lands.
- Four geometry refusals sit on one change and they are distinct.
  The memory area may not exist, the region may run past the end of
  the area, the base may break the area's access alignment, or the
  length may disagree with the parameter's own representation.
- The end of the region is the base plus the length, and the last
  addressed byte is one below that. Comparing the base alone against
  the area size accepts a window that starts inside and ends outside.
- Alignment is a property of the area, not of the request. A device
  that only answers word-aligned reads returns something for an
  unaligned base, and what it returns is not the parameter.
- The length must match what the representation needs -- four bytes
  for a thirty-two bit parameter -- because a shorter window truncates
  and a longer one reads a neighbour into the value.
- Changes are independent. A refusal leaves that definition on its
  previous window rather than withdrawing changes that already
  applied.
- Two definitions that come to address the same bytes are not
  refused. It is legal and it is usually a mistake, so it is applied
  and raised as a hazard.

## Workflow

1. Normalize the memory areas first: identifier, size in bytes and
   access alignment. Reject a zero or negative size and an alignment
   that is not a positive whole number of bytes.
2. Normalize the definition store: each raw memory parameter carries
   an identifier, a representation width in bytes, and its current
   area, base and length. Reject a repeated identifier.
3. Normalize the change list, reject an empty request rather than
   treating it as a no-op success, and collapse a parameter named
   twice by keeping the last change and recording the collision.
4. Resolve each change against the store; a change naming no known
   raw memory parameter is refused.
5. Screen the geometry in a fixed order -- unknown area, then bounds,
   then alignment, then length against the representation -- so the
   reason reported is the first thing actually wrong.
6. Fail the request at start when no change survives, and alter
   nothing in that case.
7. Apply the surviving changes into a new store, leaving the original
   as the pre-request record, and note each definition's previous
   window beside its new one.
8. Recompute the overlaps across the resulting store and raise every
   newly overlapping pair as a hazard.
9. Check applied and refused totals against the distinct change count
   and close with the verdict.

## Pitfalls

- Checking the base against the area size and not the region end. A
  window that starts one byte inside the area and runs off the end
  passes, and the read fetches whatever follows.
- Treating the region end as the last addressed byte. The check then
  refuses a window that ends exactly at the end of the area, which is
  legal, and every full-area definition is rejected.
- Taking alignment from the request instead of from the area. The
  request asserts what it wants and the device answers with what it
  has.
- Skipping the length check because the base and bounds were fine. A
  two-byte window on a four-byte parameter is perfectly in bounds and
  reports a quarter of the value padded with nothing.
- Collapsing the four geometry refusals into one code. The ground fix
  differs for each, and an alignment problem looks like a bounds
  problem until someone reads the memory map.
- Refusing an overlap. Two parameters over the same bytes is legal,
  sometimes deliberate, and turning it into a rejection blocks a
  correct request.
- Applying an overlap silently. It is usually a copy-paste of the
  wrong base, and nothing else on board will notice.
- Mutating the definition store in place. The caller loses the
  previous windows and cannot put a bad change back.

## Behavior contract (gate 3)

The memory area normalization, definition store normalization, change
list normalization and duplicate collapse, the four ordered geometry
refusals, nothing-applicable failed start, independent application
into a new store, previous-window recording, overlap hazard detection
and outcome accounting are exercised by the gate 3 contract test:
scripts/test_e7041_change_raw_memory_parameter_definitions.py against
scripts/e7041_change_raw_memory_parameter_definitions_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_change_raw_memory_parameter_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
