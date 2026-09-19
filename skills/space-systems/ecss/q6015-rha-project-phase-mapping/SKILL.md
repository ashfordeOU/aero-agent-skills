---
name: q6015-rha-project-phase-mapping
description: "Map radiation hardness assurance activities and deliverables onto the project lifecycle phases and say which ones sit in the wrong place. Use when the ECSS-Q-ST-60-15C clause 4.4 phase mapping has to be graded: normalise each declared phase against the canonical sequence, place every assurance activity inside its earliest-to-latest phase window, flag work scheduled before the inputs exist or after the review that consumes it, enforce the precedence pairs that make one activity depend on another's output, and name the phase deliverables the plan owes but never declares. Trigger: ecss, q-st-60-15c-clause-4-4, radiation-hardness-assurance-phase-mapping, project-lifecycle-phase-window, rha-activity-precedence, rha-phase-deliverable-completeness, out-of-phase-rha-activity."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-rha-project-phase-mapping, q-st-60-15c-clause-4-4, radiation-hardness-assurance-phase-mapping, project-lifecycle-phase-window, rha-activity-precedence, rha-phase-deliverable-completeness, out-of-phase-rha-activity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Project Phase Mapping (space-systems/ecss/q6015-rha-project-phase-mapping)

Use when the task is the lifecycle view of ECSS-Q-ST-60-15C clause 4.4 —
deciding which radiation hardness assurance activity belongs in which
project phase, what each phase has to hand over, and whether a declared
programme plan actually holds that shape.

## Domain quick reference

- Hardness assurance is not a task, it is a thread running the whole
  lifecycle. Each phase consumes the previous phase's output and produces
  something the next phase cannot start without, so the mapping is a
  dependency graph laid on a timeline rather than a checklist.
- Every activity has a window, not a date. The window opens when its inputs
  first exist and closes at the review that consumes its output. Scheduling
  earlier is not conservatism — the activity would run on inputs that do not
  exist yet and would have to be redone; scheduling later means the review
  that needed the answer has already been passed without it.
- One activity in the chain has a window of a single phase: the baseline
  freeze. It cannot be earlier because characterization and equipment
  shielding are not finished, and it cannot be later because everything
  downstream is procured, tested and accepted against the frozen numbers.
- Precedence is separate from the window. Two activities can both be inside
  their windows and still be in the wrong order relative to each other, which
  is why the producer-consumer pairs are graded as their own check. Sharing a
  phase is allowed; inverting the pair is not.
- Phase deliverables are what makes the mapping auditable. A phase that was
  passed without its written output leaves the next phase depending on
  something nobody can point at, so a plan is graded through the phase it has
  reached and owes everything up to and including that phase.
- The output of the mapping is a finding list, not a score. Each finding names
  the activity, the phase it was put in and the window or pair it broke, so a
  replan can be made against it.

## Workflow

1. Normalise the phase tokens of the plan; an unrecognised phase, or one
   dressed up as free text, is an input error and stops the mapping rather
   than being guessed at.
2. Look up the window of every declared activity and grade each placement
   in-window, too-early or too-late, treating both window edges as inside.
3. Sort the placements by phase then by activity name so the mapping reads as
   a timeline and two runs of the same plan produce the same order.
4. Evaluate the producer-consumer precedence pairs over the placements. Grade
   a pair only when both its activities are declared, and allow the pair to
   share a phase.
5. Accumulate the deliverables owed from the first phase through the phase the
   plan is being graded at, and subtract the declared ones after normalising
   their names.
6. Assemble the findings — out-of-phase activities first, then inverted
   precedence pairs, then absent deliverables — and return compliant only when
   the finding list is empty.

## Pitfalls

- Reading a window as a due date. An activity has an opening phase as well as
  a closing one, and work pulled forward of its opening phase is a finding in
  its own right, not early delivery.
- Grading windows and calling the mapping done. Two activities inside their
  own windows can still be inverted against each other; the precedence pairs
  are a separate pass over the same placements.
- Treating a shared phase as a precedence violation. Producer and consumer
  frequently sit in the same phase and are sequenced inside it; only an
  earlier consumer phase is the defect.
- Owing every deliverable regardless of where the project stands. A plan
  graded at an early phase does not yet owe the later phases' outputs, and
  reporting them as absent buries the findings that matter.
- Letting an unknown activity name pass as an untracked extra. An activity the
  mapping does not recognise has no window, so it cannot be graded, and
  silently dropping it hides scope the plan believes is covered.

## Behavior contract (gate 3)

The phase normalisation, window placement, precedence-pair evaluation,
deliverable accumulation and the plan-level verdict are exercised by the
gate 3 contract test:
scripts/test_q6015_rha_project_phase_mapping.py against
scripts/q6015_rha_project_phase_mapping_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6015_rha_project_phase_mapping.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
