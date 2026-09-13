---
name: e2008-power-measurement-process
description: "Verify that a string-level electrical performance measurement on a photovoltaic assembly was taken where ECSS-E-ST-20-08C clause 5.5.3.4.2 puts it: at the interface connector and referred to a declared reference temperature. Confirm the probing plane keeps the harness the string delivers through inside the loop, quantify the power a shorter plane overstates, refer the measured open-circuit voltage, short-circuit current and maximum power to the reference with the declared coefficients, and reject a correction reaching too far from it to be credible. Use when reviewing a solar-array string current-voltage measurement record. Trigger: ecss, e-st-20-08c, clause-5-5-3-4-2, solar-array-string-iv-measurement, interface-connector-measurement-plane, string-reference-temperature-correction, harness-voltage-drop-allocation, string-maximum-power-referral."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-power-measurement-process, solar-array-string-iv-measurement, interface-connector-measurement-plane, string-reference-temperature-correction, harness-voltage-drop-allocation, string-maximum-power-referral]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Power Measurement Process (space-systems/ecss/e2008-power-measurement-process)

Use when the task is the clause 5.5.3.4.2 measurement process of
ECSS-E-ST-20-08C -- judging whether a string-level electrical
performance measurement was taken the way the clause requires: at the
interface connector the assembly actually delivers through, swept by
instrumentation that brackets the string's own curve, and referred to a
declared reference temperature by a correction that stays inside the
window its coefficients were fitted in.

## Domain quick reference

- The interface connector is the plane the rest of the spacecraft sees.
  Power measured anywhere upstream of it is power the string generates,
  not power it delivers, and the difference is the resistive loss of
  everything in between.
- Which plane was probed decides which segments sit outside the
  measurement loop. A bus-bar probe leaves the connector harness out; a
  cell-level probe leaves the string interconnect out as well. Each
  omitted segment takes a share of the delivered power that the record
  then never charges to the string.
- The uncharged loss goes as the square of the working current, so it
  grows far faster than the voltage drop the same segment shows. A
  harness that looks negligible on a voltmeter can still be a
  significant fraction of the delivered power on a high-current string.
- A measurement carries the temperature it was taken at. Open-circuit
  voltage falls as the article warms, short-circuit current rises
  slightly, and maximum power falls, so three different coefficients
  refer three different quantities back to the same reference point.
- Correcting is not extrapolating. The coefficients are linear fits
  valid near the reference; a measurement far enough away is corrected
  by a term large enough that the fit itself dominates the uncertainty,
  and that is a finding rather than a number to publish.
- A sweep that does not reach past the open-circuit voltage and the
  short-circuit current never brackets the maximum-power knee, and one
  with too few points cannot locate it. Both leave the reported maximum
  power unsupported whatever plane it was measured at.

## Workflow

1. Validate the policy and the string definition: reference temperature,
   extrapolation limit, sweep density, cell and string counts, and the
   identifier of the connector the string delivers through. A string
   with no named interface connector cannot be measured at one.
2. Validate the declared measurement plane against the recognised set,
   rejecting an unrecognised one rather than treating it as the
   connector.
3. Refer the measured open-circuit voltage, short-circuit current and
   maximum power to the reference temperature with their own declared
   coefficients, and refuse a correction that drives the power
   non-physical.
4. Resolve the series resistance the plane left outside the loop from
   the declared harness segments, and require a resistance for every
   segment the plane omits rather than silently treating it as zero.
5. Charge that resistance at the corrected working current to get the
   power the record overstates and the voltage drop it hides, then
   subtract it to give the power actually available at the connector.
6. Check the sweep spans both ends of the string curve and carries
   enough points, and check the correction span against the
   extrapolation limit. A span landing exactly on the limit is credible;
   the comparison tolerance absorbs representation error.
7. Close on one verdict in order of precedence: instrumentation
   inadequate, plane short of the interface connector, extrapolation
   excessive, or measured at the interface connector -- with every
   finding reported, not only the one that set the verdict.

## Pitfalls

- Publishing the measured maximum power as the string's performance. It
  is the performance of the article at the laboratory temperature at the
  plane the probe happened to sit on, and neither of those is what the
  clause asks to be reported.
- Treating an undeclared harness segment as zero resistance. It makes a
  cell-level probe look identical to a connector measurement, which is
  precisely the error the plane check exists to catch.
- Judging a harness by its voltage drop. The drop is linear in current
  and the loss is quadratic, so a segment that drops a tolerable
  fraction of a volt can still remove a real share of the power.
- Correcting a badly off-reference measurement and reporting the result
  without the span. A large correction is not wrong by itself, but it
  carries an uncertainty the corrected number no longer shows.
- Accepting a maximum power from a sweep that stopped short of
  open circuit. The knee was never bracketed, so the reported maximum is
  the largest point the sweep happened to reach.

## Behavior contract (gate 3)

The policy and string validation, plane resolution and unmeasured
resistance, harness loss and drop, the three temperature corrections,
extrapolation span, sweep span and density checks, and the ordered
process verdict are exercised by the gate 3 contract test:
scripts/test_e2008_power_measurement_process.py against
scripts/e2008_power_measurement_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_power_measurement_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
