---
name: e20-electromagnetic-interference-safety-margins
description: "Use when determine the electromagnetic interference safety margins at the critical points of a spacecraft electrical design under ECSS-E-ST-20C clause 6.3.1.3: categorize each critical point as an ordnance firing circuit or as a safety-critical, mission-critical or non-critical function, read off the separation that category demands, normalise the demonstrated susceptibility threshold and the observed interference level onto one scale, compute the separation in decibels with the amplitude or power law the measured quantity requires, confirm every mandatory operating condition was exercised, and report the governing worst-case condition together with its margin. Trigger: ecss, e-st-20c-clause-6-3-1-3, interference-safety-margin, susceptibility-threshold, emi-critical-circuit, ordnance-firing-circuit-margin, worst-case-operating-condition, emc-margin-demonstration."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electromagnetic-interference-safety-margins, interference-safety-margin, susceptibility-threshold, emi-critical-circuit, ordnance-firing-circuit-margin, worst-case-operating-condition, emc-margin-demonstration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Interference Safety Margins (space-systems/ecss/e20-electromagnetic-interference-safety-margins)

Use when the task is the clause 6.3.1.3 interference safety margin
determination of ECSS-E-ST-20C -- naming the critical points of the
electrical design, showing how far each one sits below the level that
would upset it, and showing that the separation holds across the whole
declared range of operating conditions rather than at one convenient
measurement point.

## Domain quick reference

- A critical point is a place in the design where interference has a
  consequence, and the consequence sets the separation demanded. An
  ordnance point (an electro-explosive initiator, a firing line, a
  separation bolt drive, a safe-and-arm command line) demands the
  widest separation because the failure is energetic and irreversible.
  A safety-critical point (a propellant isolation valve drive, a
  pressurant latch valve drive, a cell bypass command, a release
  actuator) demands less, a mission-critical point (a thruster drive,
  a wheel torque command, an analogue star-tracker video line, a
  detector front end, a bus undervoltage sense) less again, and a
  non-critical point (housekeeping temperature sense, a status
  discrete, a non-critical heater line) only has to stay below the
  threshold at all. Each point is categorized exactly once, and an
  unrecognised point kind is rejected before it reaches the arithmetic.
- The margin is the separation between the susceptibility threshold
  demonstrated for that point and the interference level observed
  there. Both numbers have to reach the comparison on one scale. When
  they are already in decibels the margin is their difference,
  whatever the underlying quantity. When they are linear the law
  depends on the quantity: an amplitude quantity (voltage, current,
  field strength) uses twenty times the base-ten logarithm of the
  ratio, a power quantity uses ten times. Applying the amplitude law
  to a power measurement doubles the reported margin and is the most
  common way a non-compliant point is written up as compliant.
- The clause asks for the full range of operating conditions, so a set
  of conditions is mandatory before any margin is believable: every
  load energised, every load de-energised, the transmitter keyed, a
  mode transition in progress, and the bus at its worst-case voltage.
  A condition that was never exercised is a finding in its own right;
  it is not covered by a good margin under some other condition.
- The governing result is the worst case, not the mean and not the
  nominal condition. Reporting a point's margin means reporting the
  smallest margin found and naming the condition that produced it, so
  the reader can see which operating state the design is closest to
  losing.

## Workflow

1. Categorize each critical point from its kind; reject a kind that is
   not a clause 6.3.1.3 critical point before it enters the
   assessment.
2. Look up the separation the category demands: widest for ordnance,
   reduced for safety-critical, reduced again for mission-critical,
   and zero for non-critical points that only have to stay below the
   threshold.
3. For each operating-condition case at that point, put the
   susceptibility threshold and the interference level on one scale
   and compute the margin with the law the measured quantity
   requires -- difference for decibel inputs, twenty-log ratio for a
   linear amplitude quantity, ten-log ratio for a linear power
   quantity.
4. Flag every case whose margin falls short of the category
   requirement, absorbing representation error at the exact boundary
   so a case that is physically on the requirement is not written up
   as a failure.
5. Compare the conditions actually exercised against the mandatory
   set and flag each condition that was never run.
6. Select the worst case across the conditions and report it with the
   condition that governs it.
7. Aggregate the coverage and margin findings per point; the point is
   margin-compliant only when both lists are empty.

## Pitfalls

- Reporting one margin per point measured at the nominal operating
  condition -- clause 6.3.1.3 is about the range, and the transmitter
  keyed during a mode transition is routinely ten decibels worse than
  the quiet state the bench measurement was taken in.
- Using the amplitude law on a power measurement, which reports twice
  the true separation; a point six decibels short then reads as six
  decibels in hand.
- Treating a non-critical point's zero requirement as "no check" --
  the interference still has to sit below the threshold, and a
  negative margin there is a genuine finding even though nothing is
  demanded above the threshold.
- Letting a missing operating condition be absorbed by the margins
  that were measured; an unexercised condition has no margin at all,
  which is not the same as a margin that passed.
- Widening the requirement to make an exact-boundary case pass. A
  margin that is a few units in the last place below the requirement
  because of how the ratio was represented is on the requirement; the
  tolerance belongs in the comparison, never in the decibel figure the
  category demands.
- Averaging margins across conditions, or quoting the median, when the
  point is governed by its minimum.

## Behavior contract (gate 3)

The point categorization, required-separation, scale-normalisation,
amplitude and power decibel, operating-condition coverage, worst-case
selection and aggregated-review logic is exercised by the gate 3
contract test:
scripts/test_e20_electromagnetic_interference_safety_margins.py against
scripts/e20_electromagnetic_interference_safety_margins_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e20_electromagnetic_interference_safety_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
