---
name: q6005-special-marking-cases
description: "Determine whether a hybrid microcircuit that cannot carry a normal direct body mark may be identified by an alternative arrangement, and which one, under ECSS-Q-ST-60-05 clause 10.2.2. Use when a package is too small to letter or its finish will not hold lettering: compute the footprint the mandatory field set needs at the legibility floor, substantiate the special case before allowing any fallback, rank the fallbacks by how hard the identification is to separate from the unit, require the compensating controls the chosen fallback owes, and return the identification-adequacy index with one verdict. Trigger: ecss, q-st-60-05, hybrid-special-marking-case, hybrid-free-body-marking-area, hybrid-attached-identification-tag, hybrid-container-level-identification, hybrid-identification-compensating-controls, special-marking-case-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-special-marking-cases, hybrid-special-marking-case, hybrid-free-body-marking-area, hybrid-attached-identification-tag, hybrid-container-level-identification, hybrid-identification-compensating-controls, special-marking-case-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Special Marking Cases (space-systems/ecss/q6005-special-marking-cases)

Use when the task is clause 10.2.2 of ECSS-Q-ST-60-05: the units that cannot
be marked the ordinary way, because the body has no room for the lettering or
the finish will not hold it. The content of a normal body mark is graded
separately, under the standard marking requirements; the scheme that chose
the method is graded under the general marking provisions.

## Domain quick reference

- A special case is earned, not declared. Either the free area on the body
  cannot hold the mandatory field set at the smallest legible character
  height, or the finish cannot hold lettering that survives handling. If
  neither holds, an alternative arrangement is a shortcut and the unit is an
  ordinary direct-marking case.
- The footprint is computed, not eyeballed. Fields carry a character count,
  character width follows from height, lines need pitch between them, and a
  margin stays clear of the seal ring and the lead exits. A body that fits
  the block exactly is still a direct-marking case.
- The area test is taken at the legibility floor, not at the height someone
  would prefer. A case that fits only at a smaller height is not a case at
  all; a case that will not fit even at the floor is real.
- The fallbacks are ranked by how hard the identification is to separate from
  the unit. A permanent tag fixed to the body travels with it, a mark on the
  individual sealed container travels with the container, a mark on a
  multi-unit intermediate package identifies a group, and a register keyed on
  a carrier position identifies nothing once the carrier is unloaded.
- Why direct marking failed narrows the fallbacks. A body with no room can
  still be identified at the group package; a body whose finish cannot hold a
  mark is a unit-level problem, and a group package does not answer it.
- Every arrangement below a body mark loses something, so it owes
  compensating controls — a serial register, the arrangement named in the
  delivery documentation, a rule that the identification never leaves the
  unit, and re-identification at the next assembly level. A weaker
  arrangement owes more of them, not fewer.
- The adequacy index is taken over the controls the chosen arrangement makes
  mandatory, so the weaker arrangement is graded against the longer list. An
  unsubstantiated case, an inadmissible arrangement or a missing mandatory
  control decides the outcome on its own, at any index.

## Workflow

1. Take the free body area actually left after the seal ring and the lead
   exits, and the finish that area carries.
2. Compute the footprint the mandatory field set needs at the legibility
   floor, one field to a line, margins included.
3. Substantiate the case: area short of the footprint, or a finish that
   cannot hold lettering. With neither, stop and mark the unit for a direct
   body mark.
4. Narrow the admissible fallbacks from the reason the direct mark failed,
   not from what the shop finds convenient.
5. Select the best admissible arrangement the programme actually has, and
   record a proposed arrangement weaker than that as a finding rather than
   quietly accepting it.
6. List the compensating controls that arrangement makes mandatory, and grade
   each one from implemented and evidenced down to absent.
7. Take the weighted credit over total weight as the identification-adequacy
   index.
8. Name the verdict — direct marking required when the case is not special,
   not substantiated when an alternative was proposed anyway, not accepted on
   an inadmissible arrangement, a missing mandatory control or a low index,
   accepted with open actions when findings remain, accepted only when none
   do.

## Pitfalls

- Declaring a special case because the mark looked awkward. The footprint at
  the legibility floor decides it, and a great many small packages still fit.
- Shrinking the lettering until the mark fits and calling that a solution. A
  mark nobody can read identifies nothing, which is the failure the clause
  exists to prevent.
- Answering a finish problem with a group package. The finish is a unit-level
  defect; the group package identifies the group and leaves every unit in it
  anonymous the moment it is unpacked.
- Falling straight to the most convenient arrangement. The ranking exists
  because each step down makes the identification easier to lose, and the
  best arrangement the case admits is the one owed.
- Treating a carrier-position register as identification. It is a lookup that
  stops working the moment the carrier is unloaded, which is exactly when the
  identification is needed.
- Carrying the controls of a tag over to a container or a group package. The
  weaker arrangement owes the longer list, and re-using the short one is how
  an accepted arrangement ends up with nothing holding it together.
- Recording a control as implemented on somebody's word. Implemented without
  evidence is an open action, not a clean control.

## Behavior contract (gate 3)

The mark-footprint computation, special-case substantiation, finish
admissibility, fallback ranking and selection, mandatory compensating-control
set, control grading, identification-adequacy index and case verdict are
exercised by the gate 3 contract test:
scripts/test_q6005_special_marking_cases.py against
scripts/q6005_special_marking_cases_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6005_special_marking_cases.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
