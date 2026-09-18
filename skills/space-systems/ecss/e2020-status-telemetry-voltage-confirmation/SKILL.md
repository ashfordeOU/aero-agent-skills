---
name: e2020-status-telemetry-voltage-confirmation
description: "Assess whether a limiter's reported state confirms its output voltage, per ECSS-E-ST-20-20C clause 5.2.8.1.1. Use when a housekeeping bit has to mean the rail is inside its nominal band rather than that a command was accepted: build the band from the nominal and its tolerances, check the sense thresholds sit inside that band with workable hysteresis, derive the state the sense chain would report for the measured output, group the reported bit as on-confirmed, on-unconfirmed-under, on-unconfirmed-over, off-confirmed or off-contradicted, and reject a threshold placed under the band floor, which lets the bit read on over a collapsed rail. Trigger: ecss, e-st-20-20c, limiter-status-telemetry-bit, output-voltage-nominal-band, status-sense-threshold-placement, status-bit-hysteresis, false-on-confirmation, limiter-output-isolation-check."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-status-telemetry-voltage-confirmation, limiter-status-telemetry-bit, output-voltage-nominal-band, status-sense-threshold-placement, status-bit-hysteresis, false-on-confirmation, limiter-output-isolation-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Status Telemetry Voltage Confirmation (space-systems/ecss/e2020-status-telemetry-voltage-confirmation)

Use when the task is the status-telemetry meaning of ECSS-E-ST-20-20C
clause 5.2.8.1.1 -- showing that the on or off state a limiter puts in
the housekeeping stream is a statement about the output voltage itself,
and not merely about the command that was issued or the drive signal
inside the unit.

## Domain quick reference

- The clause fixes what the bit means. An on report asserts that the
  output is sitting inside its nominal band. A bit derived from the
  commanded state, from a drive signal or from a relay coil does not
  make that assertion, however faithfully it tracks the command.
- The band is the nominal output with its declared lower and upper
  tolerances. The tolerances need not be symmetric, and the floor is
  the edge that matters for an on report: it is the point below which a
  load is no longer being supplied what it was promised.
- The bit comes from a sense chain with two thresholds and hysteresis
  between them. Where those thresholds sit is the whole question. An on
  threshold below the band floor lets the chain assert on for an output
  that has already fallen out of tolerance -- a false confirmation, and
  the failure the clause exists to prevent. An on threshold above the
  ceiling is the opposite defect: a compliant output can never assert
  the bit at all.
- Hysteresis has a floor of its own. Thresholds placed too close
  together let bus ripple toggle the bit, which fills the housekeeping
  stream with transitions that no operator can act on.
- A reported state has five useful categories against a measured
  output: on-confirmed, on-unconfirmed-under, on-unconfirmed-over,
  off-confirmed and off-contradicted. Only the first and fourth are
  confirmations.
- on-unconfirmed-under is the dangerous one. An operator and an onboard
  procedure both read the bit and believe a load is powered; the load is
  not, and nothing else in the stream says so.
- off-confirmed is judged against a residual level rather than zero.
  Leakage and a discharging output filter keep a switched-off rail from
  reaching exactly zero volts, so the off case has a threshold too.

## Workflow

1. Build the nominal band from the declared output and its lower and
   upper tolerances, keeping them independent so an asymmetric band is
   not quietly symmetrised.
2. Check the sense thresholds: the on threshold inside the band, the
   off threshold below it, and the separation at or above the
   hysteresis floor. Reject an inverted or coincident pair outright --
   a chain with no hysteresis has no defined state at all.
3. Derive the state that chain would report for the measured output,
   carrying the previous state through the hysteresis window so a
   measurement between the thresholds resolves the way the hardware
   would resolve it.
4. Compare the derived state against the state the housekeeping stream
   actually carries. A disagreement says the reported bit is not coming
   from the output, which is the clause's failure by definition.
5. Group the reported state against the measured output into one of the
   five categories, and record the distance to the nearer band edge as
   the room the confirmation has.
6. Close with a confirms or does-not-confirm verdict that requires all
   three to hold at once: adequate thresholds, agreement between the
   derived and reported state, and a confirming category.

## Pitfalls

- Accepting a bit that echoes the command. It will agree with the
  output on every healthy unit and disagree on exactly the failures
  telemetry exists to reveal, so a command echo passes every test that
  does not include a fault case.
- Placing the on threshold at a convenient round value below the band.
  It makes the bit come up sooner during turn-on and it silently
  converts an out-of-tolerance rail into a confirmed one for the rest
  of the mission.
- Judging an off report against zero volts. A real rail decays through
  a filter and holds leakage, so an off report tested against zero
  never confirms and the check gets abandoned rather than fixed.
- Squeezing the hysteresis to make the bit responsive. Ripple then
  toggles it, and the transitions swamp the housekeeping budget while
  telling the ground nothing.
- Symmetrising the tolerance band because most rails are symmetric. The
  floor and the ceiling do different jobs, and an asymmetric band
  collapsed to one number moves whichever edge the design was actually
  relying on.
- Comparing a measurement against a band edge by bare arithmetic. The
  edges are products of a nominal and a tolerance fraction, so a
  measurement meant to sit exactly on an edge can land a few units in
  the last place outside it; the comparison absorbs that representation
  error while the band stays untouched.

## Behavior contract (gate 3)

The band construction, threshold placement checks, hysteretic state
derivation, report categorization, confirmation margin and the
confirms/does-not-confirm verdict are exercised by the gate 3 contract
test: scripts/test_e2020_status_telemetry_voltage_confirmation.py
against scripts/e2020_status_telemetry_voltage_confirmation_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_status_telemetry_voltage_confirmation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
