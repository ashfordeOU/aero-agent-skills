---
name: e2008-solar-simulator-calibration-maintenance
description: "Use when a simulator's upkeep record must be shown before an array measurement is accepted. Assess whether a solar simulator is still fit for measurement under ECSS-E-ST-20-08C clause 10.2.6, where routine calibration and upkeep keep the beam usable: grade the spatial non-uniformity, the temporal instability and the spectral match band by band, take the worst of the three as the beam grade, weigh lamp hours run against the rated life and days elapsed since the reference-cell setting, then settle one verdict - fit, conditional, recalibrate or service - against the grade the planned measurement demands. Trigger: ecss, e-st-20-electrical-scope, e-st-20-08c, solar-simulator-calibration-maintenance, simulator-spatial-non-uniformity-grade, simulator-temporal-instability-grade, simulator-spectral-match-band, simulator-lamp-service-hours, simulator-reference-cell-interval."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-solar-simulator-calibration-maintenance, simulator-spatial-non-uniformity-grade, simulator-temporal-instability-grade, simulator-spectral-match-band, simulator-lamp-service-hours, simulator-reference-cell-interval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Array — Solar Simulator Calibration Maintenance (space-systems/ecss/e2008-solar-simulator-calibration-maintenance)

Use when the task is clause 10.2.6 of ECSS-E-ST-20-08C -- the routine
calibration and upkeep that keep a solar simulator fit to measure a
solar-array assembly. The simulator is measuring equipment, not a lamp
in a room: the number it hands back is worth exactly what its last
upkeep says it is, and a beam that has quietly degraded produces
plausible currents that are simply wrong.

## Domain quick reference

- Three beam qualities decide whether the simulator can stand in for
  sunlight at all. Spatial non-uniformity says how far the irradiance
  varies across the test plane. Temporal instability says how far it
  moves while a measurement is taken. Spectral match says how far the
  irradiance in each wavelength band departs from the reference
  spectrum.
- Each quality earns a grade from its bounds, and the simulator takes
  the worst of the three. A beam that is uniform and steady but
  spectrally wrong is a spectrally wrong beam: averaging the three
  would hide exactly the quality that biases a multijunction cell.
- Spectral match is graded band by band, and the worst band wins for
  the same reason. A single band far out of window mismeasures the
  subcell that band feeds, whatever the others do.
- Two upkeep counters sit alongside. Lamp hours run against the rated
  life govern when the source is replaced; days elapsed since the beam
  was set against a reference cell govern when the irradiance level is
  re-established.
- The measurement demands a grade of its own. A simulator that does not
  reach it is not broken -- it is usable for the work its own grade
  supports and no further, which is a different finding from a beam
  outside every bound.
- Precedence: a lamp past its rated life or a quality outside every
  bound is a service finding and outranks a calibration that has merely
  gone out of date, because setting the level of a dying beam
  accomplishes nothing.

## Workflow

1. Declare the grade the planned measurement demands, and reject an
   undeclared one rather than assuming the finest.
2. Grade the spatial non-uniformity and the temporal instability
   against their percentage bounds, letting a value sitting exactly on
   a bound keep the better grade.
3. Grade the spectral match band by band against the ratio window for
   each grade, and carry the worst band forward.
4. Take the worst of the three qualities as the beam grade, and record
   the per-quality and per-band detail so the limiting quality is named
   rather than inferred.
5. Place the lamp hours inside the rated life and the elapsed days
   inside the calibration interval, each with its own warning fraction,
   honouring a project value over the default wherever one is given.
6. Rank the findings into one verdict -- service required,
   recalibration required, conditional use, or fit for measurement --
   and state plainly whether a measurement taken now would be accepted.

## Pitfalls

- Averaging the three beam qualities into one figure of merit. The
  worst quality is what biases the result, and an average lets two good
  numbers bury the one that matters.
- Grading spectral match on a whole-band integral. The integral can sit
  comfortably in window while one band is far out, and it is that band
  which mismeasures the subcell it feeds.
- Treating a lamp-hour counter as a maintenance nicety. Output and
  spectrum both move over a lamp's life, so hours run is a direct input
  to whether the last calibration still describes the beam.
- Recalibrating a simulator whose lamp is already past its rated life.
  The new setting describes a source that is still degrading, so the
  service finding has to be cleared first.
- Reading a beam that misses the required grade as unusable. It remains
  usable for work its own grade supports; conflating that with a beam
  outside every bound throws away serviceable equipment.
- Comparing a quality against a grade bound by bare arithmetic. A value
  landing exactly on a bound can fall a few units in the last place
  either side of it, so the comparison absorbs that representation
  error while the bound itself stays untouched.

## Behavior contract (gate 3)

The per-quality grading, band-by-band spectral grading, worst-quality
rollup, lamp-life and calibration-interval placement, requirement
comparison and verdict precedence are exercised by the gate 3 contract
test: scripts/test_e2008_solar_simulator_calibration_maintenance.py
against scripts/e2008_solar_simulator_calibration_maintenance_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2008_solar_simulator_calibration_maintenance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
