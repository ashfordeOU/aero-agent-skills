---
name: e2007-low-frequency-conducted-emission-setup
description: "Verify the bench arrangement a low-frequency conducted-emission run is built on under ECSS-E-ST-20-07C clause 5.4.2.3: confirm the ground plane overhangs the unit footprint on every side and the unit bond stays under its resistance limit, then grade each measured lead for its stabilisation network, the current-probe offset from the connector, the harness height above the plane and the separation from every other harness, separating true deviations from dimensions merely sitting at the edge of their window. Use when building or auditing a low-frequency conducted-emission bench before the procedure starts. Trigger: ecss, e-st-20-07c, lf-conducted-emission-setup, conducted-emission-ground-plane-bond, current-probe-offset-window, conducted-emission-harness-height, conducted-emission-harness-separation, lisn-presence-per-lead."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-low-frequency-conducted-emission-setup, lf-conducted-emission-setup, conducted-emission-ground-plane-bond, current-probe-offset-window, conducted-emission-harness-height, conducted-emission-harness-separation, lisn-presence-per-lead]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Low-Frequency Conducted-Emission Setup (space-systems/ecss/e2007-low-frequency-conducted-emission-setup)

Use when the task is the bench arrangement of ECSS-E-ST-20-07C clause
5.4.2.3 -- the layout the low-frequency conducted-emission method adds on
top of the standard test configuration, and the conformance decision on
the plane, the bond and each measured lead run before any reading is
taken.

## Domain quick reference

- The arrangement is an addition, not a replacement. The standard
  configuration already fixes the plane, the support equipment and the
  bonding; this clause adds where the probe is clamped, how high the
  measured harness runs and how far it stays from everything else.
- The ground plane must overhang the unit footprint on every side. The
  overhang is what keeps the return path under the harness rather than
  wandering off the edge, so the margin is graded per axis and the
  smaller axis governs.
- The bond between the unit and the plane is a resistance, and a
  milliohm-level limit is what makes the plane a reference rather than a
  second radiator. A bond present but high is worse than an obvious
  missing strap, because nothing on the bench looks wrong.
- Probe offset from the unit connector is a dimension with a window, not
  a preference. Moving the probe down the harness changes the stray
  capacitance between harness and plane that the measured current sees,
  so two runs at different offsets are not comparable.
- Harness height above the plane sets the loop the measured current
  closes through. A harness resting on the plane and one standing at the
  nominal height give different low-frequency levels on the same unit.
- Separation from other harnesses keeps neighbouring cables from coupling
  into the measured lead. A lead run alongside the support-equipment
  harness records the neighbour as much as the unit.
- Every measured lead carries its own stabilisation network. A lead
  measured without one sees the facility supply impedance instead of the
  controlled one, and the reading is a property of the building.
- A dimension inside its window but close to the edge is a limitation to
  carry, not a deviation to raise. Keeping the two apart stops a bench
  being rebuilt over a millimetre and stops a real deviation being filed
  as a rounding matter.

## Workflow

1. Validate the plane and the unit footprint, compute the per-axis
   overhang, and compare it with the required margin.
2. Validate the bond: present, non-negative, and inside the resistance
   limit, keeping the headroom for the report.
3. Normalize each lead run to a recognized lead designation and reject a
   lead appearing twice; a duplicate means two runs were merged.
4. Grade the probe offset and the harness height against their windows,
   splitting each result into conforming, marginal or deviation.
5. Compare the separation against the minimum and confirm the
   stabilisation network is in the lead.
6. Aggregate: plane findings, then per-lead deviations, with the marginal
   dimensions carried separately as limitations. The bench conforms only
   when no finding stands.

## Pitfalls

- Grading the plane by area. A plane that is generous lengthwise and
  short across still lets the return path leave the surface, so the
  margin is decided per axis.
- Treating a fitted bonding strap as a passed bond. The limit is on the
  resistance, and a corroded or paint-trapped joint passes inspection and
  fails the measurement.
- Clamping the probe wherever the harness is easiest to reach, then
  comparing the run against one taken at the nominal offset.
- Letting the measured harness sag onto the plane between supports, which
  changes the loop the current closes through along its length.
- Routing the measured lead beside the support-equipment harness because
  the bench is crowded, and recording the neighbour's noise.
- Fitting stabilisation networks on the primary leads only and measuring
  a secondary lead straight off the facility supply.
- Filing every millimetre at the window edge as a deviation, so the real
  deviations stop being read.

## Behavior contract (gate 3)

The plane-margin and bond validation, lead-run normalization, windowed
dimension grading, separation and network checks and the conformance
aggregation logic is exercised by the gate 3 contract test:
scripts/test_e2007_low_frequency_conducted_emission_setup.py against
scripts/e2007_low_frequency_conducted_emission_setup_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_low_frequency_conducted_emission_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
