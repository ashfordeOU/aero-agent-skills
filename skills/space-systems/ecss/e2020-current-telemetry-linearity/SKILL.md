---
name: e2020-current-telemetry-linearity
description: "Evaluate whether an output current telemetry reports linearly and holds its absolute accuracy against the class current of the device over its whole range, per clause 5.2.8.4.1 of ECSS-E-ST-20-20C. Use when a calibration set of applied against reported currents has to become a verdict rather than a plot: divide every signed error by the class current instead of by the reading or by full scale, take the worst point rather than a mean, split the departure into gain error, zero offset and residual bow around a least-squares line, and flag a set that never reached the ends of the range or that folds back. Trigger: ecss, e-st-20-20c-clause-5-2-8-4-1, current-telemetry-linearity, class-referenced-accuracy, telemetry-gain-error, telemetry-non-linearity, calibration-range-coverage, reported-current-fold-back."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e-st-20-20c-clause-5-2-8-4-1, e2020-current-telemetry-linearity, e-st-20-20c, current-telemetry-linearity, class-referenced-accuracy, telemetry-gain-error, telemetry-non-linearity, calibration-range-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Interface — Current Telemetry Linearity (space-systems/ecss/e2020-current-telemetry-linearity)

Use when the task is clause 5.2.8.4.1 of ECSS-E-ST-20-20C: the current
reported by an output telemetry has to follow the current actually
drawn linearly, and its absolute accuracy is stated against the class
current of the device and has to hold across the whole range. This leaf
reads one calibration set and returns the verdict with the error broken
into the parts a designer can act on.

## Domain quick reference

- The reference for the accuracy is fixed, and it is the class current
  of the device. An error of ten milliamps is the same error at the
  bottom of the range as at the top, so dividing it by the class current
  gives one number that means the same thing everywhere.
- The two bases that get substituted for it both hide something. A
  percentage of reading shrinks the stated error towards the top of the
  range and is undefined at the bottom, where the error is largest in
  relative terms and matters most for a quiescent-current check. A
  percentage of full scale flatters any chain whose range was stretched
  to cover the limitation current, because the divisor is then several
  times the class current.
- "Over the whole range" is a statement about the worst point. A mean
  error averages a positive end against a negative end and lands near
  zero on a chain that is out of band at both; a root-mean-square value
  buries a single bad point among good ones. The verdict is taken on the
  largest magnitude.
- Total error is not all non-linearity. A least-squares line through the
  calibration separates a gain error, which a scale-factor change in the
  telemetry conversion removes, and a zero offset, which a calibration
  constant removes, from the residual bow, which neither removes and
  which is the part that says the chain itself is not linear.
- A calibration set is evidence only where it has points. A set
  clustered around the operating point says nothing about the ends, and
  a set in which the reported current falls while the applied current
  rises has shown the characteristic is not a line at all, whatever its
  worst-point error came out at.

## Workflow

1. Validate the calibration set: pairs of applied and reported current,
   applied never negative, reported free to go negative because a
   negative zero offset pushes the bottom of the range below zero, and
   enough distinct applied currents that a straight-line fit has a
   residual at all.
2. Form the signed error at every point and divide each by the class
   current; keep the sign, because a chain that reads high at one end
   and low at the other is a gain error and not two unrelated points.
3. Take the point of largest magnitude as the verdict point and report
   its applied current, its reported current and its absolute error
   alongside the ratio.
4. Compare that magnitude with the allowed fraction of class current,
   absorbing floating-point representation error at an exact match with
   a named tolerance rather than by widening the allowance.
5. Fit the least-squares line and report the gain error as the slope
   departure from unity, the zero offset as the intercept over the class
   current, and the residual bow as the largest departure from the line
   over the class current.
6. Report the coverage of the declared range against an edge allowance
   scaled to the span, and every index at which the reported current
   falls as the applied current rises.
7. Return the verdict with each finding named: out-of-band worst point,
   an end of the range never reached, a fold-back, and a residual bow
   past its own limit when one is declared.

## Pitfalls

- Stating the accuracy as a percentage of reading. It makes the number
  look best exactly where the current is largest and the measurement is
  easiest, and it cannot be stated at all at zero applied current.
- Stating it as a percentage of full scale on a chain whose range was
  sized to reach the limitation current. The divisor is then unrelated
  to the device rating and the same physical error reads several times
  smaller than it is.
- Averaging the calibration. A mean or a root-mean-square over the set
  is not the quantity the clause bounds; one point outside the band is
  a failure however good the rest are.
- Reading a gain error as a non-linearity. A chain with a scale-factor
  error follows a perfectly straight line; calling that non-linear sends
  the fix to the wrong place, when a conversion constant would have
  removed it.
- Calibrating around the operating point only. The accuracy has to hold
  over the whole range, and a set that never reached either end has not
  demonstrated it there, no matter how tight it is in the middle.
- Passing a set in which the reported current folds back. A reversal
  makes the reported value ambiguous over part of the range, and no
  worst-point figure redeems it.

## Behavior contract (gate 3)

The calibration validation, class-referenced error formation, worst-point
selection, reference-basis comparison, least-squares fit, gain, offset
and residual split, range coverage and fold-back detection are exercised
by the gate 3 contract test:
scripts/test_e2020_current_telemetry_linearity.py against
scripts/e2020_current_telemetry_linearity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_current_telemetry_linearity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
