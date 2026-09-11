---
name: e1011-habitable-env
description: "Use when evaluate crew habitable environments under ECSS-E-ST-10-11C §4.7.1–4.7.2: verify net habitable volume per crew member against the minimum per-person threshold, assess atmospheric parameters (oxygen partial pressure, carbon dioxide partial pressure, total cabin pressure, temperature, relative humidity) against allowable bands, check layout provisions for emergency egress paths and workstation accessibility, and confirm hygiene-system allocations are on record for each compartment. The skill aggregates findings per compartment and flags every non-compliant or unrecorded item before the design review. Trigger: ecss, e-st-10-11c, habitable-environment, crew-provisions, atmospheric-habitability, volume-allocation, layout-design, hygiene."
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
  tags: [ecss, e-st-10-11c, habitable-environment, crew-provisions, atmospheric-habitability, volume-allocation, layout-design, hygiene]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Habitable Environment Design (space-systems/ecss/e1011-habitable-env)

Use when the task is to evaluate the habitability of a crewed spacecraft
compartment against ECSS-E-ST-10-11C §4.7.1–4.7.2 — verifying that net
habitable volume, atmospheric parameters, layout provisions, and hygiene
allocations all meet their respective thresholds before the design review.

## Domain quick reference

- **Net habitable volume** is the pressurized free volume available to
  the crew after accounting for fixed structures, equipment racks, and
  stowage. ECSS-E-ST-10-11C §4.7.1 ties a minimum per-person threshold
  to mission duration; for the purposes of this skill the operational
  lower bound is 11.3 m³ per crew member. Compartments below that
  threshold are flagged regardless of any compensating factor.
- **Atmospheric parameters** (§4.7.2) govern physiological safety and
  comfort. Five parameters are checked independently against their
  allowable bands:
  - Oxygen partial pressure: 19.5–23.1 kPa
  - Carbon dioxide partial pressure: < 0.5 kPa (upper limit only)
  - Total cabin pressure: 70.0–102.7 kPa
  - Cabin temperature: 18.0–27.0 °C
  - Relative humidity: 25.0–75.0 %
  A parameter outside its band is a finding even if all other parameters
  are nominal; the five checks are independent.
- **Layout provisions** cover emergency egress and workstation
  accessibility. Each habitable compartment must have at least one
  defined egress path, and at least one workstation per crew member
  allocated to that compartment.
- **Hygiene provisions** must be allocated per compartment: waste
  management, personal hygiene facilities, and a potable water
  dispenser. A compartment is not evaluated as habitable until all three
  are on record — a missing entry is a finding, not a pass.

## Workflow

1. For each habitable compartment, collect the net volume (m³) and the
   number of crew members assigned to it. Compute the volume per person;
   flag the compartment immediately if that ratio falls below 11.3 m³.
2. Collect the five atmospheric parameters for the compartment's nominal
   operating point. Check each parameter against its allowable band
   independently and record every out-of-band value as a separate
   finding.
3. Confirm the number of defined emergency egress paths (≥1) and the
   number of workstations allocated (≥ crew count). Record a finding for
   each shortfall.
4. Verify that all three required hygiene provisions (waste management,
   personal hygiene, water dispenser) are on record for the compartment.
   Record a finding for each missing provision.
5. Aggregate all findings for the compartment. The compartment is
   habitable-compliant only when the finding list is empty. Report the
   compartment identifier, compliance status, and the full finding list.

## Pitfalls

- Treating the volume threshold as a total-spacecraft limit rather than
  a per-crew-member-per-compartment limit — the 11.3 m³ floor applies
  per person in the compartment being evaluated, not shared across the
  entire vehicle.
- Checking atmospheric parameters as a single combined condition and
  passing the compartment when most values are nominal — each of the
  five parameters must pass independently; a CO2 spike is a finding
  regardless of all other parameters being in-band.
- Counting egress corridors that pass through another pressurized module
  as valid egress paths without verifying the intermediate module is
  reachable during the emergency scenario; the check here is that at
  least one egress path is defined, not that all paths are independently
  evaluated for reachability.
- Deferring the hygiene-provision check to a later review on the grounds
  that the allocation document is not yet final — an unrecorded
  provision is a finding against the compartment evaluation, not a
  pending action item.

## Behavior contract (gate 3)

The volume, atmospheric, layout, and hygiene-provision logic is
exercised by the gate 3 contract test:
scripts/test_e1011_habitable_env.py against
scripts/e1011_habitable_env_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_habitable_env.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
