---
name: q40-02-step3-decide-act
description: "Evaluate the risk-reduction measures proposed for a space-system hazard under ECSS-Q-ST-40-02C clause 5.2.3, step 3. Use when the task is holding a control set to the hazard-reduction precedence - eliminate or minimize by design first, then a safety device, then a warning device, then a procedure or training - refusing a weaker order that carries no written justification for the orders it skipped, demanding verification evidence before any measure is credited, and recomputing the residual severity, likelihood band and risk index from the measures that survive that test. Trigger: ecss, q-st-40-02c, hazard-reduction-precedence-order, risk-reduction-measure-selection, safety-measure-effectiveness-verification, ecss-residual-risk-index, design-elimination-of-hazard, hazard-control-justification."
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
  tags: [ecss, q-st-40-02-hazard-analysis-scope, q40-02-step3-decide-act, hazard-reduction-precedence-order, risk-reduction-measure-selection, safety-measure-effectiveness-verification, ecss-residual-risk-index, design-elimination-of-hazard]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hazard Analysis — Step 3, Decide and Act (space-systems/ecss/q40-02-step3-decide-act)

Use when the task is step 3 of the ECSS-Q-ST-40-02C clause 5.2 process —
choosing the risk-reduction measures for a hazard in the order the
standard requires, proving each one works, and computing the residual
risk that is left once only the proven ones are credited.

## Domain quick reference

- The precedence is an order, not a menu. Eliminating or minimizing the
  hazard by design comes first because it removes the hazard rather
  than managing it; a safety device comes next because it acts without
  anybody noticing; a warning device next because it needs somebody to
  notice; a procedure or training last because it needs somebody to
  notice and then act correctly under the conditions the hazard itself
  created.
- A weaker order is admissible, but only against a written reason for
  every stronger order it skipped. "We wrote a procedure" is a decision
  when the design fix was shown to be unavailable, and an omission
  when it was not — and the two are indistinguishable in the register
  unless the justification is recorded per skipped order.
- A measure is credited only when its effectiveness is verified. An
  unverified measure is a proposal, and crediting a proposal in the
  residual risk converts it into an assumption that will be inherited
  by every later review as fact.
- Residual risk moves on two axes. A measure can cut the occurrence
  probability, lower the consequence severity, or both, and only the
  credited ones move either. Probabilities compound multiplicatively
  across independent measures; severity steps down the category list
  and stops at the mildest category rather than wrapping.
- The index runs from 1 at the worst cell to 16 at the mildest, so the
  acceptance test is a floor and not a ceiling. A residual index below
  the project floor is the direction that needs a waiver, and that
  waiver is a step-4 decision, not a step-3 one.

## Workflow

1. Validate each proposed measure: identifier, precedence order, the
   stronger orders justified as unavailable, verification state,
   reduction effectiveness in the unit interval, and any severity
   steps claimed. Reject an unknown order and a negative severity step.
2. Run the precedence check per measure: list every stronger order the
   measure skipped without a written justification. Each one is its own
   finding, so a procedure proposed against three unjustified stronger
   orders reports three times.
3. Run the effectiveness check per measure: an unverified measure is a
   finding, and a verified measure that reduces nothing is a different
   finding — the second is usually a copied row, not an error of fact.
4. Credit only the verified, effective measures and compound their
   probability reductions. Apply their severity steps, clamping at the
   mildest category.
5. Band the residual probability and read the residual risk index from
   the severity-likelihood matrix.
6. Compare the residual index against the project acceptance floor and
   report the initial index beside it, so the reduction achieved is
   visible rather than only the endpoint.
7. The hazard is acceptable at step 3 only when no measure carries a
   finding and the residual index has reached the floor.

## Pitfalls

- Reading the precedence as a list of options with equal standing. A
  procedure that could have been a design change is not an equivalent
  control; it moves the burden onto a person operating in the middle
  of the hazard.
- Justifying the skip once, at the top of the analysis, instead of per
  skipped order. A single blanket sentence cannot be checked against
  the specific design fix that was available for this hazard.
- Crediting an unverified measure because it is obviously going to
  work. The residual index it produces is indistinguishable from a
  verified one, and every downstream review inherits it as fact.
- Adding effectiveness fractions instead of compounding them. Two
  measures at 0.6 do not remove 120 percent of the probability; they
  leave 16 percent of it.
- Treating the index as a ceiling because higher numbers usually mean
  worse. Here 1 is the worst cell, so the acceptance test is a floor
  and an inverted comparison passes exactly the hazards it should stop.

## Behavior contract (gate 3)

The precedence-justification, effectiveness-verification, credited-measure,
compounding residual probability, severity-step clamping, likelihood
banding and residual-index logic is exercised by the gate 3 contract test:
scripts/test_q40_02_step3_decide_act.py against
scripts/q40_02_step3_decide_act_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_02_step3_decide_act.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
