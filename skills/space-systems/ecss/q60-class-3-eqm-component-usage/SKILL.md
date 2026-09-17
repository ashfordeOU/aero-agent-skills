---
name: q60-class-3-eqm-component-usage
description: "Evaluate how the parts fitted to an engineering qualification model are handled under the Class 3 rules of clause 6.1.6 of ECSS-Q-ST-60C: measure how many rungs below the flight-intended level each fitted part sits, refuse a relaxation deeper than the programme allows and one left without a recorded substitution note, accumulate the thermal cycles, rework operations and powered hours the model has spent against their declared limits, keep the governing stress, and return each part's post-use disposition with its flight-build position stated separately. Use when a Class 3 model parts list, build-standard substitution or post-test disposition is in front of you. Trigger: ecss, q-st-60c, q60-class-3-eqm-component-usage, q60-c3-eqm-relaxation-depth, q60-c3-eqm-substitution-note, q60-c3-eqm-consumed-life-fraction, q60-c3-eqm-post-use-disposition, q60-c3-eqm-flight-build-position."
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
  tags: [ecss, q-st-60-eee-components-scope, q-st-60c, q60-class-3-eqm-component-usage, q60-c3-eqm-relaxation-depth, q60-c3-eqm-substitution-note, q60-c3-eqm-consumed-life-fraction, q60-c3-eqm-post-use-disposition, q60-c3-eqm-flight-build-position]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Engineering Qualification Model Part Handling (space-systems/ecss/q60-class-3-eqm-component-usage)

Use when the task is clause 6.1.6 of ECSS-Q-ST-60C: what happens to the parts
that were actually fitted to an engineering qualification model under the
Class 3 rules — what was allowed to go in, what the model has since spent on
it, and where the part stands once the model campaign is over.

## Domain quick reference

- A model is routinely built with parts below the flight-intended level, and
  the question is never whether that happened but how far it went. Relaxation
  is measured in rungs on a quality ladder, so a single rung with an agreed
  substitution note and a three-rung drop nobody wrote down are different
  findings with different corrections.
- A part fitted better than the flight-intended level is not a relaxation. It
  raises no substitution question at all, and treating a negative depth as a
  deviation generates paperwork for the one case that needed none.
- The substitution note is the record that the relaxation was a decision. A
  depth inside the allowance with no note is not a compliant part with tidy-up
  pending; the decision it stands on was never captured, and a blank string in
  the field is the same as no field.
- A model spends several stresses at once, and only the one nearest its limit
  governs. Thermal cycles, rework operations and powered hours each carry their
  own declared limit; reading the largest raw count instead of the largest
  fraction picks the wrong stress almost every time.
- Being fit to stay in the model and being fit to fly are separate answers.
  A part that has spent life on a model is at best a candidate for the flight
  build subject to review, and a relaxed part is not even that — a clean model
  disposition is not a flight-build decision and must not be printed as one.
- An incomplete usage record is not a life finding. A part whose spent record
  is missing has no disposition to take, and reporting it as near a limit
  invents a number nobody measured.

## Workflow

1. Validate each fitted part: an identifier, the level it was actually fitted
   at, the level the flight build intends, and a mapping of what the model has
   spent. Hold an incomplete record apart before any check runs on it.
2. Measure the relaxation depth as the rung difference between fitted and
   flight-intended level, keeping the sign so a better part reads as better.
3. Refuse a depth beyond the programme's allowance, then refuse an allowed
   depth carrying no substitution note, reporting the first that fails so the
   finding names what has to be closed first.
4. Divide each spent stress by its declared limit, requiring a strictly
   positive limit and rejecting an unknown stress name rather than ignoring it.
5. Keep the stress with the largest consumed fraction, breaking a tie on the
   declared stress order so the answer is stable, and absorb representation
   error at a limit or a threshold with a named tolerance.
6. Take the post-use disposition from the governing fraction: past its limit,
   near it and held by the model, or available for continued model use.
7. State the flight-build position separately for every part, roll the parts up
   into one model-level verdict, and rank the findings worst first.

## Pitfalls

- Reading the largest raw stress count as the governing one. Limits differ by
  orders of magnitude between cycles, operations and hours, so only the
  fraction of each limit compares.
- Treating a part fitted above the flight-intended level as a deviation. The
  depth is negative, the substitution question never arises, and raising one
  buries the relaxations that do matter.
- Accepting a relaxation inside the allowance with no note. The allowance says
  how deep a recorded decision may go; it does not excuse the record.
- Carrying a clean model disposition into the flight build. The part has spent
  life, and the most it can be is a candidate subject to review.
- Reporting an incomplete usage record as a life or relaxation finding. Nothing
  was measured, so nothing can be concluded except that the record is missing.
- Widening a limit or a threshold so an exactly-landed part passes. An equality
  at the boundary is a representation question handled by the tolerance inside
  the comparison; the declared limit stays where it was declared.

## Behavior contract (gate 3)

The record validation, quality-ladder ranking, signed relaxation depth,
allowance and substitution-note refusals, per-stress consumed fractions,
governing-stress selection, post-use disposition, flight-build position and
ranked findings are exercised by the gate 3 contract test:
`scripts/test_q60_class_3_eqm_component_usage.py` against
`scripts/q60_class_3_eqm_component_usage_logic.py` (stdlib unittest, offline).
Run: `python3 scripts/test_q60_class_3_eqm_component_usage.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
