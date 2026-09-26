---
name: q80-software-configuration-nonconformance
description: "Audit software configuration management and the problem and nonconformance chain under ECSS-Q-ST-80C Rev.2 from the assurance side: grade the configuration management plan for regeneration from backup, branching and merging, change control, corruption protection and integrity, check the controlled-document register, check a delivery label, configuration file and release document and recompute the integrity value from the delivered bytes, check the configuration file against each milestone baseline, move software problem reports through legal states, decide when a problem becomes a nonconformance, and check the review board disposition. Use when a delivery or a problem report log is audited. Trigger: q80-configuration-nonconformance, software-configuration-file, software-release-document, delivery-integrity-checksum, software-problem-report-lifecycle, ncr-disposition."
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
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.5.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.5.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.5.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.5.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.6.1
    items: [a, b, c, d]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.6.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.5
    items: [a, b]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.6
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.7
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.8
    items: [a, b, c]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.9
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.10
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.11
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.4.12
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-80c, q80-software-configuration-nonconformance, q80-configuration-nonconformance, software-configuration-file, software-release-document, delivery-integrity-checksum, software-problem-report-lifecycle, ncr-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Software Configuration and Nonconformance Assurance (space-systems/ecss/q80-software-configuration-nonconformance)

Use when the task is to check, as product assurance, that the software
configuration is under control and that problems flow correctly into
nonconformances under ECSS-Q-ST-80C Rev.2 (30 April 2025): clause 6.2.4
for configuration management on top of the project configuration
standard, and clauses 5.2.5 and 5.2.6 for software problem reports and
nonconformances. A one-shot triage of open items across a process audit
belongs to `q80-software-process-assurance`; this skill follows each
delivery and each report through its life.

## Domain quick reference

- The configuration system can rebuild any reference version from its
  backups. A tag that cannot be rebuilt is not a baseline.
- Every delivery carries the software configuration file and the release
  document. The label gives the name, the version, the configuration file
  reference, any protective marking the delivery requires and the
  distribution caveats.
- The configuration file holds an integrity value for the delivery (a
  checksum or digest); the receiver recomputes it. The method to protect
  against corruption and to prove integrity and authenticity is chosen in
  line with the security analysis.
- The configuration file is kept current from the critical design review
  (CDR) on, through qualification, acceptance and the operational
  readiness review (ORR).
- Customisable parts of a code generator are configuration items too, and
  branching and merging follow a written procedure.
- A problem report names the item, the problem, the proposed solution,
  the final disposition, what was changed and which tests were re-run. The
  procedure says when a problem counts as a nonconformance, and the
  assurance plan says from which life cycle point that applies.
- The review board for a software nonconformance includes software
  assurance and software engineering, and software security when a
  security impact is possible. It decides use as is, fix (correction,
  patch or redesign) or return to the supplier for procured software.

## Workflow

1. Confirm the software configuration management plan applies the
   project's configuration management standard, ECSS-M-ST-40, and adds
   the software provisions below on top of it rather than replacing it.
2. Grade the plan with `check_scm_plan`. It must show that every reference
   version can be rebuilt from the backups (ask for the last time it was
   done), that the parts of a code generator a user can customise are
   configuration items with change control written for them, and that
   branching and merging follow a written procedure that says how the
   configuration management tools are used for them.
3. From the same plan and the security analysis, check the protection of
   the supplied software (source, executable, data) against corruption:
   a named method and tool, chosen in line with what the security
   analysis asks, including any integrity-check requirements that
   analysis sets, and the elements and mechanisms by which integrity and
   authenticity of the product are proven (a checksum, a digest, a
   signature).
4. Check the controlled-document register with
   `check_controlled_documents`: the quality-system procedures, the
   planning and progress documents, and every document that describes a
   product (phase inputs and outputs, verification and validation plans
   and results, test specifications, procedures and reports, traceability
   matrices, validation control records, operator and user documentation,
   maintenance and retirement documentation) are all under document
   control.
5. For each delivery, run `check_delivery` with the delivered bytes. The
   delivery carries its configuration file and its release document; the
   configuration file holds the integrity value, which is recomputed from
   the shipped bytes; the label gives the software name, the version, the
   configuration file reference, the media and protective security marking
   the delivery rules call for, and any caveat that limits distribution.
