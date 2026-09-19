---
name: e50-on-board-network-exception-reporting
description: "Validate the exception reporting a declared on-board network catalogue actually delivers, under ECSS-E-ST-50C clause 5.7.2.6, whose two normative items ask that exceptions be detected and reported and that a report carry what an operator needs. Walk each required exception down a four-rung ladder — never detected, detected but never sent, sent without the identification, source or time somebody has to act on, sent too late to act at all — and report the rung with its reasons, the detection ratio and the entries nobody asked for. Use when reviewing on-board network fault reporting. Trigger: ecss, e-st-50-communications, on-board-network-exception-reporting, network-exception-catalogue-coverage, exception-report-field-completeness, exception-report-latency-bound, undetected-network-fault."
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
  tags: [ecss, e-st-50-communications, e50-on-board-network-exception-reporting, on-board-network-exception-reporting, network-exception-catalogue-coverage, exception-report-field-completeness, exception-report-latency-bound, undetected-network-fault]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — On-Board Network Exception Reporting (space-systems/ecss/e50-on-board-network-exception-reporting)

Use when the exceptions an on-board network can raise are being reviewed
against what it actually reports, per ECSS-E-ST-50C clause 5.7.2.6 — detection
and reporting on one side, the content of the report on the other.

## Domain quick reference

- Two normative items, and they fail as a ladder rather than as a pair
  of boxes. The first asks that exceptions be detected and reported.
  The second asks that the report carry enough to act on.
- Four rungs, four owners. Nobody detects it — an instrumentation gap.
  Detected and never sent — a plumbing gap. Sent without the
  identification, the source or the time — a content gap. Sent too
  late to act on — a timing gap. One pass-or-fail line hides which one
  you have and sends the finding to the wrong team.
- An exception missing from the catalogue entirely is the first rung,
  not an omission from the review. Silence in a catalogue is a claim
  that the network cannot raise it, and that claim gets graded.
- A report that claims to exist for an exception nothing detects is an
  input error, not a pass. The two cannot both be true.
- Timeliness only exists against a stated bound. Where there is a
  bound, an entry that declares no latency at all is late — an unstated
  number is not a fast one.
- The required field set has to be an input and printed back. Silently
  shortening it to whatever the design carries is how a content gap
  gets reported as full coverage.
- A catalogue entry nobody asked for is worth reporting and is not a
  failure. It is usually a real exception the required set forgot.

## Workflow

1. State the exceptions the network is required to raise, the fields a
   report has to carry, and the latency bound if there is one.
2. Declare each catalogue entry with whether it is detected, whether it
   is reported, the fields its report carries and its report latency.
3. Refuse an entry that claims a report for an exception it does not
   detect.
4. For every required exception, take the catalogue entry or treat its
   absence as undetected, then walk the ladder: detection, reporting,
   fields, latency.
5. Compare latency against the bound with a relative tolerance. A
   report landing exactly on the bound must be timely on every
   platform rather than on the host that rounded down.
6. Report the worst rung as the verdict with every reason underneath,
   so a thin late report shows both.
7. Report the two clause items separately, with the detection ratio
   over the required set and the entries the required set did not ask
   for.

## Pitfalls

- Reviewing the catalogue instead of the required set. Every entry
  present can be perfect while the exception that actually bit the
  mission was never listed.
- Reading a detection count as a reporting count. A network that
  notices everything and forwards nothing scores full detection.
- Accepting a report with no source. An operator with an exception
  identifier and no origin has a symptom and a fleet to search.
- Treating an unstated report latency as compliant. Against a stated
  bound, an absent number is an unmet bound, not a quiet pass.
- Shortening the required field set to match the design. The gap
  disappears from the report and from the next review with it.
- Stopping the ladder at the first reason. A thin report that is also
  late is two fixes, and reporting one of them buys a second review.

## Behavior contract (gate 3)

Name, field-list and latency validation, refusal of a report claimed
without detection, the four-rung ladder including an exception absent
from the catalogue, the latency comparison with a tolerance at the
bound and an unstated latency counted as late, the separated clause
items, the detection ratio and the unasked-for entries are exercised by
the gate 3 contract test:
scripts/test_e50_on_board_network_exception_reporting.py against
scripts/e50_on_board_network_exception_reporting_logic.py (stdlib
unittest, offline).
Run:
python3 scripts/test_e50_on_board_network_exception_reporting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
