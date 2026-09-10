---
name: e1003-eq-general-tests
description: "Use when running the general equipment test requirements of ECSS-E-ST-10-03C 5.5.1 within a qualification, acceptance, or protoflight test sequence: run the functional/performance test at each sequence position (baseline and final comprehensive, interim abbreviated unless an anomaly is suspected), evaluate current measurements against the baseline to flag degraded parameters, verify physical configuration (mass properties and visual inspection) at each test point, and confirm the launch configuration for any test representative of the launch environment, closing out the sequence only when every mandatory position is present and clear. Anchor: E-ST-10-03C clause 5.5.1. Trigger: equipment general tests, functional test, performance test, physical configuration check, launch configuration check, baseline functional test, protoflight test sequence, e-st-10-03, ecss."
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
  tags: [ecss, e-st-10-03c, equipment-testing, functional-test, physical-configuration, launch-configuration, test-sequence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Equipment General Test Requirements (space-systems/ecss/e1003-eq-general-tests)

Use when the task is running the general checks that accompany every test
in an equipment-level qualification, acceptance, or protoflight test
sequence under ECSS-E-ST-10-03C clause 5.5.1: functional/performance
testing, physical configuration verification, and launch configuration
verification. This sits inside the campaign baselines set by the
sibling e1003-eq-qual, e1003-eq-acceptance, and e1003-eq-protoflight
leaves, and applies at every mechanical, pressure, thermal, and
electrical test point in the sequence (sibling e1003-eq-mechanical,
e1003-eq-pressure, e1003-eq-thermal, e1003-eq-electrical leaves).

## Domain quick reference

- ECSS-E-ST-10-03C clause 5.5.1 requires three checks around each test
  in an equipment test sequence, independent of which specific
  environmental test is being run: a functional/performance test, a
  physical configuration verification, and (where relevant) a launch
  configuration verification.
- The functional/performance test establishes a comprehensive baseline
  before the sequence starts and repeats a comprehensive run at the end;
  the interim checks between environmental tests may be abbreviated,
  unless an anomaly is suspected, in which case a comprehensive run is
  needed to characterize it regardless of sequence position.
- Each functional/performance run is judged against the baseline, not
  against a fixed pass/fail spec alone -- a parameter that drifts beyond
  its allowed tolerance from the baseline is a degradation, even if it
  is still nominally within the equipment's overall performance
  envelope.
- Physical configuration verification covers mass properties (mass
  against a reference value and tolerance) and visual inspection for
  physical anomalies (e.g. loose hardware, cracks, contamination); either
  a mass out of tolerance or a visual anomaly is a configuration
  discrepancy.
- Launch configuration verification only applies to a test that
  represents the launch environment (e.g. the mechanical tests of the
  sibling e1003-eq-mechanical leaf); it confirms the item under test is
  in its actual launch configuration (covers on/off, stowed/deployed,
  protective covers) rather than a bench or lab configuration that would
  not represent flight.

## Workflow

1. For each point in the test sequence, capture: its position (baseline,
   interim, or final), whether an anomaly is suspected at that point,
   the baseline and current functional/performance measurements with
   their tolerance, the measured and reference mass with its tolerance,
   whether a visual anomaly was found, whether this test represents the
   launch environment, and the current vs required launch configuration.
2. Determine the required functional/performance test depth for the
   point: comprehensive for the baseline and final positions or whenever
   an anomaly is suspected; abbreviated otherwise.
3. Compare the current functional/performance measurements against the
   baseline within tolerance and list any parameter that has drifted
   beyond it -- a degraded parameter is a sequence anomaly regardless of
   test depth.
4. Verify physical configuration at the point: mass within tolerance of
   the reference and no visual anomaly reported; either failure is a
   configuration discrepancy.
5. Where the test point represents the launch environment, verify the
   current configuration matches the required launch configuration;
   points that do not represent the launch environment are exempt from
   this check.
6. Disposition each point as pass only when there is no degraded
   parameter, no configuration discrepancy, and (if applicable) the
   launch configuration matches; otherwise assign the specific blocking
   verdict so it can be dispositioned before the sequence continues.
7. Before closing the general test requirements for the sequence,
   confirm both a baseline and a final position are present and that
   every disposition in the sequence is a pass; otherwise report the
   missing mandatory positions and the open (non-pass) points.

## Pitfalls

- Running only an abbreviated functional/performance test at the
  baseline or final position -- both must be comprehensive so later
  interim results have a full-coverage reference to compare against.
- Judging a functional/performance result against the nominal spec
  alone instead of against the baseline -- a drift within spec can still
  be a real degradation the baseline comparison is meant to catch.
- Treating a mass-in-tolerance result as sufficient physical
  configuration verification while ignoring a reported visual anomaly.
- Applying the launch configuration check to a test that does not
  represent the launch environment (e.g. a pure functional bench test),
  or skipping it on a test that does.
- Closing out the general test requirements for a sequence that is
  missing its baseline or final functional/performance point, or that
  still has an unresolved anomaly at an interim point.

## Behavior contract (gate 3)

The functional-depth, baseline-comparison, physical-configuration, and
launch-configuration logic is exercised by the gate 3 contract test:
scripts/test_e1003_eq_general_tests.py against
scripts/e1003_eq_general_tests_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_eq_general_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
