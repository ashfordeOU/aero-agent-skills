---
name: e1011-ops-ergo
description: "Use when assess spacecraft operations design ergonomics under ECSS-E-ST-10C §4.6.7: evaluate each operational procedure for step-count limits, decision-branch density, and time-critical verification coverage; determine the automation level for each function given its response-time requirement and consequence severity; and verify that safety-critical commands carry sufficient independent inhibit actions. Each function is categorized into manual, supervised, or automated allocation and each finding is raised before operations documentation is finalised. Trigger: ecss, e-st-10-system-scope, operations-ergonomics, automation-allocation, error-tolerance, procedures, human-factors."
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
  tags: [ecss, e-st-10-system-scope, operations-ergonomics, automation-allocation, error-tolerance, procedures, human-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Operations Design Ergonomics — §4.6.7 (space-systems/ecss/e1011-ops-ergo)

Use when the task is the operations design ergonomics assessment required
by ECSS-E-ST-10C §4.6.7 -- evaluating operational procedures for
cognitive complexity, allocating functions to the correct automation
level based on response-time and consequence constraints, and verifying
that safety-critical commands are protected by an adequate number of
independent inhibit actions before the operations documentation is
finalised.

## Domain quick reference

- §4.6.7 addresses three interlocking design concerns: procedure
  structure, automation allocation, and error tolerance. All three must
  be assessed before an operations design is considered ergonomically
  adequate.
- A procedure is compliant when its total step count does not exceed the
  recommended limit (15 steps), no single step carries more than three
  decision branches, and every time-critical step has an associated
  verification action confirming the step was effective. Procedures
  exceeding 15 steps are split into sub-procedures; steps with more than
  three decision branches are restructured or delegated to a decision
  table. The step-count and branch-density limits reflect the cognitive
  load threshold above which operator error rates increase materially.
- Each operational function is categorized into one of three automation
  levels: manual (operator initiates and monitors without automated
  support), supervised (automation executes under operator oversight with
  the ability to intervene), or automated (the system acts without
  operator input in the execution loop). The minimum acceptable level is
  determined by the function's required response time and the severity of
  the consequence if it is executed incorrectly. Functions with a
  required response time below 2 s cannot be reliably performed by an
  operator and must be automated; functions requiring response within 10 s
  must be at least supervised; functions with catastrophic-severity
  consequences must be at minimum supervised regardless of response time.
- Error tolerance requires that a safety-critical command not be
  executable by a single inadvertent operator action. A minimum of two
  independent inhibit actions must be present; each inhibit is a
  separately intentional step (e.g. mode select, interlock release, arm)
  that cannot be triggered by a single slip. The inhibit count is checked
  per command before the command interface design is frozen.

## Workflow

1. Collect all operational procedures and, for each, list the steps with
   their decision-branch count, time-criticality flag, and verification
   action status. Reject procedures where step or branch data is missing
   before assessing them.
2. Evaluate each procedure: flag a step count above 15, flag any step
   with more than three decision branches, and flag every time-critical
   step that lacks a verification action. Record each finding against the
   procedure and step identifier.
3. Collect every operational function and its automation allocation
   proposal. For each function, record the required response time and the
   worst-case consequence category (low, medium, high, catastrophic).
   Derive the minimum acceptable automation level from the response-time
   and consequence rules. Flag any proposed level that is below the
   minimum and record the gap.
4. Collect every safety-critical command and its inhibit count (number of
   independent inhibit actions). Flag any command whose inhibit count is
   below two. Raise an error if a negative inhibit count is recorded --
   that is a data entry error, not a design choice.
5. Aggregate the procedure, automation, and error-tolerance findings into
   the review. The operations design is ergonomically adequate only when
   all three finding lists are empty.

## Pitfalls

- Splitting a long procedure only in documentation without verifying the
  sub-procedures individually: each sub-procedure must independently
  satisfy the 15-step limit and the branch-density constraint.
- Treating supervised automation as equivalent to manual with a confirm
  button: supervised level requires that the automation execute the
  action and the operator have genuine authority to halt or override, not
  merely that a dialog box appear.
- Setting the consequence category to the nominal outcome rather than the
  worst-case failure outcome: the allocation rule applies to the worst
  plausible outcome of incorrect execution, not the intended outcome of
  correct execution.
- Counting all inhibits as independent when some share the same physical
  path or mode: two inhibits on the same relay or within the same command
  string count as one for the purpose of the error-tolerance check.
- Reading a missing verification action as implicitly present: if no
  explicit verification step is listed for a time-critical procedure
  step, it is flagged as absent.

## Behavior contract (gate 3)

The procedure assessment, automation allocation, and error-tolerance
inhibit logic is exercised by the gate 3 contract test:
scripts/test_e1011_ops_ergo.py against
scripts/e1011_ops_ergo_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_ops_ergo.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
