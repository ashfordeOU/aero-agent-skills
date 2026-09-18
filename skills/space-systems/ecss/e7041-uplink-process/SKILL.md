---
name: e7041-uplink-process
description: "Model the on-board reassembly of an uplinked large message under ECSS-E-ST-70-41C clause 6.13.4.3: drive a receiver across a stream of first, intermediate and last uplink parts, hold one reception per transaction, and abort it on an unexpected part role, a duplicate or skipped part number, a short intermediate part, a reception buffer overflow, a silent gap past the inter-part timeout or a stream that ends mid transfer. Use when a service 13 uplink reassembly, its failure detection or its abort reporting is being designed or reviewed. Refuses a part stream whose timestamps move backwards. Trigger: ecss, e-st-70-41c, pus-service-13, large-message-uplink-process, uplink-part-reassembly, part-sequence-gap, inter-part-timeout, uplink-abort-reason."
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
  tags: [ecss, e-st-70-41c, pus-service-13, e7041-uplink-process, large-message-uplink-process, uplink-part-reassembly, part-sequence-gap, inter-part-timeout, uplink-abort-reason]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Large Packet Transfer — Uplink Process (space-systems/ecss/e7041-uplink-process)

Use when the task is the uplink process of ECSS-E-ST-70-41C clause 6.13.4.3 —
the on-board side that receives first, intermediate and last uplink parts,
reassembles the large message behind them, and decides when a reception has
failed and has to be abandoned with a named reason instead of being completed.

## Domain quick reference

- The receiver is a state machine with exactly two states per transaction:
  nothing open, or a reception in progress. Everything the clause asks for is
  a rule about which part is acceptable in which state, so the failures are
  enumerable rather than open-ended.
- A first part opens a reception. An intermediate or last part arriving with
  nothing open is not a recoverable start; the message it belongs to is
  already incomplete, so it is refused rather than used as an opening part.
- A second first part for an open reception is not a restart. It means the
  ground believes the earlier transfer is gone, and silently restarting would
  hide the loss of everything received so far.
- Part numbers are the detector. A repeat means a retransmission the service
  does not resolve, a skip means a part was lost, and both end the reception:
  the receiver cannot fill a hole it was never sent.
- Only the last part may be short. A short intermediate part is the signature
  of a truncated uplink, so accepting it would let a partial message be
  reassembled as if it were whole.
- Time is part of the contract. A reception holds a buffer and a transaction
  slot, so a gap longer than the inter-part timeout ends it and releases the
  resources rather than leaving the slot held for a transfer that stopped.
- A stream that simply stops is a failure too. A reception still open when
  the part stream ends never saw its last part, and reporting it as
  incomplete is what distinguishes it from a message that arrived whole.

## Workflow

1. Validate the receiver configuration: a positive part size, a positive
   reception buffer and, when one is declared, a positive inter-part timeout.
2. Validate every part record for shape and value, and refuse a stream whose
   timestamps move backwards, since that is an input defect rather than a
   reception failure.
3. Walk the stream in order. For each part, resolve the transaction it names
   and check the part role against the state of that reception.
4. Where a reception is open, check the part number against the one expected,
   the octet count against the part size and the short-part rule, the running
   total against the reception buffer, and the arrival time against the
   inter-part timeout.
5. On any violation, close the reception with an abort carrying the named
   reason and the part number that failed, and discard what had been
   assembled; on a valid last part, complete the reception and record the
   reassembled octet count.
6. When the stream ends, abort every reception still open as incomplete.
7. Report each transaction with its outcome, the octets accepted, the abort
   reason where there is one, and the accepted-part tally.

## Pitfalls

- Treating an intermediate part with nothing open as the start of a new
  reception. The parts before it are already lost, and the message that comes
  out of that reassembly is a fragment presented as a whole.
- Accepting a repeated part number as a harmless retransmission. The service
  gives the receiver no way to tell a duplicate from a resend of different
  data, so the reception ends rather than guessing.
- Letting a short intermediate part through because the total still fits.
  The short part is the truncation signal; the total is not, because the
  missing octets are never announced.
- Sizing the reception buffer from the expected message and omitting the
  overflow check. A ground error or a corrupted part count then writes past
  the buffer instead of aborting the reception.
- Leaving a stalled reception open. The transaction slot and the buffer stay
  held, and the next legitimate transfer on that transaction is refused for a
  resource that a timeout should already have released.
- Ending the stream and reporting silence as success. An open reception at
  the end of the stream is an incomplete message and has to be reported as
  one.

## Behavior contract (gate 3)

The configuration validation, part record validation, role and state rules,
sequence and size checks, buffer overflow, inter-part timeout, end-of-stream
sweep and the assembled uplink assessment are exercised by the gate 3
contract test: scripts/test_e7041_uplink_process.py against
scripts/e7041_uplink_process_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_uplink_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
