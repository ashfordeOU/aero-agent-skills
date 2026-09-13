---
name: e2008-humidity-test-execution
description: "Use when audit the chamber run of a photovoltaic assembly humidity test, in which the specimen is held in a humidity chamber at ambient pressure for the defined duration, under ECSS-E-ST-20-08C clause 5.5.1.4.4: validate the time-ordered chamber log, walk consecutive samples, credit an interval to the conditioned dwell only when both endpoints sit inside the humidity, temperature and ambient-pressure bands, accumulate the cumulative and longest excursions separately from the time spent away from ambient pressure, and compare the accounting with the defined duration and the agreed excursion limits. Trigger: ecss, e-st-20-08c, humidity-chamber-dwell-accounting, ambient-pressure-hold, damp-heat-chamber-log, control-excursion-limit, photovoltaic-assembly-humidity-run, conditioned-dwell-duration."
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
  tags: [ecss, e-st-20-08-photovoltaic-scope, e2008-humidity-test-execution, humidity-chamber-dwell-accounting, ambient-pressure-hold, damp-heat-chamber-log, control-excursion-limit, conditioned-dwell-duration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Humidity Test — Test Execution (space-systems/ecss/e2008-humidity-test-execution)

Use when the task is the chamber-run step of the humidity test of
ECSS-E-ST-20-08C clause 5.5.1.4.4 — deciding from the chamber log whether a
photovoltaic assembly specimen was actually held inside the humidity chamber,
at ambient pressure, for the duration the test specification defines.

## Domain quick reference

- Duration is a conditioned dwell, not a wall-clock span. What the specimen
  accumulates is time spent inside the humidity band, inside the temperature
  band and at ambient pressure simultaneously; the difference between the log
  span and the conditioned dwell is exactly the control the chamber lost.
- Sampling makes the accounting interval-based. Between two logged samples the
  chamber state is unknown, so an interval is credited only when both of its
  endpoints are in band. A single bad sample therefore voids the interval
  before it and the interval after it, which is the conservative reading and
  the reason a slow sampling rate costs dwell.
- Ambient pressure is a stated condition of this run, not a chamber detail. A
  chamber that partly evacuates turns a damp-heat exposure into a different
  environment, so pressure departures are accumulated and reported in their own
  right even when humidity and temperature never left their bands.
- Two excursion limits do different jobs. The longest single excursion says
  whether the specimen dried out and re-wetted, which is its own damage
  mechanism; the cumulative excursion says how much of the exposure was simply
  not delivered. A run can satisfy one and break the other.
- The band edges are part of the band. A set point sitting exactly on the
  tolerance limit is a control success, so edge membership is inclusive and the
  comparison absorbs representation error rather than moving the limit.

## Workflow

1. Validate the chamber log: at least two samples, strictly increasing time
   stamps, each carrying a relative humidity within saturation, an air
   temperature and a positive pressure. A repeated time stamp is an input
   error, not a zero-length interval.
2. Validate the three control bands and refuse an inverted one. The ambient
   pressure band defaults to the laboratory band and is overridden explicitly
   for a chamber at altitude.
3. Walk consecutive samples. Credit the interval to the conditioned dwell when
   both endpoints are inside all three bands; otherwise open or extend an
   excursion run.
4. Accumulate in parallel the time either endpoint spent outside the ambient
   pressure band, so a pressure loss is visible even when it coincides with an
   in-band humidity reading.
5. Close the final excursion run when the log ends inside one, so a run that
   finishes out of control is not silently dropped.
6. Compare the conditioned dwell with the defined duration, and the longest and
   cumulative excursions with their agreed limits, absorbing floating-point
   representation error at each boundary with a named tolerance.
7. Report the accounting — dwell, excursion time, longest excursion, excursion
   count, pressure-excursion time, sample count and log span — together with
   every finding.

## Pitfalls

- Reading the duration off the first and last time stamp. That is the log span;
  it counts the excursions as exposure and overstates what the specimen saw.
- Crediting the interval on one good endpoint. The chamber state between
  samples is not observed, so a half-credited interval is an assumption; both
  endpoints have to be in band.
- Folding the pressure check into the humidity check and reporting one number.
  A chamber that lost pressure while holding humidity produces no humidity
  finding at all, and the run silently stops being the test that was specified.
- Summing excursion time and calling it the worst excursion. Ten short dips and
  one long one give the same cumulative figure and mean different things to the
  specimen, so both are accumulated.
- Ending the walk without closing an open excursion run. A run that ends out of
  control then reports its longest excursion as whatever preceded it.
- Treating a reading exactly on a tolerance limit as an excursion. Band edges
  are inclusive; widening the band to make the run pass is the wrong fix, and
  the tolerance belongs inside the comparison.

## Behavior contract (gate 3)

The log and band validation, band membership, interval crediting, excursion
run accounting, ambient-pressure accounting and the comparison with the defined
duration and the excursion limits are exercised by the gate 3 contract test:
scripts/test_e2008_humidity_test_execution.py against
scripts/e2008_humidity_test_execution_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e2008_humidity_test_execution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
