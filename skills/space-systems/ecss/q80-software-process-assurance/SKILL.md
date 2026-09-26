---
name: q80-software-process-assurance
description: "Audit software process assurance under ECSS-Q-ST-80C Rev.2 clause 6: walk the life cycle reviews to the first open gate and the work that ran ahead of it, check the handling of critical software against its fixed obligations and the justified project measures, check verification independence by category, grade a reuse candidate and an automatic code generator, and triage nonconformances and software problem reports against the review board. Use when a supplier's development process is audited or a critical software package is prepared for review. Trigger: q80-process-assurance, critical-software-handling, software-reuse-delta, auto-generated-code-assurance, software-nonconformance-triage, lifecycle-gate-check."
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
    clause: 6.1.1
    items: [a, b]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.1.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.1.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.1.4
    items: [a, b]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.1.5
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.1.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.1.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.1.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.1.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.1.5
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.1.6
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.1.7
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.1.8
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.1.9
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.3.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.3.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.3.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.3.5
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.3.6
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.3.7
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.3.8
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.5.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.5.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.5.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.5.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.5.5
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.2
    items: [a, b]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.5
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.6
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.7
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.8
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.9
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.10
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.11
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.12
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.6.13
    items: [a, b, c]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.8.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.8.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.8.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.8.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.8.5
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.8.6
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.8.7
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-80c, q80-software-process-assurance, q80-process-assurance, critical-software-handling, software-reuse-delta, auto-generated-code-assurance, software-nonconformance-triage, lifecycle-gate-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Software Process Assurance (space-systems/ecss/q80-software-process-assurance)

Use when the task is clause 6 of ECSS-Q-ST-80C Rev.2 (30 April 2025): the
assurance of the software development process rather than of the plan or
the product. It covers the life cycle and its reviews, the requirements that
hold across every engineering process (documentation, dependability and
safety, handling of critical software, configuration management, process
metrics, verification, reuse, automatic code generation, security) and the
nonconformance and problem handling of clause 5.2.

## Domain quick reference

- The life cycle is a sequence of gates: the system requirements review
  (SRR), preliminary design review (PDR), critical design review (CDR),
  qualification review (QR) and acceptance review (AR). A review with open
  actions is not closed, whatever the minutes say, and work on the next
  phase before it closes is work at risk.
- Handling of critical software has two halves. The project chooses and
  justifies its own measures from a family of techniques (defensive
  programming, a safe language subset, full code inspection, independent
  testing and so on). Beside those, some obligations are fixed: the chosen
  measures are verified, regression runs after a platform or tool change,
  unreachable code is removed, and tests are re-run on uninstrumented code.
  Category D carries none of it; category C keeps most of it but not the
  uninstrumented re-run of unit and integration tests.
- Independence rises with category. Nobody verifies their own item; for
  categories A and B verification by an independent organisation is the
  default unless the customer records a lighter arrangement.
- Reuse is a delta argument. The reuse file records what the component
  was developed to, and every difference in requirements, platform,
  environment, category or open problems becomes verification work.
- Generated code is code. Either the generator is qualified for the
  category or its output is verified as if written by hand, and the model
  it came from is itself verified and under configuration management.
- A major nonconformance needs a review board decision with a software
  expert on the board; an open major item is a gate blocker.

## Workflow

1. Check the life cycle definition, held in the assurance plan or pointed
   to from it: its phases, what each phase takes in and hands out, how the
   completion of a phase output is judged, the milestones, the
   dependencies, who is responsible for what, and the customer's part at
   each milestone review as the project management standards
   ECSS-M-ST-10 and ECSS-M-ST-10-01 set it. The quality objectives must
   visibly shape the phases, milestones and documents chosen.
2. Confirm the life cycle was reviewed against the contract's security
   assurance, product assurance and software engineering requirements,
   and by every function that has to apply it, for fitness and for the
   resources to run it; and that resources used during development
   (machines, media, accounts, data) are released or disposed of when
   development ends under the project's security rules: the plan says
   how, and records (media sanitised, access withdrawn) show it was done.
3. Walk the reviews in order with `check_lifecycle`; record the first open
   gate, reviews marked closed with open actions, and phase work that
   started early. Before validation against the requirements baseline, a
   test readiness review must have been held as a project review, showing
   the software is in a state to start validation and that the
   resources, assurance plans, test and validation documents, simulators
   and other means are ready.
