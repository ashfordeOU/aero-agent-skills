---
name: e1004-sep-peakflux
description: "Use when you must compute solar energetic particle (SEP) peak proton fluxes with JPL-type worst-case models for single event effect (SEE) worst-case analyses per ECSS-E-ST-10-04C: confirm the analysis purpose actually needs a peak-flux (not fluence) model, pick the standard proton energy channel that covers the device's SEE sensitivity threshold, compute the worst-case integral peak flux at the chosen confidence level, and check the worst-case window is a short high-intensity period rather than a mission-duration integration. Produces the peak-flux applicability verdict, the selected energy channel, the computed peak flux, and the worst-case window classification. Trigger: sep peak flux, solar particle peak flux, jpl model, see worst case, single event effect worst case, proton peak flux, e-st-10-04c 9.2.2.3."
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
  tags: [ecss, e-st-10-04c, sep, peak-flux, jpl-model, see, radiation-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Particle Peak Flux for SEE Worst Case (space-systems/ecss/e1004-sep-peakflux)

Use when the task is ECSS-E-ST-10-04C clause 9.2.2.3 solar energetic
particle (SEP) peak-flux analysis: computing a JPL-type worst-case
peak proton flux to feed a single event effect (SEE) rate worst-case
analysis, as distinct from the mission-duration fluence analysis of
clause 9.2.2.2.

## Domain quick reference

- ECSS-E-ST-10-04C §9.2.2 splits SEP proton environment analysis into
  two distinct products: §9.2.2.2 computes mission-duration integrated
  fluence with the ESP model (for cumulative degradation and total
  dose), while §9.2.2.3 computes a short-duration worst-case peak flux
  with JPL-type models (for SEE rate worst-case analysis). The two are
  not interchangeable: SEE rates depend on the instantaneous flux
  during the worst part of an event, not the total fluence over the
  mission.
- JPL-type peak-flux models are conventionally expressed as an
  integral flux above a proton energy threshold, at a stated
  confidence level (the probability that the true worst-case peak flux
  will not be exceeded). Higher confidence levels correspond to larger
  (more conservative) peak-flux magnitudes.
- SEE worst-case analyses use standard proton energy channels chosen
  to cover the device's SEE-sensitive energy or LET threshold; the
  channel used must be at least as energetic as the device threshold.
- The peak flux is only meaningful over a short worst-case window (on
  the order of the peak period of a large event, not the whole
  mission). An analysis window stretched out to mission duration
  should instead use the §9.2.2.2 fluence model.

## Workflow

1. Confirm the analysis purpose actually calls for a peak-flux model
   with peak_flux_applicable; if the purpose is cumulative
   degradation or total dose, redirect to the e1004-sep-fluence (ESP)
   leaf instead.
2. Select the standard proton energy channel that covers the device's
   SEE-sensitive energy threshold with select_energy_channel.
3. Compute the worst-case integral peak flux at the project's stated
   confidence level with integral_peak_flux.
4. Classify the worst-case analysis window with
   worst_case_window_check; a window longer than the short-duration
   peak-flux window means the fluence model applies instead.
5. Combine steps 1-4 with peakflux_worst_case_verdict to get the
   overall applicability status, selected channel, and computed peak
   flux before handing the result to the SEE rate calculation.

## Pitfalls

- Using a peak-flux (JPL-type) result where a fluence (ESP) result was
  needed, or vice versa — they answer different questions (SEE rate
  vs. cumulative degradation).
- Selecting an energy channel below the device's actual SEE-sensitive
  threshold, understating the flux relevant to the device.
- Quoting a peak flux at one confidence level while the project's
  worst-case policy specifies another.
- Applying a peak-flux number to a mission-duration window instead of
  the short worst-case period it represents.

## Behavior contract (gate 3)

The applicability, channel-selection, peak-flux, and window-check
logic is exercised by the gate 3 contract test:
scripts/test_e1004_sep_peakflux.py against
scripts/e1004_sep_peakflux_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_sep_peakflux.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
