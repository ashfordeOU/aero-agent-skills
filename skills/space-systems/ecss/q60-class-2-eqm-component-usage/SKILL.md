---
name: q60-class-2-eqm-component-usage
description: "Evaluate how parts fitted to an engineering qualification model are handled under the Class 2 rules of clause 5.1.6 of ECSS-Q-ST-60C: settle interchangeability first, measure how many quality-ladder rungs each fitted part sits below the flight-intended one, refuse a depth past the Class 2 allowance and one left unjustified, accumulate thermal cycles, rework operations and powered hours against their declared limits, keep the governing stress, then rule on the carry-over Class 2 permits, which costs retained margin and recorded re-screening. Use when a model parts list, build-standard substitution or post-campaign disposition is in front of you. Trigger: ecss, q-st-60c, q60c2-eqm-relaxation-depth, q60c2-eqm-consumed-life-margin, q60c2-eqm-flight-reuse-eligibility, q60c2-eqm-rescreening-requirement."
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
  tags: [ecss, q-st-60c, q-st-60c-eee-class-2-scope, q60-class-2-eqm-component-usage, q60c2-eqm-fitted-part-permission, q60c2-eqm-relaxation-depth, q60c2-eqm-consumed-life-margin, q60c2-eqm-flight-reuse-eligibility, q60c2-eqm-rescreening-requirement, q60c2-eqm-post-campaign-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Parts Fitted to a Class 2 Engineering Qualification Model (space-systems/ecss/q60-class-2-eqm-component-usage)

Use when the task is clause 5.1.6 of ECSS-Q-ST-60C: the parts fitted to an
engineering qualification model on a Class 2 programme — which of them are
allowed to be there, what the model spends on each one, and where each goes when
the campaign is over, including the one place a Class 2 model can send a part
that a Class 1 model cannot.

## Domain quick reference

- A model is built to be used up. That is its purpose, and it is also why the
  handling rules exist: every part on it accumulates a history the flight build
  will not have, so the part's own future has to be decided as deliberately as
  its selection was.
- The relaxation is measured on a ladder, in rungs. A part one rung below the
  flight-intended level is a different case from one four rungs below, and both
  are different from a part that is better than the flight part. Measuring the
  depth, rather than answering yes or no, is what lets a programme allow the
  first, refuse the third and stop arguing about the second.
- The Class 2 allowance is wider than the Class 1 one and it is still an
  allowance. A depth past it is refused whatever accompanies it, because a
  justification records a decision that was available to take; it does not
  create one that was not.
- Interchangeability comes first. A part that does not match the flight-intended
  one in form, fit and function is not a relaxation to be graded at all — the
  model stops representing the flight build, and the depth of the quality rung
  is beside the point.
- Consumed life is governed by one stress, not by an average. A part at ten
  percent of its thermal cycles and at its full rework count is a spent part,
  and averaging the three numbers reports it as lightly used. The governing
  stress is worth naming, because it is what the next campaign plans around.
- The carry-over is the Class 2 relief and it is conditional twice over. A part
  a project nominates for a flight build has to still hold the reserve share of
  its life, and it has to carry a recorded re-screening. Margin without the
  re-screening is a part nobody looked at again; the re-screening without the
  margin is a careful look at something already spent.
- A part nobody nominates gets no reuse decision at all. Answering a question
  the project did not ask fills the record with dispositions nobody acts on and
  buries the two that matter.

## Workflow

1. Validate the programme's per-stress limits — thermal cycles, rework
   operations, powered hours — each strictly positive; a zero limit is an input
   error, not an unlimited allowance.
2. Grade each fitted part on the attributes without which its handling cannot be
   decided, and stop there when any is absent: an incomplete record is not a
   refusal and must not be reported as one.
3. Decide interchangeability first, then the relaxation depth against the
   flight-intended level, then whether a depth greater than zero carries a
   written justification. A blank justification is not a justification.
4. Refuse outright a depth past the Class 2 allowance, whatever accompanies it.
5. Form each stress as a fraction of its own limit, keep the largest as the
   consumed life, name the stress that governs it, and take the remainder as the
   margin the part still holds. An absent stress is unspent, not unknown.
6. Turn the consumed life into a post-campaign disposition: return to model
   stock below the retention threshold, hold for review from the threshold up,
   scrap at or above the limit — absorbing representation error at both
   boundaries with a named tolerance rather than by moving the limit.
7. For a nominated part only, rule on the flight-build carry-over: refused for a
   part that was never permitted on the model, refused below the margin reserve,
   conditional on a re-screening that is not yet recorded, and cleared when both
   hold.
8. Return every record, the scrap list, the parts actually cleared for a flight
   build, the most spent part, and one model verdict with findings ranked worst
   first.

## Pitfalls

- Treating an unjustified relaxation as a paperwork detail. The hardware may be
  perfectly acceptable; what is missing is any evidence that the choice was made
  rather than defaulted to, and that is the thing the clause protects.
- Grading the quality rung of a part that is not interchangeable. The model has
  already stopped representing the flight build, and a two-rung relaxation
  finding buries the larger problem underneath it.
- Averaging the stresses into a single usage number. One exhausted stress makes
  the part spent; the average makes it look fine and sends it back to stock.
- Reading the Class 2 carry-over as permission to reuse model parts generally.
  It applies to a part the project nominates, that still holds its reserve, and
  that has been re-screened; drop any of the three and it is a Class 1 refusal
  wearing a different label.
- Clearing a nominated part on margin alone. Margin says the part has life left,
  not that anyone has looked at what the campaign did to it.
- Moving a limit, a threshold or the reserve so an exactly-reached case passes.
  An equality at the boundary is a representation question, handled by the
  tolerance inside the comparison; the declared value stays as declared.

## Behavior contract (gate 3)

The quality-ladder ranking, relaxation depth against the Class 2 allowance,
justification requirement, interchangeability precedence, per-stress
consumed-life accounting with a named governing stress, remaining margin,
post-campaign disposition boundaries, nominated-only flight-build carry-over
with its margin reserve and re-screening condition, and ranked findings are
exercised by the gate 3 contract test:
`scripts/test_q60_class_2_eqm_component_usage.py` against
`scripts/q60_class_2_eqm_component_usage_logic.py` (stdlib unittest, offline).
Run: `python3 scripts/test_q60_class_2_eqm_component_usage.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
