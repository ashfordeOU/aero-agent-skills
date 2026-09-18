---
name: e2020-filter-charge-versus-trip-margin
description: "Verify that a load filter finishes charging well inside the shortest trip time a limiter can produce, per ECSS-E-ST-20C clause 5.4.2.3.1. Use when the separation has to be evaluated at the corner that actually binds rather than at the schematic numbers: raise the filter capacitance by tolerance and end-of-life drift, drop the limitation current to the bottom of its band, take the bus at its upper voltage, form the constant-current charge time, shorten the fastest trip time by its own tolerance, and compare the two against the required factor at inclusive equality. Trigger: ecss, e-st-20-electrical-scope, filter-charge-versus-trip-margin, worst-case-filter-capacitance, limitation-current-derating, constant-current-charge-time, shortest-trip-time-corner, charge-to-trip-separation-factor."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-filter-charge-versus-trip-margin, worst-case-filter-capacitance, limitation-current-derating, constant-current-charge-time, shortest-trip-time-corner, charge-to-trip-separation-factor, switch-on-inrush-nuisance-trip]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Filter Charge Versus Trip Margin (space-systems/ecss/e2020-filter-charge-versus-trip-margin)

Use when the task is the switch-on separation requirement of
ECSS-E-ST-20C clause 5.4.2.3.1 -- showing that charging the load's input
filter finishes comfortably inside the shortest trip time the limiter
can produce, so a healthy load starts rather than tripping its own
protection on the way up.

## Domain quick reference

- The first thing a switched-on output does is charge the load's input
  filter. The limiter holds that inrush at its limitation current, so
  the filter charges at very nearly constant current and takes a time
  set by the charge it needs and the current it is allowed to draw.
- The requirement is a separation, not a race. Charging has to clear
  the shortest trip time by a declared factor; finishing a hair inside
  the trip is a design with no room in it, and the factor exists
  because the spread is real.
- Four governing numbers all move the wrong way at once. The filter
  capacitance is taken high, because parts are bought to a tolerance
  and drift over life. The limitation current is taken low, because the
  slowest charge happens at the bottom of its band. The bus voltage is
  taken high, because the filter is charged to the bus. The trip time
  is taken short, because the limiter's fastest trip is the one the
  separation is owed against.
- The trip time comes from a family, not from a single row. The fastest
  of the declared trips governs, with its own tolerance taken off it.
- A nominal-only result is an advisory, not a pass. The schematic
  numbers produce a comfortable separation for units that trip on
  switch-on at the corner, and that is exactly the failure this clause
  exists to prevent.
- The comparison is inclusive. A separation landing exactly on the
  required factor meets the requirement, and the tolerance absorbs
  representation error rather than relaxing the factor.

## Workflow

1. Read the filter capacitance, the limitation current, the bus
   voltage, the declared trip times and the required factor. Any one of
   them missing closes the assessment on that gap rather than on a
   guess.
2. Build the nominal set from the schematic numbers, with no allowance
   applied to any of them.
3. Build the corner set: capacitance raised by tolerance and drift,
   limitation current derated, bus voltage taken at its upper end,
   fastest trip time shortened by its tolerance.
4. For each set, form the constant-current charge time and divide the
   trip time by it to get the separation actually achieved.
5. Compare each separation with the required factor at inclusive
   equality and carry the surplus as a fraction of the factor.
6. Report the corner verdict, and where the corner misses while the
   nominal clears, say so explicitly. Advise on a thin corner pass, a
   missing drift allowance, or a factor that asks for no separation at
   all.

## Pitfalls

- Running the case at nominal. It is the quickest way to close this
  clause on a unit that will not start at the cold end of the bus with
  an aged filter.
- Taking the capacitance off the schematic. Tolerance and end-of-life
  drift both add charge, and a case with no drift allowance is a
  beginning-of-life case wearing a worst-case label.
- Using the limitation current at its nominal. The slow charge is at
  the bottom of the band, and that is the only end that matters here.
- Comparing against a typical trip time. The separation is owed against
  the fastest trip the limiter can produce, tolerance included; a
  mid-family row gives a margin the hardware never promised.
- Setting a required factor of one. Charging is then only asked to
  finish before the trip rather than well before it, and the corner
  spread the analysis exists to cover has nowhere to go.
- Comparing a separation with the factor by bare arithmetic. The
  separation comes out of two divisions, so a case sitting exactly on
  the factor can fall a few units in the last place short; the
  comparison absorbs that representation error while the declared
  factor stays untouched.

## Behavior contract (gate 3)

The capacitance, current, voltage and trip-time corner construction,
the constant-current charge time, the separation ratio, the inclusive
factor comparison, the nominal-versus-corner split and the thin-pass
and missing-drift advisories are exercised by the gate 3 contract test:
scripts/test_e2020_filter_charge_versus_trip_margin.py against
scripts/e2020_filter_charge_versus_trip_margin_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_filter_charge_versus_trip_margin.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
