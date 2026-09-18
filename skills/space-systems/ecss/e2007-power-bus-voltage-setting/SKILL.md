---
name: e2007-power-bus-voltage-setting
description: "Determine which power-bus voltage extreme governs a conducted emission measurement, anchored at ECSS-E-ST-20-07C clause 5.2.12: align the sweeps recorded at the lower and the upper supply setting on one frequency grid, take the worst level at every frequency and the setting that produced it, rank the settings by the largest exceedance each reaches above the declared limit line, and refuse a campaign that exercised a single extreme, that ran at neither, or that reported a setting other than the governing one. Use when planning, auditing or accepting a conducted emission run. Trigger: ecss, e-st-20-07c, power-bus-voltage-setting, conducted-emission-voltage-extreme, worst-case-supply-setting, bus-voltage-emission-envelope, emission-limit-line-exceedance, emission-sweep-grid-alignment."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-power-bus-voltage-setting, conducted-emission-voltage-extreme, worst-case-supply-setting, bus-voltage-emission-envelope, emission-limit-line-exceedance, emission-sweep-grid-alignment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Power Bus Voltage Setting (space-systems/ecss/e2007-power-bus-voltage-setting)

Use when the task is the supply-setting rule of ECSS-E-ST-20-07C clause
5.2.12 -- a conducted emission measurement is performed at the bus
voltage extreme that produces the worst result, which means both
extremes have to be recorded before the governing one can be named.

## Domain quick reference

- The quantity that decides the setting is the emission, not the
  voltage. A switching converter can emit more at the low extreme,
  where it draws more current and its duty cycle lengthens, or at the
  high extreme, where switching transitions are faster and harmonics
  reach further up the band. Which one wins is a property of the unit
  and is settled by measurement, not by assumption.
- Both extremes have to be exercised. A campaign that recorded one of
  them has no basis on which to call it the worst, and a run held at
  the nominal bus voltage is not a substitute for either.
- The comparison is point by point on one frequency grid. Two sweeps
  taken on different grids cannot be compared without inventing values
  between the points, so a grid mismatch is an input error and not
  something to interpolate past.
- The envelope is the per-frequency worst level with the setting that
  produced it attached. When one setting holds every point, that
  setting governs and one run can be reported. When the settings cross,
  no single run is the worst result and the reported spectrum is the
  envelope of both.
- Ranking the settings against a limit line is not the same as ranking
  them on absolute level. A limit that falls with frequency can make a
  quieter run the closer one to the limit, and the setting that matters
  is the one with the largest exceedance, not the largest amplitude.
- An exactly equal pair of levels is a tie, not a winner. Ties are
  resolved on the lower voltage so two analysts reach the same answer,
  and the decibel comparison absorbs representation error rather than
  nudging a level.

## Workflow

1. Validate the declared supply extremes: both positive, and the upper
   genuinely above the lower.
2. Normalize each run: the setting label, the bus voltage it was held
   at, and its sweep. Reject an unknown key, a blank label, a
   duplicated label, a sweep of fewer than two points and a sweep that
   does not advance in frequency.
3. Establish the common frequency grid across the runs and refuse a
   mismatch in point count or in any frequency.
4. Build the envelope: the worst level at every frequency, the setting
   that produced it, and that setting's voltage, ties going to the
   lower voltage.
5. Compute per run the largest absolute level, the largest exceedance
   above the limit line when one is declared, and the number of
   frequencies at which the run holds the envelope.
6. Rank the settings on exceedance, or on absolute level when no limit
   line was declared, breaking ties on envelope coverage and then on
   the lower voltage.
7. Report findings: an extreme never exercised, a run at neither
   extreme, a governing setting that is not worst everywhere, a
   reported setting other than the governing one, and any envelope
   point above the limit.

## Pitfalls

- Deciding the extreme from the circuit rather than from the data.
  Whether the low or the high extreme emits more depends on the
  converter topology and the load, and the clause asks for the worst
  measured result.
- Running the nominal bus voltage and treating it as a middle case that
  covers the extremes. It bounds neither, and an emission peak at an
  extreme can be tens of decibels above it.
- Comparing sweeps taken on different resolution grids by interpolating
  one onto the other, which invents the very points a narrowband
  emission hides between.
- Reporting the run with the highest absolute level when a sloping
  limit line means the other setting is the one closest to breaching.
- Reporting a single setting when the two runs cross. The worst result
  is then the envelope, and reporting either run alone understates the
  emission somewhere in the band.
- Breaking a tie by whichever run was processed first. Ties are
  resolved on the lower voltage so the selection is reproducible, and
  the level comparison absorbs representation error instead of moving
  the limit.

## Behavior contract (gate 3)

The extreme validation, sweep normalization, grid alignment, limit-line
interpolation, envelope construction, per-run statistics, governing
selection and campaign findings are exercised by the gate 3 contract
test: scripts/test_e2007_power_bus_voltage_setting.py against
scripts/e2007_power_bus_voltage_setting_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_power_bus_voltage_setting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
