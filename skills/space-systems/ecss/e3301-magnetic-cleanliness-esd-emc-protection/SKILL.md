---
name: e3301-magnetic-cleanliness-esd-emc-protection
description: "Evaluate a mechanism against the magnetic cleanliness budget and the electrostatic and electromagnetic protection of ECSS-E-ST-33-01C clause 4.7.7.8. Use when the task is combining residual dipole moments by root-sum-square or worst-case alignment, deciding which combination the design actually earns, converting the governing moment into the stray field at a magnetometer, grading every conductive surface against the charge-bleed resistance window, and comparing a drive's switching harmonics with the protected receiver bands alongside its filter and screen termination. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-residual-dipole-moment, magnetometer-stray-field-limit, surface-charge-bleed-window, drive-switching-harmonic-conflict, mechanism-esd-protection, mechanism-emc-screen-termination."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-magnetic-cleanliness-esd-emc-protection, mechanism-residual-dipole-moment, magnetometer-stray-field-limit, surface-charge-bleed-window, drive-switching-harmonic-conflict, mechanism-emc-screen-termination]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Magnetic Cleanliness, ESD and EMC Protection (space-systems/ecss/e3301-magnetic-cleanliness-esd-emc-protection)

Use when the task is the cleanliness-and-protection step of
ECSS-E-ST-33-01C clause 4.7.7.8 -- showing that a mechanism's magnets,
motors and latches stay inside the magnetic budget they were allocated,
and that the mechanism neither builds a discharge nor emits into a
receiver it shares the vehicle with.

## Domain quick reference

- A mechanism's residual dipole moment is the sum of several sources:
  stepper-motor magnets, latch magnets, current loops in the drive
  harness, and permeable material that has taken a remanent moment from
  ground handling. The budget is allocated against the combined moment,
  not against the largest one.
- How the sources combine depends on what the design fixes. Orientations
  that the mechanical design genuinely constrains may be combined by
  root-sum-square; orientations that are free, or simply unrecorded,
  have to be combined as if aligned. Root-sum-squaring an unknown
  orientation is the commonest way a magnetic budget passes on paper
  and fails on the magnetometer.
- The moment is the budget quantity; the field at the magnetometer is
  the mission quantity. Because a dipole field falls with the cube of
  distance, a moment that is comfortable at three metres can dominate
  the science signal at half a metre, so both are graded.
- Charge bleed is a window, not a floor. Too resistive and a surface
  floats until it discharges into something; too conductive and the
  bleed path becomes a fault-current route that defeats the isolation
  it was fitted beside. An isolated conductive surface with no path at
  all is the worst of the three.
- A mechanism drive is a switching converter bolted to a moving load.
  Its fundamental and the harmonics above it are narrowband emissions
  that couple out along the motor harness, so the harness screen and
  its termination are part of the emission control, not an assembly
  detail.
- Harmonic placement is checkable at design time. Knowing the switching
  frequency and the receiver bands on the vehicle tells you before
  build whether a harmonic lands inside one, and moving the switching
  frequency is cheap then and expensive later.

## Workflow

1. Validate each magnetic source: identifier, moment, and whether the
   design fixes its orientation.
2. Combine the moments both ways. When any source's orientation is not
   fixed, the aligned sum governs; otherwise the root-sum-square does.
   Record which combination governed and why.
3. Convert the governing moment into the on-axis field at the
   magnetometer distance and grade it against the sensor limit; grade
   the moment against its allocation separately.
4. Validate each conductive surface and grade its bleed resistance
   against the window. A surface with no declared path is a finding in
   its own right.
5. Generate the switching fundamental and its harmonics for each drive
   and test each against the protected bands; raise a finding per
   conflicting harmonic.
6. Grade the declared conducted-emission filter and the screen
   termination of each drive harness.
7. Report the magnetic, electrostatic and electromagnetic records with
   the aggregated findings; the design is compliant only when the list
   is empty.

## Pitfalls

- Root-sum-squaring moments whose orientations nothing fixes. The
  combination is then an assumption about installed hardware that no
  drawing supports, and it understates the worst case by up to the
  ratio of the sum to the quadrature sum.
- Grading the moment and stopping. The magnetometer sees field, and the
  cube law means the same moment passes or fails depending on where the
  mechanism ends up in the accommodation.
- Treating charge bleed as "the lower the better". A low-resistance
  path across an intended isolation carries fault current and can
  couple the very interference the isolation was there to stop.
- Forgetting the surface nobody listed. A sunshield, a thermal blanket
  outer layer or a bare yoke is conductive and will float unless a path
  is drawn for it.
- Declaring a filter and calling the drive compatible. An unterminated
  or single-ended harness screen radiates the filtered noise straight
  back out along the motor cable.
- Checking the switching fundamental only. The fundamental usually sits
  far below the receiver bands; it is the fifth or seventh harmonic
  that lands inside one.

## Behavior contract (gate 3)

The source validation, root-sum-square and aligned combination, the
governing-combination decision, dipole-field conversion, budget and
sensor-limit grading, charge-bleed window grading, harmonic generation,
protected-band conflict detection and filter and screen grading are
exercised by the gate 3 contract test:
scripts/test_e3301_magnetic_cleanliness_esd_emc_protection.py against
scripts/e3301_magnetic_cleanliness_esd_emc_protection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_magnetic_cleanliness_esd_emc_protection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
