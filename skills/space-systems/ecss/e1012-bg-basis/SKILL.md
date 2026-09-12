---
name: e1012-bg-basis
description: "Use when define the sensor-background assessment basis for a space instrument under ECSS-E-ST-10-12C §10.1–10.3: identify the relevant natural radiation environments for the target orbit (trapped electrons and protons, galactic cosmic rays, solar energetic particles, albedo neutrons), map the instrument to a sensor-technology family from the standard's Table 10-1 taxonomy (silicon semiconductor, scintillator, proportional counter, solid-state germanium, CdTe/CdZnTe, neutron detector, microchannel plate), and confirm both inputs are on record before proceeding to quantitative background calculations. This leaf sets the mandatory prerequisite inputs for all downstream §10 background-flux and response calculations. Trigger: ecss, e-st-10-system-scope, background, sensor-background, radiation-environment, instrument-technology, space-instrument, background-basis."
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
  tags: [ecss, e-st-10-system-scope, background, sensor-background, radiation-environment, instrument-technology, space-instrument, background-basis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Sensor Background Assessment Basis (space-systems/ecss/e1012-bg-basis)

Use when the task is to define and confirm the sensor-background assessment
basis under ECSS-E-ST-10-12C §10.1–10.3 — selecting the relevant radiation
environments for a target orbit and mapping the instrument to a sensor-technology
family before any background-flux calculation proceeds.

## Domain quick reference

- §10.1 defines "sensor background" as the signal generated in the detector by
  the ambient space radiation environment, distinct from the scientific-target
  signal. Every instrument sensitive to electromagnetic or particle radiation
  carries a background contribution that must be characterized before the
  observation programme is planned.
- §10.2 lists the relevant environments that contribute to sensor background:
  trapped electrons and trapped protons from the Earth's radiation belts (inner
  and outer zones), galactic cosmic rays (GCR), solar energetic particles (SEP)
  during active-sun periods, and albedo neutrons (relevant for LEO instruments
  with downward-facing detectors). The applicable subset is orbit-dependent:
  LEO draws from all five sources; GEO is dominated by outer-belt electrons plus
  SEP and GCR; deep-space orbits see only GCR.
- §10.3 and Table 10-1 group instrument technologies into seven sensor families,
  each with a characteristic background-response mechanism: silicon semiconductor
  (photodiode, CCD, CMOS APS) — charge deposition by ionizing particles;
  scintillator (NaI, CsI, BGO, LaBr₃) — scintillation light from particle
  interactions; proportional counter (Xe, Ar, P10 fill) — gas ionization;
  solid-state germanium (HPGe, LEGe) — direct ionization with high spectral
  resolution; CdTe/CdZnTe — direct ionization in compound semiconductor; neutron
  detector (He-3 tube, Li-glass, BF₃) — nuclear reactions; microchannel plate
  (MCP) — direct particle hits and secondary emission. Selecting the wrong family
  misdirects the downstream response model.

## Workflow

1. Confirm the target orbit type from the mission profile (LEO, MEO, HEO, GEO,
   INTERPLANETARY, DEEP_SPACE). Reject an orbit label not on the §10.2 list
   and request a corrected value before proceeding.
2. Retrieve the relevant-environment list for that orbit type from the §10.2
   mapping. Record every environment on the list; none may be silently dropped.
3. Confirm the instrument technology from the instrument data sheet or ICD. Map
   it to one of the seven Table 10-1 sensor families. Reject a technology label
   with no match in the taxonomy before proceeding.
4. Record the sensor-family key alongside its background-response mechanism and
   applicable energy range. These become the input parameters for downstream §10
   background-flux calculations.
5. Verify that the assessment-basis record is complete: orbit type, environment
   list (at least one entry), sensor-family key, and response mechanism — all
   four fields present. A record missing any field is incomplete and must not
   proceed to the quantitative calculation stage.
6. Log the completed basis record. The record anchors every downstream
   background-flux and dose calculation for this instrument; if orbit or
   technology changes during the programme, repeat steps 1–5.

## Pitfalls

- Carrying forward an orbit-type label from an earlier mission phase without
  rechecking: a delta-V manoeuvre or mission redesign can shift the orbit from
  LEO to MEO, adding inner-belt protons to the environment list. Re-verify the
  orbit type at every phase boundary.
- Treating the sensor-family selection as advisory: using the wrong family key
  (e.g., mapping a scintillator to silicon-semiconductor) propagates a wrong
  response model through all downstream calculations. The technology-mapping step
  must be explicit and on record.
- Accepting "generic" or "TBD" as an orbit type: the standard requires a specific
  orbit label to select the correct environment subset. A generic label produces
  an underdetermined environment list and makes the basis record non-assessable.
- Omitting albedo neutrons for a downward-facing LEO detector: §10.2 includes
  albedo neutrons as a relevant LEO environment; instruments with geometrical
  sensitivity toward nadir must include this source.

## Behavior contract (gate 3)

The orbit-lookup, technology-mapping, and basis-completeness logic is exercised
by the gate 3 contract test: scripts/test_e1012_bg_basis.py against
scripts/e1012_bg_basis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_bg_basis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
