---
name: e1012-see-env-tech
description: "Use when define SEE-relevant mission orbit environments and electronic technology susceptibility profiles under ECSS-E-ST-10-12C §9.2–9.3: categorize the mission orbit as LEO, MEO, GEO, HEO, interplanetary, or lunar to determine the dominant particle population (trapped protons, heavy ions, galactic cosmic rays, solar particle events), map each candidate technology (CMOS, BiCMOS, SRAM, DRAM, Flash, FPGA, power MOSFET, linear bipolar) to its applicable SEE types (SEU, SET, SEFI, SEL, SEB, SEGR), and flag technologies with destructive SEE risk requiring protective controls. Trigger: ecss, e-st-10-system-scope, see, single-event-effects, orbital-environment, technology-susceptibility, sel, seb, segr, seu, table-9-1."
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
  tags: [ecss, e-st-10-system-scope, see, single-event-effects, orbital-environment, technology-susceptibility, sel, seb, segr, seu, table-9-1]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — SEE Environments and Susceptible Technologies (space-systems/ecss/e1012-see-env-tech)

Use when the task is to define the SEE-relevant radiation environments and
identify which electronic technologies are susceptible to Single Event Effects
(SEE) per ECSS-E-ST-10-12C §9.2–9.3 and the Table 9-1 technology-to-SEE
mapping. The workflow categorizes the mission orbit, establishes the dominant
particle population, maps each technology type to its applicable SEE effect
categories, and flags any technology carrying destructive SEE risk.

## Domain quick reference

- §9.2 covers the radiation environments that drive SEE. Six orbit regimes
  are distinguished by their particle population: LEO (trapped protons and
  heavy ions from the inner belt, partial cosmic ray exposure), MEO (peak
  trapped proton and electron fluences, significant galactic cosmic ray and
  solar particle event exposure), GEO (no trapped belts; heavy ions and
  protons from galactic cosmic rays and solar particle events dominate), HEO
  (passes through trapped belts on each perigee pass; all particle types
  relevant), interplanetary (outside Earth's magnetosphere; full galactic
  cosmic ray and solar particle event flux), and lunar (no magnetospheric
  shielding; same as interplanetary plus secondary particles from surface
  interactions).
- §9.3 and Table 9-1 map technology families to the SEE types each is
  susceptible to. CMOS and BiCMOS: SEU, SET, SEFI, and SEL — SEL is
  potentially destructive if supply current is not limited. Bipolar and linear
  bipolar: SET and SEU — no latch-up path; SET dominates in analog circuits.
  SRAM and DRAM: SEU and SEFI — SRAM has higher cross-section per bit.
  Flash: SEU and SEFI — SEFI can corrupt an entire block. FPGA: SEU, SET,
  SEFI — configuration-memory SEU can silently alter circuit behaviour and
  requires periodic scrubbing. Power MOSFET: SEB and SEGR — both are
  destructive; relevant in power converters and switching regulators.
- SEE types fall into two severity groups: non-destructive (SEU, SET, SEFI —
  correctable or tolerable with mitigation) and destructive (SEL, SEB, SEGR,
  SEHE — can permanently damage the device and require design controls such
  as current limiting, derating, or lot screening).

## Workflow

1. Identify the mission orbit regime from the mission definition and look it
   up in the §9.2 environment table. Confirm which particle populations are
   dominant (trapped protons, trapped electrons, heavy ions, galactic cosmic
   rays, solar particle events). An orbit that passes through multiple regimes
   (e.g. HEO sweeping from LEO altitudes to GEO and beyond) must be assessed
   against the most severe regime encountered.
2. List all candidate electronic technology families present in the design —
   at minimum: logic process (CMOS, BiCMOS, bipolar), memory types (SRAM,
   DRAM, Flash), programmable devices (FPGA), and any power switching
   devices (power MOSFET). Reject any unrecognized technology before
   proceeding; the assessor must explicitly confirm the family mapping.
3. For each technology, retrieve the applicable SEE types from the §9.3
   Table 9-1 analogue. Assign every effect from the table row; do not drop
   effects because they seem unlikely for the chosen orbit — the table is
   technology-driven, not orbit-driven.
4. Flag every technology that carries at least one destructive SEE type
   (SEL, SEB, SEGR, SEHE). For each flagged technology, confirm that a
   design control is specified — current limiting for SEL, voltage derating
   and lot screening for SEB/SEGR. A destructive-risk technology without a
   documented control is a non-conformance at this step.
5. Record the combined orbit–technology matrix: orbit regime, dominant
   particles, technology family, applicable SEE types, destructive flag,
   and control status. This matrix is the input to the SEE rate analysis
   (e1012-rdm-see) and the SEE margins leaf (e1012-see-margins).

## Pitfalls

- Dropping SEE types because the orbit seems benign: the Table 9-1 mapping
  is based on technology physics, not orbit. CMOS in LEO still has SEL risk
  even though LEO trapped-belt heavy-ion flux is lower than in MEO; the
  control requirement stands regardless of expected rate.
- Treating all orbit regimes as equivalent: MEO has the highest trapped
  proton fluence of any Earth orbit; collapsing it into a generic
  "Earth-orbit" assessment understates proton-SEE risk significantly.
- Treating SEL as non-destructive because the device survived a test pulse:
  SEL causes a sustained high-current state; without a current-limiting
  circuit, thermal runaway and permanent destruction can follow a single
  event in orbit. The presence of SEL in the technology family requires a
  documented current-limiting control even when the test-pulse LET
  threshold was not reached in ground testing.
- Omitting power MOSFETs from the SEE susceptibility inventory: SEB and
  SEGR occur at lower LETs than CMOS latch-up and are directly proportional
  to the drain–source voltage; power converters using commercial-grade
  MOSFETs without SEB/SEGR derating are a common gap in early-phase
  assessments.

## Behavior contract (gate 3)

The environment categorization, technology susceptibility assessment,
orbit-to-technology mapping, and destructive-effect identification logic
are exercised by the gate 3 contract test:
scripts/test_e1012_see_env_tech.py against
scripts/e1012_see_env_tech_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_see_env_tech.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
