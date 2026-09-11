---
name: e1003-tpro-drd
description: "Use when validate a Test Procedure (TPRO) document against ECSS-E-ST-10C Annex C DRD requirements: confirm the header carries all required identification fields (document ID, title, revision, objective, test level, applicable standard, safety requirements), verify each procedure step is numbered sequentially with an explicit action, expected result, and data-recording entries specifying parameter, unit, and acceptance range, check that pass/fail criteria cover all measured parameters, and surface any structural gap before the procedure enters formal review. Trigger: ecss, e-st-10-system-scope, e-st-10c, tpro, test-procedure, drd, data-recording, pass-fail-criteria, procedure-validation, annex-c."
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
  tags: [ecss, e-st-10-system-scope, e-st-10c, tpro, test-procedure, drd, data-recording, pass-fail-criteria, annex-c]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS-E-ST-10C — Test Procedure DRD (space-systems/ecss/e1003-tpro-drd)

Use when the task is to generate or validate a Test Procedure (TPRO) document
against the DRD (Document Requirements Definition) specified in ECSS-E-ST-10C
Annex C: ensuring every required field is present in the header, every
procedure step is structured with a numbered action and expected result,
every data-recording entry is complete, and pass/fail criteria are defined
before the procedure is submitted for review.

## Domain quick reference

- Annex C of ECSS-E-ST-10C defines the content requirements for a Test
  Procedure document. A TPRO must carry a header section that uniquely
  identifies the document (ID, title, revision), states the test
  objective, identifies the test level (unit, subsystem, system,
  acceptance, qualification, or protoflight), names the applicable
  standard, and records the relevant safety requirements.
- The procedure body is an ordered sequence of numbered steps. Each step
  must carry: (a) a step number that is sequential from 1; (b) a plain-
  language action instruction; (c) an expected result against which the
  operator judges pass or fail. A step may additionally carry one or more
  data-recording entries; each entry must specify the parameter name, its
  unit, and the acceptance range so that the recorded value is
  unambiguous.
- Pass/fail criteria form a separate section that collects the
  measurable acceptance conditions across the whole procedure. Each
  criterion must name the parameter, state the condition (e.g. "≤",
  "within", "equal to"), and give the acceptance value. A TPRO without
  any pass/fail criteria has no formally checkable outcome and is not
  complete.
- Findings from the DRD validation are graded: CRITICAL for a missing
  required section or header field; MAJOR for a structural defect within
  a step or criterion; MINOR for a sequencing or formatting deviation.

## Workflow

1. Receive the candidate TPRO document as a structured record with three
   top-level keys: `header`, `procedure` (an ordered list of step
   records), and `pass_fail_criteria` (a list of criterion records).
2. Validate the header: for each required field (doc_id, title,
   revision, objective, test_level, applicable_standard,
   safety_requirements) check that the field is present and non-empty;
   raise a CRITICAL finding for each missing or empty field. For
   test_level, additionally check the value is one of the six recognized
   levels; raise a MAJOR finding if the value is outside that set.
3. Validate the procedure: raise a CRITICAL finding if the step list is
   empty. For each step in order, check that step_number matches the
   expected sequential value (MINOR if it does not), that `action` and
   `expected_result` are present and non-empty (MAJOR if missing), and
   for each data-recording entry, that `parameter`, `unit`, and
   `acceptance_range` are all present and non-empty (MAJOR if any is
   missing).
4. Validate pass/fail criteria: raise a CRITICAL finding if the
   criteria list is empty. For each criterion, check that `parameter`,
   `condition`, and `acceptance_value` are present and non-empty; raise
   a MAJOR finding for each missing field.
5. Collect all findings and report them grouped by severity. The TPRO
   is considered DRD-compliant when the CRITICAL and MAJOR lists are
   both empty; MINOR findings are recorded but do not block approval.

## Pitfalls

- Accepting a step without an expected result because the action is
  "self-evident" -- the DRD requires the operator's pass/fail judgement
  to be documented at each step, not assumed from the action.
- Omitting the data-recording entries for steps that produce a numeric
  measurement -- entries with no unit or no acceptance range cannot be
  verified against the requirement, making the procedure unusable for
  formal review.
- Treating the pass/fail criteria section as optional when a procedure
  has only one step -- a single-step TPRO still requires at least one
  criterion that makes the overall outcome deterministic.
- Allowing a non-sequential step number to pass silently -- a MINOR
  sequencing deviation indicates a cut-and-paste error or a deleted step
  that was not renumbered, and it must be resolved before the procedure
  is used operationally.
- Accepting an unrecognized test level in the header -- the six
  recognized levels map to specific facility and personnel requirements;
  an arbitrary string cannot be matched to those requirements and
  represents an incomplete header.

## Behavior contract (gate 3)

The header validation, procedure validation, data-recording check, and
pass/fail criteria check are exercised by the gate 3 contract test:
scripts/test_e1003_tpro_drd.py against
scripts/e1003_tpro_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_tpro_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
