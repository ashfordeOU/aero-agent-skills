---
name: e1012-tid-basis
description: "Use when determine the TID assessment basis for a spacecraft electronics programme under ECSS-E-ST-10-12C §7.1–7.4: identify every orbit environment that contributes to total ionising dose (trapped protons, trapped electrons, solar energetic protons, galactic cosmic rays, bremsstrahlung), categorize each device technology against the TID sensitivity spectrum per Table 7-1 (high/moderate/low), flag bipolar linear technologies that require low dose-rate ELDRS testing, and derive the minimum TID qualification test level from the design dose and the required margin factor. Trigger: ecss, e-st-10-system-scope, total-ionising-dose, tid-assessment-basis, tid-environment, radiation-sensitive-technology, eldrs, dose-margin, table-7-1."
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
  tags: [ecss, e-st-10-system-scope, total-ionising-dose, tid-assessment-basis, tid-environment, radiation-sensitive-technology, eldrs, dose-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation — TID Assessment Basis (space-systems/ecss/e1012-tid-basis)

Use when the task is to establish the TID assessment basis for a spacecraft
electronics programme, following ECSS-E-ST-10-12C §7.1–7.4 — determining
which ionising-dose environments are active for the mission orbit, grouping
device technologies by their TID sensitivity, and setting the minimum
qualification test level before any detailed dose calculation begins.

## Domain quick reference

- §7.1 defines the purpose of the TID assessment: to confirm that each
  electronic part will survive the accumulated ionising dose over the mission
  lifetime, including all required margins, before the design is frozen.
  The assessment basis is the set of inputs that must be fixed before the
  dose calculation is performed: orbit, mission duration, shielding
  configuration, device-technology list, and margin factors.
- §7.2 identifies the environments that contribute to TID by orbit regime.
  LEO missions accumulate dose primarily from trapped protons (inner belt)
  and trapped electrons (outer belt) with their secondary bremsstrahlung.
  MEO sits inside the peak of both belts and is the most intense regime.
  GEO missions see outer-belt electrons and solar energetic protons (SEP)
  but are outside the inner belt. HEO missions cross the belts during
  apogee passes and add SEP exposure at high altitude. Interplanetary
  missions are dominated by SEP and galactic cosmic rays (GCR) with no
  belt contribution. GCR contributes a low but non-negligible TID to all
  mission types.
- §7.3 and Table 7-1 group device technologies by TID sensitivity. Bipolar
  linear ICs and opto-couplers carry high sensitivity; some bipolar devices
  also exhibit enhanced low dose-rate degradation (ELDRS), requiring testing
  at a representative low dose-rate rather than at the accelerated rate used
  for other technologies. CMOS bulk, power MOSFETs, and CMOS SOI carry
  moderate sensitivity. GaAs MESFETs, HEMTs, passive components, and quartz
  oscillators carry low sensitivity. A technology's sensitivity level
  determines the rigour of the dose-rate test protocol and the scrutiny
  applied to margin allocation.
- §7.4 fixes the minimum TID test level at margin_factor × design_dose,
  where margin_factor must be at least 2.0 for standard programmes. The
  design dose is the environment-predicted total dose at the part location
  (including shielding) over the full mission duration.

## Workflow

1. Identify the orbit type and mission duration. Reject any orbit type that
   does not fall within the recognised set (LEO, MEO, GEO, HEO,
   interplanetary) before proceeding — an unrecognised orbit has no mapped
   environment contributors and cannot support a valid basis.
2. Retrieve the TID-contributing environments for the orbit from the
   environment map (§7.2 analogue). Record each contributor with its key
   and description so the basis record is traceable. All contributors must
   be accounted for; omitting bremsstrahlung in a MEO mission, for example,
   understates the shielding requirement.
3. List every device technology in scope for the programme. For each one,
   look up its TID sensitivity level (high/moderate/low) from the technology
   table (§7.3 / Table 7-1 analogue). Flag any technology not found in the
   programme database as a finding that must be resolved before the basis is
   accepted — an unknown technology cannot be grouped, so its margin
   requirement is undefined.
4. For each high-sensitivity bipolar technology, add a finding that low
   dose-rate (ELDRS) testing is required per §7.3. This finding does not
   block basis acceptance but must appear in the assessment plan.
5. Apply the margin factor (minimum 2.0) to the design dose to derive the
   minimum TID qualification test level. Reject any margin factor below 2.0
   with an explicit error — reducing the margin below the floor requires a
   formal tailoring request, which is outside the scope of the standard
   assessment basis workflow.
6. Assemble the TID basis record: orbit type, mission duration, environment
   list, technology entries with sensitivity levels, minimum test level,
   margin factor, and findings list. Mark the record complete only when no
   unknown-technology or incomplete-assessment findings remain and the
   minimum test level is positive. An incomplete record must not advance to
   dose calculation.

## Pitfalls

- Omitting GCR from the environment list because its TID contribution is
  small — GCR is always present and must appear in the basis; its
  contribution is small but not zero, and it is the dominant source for
  very long interplanetary missions in deep solar minimum.
- Treating all technologies as equivalent sensitivity and applying a single
  flat test level — the sensitivity grouping in §7.3 / Table 7-1 exists
  precisely to tailor the dose-rate protocol; collapsing the groups either
  over-tests low-sensitivity passives or under-tests ELDRS-prone bipolar
  devices.
- Accepting a margin factor below 2.0 without a recorded tailoring
  justification — §7.4 sets 2.0 as the floor for a reason: it absorbs
  environment-model uncertainty and part-to-part variation simultaneously.
  Silently accepting a lower value invalidates the qualification argument.
- Proceeding to dose calculation before all technologies are resolved in the
  database — an unresolved technology has no sensitivity grouping and no
  applicable dose-rate protocol, leaving the assessment with an
  uncharacterised exposure risk.
- Omitting bremsstrahlung as a separate contributor in electron-dominated
  orbits (GEO, MEO) — bremsstrahlung from trapped electrons penetrates
  shielding differently than primary particles and must be listed so the
  transport calculation includes it.

## Behavior contract (gate 3)

The environment-identification, technology-sensitivity-grouping,
minimum-test-level derivation, and basis-record assembly logic is exercised
by the gate 3 contract test: scripts/test_e1012_tid_basis.py against
scripts/e1012_tid_basis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_tid_basis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
