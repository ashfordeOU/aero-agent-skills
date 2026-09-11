---
name: e1011-arch-complements
description: "Use when verify that an internal spacecraft zone provides adequate architecture complements under ECSS-E-ST-10-11C §4.7.4: check that every crew-access path has handrails spaced within the allowable gap limit, every defined workstation carries at least one foot or body restraint, all mobility-aid elements form a continuous path with no uncovered gap exceeding the threshold, and all stowage items fall within the anthropometric reach envelope. Collect findings per zone and determine overall compliance. Trigger: ecss, e-st-10-11c, e-st-10-system-scope, architecture-complements, handrails, restraints, mobility-aids, stowage, microgravity, human-factors."
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
  tags: [ecss, e-st-10-11c, e-st-10-system-scope, architecture-complements, handrails, restraints, mobility-aids, stowage, microgravity, human-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Architecture Complements (space-systems/ecss/e1011-arch-complements)

Use when the task is the architecture complements assessment under
ECSS-E-ST-10-11C §4.7.4 — verifying that handrails, restraints,
mobility aids, and stowage provisions in a crewed spacecraft zone
satisfy the crew-access and reach requirements for the assigned mission
and crew population.

## Domain quick reference

- §4.7.4 identifies four categories of architecture complement that a
  habitable zone must provide: handrails (continuous crew-access aids
  along walls, floors, and ceilings); restraints (foot or body
  restraints anchoring crew at defined workstations); mobility aids
  (handholds, translation paths, and ladder elements that allow
  controlled movement between zones); and stowage provisions (lockers,
  bags, and attachment points that hold equipment within the crew's
  anthropometric reach envelope). Each category is assessed
  independently; a finding in one does not waive the others.
- Handrail spacing: adjacent handrail elements must not be separated by
  a gap that prevents a crew member from maintaining a grip during
  translation. The limit applied here (500 mm) is a widely used
  microgravity-ergonomics threshold derived from population reach data.
  Any gap exceeding the limit is a finding regardless of whether a
  crew member can currently bridge it under nominal conditions.
- Workstation restraints: every location designated as a workstation
  must carry at least one of: foot restraint, body restraint, or tether
  point. A workstation with no restraint on record is flagged; a zone
  with no workstations defined is not flagged (no applicable
  requirement).
- Mobility-aid path continuity: the sequence of handholds and translation
  aids between two end points of a mobility path must not contain any
  single gap larger than 500 mm. A gap beyond this limit means a crew
  member must release contact to bridge it, which is a falls-and-injury
  risk in microgravity.
- Stowage reach: each stowage item must be accessible from a restrained
  or seated crew position; the centroid of the item must lie within
  710 mm of the crew reference point. Items beyond this envelope require
  crew to release their restraint to retrieve them — a workstation
  safety concern.

## Workflow

1. Identify the zone boundary and list every crew-access path, workstation,
   mobility path, and stowage item in scope. Reject a complement element
   with an unrecognized type before the assessment proceeds.
2. For each handrail run in the zone, measure the spacing between every
   pair of adjacent elements; record any gap that exceeds 500 mm as a
   handrail finding for that zone.
3. For each defined workstation, confirm that at least one foot
   restraint, body restraint, or tether point is on record; record any
   workstation with no restraint as a restraint finding.
4. For each mobility path, walk the sequence of gap distances between
   adjacent aids; record the path as a mobility finding if any single
   gap exceeds 500 mm, and capture the maximum gap for sizing corrective
   action.
5. For each stowage item, measure its access distance from the crew
   reference point; record any item whose distance exceeds 710 mm as a
   stowage finding.
6. Aggregate the findings by category (handrail, restraint, mobility,
   stowage); the zone is compliant only when all four categories are
   empty.

## Pitfalls

- Evaluating handrail continuity only along the nominal translation
  path and omitting secondary approach directions — crew may need to
  translate from multiple orientations in microgravity, and a gap that
  is reachable from one direction may not be from another.
- Treating a missing restraint at a workstation as acceptable because
  the crew has demonstrated they can brace against adjacent structure —
  §4.7.4 requires a dedicated restraint; opportunistic bracing is not a
  compliant substitute and introduces posture variability that degrades
  task performance.
- Closing a mobility-path gap finding by adding a single new handhold
  at the midpoint without re-checking both sub-gaps — adding one element
  creates two new intervals, and both must be checked against the 500 mm
  limit.
- Measuring stowage reach to the front face of the locker rather than
  to the centroid of the contained item — the operative distance is to
  the item's location inside the stowage volume, not the locker door.

## Behavior contract (gate 3)

The complement-type validation, handrail-spacing, workstation-restraint,
mobility-path continuity, stowage-reach, and aggregated zone review
logic is exercised by the gate 3 contract test:
scripts/test_e1011_arch_complements.py against
scripts/e1011_arch_complements_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_arch_complements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
