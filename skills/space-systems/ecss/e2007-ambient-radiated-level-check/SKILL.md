---
name: e2007-ambient-radiated-level-check
description: "Use when verify the ambient radiated-emission background of an EMC facility under ECSS-E-ST-20-07C clause 5.2.2.3: confirm the baseline run had the unit-under-test unpowered while the support-equipment stayed operating behind a closed enclosure door, sweep the recorded ambient-noise-floor against the applicable radiated-emission-limit, categorize every frequency as compliant, marginal or exceeding once the required headroom is applied, flag narrowband ambient signals that must be documented, check the swept band for coverage gaps, and decide whether a later measured level is attributable to the unit or is ambient-limited. Trigger: ecss, e-st-20-07c, ambient-radiated-level, background-noise-floor, eut-off-baseline, support-equipment-operating, radiated-emission-limit-headroom, narrowband-ambient-signal, emc-facility-baseline."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-ambient-radiated-level-check, ambient-radiated-level, background-noise-floor, eut-off-baseline, radiated-emission-limit-headroom, narrowband-ambient-signal, emc-facility-baseline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC Facility — Ambient Radiated-Level Check (space-systems/ecss/e2007-ambient-radiated-level-check)

Use when the task is the ambient radiated background baseline of
ECSS-E-ST-20-07C clause 5.2.2.3 -- recording and grading the
radiated-emission floor of the facility with the unit-under-test
unpowered and the support-equipment running, so that every later
emission reading can be attributed to the unit rather than to the
room.

## Domain quick reference

- The ambient run is not "the empty room". The unit-under-test is
  unpowered, but the support-equipment, harness, stimulation gear and
  facility services stay in exactly the configuration the graded run
  will use, with the enclosure door closed. An ambient run taken with
  the support-equipment switched off understates the floor and
  invalidates every later attribution.
- The ambient sweep must reuse the graded run's measurement settings:
  same antenna polarization, same standoff, same receiver bandwidth.
  A narrower receiver bandwidth lowers the apparent floor without
  lowering the real one, so a mismatched bandwidth is a defect in the
  baseline, not a favourable result.
- Grading is by headroom, the difference between the applicable
  radiated-emission-limit and the recorded ambient level at that
  frequency. A required headroom (conventionally 6 dB) separates a
  usable baseline from one where the room itself is close enough to
  the limit that a compliant unit could still read as failing.
  Headroom at or above the requirement is compliant; positive but
  short of it is marginal and must be recorded as a limitation;
  headroom at or below zero is an ambient exceedance and the
  frequency cannot be graded at that facility until it is resolved.
- A narrowband ambient signal is a discrete peak that stands well
  above its local neighbourhood -- a broadcast carrier, a local
  oscillator, a nearby transmitter. Clause 5.2.2.3 practice allows a
  known narrowband ambient to be documented and carried, provided it
  is identified and shown not to originate from the unit; a broadband
  floor that is simply high cannot be carried this way.
- Coverage matters as much as level. The recorded points must span
  the whole declared band, and consecutive points must not step
  further apart than the declared maximum ratio, otherwise a narrow
  ambient peak can hide between two samples.
- Attribution rules a later graded reading: a measured level well
  above the ambient is dominated by the unit, a measured level equal
  to the ambient is ambient-limited and carries no information about
  the unit, and the band between them is indeterminate -- the reading
  proves neither compliance nor a finding.

## Workflow

1. Validate the baseline configuration: unit-under-test unpowered,
   support-equipment powered, enclosure door closed, receiver
   bandwidth positive and matching the graded run, recognized antenna
   polarization, positive standoff. Reject the run rather than grading
   a configuration that cannot support attribution.
2. Validate the sweep: at least one point, strictly increasing
   frequencies, positive frequencies, an ambient level and an
   applicable limit at every point.
3. For each point compute headroom = limit - ambient, and categorize
   it as compliant, marginal or exceedance against the required
   headroom. Absorb representation error at the boundary with a
   named decibel tolerance; never lower the required headroom to make
   a boundary point pass.
4. Identify narrowband ambient peaks by comparing each interior point
   against its two neighbours; report them for documentation.
5. Check band coverage: first point at or below the band start, last
   point at or above the band stop, and no step ratio above the
   declared maximum.
6. Aggregate: the worst-case frequency, the counts per category, the
   coverage gaps, and a verdict that is usable only when no exceedance
   and no coverage gap remains.
7. When grading a later reading, apply the attribution rule to the
   measured/ambient pair before drawing any conclusion from it.

## Pitfalls

- Running the ambient sweep with the support-equipment off because
  "only the unit matters" -- the resulting floor is not the floor the
  graded run will see.
- Reading "ambient below the limit" as a usable baseline. Below the
  limit but inside the required headroom is a marginal frequency and
  has to be carried as a limitation on the measurement.
- Grading a reading that sits on top of the ambient. An emission equal
  to the ambient is ambient-limited; reporting it as a unit emission
  invents a finding, and reporting it as a pass invents compliance.
- Sampling coarsely and declaring the band clean. A narrowband carrier
  between two widely spaced points is invisible to the sweep and will
  reappear in the graded run.
- Narrowing the receiver bandwidth for the ambient run only. The floor
  drops, the graded run does not, and every later comparison is wrong.

## Behavior contract (gate 3)

The configuration-validation, headroom-categorization, narrowband
identification, coverage and attribution logic is exercised by the
gate 3 contract test:
scripts/test_e2007_ambient_radiated_level_check.py against
scripts/e2007_ambient_radiated_level_check_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2007_ambient_radiated_level_check.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
