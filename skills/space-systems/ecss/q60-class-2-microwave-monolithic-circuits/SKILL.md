---
name: q60-class-2-microwave-monolithic-circuits
description: "Evaluate a microwave monolithic integrated circuit offered for class 2 equipment under ECSS-Q-ST-60C clause 5.6.5: take the semiconductor technology, the source route and the delivery form, measure the guard band at each edge of the sweep the part was characterized over, resolve the junction temperature across the die and interface thermal path against the class 2 derating limit, take the drive utilisation and the output backoff below compression, group the electrostatic withstand, then assemble the compensating evidence the route and the delivery form oblige. Use when a class 2 radio frequency chain needs a monolithic microwave amplifier or converter stage. Trigger: ecss, q-st-60c-clause-5-6-5, class-2-mmic-source-route, class-2-mmic-guard-band-margin, class-2-mmic-junction-temperature-derating, class-2-mmic-output-backoff, class-2-mmic-compensating-evidence."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-2-microwave-monolithic-circuits, class-2-mmic-source-route, class-2-mmic-guard-band-margin, class-2-mmic-junction-temperature-derating, class-2-mmic-output-backoff, class-2-mmic-compensating-evidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 2 — Microwave Monolithic Circuits (space-systems/ecss/q60-class-2-microwave-monolithic-circuits)

Use when the task is clause 5.6.5 of ECSS-Q-ST-60C: a class 2 radio-frequency
chain needs a microwave monolithic integrated circuit, and the decision spans
the design that calls for it, the route it is drawn from, the purchase that
brings it in and the application that then runs it.

## Domain quick reference

- Class 2 widens the source base and pays for the width with evidence the
  project builds itself. A commercial catalogue part is admissible here in a
  way it is not at class 1, but it arrives with nothing demonstrated, so the
  survey, the evaluation programme, the radiation evaluation and the
  upscreening all attach to it before it attaches to a board.
- The part is bought as a component and used as a circuit, and the two halves
  do not separate. A faultlessly procured device is still nonconforming if the
  stage runs it outside the sweep it was measured over, hotter than the class 2
  junction limit, or inside compression.
- The guard band is the honest statement of the frequency margin. Coverage
  answers only whether the application fits; the guard at each edge says how
  much measured data stands between the chain and the end of the sweep, and a
  negative guard is the width running on numbers nobody took.
- Junction temperature is computed across two resistances, not one. The die to
  case path belongs to the part; the case to baseplate path belongs to the
  installation, and the interface is the half that drifts between the thermal
  analysis and the hardware that gets built.
- Backoff and utilisation are different questions. Drive utilisation asks
  whether the stage respects the rated input; backoff in decibels asks whether
  it sits far enough below compression for the linearity the link budget
  assumed, and a stage can pass one and fail the other.
- Package form decides which evidence set attaches. A bare die moves
  hermeticity and the attach process onto the equipment builder; a plastic body
  moves moisture uptake and popcorn behaviour there instead. Neither is simply
  a cheaper package.

## Workflow

1. Validate the case: the technology, the source route, the delivery form,
   both frequency bands, the two-stage thermal path and the three drive
   levels. A missing field is an input error, because the disposition is a
   conjunction and an absent term cannot be assumed benign.
2. Measure the guard band at the lower and upper edges, take the narrowest
   guard against the policy floor and report the span that was never measured.
3. Resolve the junction temperature across the die-to-case and
   case-to-baseplate resistances and take its margin against the class 2
   derating limit.
4. Take the drive utilisation as a share of rated drive, and the output backoff
   in decibels below the compression point, against their limits.
5. Assemble the compensating evidence the source route obliges, add what the
   delivery form obliges, and add reinforced handling controls when the
   electrostatic withstand sits below the control threshold.
6. Return the disposition in precedence order: not admissible when the policy
   bars the route; application nonconforming when a band, thermal, drive or
   backoff check fails; admissible with compensating evidence when anything
   beyond plain lot acceptance attaches; admissible as procured otherwise.

## Pitfalls

- Reading a datasheet plot past its last measured point. The curve ends where
  the sweep ended, and a stage placed above that edge runs on an extrapolation
  nobody took a measurement for.
- Treating class 2 as class 1 with the paperwork removed. The width of the
  source base is exactly what the compensating evidence pays for, and dropping
  the evidence leaves the width with nothing behind it.
- Taking the junction temperature from the die thermal resistance alone. The
  interface to the baseplate can add as much again, and it is the term that
  degrades with a rework, a shim or a torque that drifted.
- Quoting a drive level in decibels and comparing it as if it were linear. A
  utilisation limit is a ratio of powers; mixing the two representations is how
  a stage ends up a factor over its limit while the arithmetic looks right.
- Reading a stage as linear because the utilisation passed. Rated drive and the
  compression point are different numbers, and a part can sit inside its rating
  and still be generating the intermodulation the budget had no room for.
- Comparing a computed junction temperature, utilisation or backoff with its
  limit by bare arithmetic. All three are computed, and a decibel value comes
  through a logarithm that is not correctly rounded, so a case sitting exactly
  on its limit can land a few units in the last place the wrong side of it.

## Behavior contract (gate 3)

The policy merge, case validation, guard band margins and uncharacterized span,
two-stage junction temperature and margin, drive utilisation, output backoff in
decibels, electrostatic control grouping, compensating evidence assembly and
the four-way disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_2_microwave_monolithic_circuits.py against
scripts/q60_class_2_microwave_monolithic_circuits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_microwave_monolithic_circuits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
