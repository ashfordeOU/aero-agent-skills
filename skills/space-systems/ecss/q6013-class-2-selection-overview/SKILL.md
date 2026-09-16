---
name: q6013-class-2-selection-overview
description: "Use when a candidate parts list must become an owed-duty picture. Scope the selection duties a commercial EEE component choice owes at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.2.1: refuse a condition never declared instead of reading unknown as false, drop a conditional duty only where its condition fails, instantiate a per-programme duty exactly once so no part re-owes it, give each instance a disposition against its named owner role, and refuse a waiver on a duty that cannot be waived. Returns the duty-coverage share against the declared minimum, the outstanding set and a readiness verdict. Trigger: ecss, q-st-60-13c-clause-5-2-1, class-two-commercial-component-selection-duties, selection-duty-conditional-scoping, per-programme-selection-duty-single-instance, selection-duty-owner-role-mismatch, selection-duty-waiver-authority, class-two-selection-duty-coverage-share."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-selection-overview, class-two-commercial-component-selection-duties, selection-duty-conditional-scoping, per-programme-selection-duty-single-instance, selection-duty-owner-role-mismatch, selection-duty-waiver-authority, class-two-selection-duty-coverage-share]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Selection Duty Framing (space-systems/ecss/q6013-class-2-selection-overview)

Use when the task is clause 5.2.1 of ECSS-Q-ST-60-13C at the intermediate
assurance class: fixing what a commercial component selection owes, who
owes it, and which of those duties are owed at all on this programme --
before any single rule is applied to any single part. The framing decides
which later checks are even in scope, so getting it wrong costs either a
duty nobody noticed or a hundred duties nobody needed.

## Domain quick reference

- Part of the duty set is conditional here, and that is the difference
  from the highest class, where the whole set is owed unconditionally. A
  radiation suitability assessment is owed where a radiation environment
  was declared; a lifetime assessment where the mission runs beyond a
  short duration; an evaluation plan where the part brings no
  qualification heritage; an obsolescence continuity plan where the
  production runs to more than one batch.
- A condition that was never declared is unknown, not false. Scoping a
  duty out because nobody filled the field is how a programme discovers
  at the delta review that the radiation case was never owed to anyone.
  The framing refuses the undeclared condition instead.
- The duties divide by scope, not by importance. The usage
  justification, the procurement route record, the derating declaration
  and the conditional assessments are owed once per candidate part; the
  customer agreement and the obsolescence continuity plan are owed once
  per programme. A tool that re-owes a programme duty on every part
  reports one outstanding decision as a hundred open duties, and the
  project reading that list cannot find the one that mattered.
- Each duty has a named owner role. Evidence filed by another role is
  not a cheaper cover; it is a record the accountable role never made,
  and it is reported as mis-owned rather than counted.
- Not every duty can be waived. A waiver on a waivable duty settles it,
  provided an authority is named. A waiver on one that cannot be waived
  is a finding, not a settlement, and the intermediate class is exactly
  where that shortcut gets attempted.
- Coverage is a share, not a verdict. A programme can clear the declared
  minimum and still be blocked by one non-waivable duty sitting open, so
  the share and the blocking set are reported separately.

## Workflow

1. Validate the declared programme context: every programme-sourced
   condition must be present and boolean, and an unrecognised condition
   is refused rather than ignored.
2. Validate each candidate part and its part-sourced conditions, refusing
   a duplicate reference and a part that claims to be the programme.
3. Instantiate the in-scope duties: one instance per part for a per-part
   duty whose condition holds, exactly one instance for a per-programme
   duty whose condition holds.
4. Validate each evidence record, refusing a per-programme duty recorded
   against a part and a per-part duty recorded once for the programme.
5. Give each instance a disposition -- covered, waived, mis-owned,
   waiver-invalid, open, rejected or absent -- refusing a duty that
   carries two evidence records.
6. Report evidence matching no in-scope instance separately; it is work
   the programme did outside the owed set, not coverage.
7. Form the coverage share over the settled instances and compare it with
   the declared minimum, treating an exactly-met minimum as met through
   a named tolerance.
8. Return ranked findings and one verdict: selection-ready,
   selection-ready with actions, or not selection-ready.

## Pitfalls

- Reading an absent condition as a false one. The duty disappears, the
  coverage share goes up, and the programme is told it is ready on the
  strength of a field nobody filled in.
- Re-owing the customer agreement and the obsolescence plan on every
  part. One programme-level decision becomes a page of open duties, and
  the genuinely outstanding part-level duty is lost in it.
- Counting evidence filed by the wrong role as coverage. The record
  exists, but the accountable role never made it, and at the review it
  is the role that is asked.
- Accepting a waiver wherever one is filed. Waivability is a property of
  the duty; a waiver on a non-waivable duty is the finding, and an
  unnamed waiver authority is another.
- Treating the coverage share as the verdict. A single non-waivable duty
  left open blocks the selection at any share, which is why the blocking
  set is reported next to the number and not folded into it.
- Crediting evidence produced for a duty that was scoped out. It is real
  work and it is worth recording, but counting it inflates the share
  against a set it was never part of.

## Behavior contract (gate 3)

The context validation, conditional duty scoping, per-part and
per-programme instantiation, evidence validation, disposition rules,
waiver handling, unmatched evidence report, coverage share and readiness
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_selection_overview.py against
scripts/q6013_class_2_selection_overview_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_selection_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