4. Check the plan set. Between them, software-specific or project plans
   cover development; the specifications, design and customer documents
   to produce; configuration and documentation management; verification,
   testing and validation; maintenance and retirement; and security
   management. The assurance plan lists every plan with how they relate
   and when each is written and updated. Each plan was reviewed against
   the contract, finished before its activity began, and updated at each
   milestone.
5. Check procedures and project standards the same way: together they
   cover every type of software product in the project, each was finished
   before its activity started, reviewed against the plans and the
   contract, and reviewed beforehand by the functions that apply it for
   fitness and for the resources to apply it.
6. For categories A to C, run `critical_software_obligations` and
   `check_critical_software`. The project has chosen measures for its
   critical software, written why each fits, and applied them; the
   application of each measure has been verified.
7. Check the fixed obligations on critical software in the same pass: a
   regression run after any change in what the platform hardware does or
   in a tool that affects how the executable is produced; a recorded
   analysis of whether more verification and validation is needed after
   a change in platform function or performance or in the environment of
   the software or its hardware; unreachable code removed once found, with
   the need to re-verify and re-validate analysed; unit, integration and
   validation tests run again on the uninstrumented build.
8. Check the process metrics: metrics are used to steer development and
   to judge process quality; they are gathered, kept and analysed on a set schedule from the quality model; they include at least
   schedule duration and effort against plan, used inside the
   supplier; and two problem counts, those found in verification and those
   found in integration, validation testing and use, both used inside the
   supplier and both reported to the customer; and the metric reports sit inside the
   assurance reports.
9. Check the verification process: the verification plan says how the
   quality requirements are verified; the planned verification is enough
   to show each phase's products meet their requirements and is carried
   out as planned; each activity's outputs are checked against criteria
   fixed in advance, and nothing unverified feeds the next activity;
   actions from problem reports raised in verification are confirmed done
   and recorded; traceability matrices are checked at each milestone; and
   the assurance reports summarise this work and what it found.
10. Check that deactivated code has been verified to be impossible to
    activate or harmless if activated by accident, and that configurable
    code has been verified so that no unintended configuration can be
    switched on at run time or built in by the generator.
11. Check reviews and inspections: each follows a written plan or
    procedure naming the items, the person in charge, the participants,
    the means (tool, checklist) and the kind of report; each is run
    against defined criteria with the reviewer independent of the author
    to the level defined; each report points to its procedure and names
    the item, author, reviewer, criteria and findings.
12. Check verification independence for each critical item with
    `check_verification_independence`. Where the project's risk justifies
    it, independent verification is done by a third party (or at the
    lighter independence the customer recorded), combines reviews,
    inspections, analyses, simulations and audits, and comes on top of the
    supplier's own verification, never in place of any of it.
13. Grade every reuse candidate with `assess_reuse`.
14. Grade every code generator with `assess_autocode`. Its selection
    weighed how it evolves against the tools that consume its output,
    customisation to project standards, portability of the generated code,
    collection of design and code metrics, verification of components
    holding generated code, configuration control of the tool and its
    customisation parameters, and open standards. Testing of generated
    code has the same objectives as for hand-written code; a generator
    relied on to omit verification or testing is itself verified to at least
    the level of the code it generates; modelling standards are written,
    applied and checked; the coding rules apply to generated code unless
    it is shown never to need manual edits; and the verification and
    validation documents treat generated and hand-written code
    separately.
15. Triage the nonconformances and problem reports with
    `triage_nonconformances` and check the board.
16. Write the findings as a draft for the assurance lead.

## Obligations

