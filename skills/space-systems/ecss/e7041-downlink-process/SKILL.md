---
name: e7041-downlink-process
description: "Plan the downlink of one large message under ECSS-E-ST-70-41C clause 6.13.3.3: split it into a first part, the intermediate parts and a last part, number them from one, verify the plan covers the message contiguously with no oversized part, open the transaction identifier against the active set, and produce the truncated part run and abort report when the transfer fails part way. Use when a service 13 downlink part run, its part numbering, its coverage or its abort behaviour is being designed or reviewed. Refuses a message that fits one part and an unnamed abort reason. Trigger: ecss, e-st-70-41c, pus-service-13, large-message-downlink-process, first-intermediate-last-part, part-sequence-numbering, downlink-abort-report, transaction-identifier-reuse."
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
  tags: [ecss, e-st-70-41c, pus-service-13, e7041-downlink-process, large-message-downlink-process, first-intermediate-last-part, part-sequence-numbering, downlink-abort-report, transaction-identifier-reuse]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Large Packet Transfer — Downlink Process (space-systems/ecss/e7041-downlink-process)

Use when the task is the downlink process of ECSS-E-ST-70-41C clause 6.13.3.3
— turning one large message into the ordered run of first, intermediate and
last part reports the subservice sends, checking that the run really covers
the message, and defining what the subservice emits when the transfer has to
be abandoned before its last part.

## Domain quick reference

- A downlink transaction has exactly three part roles and only one shape: one
  first part, zero or more intermediate parts, one last part. The role is not
  cosmetic; the receiving end uses it to open its reassembly, to continue it
  and to close it, so a run with two firsts or no last is not a transfer.
- Part numbers run from one and increase by one with no gaps. A gap is
  indistinguishable at the receiver from a lost part, so a numbering scheme
  that skips a value turns a healthy downlink into an apparent failure.
- Only the last part is allowed to be short. Every earlier part carries the
  full part size, because a short intermediate part is how the receiver
  detects truncation, and a process that emits one deliberately spends that
  detector.
- A message that fits inside a single part has no first and last to send. It
  is a plain report, and the downlink process refuses it rather than
  manufacturing a degenerate two-part run.
- An abort is a real outcome, not an error return. The parts already sent
  stay sent, the run stops where it stopped, and the subservice emits an
  abort report naming the transaction and the reason so the ground can
  distinguish an abandoned transfer from a silent one.
- The transaction identifier is what ties the run together. Reusing one that
  is still open merges two messages at the receiver, so the identifier is
  claimed when the first part is generated and released only at the last part
  or at the abort.

## Workflow

1. Validate the message size and the part size as whole positive octet
   counts, and refuse a message that does not exceed one part.
2. Compute the part count by ceiling division and lay out the run: sequence
   one is the first part, the final sequence is the last part, everything
   between is an intermediate part, each with its offset into the message.
3. Give every part its octet count: the part size for all but the final one,
   the remainder for the last.
4. Verify the laid-out run independently of how it was built: one first at
   sequence one, one last at the final sequence, contiguous numbering,
   contiguous offsets, no part above the part size, no short intermediate
   part, and octets summing to the message size.
5. Claim the transaction identifier against the set already open, refusing a
   reuse while the earlier transfer is still in progress.
6. When the transfer fails, truncate the run before the failing sequence and
   build the abort report from the transaction identifier, the sequence the
   process stopped at and a named reason drawn from the recognised set.
7. Report the part run, the per-role report counts, the abort outcome when
   there is one, and every finding raised by the verification.

## Pitfalls

- Numbering the parts from zero. The first part is part one, and an
  off-by-one at the sender makes every part number disagree with the
  receiver's expectation for the whole transfer.
- Padding the last part to the full part size. The receiver sizes the
  reassembled message from the octets it was given, so padding either
  corrupts the message or forces a length field the transfer does not carry.
- Emitting a short intermediate part to align the run to a convenient
  boundary. That is exactly the signature of a truncated transfer and the
  receiver is entitled to treat it as one.
- Treating an abort as a discard. The parts already sent are already on the
  downlink; the ground needs the abort report to know why the rest never
  arrived, and a silent stop leaves a half message with no explanation.
- Releasing the transaction identifier when the last part is queued rather
  than when the transfer ends. An identifier reused a moment early is
  attached to two different messages at the receiver.

## Behavior contract (gate 3)

The message validation, part run layout, role assignment, independent run
verification, identifier claim, abort truncation and the assembled downlink
assessment are exercised by the gate 3 contract test:
scripts/test_e7041_downlink_process.py against
scripts/e7041_downlink_process_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_downlink_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
