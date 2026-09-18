---
name: e50-telecommand-acknowledgement
description: "Audit the acknowledgement trail of an uplinked telecommand batch against ECSS-E-ST-50C clause 5.4.8: validate the verification-stage ladder each command subscribed to, set a per-stage deadline from the uplink epoch plus the round-trip light time plus that stage's timeout, match the returned reports to their command and stage while refusing strays and duplicates, and decide whether each command is covered, missing a stage, late, rejected or reported out of order. Use when a pass is reconciled, a verification-report timeout is set, or an unacknowledged command has to be separated from a failed one. Trigger: ecss, e-st-50c-clause-5-4-8, telecommand-acknowledgement-coverage, telecommand-verification-stage-ladder, round-trip-light-time-deadline, telecommand-acceptance-report, telecommand-completion-report."
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
  tags: [ecss, e-st-50-communications-scope, e50-telecommand-acknowledgement, e-st-50c-clause-5-4-8, telecommand-acknowledgement-coverage, telecommand-verification-stage-ladder, round-trip-light-time-deadline, telecommand-acceptance-report, telecommand-completion-report]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications -- Telecommand Acknowledgement (space-systems/ecss/e50-telecommand-acknowledgement)

Use when the task is clause 5.4.8 of ECSS-E-ST-50C: establishing that
the ground learned the fate of every telecommand it sent. The question
is not whether the spacecraft did the right thing, it is whether the
ground can tell -- and an unacknowledged command and a rejected command
are two different problems with two different recoveries.

## Domain quick reference

- Silence is not success. A command with no report back is a command
  whose fate is unknown, and the recovery for that is to re-establish
  the report, not to resend the command: resending on an unknown fate is
  how a single manoeuvre becomes two.
- The stages answer different questions. Acceptance says the on-board
  software took the command; start says execution began; progress says
  it is still running; completion says it finished. A completion report
  with no acceptance report leaves a hole the ground cannot reason
  about, so acceptance is the base of the ladder and the rest sit above
  it.
- A progress report the ground cannot time against a start report says
  nothing useful, which is why progress is only meaningful once start is
  subscribed, while start itself stays optional for a command that
  completes promptly.
- The deadline is not the timeout. It is the uplink epoch plus the
  round-trip light time plus the stage's own timeout. Near Earth the
  light time is noise and the timeout dominates; at Mars distance the
  light time is the whole budget, and a timeout set on near-Earth habit
  declares every report late.
- Ordering is evidence in its own right. A completion timestamp earlier
  than the acceptance timestamp means the trail has been reassembled
  wrongly somewhere -- store-and-forward, a mixed ground-station buffer,
  a clock -- and the batch verdict should not be read as clean until
  that is understood.

## Workflow

1. Validate each command's subscribed stages: canonical names, no
   duplicates, acceptance present as the base, and progress only above a
   subscribed start.
2. Confirm a timeout exists for every subscribed stage; a subscription
   without a timeout has no deadline and cannot be judged late.
3. Compute each stage deadline as epoch plus round-trip light time plus
   the stage timeout.
4. Match the returned reports to their command and stage, ignoring
   reports for other commands, refusing a report for a stage that was
   never subscribed, and refusing a second report for a stage already
   seen.
5. Decide each stage: a failure report is a failure, a report past its
   deadline is late (with an exact landing on the deadline treated as on
   time), a report earlier than its predecessor is out of order, and an
   absent report is missing.
6. Roll the stage verdicts into a command verdict, keeping a failure
   visible above a mere gap, then into batch coverage and a finding list
   that names the command and the offending stages.

## Pitfalls

- Reading a missing report as a pass because nothing bad came back. The
  absence of a rejection is not an acceptance; the command's fate is
  simply unknown.
- Setting the deadline from the timeout alone. Two-way light time is
  part of every deep-space deadline, and omitting it converts a healthy
  link into a batch of late reports.
- Collapsing rejected and unacknowledged into one failure count. One
  means the spacecraft refused a command it received; the other means
  nobody knows. They are reported separately here for that reason.
- Accepting a report for a stage the command never subscribed to. That
  is a mismatch between the uplinked acknowledgement flags and the
  returned trail, and swallowing it hides a dictionary or a configuration
  error.
- Calling a report late when it lands exactly on its deadline. That is a
  representation question, handled by the tolerance inside the
  comparison; the timeout stays as specified.

## Behavior contract (gate 3)

The stage ladder validation, deadline construction, report matching,
per-stage verdicts, ordering check and batch coverage are exercised by
the gate 3 contract test:
scripts/test_e50_telecommand_acknowledgement.py against
scripts/e50_telecommand_acknowledgement_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e50_telecommand_acknowledgement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
