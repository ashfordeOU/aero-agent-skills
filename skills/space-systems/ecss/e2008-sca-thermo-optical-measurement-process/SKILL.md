---
name: e2008-sca-thermo-optical-measurement-process
description: "Compute the solar absorptance and hemispherical emittance that clause 6.4.3.6.2 of ECSS-E-ST-20-08C asks to be measured on the designated subgroup of cell assemblies: reconcile the samples actually measured against the subgroup the plan designated, weight the measured reflectance bands into an absorptance and an emittance, derive the absorptance to emittance ratio, hold repeat scans inside the instrument repeatability limit, and refuse a band the instrument spectral range never covered. Use when a thermo optical data sheet, integrating sphere record or emissometer log has to be assessed. Trigger: ecss, e-st-20-08c, sca-thermo-optical-measurement-process, solar-cell-assembly-solar-absorptance, sca-hemispherical-emittance-measurement, sca-thermo-optical-subgroup-coverage, sca-reflectance-band-instrument-range."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-thermo-optical-measurement-process, e-st-20-08c, sca-thermo-optical-measurement-process, solar-cell-assembly-solar-absorptance, sca-hemispherical-emittance-measurement, sca-thermo-optical-subgroup-coverage, sca-reflectance-band-instrument-range]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Thermo Optical Measurement (space-systems/ecss/e2008-sca-thermo-optical-measurement-process)

Use when the task is clause 6.4.3.6.2 of ECSS-E-ST-20-08C: solar absorptance
and hemispherical emittance measured on the subgroup of cell assemblies the
test plan designated for it. This leaf reduces the reflectance scans into the
two properties and their ratio, decides whether the instrument could see the
bands it reported, holds the repeat scans against a repeatability limit, and
names the designated sample that never reached the bench.

## Domain quick reference

- These two numbers set the equilibrium temperature of the array. The
  absorptance decides how much sunlight becomes heat, the emittance decides
  how much of that heat leaves, and the ratio between them is what a thermal
  model actually consumes. A small error in either walks the predicted
  temperature by tens of kelvin.
- Both properties are weighted means, not averages. Absorptance is one minus
  the reflectance weighted by the solar spectrum; emittance is one minus the
  reflectance weighted by the thermal emission spectrum. Averaging the same
  bands without their weights produces a different number that looks equally
  plausible on the data sheet.
- The two properties live in different parts of the spectrum and are measured
  by different instruments. A band reported outside the spectral range of the
  instrument that returned it is an extrapolation of that instrument's own
  calibration, so the reflectance there is not a measurement.
- One scan is a number, not a measurement. Repeat scans of the same sample
  are the only evidence available that the bench is repeatable, so the
  declared number of them is a requirement and their spread is the figure
  that decides whether the mean means anything.
- The subgroup is designated by the plan, not chosen at the bench. Measuring
  the convenient samples instead of the designated ones closes the count and
  leaves the subgroup open, which is why coverage is resolved both ways:
  designated but unmeasured, and measured but never designated.

## Workflow

1. Reduce every scan of every sample: weight the solar bands into an
   absorptance, weight the thermal bands into an emittance.
2. Check each band against the spectral range of the instrument that reported
   it, absorbing floating-point representation error at the range edges with
   a named tolerance rather than by widening the instrument range.
3. Average the repeat scans into the reported absorptance and emittance for
   that sample, and derive the absorptance to emittance ratio from those
   means.
4. Hold the scan count against the declared number of repeats and the spread
   of the repeats against the declared repeatability limit; a sample with one
   scan has no repeatability evidence at all.
5. Reconcile the identifiers measured against the identifiers designated,
   both ways, and report each direction separately.
6. Reject a sample or a designated identifier that appears twice; two records
   under one name make the subgroup ambiguous rather than redundant.
7. Roll the subgroup up into mean properties and a verdict that any coverage
   shortfall overrides.

## Pitfalls

- Reporting a single scan as the sample value. The number is indistinguishable
  from a repeatable one until a second scan exists, and the first sample to be
  re-measured for an anomaly is usually the one that never had a pair.
- Averaging the reflectance bands unweighted. The solar spectrum is far from
  flat across the band set, so the unweighted mean quietly reweights the
  measurement toward wherever the bench happened to place its points.
- Accepting a thermal band from a solar-range instrument. The instrument
  returns a value, it just is not a calibrated one, and nothing downstream
  marks that value as different from the others.
- Reading the ratio without both properties. An assembly can hold its ratio
  while both absorptance and emittance drift together, which is a different
  physical state from the one the ratio alone suggests.
- Counting samples instead of resolving identifiers. A subgroup of six
  measured six times is complete by count and can still be missing two
  designated samples while carrying two nobody asked for.

## Behavior contract (gate 3)

The weighted reduction into absorptance and emittance, the ratio, the repeat
scan count and spread against the repeatability limit, the instrument
spectral range check and the two-way subgroup coverage are exercised by the
gate 3 contract test:
scripts/test_e2008_sca_thermo_optical_measurement_process.py against
scripts/e2008_sca_thermo_optical_measurement_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_sca_thermo_optical_measurement_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
