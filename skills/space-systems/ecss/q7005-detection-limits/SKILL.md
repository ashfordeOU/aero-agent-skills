---
name: q7005-detection-limits
description: "Estimate the detection and quantification limits of an infrared surface-contamination method and the uncertainty of a result under ECSS-Q-ST-70-05C. Use when replicate blanks have been run, a calibration slope exists, and a reading has to be reported as not detected, detected but not quantified, or quantified with an interval. Forms the blank standard deviation over enough replicates, scales it by the detection and quantification multipliers, carries the same sampling factors the sample result carries, and combines the relative uncertainty components in quadrature to an expanded figure. Trigger: ecss, q-st-70-05, ir-method-detection-limit, blank-replicate-standard-deviation, quantification-limit-areal-mass, combined-standard-uncertainty, expanded-uncertainty-coverage-factor, contamination-reporting-decision."
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
  tags: [ecss, q-st-70-contamination-infrared-scope, q7005-detection-limits, ir-method-detection-limit, blank-replicate-standard-deviation, quantification-limit-areal-mass, combined-standard-uncertainty, expanded-uncertainty-coverage-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Organic Contamination by IR — Detection Limits and Uncertainty (space-systems/ecss/q7005-detection-limits)

Use when the task is saying what the method can and cannot see —
establishing the detection and quantification limits from blank
replicates, and attaching an uncertainty to a contamination result so a
number near a cleanliness limit can be argued about honestly.

## Domain quick reference

- The limits come from the blanks, not from the instrument
  specification. What matters is the scatter of the whole method run on
  a clean sample — window, solvent, handling, baseline drawing — because
  that scatter is what a small real signal has to stand out of.
- The detection limit is a small multiple of that blank standard
  deviation, and the quantification limit a larger one. Between them a
  species is present but its mass is not reportable; below the detection
  limit there is no statement to make beyond the limit itself.
- A standard deviation from too few replicates is itself badly known,
  and a limit built on three blanks is optimistic in a way that does not
  show in the number. A replicate floor is part of the method, not a
  nicety.
- Limits are expressed in the same units as the result, which means they
  carry the same chain: the calibration slope to turn signal into mass,
  then the dilution, recovery and sampled area to turn mass into an
  areal figure. A limit quoted in absorbance cannot be compared with a
  cleanliness allocation.
- The uncertainty of a result is not the blank scatter alone. The
  calibration slope, the sampled area, the recovery fraction and the
  measurement repeatability each contribute a relative component, and
  they combine in quadrature, so the largest one dominates and shaving
  the small ones changes almost nothing.
- Reporting an interval means stating the coverage factor with it. An
  expanded uncertainty without its factor is not interpretable, and two
  results quoted at different factors are not comparable.

## Workflow

1. Validate the blank replicates: enough of them, all finite, and
   measured by the same method as the samples.
2. Form the blank mean and the sample standard deviation over the
   replicates, refusing a set whose scatter is exactly zero as an
   artefact of rounding rather than a perfect method.
3. Scale the standard deviation by the detection and quantification
   multipliers to obtain both limits in signal units.
4. Convert both limits through the calibration slope and the sampling
   factor — dilution over recovery times area — into areal masses.
5. Place the sample reading against the two limits and return the
   reporting decision: not detected, detected but not quantified, or
   quantified.
6. Combine the relative uncertainty components in quadrature into a
   combined standard uncertainty, and multiply by the coverage factor
   for the expanded uncertainty.
7. Report both limits, the decision, the interval and its coverage
   factor, plus a finding when the result sits inside its own expanded
   uncertainty of a cleanliness limit.

## Pitfalls

- Quoting a detection limit in absorbance. It cannot be compared with an
  areal allocation, and converting it later usually loses the dilution
  or the recovery that the sample result carried.
- Building the limit on a handful of blanks. The standard deviation of a
  small set is unstable, so the limit moves run to run and is
  systematically optimistic.
- Reporting a mass for a reading between the two limits. The species is
  there, but the method cannot support a number; the honest output is
  the detection statement and the quantification limit.
- Adding the uncertainty components arithmetically. They combine in
  quadrature, so an arithmetic sum overstates the interval and can turn
  a compliant result into a disputed one for no physical reason.
- Giving an expanded uncertainty without its coverage factor. The
  interval is meaningless without it, and comparing two such intervals
  silently compares different confidence statements.

## Behavior contract (gate 3)

The blank-replicate validation, mean and standard deviation, detection
and quantification limits in both signal and areal units, the reporting
decision, the quadrature combination of relative components and the
expanded uncertainty are exercised by the gate 3 contract test:
scripts/test_q7005_detection_limits.py against
scripts/q7005_detection_limits_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7005_detection_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
