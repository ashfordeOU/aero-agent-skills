---
name: e2007-system-radiofrequency-compatibility-test
description: "Build and audit the system-level radiofrequency compatibility test required by ECSS-E-ST-20-07C clause 5.3.8, whose scope stops short of passive intermodulation products. Use when onboard emitters and receivers have to be shown compatible while running together: enumerate every fundamental, harmonic and spurious line, set the passive intermodulation products aside by name and reason, couple each remaining product through the declared antenna gains and pair isolation, decide passband or out-of-band and apply the receiver rejection, take the interference margin, mark the cases that must be exercised rather than argued, and reconcile the executed results against them. Trigger: ecss, e-st-20-07c, system-radiofrequency-compatibility-test, emitter-receiver-interference-margin, harmonic-and-spurious-products, passive-intermodulation-exclusion, receiver-out-of-band-rejection, antenna-pair-isolation, simultaneous-operating-modes."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-system-radiofrequency-compatibility-test, system-radiofrequency-compatibility-test, emitter-receiver-interference-margin, passive-intermodulation-exclusion, receiver-out-of-band-rejection, antenna-pair-isolation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — System Radiofrequency Compatibility Test (space-systems/ecss/e2007-system-radiofrequency-compatibility-test)

Use when the task is the system radiofrequency compatibility test of
ECSS-E-ST-20-07C clause 5.3.8 -- deciding which emitter-to-receiver
cases the integrated vehicle has to demonstrate on the floor, and
which products this particular test does not own.

## Domain quick reference

- The test is a system activity, not a unit one. Unit-level emission
  and susceptibility limits are met one box at a time; compatibility is
  a property of the emitters, the receivers, the antenna placement and
  the operating timeline taken together, and it only exists once they
  are integrated.
- The matrix is built from products, not from transmitters. One
  emitter puts its fundamental, a harmonic series and every declared
  spurious line onto the matrix, and the product that lands on a
  receiver passband is usually not the fundamental.
- Passive intermodulation products are outside this test. They are
  generated in passive hardware -- junctions, joints, imperfect
  contacts -- rather than by the emitter, and they are verified by
  their own dedicated activity. They are listed and reasoned, never
  silently dropped, because an unlabelled absence reads as coverage.
- The coupling chain is additive in decibels: product level, emitter
  antenna gain, receiver antenna gain, minus the declared pair
  isolation. Keeping every quantity in dB makes the margin exact
  arithmetic instead of a ratio of two powers that has to be rounded.
- In band and out of band are different regimes. A product inside the
  receiver passband is seen with the full susceptibility of the
  receiver; a product outside it is attenuated by the front-end
  rejection first, which is why an out-of-band harmonic 60 dB stronger
  can still matter less than a weak in-band spur.
- A case only exists while both units run at once. An emitter confined
  to a launch mode and a receiver used only on station never meet, and
  loading the matrix with impossible pairs buries the real ones.
- An analysis margin shortfall is closed by the test, not by
  re-argument: the shortfall marks the case mandatory, and only an
  executed result retires it.

## Workflow

1. Validate every emitter and receiver record: identifiers,
   frequencies, power, antenna gains, harmonic suppression, declared
   spurious lines with their mechanism, susceptibility, bandwidth,
   out-of-band rejection, operating modes. Reject an unknown mechanism,
   a non-positive frequency or bandwidth, an empty mode list, or a
   repeated identifier.
2. Enumerate the products of each emitter out to the declared harmonic
   order, applying the suppression and the per-order fall-off, and add
   each declared spurious line referred to its carrier.
3. Set aside every product whose mechanism is outside this test,
   recording the case identifier, the pair and the reason.
4. For each remaining product and receiver, take the declared pair
   isolation, couple the level in, decide passband or out-of-band under
   the named frequency tolerance, and raise the susceptibility by the
   rejection when the product is out of band.
5. Take the margin as the effective susceptibility less the coupled
   level, and mark the case mandatory when the two units share an
   operating mode and either the product is in band or the margin falls
   short of the required value under the named margin tolerance.
6. Reconcile the executed results: a mandatory case with no result is
   uncovered, a failed result is demonstrated interference, a passing
   result retires the shortfall, and a result for a case outside the
   matrix is itself a finding.
7. Report the full matrix with bands and margins, the excluded
   products, the mandatory identifiers and every finding.

## Pitfalls

- Testing the fundamentals only. The case that bites is a harmonic or
  a spurious line sitting on a navigation or telecommand passband, and
  it is invisible in a matrix built from carrier frequencies.
- Dropping passive intermodulation quietly. Excluding it is correct for
  this test and wrong for the vehicle: the exclusion has to be visible
  so its own verification is not lost with it.
- Applying the out-of-band rejection to an in-band product. It turns a
  genuine in-band exceedance into a comfortable margin, which is the
  single most common way this matrix is made to close.
- Arguing a shortfall on paper. The clause asks for a system test; a
  case whose analysis margin is short is exercised, and only a passing
  executed result retires it.
- Loading the matrix with pairs that never run together. It inflates
  the case count, consumes the test window and hides the handful of
  cases that are real.
- Widening the required margin to clear a case sitting exactly on it.
  An equality at the limit is a representation question, absorbed by
  the named tolerance inside the comparison; the required value stays
  as specified.

## Behavior contract (gate 3)

The emitter and receiver validation, product enumeration, scope
exclusion, passband decision, coupling arithmetic, margin computation,
mandatory-case marking and executed-result reconciliation are exercised
by the gate 3 contract test:
scripts/test_e2007_system_radiofrequency_compatibility_test.py against
scripts/e2007_system_radiofrequency_compatibility_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_system_radiofrequency_compatibility_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
