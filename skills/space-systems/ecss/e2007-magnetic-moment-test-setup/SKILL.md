---
name: e2007-magnetic-moment-test-setup
description: "Evaluate the field-compensated setup an intrinsic magnetic moment determination needs, under ECSS-E-ST-20-07C clause 5.4.5.2. Use when a moment-test area is prepared or reviewed: check the residual field left after compensation against the stated tolerance, derive from the unit's largest dimension the separation at which it still reads as one dipole, compute the axial field that separation delivers from the expected moment, compare it with the magnetometer noise floor for usable margin, and separate ferromagnetic hardware in the area from a fixture merely undeclared. Trigger: ecss, e-st-20-07c, magnetic-moment-test-setup, field-compensated-facility, compensation-residual-field, dipole-far-field-separation, magnetometer-noise-floor-margin, non-magnetic-test-fixture."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-magnetic-moment-test-setup, field-compensated-facility, compensation-residual-field, dipole-far-field-separation, magnetometer-noise-floor-margin, non-magnetic-test-fixture]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Magnetic Moment Test Setup (space-systems/ecss/e2007-magnetic-moment-test-setup)

Use when the task is the setup requirement of ECSS-E-ST-20-07C clause
5.4.5.2 -- standing the unit in an area whose ambient field has been
compensated away, so that what the magnetometers pick up is the unit's
own intrinsic moment and not the building it is sitting in.

## Domain quick reference

- Compensation is a state, not a switch. A coil system that is running
  still leaves a residual, and the residual is what decides whether the
  area is usable. Take the three axis components, form the vector
  magnitude, and compare that against the tolerance the test declares --
  a per-axis check alone passes an area whose three modest residuals
  sum to a field that swamps a small unit.
- The site field is not merely large, it is the wrong shape. It is
  near-uniform across the test volume, so it does not fall off with
  distance the way the unit's dipole does and cannot be subtracted by
  moving the sensors further out. That is why the clause compensates
  the area rather than correcting the numbers afterwards.
- Intrinsic moment only exists at a distance. Inside a few unit
  dimensions the magnetometer sees the individual magnets, motors and
  current loops rather than their sum, and the number that comes back
  is an artefact of where the sensor happened to sit. Three times the
  largest dimension is the usual working floor for a single-dipole
  reading.
- Distance is bought at a steep price. The axial dipole field falls
  with the cube of separation, so doubling the distance to buy
  point-source behaviour costs a factor of eight in signal. The setup
  has to clear both the separation floor and the noise floor at once,
  and on a small moment those two pull against each other.
- Ferromagnetic hardware in the area and an undeclared fixture are
  different problems. Steel in the volume carries a moment of its own
  that adds to the unit's and that no coil setting removes; a fixture
  nobody characterized may be clean, and its risk is that the reading
  cannot be attributed with confidence.

## Workflow

1. Validate the setup record: residual components finite, tolerance,
   dimension, separation, expected moment and noise floor all positive,
   and the compensation, fixture and hardware flags boolean.
2. Form the residual vector magnitude and group the area as
   compensated, partially compensated or uncompensated against the
   declared tolerance.
3. Derive the minimum separation from the unit's largest dimension and
   the point-dipole ratio, then compare the planned sensor distance
   against it.
4. Compute the axial field the expected moment produces at the planned
   separation.
5. Divide that field by the magnetometer noise floor and compare the
   ratio against the working minimum.
6. Aggregate: compensation off, a residual over tolerance, sensors
   inside the separation floor, a field lost in the noise or
   ferromagnetic hardware present are findings; an undeclared fixture
   and a thin-but-adequate noise margin are limitations.

## Pitfalls

- Reporting compensation as a yes/no. The residual is the measurement;
  a running coil system with a 200 nT residual is not a compensated
  area for a unit whose own field is tens of nanotesla.
- Checking each residual axis against the tolerance separately. Three
  components each just inside the limit give a vector magnitude well
  outside it.
- Pushing the sensors close to win signal. Under a few unit dimensions
  the reading stops being a moment at all, and it will look
  reassuringly large and repeatable while being wrong.
- Quoting a noise floor from the magnetometer datasheet and stopping
  there. The floor that matters is the one in the compensated area with
  the coils energised, and it is normally worse.
- Treating an uncharacterized fixture as a failure. It does not
  invalidate the setup on its own; it means part of a reading cannot be
  attributed, which is a limitation to record rather than a finding.

## Behavior contract (gate 3)

The setup validation, residual magnitude and compensation grouping,
minimum-separation derivation, axial dipole field, noise-floor ratio,
fixture and hardware checks and the aggregate verdict are exercised by
the gate 3 contract test:
scripts/test_e2007_magnetic_moment_test_setup.py against
scripts/e2007_magnetic_moment_test_setup_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2007_magnetic_moment_test_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
