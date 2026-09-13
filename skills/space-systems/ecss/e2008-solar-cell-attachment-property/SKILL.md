---
name: e2008-solar-cell-attachment-property
description: "Verify that bonded cell assemblies stay attached to the panel through the whole test sequence and on to mission life under ECSS-E-ST-20-08C clause 5.3.3.11.2: anchor every later measurement to the as-bonded reference, walk the humidity, solar-array-thermal-cycling, vibration, acoustic and thermal-vacuum stages in order, hold both an overall retention floor and a per-stage drop allowance so one punishing environment cannot hide inside a gentle average, take any detached cell assembly as an outright failure of the property, then check the cycles actually run against the factored mission cycles and extrapolate the surviving strength to end of life. Use when an attachment qualification record has to be sentenced. Trigger: ecss, e-st-20-electrical-scope, solar-cell-attachment-property, cell-attachment-retention, solar-array-thermal-cycling, panel-detachment-screening, attachment-life-extrapolation, mission-cycle-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-solar-cell-attachment-property, solar-cell-attachment-property, cell-attachment-retention, solar-array-thermal-cycling, panel-detachment-screening, attachment-life-extrapolation, mission-cycle-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Solar Cell Attachment Property (space-systems/ecss/e2008-solar-cell-attachment-property)

Use when the task is the attachment property of ECSS-E-ST-20-08C clause
5.3.3.11.2 -- showing that the cell assemblies stay bonded to the panel
for the whole test sequence and for the mission after it, not merely
that they were bonded on the day they were laid up.

## Domain quick reference

- One as-bonded number does not answer this clause. The property is
  retention: the panel has still to face humidity storage, a vibration
  and acoustic run, a thermal-vacuum soak and years of
  solar-array-thermal-cycling, and the attachment has to survive all of
  it.
- The evidence is a stage-by-stage record anchored to the as-bonded
  reference. Each later stage carries the adherence measured on its own
  coupons and the number of cell assemblies that came off during it.
- Two retention checks run together and catch different failures. The
  overall check compares each stage against the as-bonded reference and
  catches slow cumulative loss. The per-stage check compares a stage
  against the one before it and catches a single punishing environment
  that a gentle average would otherwise absorb.
- A detached cell assembly is not a low data point, it is the failure
  itself. Any detachment at any stage breaks the property whatever the
  surviving coupons measured, so it is counted separately from the
  strength numbers.
- A strength gain between stages is recorded as no drop rather than as
  a negative one. Coupon scatter routinely produces a higher reading
  later in the sequence, and crediting it would let a genuine loss in
  the next stage net out to nothing.
- Mission life is a cycle count, not a date. The cycles actually run
  have to cover the mission cycles multiplied by the declared test
  factor; where they fall short, the surviving strength is extrapolated
  across the missing decades of cycles and compared against the minimum
  attachment strength.
- The retention floor, the per-stage allowance, the test factor and the
  per-decade degradation are a declared project policy rather than
  physical constants, so they are stated with the result.

## Workflow

1. Take the as-bonded reference as the first stage and reject a record
   that starts anywhere else. Without that anchor, retention has no
   denominator and the later stages measure nothing.
2. Walk the remaining stages in the order they were run. Compute each
   stage's retention against the reference and its drop against the
   preceding stage, and carry the detached-cell count.
3. Sentence each stage on its own: detachments within the allowance,
   retention above the floor, drop within the per-stage allowance.
   Report the stage that failed by name so the retest is scoped to it.
4. Aggregate the detachments across the whole sequence. A single
   detachment anywhere is enough to withhold the property.
5. Compare the cycles run against the mission cycles times the test
   factor. Where the test reached or passed the mission, the measured
   strength stands; where it stopped short, degrade it across the
   missing decades and never credit a recovery.
6. Close with a verdict: attachment retained, not retained with the
   reasons listed, or not evaluated when only the reference was ever
   measured.

## Pitfalls

- Reporting the mean retention over the sequence. It hides the one
  environment that did the damage, which is the only stage a corrective
  action can be aimed at.
- Treating a detachment as a low coupon result. The property is that the
  assemblies stay on; a cell assembly that came off has already failed
  it, and averaging it away with the survivors converts a failure into a
  data point.
- Stopping at the last test measurement. A test that ran fewer cycles
  than the mission has demonstrated only the cycles it ran, and the
  remaining decades are exactly where a bondline creeps.
- Crediting a strength gain between stages. Coupon scatter produces
  them, and letting one offset a later drop lets a real loss disappear
  in the arithmetic.
- Comparing retention or an end-of-life strength against its floor by
  bare arithmetic. Retention is a quotient and the extrapolation is a
  power, so a case meant to sit exactly on the floor can land a few
  units in the last place below it; the comparison absorbs that
  representation error while the floor stays untouched.

## Behavior contract (gate 3)

The reference anchoring, per-stage retention and drop checks,
detachment aggregation, mission-cycle coverage, end-of-life
extrapolation and the retention verdict are exercised by the gate 3
contract test:
scripts/test_e2008_solar_cell_attachment_property.py against
scripts/e2008_solar_cell_attachment_property_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_solar_cell_attachment_property.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
