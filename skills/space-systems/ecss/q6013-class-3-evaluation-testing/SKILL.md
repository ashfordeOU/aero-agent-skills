---
name: q6013-class-3-evaluation-testing
description: "Determine whether the evaluation tests run on a commercial part type support its use at the lowest assurance class under clause 6.2.3.4 of ECSS-Q-ST-60-13C: size the reduced sample draw of every test group from its full-assurance size and an absolute floor, hold each executed group to zero admissible failures and to its parameter-drift limit, separate a mandatory group that was never run from a group that passed clean, and report the confidence the smaller draw actually demonstrates with one part-type verdict. Use when reduced evaluation test results have to decide a commercial part type. Trigger: ecss, q-st-60-13c, q6013-class-3-evaluation-testing, reduced-evaluation-test-group, class-3-sample-draw, zero-failure-acceptance, parameter-drift-limit."
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
  tags: [ecss, q-st-60-eee-scope, q-st-60-13c, q6013-class-3-evaluation-testing, reduced-evaluation-test-group, class-3-sample-draw, zero-failure-acceptance, parameter-drift-limit, demonstrated-zero-failure-confidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components — Class 3 Evaluation Testing (space-systems/ecss/q6013-class-3-evaluation-testing)

Use when the task is clause 6.2.3.4 of ECSS-Q-ST-60-13C: the evaluation tests
a commercial part type has to go through before it may be used at the lowest
assurance class, and the question of whether the results that came back
support that use.

## Domain quick reference

- The subject is a part type -- a manufacturer and a part number -- not a
  delivery and not a lot. A result with no such identity qualifies nothing,
  because there is nothing a later purchase has to match.
- The reduced campaign runs the same test groups as a full one, drawn smaller.
  Each group carries a full-assurance sample size; the class-3 draw is that
  size scaled by the reduction factor, rounded up, and never taken below an
  absolute floor. The rounding is upward on purpose -- a fractional device is
  a device -- and the floor exists because a draw of one or two stops being a
  sample of anything.
- Reducing the draw does not relax acceptance. A group is accepted on zero
  failures at the lowest assurance class exactly as at any other, because a
  smaller sample makes a single failure more significant, not less.
- The electrical groups also carry a parameter-drift limit, and the band under
  that limit is not uniform. Drift high in the band is not a failure and is
  not silence either: it is the warning that the reduced draw may be the only
  thing hiding a trend, so it is reported without blocking.
- A mandatory group that was never run is a coverage shortfall, not a group
  with no failures. Comparing the executed set against the mandatory set
  before any verdict is formed is what keeps the two apart.
- A clean reduced run buys only so much. The confidence a zero-failure run of
  a given size gives against a stated defect fraction is reported next to the
  verdict, so the programme can see what the smaller draw actually bought
  rather than reading "no failures" as "no risk".
- The weakest group governs the demonstrated confidence, because the part type
  is only as evidenced as its thinnest draw.

## Workflow

1. Validate the part-type identity -- manufacturer and part number -- and the
   campaign settings: reduction factor, defect fraction and the confidence the
   reduced draw is expected to demonstrate.
2. Validate every declared group: its name, sample count, failure count and,
   for a drift-bearing group, its drift reading and the limit that reading is
   held to. Reject a group reporting more failures than samples, a group drawn
   with no samples, a drift-bearing group with no limit, or a group declared
   twice.
3. Size the required draw for each group from its full-assurance size and the
   reduction factor, rounding up and holding the absolute floor.
4. Assess each executed group against its required draw, against zero
   admissible failures, and against its drift limit and warning band, keeping
   every finding rather than the first.
5. Compare the executed set against the mandatory set and record each absent
   mandatory group as a shortfall; record an absent supporting group as an
   action instead.
6. Take the weakest group's demonstrated confidence as the campaign figure and
   compare it with the target, absorbing representation error at the boundary
   with a named tolerance rather than by lowering the target.
7. Name the verdict -- not suitable on any blocking finding, suitable with
   actions while any finding stands, suitable only when neither is true -- and
   carry the per-group records and the whole finding list with it.

## Pitfalls

- Reading an unrun group as a clean group. A campaign that never ran the
  endurance group has no endurance failures; that is a shortfall and has to be
  named as one before any verdict is formed.
- Admitting a failure because the draw was small. The smaller sample is the
  reason one failure matters more, not a reason to discount it.
- Rounding the reduced draw down to the nearest whole device. The draw is a
  floor on evidence, and rounding down spends evidence the class never offered
  to give back.
- Letting the reduction factor take a group below the absolute floor. Below it
  the group stops describing the part type and describes the devices that were
  to hand.
- Treating drift inside the limit as a clean result. Drift high in the band is
  the one signal a reduced draw still gives about a trend, and dropping it
  wastes the only early warning available.
- Reading "no failures" as "no risk" and never stating the confidence the draw
  demonstrated. A clean run of three devices and a clean run of twelve are not
  the same evidence.
- Stopping at the first blocking finding, so the next test round discovers the
  next shortfall instead of repairing both at once.

## Behavior contract (gate 3)

The part-type identity validation, group validation, reduced draw sizing and
floor, zero-failure acceptance, drift limit and warning band, mandatory-group
coverage, demonstrated confidence and the part-type verdict are exercised by
the gate 3 contract test:
scripts/test_q6013_class_3_evaluation_testing.py against
scripts/q6013_class_3_evaluation_testing_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_evaluation_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
