---
name: e2008-test-tolerance-and-accuracy-rules
description: "Verify the instrument precision each controlled or measured solar-array test parameter demands, anchored at ECSS-E-ST-20-08C clause 4.3.2. Use when a photovoltaic-assembly test plan has to name its instrumentation: derive the governing tolerance half-band from the declared two-sided, asymmetric or one-sided limits, compute the largest instrument uncertainty that half-band will carry, restate it as a test-accuracy-ratio, check the reading resolution and the set-point drift a controlled parameter adds, guard-band the acceptance limits when the ratio is only marginal, and accept or reject the instrumentation list parameter by parameter. Trigger: ecss, e-st-20-08c, solar-array-test-parameter-tolerance, solar-array-instrument-precision-ratio, test-accuracy-ratio, tolerance-half-band-derivation, solar-array-reading-resolution, solar-array-set-point-drift, photovoltaic-test-instrumentation, guard-banded-acceptance-limits."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-test-tolerance-and-accuracy-rules, solar-array-test-parameter-tolerance, solar-array-instrument-precision-ratio, test-accuracy-ratio, tolerance-half-band-derivation, solar-array-reading-resolution, photovoltaic-test-instrumentation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Test Tolerance and Accuracy Rules (space-systems/ecss/e2008-test-tolerance-and-accuracy-rules)

Use when the task is the accuracy rule of ECSS-E-ST-20-08C clause 4.3.2 --
the precision an instrument has to hold relative to the tolerance of the
photovoltaic-assembly test parameter it controls or reads back, and the
consequences that follow when the instrument is only just good enough.

## Domain quick reference

- The rule is relative, not absolute. Nothing in it names a precision in
  volts or degrees; it names a share of the tolerance the parameter
  already carries. A half-degree instrument is excellent against a
  five-degree band and useless against a half-degree one, and the same
  instrument therefore passes on one parameter and fails on the next.
- The band has two sides and they are frequently not equal. An
  illumination level held to plus five percent and minus one percent is
  governed by the one-percent side, because that is the side an
  instrument error first pushes a reading across. The governing
  half-band is the tighter non-zero side, never the average and never
  the full width.
- A side declared as zero is not a tolerance, it is a hard limit. The
  band is then one-sided and the governing half-band comes from the
  other side alone. A parameter with zero on both sides carries no
  tolerance at all and is malformed input, not a demanding parameter.
- The precision rule and the test-accuracy-ratio are the same statement
  read from opposite ends: the instrument may consume at most a fixed
  share of the governing half-band, which is to say the half-band must
  be at least the reciprocal of that share times the uncertainty.
  Report both, because a plan reviewer reads the ratio and a procurement
  specification reads the precision.
- Resolution is a separate failure from uncertainty. An instrument
  accurate to a hundredth but displaying to a tenth cannot demonstrate
  a tenth-wide band, however well it is calibrated, so the reading step
  is held against its own, finer share of the half-band.
- A controlled parameter owes more than a measured one. Beyond the
  read-back uncertainty it has to hold its set point across the dwell,
  and that drift consumes its own share of the same half-band. A
  measured parameter has no set point, so a drift declaration on one is
  a mis-stated role rather than extra rigour.
- When the ratio is comfortable the declared limits are used as they
  stand. When it is only marginal, the uncertainty is subtracted from
  each toleranced side so that a reading inside the reduced window sits
  inside the real limit whichever way the instrument erred. If the
  subtraction leaves no window, the parameter cannot be demonstrated
  with that instrument at all.
- A share met exactly is met. A limit computed as a product or a ratio
  can land a few units in the last place outside an exactly-met bound;
  absorb that in the comparison, never by widening the bound.

## Workflow

1. Normalize the parameter: identifier, role, unit, nominal, the two
   tolerance magnitudes, instrument uncertainty, and optionally the
   reading resolution and the set-point drift. Reject an unknown key, a
   missing required key, a blank identifier, an unrecognised role, a
   non-numeric or non-finite value and a negative tolerance.
2. Resolve the limits into a band and take the governing half-band from
   the tighter non-zero side; flag the band as one-sided or asymmetric
   so a later reader does not re-derive it from the width.
3. Compute the largest instrument uncertainty the half-band will carry,
   and the ratio the declared instrument actually achieves.
4. If a reading resolution is declared, hold it against its own share of
   the half-band.
5. If a set-point drift is declared, confirm the parameter is controlled
   and hold the drift against its share of the same half-band.
6. Decide whether the acceptance limits need guard-banding, apply it to
   each toleranced side, and flag a window the subtraction collapses.
7. Aggregate across the list: reject a duplicate identifier, report the
   controlled and measured counts, name every guard-banded parameter,
   report the conforming fraction and accept the instrumentation only
   when no finding remains.

## Pitfalls

- Taking the governing half-band from the full width, or from the wider
  side of an asymmetric band -- both make a marginal instrument look
  comfortable by a factor of two or more.
- Reading a zero tolerance as an infinitely tight one and rejecting the
  parameter outright; the zero side is a hard limit and the other side
  governs. Guard-banding cannot shrink a zero side either, so the
  reduced window is asymmetric by construction.
- Accepting an instrument on its calibration certificate alone while its
  display resolves more coarsely than the band -- the certificate
  governs uncertainty, the display governs what can be demonstrated.
- Charging a measured parameter with a set-point drift, or excusing a
  controlled one from it. The role decides which allowances apply, and a
  drift declared on a measured parameter is a role error to raise, not a
  spare margin to consume.
- Guard-banding a parameter whose ratio is already comfortable, which
  narrows the window for no reason and can fail an article that conforms.
- Widening the share to rescue an instrument that misses the bound by a
  few units in the last place; absorb the representation error in the
  comparison instead, and treat a real miss as a real finding.

## Behavior contract (gate 3)

The tolerance-band derivation, the required-precision and
test-accuracy-ratio computation, the reading-resolution and set-point
drift checks, the guard-banded acceptance limits and the whole-list
acceptance are exercised by the gate 3 contract test:
scripts/test_e2008_test_tolerance_and_accuracy_rules.py against
scripts/e2008_test_tolerance_and_accuracy_rules_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_test_tolerance_and_accuracy_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
