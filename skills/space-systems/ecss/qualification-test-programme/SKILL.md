---
name: qualification-test-programme
description: "Use when determine which qualification tests are required for a pressure component under ECSS-E-ST-32 clause 5.4: compute proof, design-burst, and burst pressures from the Maximum Expected Operating Pressure (MEOP) using material-specific pressure factors; establish the mandatory test sequence covering proof, leak, vibration, pressure-cycling, design-burst, and burst tests; evaluate each individual test result against its acceptance criterion; and report whether the component achieves qualification status. Trigger: ecss, e-st-32-structures-scope, qualification-test, proof-pressure, burst-test, pressure-cycling, leak-test, vibration-test."
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
  tags: [ecss, e-st-32-structures-scope, qualification-test, proof-pressure, burst-test, pressure-cycling, leak-test, vibration-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Qualification Test Programme (space-systems/ecss/qualification-test-programme)

Use when the task is to determine and execute the qualification test
programme for a pressure-bearing space structure component under
ECSS-E-ST-32 clause 5.4 — establishing mandatory tests, computing
required pressures from MEOP and material-specific factors, sequencing
tests in the correct order, and evaluating each result against its
acceptance criterion.

## Domain quick reference

- Clause 5.4 defines a mandatory set of qualification proof tests for
  pressure components. The programme spans up to six test types:
  **proof**, **leak**, **vibration**, **pressure-cycling**,
  **design-burst**, and **burst**. Each test type belongs to one of
  two families: pressure tests (proof, leak, pressure-cycling,
  design-burst, burst) or dynamic tests (vibration). All six are
  required for composite-overwrap pressure vessels; metallic vessels
  require at minimum proof, leak, and burst.
- Required test pressures are derived from the Maximum Expected
  Operating Pressure (MEOP) using material-specific pressure factors.
  Metallic components use a proof factor of 1.5 and a burst factor of
  2.0; composite-overwrap components use 1.5 for proof and 2.25 for
  burst. The design-burst pressure equals the computed burst pressure
  target and is verified by test prior to the final destructive burst.
- Vibration comes first in the sequence to ensure dynamic integrity
  is demonstrated on an unfatigued article; proof and leak follow to
  verify structural tightness; pressure-cycling accumulates fatigue
  representative of mission life; design-burst confirms the burst
  margin at non-destructive pressure; burst (destructive) closes the
  programme.
- Acceptance criteria: a pressure test passes when the applied
  pressure meets or exceeds the required level with no leak detected.
  The vibration test passes when no structural failure or anomalous
  response is observed. Any missed mandatory test leaves the component
  unqualified regardless of all other results.

## Workflow

1. Identify the component's material type (metallic or
   composite-overwrap) and record its MEOP. Reject an unrecognized
   material or a non-positive MEOP before proceeding.
2. Compute the required test pressures:
   - Proof pressure = MEOP × proof factor (1.5 for both material
     types under clause 5.4).
   - Burst pressure = MEOP × burst factor (2.0 metallic, 2.25
     composite).
   - Design-burst pressure = burst pressure (same target, applied
     before the destructive burst event).
   - Pressure-cycling amplitude = MEOP (cycled between zero and MEOP
     for the number of cycles representative of the mission life).
3. Determine the mandatory test list for the material type and arrange
   tests in the required sequence: vibration → proof → leak →
   pressure-cycling → design-burst → burst. Metallic components
   omit vibration, pressure-cycling, and design-burst unless
   additionally required by the programme.
4. Execute each test and record the result: applied pressure (for
   pressure tests), whether a leak was detected (proof and leak
   tests), and any structural anomaly (vibration test).
5. Evaluate each test result against its criterion: applied pressure
   at or above the required level; no leak; no structural anomaly.
   Record a finding for every failing criterion.
6. Check that every mandatory test for the material type appears in
   the executed list. Any missing mandatory test is itself a finding.
7. Aggregate all findings. A component is qualified only when the
   finding list is empty.

## Pitfalls

- Using MEOP directly as the test pressure without applying the
  material-specific factor — the required proof or burst pressure is
  always above MEOP; using MEOP as the test level never meets the
  criterion.
- Omitting the vibration test for a composite-overwrap vessel on the
  grounds that no dynamic load environment was identified — the test
  is mandatory for composite components regardless, and the sequence
  (vibration first) is load-bearing; reversing the order can mask
  fatigue-induced delamination.
- Reading a result as a pass when the applied pressure exactly equals
  the required pressure but a small leak is present — both criteria
  (pressure level and leak absence) must be satisfied simultaneously.
- Treating a missing mandatory test as a minor gap while marking the
  component as conditionally qualified — no partial qualification
  status exists; the component is unqualified until every mandatory
  test is complete.
- Applying the composite burst factor (2.25) to a metallic component
  or vice versa — the factors are material-specific and swapping them
  invalidates the structural margin verification.

## Behavior contract (gate 3)

The pressure-factor computation, mandatory test determination,
test-result evaluation, sequence completeness check, and qualification
report logic are exercised by the gate 3 contract test:
scripts/test_qualification_test_programme.py against
scripts/qualification_test_programme_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_qualification_test_programme.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