| Item | Step |
|---|---|
| ECSS-Q-ST-80C Rev.2 6.1.1a | 1 |
| ECSS-Q-ST-80C Rev.2 6.1.1b | 1 |
| ECSS-Q-ST-80C Rev.2 6.1.2a | 1 |
| ECSS-Q-ST-80C Rev.2 6.1.3a | 2 |
| ECSS-Q-ST-80C Rev.2 6.1.4a | 2 |
| ECSS-Q-ST-80C Rev.2 6.1.4b | 2 |
| ECSS-Q-ST-80C Rev.2 6.1.5a | 3 |
| ECSS-Q-ST-80C Rev.2 6.2.1.1a | 4 |
| ECSS-Q-ST-80C Rev.2 6.2.1.2a | 4 |
| ECSS-Q-ST-80C Rev.2 6.2.1.3a | 4 |
| ECSS-Q-ST-80C Rev.2 6.2.1.4a | 4 |
| ECSS-Q-ST-80C Rev.2 6.2.1.5a | 4 |
| ECSS-Q-ST-80C Rev.2 6.2.1.6a | 5 |
| ECSS-Q-ST-80C Rev.2 6.2.1.7a | 5 |
| ECSS-Q-ST-80C Rev.2 6.2.1.8a | 5 |
| ECSS-Q-ST-80C Rev.2 6.2.1.9a | 5 |
| ECSS-Q-ST-80C Rev.2 6.2.3.2a | 6 |
| ECSS-Q-ST-80C Rev.2 6.2.3.3a | 6 |
| ECSS-Q-ST-80C Rev.2 6.2.3.4a | 7 |
| ECSS-Q-ST-80C Rev.2 6.2.3.5a | 7 |
| ECSS-Q-ST-80C Rev.2 6.2.3.6a | 7 |
| ECSS-Q-ST-80C Rev.2 6.2.3.7a | 7 |
| ECSS-Q-ST-80C Rev.2 6.2.3.8a | 7 |
| ECSS-Q-ST-80C Rev.2 6.2.5.1a | 8 |
| ECSS-Q-ST-80C Rev.2 6.2.5.2a | 8 |
| ECSS-Q-ST-80C Rev.2 6.2.5.3a | 8 |
| ECSS-Q-ST-80C Rev.2 6.2.5.4a | 8 |
| ECSS-Q-ST-80C Rev.2 6.2.5.5a | 8 |
| ECSS-Q-ST-80C Rev.2 6.2.6.1a | 9 |
| ECSS-Q-ST-80C Rev.2 6.2.6.2a | 9 |
| ECSS-Q-ST-80C Rev.2 6.2.6.2b | 9 |
| ECSS-Q-ST-80C Rev.2 6.2.6.3a | 9 |
| ECSS-Q-ST-80C Rev.2 6.2.6.4a | 9 |
| ECSS-Q-ST-80C Rev.2 6.2.6.5a | 10 |
| ECSS-Q-ST-80C Rev.2 6.2.6.6a | 10 |
| ECSS-Q-ST-80C Rev.2 6.2.6.7a | 9 |
| ECSS-Q-ST-80C Rev.2 6.2.6.8a | 11 |
| ECSS-Q-ST-80C Rev.2 6.2.6.9a | 11 |
| ECSS-Q-ST-80C Rev.2 6.2.6.10a | 11 |
| ECSS-Q-ST-80C Rev.2 6.2.6.11a | 11 |
| ECSS-Q-ST-80C Rev.2 6.2.6.12a | 9 |
| ECSS-Q-ST-80C Rev.2 6.2.6.13a | 12 |
| ECSS-Q-ST-80C Rev.2 6.2.6.13b | 12 |
| ECSS-Q-ST-80C Rev.2 6.2.6.13c | 12 |
| ECSS-Q-ST-80C Rev.2 6.2.8.1a | 14 |
| ECSS-Q-ST-80C Rev.2 6.2.8.2a | 14 |
| ECSS-Q-ST-80C Rev.2 6.2.8.3a | 14 |
| ECSS-Q-ST-80C Rev.2 6.2.8.4a | 14 |
| ECSS-Q-ST-80C Rev.2 6.2.8.5a | 14 |
| ECSS-Q-ST-80C Rev.2 6.2.8.6a | 14 |
| ECSS-Q-ST-80C Rev.2 6.2.8.7a | 14 |

## Pitfalls

- Counting a review as closed because it was held.
- Listing measures without justification. A measure that is not argued
  for this software is a catalogue entry, not a measure.
- Forgetting the uninstrumented re-run. Coverage builds are not the flight
  build.
- Reusing heritage software at a stricter category than it was built to
  without closing the evidence gap.
- Dispositioning a major software nonconformance without a software
  expert on the board.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- Any statement that a review gate is closed or that work may proceed.
- The disposition of a nonconformance or problem report.
- A reuse or generated-code acceptance argument sent to the customer.

Mark every such output as a draft, list the open questions for the
reviewer, and end with the line: STOP: human sign-off required before
submission.

## Behavior contract (gate 3)

The review normalisation and gate walk, the fixed critical-software
obligations per category with the justified-measure rule, the verification
independence check, the reuse delta grading, the generated-code grading and
the nonconformance triage with the board check are exercised by the gate 3
contract test: scripts/test_q80_software_process_assurance.py against
scripts/q80_software_process_assurance_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q80_software_process_assurance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
