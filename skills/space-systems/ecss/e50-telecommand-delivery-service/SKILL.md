---
name: e50-telecommand-delivery-service
description: "Validate the telecommand delivery service of ECSS-E-ST-50C clause 5.4.2 against a real received frame stream: run each sequence number through a sliding acceptance window, separate the frame that is expected from one already delivered, one that arrived too early to be taken in turn, and one whose sender has lost track of the receiver entirely, then judge the whole stream on the promise that matters — delivered once, delivered in order, and nothing quietly dropped. Use when an uplink shows gaps, repeats or frames refused in flight. Trigger: ecss, e-st-50c-communications-scope, telecommand-delivery-service, telecommand-frame-sequence-window, out-of-sequence-telecommand, duplicate-telecommand-frame, telecommand-retransmission-request, uplink-sequence-counter-wrap."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.4.2
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50c-communications-scope, e50-telecommand-delivery-service, telecommand-delivery-service, telecommand-frame-sequence-window, out-of-sequence-telecommand, duplicate-telecommand-frame, telecommand-retransmission-request]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Telecommand Delivery Service (space-systems/ecss/e50-telecommand-delivery-service)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.4.2 —
that the telecommand chain provides a delivery service — and the question is
what that service must do with a frame stream that arrived imperfectly.

## Domain quick reference

- A delivery service is a promise about a stream, not about a frame. One
  frame that decodes cleanly proves nothing; the service is met when the
  frames handed upward are contiguous, in the order the ground sent them,
  and each handed up exactly once.
- Refusing a frame is part of the service, not a failure of it. A frame
  that arrived before the one it should follow cannot be delivered
  without breaking the order, so the correct action is to refuse it and
  let the ground send the missing one again.
- The three abnormal cases have three different meanings. Already seen
  means the ground repeated itself and no harm is done. Too early means
  something was lost and retransmission is owed. Far outside the window
  means the sender's idea of the counter no longer matches the
  receiver's, which is a real fault and not a lost frame.
- The window has to be narrower than half the counter or the meanings
  collide. With a wider window the arithmetic that decides ahead from
  behind has no unambiguous answer, and a duplicate starts reading as a
  gap.
- The counter wraps, so every comparison is modular. A frame numbered
  one that follows a frame numbered two hundred and fifty-five is in
  order; a comparison written with plain arithmetic reads it as a jump
  backwards and refuses a perfectly good stream.
- The number the ground needs back is the one the receiver is waiting
  for. Reporting that frames were refused is not actionable; reporting
  which sequence number would unblock delivery is.

## Workflow

1. Validate the counter modulus and the acceptance window against each
   other before any frame is looked at, so an impossible configuration is
   refused rather than silently mis-deciding frames.
2. For each frame, take the modular offset from the number the receiver
   expects, resolved into a signed distance so ahead and behind are
   distinguishable across the wrap.
3. Group the frame by that distance: exactly expected, ahead but inside
   the window, behind but inside the window, or outside it altogether.
4. Deliver only the expected frame, and advance the expected value as
   part of delivering it. Record a refusal with the sequence number that
   would unblock the stream.
5. After the stream, check the delivered run against the promise:
   contiguous, ascending modulo the counter, and no repeats.
6. Separate findings from limitations. A refused frame with retransmission
   owed is a limitation; a frame outside the window, or a delivered run
   that is not contiguous, is a finding.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.4.2a | 5 |

## Pitfalls

- Delivering an early frame because it decoded correctly. Correct
  decoding says the frame survived the link; it says nothing about where
  it belongs in the order, and delivering it executes commands out of
  sequence.
- Treating a duplicate as an error. The ground repeats frames as part of
  normal retransmission, and a receiver that reports every repeat as a
  fault buries the one case that matters under routine traffic.
- Writing the sequence comparison with plain subtraction. It works for
  the whole mission until the counter wraps, and then refuses every
  frame until someone power-cycles the receiver.
- Sizing the acceptance window at more than half the counter. It looks
  more tolerant and is strictly worse: the ahead and behind regions meet,
  and the service can no longer tell a duplicate from a gap.
- Reporting only that frames were refused. The ground cannot act on a
  count; it acts on the sequence number the receiver is waiting for.
- Counting accepted frames as delivered frames without checking the run.
  The two agree only while nothing went wrong, which is precisely the
  case the service was not needed for.

## Behavior contract (gate 3)

The modulus and window validation, signed modular offset, four-way frame
disposition, stream replay with the advancing expected value, retransmission
requests, ordering and uniqueness checks and the stream verdict are exercised
by the gate 3 contract test:
scripts/test_e50_telecommand_delivery_service.py against
scripts/e50_telecommand_delivery_service_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_telecommand_delivery_service.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
