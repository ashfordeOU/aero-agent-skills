---
name: e1011-procedures
description: "Use when develop, validate, or review operational procedures for a space system under ECSS-E-ST-10-11C §4.9.1: structure each procedure with mandatory fields (procedure_id, title, purpose, procedure_type, preconditions, numbered steps, expected_outcome), verify the procedure_type is one of the accepted operational categories (nominal, contingency, maintenance, test, launch_countdown, on_orbit), confirm every step begins with an imperative verb and does not exceed the cognitive-load word limit, check that verification checkpoints are spaced within the allowed consecutive-step count, and flag compound actions that should be split into discrete steps. Trigger: ecss, e-st-10-system-scope, procedures, operational-procedures, hfe-review, procedure-validation, procedure-format, human-factors."
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
  tags: [ecss, e-st-10-system-scope, procedures, operational-procedures, hfe-review, procedure-validation, procedure-format, human-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Operational Procedures (space-systems/ecss/e1011-procedures)

Use when the task is developing, validating, or reviewing operational
procedures for a crewed or ground-operated space system under
ECSS-E-ST-10-11C §4.9.1 -- structuring the procedure, validating its
format, and confirming it meets HFE requirements before approval.

## Domain quick reference

- §4.9.1 requires each operational procedure to be typed into one
  accepted category before format checks begin: nominal (planned mission
  operation), contingency (response to an off-nominal event),
  maintenance (servicing or repair), test (acceptance or verification),
  launch_countdown (pre-launch sequencing), or on_orbit (in-flight
  operation). A procedure whose type falls outside this set is rejected
  before any further checks.
- Every procedure must carry seven mandatory fields: a unique
  procedure_id, a descriptive title, a purpose statement (what the
  procedure achieves), the procedure_type, a non-empty preconditions
  list (system states that must hold before the first step), a steps
  list (at least one step), and an expected_outcome describing a
  successful completion. A procedure with any field absent or empty is
  not approved regardless of step quality.
- Each step must be phrased in imperative mood: the action text must
  begin with a recognized action verb (connect, set, verify, enable,
  etc.). A step whose first word is not an imperative verb is flagged as
  a warning. A step that contains two imperative verbs joined by 'and'
  is flagged as a compound-action warning and should be split into two
  discrete steps.
- HFE cognitive-load bounds: no step action may exceed thirty words
  (a hard error if exceeded), and no run of non-checkpoint steps may
  exceed ten consecutive steps (a hard error). Verification checkpoints
  (is_checkpoint: true) reset the consecutive counter. Step IDs must be
  unique within a procedure; a duplicate step ID is a hard error.

## Workflow

1. Receive the procedure draft as a dict with the seven required fields.
   Reject with an explicit error before further processing if any field
   is absent or empty, or if the procedure_type is not in the accepted
   set.
2. For each step in the steps list, validate format: confirm step_id and
   action are present and non-empty; check that the action text begins
   with an imperative verb; measure the word count against the thirty-
   word limit; detect compound actions (two imperative verbs joined by
   'and') and emit a warning.
3. Review the step sequence for HFE compliance: count consecutive steps
   without an is_checkpoint marker and flag an error when the run
   exceeds ten; scan all step IDs for duplicates and flag each
   recurrence as an error.
4. Aggregate findings into three categories: field_findings (field
   completeness), step_findings (per-step format), and hfe_findings
   (checkpoint spacing and step-ID uniqueness).
5. Determine approval: the procedure is approved when no error-severity
   finding exists in any category. Warnings do not block approval but
   should be resolved before release.

## Pitfalls

- Treating a missing preconditions list as equivalent to an empty one
  -- both are errors; a procedure with no stated preconditions implies
  any system state is acceptable, which is unsafe.
- Accepting a step that begins with a passive construction ("The
  operator should connect...") as equivalent to an imperative step
  ("Connect...") -- passive phrasing increases cognitive parsing time
  and fails the imperative-verb check.
- Counting a checkpoint as a regular step for the spacing check --
  is_checkpoint steps reset the consecutive counter; only non-checkpoint
  steps accumulate toward the ten-step limit.
- Assuming a procedure with only warnings is deficient -- warnings
  (compound action, non-imperative verb) highlight improvement
  opportunities but do not block approval; errors (missing fields, word
  limit exceeded, spacing violation, duplicate step ID) are the
  approval gate.
- Reusing a step ID across separate procedures -- step ID uniqueness is
  enforced within a single procedure; the check does not span across
  multiple procedures in a set.

## Behavior contract (gate 3)

The procedure field completeness, step format validation, HFE checkpoint
spacing, and step-ID uniqueness logic is exercised by the gate 3
contract test: scripts/test_e1011_procedures.py against
scripts/e1011_procedures_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_procedures.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
