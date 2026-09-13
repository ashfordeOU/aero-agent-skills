---
name: e20-gas-discharge-general-requirements
description: "Use when verify that a radio-frequency chain stays free of corona and gas discharge at its maximum-operating-power across the whole declared environment envelope under ECSS-E-ST-20C clause 7.3.3.1: build the peak-envelope-power the item really carries from its carrier set, mismatch uplift and tolerance stack, categorize every mission phase into its ambient-pressure regime, locate the worst-case pressure inside each declared band instead of assuming an edge, scale the measured discharge-onset-power to that pressure and gap, express the headroom as a discharge-margin, and flag an envelope that leaves a required phase unexercised. Trigger: ecss, e-st-20-electrical-scope, gas-discharge-general-requirements, gas-discharge-freedom, maximum-operating-power-envelope, peak-envelope-power, discharge-onset-power, worst-case-pressure-band, environment-envelope-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e20-gas-discharge-general-requirements, gas-discharge-freedom, maximum-operating-power-envelope, peak-envelope-power, discharge-onset-power, worst-case-pressure-band, environment-envelope-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Gas Discharge General Requirements (space-systems/ecss/e20-gas-discharge-general-requirements)

Use when the task is the clause 7.3.3.1 general requirement of
ECSS-E-ST-20C -- showing that a radio-frequency chain carries its
maximum operating power without corona or gas discharge anywhere in
the declared environment, and not merely at the two convenient points
of sea-level ambient and hard vacuum.

## Domain quick reference

- The stressing quantity is not the nominal single-carrier rating. It
  is the peak envelope the item sees when its carriers align in phase
  at the worst instant, raised by the standing-wave uplift of the
  mismatch it actually presents and by the tolerance stack of the
  chain ahead of it. Carrier amplitudes add, so two equal carriers
  present four times the single-carrier power at that instant, not
  twice.
- Gas breakdown across a gap obeys a similarity law in the product of
  pressure and gap length. The breakdown voltage falls as that product
  rises from near zero, passes a minimum, then rises again as the gas
  becomes dense. Below the minimum the mean free path is long enough
  that too few ionising collisions occur to build an avalanche, and
  the gap has no finite breakdown voltage at all.
- The consequence for a declared pressure band is the point of this
  clause: the worst case inside a band is the pressure nearest the
  minimum of that curve, which is an interior point whenever the band
  straddles it. Evaluating only the band edges -- the habit that
  ascent-profile tables invite -- can miss the weakest condition by
  orders of magnitude in onset power.
- Onset power scales with the square of the breakdown voltage, so one
  measured onset point transports to any other pressure and gap by the
  square of the voltage ratio. A measured point taken on the
  long-mean-free-path branch cannot anchor such a scaling, because it
  has no finite voltage to form a ratio with.
- The environment envelope is a set of mission phases, each carrying a
  pressure band: ground ambient and pre-launch purge in the dense-gas
  regime, ascent venting, early-orbit outgassing and thin planetary
  atmosphere in the transitional regime, on-station and cruise in
  vacuum. A phase with no declared band is a gap in the envelope, and
  the transitional phases are the ones that cross the weak point.
- A radio-frequency chain is free of gas discharge only when the
  headroom between onset power and applied power holds the required
  decibel margin in every declared phase.

## Workflow

1. Build the applied power: sum the carrier amplitudes, square the
   sum, apply the standing-wave uplift of the declared mismatch, then
   the tolerance stack in decibels. Reject an empty carrier set, a
   non-positive carrier, a mismatch below unity or a negative
   tolerance.
2. Categorize every declared mission phase into its ambient regime and
   reject an unrecognized phase before it enters the assessment.
3. For each phase, find the worst-case pressure inside its band: the
   pressure that puts the pressure-gap product at the minimum of the
   breakdown curve when the band contains it, the nearer edge
   otherwise.
4. Scale the item's measured onset power to that worst-case pressure
   and to the flight gap by the square of the breakdown-voltage ratio.
   A phase whose worst case sits on the long-mean-free-path branch is
   discharge-free by construction.
5. Express the headroom as ten times the base-ten logarithm of the
   onset-to-applied power ratio and compare it against the required
   margin, absorbing representation error at an exact equality rather
   than widening the requirement.
6. Check envelope coverage separately: list the required phases with
   no declared band, and reject a phase declared twice.
7. The item is compliant only when no phase carries a margin shortfall
   and no required phase is missing from the envelope.

## Pitfalls

- Taking the nominal carrier rating as the applied power. Coherent
  carrier addition and mismatch uplift together can double the power
  the gap sees before any tolerance is applied.
- Evaluating an ascent band at its two edges. The weakest pressure is
  usually inside the band, and both edges can pass comfortably while
  the interior fails by a wide margin.
- Widening a gap to recover margin. The law is in the product, so a
  wider gap moves the weak point to a lower pressure -- straight onto
  the early-orbit outgassing band in many cases.
- Reading "no finding" on a short envelope as compliance. An envelope
  that never declares a transitional phase has not been exercised
  where the hardware is weakest; the missing phase is the finding.
- Anchoring the onset scaling on a vacuum measurement. On that branch
  there is no finite breakdown voltage, so there is no ratio to scale
  with and the transported number is meaningless.
- Treating a margin of exactly zero decibels as a pass. At zero the
  onset power equals the applied power and the chain sits on its
  threshold with nothing in hand.

## Behavior contract (gate 3)

The applied-power build-up, phase categorization, similarity-curve,
worst-case-pressure, onset-scaling, margin and envelope-coverage logic
is exercised by the gate 3 contract test:
scripts/test_e20_gas_discharge_general_requirements.py against
scripts/e20_gas_discharge_general_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_gas_discharge_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
