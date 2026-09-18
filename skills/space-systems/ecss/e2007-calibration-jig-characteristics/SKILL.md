---
name: e2007-calibration-jig-characteristics
description: "Validate the coaxial calibration fixture of ECSS-E-ST-20-07C clause 5.2.8.3. Use when a current probe is calibrated against a known current flowing on a transmission-line conductor: derive the fixture characteristic-impedance from its bore, its conductor and the dielectric between them, hold that impedance to the nominal reference within a fractional allowance, report the residual mismatch as a standing-wave ratio, hold radial clearance, insertion loss and enclosure screening against their limits, confirm the usable span covers the calibration span, then convert applied power into injected current and probe output into a decibel-ohm transfer impedance. Trigger: ecss, e-st-20-07c, calibration-jig-characteristics, coaxial-calibration-fixture, current-probe-transfer-impedance, fixture-characteristic-impedance, injected-calibration-current, jig-insertion-loss, jig-standing-wave-ratio."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-calibration-jig-characteristics, coaxial-calibration-fixture, current-probe-transfer-impedance, fixture-characteristic-impedance, injected-calibration-current, jig-standing-wave-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Calibration Jig Characteristics (space-systems/ecss/e2007-calibration-jig-characteristics)

Use when the task is the calibration-fixture rule of ECSS-E-ST-20-07C
clause 5.2.8.3 -- the coaxial jig a current probe is calibrated in
before it is trusted to read the current flowing on the conductor of a
transmission line, and the characteristics that jig has to hold for the
reading it produces to mean anything.

## Domain quick reference

- The fixture is a short coaxial line, not a clamp. The conductor under
  measurement becomes the inner conductor; the fixture bore is the
  outer. The probe encircles the conductor through an aperture in that
  bore. Because it is a line, it has a characteristic impedance set by
  the ratio of the two diameters and by the dielectric in the annulus,
  and that impedance is a geometric consequence, not a nameplate value.
- The fixture is inserted between a generator and a measuring receiver
  that both present the same reference impedance. Its own impedance is
  therefore held to that reference within a fractional allowance, and
  the residual mismatch is reported as a standing-wave ratio, which is
  the quantity the swept calibration actually degrades.
- The two limits are not the same limit. An impedance deviation is a
  one-sided distance from the reference; the standing-wave ratio is the
  larger of the two impedances over the smaller, so it is symmetric in
  the ratio and blind to which side the deviation falls on. A fixture
  can sit outside the impedance allowance while its ratio still passes,
  which is a finding on the geometry and not a pass on the mismatch.
- Geometry carries a second, independent duty: the conductor and its
  insulation have to sit clear of the bore. A diameter ratio that gives
  a perfect impedance on a hair-thin conductor can leave a clearance no
  fixture can hold, so clearance is checked on its own and not inferred
  from the impedance being correct.
- Two loss figures matter and they point in opposite directions. The
  through path may lose only a little, because the loss sits directly in
  the current the calibration is trying to establish. The enclosure must
  lose a lot, because screening is what keeps the injected current on
  the conductor instead of radiating into the survey.
- The usable span is a covering condition, not an overlap. A fixture
  whose span merely intersects the calibration span leaves part of the
  sweep uncalibrated, so both edges are compared and each shortfall is
  reported in hertz rather than collapsed into a single verdict.
- The calibration itself is two conversions: applied power into an
  injected current through the fixture impedance, then probe output
  voltage over that current into a transfer impedance in decibel-ohms.
  The second is a logarithm and is not correctly rounded across
  platforms, so equality at a limit is settled with a tolerance.

## Workflow

1. Normalize the fixture record: identifier, bore and conductor
   diameters, optional relative permittivity, insertion loss, screening
   attenuation and the usable span. Reject an unknown key, a missing
   required key, a blank identifier, a non-numeric or non-finite value,
   a permittivity below unity and a bore that does not exceed the
   conductor.
2. Derive the characteristic impedance from the diameter ratio and the
   permittivity, and carry the derived value forward; never accept a
   declared impedance in its place.
3. Compare that impedance with the reference against the fractional
   allowance, and separately compare the standing-wave ratio it implies
   against its own limit. Report both outcomes.
4. Compute the radial clearance from the same two diameters and hold it
   against the minimum the conductor and its insulation need.
5. Hold the through-path insertion loss below its limit and the
   enclosure screening above its floor, absorbing representation error
   at either boundary rather than moving the limit.
6. Check that the usable span covers the calibration span at both
   edges, reporting the low-end and high-end shortfalls separately.
7. Convert the applied power into the injected current through the
   fixture impedance, and the probe output voltage over that current
   into a transfer impedance in decibel-ohms.
8. Aggregate across the offered fixtures: report the usable fraction,
   name the qualifying identifiers, and refuse the set outright when no
   fixture qualifies for the span.

## Pitfalls

- Trusting a declared fixture impedance instead of deriving it from the
  bore, the conductor and the dielectric. The declared figure is what a
  worn or rebuilt fixture keeps long after its geometry has moved.
- Reading a passing standing-wave ratio as a passing impedance. The
  ratio is symmetric and forgiving near the reference; a fixture can
  clear it while the geometry it was built to has drifted outside the
  impedance allowance.
- Inferring the conductor clearance from a correct impedance. Only the
  diameter ratio sets the impedance, so scaling both diameters down
  keeps the impedance exact and squeezes the clearance to nothing.
- Treating an intersecting usable span as a covering one. The part of
  the calibration span the fixture does not reach is uncalibrated, and
  a single pass or fail hides which edge fell short and by how much.
- Confusing the two loss figures, so that a screening shortfall is
  excused by a low through-path loss. A leaky enclosure puts the
  injected current into the survey it was meant to stay out of.
- Comparing a transfer impedance or an insertion loss at an exact limit
  with a strict inequality. Both are logarithms, which round differently
  on different platforms; settle the equality with a tolerance and leave
  the limit where it was specified.

## Behavior contract (gate 3)

The impedance derivation, the reference match and standing-wave-ratio
check, the radial-clearance check, the insertion-loss and screening
checks, the usable-span coverage check, the current and transfer
impedance conversions and the whole-set verdict are exercised by the
gate 3 contract test:
scripts/test_e2007_calibration_jig_characteristics.py against
scripts/e2007_calibration_jig_characteristics_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_calibration_jig_characteristics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
