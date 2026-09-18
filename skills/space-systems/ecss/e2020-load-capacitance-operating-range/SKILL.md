---
name: e2020-load-capacitance-operating-range
description: "Verify a protected line operates normally at every load capacitance up to the tabulated maximum of its class. Use when ECSS-E-ST-20-20C clause 5.2.19.2.1 asks a design to cover the whole capacitance range rather than one declared part value: derate the declared bulk capacitance for initial tolerance, temperature, ageing and DC bias into a worst-case effective maximum, take the smallest class whose tabulated capacitance covers it, sweep from nothing to that tabulated maximum charging at the lower limiting current, confirm every sample completes inside the shortest trip-off delay with margin, and report the largest capacitance the class can actually start. Refuses a non-ascending class table and a derating that consumes the declaration. Trigger: ecss, e-st-20-20c, lcl-load-capacitance-operating-range, tabulated-maximum-load-capacitance, load-capacitance-derating-stack, inrush-charge-at-tabulated-maximum, startable-load-capacitance, shortest-trip-off-delay."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-load-capacitance-operating-range, tabulated-maximum-load-capacitance, load-capacitance-derating-stack, inrush-charge-at-tabulated-maximum, startable-load-capacitance, shortest-trip-off-delay]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Load Capacitance Operating Range (space-systems/ecss/e2020-load-capacitance-operating-range)

Use when the task is the load-capacitance coverage check of
ECSS-E-ST-20-20C clause 5.2.19.2.1 — showing a protected line operates
normally at every load capacitance value from nothing up to the maximum
the class table tabulates, not merely at the capacitance the load
happens to declare.

## Domain quick reference

- The class table tabulates a MAXIMUM load capacitance, and the clause
  asks for normal operation across the whole span below it. The object
  is therefore a range, and a single value checked against the tabulated
  figure answers only half the question.
- The quantity that has to fit under the tabulated maximum is not the
  part-number capacitance. Initial tolerance, temperature coefficient,
  ageing and the DC bias derating of a ceramic part all move it, and the
  binding value is the worst-case HIGH effective capacitance. The low
  end is worth reporting because it is what the filtering argument
  elsewhere in the design actually gets, but it is not what this clause
  compares.
- Energising a capacitive load is a limitation event by construction.
  While the limiter is limiting, its output is a current source, so the
  capacitance charges linearly and the charge time is C*V/I. The binding
  case is the slowest charge against the earliest opening: the LOWER
  edge of the limiting current band paired with the SHORTEST trip-off
  delay.
- A class has to be able to start its OWN tabulated maximum. A table
  that tabulates more capacitance than the class can charge inside that
  window is a data error, and it surfaces in flight as a unit that will
  not come on rather than as a paper finding.
- Charge time rises with capacitance, so the tabulated maximum is the
  binding sample of the sweep. The sweep is still walked, because it is
  what demonstrates coverage of the range and it shows a reviewer where
  the margin runs out.
- Two rejection reasons are independent and both belong in the report: a
  class whose tabulated maximum does not cover the effective load, and a
  class that cannot charge its own tabulated maximum. A class can fail
  either alone or both together.
- The smallest adequate class wins. Going up a class raises the held
  fault current and usually lengthens the trip-off delay, so an
  oversized limiter pushes more fault energy into the same harness while
  buying nothing.
- The derating contributors, the start-up time margin, the low-usage
  advisory floor and the sweep resolution are declared project policy
  rather than physical constants; the defaults in the logic module are a
  starting point a project substitutes its own values into.

## Workflow

1. Validate the derating set: unique names, a known kind, tolerances
   that are not negative, relative deratings below unity, and no
   two-sided zero entry masquerading as a contributor.
2. Build the effective capacitance range around the declared value,
   keeping the two sides separate. Refuse a downward derating that
   consumes the declaration rather than reporting a non-positive value.
3. Validate the class table: ascending tabulated capacitances, unique
   names, and a positive limiting current and trip-off delay on every
   entry.
4. For each class, sweep from nothing to its tabulated maximum, charge
   each sample at the LOWER limiting current, apply the start-up time
   margin and compare against the SHORTEST trip-off delay.
5. Report the largest capacitance the class can actually start and the
   headroom between that figure and its tabulated maximum. A negative
   headroom is the table contradicting itself.
6. Take the smallest class that both covers the worst-case effective
   capacitance and covers its own tabulated range, and report the
   capacitance headroom and the share of the tabulated figure the load
   consumes.
7. When no class passes, report every reason every class was rejected
   rather than a bare refusal, so the reader sees whether the fix is a
   larger class or a tighter table.
8. Close with a verdict, an advisory when the retained class is heavily
   underused, and an advisory when the range headroom is thin enough
   that a later capacitance growth breaks it.

## Pitfalls

- Comparing the declared part-number capacitance with the tabulated
  maximum. Tolerance, temperature, ageing and DC bias all move it, and
  the value the clause compares is the worst-case high end.
- Checking one capacitance value instead of the range. The clause asks
  for normal operation everywhere below the tabulated maximum, and a
  design that only ever demonstrates its own declared value has not
  shown the class table entry is honest.
- Charging the capacitance at the limiting band midpoint or at its upper
  edge. The limiter is allowed to limit anywhere in the band, so the
  start-up case is the lower edge; a midpoint calculation reports a
  start-up a compliant unit will not deliver.
- Comparing the charge time with the longest trip-off delay. The unit
  may open at the shortest delay in the window, so the comparison is
  against that value, with the margin applied to the charge time rather
  than by relaxing the trip-off figure.
- Assuming a tabulated maximum is achievable. The table is data like any
  other; at a high bus voltage a class can tabulate a capacitance it
  cannot charge in time, and nothing but the arithmetic catches it.
- Treating a bigger class as the safe answer. The upper limiting current
  and the trip-off delay both grow with the class, so oversizing pushes
  more fault energy through the same harness.
- Comparing a charge time or a startable capacitance by bare arithmetic.
  A case meant to sit exactly on the trip-off delay can land a few units
  in the last place the wrong side of it; the comparison absorbs that
  representation error while the tabulated figures stay as declared.

## Behavior contract (gate 3)

The policy validation, derating validation, effective capacitance range,
class table validation, charge time, startable capacitance, range sweep,
per-class assessment, smallest-adequate selection and overall verdict
are exercised by the gate 3 contract test:
scripts/test_e2020_load_capacitance_operating_range.py against
scripts/e2020_load_capacitance_operating_range_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_load_capacitance_operating_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
