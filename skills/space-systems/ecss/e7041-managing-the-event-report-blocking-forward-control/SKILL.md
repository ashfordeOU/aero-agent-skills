---
name: e7041-managing-the-event-report-blocking-forward-control
description: "Determine which on-board event reports are held back from real-time forwarding under ECSS-E-ST-70-41C clause 6.14.3.7, where the configuration lists what is blocked rather than what is passed on. Use when the task is quieting a chattering event definition without losing it from the packet stores: adding and deleting blocked event identifiers per application process, refusing an event the event service marks as not blockable, refusing a block-all wildcard that would cover one, flagging a high-severity event whose real-time visibility is being given up, and censusing the blocked set by severity. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, event-report-blocking-forward-control, blocked-event-definition, not-blockable-event, block-all-events-wildcard, blocked-event-severity-census."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-managing-the-event-report-blocking-forward-control, event-report-blocking-forward-control, blocked-event-definition, not-blockable-event, block-all-events-wildcard, blocked-event-severity-census]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Event Report Blocking Forward Control (space-systems/ecss/e7041-managing-the-event-report-blocking-forward-control)

Use when the task is the event report blocking forward-control
configuration of ECSS-E-ST-70-41C clause 6.14.3.7 -- the one
forward-control configuration whose sense is inverted, listing the
event reports the real-time forwarding control service holds back
rather than the ones it passes on.

## Domain quick reference

- Everything else in the service selects what is forwarded. This
  configuration selects what is not. An event definition named here has
  its event reports kept off the real-time path; an event definition
  absent from it is forwarded. So an empty configuration forwards every
  event report, where an empty selection configuration forwards none,
  and carrying the habit from one to the other silences a spacecraft or
  floods a link.
- Blocking is a link measure, not a detection measure. The on-board
  event service still detects the event and the packet stores still
  capture the report; only the real-time hop is suppressed. That is
  what makes blocking a chattering event definition reasonable -- the
  evidence survives for retrieval, and the reports that matter stop
  being crowded out of the downlink.
- Some event definitions are not blockable. They are the only real-time
  evidence of the anomalies they announce, the event service marks them
  so, and a request to block one is rejected rather than honoured
  quietly. A block-all wildcard over an application process holding one
  of them is refused for the same reason: a wildcard must not achieve
  by breadth what the specific request is denied.
- A high-severity event that is blockable is still a decision worth
  seeing. The request is accepted and the response carries a finding,
  so an operator giving up real-time visibility of a serious event does
  it knowingly and the log shows when it happened.
- The wildcard, the subsumption rule and the refusal to delete inside a
  wildcard work as they do elsewhere in the service, because the
  ambiguity they prevent is the same one: a configuration that reports
  one thing and behaves as another after a delete.

## Workflow

1. Validate the event catalogue: each definition carries a known
   severity and a boolean blockable marking. An unknown severity is an
   input error, not a definition to be defaulted.
2. Validate each request item and reject an application process the
   service does not control before consulting the catalogue.
3. For a specific block, reject an event the catalogue does not define
   under that application process, then reject one marked not
   blockable. For a block-all wildcard, refuse it if any event of that
   application process is marked not blockable.
4. Accept the block, clearing what a wildcard subsumes, and attach a
   high-severity finding when the event's severity says the real-time
   visibility being given up is significant.
5. Apply an unblock: the application process entry takes every block
   under it, an event that was never blocked is rejected, and a partial
   delete inside a wildcard is refused.
6. Answer a forwarding question as the negation of the blocking
   question, so the inverted sense lives in one place.
7. Report the blocked set sorted, with a census by severity, so the
   review sees what has gone quiet and how serious it was.

## Pitfalls

- Reading an empty blocking configuration as "nothing is forwarded". It
  is the opposite, and acting on the misreading adds blocks that were
  never wanted.
- Blocking a chattering event definition by disabling its detection.
  That loses the report from the packet stores too, and the record of
  the anomaly with it; blocking acts on the forwarding hop alone.
- Achieving a denied block through the block-all wildcard. The
  not-blockable marking is about the event, not about the request that
  reaches it.
- Accepting a high-severity block silently. The action is permitted,
  but an operator who is not told cannot know that the quiet downlink
  afterwards was their own doing.
- Using the blocked list as the definitive event inventory. It names
  only what is suppressed; an event definition deleted from the
  catalogue leaves a blocked identifier that matches nothing.

## Behavior contract (gate 3)

The inverted default, catalogue validation, not-blockable refusal,
wildcard refusal over an unblockable event, high-severity finding,
subsumption, partial-delete refusal and severity census are exercised
by the gate 3 contract test:
scripts/test_e7041_managing_the_event_report_blocking_forward_control.py
against
scripts/e7041_managing_the_event_report_blocking_forward_control_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_managing_the_event_report_blocking_forward_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
