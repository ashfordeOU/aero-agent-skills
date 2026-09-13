---
name: e2001-emission-yield-measurement-justification
description: "Use when determine whether an existing secondary-electron-emission-yield measurement may still be reused for a multipaction-critical gap under ECSS-E-ST-20-01C clause 9.2, or whether a fresh sample must be measured: compare the sample-provenance record behind the existing measurement against the as-built record of the gap, categorize every difference as yield-affecting (base-material substitution, surface-finish change, coating-process or plating-bath change, cleaning-route change, altered manufacturing-route) or administrative, confirm the gap is multipaction-critical from its frequency-gap product and design-margin, check the held measurement record is still within validity and covers the needed primary-electron-energy span, and emit a reuse-justification or a remeasurement demand. Trigger: ecss, e-st-20-01c, secondary-electron-emission-yield, sample-provenance, multipaction-critical-gap, yield-measurement-justification, coating-process-change, remeasurement-trigger."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-emission-yield-measurement-justification, secondary-electron-emission-yield, sample-provenance, multipaction-critical-gap, yield-measurement-justification, remeasurement-trigger]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Emission-Yield Measurement Justification (space-systems/ecss/e2001-emission-yield-measurement-justification)

Use when the task is the clause 9.2 justification of ECSS-E-ST-20-01C:
deciding whether a held secondary-electron-emission-yield measurement
still represents the emitting surface of a multipaction-critical gap,
or whether the material or the manufacturing route of that gap has
moved far enough that a fresh sample has to be measured.

## Domain quick reference

- The yield curve used in a multipaction assessment is a property of
  the *emitting surface*, not of the part number. It is set by the
  base material, by whatever sits on top of it (coating, plating,
  conversion layer), by the surface finish, and by the cleaning route
  that leaves the last few atomic layers behind. A change to any of
  those is yield-affecting and invalidates the reuse argument. A
  change to a lot identifier, a drawing revision, an operator or a
  supplier order reference is administrative: it is recorded, it does
  not by itself demand a new measurement.
- The demand only bites on a gap that is multipaction-critical. Two
  things make it so: the frequency-gap product (carrier frequency in
  GHz times the gap in mm) falls inside the susceptibility band where
  electron transit time can synchronise with the RF period, and the
  design-margin held over the predicted onset is below the threshold
  the project set. A gap outside the band, or carrying margin at or
  above the threshold, is not critical and the clause 9.2 trigger does
  not fire for it, though the difference is still recorded. A gap the
  project has explicitly declared critical stays critical whatever the
  numbers say.
- Reuse also needs the held record itself to be sound: measured on an
  identified facility and instrument, with the surface conditioning
  stated (as-received, baked-out, electron-conditioned), inside its
  validity window, and spanning the primary-electron-energy range the
  assessment reads back. A record that has aged out, hides its
  conditioning, or stops short of the needed energy span cannot carry
  a reuse argument even when nothing about the surface changed.
- The output of the clause is a decision plus its drivers, not a bare
  yes/no: the reuse-justification names the attributes that were
  compared and found equal, and the remeasurement demand names the
  attribute changes and record defects that forced it.

## Workflow

1. Normalise both provenance records — the one behind the held
   measurement and the as-built one for the gap — into the same
   attribute set. Reject an unrecognised attribute before it reaches
   the comparison; a misspelled key must not silently read as "no
   change".
2. Compare attribute by attribute. Categorise each difference as
   yield-affecting or administrative, and treat a coating-thickness
   difference inside the recording tolerance as no change rather than
   as a process change.
3. Establish criticality of the gap: compute the frequency-gap
   product, test it against the susceptibility band, and compare the
   design-margin against the project threshold. Honour an explicit
   critical declaration as an override.
4. Validate the held measurement record: age against the validity
   window, presence of facility, instrument and conditioning, and
   coverage of the required primary-electron-energy span.
5. Decide. A multipaction-critical gap with at least one
   yield-affecting change demands a fresh sample measurement. So does
   a critical gap whose held record is no longer valid. A critical gap
   with only administrative differences and a sound record supports a
   reuse-justification. A non-critical gap records its differences
   without firing the clause 9.2 trigger.
6. Emit the justification record: decision, the drivers behind it, the
   categorised differences, and the record findings, so the reviewer
   reads the argument rather than the conclusion alone.

## Pitfalls

- Comparing part numbers instead of surface attributes — the same
  drawing number can be built with a different plating bath or a
  different final clean, and that is exactly the change clause 9.2 is
  written for.
- Reading "no yield-affecting change" as sufficient while the held
  record has aged past its validity window or was taken over a
  narrower primary-electron-energy span than the assessment reads —
  the record defect is an independent reason to remeasure.
- Firing the remeasurement demand on every gap in the assembly. The
  trigger is scoped to the multipaction-critical gaps; spending sample
  measurements on gaps far outside the susceptibility band buys
  nothing and delays the ones that matter.
- Treating a design-margin exactly at the project threshold as failing
  it. A margin that equals the threshold meets it; the comparison must
  absorb floating-point representation error rather than move the
  engineering limit.
- Dropping the drivers and keeping the decision. A reuse-justification
  with no list of compared-and-equal attributes cannot be reviewed and
  is not a justification.

## Behavior contract (gate 3)

The provenance comparison, difference categorisation, gap-criticality,
record-validity and decision logic is exercised by the gate 3 contract
test: scripts/test_e2001_emission_yield_measurement_justification.py
against scripts/e2001_emission_yield_measurement_justification_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2001_emission_yield_measurement_justification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
