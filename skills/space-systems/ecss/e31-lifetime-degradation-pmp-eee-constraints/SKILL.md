---
name: e31-lifetime-degradation-pmp-eee-constraints
description: "Evaluate the end-of-life case of a thermal control design against ECSS-E-ST-31C clauses 4.4.3 to 4.4.5. Use when a radiator coating, a materials list or a parts list has to be shown good at end of life and not only at beginning of life: ageing the solar absorptance and the infrared emittance of each thermal-optical surface through its ultraviolet, atomic-oxygen and contamination exposure, re-forming the absorptance-to-emittance ratio and the extra absorbed power it costs, screening every vacuum-exposed material against the outgassing mass-loss and condensable limits, and grading each electronic part's predicted hot-case temperature against its rated limit with the required derating margin. Trigger: ecss, e-st-31-thermal-control-scope, thermo-optical-end-of-life-degradation, solar-absorptance-ageing, radiator-coating-degradation, pmp-outgassing-screening, eee-part-temperature-derating, thermal-control-material-restriction."
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
  tags: [ecss, e-st-31-thermal-control-scope, e31-lifetime-degradation-pmp-eee-constraints, thermo-optical-end-of-life-degradation, solar-absorptance-ageing, pmp-outgassing-screening, eee-part-temperature-derating, thermal-control-material-restriction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Lifetime Degradation, PMP and EEE Constraints (space-systems/ecss/e31-lifetime-degradation-pmp-eee-constraints)

Use when the task is the end-of-life side of thermal control design under
ECSS-E-ST-31C clauses 4.4.3 to 4.4.5 — ageing the thermo-optical
properties the design leans on, applying the materials-and-processes
restrictions to the materials that see vacuum, and applying the
electrical-parts restrictions to the temperature each part is allowed to
reach.

## Domain quick reference

- A radiator is sized by the ratio of solar absorptance to infrared
  emittance, not by either property alone. Absorptance rises through
  life under ultraviolet dose, atomic-oxygen erosion and molecular
  contamination; emittance usually moves far less. The ratio therefore
  grows, and the hot case that sizes the radiator is the end-of-life
  one, never the beginning-of-life one measured at delivery.
- Absorptance ageing saturates. A dose-driven exponential approach to an
  asymptotic increase reproduces coating test data far better than a
  linear rate, so a linear extrapolation of an early data point
  overstates late-life damage while understating early-life damage.
- The cost of that ageing is a power: the extra absorbed solar power on
  a radiator is its area times the incident solar flux times the growth
  in absorptance. That figure is what the radiator margin at delivery
  has to be able to absorb.
- Materials that see vacuum carry outgassing restrictions expressed as a
  total mass loss and a collected volatile condensable fraction. A
  material screened out on either figure is not usable by a
  substitution argument; it needs a different material or a bake-out
  with recorded evidence.
- A material that never sees vacuum is outside the screening, but the
  reason has to be recorded. An undeclared exemption is indistinguishable
  from an unscreened material at review.
- An electronic part carries a rated temperature limit that the design
  is not allowed to reach: the usable limit is the rated one reduced by
  the required derating margin, and the prediction graded against it is
  the end-of-life hot one with its uncertainty already inside.

## Workflow

1. Validate each thermal-optical surface: absorptance and emittance at
   beginning of life in the open unit interval, a non-negative
   saturating absorptance increment, a positive dose constant, and an
   exposure dose that is non-negative.
2. Age each surface: grow absorptance towards its asymptote with the
   accumulated equivalent sun hours, move emittance with the
   atomic-oxygen fluence, and refuse a combination whose asymptote
   would carry either property outside the physical unit interval.
3. Re-form the absorptance-to-emittance ratio at end of life, report its
   growth over beginning of life, and convert the absorptance growth
   into the extra absorbed power on the declared radiator area.
4. Screen every vacuum-exposed material against the mass-loss and
   condensable limits; group each as compliant, screened out, or exempt,
   and raise a finding on an exemption with no recorded justification.
5. Grade each electronic part: form the usable limit as the rated limit
   less the derating margin and compare the end-of-life hot prediction
   against it, absorbing representation error at the boundary with a
   named tolerance rather than by shaving the margin.
6. Report the aged surfaces, the material dispositions, the part
   dispositions and every finding, with the overall verdict compliant
   only when no category raised one.

## Pitfalls

- Sizing the radiator on the delivered coating. The measured
  beginning-of-life absorptance is the best-case number of the mission;
  the hot case belongs to the aged surface, and a design closed on the
  delivered value has no end-of-life case at all.
- Extrapolating absorptance ageing linearly from an early dose point.
  The damage saturates, so a straight line through an early measurement
  overpredicts at end of life and underpredicts at the first hot case.
- Degrading absorptance while holding emittance fixed by habit.
  Atomic-oxygen erosion moves emittance too, and on a surface where it
  falls the ratio grows faster than the absorptance change alone.
- Passing a material on one outgassing figure. Mass loss and condensable
  fraction are separate limits and a material has to clear both; a
  condensable failure is the one that lands on the cold optics.
- Leaving a non-vacuum exemption undeclared. The screening record cannot
  tell an exempt material from a forgotten one, so the exemption is a
  finding until its reason is written down.
- Grading a part against its rated limit. The rated value is not the
  design limit; the derating margin is subtracted first, and widening
  the margin to rescue an exact-equality case swaps an engineering limit
  for a rounding question.

## Behavior contract (gate 3)

Surface validation, saturating absorptance ageing, emittance movement,
ratio and absorbed-power growth, outgassing screening with exemption
handling, and part derating with boundary tolerance are exercised by the
gate 3 contract test:
scripts/test_e31_lifetime_degradation_pmp_eee_constraints.py against
scripts/e31_lifetime_degradation_pmp_eee_constraints_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_lifetime_degradation_pmp_eee_constraints.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
