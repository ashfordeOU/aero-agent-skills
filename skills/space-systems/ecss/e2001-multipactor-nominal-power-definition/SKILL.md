---
name: e2001-multipactor-nominal-power-definition
description: "Use when derive the nominal input power at which equipment stays free of multipactor discharge under ECSS-E-ST-20-01C clause 4.3.1.1: take the declared per-carrier powers at the equipment input, combine them by the agreed rule -- the in-phase peak envelope for a multi-carrier unit, the average sum where that is what the input sees -- convert between watt and decibel-milliwatt, aggregate the input-power budget with signed biases added algebraically and uncertainty magnitudes combined linearly or by root-sum-square, check the declared multipactor-free power covers that worst-case input rather than the nominal drive level, and raise it by the route margin to obtain the level the analysis or the multipactor-test has to reach. Trigger: ecss, e-st-20-electrical-scope, multipactor-free-power, nominal-input-power, multi-carrier-peak-envelope, peak-to-average-ratio, power-uncertainty-budget, decibel-milliwatt-conversion."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-nominal-power-definition, multipactor-free-power, nominal-input-power, multi-carrier-peak-envelope, peak-to-average-ratio, power-uncertainty-budget, decibel-milliwatt-conversion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Multipactor Nominal Power Definition (space-systems/ecss/e2001-multipactor-nominal-power-definition)

Use when the task is fixing the number that ECSS-E-ST-20-01C clause
4.3.1.1 turns into a requirement -- the specified input power at which the
equipment is required to stay free of multipactor discharge. Everything
downstream (the margin policy, the analysis, the campaign level) is
referred to this one figure, so it has to be the worst case the input
really sees.

## Domain quick reference

- The definition is stated at the equipment input, not at the amplifier
  output and not at the antenna. Whatever sits between them -- harness
  loss, a pre-amplifier, a switch -- belongs in the budget that leads to
  the input figure, never left implicit.
- Carriers combine on amplitude, not on power. N carriers that can align
  in phase produce an envelope of the squared sum of their amplitudes,
  which for N equal carriers is N-squared times one carrier, that is N
  times their average sum. Two equal carriers therefore peak 3 dB above
  the average sum and four peak 6 dB above it.
- Which rule applies is an engineering statement about the unit, not a
  preference. A multi-carrier unit whose carriers can align is defined on
  the in-phase envelope; a unit that only ever sees the summed average
  may be defined on that, and the peak-to-average ratio is then the
  quantity that has to be stated rather than quietly dropped.
- The budget carries two different kinds of term. A bias is signed and
  adds algebraically -- a harness loss lowers the input, a gain raises
  it. An uncertainty is a magnitude and only ever widens the worst case;
  magnitudes combine linearly for a hard worst case, or by root-sum-square
  when the project accepts a statistical combination.
- The declared multipactor-free power has to cover the derived worst
  case. Declaring the nominal drive level and carrying the uncertainties
  elsewhere leaves the requirement stated at a power the equipment is not
  held to.
- The declared power is the reference, not the demonstration level. The
  route margin is applied on top of it: the level an analysis has to
  clear, or the level a multipactor-test has to be driven to, sits above
  the declared power by the margin the route owes.

## Workflow

1. Validate the per-carrier powers at the equipment input: a strictly
   positive, finite watt figure per carrier, at least one carrier.
2. Combine them by the declared rule -- in-phase envelope, average sum,
   or a single carrier on its own -- rejecting a single-carrier rule
   applied to a carrier set and an unrecognized rule outright.
3. Report the peak-to-average ratio of the carrier set, so a
   multi-carrier unit defined on its average sum is visible as a
   deliberate decision rather than an omission.
4. Aggregate the input-power budget: biases summed algebraically,
   uncertainty magnitudes combined linearly or by root-sum-square. A
   negative uncertainty magnitude is a contradiction and stops the
   derivation.
5. Convert the combined power to decibel-milliwatt and add the budget to
   obtain the worst-case input the definition has to cover.
6. Compare the declared multipactor-free power with that worst case. A
   declaration landing exactly on it is compliant -- the comparison
   absorbs floating-point representation error rather than widening the
   engineering limit -- and anything measurably below reports its
   shortfall in decibel.
7. Apply the route margin to the declared power to obtain the level the
   analysis or the multipactor-test has to reach, and aggregate the
   findings.

## Pitfalls

- Adding carrier powers for a multi-carrier unit. The summed average is
  N times one carrier where the in-phase envelope is N-squared times it;
  on four equal carriers that is a 6 dB understatement of the field the
  gaps actually see.
- Declaring the nominal drive level as the multipactor-free power. The
  requirement then sits below the power the unit reaches on a bad day,
  and every margin computed from it inherits the error.
- Treating an uncertainty as a signed term. A drive tolerance widens the
  worst case in the adverse direction whichever way it is written; giving
  it a sign lets a negative entry cancel a real bias and shrink the
  budget.
- Mixing the decibel conventions. Ten log of a power ratio and twenty log
  of a voltage ratio are the same margin expressed twice; using the
  voltage form on powers doubles every figure in the budget.
- Confusing the declared power with the demonstration level. The route
  margin sits above the declaration; reading the raised level back as the
  requirement inflates the specification the equipment is qualified to.
- Stating the figure without its interface. The same unit has different
  input powers at the amplifier output and after the harness, and a
  definition that does not name the plane is not a definition.

## Behavior contract (gate 3)

The carrier validation, amplitude-based combining rules,
peak-to-average ratio, watt and decibel-milliwatt conversion, bias and
uncertainty budget aggregation, worst-case derivation, boundary-safe
declaration check, route margin lookup and the aggregated verdict are
exercised by the gate 3 contract test:
scripts/test_e2001_multipactor_nominal_power_definition.py against
scripts/e2001_multipactor_nominal_power_definition_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_multipactor_nominal_power_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
