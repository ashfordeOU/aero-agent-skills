---
name: e5053-status-code
description: "Evaluate the status code a sending node writes into a CCSDS packet transfer protocol data unit on SpaceWire under ECSS-E-ST-50-53C clause 5.1.3: check the encoding fits the one octet field, group it against the deployment code assignment as success, a defined error, user-defined, unassigned or reserved, decide whether the receiving node accepts, reports or rejects the transfer, and summarise a run of received codes. Use when a receiver meets a status encoding it did not expect. Trigger: ecss, e-st-50-53-spacewire-ccsds-scope, ccsds-transfer-status-code, reserved-status-encoding, unassigned-status-encoding, transfer-error-reporting, status-code-registry."
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
  tags: [ecss, e-st-50-53-spacewire-ccsds-scope, e5053-status-code, ccsds-transfer-status-code, reserved-status-encoding, unassigned-status-encoding, transfer-error-reporting, status-code-registry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Status Code (space-systems/ecss/e5053-status-code)

Use when the task is the status code field of the CCSDS packet transfer
protocol data unit of ECSS-E-ST-50-53C clause 5.1.3 — what a sending node is
allowed to put in it, and what a receiving node has to do with an encoding it
does not recognise.

## Domain quick reference

- The status field reports the outcome of the transfer it accompanies. It
  says nothing about the carried packet's content and nothing about the
  SpaceWire link itself, so a clean status is not evidence that the packet
  inside is well formed.
- The field is one octet. Every encoding it can hold falls into exactly one
  of five groups once a code assignment exists: the single success
  encoding, encodings the protocol assigns to named error conditions,
  encodings a project has taken for its own use, encodings nothing has been
  assigned to yet, and encodings held reserved.
- Only the first three groups may be emitted. An unassigned or reserved
  encoding arriving at a receiver is evidence of a sender fault, a stale
  code table or a corrupted field, and none of those is a transfer that
  should be handed upward.
- Reading anything other than the success encoding as success is the
  failure mode this clause exists to prevent. A receiver that tests for a
  known error list and treats everything else as good will accept exactly
  the encodings it has never seen before.
- The code assignment belongs to the deployment, not to this module. State
  the bands explicitly and validate them for overlap; a registry whose
  bands overlap makes categorisation depend on scan order rather than on
  the assignment.

## Workflow

1. Validate the received encoding against the width of the field. A value
   that does not fit one octet is a parsing fault upstream, not a status.
2. Build or accept the code registry for the deployment, checking that the
   defined-error, user-defined and reserved bands do not overlap each other
   and that none of them swallows the success encoding.
3. Group the encoding: success, defined error, user-defined, unassigned or
   reserved. An encoding that falls in no band is unassigned, and that is a
   real outcome, not a default to success.
4. Decide the disposition. Success is accepted; a defined error is reported
   upward with its encoding intact; reserved and unassigned encodings are
   rejected; a user-defined encoding follows the receiving node's declared
   policy rather than a silent assumption.
5. Record whether the encoding was one a sender was allowed to emit at all,
   separately from what the receiver does with it, so a sender fault is
   attributable.
6. Over a run of transfers, count the outcomes by group, keep the index of
   the first non-success transfer, and report the error fraction so an
   intermittent fault is visible as a rate rather than one bad frame.

## Pitfalls

- Testing for a list of known error encodings and accepting everything
  else. That inverts the obligation: an encoding is acceptable because it
  is assigned, not because it is unfamiliar.
- Treating a user-defined encoding as if the transfer protocol gave it a
  meaning. It carries project meaning only; accepting it is a policy
  decision that belongs in the receiving node's configuration and should be
  recorded as a limitation when it is taken.
- Letting the registry bands overlap. Once two bands claim the same
  encoding, the group returned depends on the order the bands are scanned
  in, and two implementations of the same table will disagree.
- Collapsing the reserved group into unassigned. They have different
  causes: a reserved encoding was deliberately set aside, an unassigned one
  simply has no meaning yet, and the corrective actions differ.
- Reporting a status error as a link error. The status field is written by
  the sending application layer; a fault it reports is not evidence that
  the SpaceWire transfer itself failed.

## Behavior contract (gate 3)

The one-octet field check, registry construction and overlap refusal, the
five-way grouping, the accept, report and reject dispositions, the
emittability test and the run summary are exercised by the gate 3 contract
test: scripts/test_e5053_status_code.py against
scripts/e5053_status_code_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5053_status_code.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
