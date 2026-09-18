---
name: q6012-sensitivity-and-stability-review-item
description: "Review the sensitivity and stability item of an ECSS-Q-ST-60-12C clause 7.3.5 die-form MMIC design review: turn each declared variation source into a normalised sensitivity coefficient, combine the tolerance-weighted contributions root-sum-square against the allowed spread, then form Rollett's factor and the scattering determinant at every swept frequency and grade the sweep span itself. Use when a MMIC design offers evidence that it tolerates process, temperature and supply variation and will not oscillate, and that evidence has to be graded rather than accepted. Trigger: ecss, q-st-60-12c-clause-7-3-5, mmic-sensitivity-review, mmic-unconditional-stability, rollett-stability-factor, scattering-determinant-magnitude, root-sum-square-spread, out-of-band-oscillation-sweep-span."
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
  tags: [ecss, q-st-60-12-die-mmic-scope, q6012-sensitivity-and-stability-review-item, mmic-sensitivity-review, mmic-unconditional-stability, rollett-stability-factor, scattering-determinant-magnitude, root-sum-square-spread, out-of-band-oscillation-sweep-span]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Die-Form MMIC -- Sensitivity And Stability Review Item (space-systems/ecss/q6012-sensitivity-and-stability-review-item)

Use when the task is the sensitivity and stability item of the design
review of ECSS-Q-ST-60-12C clause 7.3.5 -- grading the evidence that the
circuit keeps its performance while process, temperature, supply and
bias move, and the evidence that it does not oscillate anywhere.

## Domain quick reference

- Sensitivity is only comparable once it is normalised. The coefficient
  is S = (dY/Y) / (dx/x), a fractional output move per fractional input
  move, which puts a process shift, a temperature swing and a supply
  tolerance on one scale even though their raw units share nothing.
- The sources are independent, so their tolerance-weighted contributions
  combine root-sum-square, not arithmetically. Adding them
  arithmetically overstates the spread and drives design margin into a
  case that cannot occur; using the worst single source understates it.
- The dominant contributor is the reviewable output. Two designs with
  the same combined spread need different fixes depending on whether
  process or temperature dominates it, and only the dominant term repays
  a design change.
- Stability at a frequency is a two-part test. With D = s11*s22 -
  s12*s21, Rollett's factor is K = (1 - |s11|^2 - |s22|^2 + |D|^2) /
  (2*|s12*s21|), and unconditional stability needs K above one AND |D|
  below one. K alone is not sufficient, which is why the single
  parameter factor mu is carried alongside as a cross-check.
- Unwanted oscillation is usually out of band. Device gain is still high
  well below the operating band while the matching networks no longer
  control the terminations, so a sweep that stops at the band edges has
  not looked where oscillation lives. The swept span is graded as
  evidence in its own right, independently of what the swept points say.
- A variation source whose perturbation moved the output by nothing is
  almost always a perturbation that never reached the netlist, not a
  genuinely insensitive design.

## Workflow

1. For each performance parameter, validate the nominal value and the
   allowed relative spread, then form a normalised sensitivity
   coefficient per declared variation source.
2. Weight each coefficient by that source's own tolerance, combine the
   contributions root-sum-square, and compare with the allowance,
   treating an exact landing on it as within it through a named
   tolerance rather than by widening the allowance.
3. Name the dominant contributor, and flag both a source that moved the
   output by nothing and a required variation source the evidence never
   exercised.
4. For the stability sweep, validate that the frequencies strictly
   increase, then at each point form the scattering determinant,
   Rollett's factor and mu.
5. Grade each point on K above the required value and determinant
   magnitude below one, counting an exact landing on either boundary as
   not cleared, since unconditional stability is a strict condition.
6. Grade the sweep span: it reaches below the band low edge and above
   the band high edge by the declared factor, and contains at least one
   in-band point. A short sweep is a finding even when every swept point
   is stable.
7. Collect the sensitivity and stability findings into one item verdict,
   reporting the minimum K, the unstable frequencies and the
   worst-spread parameter.

## Pitfalls

- Adding sensitivity contributions arithmetically. Independent sources
  combine root-sum-square; the arithmetic sum is a case that does not
  occur and turns a compliant design into a redesign.
- Comparing raw sensitivities across sources. An unnormalised
  millivolt-per-degree figure cannot be ranked against a
  percent-per-percent one, so the dominant contributor comes out wrong.
- Accepting K above one as unconditional stability. The determinant
  magnitude has to be below one at the same frequency; K on its own
  admits a design that oscillates into certain terminations.
- Sweeping only the operating band. Low-frequency and out-of-band
  oscillation is the usual failure mode, and a band-limited sweep
  reports clean because it never looked there.
- Reading a flat perturbation response as an insensitive design. A
  source that produced no output move is evidence the perturbation was
  never applied, and it is reported as such.
- Relaxing K, the determinant bound or the spread allowance so a design
  that lands exactly on one of them passes. An exact landing is a
  representation question, absorbed inside the comparison; the limits
  stay where the review put them.

## Behavior contract (gate 3)

The normalised sensitivity coefficients, tolerance weighting,
root-sum-square combination, dominant-source selection, the scattering
determinant, Rollett's factor, mu, the per-frequency stability grading,
the sweep-span coverage check and the assembled item verdict are
exercised by the gate 3 contract test:
scripts/test_q6012_sensitivity_and_stability_review_item.py against
scripts/q6012_sensitivity_and_stability_review_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_sensitivity_and_stability_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
