---
name: q7001-cleanroom-class-requirements
description: "Determine the airborne particulate class an exposed-hardware operation needs and grade the clean area it has been given against that class. Use when an operation states a concentration it can tolerate at a threshold particle size and a facility offers a room, and the two must be reconciled before hardware is uncovered. Evaluates the ISO 14644-1 class ceiling from the size relation, runs it backwards to the least demanding class that still holds, refuses a threshold size outside the range the relation designates, rejects an area looser than the work needs, reports an area two classes cleaner as scarce space overspent, and rejects an operational requirement backed only by an unoccupied demonstration. Trigger: ecss, iso-14644-1, cleanroom-class-selection, airborne-particle-concentration-ceiling, clean-area-assignment, at-rest-versus-operational-demonstration, threshold-particle-size."
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
  tags: [ecss, q-st-70-cleanliness-control-scope, q7001-cleanroom-class-requirements, cleanroom-class-selection, airborne-particle-concentration-ceiling, clean-area-assignment, at-rest-versus-operational-demonstration, threshold-particle-size]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Control — Clean-Area Class Requirements (space-systems/ecss/q7001-cleanroom-class-requirements)

Use when the task is designating an airborne particulate class for an
operation on space hardware — picking the class the work actually needs
from a tolerable concentration, and judging whether the area the
facility has offered meets it in the state the work happens in.

## Domain quick reference

- A class is not a single number. It is a concentration ceiling that
  depends on the particle size being counted, and the ceiling rises
  steeply as the threshold size falls. Quoting a class without the
  threshold it was evaluated at says almost nothing.
- Selection runs the relation backwards. The operation names the
  concentration it can live with at a threshold size, and the answer is
  the least demanding class whose ceiling still sits under it. Anything
  cleaner is a real cost in air handling, gowning and schedule that the
  hardware did not ask for.
- The relation designates a class only over the particle-size band it
  covers. A threshold below or above that band produces a number, but
  not a class, so it is refused rather than extrapolated.
- A requirement sitting exactly on a class ceiling is a real case and
  has to select that class. The comparison therefore carries a relative
  tolerance for representation error, not a widened ceiling.
- Classes are demonstrated in an occupancy state. An empty room is the
  cleanest the room will ever be, so a requirement written for work in
  progress is not met by an unoccupied demonstration, and accepting one
  is the most common way a compliant-looking area fails at first use.
- An area far cleaner than the operation needs is not a safety margin
  worth celebrating. Clean space is scarce, and the operation occupying
  it has displaced the one that needed it.

## Workflow

1. Validate the threshold particle size against the band the relation
   designates a class over, and refuse anything outside it.
2. Evaluate the class ceiling at that threshold from the size relation,
   and report it at the precision the scheme uses.
3. Run the relation backwards against the tolerable concentration to get
   the least demanding integer class that still holds, absorbing
   representation error with a relative tolerance.
4. Raise a refusal where no room class holds the requirement at all: the
   answer there is a local enclosure or a purge, not a cleaner room.
5. Compare the assigned class with the required class. Reject an
   assignment that is looser; report one two or more classes cleaner as
   scarce space spent on work that did not need it.
6. Check the occupancy state the class was demonstrated in against
   whether hardware is exposed during the operation.
7. Roll up across the plan: the cleanest class any operation requires,
   the operations that cannot be accepted, and every finding.

## Pitfalls

- Naming a class with no threshold size beside it. The same area is
  compliant or not depending on whether the requirement was written at
  half a micron or at five, and the ambiguity survives into the
  facility contract.
- Extrapolating the relation past the band it covers to get a ceiling
  for very large or very small particles. The number looks like a class
  and is not one.
- Assigning the cleanest available area by default. It reads as
  conservatism and is a scheduling decision that pushes the operation
  that genuinely needed the space into a dirtier room.
- Accepting an unoccupied demonstration for work with people and
  hardware in the room. The certificate is genuine and describes a
  condition the operation never runs in.
- Comparing a measured concentration with a ceiling using a strict
  inequality on a value that lands on the boundary. The verdict then
  flips between platforms and between runs for no physical reason.

## Behavior contract (gate 3)

Threshold-band refusal, ceiling evaluation and reporting precision,
backwards selection of the least demanding class including the
on-the-boundary case, the no-room-class refusal, the looser-than-needed
rejection, the overspend report and the occupancy-state rule are
exercised by the gate 3 contract test:
scripts/test_q7001_cleanroom_class_requirements.py against
scripts/q7001_cleanroom_class_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_cleanroom_class_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
