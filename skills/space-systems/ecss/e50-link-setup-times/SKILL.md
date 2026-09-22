---
name: e50-link-setup-times
description: "Compute the time a space communication link takes to come into service and assess it against the budget it is allowed, under ECSS-E-ST-50C clause 5.6.8: every stage that must complete before user data flows — carrier acquisition, symbol and frame synchronisation, each negotiation handshake and the round trips it costs — is summed, compared with the declared setup budget, and measured against the contact window that has to absorb it. Report the dominant stage, the margin, the share of the pass consumed and the seconds that must be shaved. Use when budgeting or reviewing acquisition time on a spacecraft link. Trigger: ecss, e-st-50-communications, link-setup-time-budget, carrier-acquisition-stage-timing, handshake-round-trip-delay, contact-window-setup-share, link-acquisition-margin."
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
    clause: 5.6.8
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-link-setup-times, link-setup-time-budget, carrier-acquisition-stage-timing, handshake-round-trip-delay, contact-window-setup-share, link-acquisition-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Link Setup Times (space-systems/ecss/e50-link-setup-times)

Use when a space communication link has to be brought into service inside a
stated time, per ECSS-E-ST-50C clause 5.6.8 — how long setup actually takes,
and whether the pass it is spent in can afford it.

## Domain quick reference

- Setup time is a sum over stages, not a single figure quoted by the
  transceiver supplier. Carrier acquisition, symbol synchronisation,
  frame synchronisation and any negotiation all have to complete before
  the first user bit moves, and each one belongs in the list by name.
- A handshake costs propagation, and propagation does not improve with
  a better receiver. Each exchange is a message out and an answer back,
  so on a long link the number of exchanges, not the speed of any stage,
  is what sets the setup time.
- There are two independent limits and a design can meet one and fail
  the other. The declared budget is a supplier obligation; the contact
  window is a mission fact. Setup inside budget that eats a third of a
  short pass is the case a budget-only check reports as fine.
- The dominant stage is what makes a report actionable. A total says
  there is a problem; the largest contributor says where the next
  engineering hour goes.
- Compare against both bounds with a relative tolerance. A setup sized
  to land exactly on its budget must come out compliant, and an exact
  comparison on floating point decides that by rounding.

## Workflow

1. List every stage that must complete before user data flows, each with
   a name and its own duration. A stage left off the list is being
   asserted to cost nothing.
2. Reject a duplicate stage name. Two entries under one name are two
   teams sizing the same stage, and the total silently doubles it.
3. State the handshake separately: how many exchanges the setup protocol
   needs, and the one-way delay of the link they cross.
4. Sum the stage work and the handshake propagation into one setup time,
   and keep the two parts visible in the result.
5. Compare the total with the declared budget using a relative
   tolerance, and report the margin in seconds rather than a verdict
   alone.
6. Compare the total with the contact window as a share, against the
   share the design allows itself. Report the seconds of pass left for
   user data, and take the window from the shortest contact a
   contingency leaves: what remains after setup has to carry a command
   worth sending and the status report that answers it, and a pass that
   only finishes acquiring supports neither.
7. Where the setup misses, report the seconds that must be shaved and
   the stage that dominates, and where propagation is more than half the
   total, say so — that is a protocol change, not a hardware one.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.8a | 6 |

## Pitfalls

- Quoting the transceiver acquisition figure as the link setup time. It
  omits frame synchronisation and every protocol exchange above it.
- Budgeting a handshake in stage durations. The cost of an exchange is
  two propagation delays, and on a deep-space link that dwarfs every
  stage in the list.
- Passing a setup because it fits the budget. On a short pass the same
  setup can consume most of the window, which the budget check never
  looks at.
- Reporting a negative remainder when setup runs past the end of the
  pass. Nothing is left, and a negative number there reads as a credit.
- Deciding compliance with a bare equality or strict inequality at the
  budget. Two arithmetically identical totals can straddle the bound on
  different platforms, so the verdict changes with the build host.

## Behavior contract (gate 3)

Duration, exchange-count and share validation, duplicate stage
rejection, the stage sum, handshake propagation, the two-bound verdict
with a tolerance at each bound, the dominant stage, the usable pass
remainder and the required reduction are exercised by the gate 3
contract test:
scripts/test_e50_link_setup_times.py against
scripts/e50_link_setup_times_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_link_setup_times.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
