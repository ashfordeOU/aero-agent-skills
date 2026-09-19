---
name: e7041-perform-an-on-board-connection-test
description: "Execute the on-board connection test of ECSS-E-ST-70-41C clause 6.17.4.2, the connection test that names a target application process instead of answering for the service itself. Use when the task is refusing a target the test service was never declared able to reach before anything is sent, waiting for the on-board connection-test report inside a declared timeout, checking the identifier the report carries is the one that was asked for, grading a timeout, an identifier mismatch, a wrong report type or a duplicate answer, and sweeping several targets into one reachability picture. Trigger: ecss, e-st-70-41c, on-board-connection-test, on-board-connection-test-report, target-application-process-identifier-mismatch, on-board-connection-test-timeout, unreached-target-refusal, multi-target-connection-sweep."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-perform-an-on-board-connection-test, on-board-connection-test, on-board-connection-test-report, target-application-process-identifier-mismatch, unreached-target-refusal, multi-target-connection-sweep]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — On-Board Connection Test (space-systems/ecss/e7041-perform-an-on-board-connection-test)

Use when the task is the on-board connection test of ECSS-E-ST-70-41C
clause 6.17.4.2 -- the connection test that asks one application process
about another, and whose report has to be checked for who it is actually
answering about.

## Domain quick reference

- This test names a target. Unlike the service-level liveness question,
  the request carries the identifier of the application process being
  asked about, and the report carries an identifier back. The whole
  value of the test sits in comparing those two, because a report that
  answers about a different process is a routing or addressing defect
  wearing the shape of a pass.
- Accessibility is checked first, and locally. A target the test service
  was never declared able to reach produces a refusal before any packet
  is generated, and that refusal says nothing about the target: it is a
  statement about the declaration. Recording it as an unreachable target
  conflates a configuration gap with a silent process.
- An identifier mismatch outranks the timing. A report that came back
  quickly but names another process is worse than a slow correct one,
  so the grader settles the identity question before it settles the
  budget question.
- One answer per request. Two reports naming the target are not a firmer
  result; they indicate a duplicated request or two responders bound to
  the same identifier, and a grader that stops at the first match never
  sees either.
- A sweep is read by its three groups, not by a pass count: reached,
  refused before transmission, and asked but silent. Only the third
  group is evidence about the on-board processes themselves.

## Workflow

1. Validate the request: a target application process identifier inside
   the field and not the reserved idle value, an empty application data
   field, and a positive finite timeout.
2. Check the target against the accessibility declaration of the test
   service. Not accessible gives a refused verdict immediately, with
   nothing transmitted and no conclusion about the target.
3. Collect the responses observed after the request and discard anything
   of another report type, anything timestamped before the request, and
   anything carrying an unexpected data field, keeping each discard
   reason.
4. Settle identity first: a report whose target identifier differs from
   the requested one is a mismatch verdict, and it names both values so
   the addressing defect can be chased.
5. Count the surviving matches: none is silence, more than one is a
   duplicate-answer verdict carrying every arrival time.
6. For the single match, compute the round-trip and compare it against
   the timeout through the named tolerance, so an arrival landing
   exactly on the budget is in time.
7. Sweep: group the targets into reached, refused and silent, report the
   worst round-trip among the reached, and keep the refused group out of
   the reachability conclusion.

## Pitfalls

- Accepting a report without checking the identifier it carries. A
  misrouted answer then reads as a pass for a process that never
  replied.
- Counting an accessibility refusal as an unreachable target. Nothing
  was sent; the finding belongs to the declaration.
- Grading the budget before the identity. A fast wrong answer is not a
  marginal pass.
- Reading two answers as confirmation. It is a duplicated request or a
  duplicated responder, and both are defects.
- Reporting a sweep as a pass fraction. Three different outcomes are
  being summed, and only one of them is evidence about the on-board
  processes.

## Behavior contract (gate 3)

The request validation, pre-transmission accessibility refusal, response
filtering, identifier-mismatch precedence, duplicate detection,
round-trip comparison through the named tolerance and the three-group
sweep are exercised by the gate 3 contract test:
scripts/test_e7041_perform_an_on_board_connection_test.py against
scripts/e7041_perform_an_on_board_connection_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_perform_an_on_board_connection_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
