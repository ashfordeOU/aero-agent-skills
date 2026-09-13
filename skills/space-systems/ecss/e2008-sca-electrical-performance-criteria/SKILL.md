---
name: e2008-sca-electrical-performance-criteria
description: "Evaluate a solar cell assembly against the minimum current values ECSS-E-ST-20-08C clause 6.4.3.3.3 draws from the control drawing, before and after electron irradiation: confirm the minima come from the drawing rather than a datasheet, refuse a pair that allows no credible degradation, check the delivered electron fluence reached the level the drawing qualifies, then place each measured current against its own minimum with a guard band the size of the measurement uncertainty, reporting both margins and the retained current fraction. Use when a measured solar cell current is about to be recorded as a pass or a fail. Trigger: ecss, e-st-20-08c-clause-6-4-3-3-3, solar-cell-assembly-performance-criteria, solar-cell-control-drawing-minimum-current, post-electron-irradiation-current-retention, solar-cell-electron-fluence-qualification, solar-cell-current-measurement-guard-band."
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
  tags: [ecss, e-st-20-08-solar-cell-assembly-scope, e2008-sca-electrical-performance-criteria, solar-cell-assembly-performance-criteria, solar-cell-control-drawing-minimum-current, post-electron-irradiation-current-retention, solar-cell-electron-fluence-qualification, solar-cell-current-measurement-guard-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies -- Electrical Performance Criteria (space-systems/ecss/e2008-sca-electrical-performance-criteria)

Use when the task is clause 6.4.3.3.3 of ECSS-E-ST-20-08C -- deciding
whether a solar cell assembly passes, against minimum current values
stated for the condition before electron irradiation and the condition
after it, with both values taken from the control drawing for the
assembly. The clause fixes the source as firmly as it fixes the
comparison, and a criterion applied from the wrong source is not a
weaker judgement, it is a different one.

## Domain quick reference

- The pair of minima is the criterion, not one number applied twice.
  The before value accepts the assembly as built; the after value
  accepts what survives the exposure. An assembly can pass one and fail
  the other, and that is the outcome the clause is shaped to produce.
- The control drawing is the only source that carries authority here. A
  supplier's typical figure describes a population, a datasheet
  describes a family, and neither was the value the design was accepted
  against. Applying one silently moves the acceptance limit.
- A drawing pair is itself checkable. Electron irradiation removes
  current; it does not add any. A post-irradiation minimum above the
  pre-irradiation one is not a strict criterion, it is an inconsistency,
  and a pair that allows almost no loss is one nobody can meet.
- The after minimum only means anything at a stated exposure. A
  measurement taken after a lighter fluence can sail past the number
  while demonstrating nothing about the end-of-life condition the number
  was written for.
- Every comparison carries measurement uncertainty. Current measurement
  on an illuminated assembly is good to around a per cent at best, so a
  value that lands inside a per cent of its minimum has not been shown
  to be on either side of it. Recording that as a pass, or as a fail,
  invents precision the measurement never had.
- The retained fraction -- after over before, on the same article -- is
  the quantity that travels. Two assemblies can both pass while one
  degrades twice as far as the other, and the fraction is what an
  end-of-life power prediction actually consumes.

## Workflow

1. Validate the acceptance policy first: the accepted limit sources,
   the measurement uncertainty fraction and the credible retention
   window. An inverted retention window is refused rather than used.
2. Validate the drawing pair before touching any measurement: both
   minima positive, the after minimum at or below the before minimum,
   a drawing reference present, and a qualification fluence stated.
3. Check the source of the minima. A source outside the accepted list
   stops the judgement there and names what was used instead -- the
   measured currents are reported, but no verdict is drawn from a limit
   nobody can trace.
4. Check the drawing's own pair for credibility against the retention
   window, since a criterion demanding an implausible survival is a
   drawing finding, not an article finding.
5. Check the delivered fluence against the fluence the drawing
   qualifies. Short of it, the post-irradiation measurement does not
   demonstrate the criterion however high the current reads.
6. Place each measured current against its own minimum with a guard
   band the size of the measurement uncertainty, and group the outcome
   as above, unresolved, or below. A value landing exactly on a band
   edge is on the passing side; the comparison absorbs representation
   error and the minimum itself does not move.
7. Report both margins, the measured retained fraction and the
   degradation it implies, then close on one verdict, listing every
   finding rather than only the first.

## Pitfalls

- Quoting a beginning-of-life current as the acceptance evidence. It
  answers the before criterion only; the after criterion is a separate
  minimum at a stated exposure and needs its own measurement.
- Reading the minima off a datasheet because the drawing is slow to
  obtain. The numbers are usually close, which is what makes the
  substitution survive review, and the acceptance limit has moved with
  no record of it.
- Taking a pass from a current measured after a partial exposure. The
  fluence is part of the criterion, and an under-delivered exposure
  produces a comfortable number that demonstrates nothing.
- Recording a current sitting on its minimum as a pass. The measurement
  cannot resolve the difference, and the run has produced an
  unresolved result, which is a different thing to report.
- Comparing a measured current against a guard-band edge by bare
  arithmetic. The band is a fraction of a measured minimum, so both
  sides are floats that can land a few units in the last place either
  side of the edge; the comparison absorbs that error while the minimum
  itself is never relaxed.
- Reporting the retained fraction against the drawing minimum rather
  than against the article's own before measurement. The first is a
  property of the criterion, the second is a property of the assembly,
  and only the second predicts what the array does at end of life.

## Behavior contract (gate 3)

The policy validation, drawing-pair validation and self-consistency
rule, accepted limit-source check, retention window credibility,
qualification fluence check, guard-banded current outcome grouping,
margin and retained fraction reporting and the acceptance verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_sca_electrical_performance_criteria.py against
scripts/e2008_sca_electrical_performance_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_sca_electrical_performance_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
