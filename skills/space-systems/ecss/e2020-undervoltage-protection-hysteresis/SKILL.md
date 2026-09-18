---
name: e2020-undervoltage-protection-hysteresis
description: "Evaluate the hysteresis designed into an undervoltage protection trip against clause 5.2.5.2.1 of ECSS-E-ST-20-20C. Use when a power distribution unit declares an undervoltage drop-out threshold and a re-arm threshold and the band between them has to be judged. Derive the hysteresis band and its fraction of the trip point, build the disturbance envelope from bus ripple, sensing uncertainty and transient droop, and decide whether the band clears it. Treat the band as mandatory for a retriggerable limiter, whose auto re-arm chatters without one, and as recommended elsewhere, so a shortfall returns an advisory rather than a failure. Trigger: ecss, e-st-20-20c, undervoltage-trip-hysteresis-band, undervoltage-rearm-threshold, retriggerable-limiter-hysteresis-obligation, bus-ripple-chatter-margin, undervoltage-sensing-uncertainty, undervoltage-protection-chatter."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-undervoltage-protection-hysteresis, undervoltage-trip-hysteresis-band, undervoltage-rearm-threshold, retriggerable-limiter-hysteresis-obligation, bus-ripple-chatter-margin, undervoltage-sensing-uncertainty, undervoltage-protection-chatter]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Undervoltage Trip Hysteresis (space-systems/ecss/e2020-undervoltage-protection-hysteresis)

Use when the task is clause 5.2.5.2.1 of ECSS-E-ST-20-20C: the undervoltage
protection of a current limiter carries a hysteresis band between the
threshold it drops out on and the threshold it re-arms on. The band is
mandatory where the limiter re-triggers by itself and recommended for the
other limiter categories. This leaf grades a declared threshold pair against
the disturbance the bus actually presents.

## Domain quick reference

- The two thresholds are different quantities. The drop-out threshold is the
  bus voltage at which the protection removes the load; the re-arm threshold
  is the higher voltage the bus has to recover to before the protection will
  allow the output back. Their difference is the hysteresis band, and a design
  that quotes a single undervoltage number has a band of zero whether or not
  it says so.
- What the band has to clear is not noise in the abstract but a specific
  envelope: peak-to-peak ripple on the bus, the uncertainty of the sensing
  chain counted once at each comparator because either one can move toward the
  other, and the transient droop the bus shows on the largest load step the
  unit switches. A band smaller than that envelope lets one disturbance cross
  both thresholds.
- The obligation follows the limiter category, and that is the whole point of
  the clause. A retriggerable limiter re-arms on its own, so a crossed pair of
  thresholds becomes a self-sustaining trip-and-recover oscillation at the
  disturbance rate, which dissipates in the limiter and pulses the load; for
  that category the band is mandatory. A latching or high-power limiter stays
  down until it is commanded, so an absent band costs one unnecessary trip
  rather than a permanent oscillation, and the clause recommends rather than
  demands.
- Recommended is not optional-and-silent. A shortfall on a latching limiter is
  still a reportable finding; it is graded as an advisory so the project can
  accept it deliberately, not dropped so the design reads clean.
- Threshold placement is separate from band width and is wrong for every
  category. A drop-out point at or above the nominal bus trips a healthy bus;
  a re-arm point above the nominal bus can never be reached, so the limiter
  stays down for good once it has tripped.

## Workflow

1. Normalise the limiter category and read the obligation it carries;
   an unrecognised category is an input error, not a default to recommended.
2. Validate the two thresholds and the nominal bus. A re-arm threshold below
   the drop-out threshold is an input error; a re-arm threshold equal to it is
   a legitimate design with no hysteresis and is graded, not refused.
3. Derive the band and its fraction of the drop-out threshold, so a band can
   be compared across buses of different voltage.
4. Build the disturbance envelope from ripple, sensing uncertainty doubled
   across the two comparators, and transient droop; apply the design margin
   factor to get the band the design owes.
5. Compare band against requirement, absorbing an exact equality at the bound
   with a named tolerance rather than by widening the envelope.
6. Check threshold placement against the nominal bus independently of the
   band result.
7. Return the verdict — compliant, advisory or non-compliant — with the band,
   envelope, chatter margin and every finding behind it.

## Pitfalls

- Reading a single quoted undervoltage number as if the band were implied.
  The absence of a second threshold is a zero band and has to be graded as
  one, on a retriggerable limiter especially.
- Sizing the band on ripple alone. Sensing uncertainty enters twice and the
  load-step droop is frequently the largest of the three; a band that clears
  only the ripple still chatters on the first big load step.
- Counting the sensing uncertainty once. The drop-out comparator can sit high
  by its tolerance while the re-arm comparator sits low by its own, so the
  effective band shrinks by twice the uncertainty, not once.
- Treating recommended as nothing to report. The clause distinguishes the
  categories by consequence, not by whether the finding exists; a latching
  limiter with no band still owes the project a deliberate acceptance.
- Relaxing the envelope so a design that lands exactly on the bound reads as a
  pass. An equality at the limit is a representation question handled by the
  tolerance inside the comparison; the envelope stays as computed.
- Grading a re-arm point above the nominal bus as merely generous hysteresis.
  It is an unreachable threshold, and no band width redeems it.

## Behavior contract (gate 3)

The category obligation mapping, threshold validation, band and fraction
derivation, disturbance envelope, margin-factor requirement, bound-equality
handling, threshold placement checks and the verdict ladder are exercised by
the gate 3 contract test:
scripts/test_e2020_undervoltage_protection_hysteresis.py against
scripts/e2020_undervoltage_protection_hysteresis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_undervoltage_protection_hysteresis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
