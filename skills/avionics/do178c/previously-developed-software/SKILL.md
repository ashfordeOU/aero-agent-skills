---
name: previously-developed-software
description: "Use when you must scope the reuse credit of previously developed software in a DO-178C project: classify a reused item from its origin standard, its modification state and whether its assurance level meets the target level into unchanged direct credit, modified PDS with delta qualification over the changed scope plus affected interfaces, or level upgrade needing additional verification at the higher level, compute the delta objective coverage ratio and verdict against the required objective set, and bound the regression of modified items from the changed code fraction and touched interfaces. Produces the reuse classification, the credit path, the delta objective gap and verdict, and the bounded regression scope that frame the reuse argument. Trigger: previously developed software, PDS reuse, reuse credit, delta objective coverage, modified software scope, regression scope, direct credit, level upgrade."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
gated: false
domain: avionics
pack: do178c
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do178c
  tags: [previously-developed-software, pds-qualification, software-reuse-credit, delta-objective-analysis, modified-software-scope, reuse-classification]
  version: 0.1.0
  author: AeroSkills
---

# Previously Developed Software Reuse Scoping (avionics/do178c/previously-developed-software)

Use when the task is scoping the reuse credit of previously developed
software (PDS) in a DO-178C project: rating a reused item from its
origin standard, its modification state and whether its assurance level
meets the target level, then turning those declared facts into the delta
objective assessment and the regression scope that justify taking
credit. This leaf implements the reuse classification model, the delta
objective coverage verdict and the modified software scope rules in pure
Python, stdlib only, deterministic and offline. It pairs with
avionics/do178c/verification and avionics/do178c/software-testing for
the delta verification this leaf scopes, and with
avionics/do178c/configuration-management and avionics/do178c/planning
for the adjacent project-data and project-strategy siblings.

## Domain quick reference

- Reuse classes (user-declared facts in, classes out): when the item's
  assurance level does not meet the target level, the class is
  level-upgrade, meaning additional verification at the higher level is
  required and the level gap is treated as the delta scope. When the
  level is met and the item is unmodified, the class is
  unchanged-direct-credit: existing data is accepted and no delta
  objectives apply. When the level is met and the item is modified, the
  class is modified-pds: delta qualification applies over the changed
  scope plus the affected interfaces.
- Coverage: coverage_ratio = covered / required, rounded to 4 decimals;
  delta_objectives = required - covered. The verdict flips at equality:
  any covered below required gives delta-qualification-required, and
  covered equal to required gives full-coverage. No objective count
  table is reproduced: both counts are caller inputs.
- Modified scope: changed_fraction = changed_loc / total_loc (rounded to
  4 decimals) and interface_fraction = touched_interfaces /
  total_interfaces. The scope is bounded-regression when changed_fraction
  is at or under 0.2 and interface_fraction is at or under 0.5, and
  broad-regression otherwise.
- DO-178C frames the reuse credit question for previously developed
  software; the relations above are the standard engineering method,
  summary-only.

## Workflow

1. Collect the declared facts for the reused item: origin standard id
   (for example do-178c), modified flag, level-meets flag, changed and
   total lines of code, touched and total interfaces, and the required
   and covered objective counts for the delta case.
2. Rate the item with classify_pds(origin_standard, modified,
   level_meets) and read reuse_class and credit_path.
3. When the class is modified-pds or level-upgrade, assess the gap with
   delta_objective_coverage(required_objectives, covered_objectives)
   and read coverage_ratio, delta_objectives and verdict.
4. When the item is modified, scope the regression with
   modified_scope(changed_loc, total_loc, touched_interfaces,
   total_interfaces) and read changed_fraction, interface_fraction and
   scope.
5. For a single record of the item, call pds_report with all nine
   inputs; it merges the classification, coverage and scope sections.
6. Hand the delta verdict and the scope to the verification and
   software-testing effort that performs the scoped delta verification.
7. Confirm the deterministic checks with the contract test.

## Worked example

Reference item: a previously certified autopilot module (DO-178C, DAL C
data) reused in a DAL C project, 8000 LOC and 12 interfaces. Three
cases:

- Unmodified reuse at the same level:
  classify_pds('do-178c', False, True) returns reuse_class
  unchanged-direct-credit and the credit path "accepted as-is at the
  target assurance level from existing data; no delta objectives
  required".
