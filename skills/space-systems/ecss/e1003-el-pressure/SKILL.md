---
name: e1003-el-pressure
description: "Use when run element-level pressure tests for pressurized space hardware under ECSS-E-ST-10C §6.5.3: determine proof pressure from the maximum expected operating pressure and verify the hold duration, cycle pressure between bounds for the required number of fatigue cycles, apply design burst pressure to confirm ultimate structural integrity, and measure leakage against the allowable leak rate. Each test produces a pass/fail verdict with explicit findings. Trigger: ecss, e-st-10-system-scope, pressure-test, proof-pressure, burst-pressure, pressure-cycling, leak-test, meop."
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
  tags: [ecss, e-st-10-system-scope, pressure-test, proof-pressure, burst-pressure, pressure-cycling, leak-test, meop]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Element Pressure Tests — Proof, Cycling, Burst, Leak (space-systems/ecss/e1003-el-pressure)

Use when the task is running the element-level pressure test sequence required
by ECSS-E-ST-10C §6.5.3 -- proof, pressure cycling, design burst, and leak --
for a pressurized hardware item, verifying that each test result meets its
acceptance criterion before the element advances to integration.

## Domain quick reference

- **Proof test**: Apply a proof pressure derived from the maximum expected
  operating pressure (MEOP) multiplied by a proof factor (default 1.5×) and
  hold it for the required duration. The item must sustain the proof pressure
  without permanent deformation or detectable leakage.
- **Pressure cycling test**: Cycle the internal pressure between a lower bound
  and an upper bound for at least the required number of cycles, simulating
  the fatigue loads accumulated over the operational life. The item must remain
  leak-free and dimensionally stable after the full cycle count.
- **Design burst test**: Apply the design burst pressure (MEOP × burst factor,
  default 2.0×) to verify that the item retains structural integrity up to its
  ultimate pressure limit. The item must not rupture at or below the design
  burst pressure; rupture above it confirms the margin is genuine.
- **Leak test**: Measure the leak rate and compare it against the allowable
  leak rate for the application (e.g. Pa·m³/s). The measured rate must not
  exceed the allowable; a margin is computed as allowable minus measured.
- Each test type returns a `passed` flag and a `findings` list; an empty
  findings list means the criterion is met. The full sequence is summarised by
  an `overall_passed` flag.

## Workflow

1. Confirm the MEOP of the element and select the proof factor and burst
   factor from the applicable requirements document. Verify the allowable
   leak rate is on record before starting.
2. **Proof test**: compute the required proof pressure (`MEOP × proof_factor`)
   and verify that the test facility can reach and hold it. Apply the proof
   pressure and maintain it for at least the required hold duration. Record
   whether deformation or leakage was observed; either observation is a
   finding.
3. **Pressure cycling test**: set the cycling bounds (min pressure ≥ 0,
   max pressure > min) and the required cycle count. Run the cycles and
   record any leakage or deformation observed during or after. Confirm that
   the completed cycle count meets or exceeds the requirement.
4. **Design burst test**: compute the required burst pressure (`MEOP × burst_factor`).
   Apply pressure up to the design burst pressure and record whether rupture
   occurred. A result is a finding if the applied pressure was below the
   required burst pressure or if the item ruptured.
5. **Leak test**: with the element pressurized, measure the leak rate using
   the agreed test method. Compare against the allowable rate. Record the
   margin; a negative margin is a finding.
6. Aggregate all findings across the four tests. Issue the element for
   integration only when every findings list is empty and `overall_passed`
   is true.

## Pitfalls

- Applying the proof pressure and immediately releasing it without holding it
  for the required duration -- a short hold does not adequately stress
  manufacturing defects into detectable leakage or deformation and the test
  criterion is not met.
- Treating a design burst test where the applied pressure was below the design
  burst pressure as a pass because the item did not rupture -- the test is
  only valid when the required pressure was actually reached; an under-pressure
  run is inconclusive, not a pass.
- Running a leak test at ambient pressure rather than at the operational
  pressure -- leakage at zero differential is always zero and gives no
  information about the in-service condition.
- Omitting the pressure cycling test on the grounds that the proof test was
  already run -- cycling accumulates fatigue in a way a single proof hold
  cannot reveal; the two tests are not substitutes for each other.
- Setting the allowable leak rate to zero or leaving it unset and then
  reading "no violation found" as compliance -- an unset allowable means the
  system-level leakage budget was never allocated to this element, which is
  itself a finding.

## Behavior contract (gate 3)

The proof, cycling, burst, and leak evaluation logic is exercised by the
gate 3 contract test: scripts/test_e1003_el_pressure.py against
scripts/e1003_el_pressure_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_e1003_el_pressure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
