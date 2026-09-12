---
name: acoustic-analysis
description: "Use when analyze acoustic loading response of spacecraft structural panels under a diffuse acoustic field per ECSS-E-ST-32C clause 4.6.2.6: convert broadband sound pressure levels to acoustic pressure, compute overall sound pressure level from spectral bands, categorize the excitation as low-frequency or high-frequency coupling, compute acoustic force on each panel, verify structural response margins against allowables, confirm the diffuse-field assumption above the Schroeder frequency, assess acoustic fatigue risk for sustained high-level exposures, and aggregate compliance findings per surface. Trigger: ecss, e-st-32-structures-scope, acoustic-analysis, diffuse-acoustic-field, sound-pressure-level, acoustic-loading, low-frequency-response, structural-acoustic, acoustic-fatigue."
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
  tags: [ecss, e-st-32-structures-scope, acoustic-analysis, diffuse-acoustic-field, sound-pressure-level, acoustic-loading, low-frequency-response, structural-acoustic, acoustic-fatigue]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Acoustic Loading Response Analysis (space-systems/ecss/acoustic-analysis)

Use when the task is the acoustic loading response analysis of spacecraft structural
panels per ECSS-E-ST-32C clause 4.6.2.6 — converting measured or predicted broadband
sound pressure levels into panel acoustic forces, verifying that the diffuse-field
assumption applies at the frequencies of interest, categorizing excitation as
low-frequency or high-frequency structural coupling, checking structural response
margins, screening for acoustic fatigue risk, and aggregating per-surface compliance
findings.

## Domain quick reference

- **Sound pressure level (SPL)** is expressed in decibels relative to the standard
  acoustic reference pressure of 20 µPa. The overall SPL (OASPL) across a spectrum
  is computed by logarithmic summation of the individual band levels: each band
  contributes 10^(SPL/10) to the linear sum, then the total is converted back to
  decibels. Combining bands on a linear (power) scale prevents the underestimation
  that results from averaging decibel values directly.

- **Diffuse acoustic field** assumption: the acoustic field inside an acoustic test
  facility or launch vehicle fairing can be treated as homogeneous and isotropic only
  above the Schroeder frequency, which depends on the facility reverberation time
  and volume (f_s = 2000 × √(T60 / V)). At frequencies below f_s the modal density
  is too sparse for a statistical diffuse-field model to apply; analysis in that
  regime requires a deterministic wave or statistical energy analysis approach.

- **Frequency regime**: ECSS-E-ST-32C distinguishes low-frequency response (panel
  behaviour dominated by global structural modes, typically below 200 Hz) from
  high-frequency response (local panel resonances, dominated by radiation efficiency
  and statistical energy analysis). The boundary at 200 Hz is a guideline; the
  analyst must confirm using the panel critical frequency. Below the critical
  frequency, radiation efficiency is less than unity and scales approximately as
  the square root of the frequency-to-critical-frequency ratio.

- **Acoustic force on a panel** is the product of the RMS acoustic pressure and the
  panel reference area. For a diffuse field the effective pressure loading is
  computed from the OASPL converted back to pressure units.

- **Margin of safety** follows the standard structural convention:
  MS = (allowable / response) − 1. A negative MS indicates non-compliance.

- **Acoustic fatigue risk** is screened by combining the OASPL level with exposure
  duration; sustained exposures (≥ 60 s) above a high-level threshold (typically
  140 dB OASPL) warrant a detailed acoustic fatigue analysis.

## Workflow

1. **Collect the acoustic environment specification**: obtain the 1/3-octave SPL
   spectrum (or OASPL) for each loading event (launch, acoustic test, in-orbit
   transient). Confirm the reference pressure convention (20 µPa) and the
   measurement or prediction basis.

2. **Verify diffuse-field applicability**: for each frequency band of interest and
   each facility or structural bay, compute the Schroeder frequency from the
   reverberation time and volume. Drop any frequency bands below the Schroeder
   frequency from the diffuse-field analysis and flag them for separate deterministic
   treatment.

3. **Compute OASPL**: sum the individual 1/3-octave band levels on a linear power
   basis to obtain the OASPL for each loading event. Use the OASPL to derive the
   RMS acoustic pressure applied to each panel.

4. **Categorize frequency regime**: for each panel, determine whether the dominant
   response frequency falls in the low-frequency or high-frequency regime relative
   to the 200 Hz boundary and relative to the panel critical frequency. Low-frequency
   panels are assessed using global structural models; high-frequency panels require
   statistical energy analysis or a radiation-efficiency correction.

5. **Compute panel acoustic force**: multiply the RMS acoustic pressure by the panel
   reference area to obtain the acoustic force input. For high-frequency panels apply
   the radiation efficiency factor (< 1 below the critical frequency).

6. **Check structural response margins**: compute the margin of safety for each panel
   from the analysis response and the allowable stress or displacement. Flag any panel
   with MS < 0 as non-compliant.

7. **Screen for acoustic fatigue risk**: for each loading event, check whether the
   OASPL exceeds the fatigue screening threshold and whether the exposure duration
   meets or exceeds 60 s. Flag any event–panel combination that meets both conditions
   for a detailed acoustic fatigue analysis.

8. **Aggregate findings**: collect the per-panel compliance results (margin check,
   diffuse-field validity, fatigue risk flag) and produce a surface-level summary.
   A surface is compliant only when all three checks pass.

## Pitfalls

- **Averaging SPL values arithmetically**: acoustic levels must be combined on a
  linear (power) scale. Averaging decibel values directly underestimates the OASPL
  whenever the band levels differ significantly and produces a non-conservative result.

- **Applying a diffuse-field model below the Schroeder frequency**: in the
  low-modal-density region the pressure field is not statistically uniform; treating
  it as diffuse underestimates the spatial variation and can miss local pressure
  peaks by a significant margin.

- **Ignoring radiation efficiency below the critical frequency**: a panel radiates
  less than a baffled piston below its critical frequency; collapsing radiation
  efficiency to unity overestimates the acoustic force and is non-conservative for
  response but unconservative for coupling loss factors in a statistical energy
  analysis.

- **Reading an unset allowable as a pass**: if no allowable stress or displacement
  budget is on record for a panel, the margin check cannot be performed and the
  surface must be flagged as having an incomplete assessment, not as compliant.

- **Skipping the fatigue screen for short acoustic test events**: a brief burst at
  very high OASPL can still initiate fatigue cracking in thin-gage aluminum panels;
  the screening criterion combines level AND duration and both gates must be checked.

## Behavior contract (gate 3)

The SPL conversion, OASPL aggregation, diffuse-field check, frequency-regime
categorization, acoustic-force computation, margin-of-safety calculation,
acoustic-fatigue risk screen, and compliance aggregation logic are exercised by
the gate 3 contract test:
scripts/test_acoustic_analysis.py against scripts/acoustic_analysis_logic.py
(stdlib unittest, offline). Run:

    python3 scripts/test_acoustic_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
