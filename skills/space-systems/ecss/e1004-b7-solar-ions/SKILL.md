---
name: e1004-b7-solar-ions
description: "Use when deriving solar energetic particle (SEP) heavy-ion energy spectra with Z-dependent elemental abundances for single-event-effects (SEE) analysis under ECSS-E-ST-10-04C Annex B.7: derive each species' differential flux spectrum from a reference element (oxygen) spectrum, classify the SEP event type (gradual/shock-associated vs impulsive/flare-associated) from its iron-to-oxygen abundance ratio, apply the event type's elemental abundance table to scale species spectra, verify heavy-ion species coverage extends through the iron group, and identify whether the worst-case impulsive-enhanced abundance table is selected for SEE. Trigger: solar energetic particle, SEP heavy ion, Annex B.7, Z-dependent abundance, iron-rich event, Fe/O ratio, heavy ion spectrum, SEE analysis, e-st-10-04, ecss, space environment, radiation environment."
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
  tags: [ecss, e-st-10-04c, sep, solar-energetic-particle, heavy-ion, z-dependent-abundance, annex-b7, see]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Energetic Ion Spectra (space-systems/ecss/e1004-b7-solar-ions)

Use when the task is deriving the heavy-ion (Z > 2) content of the solar
energetic particle (SEP) environment under ECSS-E-ST-10-04C Annex B.7,
with element-by-element abundance ratios, for a single-event-effects
(SEE) radiation analysis.

## Domain quick reference

- Annex B.7 gives the heavy-ion (Z > 2) energy-spectra content of the
  SEP worst-case/worst-week environment used for SEE analyses,
  expressed as element-by-element differential flux vs. energy; the
  SEP proton/light-ion fluence and peak-flux leaves (sibling
  e1004-sep-fluence, e1004-sep-peakflux) cover the bulk light-particle
  content of the same environment.
- Because a first-principles spectrum for every element is
  impractical, per-species spectra are conventionally derived by
  scaling a reference element's measured/modeled differential energy
  spectrum (conventionally oxygen, Z=8) by that element's abundance
  ratio relative to the reference element.
- Elemental abundance ratios are far from constant between events:
  "gradual" (shock-associated, proton-rich) events carry abundance
  ratios close to average solar/coronal composition, while "impulsive"
  (flare-associated) events are strongly enhanced in heavy ions --
  especially iron -- sometimes by an order of magnitude or more
  relative to gradual events. The iron-to-oxygen (Fe/O) ratio is the
  discriminating indicator between the two classes.
- Because the SEE rate at a given LET threshold is driven
  disproportionately by the heavy-ion tail, an SEE worst-case analysis
  must use the impulsive-event (Fe-enhanced) abundance table, not the
  gradual/average table -- the opposite bias from a proton-fluence
  total-dose analysis, which is dominated by the light-ion/proton
  content of gradual events.
- SEE analyses need heavy-ion species coverage extending at minimum
  through the iron group (through nickel, Z=28); truncating the
  species set below that discards ions that can dominate the
  single-event rate for high-LET-sensitive parts, mirroring the
  coverage concern in the sibling e1004-gcr leaf.
- This leaf scopes per-species spectrum derivation, event-type
  classification from Fe/O ratio, abundance-table application, and
  species-coverage/worst-case verification only. LET calculation from
  an ion spectrum and shielding/path-length effects are out of scope
  of this leaf.

## Workflow

1. For each SEE case, record the reference element's (oxygen, Z=8)
   differential energy spectrum, the case's observed or assumed Fe/O
   abundance ratio, and the maximum ion charge number (species_max_z)
   the case's heavy-ion table covers.
2. Classify the case's SEP event type from its Fe/O ratio: gradual/
   shock-associated when Fe/O sits at or below the average-composition
   threshold, impulsive/flare-associated when Fe/O sits at or above the
   enhanced threshold, mixed/intermediate otherwise.
3. Select the elemental abundance table for the event type (the
   gradual-composition table or the impulsive/Fe-enhanced table; for a
   mixed classification, use the conservative envelope of both
   tables).
4. For each species of interest, look up its abundance ratio relative
   to the reference element in the selected table and scale the
   reference element's differential flux spectrum by that ratio to
   obtain the species' differential flux spectrum.
5. Determine the minimum heavy-ion species coverage the SEE analysis
   requires (through the iron group, Z=28) and verify the case's
   species_max_z meets it; flag insufficient coverage rather than
   silently truncating the species set.
6. Determine the worst-case event classification required for an SEE
   analysis (impulsive or the mixed envelope; gradual alone is
   insufficient) and check the case's event-type result against it.
7. Mark the case compliant only when its species coverage is adequate
   and its event type is impulsive or mixed; roll every case's
   compliance into the assessment record and do not close the
   radiation environment specification while any case remains
   non-compliant.

## Pitfalls

- Using the gradual/average-composition abundance table for an SEE
  worst-case analysis instead of the impulsive/Fe-enhanced table,
  understating heavy-ion (especially iron-group) fluence and therefore
  the single-event rate.
- Truncating the heavy-ion species set below the iron group because
  those ions are rare, when rare high-Z, high-LET ions can still
  dominate the single-event rate for sensitive parts.
- Treating the reference element's spectral shape as sufficient for
  every species without applying the abundance ratio, which conflates
  the reference element's absolute flux with the flux of other
  elements.
- Using a single Fe/O ratio and abundance table for an entire
  mission's worst-case SEE analysis when the actual event population
  is a mix -- the conservative envelope (mixed classification) should
  be used unless a mission-specific single event is contractually the
  design case.

## Behavior contract (gate 3)

The event-classification, abundance-table, spectrum-scaling,
species-coverage, and compliance logic is exercised by the gate 3
contract test: scripts/test_e1004_b7_solar_ions.py against
scripts/e1004_b7_solar_ions_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_b7_solar_ions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
