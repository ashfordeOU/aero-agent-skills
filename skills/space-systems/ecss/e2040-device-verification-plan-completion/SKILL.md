---
name: e2040-device-verification-plan-completion
description: "Assess whether the complete device verification plan is actually ready at the start of the design phase, as ECSS-E-ST-20-40C clause 5.4.2 requires: judge each entry on all five fields it needs to be executable, treat a field reading TBD or TBC as empty and name it, keep a requirement carrying no entry inside the completeness denominator, and refuse a plan still at draft however full its entries look. Use when a design phase is about to open on a verification plan, or when plan readiness is challenged. Trigger: ecss, e-st-20-electrical-scope, device-verification-plan-completion, verification-entry-executability, verification-plan-placeholder-field, verification-plan-approval-at-phase-start, verification-facility-availability."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-verification-plan-completion, device-verification-plan-completion, verification-entry-executability, verification-plan-placeholder-field, verification-plan-approval-at-phase-start, verification-facility-availability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Verification Plan Completion (space-systems/ecss/e2040-device-verification-plan-completion)

Use when the task is the readiness duty of ECSS-E-ST-20-40C clause 5.4.2
-- saying whether the full verification plan is in place at the moment
the design phase opens, rather than still being assembled alongside the
design.

## Domain quick reference

- Completeness is a property of every entry, not of the document. An
  entry is executable only with all five fields behind it: method,
  level, facility, success criterion and schedule slot. Four of five
  renders as a row on the page and cannot be run.
- A field filled with a placeholder is not filled. TBD, TBC, "to be
  confirmed" and a bare dash are the commonest way a plan reaches full
  completeness on paper with the work still ahead of it, so they are
  treated as empty and reported by name rather than silently counted.
- A requirement with no entry at all stays in the denominator. Dropping
  it produces a plan reporting complete coverage of the requirements it
  chose to count, and it reads best precisely when it is worst.
- Approval is separate from completeness. A draft plan with perfect
  entries is not the plan this clause asks for, because nothing in it
  is committed and the entries can still move.
- A facility has to exist by the date its entry is scheduled into. A
  slot booked against a facility arriving two months later is a plan
  that cannot be executed as written, and nothing inside the entry
  reveals it.
- An entry for a requirement outside the set the plan covers is an
  orphan obligation that keeps consuming campaign time.
- Completeness is complete entries over requirements owed, so a
  threshold met exactly is met and the comparison absorbs
  representation error.

## Workflow

1. Resolve the requirement set, refusing a repeat, and resolve the
   entries keyed by requirement, refusing two entries for one
   requirement or an unknown key.
2. Fold the approval state and refuse anything short of approved at the
   phase start.
3. For every requirement owed, report one carrying no entry, and keep it
   in the denominator.
4. For every entry, list the fields it leaves empty, counting a
   placeholder as empty, and name each placeholder field separately so
   it cannot be read as an oversight.
5. Resolve each entry's facility against the declared facilities and
   report one that is not declared, or one that is not available by the
   phase start.
6. Report entries for requirements outside the covered set.
7. Compute completeness over the requirements owed, compare it against
   any declared threshold absorbing representation error, and return the
   verdict: not-ready, ready-with-actions or ready.

## Pitfalls

- Counting entries instead of grading them. Every requirement has a row,
  the plan reports complete, and a third of the rows have no success
  criterion behind them.
- Reading TBD as a filled field. It is the single mechanism by which a
  plan reaches a hundred per cent complete while the campaign cannot be
  scheduled from it.
- Dropping requirements with no entry from the denominator. The figure
  then measures the plan's own selection rather than the requirement
  set.
- Accepting a draft plan because its entries look finished. Nothing in
  it is committed, and the entries move after the design starts against
  them.
- Comparing completeness against its threshold with a strict inequality.
  A two-of-two division landing on 1.0 can sit a unit in the last place
  below it and red a plan that is fully complete.

## Behavior contract (gate 3)

The placeholder detection, five-field executability grading, approval
folding, uncovered-requirement handling inside the denominator, facility
resolution and availability against the phase start, orphan-entry
detection and the completeness-threshold comparison are exercised by the
gate 3 contract test:
scripts/test_e2040_device_verification_plan_completion.py against
scripts/e2040_device_verification_plan_completion_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_verification_plan_completion.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
