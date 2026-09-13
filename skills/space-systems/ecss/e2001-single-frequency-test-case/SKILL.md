---
name: e2001-single-frequency-test-case
description: "Use when determine the one radio-frequency point at which a single-frequency multipactor test is run under ECSS-E-ST-20-01C clause 6.4.2: categorize the item as resonant-field or non-resonant-field hardware, take the drift-shifted low band edge for a non-resonant run because the onset threshold tracks the frequency-gap-product, take the frequency of peak voltage-magnification from the measured field map for a resonant unit, confirm the tuning-and-thermal-drift window stays inside the declared operating-band, check the resulting frequency-gap-product against the validated susceptibility-chart span, and establish whether one point suffices. Trigger: ecss, e-st-20-electrical-scope, e-st-20-01c, single-frequency-multipactor-test, frequency-selection-provision, peak-voltage-magnification, frequency-gap-product, tuning-drift-window, susceptibility-chart-span, critical-gap-selection."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-single-frequency-test-case, single-frequency-multipactor-test, peak-voltage-magnification, frequency-gap-product, tuning-drift-window, critical-gap-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Single Frequency Test Case (space-systems/ecss/e2001-single-frequency-test-case)

Use when the task is picking, for ECSS-E-ST-20-01C clause 6.4.2, the single
radio-frequency point that a multipactor test is run at, and justifying that
point against the frequency selection provisions rather than defaulting to
the band centre.

## Domain quick reference

- The worst case inside an operating band depends on how the item stores
  energy, so the selection starts by categorizing the hardware. A waveguide
  run, a coaxial line, a connector, a transition, a rotary joint or a
  switch is non-resonant-field: the peak field per unit input power barely
  varies across the band. A cavity filter, an output multiplexer, a
  diplexer or a dielectric-resonator filter is resonant-field: voltage
  builds up at the resonances and the peak field per unit input power can
  vary by a large factor within the same band.
- For non-resonant-field hardware the onset threshold is set by the
  frequency-gap product of the critical gap. The threshold falls with that
  product, so the worst case is the low band edge, taken at the
  drift-allowance-shifted edge rather than the nominal one.
- For resonant-field hardware the worst case is instead the frequency at
  which the voltage-magnification of the critical gap peaks, read from the
  measured or modelled field map. A band edge is usually not that point,
  and testing at the edge of such a unit under-stresses the gap that
  actually breaks down.
- The critical gap is the smallest declared gap, since for a common
  frequency the smallest gap carries the lowest frequency-gap product and
  therefore the lowest threshold. Ties between equal gaps are broken
  deterministically so a rerun of the selection reproduces the same record.
- Tuning error and thermal drift move a resonance. The drift window around
  a resonant selection is checked against the declared band: a window that
  reaches past an edge means the true worst case can sit outside the point
  being tested, which is a finding, not a rounding detail.
- The selected point is re-expressed as a frequency-gap product in GHz.mm
  and checked against the validated span of the susceptibility chart being
  used; a product outside that span means the chart is being read beyond
  where it was established.

## Workflow

1. Categorize the item as resonant-field or non-resonant-field hardware;
   an unrecognized component type is an error, because the selection rule
   branches on this and there is no safe default.
2. Validate the declared operating band and identify the critical gap as
   the smallest declared gap, rejecting duplicate or unnamed gap entries.
3. For non-resonant-field hardware, select the low band edge shifted down
   by the drift allowance, and record the basis as the lowest
   frequency-gap product.
4. For resonant-field hardware, read the field map, reject any entry that
   sits outside the declared band, and select the frequency of peak
   voltage-magnification, breaking ties toward the lower frequency.
5. For a resonant selection, open the tuning-and-thermal-drift window
   around the selected point and report any part of it that falls outside
   the declared band.
6. Convert the selected point and the critical gap into a frequency-gap
   product and report a product that lies outside the validated
   susceptibility-chart span.
7. When the covered-band ratios of the test are known, check that the one
   selected point covers both band edges; otherwise the single-frequency
   test case is not established and more points are needed.
8. Aggregate every finding into one record; the single-frequency test case
   is valid only when that list is empty.

## Pitfalls

- Selecting the band centre out of habit. The centre is the worst case for
  neither family: the non-resonant worst case is an edge, the resonant one
  is wherever the field map peaks.
- Using the largest gap as the critical gap. The smallest gap carries the
  lowest frequency-gap product and breaks down first.
- Applying the resonant rule with no field map, or applying the
  non-resonant rule to a filter. Both produce a defensible-looking number
  from the wrong physics.
- Ignoring the drift window because the nominal peak sits inside the band.
  A resonance a fraction of a percent from an edge leaves the band over
  temperature, and the test point then no longer represents the worst case.
- Reading a susceptibility chart outside the span over which it was
  established, which silently converts an extrapolation into a quoted
  threshold.
- Comparing a selected frequency with a band edge using bare
  floating-point equality. A point derived from a drift fraction lands a
  few units in the last place off the edge; absorb that in the comparison,
  never by widening the band.

## Behavior contract (gate 3)

The response categorization, critical-gap selection, field-map peak search,
drift-window check, frequency-gap-product conversion, chart-span check and
single-point sufficiency logic are exercised by the gate 3 contract test:
scripts/test_e2001_single_frequency_test_case.py against
scripts/e2001_single_frequency_test_case_logic.py (stdlib unittest,
offline, deterministic). Run:
python3 scripts/test_e2001_single_frequency_test_case.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
