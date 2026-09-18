---
name: q7031-film-thickness-control
description: "Compute and grade the wet and dry film thickness of every coat in a paint system under ECSS-Q-ST-70-31C: reduce the tin volume solids by the thinner added at the gun, issue the wet comb target that lands a coat inside its dry band, grade the gauge population so a thin spot under the absolute floor is caught even when the mean reads acceptable, and sum the coat means into a system thickness. Use when a coat has to be sprayed to a thickness band, a gauge reading set needs a verdict, or a stack of individually good coats may overshoot the system maximum. Trigger: ecss, q-st-70-31c-paint-application, coating-wet-film-thickness-target, coating-dry-film-thickness-band, paint-volume-solids-thinning, paint-system-total-dft, coating-thin-spot-floor."
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
  tags: [ecss, q-st-70-31c-paint-application-scope, q7031-film-thickness-control, coating-wet-film-thickness-target, coating-dry-film-thickness-band, paint-volume-solids-thinning, paint-system-total-dft, coating-thin-spot-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paint Application -- Film Thickness Control (space-systems/ecss/q7031-film-thickness-control)

Use when the task is the per-coat thickness control of ECSS-Q-ST-70-31C:
deciding what wet film the operator has to lay down, and deciding whether the
dry film readings taken afterwards put the coat, and the finished system,
inside the bands the paint system declares.

## Domain quick reference

- The operator can only control the wet film. The dry film is what the
  requirement is written against, and the bridge between them is volume
  solids: a wet film leaves behind the solids fraction of its own thickness.
  Issuing a dry number to a spray booth is issuing a number nobody can set.
- Thinner added at the gun is not free. It dilutes the solids in the cup, so
  a paint thinned by a tenth of its volume converts at roughly a tenth less
  solids than the tin value, and a wet comb target computed from the tin
  value lands the coat under its band.
- A coat is graded as a population, not as a reading. The mean carries the
  band decision, but a mean sitting comfortably mid-band can hide a thin spot
  with no barrier left at all, so a separate absolute floor, a fraction of
  the band minimum, is applied reading by reading.
- Coat maxima and the system maximum are different requirements. Three coats
  each individually inside their band can stack past a system limit set for
  mass, thermo-optical behaviour or crack resistance, so the summed thickness
  is graded in its own right.
- Spreading rate follows from the target dry thickness and the effective
  solids, derated by transfer efficiency. It is how the material draw is
  sized, and an undrawn litre is the usual reason a last coat comes out thin.

## Workflow

1. Validate each coat record: volume solids in a physical range, a thinner
   ratio that is not negative, a band whose minimum does not exceed its
   maximum, and a non-empty reading population.
2. Reduce the declared volume solids by the thinner ratio to get the solids
   actually in the cup, and carry that value through every conversion.
3. Take the coat target as the midpoint of its dry band and convert it to the
   wet comb target the operator sets, plus the spreading rate at that target.
4. Grade the gauge population: mean against the band, every reading against
   the absolute floor, every reading against the coat maximum. Keep each
   breach as its own finding rather than collapsing them into one verdict.
5. Sum the coat means into the system dry film thickness and grade it against
   the system band when one is declared.
6. Return per-coat records and the system verdict with every finding named
   and prefixed by the coat it belongs to.

## Pitfalls

- Converting at the tin volume solids after thinning at the gun. The wet comb
  target comes out low, every coat lands under its band, and the defect shows
  up only when the system total is measured at the end.
- Accepting a coat on its mean alone. The mean is a population statistic; the
  barrier property belongs to the thinnest point, which is why the floor is
  applied reading by reading and not to the average.
- Grading only the coats and never the stack. A system maximum exists for its
  own reasons, and a stack of compliant coats can still breach it.
- Measuring dry film thickness on a coat that has not reached its cure state.
  A gauge reading on a soft film is a reading of an intermediate condition,
  not of the dry thickness the requirement is written against.
- Moving a band limit to absorb a reading that landed exactly on it. Equality
  at a limit is a representation question, handled by the tolerance inside
  the comparison; the declared band stays as specified.

## Behavior contract (gate 3)

The coat record validation, the thinner-corrected volume solids, the wet and
dry conversions in both directions, the spreading rate, the population
grading against band, floor and maximum, and the system-total verdict are
exercised by the gate 3 contract test:
scripts/test_q7031_film_thickness_control.py against
scripts/q7031_film_thickness_control_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7031_film_thickness_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
