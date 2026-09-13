---
name: e2001-dimensional-accuracy-and-stability
description: "Use when derive the worst-case gap dimension of a multipactor-critical radio-frequency gap under ECSS-E-ST-20-01C clause 5.3.3.2: categorize every dimensional contribution as manufacturing-accuracy (machining-tolerance, assembly-tolerance, plating-thickness-variation) or in-service-dimensional-stability (thermo-elastic-expansion, launch-induced-permanent-set, material-creep, moisture-release-shrinkage), stack them arithmetically for a true worst-case bound or root-sum-square for independent random terms while systematic terms stay linear, bound the gap between its smallest and largest in-service value, reject a stack-up that closes the electrode gap, and map the resulting frequency-gap-product interval onto the susceptibility-chart band. Trigger: ecss, e-st-20-electrical-scope, worst-case-gap-dimension, manufacturing-accuracy, in-service-dimensional-stability, tolerance-stack-up, thermo-elastic-expansion, frequency-gap-product, multipactor-critical-gap."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-dimensional-accuracy-and-stability, worst-case-gap-dimension, manufacturing-accuracy, in-service-dimensional-stability, tolerance-stack-up, thermo-elastic-expansion, frequency-gap-product]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Dimensional Accuracy and Stability (space-systems/ecss/e2001-dimensional-accuracy-and-stability)

Use when the task is the worst-case gap derivation of ECSS-E-ST-20-01C
clause 5.3.3.2 -- turning a drawing nominal into the dimension band a
multipactor-critical gap actually occupies in orbit, once the accuracy
the hardware is built to and the movement it undergoes in service are
both stacked onto that nominal.

## Domain quick reference

- Multipactor susceptibility is governed by the frequency-gap-product,
  the operating frequency times the electrode separation. The
  separation that enters it is not the nominal: it is the extreme the
  gap reaches once every dimensional contribution is applied, so the
  clause asks for a derived worst-case dimension, not a drawing value.
- Contributions fall into two families that are stacked together but
  reasoned about separately. Manufacturing-accuracy covers what the
  build process leaves behind -- machining-tolerance, assembly and
  shimming tolerance, plating-thickness-variation, braze-gap-variation,
  and the uncertainty of the dimensional measurement that verifies the
  part. In-service-dimensional-stability covers what moves afterwards
  -- thermo-elastic-expansion across the qualification temperature
  range, launch-induced-permanent-set, material-creep under preload,
  moisture-release-shrinkage on entering vacuum, radiation-induced
  swelling, and joint-settling over the mission.
- Each contribution is directional: a closing excursion shrinks the
  gap, an opening excursion widens it, and the two are rarely equal
  (thermo-elastic-expansion of dissimilar metals is a clear case).
  Both bounds matter, because a gap sitting above the susceptible band
  is driven critical by its closing excursion and a gap sitting below
  it is driven critical by its opening excursion.
- Two stacking rules are defensible. Arithmetic stacking sums every
  term linearly and is the true worst case, required when the terms
  are few or correlated. Statistical stacking combines independent
  random terms root-sum-square but still sums systematic terms
  linearly, because a bias does not cancel against another bias.
- A stack-up whose closing excursion reaches or passes the nominal
  drives the electrodes into contact. That is a design or a budgeting
  error, not a very small gap, and it is rejected rather than analysed.

## Workflow

1. List every dimensional contribution acting on the gap and assign
   each to the manufacturing-accuracy family or the
   in-service-dimensional-stability family. Reject an unrecognised
   mechanism instead of carrying it as an unfamilied term.
2. Record each contribution as a closing magnitude and an opening
   magnitude, mark it systematic or random, and attach the evidence
   kind behind it -- measured, analysed, or taken from a
   specification. A contribution with no evidence kind is a finding.
3. Choose the stacking rule. Use arithmetic stacking by default; use
   statistical stacking only when the random terms are genuinely
   independent, and keep every systematic term linear inside it.
4. Derive the bounds: minimum equals nominal minus the stacked closing
   excursion, maximum equals nominal plus the stacked opening
   excursion. Reject the gap if the minimum reaches zero.
5. Compare the derived excursion against the stability allowance held
   for the gap in the mechanical budget; flag an exceedance.
6. Multiply both bounds by the operating frequency to get the
   frequency-gap-product interval, then test that interval against the
   susceptibility-chart band. An interval that reaches the band --
   including one that only touches its edge -- leaves the gap
   multipactor-critical; an interval clear of the band on either side
   removes the gap from the multipactor assessment, with the derived
   dimension as the recorded justification.
7. Aggregate across the gap set; the set is accepted only when no gap
   carries an open finding.

## Pitfalls

- Running the multipactor assessment on the nominal dimension and
  treating the tolerance as a second-order effect -- on a narrow gap
  the manufacturing-accuracy band alone can move the
  frequency-gap-product across a chart boundary.
- Stacking manufacturing-accuracy only and omitting the in-service
  terms because the hardware passed its dimensional inspection --
  inspection proves the as-built dimension, not the in-orbit one.
- Applying root-sum-square to every term because it produces a
  friendlier number -- a systematic term such as a thermo-elastic
  excursion at a known temperature is a bias and stays linear.
- Carrying a single symmetric tolerance when the closing and opening
  excursions differ, which understates whichever direction actually
  drives the gap toward the susceptible band.
- Reading a closing excursion that swallows the nominal as a
  vanishingly small gap instead of electrode contact.
- Declaring a gap non-critical from an interval that touches the band
  edge, where the derived dimension carries more uncertainty than the
  distance to the boundary.

## Behavior contract (gate 3)

The mechanism categorization, contribution validation, arithmetic and
statistical stacking, worst-case bound derivation, allowance check,
and frequency-gap-product band logic are exercised by the gate 3
contract test:
scripts/test_e2001_dimensional_accuracy_and_stability.py against
scripts/e2001_dimensional_accuracy_and_stability_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_dimensional_accuracy_and_stability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
