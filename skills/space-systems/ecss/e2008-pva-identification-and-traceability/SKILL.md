---
name: e2008-pva-identification-and-traceability
description: "Trace the non-cell components of a photovoltaic assembly under ECSS-E-ST-20-08C clause 5.4.4. Use when identification and record keeping have to be shown before build records are accepted: match each component form to an identification carrier that can physically survive its processing, walk the production route to the step where identity stops being transcribed, verify a lot identifier exists for the chain to point back to, resolve the assemblies a suspect lot reached, and name the component whose records are weakest. Trigger: ecss, e-st-20-08c, non-cell-component-traceability, photovoltaic-assembly-identification-marking, lot-identifier-record-keeping, production-route-identity-chain, suspect-lot-recall-scope, travelling-record-transcription, bulk-consumable-batch-identity."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-pva-identification-and-traceability, non-cell-component-traceability, photovoltaic-assembly-identification-marking, lot-identifier-record-keeping, production-route-identity-chain, suspect-lot-recall-scope, bulk-consumable-batch-identity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Identification and Traceability (space-systems/ecss/e2008-pva-identification-and-traceability)

Use when the task is the identification and record-keeping duty of
ECSS-E-ST-20-08C clause 5.4.4 -- making every part of an assembly that
is not a cell chaseable in both directions: from a suspect lot forward
to the assemblies that consumed it, and from a delivered assembly back
to the lots it was built from.

## Domain quick reference

- Cells are serialised as a matter of course. Coverglass,
  interconnector stock, adhesive, substrate laminate, wiring and bypass
  diodes are not, so their identity has to be carried by something
  else, and that something has to survive the process the part goes
  through.
- Component form decides what identification is physically possible. A
  discrete part can carry its own mark. Continuous stock can be marked
  at the reel, but the mark is lost the moment the stock is sectioned.
  A bulk consumable has no part to mark at all; its identity lives on
  the container and, after dispensing, only on the record.
- Identity carrier, strongest to weakest: permanent-part-marking (the
  item carries its own identity), tagged-container (the identity lives
  on the packaging), travelling-record-only (the identity lives on
  paperwork alone), and unmarked. The carrier sets the best resolution
  available -- part-level or batch-level -- and nothing downstream can
  improve on it.
- The chain matters more than the mark. Identification that is not
  transcribed at a production step ends at that step, and every step
  past the break is untraceable however well the part was marked on
  arrival. A later step that records identity does not repair the
  break; it records an identity nobody can substantiate.
- A lot identifier is what the chain points back to. A component with
  a perfect marking scheme and no recorded lot is a component whose
  records lead nowhere.
- The forward direction is the one an anomaly needs. Given a suspect
  lot, the build records have to return the set of assembly serials
  that consumed it, and a build record that lists no lots removes its
  assembly from every recall the records can compute.

## Workflow

1. List every non-cell component of the assembly with its form, its
   declared identification carrier and its lot identifier. Reject a
   declared part marking on a bulk consumable; there is no part to
   carry it and the declaration hides the real carrier.
2. Resolve what each carrier actually delivers: the identity resolution
   it can reach and whether it survives the processing the component
   sees. Record the demotions -- sectioned stock and dispensed
   consumables both fall back to batch identity.
3. Walk the production route in order and find the first step that does
   not transcribe identity. Report that step by name and the share of
   the route that retains the link, so the repair is aimed at a step
   rather than at the whole route.
4. Fail a component with no recorded lot identifier outright, whatever
   its marking and whatever its route.
5. Grade each component: traceable to the part, traceable to its batch
   only, or trace-broken. Roll the assembly up to the weakest component
   and name it.
6. Exercise the forward direction on the build records: pick a lot and
   confirm the records return every assembly that consumed it, with no
   build record left lotless.

## Pitfalls

- Grading the marking scheme and stopping there. A reel-marked ribbon
  looks fully identified in the stores and is anonymous the moment it
  is cut, so the adequacy question is always the carrier against the
  process, never the carrier alone.
- Counting steps that record identity rather than the steps before the
  break. A route that drops identity at kitting and diligently records
  it at three later steps is traceable for one step, not four; summing
  the flags reports the opposite.
- Treating a travelling record as equivalent to a physical mark. It is
  the only carrier with no fallback: one missed transcription and there
  is nothing on the hardware to recover the identity from.
- Building the records for the backward direction only. An assembly
  that can list its lots is not the same as a lot that can list its
  assemblies, and an anomaly needs the second one under time pressure.
- Accepting a build record with no lots as merely incomplete. It
  silently shrinks every recall the records can compute, because the
  assembly is absent from the answer rather than flagged in it.

## Behavior contract (gate 3)

The carrier adequacy, identity-chain walk, lot-identifier check,
component grading, forward recall scope and assembly roll-up are
exercised by the gate 3 contract test:
scripts/test_e2008_pva_identification_and_traceability.py against
scripts/e2008_pva_identification_and_traceability_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_pva_identification_and_traceability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
