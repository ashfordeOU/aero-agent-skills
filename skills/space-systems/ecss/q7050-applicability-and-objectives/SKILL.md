---
name: q7050-applicability-and-objectives
description: "Determine whether a spacecraft item or a cleanroom zone owes particle contamination monitoring under ECSS-Q-ST-70-50C, and which of the three modes it owes: read the airborne obligation from the zone, the fallout obligation from the open exposed area and its duration, and the tape-lift obligation from a stated surface cleanliness level, then return the objective each mode answers. Use when scoping a contamination control plan, arguing that a bagged unit sits outside the monitoring scope, or checking that an optical surface has not been left with air data alone. Trigger: ecss, q-st-70-50c, particle-monitoring-applicability, particle-monitoring-objectives, cleanroom-airborne-monitoring-scope, hardware-surface-particle-monitoring, witness-plate-fallout-obligation, tape-lift-obligation."
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
  tags: [ecss, q-st-70-50c-particle-contamination-monitoring, q-st-70-50c, q7050-applicability-and-objectives, particle-monitoring-applicability, particle-monitoring-objectives, cleanroom-airborne-monitoring-scope, witness-plate-fallout-obligation, tape-lift-obligation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle Monitoring — Applicability and Objectives (space-systems/ecss/q7050-applicability-and-objectives)

Use when the task is the framework clause of ECSS-Q-ST-70-50C: what particle
monitoring of hardware surfaces and cleanroom air is for, which usages owe it,
and which of the three monitoring modes answers which question.

## Domain quick reference

- Three modes answer three different questions and none of them substitutes
  for another. Airborne counting grades the air of a zone. Fallout witness
  plates grade the rate at which that air deposits onto an upward-facing
  surface. A tape lift grades the hardware surface itself, including whatever
  it arrived with and whatever handling has since put there.
- The airborne obligation belongs to the zone, not to the item. A room with a
  declared cleanroom class owes counting on its own schedule whether or not
  any hardware is open in it that day, because the class is a property the
  facility maintains and reports.
- The fallout obligation belongs to the item, and only an open item has one.
  Bagged hardware and hardware inside a sealed enclosure collect nothing from
  the room, so a plate beside them measures the room and says nothing about
  the part.
- Deposition is a rate, so exposure duration is part of applicability. A
  general surface open for a few minutes during a lifting operation collects
  a different order of deposit from one open across a two-week integration.
- A de-minimis exposed area keeps the plate count finite, and a sensitive
  surface removes it. A few square centimetres of optic in view of the room
  is exactly the case the contamination budget was written for.
- A tape lift is a contact method. It answers a stated surface cleanliness
  level well, and it is the wrong instrument on a bare optical surface, where
  a co-located witness coupon carries the sample instead.
- Monitoring records an exposure; it does not control one. Open sensitive
  hardware in a zone with no declared class is a containment finding, and no
  amount of counting turns that into a compliant condition.

## Workflow

1. Read the usage rather than the part number: surface sensitivity, the zone
   type, the containment state, the exposed area and the exposure duration.
2. Decide the airborne obligation from the zone type; extend it to a
   controlled area only when sensitive hardware is open in it.
3. Decide the fallout obligation from the containment state first — bagged or
   enclosed hardware is out — then from sensitivity, exposed area and
   duration, waiving the de-minimis area in front of an optical surface.
4. Decide the tape-lift obligation from a stated cleanliness level plus
   physical access, diverting a bare optic to a witness coupon.
5. Attach to each owed mode the objective it answers, so the plan records why
   a sample is taken and not only that it is taken.
6. Raise the usage-level findings the modes cannot cover: open sensitive
   hardware outside a controlled zone, an optic with a lift requested against
   it, and a usage that owes nothing at all, which needs a recorded basis.

## Pitfalls

- Reading air data as surface data. A zone holding its class says the air is
  clean; it does not say the hardware surface is, because handling, tooling
  and prior history deposit particles the air counter never saw.
- Waiving fallout monitoring on a bagged item and then opening it. The
  containment state that carried the waiver is part of the waiver, so a change
  of state re-opens the obligation rather than inheriting the old answer.
- Applying the de-minimis exposed area in front of an optic. Small areas near
  cold or reflective surfaces are where a contamination budget is actually
  spent, which is why the de-minimis rule stops at the sensitive levels.
- Lifting from the optical surface itself. The method removes particles by
  contact and can take coating with them; the coupon exists so the sample does
  not have to be taken from the article under test.
- Treating a short exposure as no exposure. Deposition is a rate, and a
  precision surface open briefly still owes a plate; only the general and
  insensitive levels carry a duration threshold at all.
- Answering an applicability question with a material or a part name. The
  same bracket owes monitoring open on a bench and owes none inside a sealed
  box, so an answer with no zone and no containment behind it is not one.

## Behavior contract (gate 3)

The sensitivity, zone, containment, area and duration validation, the three
per-mode obligation rules, the objective mapping and the usage-level findings
are exercised by the gate 3 contract test:
scripts/test_q7050_applicability_and_objectives.py against
scripts/q7050_applicability_and_objectives_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7050_applicability_and_objectives.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
