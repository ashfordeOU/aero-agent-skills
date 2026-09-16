---
name: q60-class-1-eqm-component-usage
description: "Use when a model parts list, build-standard substitution or post-test part disposition is in front of you. Evaluate how parts fitted to an engineering qualification model are handled under the Class 1 rules of clause 4.1.6 of ECSS-Q-ST-60C: measure how far each fitted part's quality level sits below the flight-intended level, refuse a relaxation deeper than the programme allows and one left without a recorded substitution note, accumulate the thermal cycles, rework operations and powered hours the model has spent against their declared limits, keep the governing stress, and return each part's post-use disposition with the flight-build position stated. Trigger: ecss, q-st-60c, q60-eqm-fitted-part-usage-permission, q60-eqm-quality-level-relaxation-depth, q60-eqm-consumed-life-fraction, q60-eqm-post-use-disposition, q60-eqm-flight-build-reuse-position."
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
  tags: [ecss, q-st-60-eee-components-scope, q-st-60c, q60-class-1-eqm-component-usage, q60-eqm-fitted-part-usage-permission, q60-eqm-quality-level-relaxation-depth, q60-eqm-consumed-life-fraction, q60-eqm-post-use-disposition, q60-eqm-flight-build-reuse-position]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Parts Fitted to an Engineering Qualification Model (space-systems/ecss/q60-class-1-eqm-component-usage)

Use when the task is clause 4.1.6 of ECSS-Q-ST-60C: the parts fitted to an
engineering qualification model on a Class 1 programme — which of them are
allowed to be there, what the model spends on each one, and where each goes
when the campaign is over.

## Domain quick reference

- A model is built to be used up. That is its purpose, and it is also why the
  handling rules exist: every part on it accumulates a history the flight build
  will not have, so the part's own future has to be decided as deliberately as
  its selection was.
- The relaxation is measured on a ladder, in steps. A part one step below the
  flight-intended level is a different case from one three steps below, and
  both are different from a part that is better than the flight part. Measuring
  the depth, rather than answering yes or no, is what lets a programme allow
  the first, refuse the third and stop arguing about the second.
- A permitted relaxation still has to be written down. An unrecorded
  substitution is not a smaller version of a recorded one; it is the same
  hardware with no trace of the decision, so the next reader cannot tell
  whether anybody chose it or whether a stores clerk grabbed what was on the
  shelf. Recording it costs a line and is the whole difference.
- Interchangeability comes first. A part that does not match the
  flight-intended one in form, fit and function is not a relaxation to be
  graded at all — the model stops representing the flight build, and the depth
  of the quality step is beside the point.
- Consumed life is governed by one stress, not by an average. A part at ten
  percent of its thermal cycles and at its full rework count is a spent part,
  and averaging the three numbers reports it as lightly used. The governing
  stress is worth naming, because it is what the next campaign has to plan
  around.
- The flight-build position is stated, never inferred. A part that has been
  through a model's build, test and rework history is not a candidate for a
  flight build, and writing that on every record is cheaper than discovering
  later that somebody read silence as permission.

## Workflow

1. Validate the programme's per-stress limits — thermal cycles, rework
   operations, powered hours — each strictly positive; a zero limit is an input
   error, not an unlimited allowance.
2. Grade each fitted part on the attributes without which its handling cannot
   be decided, and stop there when any is absent: an incomplete record is not a
   refusal and must not be reported as one.
3. Decide interchangeability first, then the relaxation depth against the
   flight-intended level, then whether a depth greater than zero carries a
   recorded substitution note. A blank note is not a note.
4. Refuse outright a depth beyond what the programme allows, whatever note
   accompanies it; a note records a decision that was available to take, it
   does not create one that was not.
5. Form each stress as a fraction of its own limit, keep the largest as the
   consumed life and name the stress that governs it, treating an absent stress
   as unspent rather than as unknown.
6. Turn the consumed life into a disposition: return to model stock below the
   retention threshold, hold for review from the threshold up, scrap at or
   above the limit — absorbing floating-point representation error at both
   boundaries with a named tolerance rather than by moving the limit.
7. Return every record with its flight-build position stated, the scrap list,
   the most spent part, and one model verdict with findings ranked worst first.

## Pitfalls

- Treating an unrecorded substitution as a paperwork detail. The hardware may
  be perfectly acceptable; what is missing is any evidence that the choice was
  made rather than defaulted to, and that is the thing the clause is protecting.
- Grading the quality step of a part that is not interchangeable. The model has
  already stopped representing the flight build, and a two-step relaxation
  finding buries the larger problem underneath it.
- Averaging the stresses into a single usage number. One exhausted stress makes
  the part spent; the average makes it look fine and sends it back to stock.
- Reading an absent stress figure as an unknown that blocks the assessment. A
  stress the model never applied is zero; what must never be assumed is a limit
  nobody declared.
- Letting a part drift back toward a flight build because nothing on its record
  says it cannot. Silence is the failure mode; the position is written on every
  record precisely so that it cannot be read as permission.
- Moving a limit or a threshold so an exactly-reached case passes. An equality
  at the boundary is a representation question, handled by the tolerance inside
  the comparison; the declared limit stays as declared.

## Behavior contract (gate 3)

The quality-ladder ranking, relaxation depth, substitution-note requirement,
interchangeability precedence, per-stress consumed-life accounting with a named
governing stress, post-use disposition boundaries, flight-build position and
ranked findings are exercised by the gate 3 contract test:
`scripts/test_q60_class_1_eqm_component_usage.py` against
`scripts/q60_class_1_eqm_component_usage_logic.py` (stdlib unittest, offline).
Run: `python3 scripts/test_q60_class_1_eqm_component_usage.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