6. At each review from CDR on, run `check_scf_currency`: the
   configuration file exists and matches the baseline presented at that
   milestone, and every change authorised since the previous baseline
   appears in it, implemented through the plan's change procedure.
7. Check the problem reporting procedure: it covers logging, analysis and
   correction of every software problem met during development, and it
   says when a problem becomes a nonconformance.
8. Replay the problem report log through `spr_transition` to find illegal
   moves and reports closed without their content: each report names the
   software item, describes the problem, proposes a solution, records the
   final disposition, lists what was modified (documents, code, tools) and
   lists the tests run again. Sample the log against the procedure to show
   it is really followed, not only written.
9. Confirm the plan names the life cycle point from which nonconformance
   procedures apply, and that nonconformances follow the project's
   nonconformance standard, ECSS-Q-ST-10-09.
10. Apply `qualifies_as_nonconformance` to open reports and check each
    nonconformance with `check_ncr_disposition`: the review board has a
    software product assurance member and a software engineering member,
    plus a software security member whenever a security impact is
    possible, and the disposition is use as is, fix (correction, patch or
    redesign), or return to the supplier for procured software only.
11. Hand the findings to the reviewer as a draft.

## Obligations

| Item | Step |
|---|---|
| ECSS-Q-ST-80C Rev.2 5.2.5.1a | 7 |
| ECSS-Q-ST-80C Rev.2 5.2.5.2a | 8 |
| ECSS-Q-ST-80C Rev.2 5.2.5.3a | 7 |
| ECSS-Q-ST-80C Rev.2 5.2.5.4a | 8 |
| ECSS-Q-ST-80C Rev.2 5.2.6.1a | 9 |
| ECSS-Q-ST-80C Rev.2 5.2.6.1b | 10 |
| ECSS-Q-ST-80C Rev.2 5.2.6.1c | 10 |
| ECSS-Q-ST-80C Rev.2 5.2.6.1d | 10 |
| ECSS-Q-ST-80C Rev.2 5.2.6.2a | 9 |
| ECSS-Q-ST-80C Rev.2 6.2.4.1a | 1 |
| ECSS-Q-ST-80C Rev.2 6.2.4.2a | 2 |
| ECSS-Q-ST-80C Rev.2 6.2.4.3a | 5 |
| ECSS-Q-ST-80C Rev.2 6.2.4.4a | 6 |
| ECSS-Q-ST-80C Rev.2 6.2.4.5a | 2 |
| ECSS-Q-ST-80C Rev.2 6.2.4.5b | 2 |
| ECSS-Q-ST-80C Rev.2 6.2.4.6a | 6 |
| ECSS-Q-ST-80C Rev.2 6.2.4.7a | 4 |
| ECSS-Q-ST-80C Rev.2 6.2.4.8a | 3 |
| ECSS-Q-ST-80C Rev.2 6.2.4.8b | 3 |
| ECSS-Q-ST-80C Rev.2 6.2.4.8c | 3 |
| ECSS-Q-ST-80C Rev.2 6.2.4.9a | 3 |
| ECSS-Q-ST-80C Rev.2 6.2.4.10a | 5 |
| ECSS-Q-ST-80C Rev.2 6.2.4.11a | 5 |
| ECSS-Q-ST-80C Rev.2 6.2.4.12a | 2 |

## Pitfalls

- A configuration file whose baseline is one build behind the software
  on the bench at the review.
- An integrity value copied from the build log rather than recomputed
  from the bytes that were shipped.
- Closing a report after a fix with no record of the tests re-run.
- Letting problems found after the baseline stay informal because the
  plan never said when nonconformance procedures start.
- Returning in-house code "to the supplier", or a board of engineers only
  deciding use as is.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- Acceptance or rejection of a delivery.
- Closure of a problem report or a nonconformance disposition.
- A statement that the configuration is current for a review.

Mark every such output as a draft, list the open questions for the
reviewer, and end with the line: STOP: human sign-off required before
submission.

## Behavior contract (gate 3)

The plan provisions check, the controlled-document register check, the
delivery check with the recomputed integrity value, the configuration file
currency check, the problem report state machine, the problem to
nonconformance interface and the disposition check are exercised by the
gate 3 contract test:
scripts/test_q80_software_configuration_nonconformance.py against
scripts/q80_software_configuration_nonconformance_logic.py (stdlib
unittest, offline).
Run: python3 scripts/test_q80_software_configuration_nonconformance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
