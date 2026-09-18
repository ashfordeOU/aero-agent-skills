---
name: e2020-minimum-interval-between-on-commands
description: "Determine the shortest spacing a channel allows between two consecutive external turn on commands, per clause 5.4.1.4.1 of ECSS-E-ST-20-20C. Use when a command sequence, a retry policy or an autonomous reconfiguration has to be graded before it reaches the platform timeline. Take the governing interval as the longest of the declared minimum, the thermal recovery and the inrush settling time, say so when the declared figure is not the one that governs, grade every consecutive pair for its shortfall, and return the repaired schedule and the sustained command rate. Trigger: ecss, e-st-20-20c, lcl-on-command-spacing, minimum-interval-between-on-commands, consecutive-turn-on-command-spacing, limiter-thermal-recovery-interval, on-command-schedule-repair."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-minimum-interval-between-on-commands, minimum-interval-between-on-commands, lcl-on-command-spacing, consecutive-turn-on-command-spacing, limiter-thermal-recovery-interval, on-command-schedule-repair, sustained-on-command-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Minimum Interval Between On Commands (space-systems/ecss/e2020-minimum-interval-between-on-commands)

Use when the task is clause 5.4.1.4.1 of ECSS-E-ST-20-20C: the shortest
spacing permitted between two consecutive externally issued turn on commands
to a limiter channel. This leaf works out what that interval actually is, then
grades a planned command schedule against it and repairs it.

## Domain quick reference

- The interface sheet figure is a claim, not the constraint. A channel carries
  several contributors to the spacing — the declared minimum, the time the die
  needs to recover thermally from the previous inrush, the time the output
  filter needs to settle — and the one that governs is the longest of them.
- When the declared figure is not the governing one, the interface sheet is
  the thing that has to move. A command issued at the declared minimum while a
  longer recovery is still running re-triggers the channel inside recovery,
  and every sequence built against that figure inherits the defect.
- The constraint is on the pair, not on the sequence. Two commands 40 ms apart
  in an otherwise leisurely schedule are the violation; a schedule that
  averages well inside the interval can still contain them, which is why every
  consecutive pair is graded rather than the mean rate.
- A gap exactly on the interval is admissible. The requirement is a minimum,
  so equality passes; a gap short by a representation error is the same gap,
  and a named tolerance is what keeps the two from being graded differently.
- The shortfall is the useful number. Knowing a pair is 40 ms short tells an
  operator how much slack the sequence needs; knowing only that it failed does
  not.
- The repair cascades. Pushing one command out to the earliest admissible
  instant moves everything behind it that was already tight, so the honest
  cost of the constraint is the shift at the end of the schedule, not the
  shift at the offending pair.
- The categories matter. The clause addresses channels switched on by an
  external command; a retriggerable or foldback limiter recovers by itself and
  is reported out of scope rather than failed.

## Workflow

1. Normalise the category and decide whether the clause applies; report an
   out-of-scope channel rather than failing it.
2. Validate the constraints: a positive declared minimum, and where present a
   positive thermal recovery and a positive inrush settling time.
3. Validate the schedule: non-negative, finite, strictly ascending command
   times, with a repeated or out-of-order time refused outright.
4. Take the governing interval as the longest contributor and record which
   contributor set it; a tie resolves to the declared figure.
5. Raise a finding where the declared minimum is not the governing interval,
   naming the contributor that overrides it.
6. Grade every consecutive pair against the governing interval, with an exact
   equality at the bound absorbed by the tolerance, and record the gap and the
   shortfall for each offending pair.
7. Repair the schedule by pushing each command to the earliest admissible
   instant, letting the change cascade, and take the shift at the end.
8. Return the verdict with the governing interval and its source, the
   sustained command rate, the gaps, the violations, the repaired schedule and
   every finding.

## Pitfalls

- Grading against the declared minimum. Where a thermal recovery or a settling
  time is longer, the declared figure admits sequences the channel does not.
- Checking the average command rate. The requirement is on consecutive pairs,
  and a sequence with a comfortable mean rate can still crowd two commands
  together.
- Failing a gap that sits exactly on the interval. A minimum includes its
  bound; only a gap short by more than representation error is a finding.
- Reporting the first violation only. A crowded burst produces several
  offending pairs, and stopping at the first understates how much the sequence
  has to move.
- Repairing one pair in isolation. Moving a command later can push the next
  one inside the interval, so the repair has to run forward through the whole
  schedule.
- Moving a command earlier to close a gap. The repair only ever delays; a
  command brought forward changes the operation the sequence was written for.
- Grading a retriggerable or foldback limiter here. Those are not switched on
  by an external command in the sense this clause means, and the accurate
  result is an out-of-scope report.

## Behavior contract (gate 3)

The category normalisation, constraint and schedule validation, the governing
interval and its source with a tie resolving to the declared figure, the
sustained command rate, per-pair gap and shortfall grading with its
bound-equality tolerance, the cascading schedule repair and its end shift, and
the verdict ladder — compliant, non-compliant, out of scope — are exercised by
the gate 3 contract test:
scripts/test_e2020_minimum_interval_between_on_commands.py against
scripts/e2020_minimum_interval_between_on_commands_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_minimum_interval_between_on_commands.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
