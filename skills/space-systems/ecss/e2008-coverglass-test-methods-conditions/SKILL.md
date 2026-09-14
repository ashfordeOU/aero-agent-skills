---
name: e2008-coverglass-test-methods-conditions
description: "Use when a coverglass acceptance procedure, test condition table or method reuse justification has to be reviewed. Audit a coverglass acceptance procedure against the method and condition definitions clause 8.5.3 of ECSS-E-ST-20-08C points forward to: follow each activity pointer and report one that resolves to nothing, settle a substituted method before any condition is compared, judge every condition under its own sense so a relaxation and an over-test are told apart, name a condition the procedure omitted or invented, flag a referenced definition nobody picks up, and return one reuse verdict with ranked findings. Trigger: ecss, e-st-20-08c, coverglass-acceptance-methods-and-conditions, coverglass-definition-pointer-resolution, coverglass-acceptance-method-substitution, coverglass-acceptance-condition-relaxation, coverglass-acceptance-over-test, coverglass-condition-sense-comparison."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e-st-20-08c, e2008-coverglass-test-methods-conditions, coverglass-acceptance-methods-and-conditions, coverglass-definition-pointer-resolution, coverglass-acceptance-method-substitution, coverglass-acceptance-condition-relaxation, coverglass-acceptance-over-test, coverglass-condition-sense-comparison]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses — Acceptance Test Methods and Conditions (space-systems/ecss/e2008-coverglass-test-methods-conditions)

Use when the task is clause 8.5.3 of ECSS-E-ST-20-08C: coverglass acceptance
testing is not defined where it is called for, it is run at the methods and
conditions defined further down clause 8. This leaf grades a declared
acceptance procedure against the definitions it claims to be reusing.

## Domain quick reference

- Everything that goes wrong here is a pointer problem, not a measurement
  problem. The procedure can be internally consistent, fully populated and
  signed, and still be measuring something the standard never asked for,
  because the reference at the far end was never opened.
- A pointer that resolves to nothing is the worst state and the easiest to
  miss. A procedure naming an activity the downstream clause never defines
  still reads as complete; no field is blank, the reference simply has no
  other end, and nobody notices until somebody tries to follow it.
- A substituted method is settled before any condition is looked at. Swapping
  a magnified examination for an unaided one, or a spectrophotometer scan for
  a handheld probe, invalidates every condition underneath it, and comparing
  the conditions anyway produces a tidy table about nothing.
- The same numeric gap means opposite things depending on the condition. A
  severity floor -- measurement points, magnification, probe sites -- is
  weakened by a smaller number. A permitted ceiling -- gauge resolution,
  wavelength step, humidity -- is weakened by a larger one. A set point with a
  tolerance is off its baseline in either direction.
- Relaxation and escalation are both deviations and are not the same finding.
  A relaxation leaves acceptance weaker than the qualification-era definition
  it inherits, which is what the clause exists to prevent. An escalation
  over-tests delivered hardware, costs money and rejects good pieces, so it is
  reported -- but whether it blocks is a project position, not a default.
- An omitted condition and an invented one are changes to the defined test,
  not details. A procedure that drops the illuminance and adds something of
  its own is not running the referenced test at a variation; it is running a
  different test with the referenced name on it.
- A definition the procedure never picks up is its own finding. The clause
  points at a set, and a set with entries nobody reaches has holes exactly
  where nobody is looking.

## Workflow

1. Validate each declared activity: a name, a method, and conditions carrying
   finite numbers. Refuse a repeated condition and a non-numeric value.
2. Follow the pointer to the referenced definition. Where it resolves to
   nothing, stop on that activity and report the dangling reference.
3. Compare the declared method against the referenced method. Where they
   differ, stop on that activity: the conditions underneath are not comparable.
4. Split the condition sets: referenced conditions the procedure omitted,
   declared conditions the reference does not carry, and the overlap.
5. Compare each overlapping condition under its own sense, and categorize it
   as reused, relaxed, escalated or off its baseline band.
6. Rank the activity verdict -- unresolved, substituted, omitted, invented,
   relaxed, off-baseline, escalated -- and apply the project carry positions.
7. Roll the procedure up: activities grouped by verdict, definitions nobody
   picked up, the reuse fraction, the weakest activity and every finding.

## Pitfalls

- Reading a fully populated procedure as a reused one. Completeness is a
  property of the paperwork; reuse is a property of the reference at the far
  end, and only one of the two is visible without following the pointer.
- Comparing conditions across two different methods. The table looks rigorous
  and means nothing, and it hides the substitution that caused it.
- Comparing every condition in one direction. A humidity ceiling and a
  magnification floor are weakened by opposite signs, so a single-direction
  comparison reports half the relaxations as over-tests and vice versa.
- Treating an escalation as harmless. Over-testing delivered hardware rejects
  good pieces and costs schedule; it is reported, and whether it blocks is
  read from the project position rather than assumed either way.
- Folding an invented condition into the comparison. It has no reference to be
  compared against, and averaging it in dilutes the findings that do.
- Grading only the activities the procedure listed. A referenced definition
  nobody picked up leaves a hole exactly where no one is looking.
- Judging a condition that lands exactly on its referenced bound by bare
  arithmetic. Declared values are routinely arrived at by arithmetic -- a step
  count multiplied out, a band summed up -- and the result can evaluate a unit
  in the last place either side of the bound on one platform and not on
  another; the comparison absorbs that while the referenced value stays as
  referenced.

## Behavior contract (gate 3)

The activity record validation, the pointer that resolves to nothing, the
substituted method settled before any condition, the floor, ceiling and
nominal senses with their opposite directions of relaxation and escalation,
the referenced bounds a float arrives at by arithmetic, the omitted and
invented conditions, the carry positions for an escalation and an off-baseline
set point, the ranked activity verdict, the definitions nobody picked up and
the rolled-up reuse verdict are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_test_methods_conditions.py against
scripts/e2008_coverglass_test_methods_conditions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_test_methods_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
