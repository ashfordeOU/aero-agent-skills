---
name: e5052-error-codes
description: "Determine which status a SpaceWire RMAP target reports and whether the reply agrees with it. Use when an ECSS-E-ST-50-52C clause 5.6 error-code question arises: look a status value up in the registry for its slug and fault family, walk the detection precedence so a command that trips several conditions is answered with the one a target settles on, decide whether a reply leaves the target at all when the header cannot be trusted, check that a failure status carries no returned data and that no value kept aside is reported, then summarise a run of transactions by family. Trigger: ecss, e-st-50-52c, rmap-status-code-registry, rmap-error-detection-precedence, rmap-silently-dropped-command, rmap-reserved-status-value, rmap-reply-status-consistency, rmap-fault-family-summary."
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
  tags: [ecss, e-st-50-52-rmap-scope, e5052-error-codes, rmap-status-code-registry, rmap-error-detection-precedence, rmap-silently-dropped-command, rmap-reserved-status-value, rmap-fault-family-summary]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire RMAP — Error Codes (space-systems/ecss/e5052-error-codes)

Use when the task is the error-code set of ECSS-E-ST-50-52C clause 5.6 —
deciding which single status a target puts in a reply, whether a reply
is sent at all, and whether a captured reply is self-consistent with the
status it carries.

## Domain quick reference

- The status field carries one value, not a list. A command can trip
  several conditions at once — a rejected key on a packet that also
  ended early — and the target still reports one of them, so the order
  in which conditions are detected is part of the specification, not an
  implementation choice.
- The order runs outwards in. Whether the packet reached the right
  target comes before whether the sender was entitled to command it,
  which comes before whether the command code means anything, which
  comes before whether the payload survived. A target that reports a
  payload fault on a command it should have rejected on the key has
  answered the wrong question.
- One condition produces no status at all. If the header check fails,
  nothing in the header can be relied on — including the fields a reply
  would be addressed with — so the command is dropped and the initiator
  learns of it by timeout rather than by status.
- A failure reply carries no data. Anything read out of the payload of a
  reply whose status is non-zero is whatever the buffer held before, so
  a non-zero status with a non-zero returned length is a defect in the
  target, not a partial result.
- Values outside the defined set are kept aside, not free. A target that
  reports one has invented a code an initiator cannot act on, and an
  initiator that grades one as a generic failure has hidden a defect.
- Fault families are what a campaign is read by. Routing, authorisation,
  command and payload faults point at different parts of the system, and
  a run that is all authorisation faults is a key-management problem
  rather than a link problem.

## Workflow

1. Normalise the observed conditions into the known condition tokens. An
   unrecognised token is an input error, because a condition nobody
   named cannot be placed in the detection order.
2. Walk the detection order and take the first condition present. When
   that condition is the untrusted header, the answer is that no status
   exists and no reply is built.
3. Decide separately whether a reply leaves the target: an untrusted
   header silences it, and so does a command that asked for no
   acknowledgement.
4. Look the reported value up for its slug and family, and grade a
   reported value that is kept aside as a finding in its own right.
5. Compare the reported value with the one the observed conditions call
   for, and check the returned length against the status: zero bytes
   whenever the status is not success.
6. Roll a run of transaction records into per-family counts plus a count
   of the commands dropped without a reply, and index every finding by
   the record it came from.

## Pitfalls

- Reporting the last condition detected rather than the first in the
  order. Later conditions are usually consequences of earlier ones, and
  reporting a consequence sends the investigation to the wrong place.
- Treating a dropped command as a link fault. A command dropped for an
  untrusted header never produced a status, so the initiator sees a
  timeout; reading that timeout as a lost packet hides a corrupted
  header the link layer did not catch.
- Reading data out of a failed reply. The payload of a non-zero-status
  reply is not a partial result and concatenating it with a retry
  produces a buffer that never existed in the target.
- Folding a value kept aside into a generic failure bucket. It is
  evidence that a target is reporting outside the defined set, and the
  bucket makes it disappear.
- Counting faults without their families. A total fault count says
  nothing about where to look; the same count split across routing,
  authorisation, command and payload families usually names the
  subsystem outright.

## Behavior contract (gate 3)

The registry lookups, family assignment, reserved-value handling,
condition normalisation, detection precedence, reply-or-drop decision,
reply consistency checks and run summary are exercised by the gate 3
contract test: scripts/test_e5052_error_codes.py against
scripts/e5052_error_codes_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5052_error_codes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
