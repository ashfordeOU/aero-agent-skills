---
name: e50-telemetry-in-the-blind
description: "Determine whether a spacecraft can transmit telemetry in the blind under ECSS-E-ST-50C clause 5.5.4: check the blind mode arms itself within the required time after the uplink is lost, that its carrier, modulation, coding and rate are a default the ground can acquire without first sending a command, and close the worst-case link budget at maximum range on the low-gain antenna to show the blind rate is actually receivable. Use when sizing a launch-and-early-orbit or safe-mode downlink, reviewing a no-uplink recovery path, or verifying an emergency beacon configuration. Trigger: ecss, e-st-50-communications-scope, telemetry-in-the-blind, uplink-loss-timeout-arming, default-blind-downlink-configuration, blind-mode-low-gain-link-margin, blind-downlink-station-acquisition, emergency-downlink-rate."
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
  tags: [ecss, e-st-50-communications-scope, e50-telemetry-in-the-blind, blind-telemetry-transmission, uplink-loss-timeout-arming, default-blind-downlink-configuration, blind-mode-low-gain-link-margin, blind-downlink-station-acquisition, emergency-downlink-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Telemetry in the Blind (space-systems/ecss/e50-telemetry-in-the-blind)

Use when the task is the telemetry-in-the-blind provision of ECSS-E-ST-50C
clause 5.5.4 — showing the spacecraft keeps transmitting telemetry that the
ground can acquire when no uplink has been received and no command can be
sent to make it do so.

## Domain quick reference

- Blind transmission exists for the states where commanding is not
  available: separation before first acquisition, a safe mode entered out
  of contact, a receiver or uplink chain failure. In every one of them the
  ground has no way to configure the downlink, so the configuration has to
  already be the one the ground is listening for.
- Arming is on a timeout, not on a diagnosis. The on-board logic counts
  the time since the last valid uplink event and enters the blind mode
  when that exceeds the configured timeout. A configured timeout longer
  than the required maximum means the spacecraft stays silent through a
  window the ground had planned to use.
- Ground acquirability is a property of the whole configuration, not of
  the carrier alone. Frequency, modulation scheme, symbol rate and coding
  each have to be in the set the receiving station can lock without being
  told; one parameter outside that set makes the signal present and
  unusable, which is the failure mode this clause exists to prevent.
- The link budget is the worst case, not the nominal one. Maximum range,
  the low-gain antenna pattern at the worst attitude, and no pointing
  gain: the received energy per bit has to clear the required threshold
  with the implementation loss included, which is what bounds the blind
  data rate from above.
- Rate and margin trade directly. Every doubling of the blind rate costs
  about three decibels of margin, so a blind mode that carries the full
  housekeeping rate is usually a mode whose margin closes only at short
  range — which is not the case it is needed in.

## Workflow

1. Validate the blind configuration: a positive carrier frequency, a
   positive symbol or bit rate, a named modulation and coding, and the
   configured uplink-loss timeout. Missing or non-positive entries are
   input errors.
2. Compare the configured timeout with the maximum the mission allows
   before blind telemetry has to be radiating, absorbing floating-point
   representation error at the boundary with a named tolerance.
3. Screen the configuration against the set the receiving station can
   acquire without an uplink: modulation, coding and rate each checked
   separately so the report names the offending parameter.
4. Confirm no element of the blind configuration is reached only through
   a telecommand; a parameter that needs commanding is unavailable in the
   state that triggers the mode.
5. Compute the worst-case free-space loss at maximum range, then close
   the budget: transmit effective isotropic radiated power, less losses,
   plus the station figure of merit, less the noise constant, less the
   rate term, less the required energy-per-bit threshold and the
   implementation loss.
6. Report the achieved margin, the rate the margin would support, and
   every finding: late arming, non-default parameter, command-dependent
   parameter, negative margin.

## Pitfalls

- Verifying the blind mode with the high-gain antenna pointed. That
  budget closes easily and proves nothing about the tumbling, unpointed
  case the mode is entered in.
- Treating an unlocked receiver as a valid uplink event. Carrier lock
  without a valid, authenticated frame is not evidence of a working
  uplink; resetting the timeout on lock alone can hold the spacecraft out
  of blind mode indefinitely.
- Leaving the blind rate at the nominal housekeeping rate. The rate term
  is ten times the base-ten logarithm of the bit rate, so keeping the
  nominal rate spends the entire worst-case margin.
- Assuming the station will search. Acquisition without an uplink means
  the station is listening at a pre-agreed frequency with a pre-agreed
  demodulator; a swept or non-default configuration can go unnoticed for
  a whole pass.
- Relaxing the required energy-per-bit threshold to make a marginal case
  close. The threshold belongs to the coding scheme and the required
  frame error rate; an equality at the limit is a representation
  question, handled by the tolerance inside the comparison.

## Behavior contract (gate 3)

The configuration validation, timeout comparison, default-configuration
screening, command-dependency screening, free-space-loss computation and
link-margin closure are exercised by the gate 3 contract test:
scripts/test_e50_telemetry_in_the_blind.py against
scripts/e50_telemetry_in_the_blind_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_telemetry_in_the_blind.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
