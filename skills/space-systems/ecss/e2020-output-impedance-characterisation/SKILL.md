---
name: e2020-output-impedance-characterisation
description: "Evaluate the output-impedance dataset delivered for each protection-device class against the frequency band the project specified, under ECSS-E-ST-20-20C clause 5.2.17.1.1. Use when gain and phase have to arrive as a reviewable characterisation rather than a plot: refuse a descending or repeated frequency, convert between ohms and dB-ohm, require the sweep to reach both band edges, hold a points-per-decade floor and a largest step between adjacent frequencies, bound the reported phase, report the peak magnitude with the frequency carrying it, and name every declared class whose dataset never arrived. Trigger: ecss, e-st-20-20c-clause-5-2-17, lcl-output-impedance-characterisation, output-impedance-gain-and-phase, output-impedance-sweep-band-coverage, impedance-sweep-points-per-decade, peak-output-impedance-magnitude, db-ohm-magnitude-conversion."
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
  tags: [ecss, e-st-20-20-power-protection-device-scope, e2020-output-impedance-characterisation, lcl-output-impedance-characterisation, output-impedance-gain-and-phase, output-impedance-sweep-band-coverage, impedance-sweep-points-per-decade, peak-output-impedance-magnitude, db-ohm-magnitude-conversion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Protection Devices -- Output Impedance Characterisation (space-systems/ecss/e2020-output-impedance-characterisation)

Use when the task is the clause 5.2.17.1.1 deliverable of
ECSS-E-ST-20-20C: the output impedance of each protection-device class
has to be supplied as gain AND phase across the frequency band the
project specified, and the dataset that arrives has to be judged
reviewable before anybody builds a bus stability case on it.

## Domain quick reference

- What the device presents to the load behind it is a complex
  impedance, not a resistance. The magnitude is what turns a load
  current step into a voltage excursion at the load terminals; the
  phase is what decides whether the device and the input filter of that
  load form a damped loop or an oscillator. Asking for both is the
  clause; a magnitude curve alone cannot answer the second question.
- The characterisation is per class, because each class has its own
  series element, its own control loop and therefore its own curve.
  Supplying one dataset and calling it representative of the family is
  the defect this check exists to catch.
- Reaching the band is not the same as sitting inside it. A sweep that
  starts above the lower edge or stops below the upper edge leaves the
  reader extrapolating exactly where the answer matters, so both edges
  are tested against the sweep ends rather than against its midpoint.
- Resolution has two separate measures and both are needed. Points per
  decade says whether the sweep is dense enough overall; the largest
  step between two adjacent frequencies says whether any single stride
  is wide enough to walk straight over a resonance. A sweep can pass the
  first and fail the second, which is the usual way a peak goes missing.
- Magnitudes travel in two units. Ohms are what the measurement is in,
  dB-ohm is what the plot is read in, and the conversion is twenty times
  the base-ten log. Both are reported so neither reader has to convert
  by hand and misplace a factor of two.
- The peak magnitude and the frequency carrying it are called out
  explicitly, because that pair is what a downstream transient or
  stability budget is actually built on, and it is the one number a
  reader should never have to find by eye.
- The resolution floor, the largest permitted step, the phase bound and
  the peak advisory ceiling are declared project policy rather than
  physical constants; the defaults in the logic module are a starting
  point a project substitutes its own values into.

## Workflow

1. Validate the policy: a resolution floor below one point per decade,
   a step limit at unity and a phase bound beyond a full turn are data
   errors, not conservative entries.
2. Validate each sweep: a positive frequency, a positive magnitude and
   a finite phase at every point, strictly ascending frequencies, no
   repeated point, and at least two points so the sweep describes a band
   rather than a single measurement.
3. Test both band edges against the sweep ends, and report a shortfall
   at each edge as its own finding so the reader knows which end to go
   back and measure.
4. Take the points per decade across the sweep span against the policy
   floor, and the widest adjacent-frequency step against the policy
   limit. Report the two separately; they fail for different reasons and
   are fixed by different reruns.
5. Bound the reported phase and name every point outside it with its
   frequency, since a phase excursion is usually a wrap or a sign
   convention rather than a real measurement.
6. Report the peak magnitude in ohms and in dB-ohm with the frequency
   carrying it, and raise an advisory when the peak sits above the
   project ceiling.
7. Walk the declared class list, not the delivered one. A declared class
   with no dataset is a finding; a dataset for a class nobody declared
   is an advisory, because the second is untidy and the first is a hole.

## Pitfalls

- Delivering magnitude and leaving phase to a separate note. The two
  are one deliverable, and a stability argument built on magnitude alone
  cannot distinguish a damped response from a marginal one.
- Judging band coverage from the middle of the sweep. Coverage is a
  statement about the two ends, and a sweep comfortably inside the band
  fails it while looking entirely healthy on a plot.
- Passing the points-per-decade floor and calling the sweep resolved. A
  dense sweep with one wide stride in it steps over the resonance the
  whole exercise exists to find; the adjacent-step check is what catches
  that, and it is a separate test.
- Walking the delivered datasets instead of the declared class list. A
  class nobody measured produces no row to notice, so the absence is
  invisible unless the declared list drives the loop.
- Comparing a frequency ratio, a points-per-decade figure or a dB-ohm
  value by bare arithmetic. These are built from division and from
  log10, which is not correctly rounded and lands differently on
  different platforms, so a point meant to sit exactly on a bound can
  fall the wrong side of it; the comparison absorbs that representation
  error while the bound stays as declared.

## Behavior contract (gate 3)

The policy validation, point and sweep validation, ohm to dB-ohm
conversion, band-edge coverage, points-per-decade and adjacent-step
resolution, phase bounding, peak reporting, per-class assessment and
the declared-class delivery verdict are exercised by the gate 3 contract
test: scripts/test_e2020_output_impedance_characterisation.py against
scripts/e2020_output_impedance_characterisation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_output_impedance_characterisation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
