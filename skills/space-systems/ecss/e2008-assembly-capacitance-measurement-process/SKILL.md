---
name: e2008-assembly-capacitance-measurement-process
description: "Use when a string capacitance figure is about to be quoted from a method nobody established as accepted. Determine which single accepted method, frequency domain or time domain, a photovoltaic string capacitance measurement runs under per ECSS-E-ST-20-08C clause 5.5.3.5.2, and show the nominated one holds: size the reactance at the test frequency against the instrument band, derive the dissipation factor the string leakage produces, compute the decay constant a discharge resistor sets and the samples the recorder places inside it, size the fixture stray against the article, and close an uncertainty budget against the requirement. Trigger: ecss, e-st-20-08c-clause-5-5-3-5-2, solar-array-string-capacitance-measurement, frequency-domain-capacitance-method, time-domain-capacitance-method, string-capacitance-uncertainty-budget, fixture-stray-capacitance-fraction, capacitance-bridge-dissipation-limit."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-assembly-capacitance-measurement-process, solar-array-string-capacitance-measurement, frequency-domain-capacitance-method, time-domain-capacitance-method, string-capacitance-uncertainty-budget, fixture-stray-capacitance-fraction, capacitance-bridge-dissipation-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- String Capacitance Measurement Process (space-systems/ecss/e2008-assembly-capacitance-measurement-process)

Use when the task is clause 5.5.3.5.2 of ECSS-E-ST-20-08C -- measuring
the capacitance of a photovoltaic assembly string by one accepted
method, taken either from the frequency domain or from the time domain.
The clause asks for a method, singular. A campaign that leaves both
domains open produces two numbers with no rule for reconciling them,
and the string capacitance is the quantity that sizes the stored energy
a surface discharge releases, so the number has to be defensible rather
than merely available.

## Domain quick reference

- The string is a distributed capacitor. Cells, coverglasses and the
  substrate under them hold charge against the structure, and that
  charge is what feeds an electrostatic discharge when the front
  surface flashes over. The measurement exists to size that store.
- Frequency-domain methods -- a balanced bridge or a swept impedance
  analyser -- read the reactive part of the impedance at a test
  frequency. The article presents 1 / (2 pi f C) ohms there, and the
  instrument has to have that impedance inside its range; a frequency
  chosen for convenience can put the article off the end of the scale.
- The frequency domain has a second gate the time domain does not: the
  dissipation factor, leakage conductance over 2 pi f C. A lossy string
  reads as a capacitance that moves with frequency, so a dissipation
  factor above about a tenth means the recorded number is not a
  capacitance at all.
- Time-domain methods -- a resistive discharge or a constant-current
  charge -- read the decay constant R times C, or the ramp rate I over
  C. They ask for instrumentation rather than for a clean article: the
  recorder needs roughly ten samples inside one decay constant to fit
  the exponential, and a window of about five decay constants for the
  decay to finish before the record stops.
- Fixture stray and lead capacitance sit in series with neither domain
  and in parallel with both. A harness contributing more than a few
  per cent of the article has to be guarded or subtracted from a
  measured open-circuit reading, because it biases the answer in the
  same direction every time and no repeat will reveal it.
- The uncertainty that matters is the combination, not the instrument
  specification alone. Instrument accuracy, stray share and fixture
  repeatability are independent, so they add as a root sum of squares
  and the total is what gets compared against the requirement.

## Workflow

1. Take the nomination and reduce it to one method. Refuse a nomination
   that names none or names two, rather than picking a preferred one,
   because the choice is the clause's subject.
2. Pull the evidence that method owes from its domain. A bridge owes a
   test frequency, a leakage conductance and an instrument range; a
   discharge owes a resistor, a sample rate and a record window.
   Missing evidence stops the judgement instead of defaulting.
3. Size the fixture stray as a fraction of the expected article
   capacitance first, since it applies whichever domain was chosen and
   a dominant stray invalidates both.
4. For a frequency-domain nomination, compute the reactance at the test
   frequency and place it in the instrument band, then compute the
   dissipation factor and hold it under the loss ceiling.
5. For a time-domain nomination, compute the decay constant, then the
   samples the recorder places inside it and the decay constants the
   window spans, and hold both above their floors.
6. Combine instrument accuracy, stray share and fixture repeatability
   as a root sum of squares and compare against the required
   uncertainty. Close with a verdict that stays open while any finding
   stands.

## Pitfalls

- Averaging a bridge reading with a discharge reading. The clause asks
  for one method; two methods with different stray paths and different
  loss sensitivities do not produce a better number by being averaged,
  they produce one nobody can trace.
- Choosing the test frequency from habit. At 1 kHz a tenth of a
  microfarad sits near a kilohm, but a small coupon string can land
  megohms away and off the instrument scale, and the reading that comes
  back looks like a measurement.
- Recording a capacitance from a lossy string without the dissipation
  factor. The bridge always returns a number; only the loss term says
  whether that number is a capacitance or an artefact of the leakage.
- Sampling a discharge at a rate chosen for the trigger rather than for
  the decay. A handful of points on an exponential fits almost any
  time constant, and the fit residual will not look wrong.
- Stopping the record when the trace looks flat. A window shorter than
  about five decay constants truncates the tail, and the truncation
  biases the fitted constant low rather than scattering it.
- Comparing a derived span or sample count against its floor by bare
  arithmetic. Both are products of floats that can land a few units in
  the last place either side of a limit written in another unit, so the
  comparison absorbs that error while the limit itself is never
  relaxed.
- Quoting the instrument accuracy as the measurement uncertainty. The
  fixture stray and the repeatability are usually the larger terms on a
  string, and dropping them understates the budget exactly where the
  requirement is tightest.

## Behavior contract (gate 3)

The single-method nomination, per-domain evidence requirement,
reactance and instrument-band check, dissipation factor, decay
constant, samples per decay constant, record-window span, fixture stray
share and root-sum-square uncertainty budget are exercised by the gate
3 contract test:
scripts/test_e2008_assembly_capacitance_measurement_process.py against
scripts/e2008_assembly_capacitance_measurement_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_assembly_capacitance_measurement_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
