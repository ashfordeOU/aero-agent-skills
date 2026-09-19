---
name: e7041-application-process-accessibility
description: "Determine which application processes an on-board connection test may address under ECSS-E-ST-70-41C clause 6.17.4.1, where accessibility is declared per test-service instance and is never implied by an application process merely existing. Use when the task is validating a declared accessibility list for duplicates, reserved and out-of-range identifiers, partitioning requested identifiers into reachable and refused with a reason for each refusal, spotting a declaration naming a process the mission does not define, and censusing how much of the process set the test service can actually reach. Trigger: ecss, e-st-70-41c, connection-test-application-process-accessibility, declared-accessibility-list, inaccessible-application-process, stale-accessibility-declaration, reserved-idle-identifier-refusal, accessibility-coverage-census."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-application-process-accessibility, connection-test-application-process-accessibility, declared-accessibility-list, inaccessible-application-process, stale-accessibility-declaration, accessibility-coverage-census]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Connection Test Application Process Accessibility (space-systems/ecss/e7041-application-process-accessibility)

Use when the task is the application process accessibility of
ECSS-E-ST-70-41C clause 6.17.4.1 -- the declaration that says which
application processes an on-board connection test is allowed to address,
and which therefore bounds what the test can ever tell you.

## Domain quick reference

- Accessibility is declared, not discovered. An application process can
  exist, be generating telemetry and be perfectly healthy, and still sit
  outside the accessibility declaration of a test service; the test
  service will refuse to reach it. Treating the process list of the
  mission as the accessibility list is the single mistake this clause
  exists to prevent.
- The declaration belongs to the test-service instance. Two test
  services on the same platform can declare different accessible sets,
  so an identifier is not accessible in the abstract -- it is accessible
  from a named service, and a refusal is a statement about the pair.
- The identifier space has holes that a declaration cannot use. The
  all-ones value is reserved for idle packets and never names a process;
  anything past the identifier field is not an identifier at all. Both
  belong in the validation of the declaration, not in a runtime surprise
  when the first request is built.
- A declaration can name a process the mission does not define. That
  entry refuses nothing and reaches nothing: it is a stale declaration
  left behind by a deleted or renumbered process, and it is visible only
  by comparing the declaration against the defined process set.
- The useful summary is coverage, not a count. The fraction of defined
  application processes the service can reach, plus the named list it
  cannot, is what tells an operator how much of the platform a clean
  connection-test sweep would actually have covered.

## Workflow

1. Validate the declared accessibility list: every entry an integer
   identifier inside the field, none the reserved idle value, no
   duplicates, and the list non-empty only if the service claims any
   reach at all.
2. Validate the defined application process set the mission declares, so
   the declaration has something to be compared against.
3. Compare the two: an entry accessible and defined is reachable, an
   entry accessible but not defined is a stale declaration finding.
4. Partition a set of requested identifiers into reachable and refused,
   attaching the reason to each refusal: out of range, the reserved idle
   value, or not declared accessible from this service.
5. Census the coverage: how many defined processes are reachable, the
   fraction, and the sorted list of defined processes the service cannot
   address.
6. Report the findings so a refusal can be told apart from an absence:
   a request refused for accessibility is a configuration statement, not
   evidence about the target process.

## Pitfalls

- Reading a refusal as the target being dead. The request never left the
  service; nothing was learned about the process at all.
- Taking the mission process list as the accessibility list. The two are
  independent, and the declaration is usually the smaller.
- Declaring accessibility once for the platform. It is per test service,
  and copying one service's list onto another asserts reach that was
  never configured.
- Leaving a deleted process in the declaration. It is silent: no request
  ever names it, so only the comparison against the defined set finds
  it.
- Summarising with a count of accessible entries. The count rises when a
  stale entry is added; coverage against the defined set does not.

## Behavior contract (gate 3)

The declaration validation, defined-process comparison, stale-entry
detection, request partitioning with per-refusal reasons and the
coverage census are exercised by the gate 3 contract test:
scripts/test_e7041_application_process_accessibility.py against
scripts/e7041_application_process_accessibility_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_application_process_accessibility.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
