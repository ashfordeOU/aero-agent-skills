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

1. Walk the reviews in order; record the first open gate, reviews marked
   closed with open actions, and phase work that started early.
2. For categories A to C, check the fixed critical-software obligations
   and that at least one justified measure is applied.
3. Check verification independence for each critical item.
4. Grade every reuse candidate and every code generator in the project.
5. Triage the nonconformances and problem reports and check the board.
6. Write the findings as a draft for the assurance lead.

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
