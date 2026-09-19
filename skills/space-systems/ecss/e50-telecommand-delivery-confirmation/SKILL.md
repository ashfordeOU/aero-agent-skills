---
name: e50-telecommand-delivery-confirmation
description: "Verify that an on-board network confirms telecommand delivery to the destination within a bounded time, per ECSS-E-ST-50C clause 5.7.2.7, by matching a real dispatch log against a real confirmation log rather than counting acknowledgements. Derive a per-command deadline from dispatch plus the transit and return bounds, keep the earliest confirmation, and separate one that never came from one that came after the sender had already had to act. Report strays, duplicates, a confirmation dated before its own dispatch, and the bound that would have held. Use when reviewing on-board telecommand delivery. Trigger: ecss, e-st-50-communications, on-board-telecommand-delivery-confirmation, telecommand-confirmation-deadline, unconfirmed-telecommand-delivery, stray-delivery-confirmation, duplicate-delivery-confirmation."
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
  tags: [ecss, e-st-50-communications, e50-telecommand-delivery-confirmation, on-board-telecommand-delivery-confirmation, telecommand-confirmation-deadline, unconfirmed-telecommand-delivery, stray-delivery-confirmation, duplicate-delivery-confirmation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — On-Board Telecommand Delivery Confirmation (space-systems/ecss/e50-telecommand-delivery-confirmation)

Use when a telecommand dispatch log is being reviewed against what came back
from the on-board network, per ECSS-E-ST-50C clause 5.7.2.7 — whether the
sender learned the destination had it, and learned it in time.

## Domain quick reference

- Confirmation is a service with a deadline, not a count. Every
  confirmation in the log can be genuine while the command that
  mattered was never confirmed at all.
- The deadline for a command is its own dispatch time plus the transit
  bound across the network plus the bound on the confirmation coming
  back. It is per command, because dispatch times differ.
- A confirmation after the deadline is evidence of delivery and not of
  the service. By then the sender has already had to decide what to do
  without it, so late and confirmed are different verdicts.
- Three things go wrong in the matching itself and each has its own
  cause. A confirmation for a command nobody dispatched is a stray,
  and it usually means two senders share an identifier space. A second
  confirmation for one command is a duplicate. A confirmation dated
  before its own dispatch is impossible and is refused rather than
  averaged into a latency figure.
- A clean service and a clean log are separate claims. Every command
  can be confirmed on time in a log that also carries a stray, and the
  stray is the finding that points at a real defect elsewhere.
- The worst latency actually observed is worth printing. It is the
  bound the design would have needed, stated as a number rather than
  as a request for more margin.

## Workflow

1. State the dispatch log: command identifier, dispatch time and
   destination. Reject a duplicate identifier — two commands under one
   name cannot be told apart in the confirmation log either.
2. State the confirmation log, and the two bounds: transit across the
   network, and the confirmation coming back.
3. Match each confirmation to its command. Keep the earliest and name
   the later ones as duplicates rather than dropping them silently.
4. Refuse a confirmation dated before its own dispatch. It is a clock
   or an identifier fault, and averaging it in hides both.
5. Derive each command's deadline from its own dispatch time plus the
   two bounds.
6. Compare with a relative tolerance. A confirmation landing exactly on
   its deadline must come out confirmed on every platform rather than
   on the host that rounded down.
7. Report the three command verdicts, the strays and duplicates
   separately from them, the confirmation ratio, and the worst latency
   actually observed.

## Pitfalls

- Counting confirmations instead of matching them. The totals agree
  while one command is unconfirmed and one confirmation is a stray.
- Using one deadline for the batch. Commands dispatched minutes apart
  do not share a deadline, and a single cut-off passes the early ones
  and fails the late ones for the wrong reason.
- Folding late into confirmed. The delivery happened; the service did
  not, and the operator acted without it either way.
- Keeping the last confirmation rather than the first. The service is
  judged on when the sender could first have known.
- Discarding strays as noise. A confirmation for a command nobody sent
  is usually an identifier collision between two senders, which is a
  defect that will also mis-route a real one.
- Deciding the deadline with a bare inequality. Two arithmetically
  identical logs can straddle the bound on different machines, so the
  verdict depends on the build host.

## Behavior contract (gate 3)

Identifier, epoch and bound validation, the per-command deadline,
earliest-wins matching with strays and duplicates named, refusal of a
confirmation dated before its dispatch, the three-way command verdict
with a tolerance at the deadline, the separation of a clean service
from a clean log, the confirmation ratio and the worst observed
latency are exercised by the gate 3 contract test:
scripts/test_e50_telecommand_delivery_confirmation.py against
scripts/e50_telecommand_delivery_confirmation_logic.py (stdlib
unittest, offline).
Run:
python3 scripts/test_e50_telecommand_delivery_confirmation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
