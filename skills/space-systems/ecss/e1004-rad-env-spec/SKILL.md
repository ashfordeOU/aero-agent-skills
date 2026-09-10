---
name: e1004-rad-env-spec
description: "Use when producing the radiation environment specification (RES) required by ECSS-E-ST-10-04C clause 9.3 for a space mission: determine which radiation environment components (trapped radiation, solar energetic particles, galactic cosmic rays, internal-charging worst-case spectra, trapped-proton worst-case spectra, atmospheric albedo neutrons) apply to each orbit segment, verify that the RES states the model choice, basis (long-term-average vs. worst-case), and uncertainty for every applicable component, and flag missing sections or missing uncertainty statements before the RES is closed out. Trigger: radiation environment specification, RES, e-st-10-04, ecss, per-orbit radiation data, model choice, worst-case spectrum, radiation uncertainty."
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
  tags: [ecss, e-st-10-04c, radiation-environment, res, space-systems]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Environment Specification (space-systems/ecss/e1004-rad-env-spec)

Use when the task is assembling or checking the radiation environment
specification (RES) for a mission under ECSS-E-ST-10-04C clause 9.3:
the document that consolidates every applicable energetic-particle
radiation component into per-orbit-segment data with stated model
choices and uncertainties.

## Domain quick reference

- The RES is the deliverable that rolls up the individual radiation
  environment components (trapped radiation §9.2.1, solar particle
  events §9.2.2, galactic cosmic rays §9.2.3, geomagnetic shielding
  §9.2.4, atmospheric albedo neutrons §9.2.5, L2/magnetotail §9.2.7)
  into one specification, broken down per orbit segment of the
  mission profile.
- Which components apply depends on the orbit regime: trapped
  radiation applies to any orbit that crosses the radiation belts
  (LEO, MEO, GEO, GTO, HEO); solar energetic particles (SEP) and
  galactic cosmic rays (GCR) apply outside strong geomagnetic
  shielding (MEO/GEO/GTO/HEO, L2, deep magnetotail, interplanetary,
  and polar/high-inclination LEO); atmospheric albedo neutrons apply
  to LEO only; internal-charging worst-case electron spectra apply to
  MEO/GEO/GTO/HEO; worst-case trapped-proton spectra are additionally
  required for long missions (nominally 5 years or more) in
  MEO/GEO/GTO/HEO.
- For every applicable component the RES must record: the model used
  (e.g. AE/AP-family, IGE-2006, ONERA MEOv2, FLUMIC, NASA worst-case
  GEO, ESP, MOBE-DIC), the basis of the value (long-term average vs.
  worst-case vs. a fluence or spectrum tied to a confidence level),
  and the associated uncertainty. A component entry that names a
  model but omits the basis or the uncertainty is incomplete.
- The RES as a whole is only complete when its required top-level
  sections are present (mission/orbit definition, which environment
  components were addressed, model selection and justification,
  per-orbit-segment data, an uncertainty discussion, an explicit
  worst-case-vs-average basis statement, and references to the source
  models) and every orbit segment carries all of its applicable
  components with no incomplete entries.

## Workflow

1. Enumerate the mission's orbit segments and classify each by
   regime (LEO, MEO, GEO, GTO, HEO, L2, deep-tail, interplanetary),
   noting inclination/polar coverage and the mission duration
   relevant to that segment.
2. For each orbit segment, derive the set of applicable radiation
   components from its regime, polar flag, and duration (trapped
   radiation, SEP, GCR, internal charging, worst-case trapped proton,
   atmospheric neutrons) rather than assuming every mission needs
   every component.
3. For each applicable component, record the model choice, its basis
   (long-term-average, worst-case, fluence, or spectrum), and its
   uncertainty statement; do not leave any of the three blank.
4. Check the orbit segment against its derived requirement set: any
   applicable component with no entry is a missing component; any
   entry missing model, basis, or uncertainty is an incomplete entry.
5. Check the RES document itself against the required top-level
   section list; any absent section blocks sign-off regardless of
   how complete the per-segment data is.
6. Only mark the RES complete when every orbit segment is complete
   (no missing components, no incomplete entries) and no top-level
   section is missing; otherwise report the specific gaps so they can
   be closed before the RES is issued.

## Pitfalls

- Applying a single generic radiation environment to the whole
  mission instead of breaking it down per orbit segment, which hides
  regime-specific requirements (e.g. missing SEP/GCR for a GEO
  segment because it was only checked against LEO's component set).
- Recording a model name without its basis (worst-case vs.
  long-term-average) — the two answer different design questions
  (lifetime dose vs. peak single-event/charging risk) and are not
  interchangeable.
- Omitting the worst-case trapped-proton spectrum for long-duration
  MEO/GEO/GTO/HEO missions because it is easy to mistake for a
  duplicate of the long-term-average trapped-radiation entry.
- Treating the RES as complete once every orbit segment's component
  data is filled in, while a top-level section (e.g. the uncertainty
  discussion or model justification) is still missing from the
  document.

## Behavior contract (gate 3)

The applicability derivation, component-entry completeness, orbit-
segment assessment, and RES-level roll-up logic is exercised by the
gate 3 contract test: scripts/test_e1004_rad_env_spec.py against
scripts/e1004_rad_env_spec_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_rad_env_spec.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
