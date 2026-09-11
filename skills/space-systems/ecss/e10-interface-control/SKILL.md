---
name: e10-interface-control
description: "Use when you identify and control system-level interfaces under ECSS-E-ST-10C clause 5.6.4: catalog each interface between two interfacing elements, classify its physical domain (mechanical, electrical, thermal, data, fluid) and reject an unrecognized domain, determine whether it crosses an internal or external responsibility boundary and which control document ECSS-E-ST-10-24 requires as a result, draft the interface requirement document (IRD) before the interface matures, define the interface control document (ICD) baseline once it does, verify that both sides declare matching interface parameters, and manage the interface through its control status lifecycle from identified to verified without skipping a step. Trigger: ecss, e-st-10-system-scope, interface management, interface control document, interface requirement document, icd, ird, e-st-10-24."
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
  tags: [ecss, e-st-10-system-scope, interface-management, interface-control-document, interface-requirement-document, icd, ird, e-st-10-24]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Interface Management/Control (space-systems/ecss/e10-interface-control)

Use when the task is system-level interface management/control under
ECSS-E-ST-10C clause 5.6.4 -- identifying every interface between two
interfacing elements, determining the control document each interface
needs per ECSS-E-ST-10-24, and tracking that interface through its
control lifecycle from identification to verification.

## Domain quick reference

- An interface exists between exactly two interfacing elements and
  belongs to exactly one physical domain: mechanical, electrical,
  thermal, data, or fluid. A source pairing outside these five domains
  is rejected before it enters the register.
- An interface's responsibility boundary is internal (both interfacing
  elements sit under the same responsible owner) or external (the two
  elements have different responsible owners, e.g. a spacecraft-to-
  launcher or spacecraft-to-ground interface). The boundary determines
  the control document ECSS-E-ST-10-24 requires once the interface
  matures past drafting: an internal interface is controlled by a
  lighter-weight interface control note, an external interface must be
  controlled by a formal, configuration-baselined ICD.
- Every interface progresses through a fixed control status sequence:
  identified, ird_drafted, ird_agreed, icd_baselined, verified. The
  interface requirement document (IRD) captures the needed interface
  characteristics before design commitment; the interface control
  document (ICD) (or, for an internal interface, the interface control
  note) baselines the agreed, as-designed definition once the
  interface has matured. A status cannot advance more than one step at
  a time -- an interface cannot jump from identified straight to
  icd_baselined without first passing through the IRD steps.
- Each interfacing side declares its own parameter set for the
  interface (e.g. connector type, voltage, data rate, mounting
  envelope). The two declarations must agree key-for-key; a parameter
  present on only one side, or present on both with different values,
  is an unresolved interface definition, not a controlled one.

## Workflow

1. For each candidate interface, record the two interfacing elements
   and their responsible owners, and classify the interface's physical
   domain. Reject an unrecognized domain before the interface enters
   the register.
2. Determine the interface's responsibility boundary from the two
   owners: internal if they match, external if they differ. Use the
   boundary to look up the control document ECSS-E-ST-10-24 requires
   once the interface reaches baselining (ICD for an external
   interface, interface control note for an internal one).
3. Check the interface's current control status against the documents
   on record: an interface at ird_drafted or later must show an IRD on
   record; an interface at icd_baselined or later must additionally
   show the boundary-appropriate control document on record. Flag any
   status/document mismatch.
4. Compare the two sides' declared interface parameters key by key.
   Flag a parameter missing from one side and a parameter present on
   both sides with mismatched values.
5. When advancing an interface's status, verify the move is exactly
   one step forward along the fixed sequence (identified ->
   ird_drafted -> ird_agreed -> icd_baselined -> verified); reject a
   skipped step, a backward move, or an unrecognized status name.
6. Aggregate the documentation and parameter findings per interface;
   the interface is not under control until both lists are empty.

## Pitfalls

- Treating an internal interface as exempt from control -- it still
  needs an IRD and a baselined control record, just not the formal
  external ICD; only the required document changes with the boundary,
  not whether control is required at all.
- Letting an interface reach icd_baselined or verified while its two
  sides still declare different parameter values -- a status advance
  is not evidence that the definitions agree; check the parameters
  independently of the status.
- Allowing a status to jump straight from identified to icd_baselined
  because "the design is obviously done" -- the IRD steps exist to
  capture the interface requirement before the design commits to a
  specific ICD, and skipping them removes that checkpoint.
- Reporting an interface as controlled because an IRD exists, without
  checking whether the later-stage document (ICD or control note) was
  ever baselined -- an IRD is a precursor, not a substitute, for the
  baselined control record.

## Behavior contract (gate 3)

The domain-classification, boundary/required-document, status-
transition, and parameter-consistency logic is exercised by the gate 3
contract test: scripts/test_e10_interface_control.py against
scripts/e10_interface_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_interface_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
