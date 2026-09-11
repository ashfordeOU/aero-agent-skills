---
name: e1011-crew-provisions
description: "Use when specifying crew station provisions under ECSS-E-ST-10C §4.7.5:
  identify each station by type (piloting, mission, payload, maintenance), verify
  seat dimensions against the crew anthropometric envelope, confirm restraint load
  capacities for shoulder harness, lap belt, and footrest, assess console reach and
  height against the seated crew envelope, and validate egress clearance against the
  minimum path width. Flag each station that fails a geometry, load, or clearance
  requirement before proceeding to detailed design. Trigger: ecss, e-st-10-system-scope,
  crew-stations, seat-restraints, console-layout, egress, anthropometry, crew-accommodation."
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
  tags: [ecss, e-st-10-system-scope, crew-stations, seat-restraints, console-layout, egress, anthropometry, crew-accommodation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Crew Station Provisions (space-systems/ecss/e1011-crew-provisions)

Use when the task is specifying and verifying crew station provisions under
ECSS-E-ST-10C §4.7.5 — assigning station types, checking seat geometry and
restraint loads against the crew anthropometric envelope, validating console
reach and height, and confirming egress clearance before proceeding to
detailed design.

## Domain quick reference

- §4.7.5 requires each crew station to be categorized by function before
  dimensional requirements are applied. The recognized station types are:
  piloting (primary vehicle control), mission (experiment or payload
  operations), payload (dedicated payload handling), and maintenance
  (system servicing). Each type carries the same geometric and structural
  requirements; the categorization is used to trace requirements to the
  correct system interface.
- Seat geometry is governed by the combined crew anthropometric envelope
  spanning the 5th-to-95th percentile range for the crew population. The
  seat pan must be wide enough and deep enough to accommodate the full
  range. A seat that meets the numeric thresholds is in conformance;
  a seat that falls below either threshold on either axis is a finding
  regardless of margin on the other axis.
- Restraint systems must demonstrate adequate load capacity for the
  three structural attachment points: shoulder harness, lap belt, and
  footrest. Each attachment is assessed independently; a failure on
  one does not relax the requirement on the others.
- Console layout is bounded by a combined reach-and-height envelope
  derived from seated crew reach studies. The lower and upper control
  surface heights are bounded relative to the deck reference plane;
  the maximum reach distance is measured from the torso reference
  point in the nominal seated posture. Controls outside the envelope
  are unreachable under loading conditions.
- Egress clearance is the minimum unobstructed width of the path
  through which crew must pass to exit the station. The requirement
  applies at all points along the egress path; a single narrow point
  governs.

## Workflow

1. Receive the station manifest listing every crew station with its
   assigned station type. Reject any station whose type is not one of
   the four recognized types before proceeding; an unrecognized type
   means a requirements gap that must be resolved upstream.
2. For each station, check seat geometry: confirm the seat pan width
   meets the minimum width threshold and the seat pan depth meets the
   minimum depth threshold. Record a finding for any dimension below
   threshold; a finding on one dimension does not exempt the other
   from being checked.
3. For each station, check restraint load capacity: confirm the
   shoulder harness, lap belt, and footrest each meet their
   respective minimum load ratings. Record a separate finding for
   each attachment point that falls below its minimum.
4. For each station, check console geometry: confirm the lower control
   surface height is at or above the minimum height above deck, the
   upper surface is at or below the maximum height above deck, and
   the maximum control reach distance is within the crew reach
   envelope. Record a finding for each parameter that is out of range.
5. For each station, check egress clearance: confirm the minimum
   unobstructed egress path width meets the required threshold.
   Record a finding if the clearance is below threshold.
6. Aggregate all findings per station. A station is conformant only
   when it has zero findings across all five checks. Present a
   per-station compliance summary and a fleet-level count of
   conformant and non-conformant stations.

## Pitfalls

- Categorizing a station by its primary function and then omitting
  dimensional checks on secondary controls in the same volume — all
  controls that crew must reach from a station are subject to the
  reach and height envelope, not only the primary interface.
- Treating the anthropometric envelope as a single average-user value
  and checking only the 50th-percentile seat — the requirement spans
  the full 5th-to-95th range; a seat sized for the average user fails
  the tails.
- Accepting a restraint system that passes shoulder-harness and
  lap-belt checks but has an undersized footrest — each attachment
  point is independently required; a partial pass is a fail.
- Reading an unconstrained egress path (no furniture in the nominal
  CAD model) as meeting the clearance requirement — the check must
  reflect the as-stowed configuration including crew equipment,
  portable items, and EVA suit stowage when applicable.
- Skipping the station-type validation step and applying a generic
  dimensional matrix — an unrecognized type may map to a different
  human factors standard or a more stringent requirement, and the
  mismatch will not surface until design review.

## Behavior contract (gate 3)

The station-type validation, seat geometry, restraint load, console
envelope, egress clearance, and aggregate assessment logic is exercised
by the gate 3 contract test:
scripts/test_e1011_crew_provisions.py against
scripts/e1011_crew_provisions_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_crew_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
