---
name: e1012-dd-env-tech
description: "Use when identify displacement-damage-relevant particle environments and susceptible component technologies for a space mission under ECSS-E-ST-10-12C §8.3–8.4: categorize the orbital environment by DD relevance (trapped protons, solar proton events, galactic cosmic rays), map each candidate technology (solar cells, bipolar devices, CCDs, optocouplers, photonic components) to its DD susceptibility tier, and confirm every DD-susceptible item has an assigned NIEL-based analysis path. Trigger: ecss, e-st-10-system-scope, displacement-damage, dd, niel, trapped-protons, solar-cells, bipolar-devices, ccd, optocoupler."
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
  tags: [ecss, e-st-10-system-scope, displacement-damage, dd, niel, trapped-protons, solar-cells, bipolar-devices, ccd, optocoupler]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — DD-Relevant Environments and Technologies (space-systems/ecss/e1012-dd-env-tech)

Use when the task is to identify which particle environments drive displacement
damage (DD) and which component technologies on a spacecraft require a
NIEL-based DD analysis under ECSS-E-ST-10-12C §8.3–8.4.

## Domain quick reference

- Displacement damage occurs when energetic particles displace atoms from their
  lattice sites in semiconductor or photonic materials, permanently degrading
  carrier lifetime and mobility. The governing metric is non-ionising energy
  loss (NIEL), expressed in MeV·cm²/g and integrated over the particle fluence
  spectrum of the mission orbit.
- §8.3 partitions the space particle environment by DD relevance. Trapped
  protons in the inner Van Allen belt dominate NIEL fluence for most low and
  medium Earth orbits. Solar proton events (SPEs) contribute significant
  peak-fluence bursts on any orbit with low shielding depth. Galactic cosmic
  rays (GCRs) contribute a moderate NIEL background, important for long-duration
  missions. Trapped electrons deposit energy mainly via ionisation; their NIEL
  contribution is negligible for most device types but is recorded for
  completeness.
- §8.4 groups component technologies by DD susceptibility tier. Technologies
  with CRITICAL tier (e.g. silicon and GaAs solar cells, multi-junction
  photovoltaics) experience large beginning-of-life to end-of-life power
  degradation and always require a NIEL analysis. HIGH-tier devices — CCDs,
  bipolar transistors and ICs, optocouplers, photodiodes, laser diodes —
  exhibit measurable gain degradation or dark-current increase at mission
  fluences and require analysis. MODERATE-tier devices require analysis only
  when the orbit carries a HIGH-relevance environment. LOW and NONE tiers
  (CMOS digital logic, passives) are DD-resistant and do not require a
  dedicated NIEL analysis unless the designer flags a specific concern.
- A DD-susceptible item without an assigned analysis path is a non-conformance
  against §8.4, not merely a gap: the standard requires positive evidence that
  every susceptible item has been analysed or dispositioned.

## Workflow

1. Determine the mission orbit type (LEO, MEO, GEO, HEO, interplanetary,
   lunar). Map it to the set of DD-relevant particle environments using the
   §8.3 environment table. Record each environment alongside its DD relevance
   tier (HIGH, MODERATE, LOW, NEGLIGIBLE). Flag any orbit that contains at
   least one HIGH-relevance environment — such missions always require a
   complete NIEL analysis for every CRITICAL and HIGH-tier technology.
2. Inventory every candidate component and technology in the design. For each
   item, retrieve its DD susceptibility tier from the §8.4 technology table.
   Reject any item whose technology label does not appear in the table —
   unknown technologies must be resolved before the scope is closed.
3. For every item whose susceptibility tier is CRITICAL or HIGH, confirm that
   a NIEL-based DD analysis has been assigned. For MODERATE-tier items, confirm
   analysis assignment only when the orbit's environment set includes a
   HIGH-relevance environment. Record LOW and NONE items as not requiring
   analysis, but retain them in the scope register.
4. Produce the DD analysis coverage report: a list of covered items (analysis
   assigned or not required), missing items (analysis required but not assigned),
   and error items (technology not recognised). The mission DD scope is closed
   only when the missing and error lists are both empty.

## Pitfalls

- Treating trapped electrons as a DD driver equivalent to protons — electrons
  deposit energy primarily via ionisation; their NIEL contribution is typically
  orders of magnitude lower than trapped protons at the same fluence and must
  not be substituted for proton NIEL in solar-cell degradation calculations.
- Omitting SPE contributions for GEO and HEO missions — trapped proton belts
  are thin or absent at those altitudes, but the SPE proton fluence over a
  7–10 year mission lifetime can be the dominant NIEL source for solar panels
  and bipolar devices at those orbits.
- Equating "no NIEL analysis performed" with "no DD concern" — §8.4 requires
  a positive disposition for every CRITICAL and HIGH-tier item regardless of
  engineering judgement; the absence of an assigned analysis is a finding in
  itself.
- Applying a single generic NIEL value across all particle species and energies
  — NIEL is strongly energy- and species-dependent; the correct approach
  integrates the product of the differential fluence spectrum and the
  energy-dependent NIEL curve over the full spectrum for each relevant species.

## Behavior contract (gate 3)

The environment-categorization, technology-susceptibility, analysis-coverage,
and mission-scope-mapping logic is exercised by the gate 3 contract test:
scripts/test_e1012_dd_env_tech.py against scripts/e1012_dd_env_tech_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1012_dd_env_tech.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
