---
name: e7041-perform-an-are-you-alive-connection-test
description: "Perform the are-you-alive connection test of ECSS-E-ST-70-41C clause 6.17.3 and decide what its outcome actually proves. Use when the task is issuing the connection-test request that carries no application data, waiting for one are-you-alive report inside a declared timeout, refusing a request whose data field is not empty, grading an absent, late, duplicated, foreign-source or wrong-type response as its own verdict rather than a single pass or fail, comparing the round-trip against the timeout through a named tolerance, and censusing a campaign for availability. Trigger: ecss, e-st-70-41c, are-you-alive-connection-test, are-you-alive-report, connection-test-timeout, empty-connection-test-data-field, duplicate-connection-test-response, connection-test-availability-census."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-perform-an-are-you-alive-connection-test, are-you-alive-connection-test, are-you-alive-report, connection-test-timeout, empty-connection-test-data-field, connection-test-availability-census]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Are-You-Alive Connection Test (space-systems/ecss/e7041-perform-an-are-you-alive-connection-test)

Use when the task is the are-you-alive connection test of
ECSS-E-ST-70-41C clause 6.17.3 -- the cheapest question the ground can
ask the on-board test service, and the one whose answer is most often
over-read.

## Domain quick reference

- The request carries nothing. It names a destination and has an empty
  application data field, and the report that answers it carries nothing
  either. Anything in either data field means the packet being graded is
  not the connection test it is being taken for, so the emptiness is a
  precondition of the test and not a formatting detail.
- What a successful test proves is bounded and worth stating: the
  request reached the test service of that application process, was
  recognised, and a report came back. It does not prove any other
  service is running, that telemetry is flowing, or that the platform is
  healthy. A green connection test beside a silent housekeeping stream
  is a real and informative combination, not a contradiction.
- Exactly one report answers one request. A second report matching the
  same request is not a stronger pass; it points at a duplicated uplink,
  a retransmission that was never suppressed, or two responders
  answering for the same application process, and each of those is worth
  more than the pass it hides.
- A report arriving after the timeout is not the same outcome as no
  report. The first says the path works and the budget is wrong or the
  responder is loaded; the second says nothing came back at all. A grader
  that folds both into one failure discards the distinction an operator
  needs to decide what to do next.
- The timeout comparison is a float comparison of times. A response that
  lands exactly on the budget is in time, and that equality is absorbed
  by a named tolerance rather than by quietly widening the budget.

## Workflow

1. Validate the request: destination application process identifier in
   range and not the reserved idle value, an empty application data
   field, and a positive finite timeout.
2. Collect the candidate responses observed after the request time and
   discard anything timestamped before it.
3. Grade each candidate: a report of another type is a wrong-type
   finding, a report sourced from another application process is a
   foreign-source finding, and neither counts as the answer.
4. Count the matching reports. None gives a no-response verdict; more
   than one gives a duplicate-response verdict carrying every arrival
   time so the second source can be chased.
5. For the single matching report, compute the round-trip as its arrival
   minus the request time, and compare it with the timeout through the
   named tolerance so an exact-budget arrival is in time.
6. Return the verdict, the round-trip when one exists, and the explicit
   statement of what the pass covers.
7. Over a campaign, census the verdicts: availability as the alive
   fraction, the worst round-trip among the alive tests, and the list of
   application processes that never answered.

## Pitfalls

- Reading a pass as platform health. It covers one test service of one
  application process and the path to it.
- Treating two responses as a better pass. It is a finding about the
  uplink or the responder set, and it disappears the moment the grader
  stops at the first match.
- Collapsing a late report into no report. The two point at different
  causes and different next actions.
- Accepting a request with a populated data field. Whatever is being
  measured then, it is not this test.
- Grading the round-trip with a bare strict comparison. An arrival
  exactly on the budget then fails or passes according to the last bit
  of a subtraction, which is not an engineering decision.

## Behavior contract (gate 3)

The request validation, candidate filtering, wrong-type and
foreign-source grading, duplicate detection, round-trip comparison
through the named tolerance and campaign census are exercised by the
gate 3 contract test:
scripts/test_e7041_perform_an_are_you_alive_connection_test.py against
scripts/e7041_perform_an_are_you_alive_connection_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_perform_an_are_you_alive_connection_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
