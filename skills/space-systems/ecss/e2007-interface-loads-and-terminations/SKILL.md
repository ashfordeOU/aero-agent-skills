---
name: e2007-interface-loads-and-terminations
description: "Verify that every interface of a tested unit is terminated in real hardware or a representative equivalent load before an ECSS-E-ST-20-07C clause 5.2.6.7 electromagnetic run: categorize each termination, compare equivalent-load impedance magnitude and phase against the hardware it stands in for, check that a simulated power load draws the flight load current and is rated above its dissipation, and hold the run while any interface is open or out of tolerance. Use when a bench substitutes load simulators, dummy loads or bus terminators for flight items. Trigger: ecss, e-st-20-electrical-scope, interface-termination-load, equivalent-load-impedance-match, flight-hardware-termination, open-interface-detection, power-interface-load-current, emc-bench-termination-gate."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-interface-loads-and-terminations, interface-termination-load, equivalent-load-impedance-match, flight-hardware-termination, open-interface-detection, power-interface-load-current]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Test Setup — Interface Loads and Terminations (space-systems/ecss/e2007-interface-loads-and-terminations)

Use when the task is the ECSS-E-ST-20-07C clause 5.2.6.7 obligation that the
interfaces of a tested unit be terminated during an electromagnetic
measurement -- in the real hardware they drive in flight, or in an equivalent
load that presents the same termination -- and the bench record has to be
reviewed before the first sweep.

## Domain quick reference

- An interface left open is not a simplification of the flight
  configuration, it is a different configuration. The open changes the
  current distribution on the harness, and the harness is the dominant
  radiator, so the measured emission belongs to a unit that will never fly.
- Every termination is categorized before the run: real hardware, equivalent
  load, or unterminated. A termination kind outside that set has no defined
  standing on the bench and is rejected rather than assumed benign.
- An equivalent load is equivalent only inside a declared tolerance, and the
  tolerance has two independent parts. The impedance magnitude is compared
  as a relative deviation from the hardware it replaces; the reactive
  character is compared as a phase deviation. A resistor that matches in
  magnitude but not in phase is a different termination at every frequency
  where the reactance matters.
- A power interface carries one obligation more than a signal interface. The
  simulated load must draw the flight load current within tolerance, because
  the conducted emission spectrum rides on that current, and the load bank
  must be rated above the power it dissipates by a stated margin, or it
  drifts thermally through the sweep and the measurement drifts with it.
- Impedance and phase deviations are unsigned. A load 10 % low is as wrong as
  a load 10 % high, and treating one as conservative hides the case where the
  stand-in loads the interface harder than flight ever will.
- A phase outside a quarter turn is a data error rather than a poor load; a
  passive termination does not present it, and accepting the value would put
  a transcription mistake into the configuration record.

## Workflow

1. Categorize every interface: map each declared termination kind to real
   hardware, equivalent load or unterminated. Reject an unrecognized kind, a
   duplicate interface name, or an empty interface list.
2. Raise a finding for each unterminated interface and stop checking it; an
   open interface has no impedance to compare.
3. For each equivalent load, compute the impedance deviation from the
   hardware it stands in for and compare it with the tolerance, then compare
   the phase deviation with its own tolerance.
4. For each power interface fed by an equivalent load, compare the simulated
   load current with the flight load current, then compute the dissipated
   power and the rating margin of the load bank.
5. Report the share of interfaces terminated in real hardware, and check it
   against any floor the test configuration declares.
6. Aggregate the findings and emit the gate token. Only an empty finding list
   releases the unit for measurement; anything else holds the terminations.

## Pitfalls

- Leaving a spare or unused connector open because nothing is connected to it
  in the test. The flight configuration terminates it, so the bench does too.
- Matching the impedance magnitude and declaring the load equivalent. Phase
  is a separate requirement, and a reactive flight load replaced by a pure
  resistor changes the conducted spectrum.
- Sizing the load bank to the dissipated power. The margin exists so the load
  does not drift as it heats, so the rating is compared against dissipation
  times the required factor, not against dissipation.
- Treating a simulated current below the flight value as conservative. It
  lowers the conducted emission and the unit passes on a current it will
  never draw in orbit.
- Checking the power interface and skipping the data-bus terminator. An
  unterminated bus reflects, and the reflection is a radiator.
- Letting a percentage that lands a few units in the last place outside a
  tolerance read as a non-conformance. The logic absorbs representation error
  with a named tolerance far below any engineering value; the tolerance
  itself is never widened.

## Behavior contract (gate 3)

The termination categorization, impedance and phase comparison, power-load
current and rating checks, real-hardware share and readiness-gate logic is
exercised by the gate 3 contract test:
`scripts/test_e2007_interface_loads_and_terminations.py` against
`scripts/e2007_interface_loads_and_terminations_logic.py` (stdlib unittest,
offline).
Run: python3 scripts/test_e2007_interface_loads_and_terminations.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
