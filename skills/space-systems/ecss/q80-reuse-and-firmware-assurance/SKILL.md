---
name: q80-reuse-and-firmware-assurance
description: "Assess existing software and programmable devices for qualification under ECSS-Q-ST-80C Rev.2: sort an item as supplier heritage, customer-furnished, COTS, MOTS, freeware or open source, grade its quality-level evidence, suitability and security aspects into corrective actions for the software reuse file, choose reverse engineering or service history to recover missing evidence and grade that history, check open-source licences against how the product is distributed, check a component built for future reuse on every target platform, and check a programmed device for its procedure, marking, programmer calibration and image digest. Use when a COTS or open-source library, heritage code or an FPGA or PROM image enters a space project. Trigger: q80-reuse-firmware, existing-software-qualification, cots-open-source-qualification, software-reuse-file, service-history, programmable-device-firmware."
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
    clause: 6.2.7.2
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.7.3
    items: [a, b]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.7.4
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.7.5
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.7.6
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.7.7
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.7.8
    items: [a, b]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.7.9
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.7.10
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.7.11
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.3.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.3.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.3.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.3.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.3.5
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.3.6
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.3.7
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.5.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.5.2
    items: [a, b]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.5.3
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-80c, q80-reuse-and-firmware-assurance, q80-reuse-firmware, existing-software-qualification, cots-open-source-qualification, software-reuse-file, service-history, programmable-device-firmware]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Reuse and Firmware Assurance (space-systems/ecss/q80-reuse-and-firmware-assurance)

Use when the task is to qualify software that was not written under the
current contract, or to control a programmed device, under ECSS-Q-ST-80C
Rev.2 (30 April 2025): clause 6.2.7 for existing software, clause 7.3 for
software built so that later projects can reuse it, and clause 7.5 for
programmable devices (the clause Revision 2 renamed from firmware). The
quick delta grade of a heritage component against a new context is in
`q80-software-process-assurance`; this skill builds the full reuse file
behind it.

## Domain quick reference

- Existing software is anything developed outside the current contract:
  the supplier's heritage, software the customer hands over, commercial
  and modified off-the-shelf products, freeware and open source.
  Development tools are not handled here; the tools clause covers them.
- The reuse file starts with why reuse beats new development, then weighs
  the item against the project's functional, performance, quality and
  security needs: requirements and design documents, traceability, test
  coverage at each level, verification reports, performance, residual
  nonconformances and alerts, user documentation, code quality and known
  vulnerabilities including those that come in through dependencies.
- Suitability also covers warranty, support, installation and training,
  configuration registration, who maintains it, whether the original
  methods and tools still exist, modification rights, licensing and export
  constraints. For security: authorisation to use it, its sensitivity, the
  security assurance asked of it, and any evaluation or certification.
- Every gap becomes a corrective action recorded in the reuse file and
  followed at each milestone. Missing evidence is regenerated by reverse
  engineering where life cycle data or source exists; otherwise from the
  user documentation plus tests to the coverage required, backed by
  service history (relevance, change control, problem reporting, error
  rates, modification impact, vulnerability statistics).
- Software built for future reuse keeps its documentation separate and
  self-contained, specifies maintainability, portability and verification,
  plans configuration management for a longer life, is tested on every
  platform it targets, and ships a certificate of conformance that names
  any platform not tested.
- A programmed device has a written programming and duplication
  procedure, an indelible marking linking the hardware and the software
  reference (plus protective marking where required), and was programmed
  on calibrated equipment.

## Workflow

1. Sort each candidate with `categorize_existing`; send tools to the tools
   assessment.
2. Open its reuse file with the case for reuse: what the project gains by
   taking this item rather than developing it new (cost, schedule, risk,
   maturity), weighed honestly against the gaps found below.
3. Assess the item against the project's functional, performance and
   quality requirements, and against its security requirements: who
   authorised its use, how sensitive it is, which security assurance is
   asked of it, and which evaluations, certifications or accreditations it
   holds.
4. Grade it with `grade_existing_software` for the category and the
   sensitivity of the function it implements, covering each quality
   aspect: requirements and design documentation, traceability both ways
   from system requirements to code, unit, integration and validation test
   documentation with their coverage, verification reports, performance
   and in-service performance, residual nonconformances, waivers and
   alerts, user documentation, code quality against standards and
   metrics, and the known vulnerabilities of the item and of every
   dependency it pulls in.
5. Complete the suitability part: acceptance and warranty terms, support
   documentation, installation, preparation, training and use, how it is
   identified and registered in configuration management, who maintains
   it and on what terms (changes included), whether the original methods
   and tools still exist and remain valid, copyright and modification
   rights, the licence conditions (list every third-party component with
   its SPDX licence and run `check_licences` for the planned
   distribution), and export constraints.
6. Write the result into the reuse file: the findings of steps 3 to 5, the
   level of reuse judged possible, and the assumptions and method behind
   that judgement.
