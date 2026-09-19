---
name: e2040-device-validation-execution
description: "Evaluate whether the device validation activities have actually been run and documented well enough to prove the device meets its intended purpose. Use when an ECSS-E-ST-20-40C clause 5.8.2 validation campaign is being closed: measure how much of the plan ran and how much passed, find runs with no evidence reference, find runs gathered on an article other than the delivered configuration, propagate retest transitively from every failure through the dependency graph, and combine execution, outcome and documentation into one completeness index. Refuses a run with no result, a result on an unrun case and a dependency cycle. Trigger: ecss, e-st-20-40c, device-validation-execution, validation-evidence-reference, validation-article-configuration-match, validation-retest-closure, validation-pass-with-deviation, validation-completeness-index."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-validation-execution, validation-evidence-reference, validation-article-configuration-match, validation-retest-closure, validation-pass-with-deviation, validation-completeness-index]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Validation Execution (space-systems/ecss/e2040-device-validation-execution)

Use when the task is the validation execution step of ECSS-E-ST-20-40C
clause 5.8.2 — running the validation activities on an ASIC, FPGA or IP core
and recording the evidence that the device does what it was built to do,
then judging whether that campaign is actually finished.

## Domain quick reference

- Three independent things have to hold before validation is finished:
  the planned cases were run, the runs passed, and each run produced a
  referenced piece of evidence. A campaign at full execution with no
  evidence references has proven nothing that can be shown to a customer.
- A pass with a recorded deviation counts toward the pass fraction but
  is reported separately, because it carries a disposition that someone
  still has to accept. Folding it silently into a clean pass hides the
  item that the acceptance board needs to see.
- Validation is evidence about one article. A case run on an engineering
  model or a pre-fix build is evidence about a device that is not the
  one being delivered, so the configuration each run names is compared
  with the delivered configuration and a difference is a finding, not a
  bookkeeping note.
- A failure does not invalidate only itself. Every case whose setup,
  state or precondition came from the failed case is invalidated too,
  and so is every case depending on those, so the retest set is the
  transitive closure over the dependency graph rather than the failure
  list.
- A dependency cycle in the ledger makes that closure meaningless. It is
  refused outright rather than broken arbitrarily, because whichever
  edge you drop changes the retest answer.

## Workflow

1. Validate each execution record. A case reported run with no result,
   no device configuration, a result attached to a case that never ran,
   a self-dependency or a repeated dependency is an input error.
2. Validate the ledger as a whole: identifiers unique, every dependency
   resolving to a case that is actually in the ledger.
3. Measure the execution fraction over the planned cases, naming the
   cases never run and the cases aborted without a result separately —
   they have different causes and different recoveries.
4. Split the run cases into passes, passes with deviation and failures,
   and compute the pass fraction over what was run rather than over what
   was planned.
5. Collect the run cases with no evidence reference and compute the
   documentation fraction.
6. Compare each run case configuration with the delivered configuration
   and collect the mismatches.
7. Detect a dependency cycle, then compute the retest closure from the
   failures forward through their dependents.
8. Combine execution, outcome and documentation into the weighted
   completeness index, absorb representation error at unity with a named
   tolerance, and declare completion only when the index is at unity and
   no finding stands.

## Pitfalls

- Reporting the pass fraction over the planned cases instead of the run
  cases. That mixes two different shortfalls into one number and makes a
  half-executed campaign look like a half-failing one.
- Accepting a run with no evidence reference because the result says
  pass. The result is a claim; the reference is what makes it evidence,
  and clause 5.8.2 is about both running and documenting.
- Treating a pass with deviation as a clean pass. It carries an open
  disposition and has to stay visible in the report.
- Retesting only the failed case. The dependent cases ran on state the
  failed case produced, so their evidence went stale at the same moment.
- Breaking a dependency cycle to get an answer out. The retest set
  depends on which edge you drop, so a cycle is refused and fixed in the
  ledger instead.
- Letting evidence from an engineering model stand for the delivered
  device. The article identity is the whole basis of the claim.

## Behavior contract (gate 3)

Record and ledger validation, execution coverage, the pass and deviation
split, evidence-reference gaps, delivered-article configuration comparison,
cycle detection, the transitive retest closure and the weighted completeness
index are exercised by the gate 3 contract test:
scripts/test_e2040_device_validation_execution.py against
scripts/e2040_device_validation_execution_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_validation_execution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
