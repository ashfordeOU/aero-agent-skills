---
name: e1011-maint-stations
description: "Use when design physical maintenance stations for a crewed spacecraft
  per ECSS-E-ST-10-11C §4.7.8: verify that each station's access zone meets minimum
  reach depth, lateral clearance, and vertical clearance thresholds for intravehicular,
  extravehicular, or hybrid zone types; confirm that registered tools are compatible
  with the station zone type and that large-envelope single-hand tools are flagged
  for operating-arc review; validate that lighting levels meet the minimum lux
  requirement for the zone; and categorize all maintenance tasks by frequency and
  zone type while flagging tasks that reference tools not on record at the station.
  Trigger: ecss, e-st-10-system-scope, maintenance-stations, access-zone, workspace,
  tooling, lighting, human-factors."
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
  tags: [ecss, e-st-10-system-scope, maintenance-stations, access-zone, workspace, tooling, human-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Physical Maintenance Stations (space-systems/ecss/e1011-maint-stations)

Use when the task is to design and verify physical maintenance stations for a
crewed spacecraft per ECSS-E-ST-10-11C §4.7.8 — establishing that each
station's spatial envelope, tooling inventory, lighting, and assigned maintenance
tasks together satisfy the human-factors requirements for crew accessibility and
task performance.

## Domain quick reference

- §4.7.8 treats each maintenance station as a bounded workspace defined by three
  axes: forward reach depth (the crewmember's working distance into the
  station), lateral clearance (the side-to-side working width), and vertical
  clearance (headroom and vertical working range). Minimum values differ by zone
  type: intravehicular activity (IVA) stations accommodate an unsuited
  crewmember, while extravehicular activity (EVA) and hybrid stations must
  accommodate a pressure-suited crewmember whose suit envelope adds to all
  dimensional requirements. HYBRID stations must meet EVA minimums and serve
  both activity modes.
- Tools used at a station must be rated for the station's zone type. A tool that
  is IVA-only cannot be assigned to an EVA or HYBRID station. Tools whose
  single-hand operating arc exceeds 300 mm must be verified for clearance or
  re-designated as two-hand operations so that the full torque arc lies within
  the station envelope.
- Lighting is a separate physical parameter: IVA stations require at least
  150 lux at the work surface; EVA stations require at least 100 lux
  (supplemented where necessary by portable or suit-mounted illumination).
  A lighting value that is absent from the station record is a non-compliant
  finding, not a pass.
- Maintenance tasks are categorized by frequency (routine, on-condition,
  corrective) and by zone type. Each task names the tools it needs; if any
  named tool is not on record at the station, the task is flagged and the
  station is not compliant until the tool is added or the task reference is
  corrected.

## Workflow

1. Inventory every maintenance station in the spacecraft layout and assign it a
   zone type (IVA, EVA, or HYBRID) based on the crew access method documented
   in the maintenance concept.
2. For each station, record the three dimensional parameters: reach depth (mm),
   lateral clearance (mm), and vertical clearance (mm). Compare each against
   the applicable threshold. Flag any axis below the minimum; EVA and HYBRID
   stations use the larger EVA thresholds on all three axes.
3. Register every tool assigned to the station. For each tool, verify it is
   rated for the station zone type. For any tool whose maximum operating
   envelope exceeds 300 mm and is not designated as a two-hand operation, raise
   a finding to verify the arc fits within the station's available clearance.
4. Record the illuminance level (lux) at the work surface. Compare against the
   zone-type minimum. A missing or unverified lighting value is a non-compliant
   finding.
5. Assign maintenance tasks to the station. Categorize each task by frequency
   and zone type. Cross-check each task's required tool list against the tools
   on record at the station; flag any task that references a tool not on record.
6. A station is compliant when all dimensional checks pass, no tooling
   incompatibilities remain, lighting is verified above the minimum, and no
   task references an unresolved tool. Aggregate the findings per station and
   resolve each before the station enters the design review.

## Pitfalls

- Applying IVA dimensional thresholds to a HYBRID station — a HYBRID station
  serves suited crewmembers and must use the larger EVA thresholds even if
  IVA access is also present.
- Treating an absent lighting record as compliant — a lighting value must be
  explicitly measured and recorded; the absence of a finding is not evidence
  of adequacy.
- Assigning a tool to a station without checking zone-type compatibility —
  a tool that works well unsuited may be unusable in a pressure suit; the
  per-tool compatibility flag must be set before the tool is accepted at a
  station.
- Leaving task-to-tool references unresolved — a task that names a tool not
  on record at the station cannot be verified as executable; this is a
  blocking finding, not a documentation gap.

## Behavior contract (gate 3)

Access zone, tooling, lighting, and task-categorization logic is exercised by
the gate 3 contract test: scripts/test_e1011_maint_stations.py against
scripts/e1011_maint_stations_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_maint_stations.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
