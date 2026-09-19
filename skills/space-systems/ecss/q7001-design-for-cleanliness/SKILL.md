---
name: q7001-design-for-cleanliness
description: "Evaluate a design against the cleanliness provisions it owes under ECSS-Q-ST-70-01C: drainage, venting, material choice and surfaces a cleaning operation can reach. Use when a drawing set has been assigned a cleanliness level and somebody has to say whether the hardware can be built, cleaned and held there. Sizes each vent path from the depressurizing time constant it must achieve, finds trapped volumes with no drain, requires exposed-surface materials to come from the screened set, and grades the reachable share of the surface area. Reports each provision separately so one failure does not hide the rest. Trigger: ecss, q-st-70-01, design-for-cleanliness-provisions, enclosure-vent-sizing, trapped-volume-drainage, cleanable-surface-accessibility, exposed-surface-material-screening, contamination-design-review."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-design-for-cleanliness, design-for-cleanliness-provisions, enclosure-vent-sizing, trapped-volume-drainage, cleanable-surface-accessibility, exposed-surface-material-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Design Provisions (space-systems/ecss/q7001-design-for-cleanliness)

Use when the task is the design clause of ECSS-Q-ST-70-01C — checking
that a design carries the provisions its assigned cleanliness level
depends on, so the level is something the hardware can be brought to
and held at rather than a number written on a drawing.

## Domain quick reference

- Cleanliness is designed in, not cleaned in. Every provision here is
  cheap on a drawing and close to impossible once the hardware exists:
  a drain hole is a change of a few grams before release and a
  structural modification afterwards.
- A vent is a sizing problem before it is a hole. The enclosed volume
  has to follow the ambient pressure down through ascent without
  building a differential the structure or a seal cannot take, and the
  time constant that demands is what fixes the free area. Volume
  divided by the product of the free area and the path conductance is
  the quantity to compare with the limit.
- A vent is also a contamination path in both directions. An unfiltered
  vent carries whatever the volume has collected straight out, and a
  plume aimed at a radiator or an optic deposits it exactly where the
  budget has least room. Filtering and direction are provisions in
  their own right, not refinements of the sizing.
- Drainage is about cleaning fluid, not just launch. A blind hole, an
  unvented honeycomb cell or an upward-facing pocket holds the
  solvent and the contamination it lifted; when it finally evaporates,
  the residue is left concentrated in the place hardest to inspect.
- Material choice belongs to the exposed surface. A material inside a
  sealed, separately controlled volume is a different question from the
  same material on a line of sight to a sensitive surface, and only the
  exposed population is graded against the screened set here.
- A surface a cleaning operation cannot reach cannot be brought to a
  level, and cannot be shown to be at one either. The reachable area
  fraction is a design output, and the level a design can support is
  bounded by it.

## Workflow

1. For each enclosed volume, validate the volume, free vent area and
   path conductance, compute the depressurizing time constant, and
   compare it with the limit. When it misses, report the free area the
   volume actually needs rather than only the shortfall.
2. Check the same vent for filtration and for the direction its plume
   travels; record either failure separately from the sizing.
3. Walk the geometric feature list and list every feature that traps
   fluid and carries no drain path. A feature that traps nothing needs
   no drain and is not a finding.
4. Grade the exposed-surface materials: refuse an exposed material with
   no screening behind it, and flag one that is screened but misses the
   low-outgassing criterion, naming a known substitute where one
   exists.
5. Compute the reachable area fraction and compare it with what the
   assigned level needs, absorbing an exact landing with a named
   tolerance.
6. Report every provision separately, list which are met and which are
   outstanding, and only call the design compliant when all of them are
   met.

## Pitfalls

- Sizing a vent from a rule of thumb area per volume. The quantity that
  matters is the time constant, and two enclosures with the same
  volume-to-area ratio behave differently once the path conductance
  differs.
- Treating a vent as sized and therefore done. An adequately sized vent
  with no filter, or one pointed at an optic, moves the contamination
  problem rather than solving it.
- Reading a drain hole as a launch provision only. Most of what a drain
  removes is ground-phase cleaning fluid, so an item that never sees a
  pressure transient can still need one.
- Grading every material in the build against the exposed-surface
  criterion. It buries the exposed population that actually matters in
  a list dominated by internal items behind their own barriers.
- Accepting an inaccessible surface because it is small. Inaccessible
  area cannot be verified, so it is not a small overrun risk but an
  unbounded one, and it caps the level the whole item can claim.
- Declaring the design compliant on the strength of the provisions that
  passed. The provisions are independent, and one outstanding drain
  path is as capable of losing the level as all four failing.

## Behavior contract (gate 3)

The vent time-constant sizing and required-area inversion, the
filtration and plume-direction checks, undrained trapped-feature
detection, exposed-surface material grading, reachable-area fraction
and the provision-by-provision roll-up are exercised by the gate 3
contract test: scripts/test_q7001_design_for_cleanliness.py against
scripts/q7001_design_for_cleanliness_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_design_for_cleanliness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
