---
name: e2020-lcl-class-selection
description: "Determine which latching current limiter class a protected load belongs on. Use when an ECSS-E-ST-20-20C clause 5.2.1.1.1 power-distribution design has to take an LCL class from the project class table and show the associated performance figures are met: derate each class continuous rating, keep the classes that carry the steady load, charge the load capacitance at the worst-case lower limiting current and check the charge completes inside the shortest trip-off delay, confirm the upper limiting current sits under the protected harness rating, then take the smallest passing class and report its utilisation, start-up and harness margins. Refuses a non-ascending class table, an inverted limiting band and a limiting band that would trip at its own continuous rating. Trigger: ecss, e-st-20-20c, lcl-class-selection, latching-current-limiter, lcl-limiting-current-band, lcl-trip-off-time, lcl-inrush-charge-time, lcl-derated-capability, protected-harness-rating."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-lcl-class-selection, latching-current-limiter, lcl-limiting-current-band, lcl-trip-off-time, lcl-inrush-charge-time, lcl-derated-capability, protected-harness-rating]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — LCL Class Selection (space-systems/ecss/e2020-lcl-class-selection)

Use when the task is the latching-current-limiter class choice of
ECSS-E-ST-20-20C clause 5.2.1.1.1 — taking one class out of the
standard's class table for a given protected load and demonstrating that
the performance figures attached to that class are actually met by the
load it is being asked to feed.

## Domain quick reference

- An LCL sits between a regulated bus and one load. In normal operation
  it is a closed switch; when the load draws too much it holds its
  output inside a limiting current band, and after a trip-off delay it
  opens and stays open until commanded back on. That is why the class is
  a table entry and not a free parameter: each class ships with a
  continuous rating, a limiting band and a trip-off window that were
  qualified together.
- The four figures a class selection is graded against are the highest
  steady current the class carries without entering limitation, the
  lower and upper edges of the limiting current band, and the shortest
  and longest trip-off delay. All four enter the decision; picking on
  the continuous rating alone is the common defect.
- Energising a capacitive load is a limitation event by construction.
  While the limiter is limiting, the output is a current source, so the
  load capacitance charges linearly and the charge time is C*V/I. The
  binding case is the slowest charge against the earliest trip: the
  LOWER edge of the limiting band paired with the SHORTEST trip-off
  delay. Using the band midpoint or the nominal trip time hides a unit
  that will refuse to start.
- The UPPER edge of the limiting band is the fault current the harness,
  the connector pins and the load see for the whole trip-off delay, so
  the class only protects the hardware downstream when that upper edge
  sits under the harness rating. A class that carries the load
  comfortably can still fail this check.
- The smallest adequate class wins. Going up a class raises the held
  fault current and usually lengthens the trip-off delay, so an
  oversized limiter delivers more fault energy into the same harness
  while buying nothing.
- Derating factor, start-up time margin and the low-utilisation
  advisory floor are declared project policy rather than physical
  constants; the defaults in the logic module are a starting point a
  project substitutes its own values into.

## Workflow

1. Validate the class table: ascending continuous ratings, unique
   names, a limiting band that is the right way up and that sits above
   the class's own continuous rating, and a trip-off window that is not
   inverted. A table that trips at its own rating is a data error, not a
   conservative entry.
2. Validate the load: steady-state current, load capacitance, bus
   voltage and the rating of the harness being protected. A load with no
   declared capacitance cannot be assessed for start-up, so it is
   refused rather than assumed to be resistive.
3. Derate each class continuous rating by the project factor and keep
   the classes whose derated capability covers the steady load.
4. For each class, charge the load capacitance at the LOWER limiting
   current, apply the start-up time margin, and compare against the
   SHORTEST trip-off delay. A class that cannot finish the charge in
   time is rejected however well it carries the steady load.
5. Compare the UPPER limiting current against the harness rating and
   reject any class whose fault current the harness cannot survive.
6. Take the smallest class that passes all three checks, and report its
   utilisation, its start-up slack in seconds and its harness slack in
   amperes so a reviewer sees which check is nearest its edge.
7. Raise an advisory, not a finding, when the retained class is heavily
   oversized for the load; and when no class passes, report every reason
   each class was rejected rather than a bare refusal.

## Pitfalls

- Picking the class on the continuous rating alone. The rating answers
  only whether the load can be carried; the limiting band and the
  trip-off window decide whether the load can be started and whether the
  harness survives a fault, and either can force a different class.
- Charging the load capacitance at the limiting band midpoint or at its
  upper edge. The limiter is allowed to limit anywhere in the band, so
  the start-up case is the lower edge; a midpoint calculation reports a
  start-up that a compliant unit will not deliver.
- Comparing the charge time with the longest trip-off delay. The unit
  may open at the shortest delay in the window, so the comparison is
  against that value, with the margin applied to the charge time rather
  than by relaxing the trip-off figure.
- Treating a bigger class as the safe answer. The upper limiting
  current and the trip-off delay both grow with the class, so oversizing
  pushes more fault energy through the same harness and can turn a
  passing harness check into a failing one.
- Comparing a charge time or a derated capability by bare arithmetic. A
  case meant to sit exactly on the derated capability or exactly on the
  trip-off delay can land a few units in the last place the wrong side
  of the bound; the comparison absorbs that representation error while
  the derating and the trip-off figure stay as specified.

## Behavior contract (gate 3)

The class-table validation, load validation, derating, inrush charge
time, harness comparison, per-class assessment and smallest-adequate
selection are exercised by the gate 3 contract test:
scripts/test_e2020_lcl_class_selection.py against
scripts/e2020_lcl_class_selection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2020_lcl_class_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
