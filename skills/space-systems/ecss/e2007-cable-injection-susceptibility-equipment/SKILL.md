---
name: e2007-cable-injection-susceptibility-equipment
description: "Size the bench ECSS-E-ST-20-07C clause 5.4.8.2 calls for before a harness injection run is built: derive the forward power the amplifier owes from the target current, the loop impedance and the coupling loss, the probe current rating from that current and its headroom, the monitor transfer impedance from the receiver noise floor, and the pulse generator edge from the band ceiling; normalize the declared inventory, refuse an unknown or repeated item, compare each quantity as a floor or a ceiling, categorize it adequate, marginal or inadequate, and name the governing shortfall. Use when assembling or reviewing a cable injection susceptibility bench. Trigger: ecss, e-st-20-07c, cable-injection-susceptibility-equipment, injection-amplifier-forward-power, injection-probe-current-rating, current-monitor-transfer-impedance, injection-pulse-generator-edge, injection-bench-governing-shortfall."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-cable-injection-susceptibility-equipment, injection-amplifier-forward-power, injection-probe-current-rating, current-monitor-transfer-impedance, injection-pulse-generator-edge, injection-bench-governing-shortfall]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Cable Injection Susceptibility Equipment (space-systems/ecss/e2007-cable-injection-susceptibility-equipment)

Use when the task is the equipment list of ECSS-E-ST-20-07C clause 5.4.8.2
-- deciding whether the modulated source, the amplifier behind it, the
coupling probe, the monitoring probe, the pulse generator and the coupler
declared for a harness injection run can actually put the specified current
onto the bundle and measure what went on, before the bench is built rather
than after a run stalls halfway up the band.

## Domain quick reference

- Every requirement on this bench comes from four numbers about the
  injection: the current to be driven, the common-mode impedance of the
  loop it is driven into, the coupling loss of the probe, and the top of
  the band. The rest is arithmetic on those.
- Power follows the square of the current, so the amplifier is the item
  that surprises people. Doubling the specified current quadruples the
  power before any loss is counted, and the probe's coupling loss is then
  a multiplier on top of that, not a subtraction from it.
- The drive headroom is not padding. The probe is calibrated into a jig,
  the real harness is not the jig, and the amplifier has to be able to
  make up the difference at the frequency where the loop impedance is
  worst without being driven into compression.
- The injection probe is a transformer with a current rating and a usable
  band, and the rating is the peak it passes without the core saturating.
  A saturating probe does not clip gracefully; it turns a sine into
  harmonics and injects at frequencies nobody is grading.
- Whatever the amplifier did, only the monitor probe knows what actually
  flowed. Its transfer impedance converts the injected current into a
  voltage the receiver has to be able to read, so the sensitivity of the
  receiver sets a floor on the transfer impedance for the target current.
- The pulse generator is graded on its edge, not its amplitude. The edge
  decides how far up the band the transient carries spectrum, through the
  rise-time bandwidth product, and a slow edge quietly stops testing the
  top of the band while still producing a large pulse.
- The coupler earns its place only through its directivity. Forward power
  told from reflected power is what says whether the amplifier is driving
  the harness or a mismatch, and poor directivity mixes the two.
- Fitness is three-valued, not pass or fail. A capability comfortably past
  its requirement is adequate; one sitting on it is usable but carried as a
  limitation, because instrument figures are typical rather than
  guaranteed; one short of it is inadequate.
- When several items are short, the one that governs is the one short by
  the largest factor, not the first one listed. That is the item whose
  replacement changes the answer.

## Workflow

1. Validate the injection target: positive current, impedance, band edges
   and receiver sensitivity, a non-negative coupling loss, a headroom of at
   least unity and a modulation depth inside full scale.
2. Derive the forward power from the current, the loop impedance and the
   coupling loss with the drive headroom applied in the logarithmic domain.
3. Derive the probe current rating from the target current and its
   headroom, and the monitor transfer impedance floor from the receiver
   sensitivity and that same current.
4. Derive the pulse generator edge ceiling from the band ceiling through
   the rise-time bandwidth product, and its amplitude floor from the
   current in the loop.
5. Normalize the declared inventory, refusing an unrecognized item, a
   repeated declaration and a record that is not an item, and record every
   required item that is absent.
6. Compare each declared quantity against its requirement in the right
   sense -- a floor for power, rating, transfer impedance, depth,
   directivity and band ceiling, a ceiling for band floor, coupling loss
   and pulse edge -- and categorize it adequate, marginal or inadequate,
   refusing a declared quantity that is not positive.
7. Reduce the inadequate checks to the governing shortfall and aggregate
   findings and limitations. The bench is fit only when no finding stands.

## Pitfalls

- Sizing the amplifier on the current alone. The power goes as the square
  of it, and the probe's coupling loss multiplies the result again.
- Reading the amplifier's saturated output as its usable output. An
  injection run needs linear drive, and the last decibel before
  compression is where the harmonics appear.
- Choosing the injection probe on its band alone and never on its current
  rating, then injecting through a saturated core and grading harmonics
  the unit was never specified against.
- Assuming the monitor probe can see the target current because it can see
  a larger one. The transfer impedance times the target current has to
  clear the receiver's own noise floor.
- Grading the pulse generator on amplitude. A tall pulse with a slow edge
  carries no spectrum at the top of the band, so the transient part of the
  run silently stops short of where it was specified.
- Leaving the coupler out because the amplifier has a power meter. Without
  directivity, reflected power reads as delivered power and the bench
  reports drive it never coupled.
- Reporting the first inadequate item found as the problem, when another
  item is short by a far larger factor and is what actually has to change.
- Treating a capability that exactly equals its requirement as headroom.
  Instrument figures are typical, and the next unit off the shelf sits on
  the other side.

## Behavior contract (gate 3)

The target validation, forward-power, probe-rating, transfer-impedance and
pulse-edge derivation, inventory normalization with unknown and duplicate
refusal, floor and ceiling categorization into adequate, marginal and
inadequate, governing-shortfall reduction and the aggregate verdict are
exercised by the gate 3 contract test:
scripts/test_e2007_cable_injection_susceptibility_equipment.py against
scripts/e2007_cable_injection_susceptibility_equipment_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_cable_injection_susceptibility_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