- Modified reuse at the same level (500 of 8000 LOC changed, 2 of 12
  interfaces touched): classify_pds('do-178c', True, True) returns
  reuse_class modified-pds with the credit path "delta qualification
  over the changed scope plus affected interfaces".
  delta_objective_coverage(24, 19) returns coverage_ratio 0.7917,
  delta_objectives 5 and verdict delta-qualification-required.
  modified_scope(500, 8000, 2, 12) returns changed_fraction 0.0625,
  interface_fraction 0.1667 and scope bounded-regression.
- Level-upgraded reuse (DAL C data reused at DAL B):
  classify_pds('do-178c', False, False) returns reuse_class
  level-upgrade with the credit path "additional verification at the
  higher assurance level required, treating the level gap as the delta
  scope".
- Combined record for the modified case: pds_report('do-178c', True,
  True, 24, 19, 500, 8000, 2, 12) returns one dict holding reuse_class
  modified-pds, the modified credit path, required 24, covered 19,
  coverage_ratio 0.7917, delta_objectives 5, verdict
  delta-qualification-required, changed_fraction 0.0625,
  interface_fraction 0.1667 and scope bounded-regression.

## Verification

- Confirm classify_pds('do-178c', False, True) gives unchanged direct
  credit, ('do-178c', True, True) gives modified-pds and ('do-178c',
  False, False) gives level-upgrade.
- Confirm delta_objective_coverage(24, 19) gives ratio 0.7917 with a
  delta of 5 and the delta-qualification-required verdict, and that the
  verdict flips to full-coverage when covered reaches required.
- Confirm modified_scope(500, 8000, 2, 12) gives changed_fraction
  0.0625 and bounded-regression, while a 30% change with the same
  interfaces gives broad-regression.
- Confirm every non-string or empty origin standard, required counts at
  or below zero, covered counts outside [0, required], changed lines
  outside [0, total] and touched interfaces outside [0, total] raise
  ValueError.
- Run the contract test offline: python3
  scripts/test_previously_developed_software.py (30 tests,
  deterministic).

## Related leaves

- avionics/do178c/configuration-management: the current-data sibling;
  boundary between managing the accepted item's current data and rating
  its reuse credit.
- avionics/do178c/planning: the project-strategy sibling that records
  the reuse approach decided here.
- avionics/do178c/verification and avionics/do178c/software-testing: the
  delta verification this leaf scopes.

## Pitfalls

- Confusing level-upgrade with modified-pds: a level gap on an
  unmodified item (classify_pds('do-178c', False, False)) is
  level-upgrade — additional verification at the higher assurance
  level with the gap as the delta scope — not modified-pds, which
  applies only when the level is met and the item is modified.
- Missing the verdict flip at equality: coverage flips to
  full-coverage only when covered equals required; any covered below
  required, however close (19 of 24 is 0.7917), is
  delta-qualification-required with delta_objectives 5.
- Inventing the objective counts: no objective count table is
  reproduced in this leaf — required and covered are caller inputs
  from the project planning data, so pull them from the plan, never
  from a guess at the DO-178C tables.
- Reading bounded-regression from one threshold alone: the scope is
  bounded-regression only when changed_fraction is at or under 0.2 AND
  interface_fraction is at or under 0.5; a 30 percent change with
  untouched interfaces is still broad-regression.
- Taking direct credit on a modified item or across a level gap:
  unchanged-direct-credit applies only to unmodified reuse at a met
  level; modified reuse always carries delta qualification over the
  changed scope plus the affected interfaces.
- Scoping the delta to changed lines only: the modified case rates the
  changed LOC fraction and the touched interface fraction together,
  and pds_report merges classification, coverage, and scope into one
  record for the verification effort — hand over the report, not just
  the changed-lines count.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_previously_developed_software.py

The test covers the three reuse classes and their credit paths (including
the level-upgrade-not-modified-pds distinction), the delta objective
coverage ratio and verdict flip at full coverage, ratio preservation
under input doubling, the modified scope fractions and both regression
threshold boundaries, the combined pds_report record, run-to-run
determinism, and ValueError rejection of empty or non-string origin
standards, non-positive required counts, out-of-range covered counts,
negative or oversized changed lines and out-of-range touched interfaces.

## Compliance

- Standards referenced, not reproduced: DO-178C (RTCA/SAE) frames the
  reuse credit question; the classification and scoping rules above are
  standard engineering method, summary-only per standards-map.yaml, and
  no objective count tables are reproduced.
- compliance: STANDARDS-REF, gated: false.