7. Turn every aspect that falls short into a corrective action, record it
   in the reuse file, and follow it until it is applied to the item.
8. Recover missing evidence with `choose_recovery`. Where life cycle data
   or source exists, reverse-engineer the missing documents and run the
   tests needed to reach the coverage required. Where it does not, build
   the verification and validation documents from the user documentation
   and test to that coverage, or argue service history and grade it with
   `grade_service_history`: its relevance to the new environment, change
   control, how well problems were reported, observed error rates and
   maintenance history, the effect of modifications, and the count, types,
   priorities and fix rates of vulnerabilities.
9. Put every reused item under configuration control, and put the reused
   baseline's configuration status, in detail, into the reuse file for
   the customer to accept.
10. At each milestone, update the reuse file with the outcome of the
    corrective actions still open.
11. For components the project builds for later reuse, confirm the
    development applies the reuse provisions of ECSS-E-ST-40 (its clauses
    5.2.4.7 and 5.4.3.6): reusability requirements stated by the customer,
    reuse procedures, methods and tools defined and applied, the reuse
    potential evaluated at PDR and CDR, and mission and configuration data
    kept apart from the code. Confirm also that what the
    specification, the design files (justification and definition) and
    the assurance file say about them sits in its own part of each and can
    be read without the rest.
12. Run `check_intended_reuse` on those components: their specification
    states maintainability, portability and verification requirements;
    configuration management plans for their longer life, for a changed
    development environment in the next project, and for handing the
    configuration and documentation records over to it; they are tested on
    every platform they target, and a certificate of conformance states
    that those tests passed and names any platform not tested.
13. For each FPGA configuration, PROM or flash image, run
    `check_programmable_device` with the programmed bytes: a written
    procedure covers programming and duplication, the device carries a
    permanent marking that identifies both the hardware part and the
    software reference, devices and software configuration items carry
    protective security marking where it is required, and the programming
    equipment was in calibration.
14. Hand the reuse file draft and findings to the reviewer.

## Obligations

| Item | Step |
|---|---|
| ECSS-Q-ST-80C Rev.2 6.2.7.2a | 2 |
| ECSS-Q-ST-80C Rev.2 6.2.7.3a | 3 |
| ECSS-Q-ST-80C Rev.2 6.2.7.3b | 3 |
| ECSS-Q-ST-80C Rev.2 6.2.7.4a | 4 |
| ECSS-Q-ST-80C Rev.2 6.2.7.5a | 6 |
| ECSS-Q-ST-80C Rev.2 6.2.7.6a | 5 |
| ECSS-Q-ST-80C Rev.2 6.2.7.7a | 7 |
| ECSS-Q-ST-80C Rev.2 6.2.7.8a | 8 |
| ECSS-Q-ST-80C Rev.2 6.2.7.8b | 8 |
| ECSS-Q-ST-80C Rev.2 6.2.7.9a | 10 |
| ECSS-Q-ST-80C Rev.2 6.2.7.10a | 9 |
| ECSS-Q-ST-80C Rev.2 6.2.7.11a | 9 |
| ECSS-Q-ST-80C Rev.2 7.3.1a | 11 |
| ECSS-Q-ST-80C Rev.2 7.3.2a | 11 |
| ECSS-Q-ST-80C Rev.2 7.3.3a | 11 |
| ECSS-Q-ST-80C Rev.2 7.3.4a | 12 |
| ECSS-Q-ST-80C Rev.2 7.3.5a | 12 |
| ECSS-Q-ST-80C Rev.2 7.3.6a | 12 |
| ECSS-Q-ST-80C Rev.2 7.3.7a | 12 |
| ECSS-Q-ST-80C Rev.2 7.5.1a | 13 |
| ECSS-Q-ST-80C Rev.2 7.5.2a | 13 |
| ECSS-Q-ST-80C Rev.2 7.5.2b | 13 |
| ECSS-Q-ST-80C Rev.2 7.5.3a | 13 |

## Pitfalls

- Qualifying an open-source library by its popularity rather than its
  evidence, and never listing the vulnerabilities its dependencies bring.
- Treating customer-furnished software as already qualified.
- Arguing service history from a different processor, mission profile or
  configuration.
- Shipping a binary built from copyleft code without planning the source
  release it owes.
- Programming flight parts on a programmer whose calibration lapsed last
  week.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- The level of reuse claimed for an existing item or its acceptance.
- A licence conclusion; licences also go to legal review.
- Release of a programmed device or a certificate of conformance.

Mark every such output as a draft, list the open questions for the
reviewer, and end with the line: STOP: human sign-off required before
submission.

## Behavior contract (gate 3)

The existing-software sorting, the quality, suitability and security
grading into corrective actions, the recovery choice, the service history
grade, the licence rules, the intended-reuse check and the programmable
device check with its image digest are exercised by the gate 3 contract
test: scripts/test_q80_reuse_and_firmware_assurance.py against
scripts/q80_reuse_and_firmware_assurance_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q80_reuse_and_firmware_assurance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
