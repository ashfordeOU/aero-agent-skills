---
name: e10-se-planning
description: "Use when plan the systems engineering (SE) activities and
  milestones for an ECSS-E-ST-10C project: integrate each technical
  discipline's own plan (product assurance, verification, configuration
  management, software engineering, assembly/integration/verification)
  into the single project schedule, phase the SE activities against the
  canonical technical review sequence, and check that every discipline's
  input is delivered on or before the review milestone it feeds. Also
  determine when a required discipline plan is missing from the schedule
  and verify the review milestones themselves run in sequence. Trigger:
  ecss, e-st-10c, se planning, systems engineering plan, sep, milestone
  phasing, discipline integration, review sequence, 5.6.2."
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
  tags: [ecss, e-st-10-system-scope, se-planning, systems-engineering-plan, milestone-phasing, discipline-integration, 5.6.2]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Systems Engineering — SE Planning (space-systems/ecss/e10-se-planning)

Use when the task is planning the systems engineering activities and
milestones of an ECSS-E-ST-10C project per clause 5.6.2 -- integrating
every technical discipline's plan into the project schedule and
phasing SE reviews so each discipline's input arrives before the
review milestone that consumes it.

## Domain quick reference

- Clause 5.6.2 requires the project's System Engineering Plan (SEP) to
  lay out the SE activities together with the project's technical
  review milestones, and to integrate every technical discipline's own
  plan into that single schedule rather than letting each discipline
  run on an unlinked timeline. This leaf uses a simplified canonical
  review sequence -- SRR, PDR, CDR, QR, AR -- to phase that
  integration; a real project's SEP may carry additional or
  project-specific reviews, but this leaf's sequencing check is scoped
  to those five.
- A discipline plan (product assurance, verification, configuration
  management, software engineering, assembly/integration/verification)
  is "integrated" only when it is explicitly linked to one of the
  project's planned review milestones and its delivery date is on or
  before that milestone's planned date. A plan with no linked milestone,
  or one delivered after the milestone it feeds, has not actually been
  phased into the schedule -- it is a finding, not a scheduling detail.
- The review milestones themselves must run in canonical order: a
  later-in-sequence review (e.g. PDR) must not be planned to occur
  before an earlier one (e.g. SRR). A duplicate entry for the same
  milestone is also a finding -- the schedule is expected to carry
  exactly one planned date per milestone.
- Coverage is independent of sequencing and integration: every
  required discipline (product assurance, verification, configuration
  management, software engineering, AIV) must have a plan on record at
  all, regardless of whether the milestones it targets are otherwise
  well-formed.

## Workflow

1. Collect the project's planned review milestones (milestone id +
   planned date) and validate they run in canonical SRR -> PDR -> CDR
   -> QR -> AR order with no duplicates. Reject an unrecognized
   milestone id before it enters the schedule.
2. Collect each technical discipline's plan (discipline id, the
   milestone it contributes to, and its delivery date). For each plan,
   confirm the target milestone exists in the project's planned
   milestones; if not, flag a missing linkage rather than assuming an
   implicit date.
3. For each linked discipline plan, compare its delivery date against
   the target milestone's planned date; flag any plan delivered after
   the milestone it is meant to feed.
4. Check that every required discipline (product assurance,
   verification, configuration management, software engineering, AIV)
   has a plan on record; flag each one that is missing.
5. Aggregate the sequence, integration, and coverage findings; the SE
   plan is not clause-5.6.2-compliant until all three lists are empty.

## Pitfalls

- Treating a discipline plan's own internal schedule as sufficient
  without linking it to a project review milestone -- clause 5.6.2
  requires integration into the single project schedule, not a
  standalone discipline timeline.
- Accepting a discipline input delivered after the review it feeds
  because the discipline's own deadline was met -- the relevant
  deadline is the milestone date, not the discipline's internal one.
- Checking milestone sequencing only between immediately adjacent
  entries supplied in the schedule and missing a regression across a
  gap (e.g. SRR after QR when PDR/CDR are not yet scheduled) -- the
  check must walk the full canonical order of whatever milestones are
  present.
- Reading an empty discipline-plan list as "nothing to flag" -- a
  required discipline with no plan at all is itself a coverage finding,
  not an absence of findings.

## Behavior contract (gate 3)

The milestone-sequencing, discipline-integration, and
required-discipline-coverage logic is exercised by the gate 3 contract
test: scripts/test_e10_se_planning.py against
scripts/e10_se_planning_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_se_planning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
