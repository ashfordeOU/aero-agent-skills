---
name: e2040-device-development-plan-task
description: "Review the development strategy ECSS-E-ST-20-40C clause 5.2.3 asks the supplier to set out for a device, and check the four strands hold together: the model sequence runs in the canonical order and reaches a model that can carry qualification, the phase windows meet end to start with no gap or overlap, every milestone falls inside the phase that owns it, each critical technology below the readiness floor carries a maturation activity that finishes before the design needs it, and each bought item names a source. Use when a device development plan is being written or reviewed before the definition phase closes. Trigger: ecss, e-st-20-40-device-scope, device-development-plan-task, development-model-philosophy, phase-window-continuity, milestone-inside-phase, critical-technology-maturation, make-or-buy-sourcing."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-device-development-plan-task, device-development-plan-task, development-model-philosophy, phase-window-continuity, milestone-inside-phase, critical-technology-maturation, make-or-buy-sourcing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Development Plan Task (space-systems/ecss/e2040-device-development-plan-task)

Use when the task is the strategy duty of ECSS-E-ST-20-40C clause 5.2.3
-- writing down how the supplier intends to develop the device, and
checking that the model philosophy, the phase windows, the technology
maturation and the make-or-buy split describe one development rather
than four independent wish lists.

## Domain quick reference

- The model philosophy is a sequence, not a set. Models run from
  breadboard through engineering and qualification hardware to flight
  hardware, and each one exists to retire the risk the next one cannot
  afford. A sequence that jumps backwards has a model learning
  something the one before it already assumed.
- The sequence has to reach hardware that can carry qualification. A
  plan that ends at an engineering model and a flight model has no
  qualification-bearing article, so the qualification campaign has
  nothing to run on and the gap surfaces at the review that needs it.
- Phase windows meet end to start. A gap is unplanned time nobody owns
  and an overlap is two phases competing for the same team, so both are
  reported rather than smoothed over.
- Milestones belong to phases. A milestone outside the window of the
  phase that owns it is either mis-assigned or evidence that the
  window moved and the milestone did not, and the plan reads
  consistently in either case until the two are compared.
- A critical technology below the readiness floor needs a maturation
  activity, and the activity has to finish before the design depends
  on it. Maturation that lands after the need date is a schedule
  written as if the risk were already retired.
- Make-or-buy is only a decision once the bought items name a source.
  An unsourced procurement is a lead time nobody has quoted, and it
  usually appears on the critical path later.
- Durations and dates land exactly on each other. Continuity and
  need-date comparisons absorb that representation error rather than
  reporting a gap of a fraction of a day.

## Workflow

1. Fold the model names onto the canonical development models, refuse
   an unknown one, and report a sequence that does not run in canonical
   order or that reaches no qualification-bearing model.
2. Resolve the phases: unique names and a window whose end is later
   than its start. Refuse a zero-length or reversed window.
3. Walk the phase windows in declared order and report each gap and
   each overlap, absorbing representation error at the joins.
4. Resolve the milestones, each naming a phase the plan declares, and
   report a milestone falling outside that phase window.
5. Resolve the critical technologies with a readiness level in range
   and a need date. Report one below the floor carrying no maturation
   activity, and one whose maturation completes after its need date.
6. Resolve the make-or-buy list and report a bought item naming no
   source, and a made item sourced from outside.
7. Total the phase durations, compare against the target the plan
   commits to, and return the findings with the schedule figures.

## Pitfalls

- Reading the model philosophy as a list of hardware to be built. It
  is an argument about what each article retires, so the order carries
  the meaning and a re-ordered list is a different plan.
- Planning a flight model with no qualification-bearing article.
  Everyone reads the list and sees hardware; nobody notices that
  nothing in it can be taken to qualification levels and survive being
  delivered.
- Closing a phase gap by moving the milestone rather than the window.
  The milestone then sits outside its phase, which looks like a
  bookkeeping slip and is the record of a schedule change nobody
  agreed.
- Accepting a maturation activity with no completion date. The
  technology is then permanently in work, and the need date passes
  without anything in the plan objecting.
- Comparing phase joins with a strict inequality. A window ending at
  the same instant the next one starts can differ in the last place
  and be reported as an overlap of a fraction of a day.

## Behavior contract (gate 3)

The model sequence check, phase window continuity, milestone placement,
technology maturation against need dates, make-or-buy sourcing and the
duration comparison are exercised by the gate 3 contract test:
scripts/test_e2040_device_development_plan_task.py against
scripts/e2040_device_development_plan_task_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_development_plan_task.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
