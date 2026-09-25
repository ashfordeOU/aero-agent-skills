---
name: q80-milestone-assurance-evidence
description: "Plan and audit the software product assurance evidence owed at each milestone review under ECSS-Q-ST-80C Rev.2: resolve the documents a review owes for the software category and project scope from the clauses that drive them, grade a submitted review pack for missing, immature and unplanned items, list the evidence kept continuously rather than per review, build the software product assurance milestone report skeleton, and find the first incomplete review. Use when a review data pack is assembled or audited. Trigger: q80-milestone-evidence, spamr, software-review-data-pack, srr-pdr-cdr-qr-ar-evidence, spa-milestone-report, q-st-80c-annex-f."
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
  tags: [ecss, q-st-80c, q80-milestone-assurance-evidence, q80-milestone-evidence, spamr, software-review-data-pack, srr-pdr-cdr-qr-ar-evidence, spa-milestone-report, q-st-80c-annex-f]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Software Assurance Evidence per Milestone (space-systems/ecss/q80-milestone-assurance-evidence)

Use when the task is to know which software product assurance evidence of
ECSS-Q-ST-80C Rev.2 (30 April 2025) is due at which review, or to audit a
review data pack against it. Every requirement of the standard names the
output that evidences it and the reviews that expect it; Annex F regroups
those outputs per review, and Annex C defines the software product assurance
milestone report (SPAMR) that summarises them.

## Domain quick reference

- The reviews are the system requirements review (SRR), preliminary design
  review (PDR), critical design review (CDR), qualification review (QR),
  acceptance review (AR) and operational readiness review (ORR), with test
  readiness reviews (TRR) held before each test campaign.
- The plan (SPAP) and the milestone report (SPAMR) are owed at every main
  review. Most other evidence has a window: the verification plan early,
  the verification report from PDR on, the configuration file from CDR on,
  acceptance evidence at QR and AR.
- What a review owes depends on the category and the scope. A clause
  tailored out for the category does not owe its output; reuse, supplier,
  procurement, security and operations evidence is owed only when the
  project has that scope. Independent verification evidence is owed for
  categories A and B only.
- Some evidence belongs to no review: periodic assurance reports, review
  and inspection records, process assessment records, alerts. It is kept
  current and sampled at any audit, not delivered in a pack.
- The milestone report has a fixed outline: verification activities,
  methods and tools, adherence to standards, metrics, testing and
  validation, problem and nonconformance status, references to progress
  reports. A section with no input behind it is a finding, not a
  formatting gap.
- A document present in draft where issue is owed is present and unmet at
  the same time. A document nobody asked for is listed, not failed.

## Workflow

1. Normalise the review, the category and the scope flags.
2. Resolve the documents owed with the clauses driving each.
3. Grade the submitted pack: missing, below the maturity owed, unplanned.
4. List the continuous evidence to sample alongside the pack.
5. Build the milestone report skeleton and mark the missing inputs.
6. Across the sequence, report the first review that is not complete.

## Pitfalls

- Using one document list for every category. Category D owes less, and
  grading it against the category A list manufactures findings.
- Forgetting scope. Reuse and supplier evidence gated off is not a gap;
  gated on and absent is.
- Delivering the milestone report with empty sections and calling it
  complete.
- Treating continuous evidence as a review deliverable, or forgetting it
  exists because no review asks for it.
- Reporting every gap across every review when the question is which
  review blocks first.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- The review data pack and its completeness statement.
- The software product assurance milestone report.
- Any statement that a review may be held or closed on this evidence.

Mark every such output as a draft, list the open questions for the
reviewer, and end with the line: STOP: human sign-off required before
submission.

## Behavior contract (gate 3)

The review, category and scope normalisation, the document map from
driving clauses to reviews, the category filter through the applicability
data including security-driven clauses, the pack grading for missing,
immature and unplanned items, the continuous evidence list, the milestone
report skeleton and the first incomplete review are exercised by the gate 3
contract test: scripts/test_q80_milestone_assurance_evidence.py against
scripts/q80_milestone_assurance_evidence_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q80_milestone_assurance_evidence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
