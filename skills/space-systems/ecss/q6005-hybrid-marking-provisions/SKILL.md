---
name: q6005-hybrid-marking-provisions
description: "Evaluate the marking scheme a hybrid microcircuit programme proposes for its finished units and decide whether the identification it puts on them is permanent, legible and traceable, under ECSS-Q-ST-60-05 clause 10.2. Use when a marking approach needs grading before it is frozen: test the method against the surface it goes on and the processing the unit still faces, size the mark against the free area of the package body, judge where the mark is placed, check that it binds the unit to its lot record and serial register, and return the marking-provision index with one verdict. Trigger: ecss, q-st-60-05, hybrid-marking-provisions, hybrid-marking-permanence-grade, hybrid-package-body-marking-area, hybrid-marking-placement, hybrid-marking-traceability-link, alternative-hybrid-identification, hybrid-marking-scheme-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-hybrid-marking-provisions, hybrid-marking-permanence-grade, hybrid-package-body-marking-area, hybrid-marking-placement, hybrid-marking-traceability-link, alternative-hybrid-identification, hybrid-marking-scheme-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Marking Provisions (space-systems/ecss/q6005-hybrid-marking-provisions)

Use when the task is clause 10.2 of ECSS-Q-ST-60-05: the general provisions
for identifying a finished hybrid — the scheme as a whole, decided before the
first unit is marked, rather than the individual characters the package body
ends up carrying.

## Domain quick reference

- Permanence is not a property of the marking method alone. It is the method
  measured against everything the unit still faces after it is marked: a mark
  that survives handling is not a mark that survives solvent cleaning, and the
  hardest exposure still ahead is the one the method has to answer.
- A method also has to suit the surface it goes on. A method the declared
  package material will not take is refused outright rather than graded down,
  because the mark either does not form or does not stay on.
- Legibility is a geometry question before it is an inspection question. The
  character height, the longest line, the line count and the margins give the
  mark a footprint, and that footprint either fits the face it is assigned to
  or it does not.
- Where the mark goes decides what it identifies. A mark on a removable lid
  identifies the lid, and the unit is anonymous the moment the lid is changed.
  A mark on the container identifies the shipment, which is the route left for
  a unit with no usable face — but only when the container record is genuinely
  maintained, and never for a unit whose body had the room.
- The mark is an index into the records, not the record. A scheme that puts a
  flawless permanent mark on every unit without binding it to the lot record
  and the serial register has identified nothing.
- The provisions are what is frozen; the content of the mark and the
  durability evidence for the lettering are graded separately, against the
  standard content requirements.

## Workflow

1. Name the product and collect the scheme: method, package surface, where the
   mark goes, whether the lid comes off, the character height and the lines
   the mark is to carry.
2. Collect the processing the marked unit still faces, and take the hardest of
   those exposures as the permanence the method has to reach.
3. Refuse a method the declared surface cannot take, before grading anything
   else about the scheme.
4. Size the mark: longest line and character height give the width, line count
   and pitch give the depth, margins are added to both, and the result is
   compared with the face it is assigned to under a named tolerance.
5. Judge the placement — a removable lid is a finding on its own, and
   container-only identification is a finding whenever the body had the room.
6. Check the records behind the mark: the lot link, the serial register, and
   the container record whenever the container is carrying the identification.
7. Grade every provision element against the full set, so an element nobody
   mentioned is graded as not defined, and mark the mandatory ones.
8. Take weighted credit over total weight as the marking-provision index and
   name the verdict — incomplete while a mandatory provision is absent,
   inadequate on an unsuitable method, a short permanence, a mark that does
   not fit, a placement finding, a broken record link or a low index, adequate
   with open actions when findings remain, adequate only when none do.

## Pitfalls

- Choosing the method from the package and stopping there. The surface says
  which methods are possible; the downstream processing says which of those
  are sufficient, and only the second question is about permanence.
- Marking the lid because it is the flat face. A lid that can be removed or
  replaced carries the identification away with it, and a unit that has lost
  its identity cannot be given one back from the records.
- Falling back to container identification for convenience. It exists for
  units with no usable face; used on a unit whose body had room it converts a
  per-unit identification into a per-shipment one.
- Sizing the mark from the character height alone. The longest line and the
  line pitch decide the footprint, and a mark that is legible in isolation can
  still not fit the face it was drawn for.
- Treating a permanent, legible mark as traceability. Until the mark resolves
  to a lot record and a serial register, it identifies the unit to nobody.
- Freezing the scheme without a remarking rule. Every unit that is reworked or
  re-screened will need its mark changed, and an undefined remarking route is
  where a second identity enters the fleet.

## Behavior contract (gate 3)

The permanence demand, the method-surface check, the footprint geometry and
face fit, the placement rules, the traceability link checks, the provision
grading, the marking-provision index and the scheme verdict are exercised by
the gate 3 contract test:
scripts/test_q6005_hybrid_marking_provisions.py against
scripts/q6005_hybrid_marking_provisions_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6005_hybrid_marking_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
