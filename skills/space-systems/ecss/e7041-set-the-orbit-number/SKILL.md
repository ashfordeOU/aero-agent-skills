---
name: e7041-set-the-orbit-number
description: "Determine the effect of setting the on-board orbit number under ECSS-E-ST-70-41C clause 6.22.6.4: check the commanded number against the orbit number field, measure the jump against the number currently held, and group every scheduled activity into those the change carries past, those now due and those still ahead. Use when the set orbit number command, an orbit counter re-synchronisation after a propagator update, a backward orbit jump, or the disposition of position-based activities skipped by the change is being specified or reviewed. Refuses a non-integer orbit number and one outside the field. Trigger: ecss, e-st-70-41c, pus-service-22, set-orbit-number-command, orbit-counter-resynchronisation, backward-orbit-jump, skipped-scheduled-activity, orbit-number-field-range."
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
  tags: [ecss, e-st-70-41c, pus-service-22, e7041-set-the-orbit-number, set-orbit-number-command, orbit-counter-resynchronisation, backward-orbit-jump, skipped-scheduled-activity, orbit-number-field-range]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Position-Based Scheduling — Set the Orbit Number (space-systems/ecss/e7041-set-the-orbit-number)

Use when the task is the set orbit number command of ECSS-E-ST-70-41C clause
6.22.6.4 — moving the on-board orbit counter to a commanded value and working
out what that does to a position-based schedule already loaded against the
old one.

## Domain quick reference

- The command moves the reference every scheduled activity is pinned to. It
  is not a housekeeping counter; changing it re-decides which activities are
  behind the spacecraft and which are in front of it, all at once.
- The commanded value has to fit the on-board field. A number past the field
  is not clamped to the top of it, because a clamp silently reschedules
  every held activity against a position nobody commanded.
- A forward jump can step over activities without releasing them. They were
  due on an orbit the counter has now passed, so they are skipped rather
  than executed, and every one of them needs naming.
- A backward jump puts activities back in front of the spacecraft. Some of
  them have already run, so a schedule that simply re-arms them executes the
  same activity twice, and the reverse jump is the only place to catch that.
- Setting the number already held is not a no-op worth hiding. It is a
  legitimate command and the useful answer is that the schedule is
  unchanged, reported as such.
- The disposition of a skipped activity is a design decision, not a default.
  Dropping it loses a planned operation; keeping it leaves an entry due at a
  position the spacecraft will not reach again this counter cycle.

## Workflow

1. Validate the orbit number field width, then validate both the number
   currently held and the number the command carries against it.
2. Validate the activities: unique request identifiers, orbit numbers inside
   the field and angles inside one revolution from the ascending node.
3. Group the activities against the old orbit position, then against the new
   one, into past, due and ahead.
4. Name the jump and its magnitude, and derive the two differences that
   matter: the activities newly carried past, and the activities a backward
   jump has returned to the future.
5. Apply the declared disposition to the newly skipped activities: discard
   them, or keep them in the schedule.
6. Report the new orbit position, the three groups, the skipped and returned
   sets, the retained schedule and the findings the change earned.

## Pitfalls

- Clamping a commanded orbit number to the top of the field. The schedule
  then runs against a position the ground never sent, and nothing in the
  telemetry says the command was altered.
- Applying the change and reporting only the new counter. The activities the
  jump stepped over are the whole consequence of the command, and a bare
  counter report hides them.
- Treating a backward jump as an ordinary correction. Activities that have
  already executed come back into the future of the schedule, and the second
  execution is a real command to real hardware.
- Comparing on the orbit number alone. Two activities on the same orbit sit
  either side of the current angle, and only one of them is behind the
  spacecraft.
- Deciding the skipped disposition per command rather than per subservice.
  The same jump then drops an activity on one occasion and re-arms it on
  another, and the schedule stops being predictable.

## Behavior contract (gate 3)

The orbit number field validation, jump direction and magnitude, the
grouping of activities into past, due and ahead, the newly skipped and
returned-to-future differences, the skipped dispositions and the assembled
set orbit number assessment are exercised by the gate 3 contract test:
scripts/test_e7041_set_the_orbit_number.py against
scripts/e7041_set_the_orbit_number_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_set_the_orbit_number.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
