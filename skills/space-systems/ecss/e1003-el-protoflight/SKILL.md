---
name: e1003-el-protoflight
description: "Use when define the element protoflight test baseline under ECSS-E-ST-10-03C §6.4: decide whether a space element must follow the protoflight test approach (one hardware model demonstrating both design qualification and flight acceptance, with no separate dedicated qualification model), and derive, for each required test type, the protoflight test level from the Table 6-5 qualification severities and the protoflight test duration from the Table 6-6 acceptance durations. Also flag any protoflight baseline entry whose level or duration deviates from the standard qualification-level/acceptance-duration rule without a documented engineering deviation. Trigger: ecss, e-st-10-system-scope, protoflight, element-testing, test-levels, test-durations, Table-6-5, Table-6-6, qualification-baseline, acceptance-baseline."
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
  tags: [ecss, e-st-10-system-scope, protoflight, element-testing, test-levels, test-durations, qualification-baseline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Element Protoflight Test Baseline (space-systems/ecss/e1003-el-protoflight)

Use when the task is defining the element protoflight test baseline
under ECSS-E-ST-10-03C §6.4: deciding which test approach a space
element follows, and deriving the protoflight test level and duration
for each applicable test type ahead of test specification and test
procedure drafting.

## Domain quick reference

- ECSS-E-ST-10-03C §6.4 defines the protoflight test approach at the
  element level: when a single element model must serve as both the
  design qualification article and the flight article (no separate,
  dedicated qualification model is produced), that element follows a
  protoflight test baseline instead of running a full qualification
  campaign on one model and a separate acceptance campaign on another.
- Table 6-5 tabulates, per test type (for example mechanical vibration,
  thermal vacuum, thermal cycling, shock, EMC), the qualification-level
  and acceptance-level test severities: the qualification level carries
  more margin above the predicted flight environment than the
  acceptance level.
- Table 6-6 tabulates, per test type, the associated qualification and
  acceptance test durations or cycle counts: the qualification duration
  is longer than the acceptance duration.
- The protoflight baseline rule combines the two tables: the
  protoflight test level for a test type is set at the qualification
  level, while the protoflight test duration is set at the (shorter)
  acceptance duration. This demonstrates qualification-level design
  margin without exposing the flight element to the full qualification
  duration, which would induce excess wear-out or fatigue on an article
  that still has to fly.
- A protoflight baseline entry that departs from this level/duration
  combination is a deviation and requires a documented engineering
  rationale — it cannot be substituted silently. An element with a
  dedicated qualification model does not use the protoflight baseline
  at all; it keeps separate qualification and acceptance campaigns.

## Workflow

1. For each element, determine its test approach: protoflight when no
   dedicated qualification model exists (the same hardware demonstrates
   qualification and then flies), otherwise qualification-and-acceptance
   (separate models, standard campaigns).
2. For each applicable test type on a protoflight element, capture its
   Table 6-5 qualification level and acceptance level, and its Table
   6-6 qualification duration and acceptance duration. Reject a spec
   where the qualification level is below the acceptance level or the
   qualification duration is below the acceptance duration —
   qualification must carry more margin and more exposure than
   acceptance, not less.
3. Derive the protoflight baseline for the test type: level =
   qualification level, duration = acceptance duration.
4. Build the full baseline matrix across every required test type for
   the element; reject a duplicate test type entry and report any
   required test type still missing from the matrix.
5. When a proposed baseline entry is supplied from elsewhere (for
   example a test specification already in draft), compare it against
   the standard-rule baseline derived from the same spec; flag any
   entry whose level or duration does not match unless the test type
   already has a recorded, approved deviation.
6. Before declaring an element ready for protoflight testing, confirm
   it is categorized as following the protoflight approach and that its
   baseline matrix has no missing required test types.

## Pitfalls

- Applying the protoflight baseline (qualification level, acceptance
  duration) to an element that actually has a dedicated qualification
  model — that element should run separate qualification and acceptance
  campaigns, not a blended baseline.
- Accepting a test spec where the qualification severity or duration is
  weaker than the acceptance one — that inverts the margin relationship
  the baseline rule depends on.
- Silently substituting a different level or duration than the standard
  rule produces instead of flagging it as a deviation needing documented
  justification.
- Declaring an element ready for protoflight testing while a required
  test type is still missing from its baseline matrix.

## Behavior contract (gate 3)

The approach-determination, spec-validation, baseline-derivation,
matrix-completeness, and deviation-flagging logic is exercised by the
gate 3 contract test: scripts/test_e1003_el_protoflight.py against
scripts/e1003_el_protoflight_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_el_protoflight.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
