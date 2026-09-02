---
name: nonconformance-control
description: "Determine and record the disposition of nonconforming aerospace product per AS9100 control of nonconforming output: identify and segregate the part, choose between rework, repair, scrap, use-as-is (derogation), and return to supplier, route repair and use-as-is dispositions through the material review board (MRB), and re-verify reworked characteristics before release. Use when dispositioning nonconforming parts, running an MRB decision, or checking disposition record completeness for identification, segregation, disposition, disposition authority, and customer notification. Trigger: nonconforming product, material review board, mrb, disposition, rework, repair, scrap, use as is, segregation, re-verification."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [nonconformance-control, nonconforming-product, material-review-board, mrb, disposition, rework, repair, scrap, use-as-is, segregation]
  version: 0.1.0
  author: Aero Agent Skills
---

# Nonconformance Control (manufacturing-quality/as9100/nonconformance-control)

Use when the task is dispositioning nonconforming aerospace product under
AS9100 clause 10.2: identification, segregation, disposition through the
material review board, and re-verification after rework.

## Domain quick reference

- AS9100 clause 10.2 requires controlling nonconforming output
  (paraphrase): the part is identified as nonconforming and segregated so
  it cannot be used or delivered.
- Disposition options: rework (return to the original specification),
  repair (restore function without full original conformance), scrap,
  use-as-is (derogation, usually customer approved), and return to
  supplier.
- The material review board (MRB) holds the disposition authority;
  repair and use-as-is need MRB approval, rework and scrap do not.
- Reworked output is re-verified against the original acceptance criteria
  before release; re-verification is mandatory for critical
  characteristics.
- Safety-critical nonconformances are the strictest case: anything that
  cannot be reworked to spec is scrapped; repair and use-as-is are not
  acceptable dispositions for them.
- The disposition record covers identification, segregation, disposition,
  disposition authority, and customer notification; a record missing any
  of the five is incomplete.

## Workflow

1. Identify the nonconforming output and record the nonconformance type
   (dimensional, material, process, or finish).
2. Segregate the part so it cannot be used, shipped, or reworked
   accidentally.
3. Decide the disposition with scripts/nonconformance_logic.py:
   disposition_decision() walks the safety and rework/repair rules.
4. Route repair and use-as-is dispositions through the material review
   board (MRB) for approval (mrb_approval_required()).
5. After rework, re-verify the reworked characteristics
   (rework_requires_reverification()).
6. Close the record only when identification, segregation, disposition,
   disposition authority, and customer notification are all recorded
   (disposition_record_complete()).

## Pitfalls

- Safety-critical parts: never dispose to repair or use-as-is; only
  rework that restores the original specification, or scrap.
  disposition_decision() enforces this rule order.
- Rework re-verification: reworked critical characteristics must be
  re-verified against the original acceptance criteria before release;
  skipping re-verification ships an unverified part.
- MRB authority boundaries: repair and use-as-is require MRB approval;
  rework, scrap, and return to supplier do not. Approving the wrong
  disposition class breaks the authority chain.
- Record completeness: a disposition record missing identification,
  segregation, disposition, disposition authority, or customer
  notification is incomplete regardless of the disposition chosen.
- Repair vs rework definitions: rework restores full conformance to the
  original specification; repair restores function only. Calling repair
  "rework" skips the MRB and re-verification steps.
- Derogation discipline: use-as-is (derogation) is a waiver that normally
  needs customer approval; treating it as a routine disposition bypasses
  the approval chain.

## Behavior contract (gate 3)

The disposition, re-verification, MRB, and record-completeness logic is
exercised by the gate 3 contract test: scripts/test_nonconformance_logic.py
against scripts/nonconformance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_nonconformance_logic.py

## Compliance

- Standards referenced, not reproduced: AS9100 text is proprietary
  (IAQG/SAE); this skill uses name and paraphrase only. The purchase link
  is recorded in standards-map.yaml (as9100 entry).
- compliance: STANDARDS-REF, gated: false; the standard is listed
  reference-only.
