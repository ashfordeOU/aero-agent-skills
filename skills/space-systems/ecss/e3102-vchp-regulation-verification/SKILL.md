---
name: e3102-vchp-regulation-verification
description: "Verify a variable conductance heat pipe against its transport, heat-leak, reservoir and temperature-regulation requirements under ECSS-E-ST-31-02C clause 5.5.5.2b. Use when the task is confirming maximum transport at the design temperature, bounding the heat a fully blocked condenser still passes in off mode, deriving the reservoir thermal resistance from a measured rise, grading the evaporator temperature swing across the recorded power and sink range against the control band, and sizing the reservoir heater an actively controlled unit demands at its coldest sink. Trigger: ecss, e-st-31-02c, vchp-maximum-transport, off-mode-heat-leak, reservoir-thermal-resistance, evaporator-regulation-band, active-reservoir-heater, condenser-blockage-fraction."
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
  tags: [ecss, e-st-31-02-two-phase-scope, e3102-vchp-regulation-verification, vchp-maximum-transport, off-mode-heat-leak, reservoir-thermal-resistance, evaporator-regulation-band, condenser-blockage-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — VCHP Regulation Verification (space-systems/ecss/e3102-vchp-regulation-verification)

Use when the task is the variable conductance heat pipe verification of
ECSS-E-ST-31-02C clause 5.5.5.2b -- the four things a gas-controlled pipe
owes beyond a plain heat pipe: how much it transports, how little it
leaks when it is supposed to be off, how tightly its reservoir is held,
and how well it actually regulates the evaporator.

## Domain quick reference

- A variable conductance pipe works by parking a non-condensable gas
  charge at the condenser end. As the load falls or the sink cools, the
  gas front advances and shuts off condenser area, so the evaporator
  temperature barely moves while the heat rejected does. Everything in
  the verification follows from that mechanism.
- Maximum transport is still a capillary-limit question and is read off
  a temperature curve exactly as for a fixed-conductance pipe. The gas
  charge does not add capability; it only removes condenser area.
- Off mode is not zero. With the front pushed over the whole condenser
  the vapour path is shut, but axial conduction through the envelope and
  the wick still carries heat, and that residue is a conductance times a
  temperature difference. A requirement that assumes a blocked pipe
  passes nothing will be violated by physics, not by workmanship.
- The reservoir has to be tied tightly to whatever sets its temperature.
  Reservoir thermal resistance is a measured rise divided by the
  parasitic heat that produced it, and a high resistance means the
  reservoir drifts, the gas pressure drifts with it, and the front sits
  somewhere other than where the control law wants it. That is a
  regulation failure that a transport test will never show.
- Regulation is graded as a swing, not as an absolute temperature. The
  evaporator temperature is recorded across the full power and sink
  matrix, and what matters is the spread between the coldest and hottest
  points and which two points produced it.
- Passive and active units are graded differently. A passive unit has to
  hold the band with no heater power at all. An active unit may hold its
  reservoir at a setpoint, but the heater demand at the coldest sink --
  reservoir conductance times the lift from sink to setpoint -- has to
  fit inside the power budget, and at a sink above the setpoint it needs
  nothing.
- Reservoir size sets how far the front can travel. The condenser
  fraction the front must block at the lowest power is roughly the power
  turndown, and a reservoir sized for less than that cannot reach the
  low end of the range.

## Workflow

1. Validate the transport curve and read the capability at the design
   temperature, refusing a temperature outside the tabulated span.
2. Grade the capability against the required transport as a ratio, with
   an exact unity treated as compliant.
3. Compute the off-mode heat leak from the axial conductance and the
   end-to-end temperature difference, and grade it against the allowance.
   Where the conductance is not given directly, derive it from the
   conductivity, the conducting cross-section and the length.
4. Derive the reservoir thermal resistance from the measured rise and
   the parasitic heat, and grade it against the specified maximum.
5. Reduce the recorded operating points to an evaporator swing, and
   report the coldest and hottest points by name alongside the verdict
   so the governing corner of the matrix is visible.
6. For an active unit, take the coldest sink in the recorded matrix,
   size the reservoir heater demand, and grade it against the available
   power; refuse an active unit whose heater data is absent rather than
   grading it as passive.
7. Where a full-power reference and a reservoir sizing limit are given,
   convert the lowest recorded power into a condenser blockage fraction
   and grade the reservoir sizing against it.
8. Aggregate every shortfall into one finding list and declare the unit
   compliant only when that list is empty.

## Pitfalls

- Verifying transport and calling the pipe qualified. Transport is the
  one requirement a variable conductance pipe shares with a plain one;
  the heat leak, the reservoir and the regulation band are what make it
  a control device.
- Specifying zero off-mode heat leak. Axial conduction does not switch
  off with the vapour path, and the allowance has to be a number the
  conduction path can actually meet.
- Reading a reservoir resistance measurement as a thermal-design detail.
  It is a regulation requirement: a loosely coupled reservoir moves the
  gas front, and the evaporator follows it.
- Grading regulation on a single operating point. A swing needs at least
  two, and the pair that produces the worst spread is usually the
  min-power cold-sink corner against the max-power hot-sink corner.
- Letting an active unit be graded as passive because its heater data is
  missing. That reads as a pass with no heater demand, when the real
  answer is that the evidence is absent.
- Sizing the reservoir for the nominal power only. The front has to
  reach far enough to cover the lowest power in the range, and the
  turndown is what sets that.

## Behavior contract (gate 3)

The curve validation and refusal to extrapolate, the transport ratio, the
axial conductance and off-mode leak grading, the reservoir resistance
derivation, the evaporator swing with its governing point pair, the
passive and active mode split with reservoir heater sizing, and the
condenser blockage fraction are exercised by the gate 3 contract test:
scripts/test_e3102_vchp_regulation_verification.py against
scripts/e3102_vchp_regulation_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3102_vchp_regulation_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
