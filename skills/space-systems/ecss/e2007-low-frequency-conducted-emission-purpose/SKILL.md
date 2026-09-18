---
name: e2007-low-frequency-conducted-emission-purpose
description: "Evaluate whether a low-frequency conducted-emission test plan serves the aim of ECSS-E-ST-20-07C clause 5.4.2.1. Use when the task is judging a plan against the purpose rather than a limit: confirming the sweep spans the low part of the spectrum, that every power supply lead and every matching return lead carries a sensor, that the method senses lead current rather than a terminal voltage, that a limit line exists to compare against, and quantifying the swept share of the aim band in the logarithmic domain. Trigger: ecss, e-st-20-07c, low-frequency-conducted-emission, power-lead-emission-sweep, return-lead-instrumentation, conducted-emission-current-probe, conducted-emission-limit-line, emission-band-coverage-decades."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-low-frequency-conducted-emission-purpose, low-frequency-conducted-emission, power-lead-emission-sweep, return-lead-instrumentation, conducted-emission-current-probe, emission-band-coverage-decades]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Low-Frequency Conducted Emission Purpose (space-systems/ecss/e2007-low-frequency-conducted-emission-purpose)

Use when the task is the aim of the low-frequency conducted-emission
measurement in ECSS-E-ST-20-07C clause 5.4.2.1 -- deciding whether a
proposed test plan actually produces the evidence the clause exists to
obtain, before anybody argues about a limit line.

## Domain quick reference

- The clause states an aim, not a limit, and the distinction matters.
  It says what the measurement is for: bounding the interference a unit
  pushes back onto the leads that feed it, low in the spectrum, where
  the power distribution rather than free space is the coupling path.
  A plan can run flawlessly, produce a clean sweep and satisfy nobody,
  because it measured the wrong leads over the wrong span.
- Supply leads and return leads are both named, and the returns are the
  half that gets dropped. A sensor on the supply lead alone sees the
  sum of the differential and common-mode contributions with no way to
  separate them; the return lead carries the differential current back
  and the common-mode current onward, and only the pair distinguishes
  the two. A plan that probes the supply leads and stops has not halved
  its coverage, it has removed the ability to attribute anything it
  measured.
- The quantity is a lead current, not a terminal voltage. A probe
  clamped around the lead reads the current the unit actually injects
  whatever the bus impedance turns out to be; a voltage measured at the
  terminals is that current times an impedance nobody controls, so it
  changes when the harness changes and characterizes the setup rather
  than the unit.
- The span is low-frequency and it is wide -- several decades, not a
  narrow window. Coverage is therefore worked in the logarithmic
  domain: a plan starting a decade late has lost a large share of the
  aim's band even though the linear frequency it skipped looks
  negligible next to the top of the sweep.
- A measurement with no limit line on record is a number. The aim is to
  produce evidence against a bound, so the bound is part of the plan,
  not something located afterwards when the data looks inconvenient.

## Workflow

1. Validate the plan: identifier, sweep start and stop, sensing
   method, supply leads, return leads, instrumented leads, limit-line
   flag. Reject a non-positive start, a stop at or below the start, an
   unknown method, an empty lead list, a lead named as both a supply
   and a return, a repeated lead, or a sensor on a lead the unit does
   not have.
2. Work out which supply leads and which return leads are left without
   a sensor, and keep the two lists separate -- a plan missing its
   returns is a different defect from one missing everything.
3. Decide whether the sweep reaches both edges of the aim's band,
   comparing against the edges with a relative tolerance so a plan
   written to the exact edge frequency is not failed by the last place
   of a float.
4. Quantify the swept share of the aim band: clip the sweep to the band
   at both ends, take the decades of the overlap over the decades of
   the band, and return zero when a sweep sits wholly outside.
5. Grade the five objectives of the aim -- supply leads, return leads,
   band span, limit line, current sensing -- and report the unserved
   ones in a fixed order so two reviews of one plan read alike.
6. Aggregate over a plan set: mean band coverage, the plans that miss
   the aim by name, and a set-level verdict that is positive only when
   every plan serves every objective.

## Pitfalls

- Reading a purpose clause as having nothing to check. It is the
  clause that decides whether the rest of the test was worth running,
  and a plan can fail it while passing every procedural requirement.
- Instrumenting the supply leads and treating the returns as implied.
  The return is where the common-mode share separates from the
  differential share, and without it the sweep cannot be attributed.
- Measuring a terminal voltage and calling it a conducted emission. It
  is the injected current times whatever impedance the bench presented,
  and it moves when the bench does.
- Judging band coverage linearly. Over several decades a linear share
  is dominated by the top of the sweep, so a plan that skipped the
  bottom decade scores as nearly complete.
- Deferring the limit line. A sweep with no bound to compare against
  cannot conclude anything, and choosing the bound after seeing the
  data is not a comparison.

## Behavior contract (gate 3)

The plan-validation, lead-coverage, band-span, log-domain
coverage-fraction, objective-grading and set-aggregation logic is
exercised by the gate 3 contract test:
scripts/test_e2007_low_frequency_conducted_emission_purpose.py against
scripts/e2007_low_frequency_conducted_emission_purpose_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_low_frequency_conducted_emission_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
