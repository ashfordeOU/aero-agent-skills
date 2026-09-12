---
name: e20-signal-interface-compatibility
description: "Use when verify that the electrical characteristics of a spacecraft signal interface are compatible end to end under ECSS-E-ST-20C clause 4.1.2: categorize each interface as a bi-level discrete, an analog measurement, a serial data line or a pulse command, compute the loaded signal voltage from the source open-circuit level and the source/load impedance divider, evaluate the resulting high and low noise margins against the receiver switching thresholds, confirm the load-to-source impedance ratio suits the interface family, and verify the source can supply the drive current the loaded interface demands. Trigger: ecss, e-st-20-electrical-scope, signal-interface-compatibility, source-impedance, load-impedance, signal-noise-margin, receiver-switching-threshold, drive-current-capability, impedance-matching."
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
  tags: [ecss, e-st-20-electrical-scope, e20-signal-interface-compatibility, signal-interface, source-impedance, load-impedance, signal-noise-margin, impedance-matching]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical & Electronic — Signal Interface Compatibility (space-systems/ecss/e20-signal-interface-compatibility)

Use when the task is the electrical compatibility check of a signal
interface under ECSS-E-ST-20C clause 4.1.2 -- pairing a source with a
load, propagating the source and load impedances into the voltage
actually seen at the receiver, and confirming that levels, noise
margins and drive current all close at the interface boundary.

## Domain quick reference

- Clause 4.1.2 treats a signal interface as a contract between two
  units: the source declares its open-circuit output levels, its
  output impedance and the current it can drive; the load declares its
  input switching thresholds (or full-scale range) and its input
  impedance. Compatibility is a property of the pair, never of either
  unit alone, so a source qualified against one load says nothing
  about a second.
- Four interface families behave differently and are categorized
  before any number is computed. A bi-level discrete and a pulse
  command are level-driven and want a load impedance well above the
  source impedance so the divider loss stays small. An analog
  measurement is the strictest of the level-driven families, because
  divider loss appears directly as a gain error on the measurand. A
  serial data line is transmission-line driven and wants the opposite:
  a load impedance matched to the source characteristic impedance
  within a tolerance band, since both an under- and an over-terminated
  line reflect.
- The voltage at the receiver is the open-circuit source level scaled
  by the divider load/(source+load). The high-side noise margin is
  that loaded high level minus the receiver's minimum guaranteed high
  threshold; the low-side margin is the receiver's maximum guaranteed
  low threshold minus the driven low level. Either margin at or below
  zero is a hard incompatibility; a small positive margin is a finding
  against the required margin floor, not a pass.
- Loop current is the open-circuit level divided by the series sum of
  the two impedances. An interface whose levels and margins close can
  still fail because the source cannot sink or source that current.

## Workflow

1. Categorize the interface as bi-level discrete, analog measurement,
   serial data line or pulse command. Reject an interface whose family
   is unrecognized before any electrical number is computed.
2. Check the impedance relationship demanded by that family: a minimum
   load-to-source ratio for the level-driven families, or a matched
   termination inside a tolerance band for the serial data line.
3. Compute the loaded high level from the source open-circuit high and
   the source/load divider. The driven low level is taken at the
   source declaration, since a low is sunk rather than divided.
4. Compute the high-side and low-side noise margins against the
   receiver switching thresholds, and compare both against the margin
   floor required for the interface.
5. Compute the loop current at the loaded operating point and compare
   it against the source drive capability.
6. Aggregate the findings; the interface is compatible only when the
   family, impedance, margin and drive-current checks are all clear.
   Report each pair separately -- one incompatible pair does not
   condemn the source, and one compatible pair does not clear it.

## Pitfalls

- Comparing the source's open-circuit output level against the
  receiver threshold and declaring a margin. The divider has not been
  applied yet; with a high source impedance the loaded level can sit
  below the threshold the open-circuit level cleared comfortably.
- Applying the level-driven "load much greater than source" rule to a
  serial data line. On a transmission-line interface a very high load
  impedance is an open termination, which reflects as badly as a short
  one; the rule there is a matched impedance inside a band.
- Reading a positive noise margin as compliant. A margin has to clear
  a floor that covers the coupled noise and the drift the interface
  will see in flight; a margin of a few millivolts is a finding.
- Stopping once the levels close and never checking the loop current.
  A low load impedance can pull a current the source cannot deliver,
  which collapses the level that was just shown to be adequate.
- Carrying an analog measurement interface at the discrete impedance
  ratio. The divider loss that is a rounding error on a bi-level
  discrete is a systematic gain error on a measured quantity.

## Behavior contract (gate 3)

The family categorization, impedance-ratio, loaded-level, noise-margin
and drive-current logic is exercised by the gate 3 contract test:
`scripts/test_e20_signal_interface_compatibility.py` against
`scripts/e20_signal_interface_compatibility_logic.py` (stdlib
unittest, offline). Run:
python3 scripts/test_e20_signal_interface_compatibility.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
