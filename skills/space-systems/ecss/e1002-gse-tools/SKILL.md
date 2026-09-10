---
name: e1002-gse-tools
description: "Use when ground support equipment (GSE) will interface with flight hardware during verification and needs to be qualified as verification tooling before use, consistent with ECSS-E-ST-10-02C clause 5.2.6.2 (GSE qualification) and the general tool-qualification regime of clause 5.2.6.1. Classifies GSE as mechanical (MGSE) or electrical (EGSE) and determines the required qualification actions (interface control document, proof test, periodic re-proof, interface safety verification, calibration with traceability). Trigger: GSE, ground support equipment, MGSE, EGSE, proof test, handling equipment, test stimulation equipment, tool qualification, E-ST-10-02, verification tooling, ecss, e-st-10c."
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
  tags: [ecss, e-st-10c, gse, mgse, egse, verification-tooling, tool-qualification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS GSE Qualification for Verification Tooling (space-systems/ecss/e1002-gse-tools)

Use when the task is qualifying ground support equipment (GSE) that
will be used as verification tooling under ECSS-E-ST-10-02C, ahead of
letting that GSE contact, handle, stimulate, or measure flight
hardware.

## Domain quick reference

- ECSS-E-ST-10-02C clause 5.2.6.2 requires GSE used in verification to
  itself be qualified before it interfaces with flight hardware,
  extending the general tool-qualification regime of clause 5.2.6.1
  (see the sibling e1002-tools-general leaf).
- GSE splits into two classes: MGSE (mechanical GSE -- handling,
  lifting, transport, alignment fixtures, protective covers) and EGSE
  (electrical GSE -- test stimulation, simulation, power supplies,
  signal/checkout equipment, harnesses).
- MGSE that physically contacts the flight item carries a structural
  risk and needs a proof test (loaded above design load) before first
  use, plus periodic re-proof (after modification, or once usage since
  the last proof reaches the item's allowed limit).
- EGSE that electrically interfaces the flight item carries an
  over-stress risk and needs an interface safety verification
  confirming it cannot deliver an out-of-spec stimulus to the flight
  item.
- Any GSE acting as the measurement or stimulus of record for a formal
  verification result -- of either class -- needs calibration with
  traceability, because its accuracy directly bounds the verification
  result's credibility.
- Any GSE that contacts or interfaces the flight item, of either
  class, needs an interface control document (ICD) so that GSE
  configuration changes are tracked like a flight interface change.

## Workflow

1. For each GSE item used in the verification programme, record its
   primary function, whether it contacts or otherwise interfaces the
   flight item, and whether it is the measurement or stimulus of
   record for a formal verification result.
2. Classify the GSE as MGSE or EGSE from its primary function.
3. Derive the required qualification actions for the item: ICD if it
   interfaces the flight item; proof test and periodic re-proof if it
   is MGSE that contacts the flight item; interface safety
   verification if it is EGSE that interfaces the flight item;
   calibration with traceability if it is the measurement/stimulus of
   record.
4. Build the GSE register: one classification and required-action set
   per GSE id, and confirm no GSE id used in the verification
   programme is missing from the register.
5. Before releasing any GSE item for use with flight hardware, check
   its required actions against the actions actually completed and
   block use on any gap; treat an item with no completion record as
   fully unqualified rather than assuming it is covered.
6. For MGSE items requiring periodic re-proof, track modification and
   usage-since-last-proof and flag any item due for re-proof (or with
   no re-proof status on record) before its next use.
7. Hand the register and any measurement-chain GSE ids to the
   Verification Plan tooling section (E-ST-10-02 clause 5.2.8.1) and
   to the general tool-qualification record (e1002-tools-general).

## Pitfalls

- Letting MGSE contact flight hardware without a proof test, or
  treating an old proof test as still valid after a modification.
- Treating EGSE as risk-free because it does not touch the flight item
  mechanically, and skipping the interface safety verification for a
  stimulus or power interface.
- Missing that GSE serving as the sensor of record for a verification
  measurement needs its own calibration and traceability, even when
  its class would not otherwise require special qualification.
- Assuming a GSE item with no completion or re-proof record is fine to
  use, instead of treating the missing record as a qualification gap.

## Behavior contract (gate 3)

The classification, required-action, register-completeness, and
re-proof-due logic is exercised by the gate 3 contract test:
scripts/test_e1002_gse_tools.py against
scripts/e1002_gse_tools_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_gse_tools.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
