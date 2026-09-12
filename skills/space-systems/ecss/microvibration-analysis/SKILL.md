---
name: microvibration-analysis
description: "Use when determine the micro-vibration environment of a spacecraft structure under ECSS-E-ST-32C clause 4.6.2.21: categorize each disturbance source as rotating (reaction wheels, momentum wheels, cryocoolers, pumps), periodic-low-frequency (solar array drives), or impulsive (thruster valves), compute harmonic frequencies for each rotating source, apply the structural transmissibility from source mounting to sensitive equipment, check whether any harmonic falls within the instrument sensitive frequency band, compute the induced micro-vibration amplitude at equipment, and verify compliance against the instrument micro-vibration allowable. Trigger: ecss, e-st-32-structures-scope, microvibration, micro-vibration, reaction-wheel, disturbance-source, transmissibility, sensitive-instrument, jitter, harmonic."
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
  tags: [ecss, e-st-32-structures-scope, microvibration, micro-vibration, reaction-wheel, disturbance-source, transmissibility, jitter, harmonic]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Micro-Vibration Analysis (space-systems/ecss/microvibration-analysis)

Use when the task is the micro-vibration (microgravity, noise, and
human-induced disturbance) analysis of a spacecraft structure under
ECSS-E-ST-32C clause 4.6.2.21 — categorizing on-board disturbance
sources, computing their harmonic content, propagating disturbance
levels through the structural transfer function, and verifying
compliance of each sensitive instrument against its micro-vibration
allowable.

## Domain quick reference

- Clause 4.6.2.21 addresses micro-vibration: the low-level, broadband
  vibration environment induced on a spacecraft by on-board mechanical
  equipment (reaction wheels, momentum wheels, cryocoolers, pumps),
  low-speed periodic actuators (solar array drives), and impulsive
  devices (thruster valve operations). These disturbances propagate
  through the structure and can degrade pointing accuracy, blur
  optical instruments, or disrupt scientific payloads.
- Disturbance sources are categorized into three families by mechanism:
  rotating (generates harmonics at integer multiples of spin
  frequency), periodic-low-frequency (generates a single fundamental
  or small set of harmonics at the drive rate), and impulsive (broadband
  shock-like input with no dominant harmonic).
- For rotating and periodic sources, structural transmissibility governs
  how much of the source amplitude reaches the sensitive equipment.
  Below the isolation-system natural frequency the structure transmits
  essentially at unity gain; above that frequency the transmissibility
  rolls off approximately as (f_isolation / f)^2 for a second-order
  passive isolation system.
- A harmonic is in the sensitive band of an instrument if its frequency
  falls between the instrument's lower and upper susceptibility
  frequency limits. Only in-band harmonics contribute to the compliance
  check; out-of-band harmonics are dropped from the amplitude
  assessment for that instrument.
- Compliance at equipment is verified by comparing the peak in-band
  induced amplitude (source amplitude multiplied by worst-case
  transmissibility at the harmonic frequency) against the instrument
  micro-vibration allowable. An instrument with in-band harmonics but
  no allowable on record is itself a finding — the requirement was never
  captured.

## Workflow

1. Inventory every on-board disturbance source and categorize each as
   rotating, periodic-low-frequency, or impulsive. Reject an
   unrecognized source type before it enters the assessment.
2. For each rotating source, compute the harmonic frequency series:
   f_n = n × f_spin for each harmonic order defined for that source
   type. For periodic-low-frequency sources use the drive frequency
   directly as the fundamental. Impulsive sources carry no harmonic
   list; flag them for broadband review separately.
3. For each (source, sensitive-instrument) pair, check whether any
   harmonic falls within the instrument's susceptibility band
   [f_low, f_high]. Pairs with no in-band harmonic make no contribution
   to that instrument's amplitude budget; drop them from further
   computation.
4. For each in-band harmonic, compute the structural transmissibility
   T(f) = 1.0 when f ≤ f_isolation, T(f) = (f_isolation / f)^2 when
   f > f_isolation, where f_isolation is the natural frequency of the
   isolation system between source and instrument. Apply T(f) to the
   source harmonic amplitude to obtain the induced amplitude at the
   instrument.
5. Take the worst-case (maximum) induced amplitude over all in-band
   harmonics of all reaching sources for each instrument.
6. Compare the worst-case induced amplitude against the instrument's
   micro-vibration allowable. Flag an exceedance. Separately flag an
   instrument with in-band sources but no allowable on record.
7. Aggregate findings per instrument; an instrument is compliant only
   when no exceedance and no missing-allowable finding is present.

## Pitfalls

- Computing transmissibility once at the spin frequency rather than at
  each harmonic — higher harmonics push into the isolation roll-off
  region and may be the critical driver, while lower harmonics remain
  in the rigid-body unity-gain region.
- Treating all in-band harmonics as equally driven — harmonic amplitude
  typically decreases with harmonic order; use per-order amplitude
  data from the source characterization rather than copying the
  fundamental amplitude to every harmonic.
- Assuming transmissibility equals unity across all frequencies because
  no isolation system is installed — structural stiffness still sets an
  effective transmissibility profile; unity is a conservative but valid
  bound only when no structural model is available.
- Counting an impulsive source as compliant because it has no harmonic
  frequency and therefore zero overlap with the sensitive band — an
  impulsive source requires a separate broadband amplitude assessment
  outside the harmonic framework; this leaf's harmonic check is not
  sufficient to clear an impulsive source.
- Leaving a sensitive instrument's micro-vibration allowable unset and
  reading "no exceedance" as compliant — an unset allowable means the
  interface requirement was never established, which is itself a finding.

## Behavior contract (gate 3)

The source-categorization, harmonic-frequency, transmissibility,
frequency-overlap, induced-amplitude, and compliance logic is exercised
by the gate 3 contract test: scripts/test_microvibration_analysis.py
against scripts/microvibration_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_microvibration_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
