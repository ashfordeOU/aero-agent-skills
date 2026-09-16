---
name: e2008-bare-cell-electrical-performance
description: "Use when a bare cell parameter sheet or lot summary has to support array sizing. Assess the bare solar cell electrical parameters that clause 7.5.3 of ECSS-E-ST-20-08C puts behind a solar generator design decision: hold each measurement to the reference illumination and the cell temperature window, derive maximum power, fill factor and conversion efficiency from the recorded current and voltage pairs, refuse a point set whose peak power pair sits outside its own short circuit current or open circuit voltage, then reduce the measured lot to the mean, spread and lower bound a generator sizing case can be built on. Trigger: ecss, e-st-20-08c-clause-7-5-3, bare-solar-cell-electrical-performance, bare-cell-fill-factor-derivation, bare-cell-conversion-efficiency, bare-cell-lot-design-power-bound, bare-cell-measurement-condition-window."
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
  tags: [ecss, e-st-20-08-bare-solar-cell-scope, e2008-bare-cell-electrical-performance, e-st-20-08c-clause-7-5-3, bare-solar-cell-electrical-performance, bare-cell-fill-factor-derivation, bare-cell-conversion-efficiency, bare-cell-lot-design-power-bound, bare-cell-measurement-condition-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells — Electrical Performance (space-systems/ecss/e2008-bare-cell-electrical-performance)

Use when the task is clause 7.5.3 of ECSS-E-ST-20-08C: the electrical
parameters of bare cells measured so that a solar generator can be designed
around them. The clause's subject is a decision, not a data sheet. What turns
four measured numbers per cell into a design input is the derivation that ties
them together and the population statistic that survives the spread.

## Domain quick reference

- The design input is a distribution, not a cell. A generator is sized on what
  the weakest string will deliver, and a single cell says nothing about that.
  The lot has to be wide enough for its spread to mean something before any
  number taken from it belongs in a sizing case.
- Fill factor is a derived quantity and therefore a consistency check. It is
  the peak power divided by the product of the two extremes, so a value no real
  characteristic curve produces is evidence the four numbers were not taken
  from one curve rather than evidence of a poor cell.
- A peak power pair outside its own short circuit current or open circuit
  voltage is arithmetically impossible on a single curve. That record is
  refused outright; it is not a weak cell to be reported, it is a transcription
  or instrument fault to be sent back.
- Efficiency needs the cell area, and area is where unit slips live. The
  parameters arrive in amperes and volts while the area arrives in square
  centimetres, so the incident flux carries the conversion and nothing else in
  the chain should.
- The measurement belongs to the bench. Cell current tracks the illumination
  almost linearly and the voltage drifts with temperature, so a parameter read
  off an uncontrolled bench describes the bench and a generator sized on it
  inherits that drift silently.

## Workflow

1. For each cell, confirm the measurement sat inside the reference illumination
   tolerance and the cell temperature window. A reading outside it is a
   condition finding, not a parameter.
2. Derive maximum power from the recorded peak power pair, then fill factor
   against the short circuit current and open circuit voltage, refusing any
   pair that sits outside those two extremes.
3. Convert maximum power and cell area into a conversion efficiency at the
   reference irradiance, and hold both power and efficiency against the
   declared minima, absorbing floating-point representation error at the limit
   with a named tolerance rather than by loosening the limit.
4. Reject a cell identifier that appears twice; two records under one name make
   the lot ambiguous rather than redundant.
5. Reduce the lot to a count, a mean, a sample spread and its extremes, for
   both power and efficiency.
6. Report the per-cell design power as a lower statistical bound on the lot,
   never above the worst cell actually measured, and report a lot too small to
   carry a spread as a finding against the design decision itself.

## Pitfalls

- Sizing a generator on the mean. The mean is the centre of the lot, and half
  the cells are below it; a string built on the mean is a string that does not
  make its number.
- Accepting a declared fill factor instead of deriving one. A declared value
  agrees with itself and catches nothing, while a derived one is the only check
  that the four measured quantities describe one curve.
- Taking the lower statistical bound as the answer when it sits above the worst
  measured cell. The bound is an inference about a population; a cell actually
  measured below it is a fact, and the fact wins.
- Reading a cell that just clears a declared minimum by bare arithmetic. The
  power is a product of floats, so a cell built exactly to the limit can land a
  few units in the last place under it; the comparison absorbs that while the
  declared minimum stays as declared.
- Treating a lot of two or three cells as a small lot rather than as no lot. A
  spread computed from three readings is a number, not an estimate, and a
  sizing case resting on it is resting on nothing.

## Behavior contract (gate 3)

The measurement condition window, the maximum power and fill factor
derivations, the impossible peak power pair rejection, the conversion
efficiency, the lot statistics, the design power bound and the short-lot and
duplicate-identifier findings are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_electrical_performance.py against
scripts/e2008_bare_cell_electrical_performance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_electrical_performance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
