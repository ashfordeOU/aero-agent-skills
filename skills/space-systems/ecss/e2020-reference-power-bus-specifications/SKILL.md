---
name: e2020-reference-power-bus-specifications
description: "Determine whether a protection device operates correctly across the reference power bus of ECSS-E-ST-20-20C clause 5.1. Use when a latching current limiter has to be shown compatible with the bus it will sit on: refuse a specification whose transient envelope is narrower than its steady band, build the worst-case high and low instantaneous voltages from the steady limits, the ripple and the transient excursions, compare every device operating window against them, check the transient duration each device tolerates, and report the limiting margin per device. Trigger: ecss, e-st-20-20c-clause-5-1, reference-power-bus-voltage-range, power-bus-ripple-envelope, power-bus-transient-excursion, protection-device-operating-window, worst-case-instantaneous-bus-voltage, transient-duration-tolerance."
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
  tags: [ecss, e-st-20-20-power-protection-device-scope, e2020-reference-power-bus-specifications, reference-power-bus-voltage-range, power-bus-ripple-envelope, power-bus-transient-excursion, protection-device-operating-window, worst-case-instantaneous-bus-voltage, transient-duration-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Protection Devices -- Reference Power Bus Specifications (space-systems/ecss/e2020-reference-power-bus-specifications)

Use when the task is the clause 5.1 bus envelope of ECSS-E-ST-20-20C:
the reference power bus has been specified as a nominal voltage, a
steady range, the ripple riding on it and the transient excursions it
may make, and a protection device has to be shown to go on working
correctly everywhere in that picture.

## Domain quick reference

- The reference bus is three things at once and only reads as one
  envelope when all three are combined: where the bus sits in steady
  state, the ripple superimposed on that, and the excursions it may make
  and return from. A device is compatible with the combination, not with
  the nominal voltage.
- The deciding quantity is the worst-case instantaneous voltage, and it
  is built rather than read. Upward: the steady upper limit plus half
  the ripple, against the upper transient bound, whichever is higher.
  Downward: the steady lower limit minus half the ripple, against the
  lower transient bound, whichever is lower.
- Which of the two terms wins is not fixed. On a bus with a wide
  transient allowance the transient sets both extremes; on a tightly
  clamped bus with heavy ripple the ripple does, and a device sized on
  the assumption that transients always dominate is sized against the
  wrong number.
- Duration is an independent axis. A device that tolerates the transient
  amplitude but not for as long as the bus may hold it is incompatible,
  and no amount of voltage headroom compensates: the two are different
  failure mechanisms and are reported separately.
- The band just outside the steady limits is exactly where a latching
  current limiter misbehaves -- nuisance trips on the upper excursion,
  failure to reset or to hold on the lower one -- so understating the
  excursion by half a ripple is not a rounding matter.
- A specification is checked before it is used. An upper transient bound
  below the steady upper limit, or a lower transient bound above the
  steady lower limit, describes no bus: the steady limits are reached in
  normal operation, so that shape is a transcription defect.
- A bound is inclusive. A device whose operating bound lands exactly on
  the worst-case instantaneous voltage is compatible, and the comparison
  tolerance absorbs representation error rather than widening the
  device.

## Workflow

1. Validate the marginal-band policy first: the voltage band and
   duration band inside which a compatible device is still called out. A
   non-positive band is refused rather than read as "no advisories".
2. Read the bus specification. An absent specification, or one whose
   reference is blank, closes the assessment on reference bus
   specification not established.
3. Check the specification for sense: a steady band that actually
   spans, a nominal voltage sitting inside it, non-negative ripple, a
   transient envelope no narrower than the steady band on either side,
   and a positive transient duration.
4. Build the worst-case instantaneous voltages: the higher of the
   steady upper limit plus half the ripple and the upper transient
   bound, and the lower of the steady lower limit minus half the ripple
   and the lower transient bound.
5. Validate every device window: a non-blank identifier, no duplicate
   identifier, an operating range that actually spans, and a positive
   tolerated transient duration.
6. Judge each device on all three counts -- upper bound, lower bound,
   transient duration -- admitting a tie on each, and record all three
   margins plus the smaller of the two voltage margins as the limiting
   one. Name every shortfall, not the first found.
7. Report the weakest device and its limiting voltage margin beside the
   verdict, and raise a marginal advisory for each compatible device
   inside the policy bands. Advisories do not move the verdict.
8. Close on one verdict: reference bus specification not established,
   device outside reference bus envelope, or devices cover reference
   bus.

## Pitfalls

- Sizing the device at the nominal voltage. The nominal is where the
  bus spends its time, not where it stresses the device, and a window
  sized on it clears none of the conditions that matter.
- Comparing against the steady limits and stopping there. That
  understates the excursion by half the ripple at least and by the whole
  transient allowance at worst, in exactly the band where a limiter
  nuisance-trips.
- Assuming the transient always dominates. On a tightly clamped bus with
  heavy ripple the ripple term is the higher one, so both terms are
  formed and the larger kept rather than one assumed.
- Adding ripple peak-to-peak instead of half of it. The steady limit is
  the centre the ripple rides on, so the excursion above it is half the
  peak-to-peak figure, and doubling it invents margin pressure that is
  not there.
- Letting voltage headroom excuse a duration shortfall. Amplitude and
  duration are separate failure mechanisms, and a device that cannot
  hold through the transient is incompatible however wide its window.
- Reporting compatible with no margin and no weakest device. The verdict
  alone hides the difference between a device with volts to spare and
  one holding on a tenth of a volt, and the next bus re-baseline has
  nothing to compare against.

## Behavior contract (gate 3)

The marginal-band policy validation, the specification sense checks
including the narrow transient envelope, the construction of the
worst-case instantaneous voltages from steady limits, ripple and
transients, the device window validation, the three-count judgement with
an admissible tie, the margins and the limiting voltage margin, the
weakest device, the marginal advisories and the compatibility verdict
are exercised by the gate 3 contract test:
scripts/test_e2020_reference_power_bus_specifications.py against
scripts/e2020_reference_power_bus_specifications_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_reference_power_bus_specifications.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
