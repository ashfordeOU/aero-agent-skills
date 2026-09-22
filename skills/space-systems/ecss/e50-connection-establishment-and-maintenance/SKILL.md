---
name: e50-connection-establishment-and-maintenance
description: "Validate the establishment and maintenance of a connection-oriented space link service under ECSS-E-ST-50C clause 5.6.14.1, whose single normative item asks that the service both open a connection and keep it open for as long as the exchange needs it. Replay a connection state trace against the transitions the service allows, derive the establishment timeout floor from the handshake exchanges and the round trip, compute the worst case time to open across the permitted attempts, and check that the keepalive interval survives the tolerated losses inside the inactivity timeout. Use when specifying a connection handshake or reviewing link supervision. Trigger: ecss, e-st-50-communications, connection-oriented-space-link-service, connection-establishment-handshake-timeout, connection-keepalive-interval-budget, connection-state-machine-transitions, connection-maintenance-inactivity-timeout."
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
    clause: 5.6.14.1
    items: [a]
    relation: implements
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-connection-establishment-and-maintenance, connection-oriented-space-link-service, connection-establishment-handshake-timeout, connection-keepalive-interval-budget, connection-state-machine-transitions, connection-maintenance-inactivity-timeout]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Connection Establishment and Maintenance (space-systems/ecss/e50-connection-establishment-and-maintenance)

Use when a connection-oriented space link service has to be specified or
reviewed, per ECSS-E-ST-50C clause 5.6.14.1 — how the connection opens, how
long opening is allowed to take, and what keeps it open once the data starts
flowing.

## Domain quick reference

- Establishment and maintenance are one obligation with two failure modes.
  A service that opens reliably and drops the connection whenever the
  traffic pauses has met half of it, and the half it missed is the one an
  operator notices.
- The state machine is small and worth writing down. Closed, establishing,
  open, maintaining and closing, with the transitions named; anything a
  trace does that the machine does not allow is a defect in the
  implementation or in the specification, and it is worth knowing which.
- The establishment timeout has a floor set by the handshake. Each
  exchange in the handshake costs a round trip, and the far end spends
  time deciding, so a timeout below that floor abandons connections that
  were about to open.
- Retrying establishment multiplies the floor, not the round trip. The
  worst case time to open is the attempts times the timeout, and on a
  deep-space link that can be longer than the contact.
- Maintenance is a race between keepalives and the inactivity timeout. The
  connection survives only if enough keepalives fit inside the timeout to
  absorb the losses the link is expected to inflict, so the interval times
  one more than the tolerated losses has to stay inside it.
- A keepalive interval much shorter than needed is also a finding. Every
  keepalive costs link time and far-end processing, and on a short contact
  that is capacity the mission wanted for data.

## Workflow

1. Fix what the space link owes before any number is chosen: bringing
   the carrier up and setting the link up for data transfer as the
   contact opens, holding the connection while the exchange runs, and
   taking it down in an orderly way once the contact ends. Then state
   the service as the handshake exchange count, the far-end processing
   time, the round trip, the configured establishment timeout and the
   attempts allowed.
2. Compute the establishment timeout floor and compare the configured
   timeout against it with a relative tolerance, so a timeout set exactly
   at the floor is acceptable on every build host.
3. Compute the worst case time to open across the permitted attempts and
   compare it with the contact time available.
4. State maintenance as the keepalive interval, the inactivity timeout and
   the consecutive keepalive losses the link is expected to inflict.
   Opening the connection may also settle the rate the contact will run
   at, and maintenance may return to that rate as the radio conditions
   move through the pass; where the service offers either, specify it
   here with the rest of the function instead of leaving it to the
   implementation.
5. Check that the interval times one more than the tolerated losses stays
   inside the inactivity timeout, and report the interval that would.
6. Replay any recorded state trace against the allowed transitions and
   name the first step the machine does not permit.
7. Report the verdict with the numbers an implementer can set: the
   establishment timeout, the attempts and the keepalive interval.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.14.1a | 1 |

## Pitfalls

- Sizing the establishment timeout at one round trip. A handshake of more
  than one exchange costs a round trip per exchange, and the far end still
  has to decide before it answers.
- Counting retries as free. Each abandoned attempt costs a full timeout
  before the next one starts, and the sum can exceed the contact the
  connection was supposed to open inside.
- Setting the keepalive interval to the inactivity timeout. A single lost
  keepalive then drops the connection, and a space link loses keepalives.
- Treating an unexpected state transition as a logging artefact. It is
  either an implementation that does not follow the specification or a
  specification that did not anticipate the case, and both need an answer.
- Shortening the keepalive interval until the connection never drops. The
  supervision traffic then competes with the data the connection exists to
  carry, which on a short contact is the more expensive failure.

## Behavior contract (gate 3)

Parameter validation, the allowed state transitions and the trace replay,
the establishment timeout floor, the worst case time to open, the keepalive
budget against the inactivity timeout, acceptance exactly at the floor and
the recommended interval are exercised by the gate 3 contract test:
scripts/test_e50_connection_establishment_and_maintenance.py against
scripts/e50_connection_establishment_and_maintenance_logic.py
(stdlib unittest, offline).
Run:
python3 scripts/test_e50_connection_establishment_and_maintenance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
