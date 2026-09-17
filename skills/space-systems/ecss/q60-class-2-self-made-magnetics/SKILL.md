---
name: q60-class-2-self-made-magnetics
description: "Validate an in-house wound magnetic part built for class 2 equipment under ECSS-Q-ST-60C clause 5.6.8: refuse a part with no wire specification, no core specification and no qualified winding procedure behind it, resolve the peak flux density from the volt-second product and its utilisation of core saturation, take the window fill factor and the winding current density, carry the copper and core losses across the thermal path to a hot spot margin below the derated insulation rating, and derive the screening sequence the construction and the flight lot call for. Use when a transformer or inductor is wound in house rather than procured to a component specification. Trigger: ecss, q-st-60c-clause-5-6-8, class-2-magnetics-volt-second-flux-density, class-2-magnetics-window-fill-factor, class-2-magnetics-hot-spot-margin, class-2-magnetics-screening-sequence."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-2-self-made-magnetics, class-2-magnetics-volt-second-flux-density, class-2-magnetics-window-fill-factor, class-2-magnetics-hot-spot-margin, class-2-magnetics-screening-sequence, class-2-magnetics-lot-sampling-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 2 — Self-Made Wound Magnetic Parts (space-systems/ecss/q60-class-2-self-made-magnetics)

Use when the task is clause 5.6.8 of ECSS-Q-ST-60C: a magnetic part wound in
house for class 2 equipment rather than bought against a component
specification. This leaf checks the design against recognised practice and
derives the screening the part owes before it may be fitted.

## Domain quick reference

- A self-made part has no procurement history to lean on, so the evidence is
  built rather than inherited. Without a stated wire specification, a stated
  core specification and a qualified winding procedure there is nothing to
  assess: the part is not admissible, and class 2 relaxes only who may hold the
  needle, not whether the procedure exists.
- The flux the core sees is set by the volt-second product, not by the current.
  Applied voltage times the time it is applied, divided by the turns and the
  effective core section, is the peak flux; a design that looks conservative on
  current can still be sitting at the knee of the loop.
- Saturation is a datasheet maximum, not a working point. The recognised
  practice figure is a fraction of it, and a part exactly on that fraction is
  compliant because the limit belongs to the acceptable side.
- The window is a budget with three claimants. Turns, conductor section and
  insulation all draw on the same bobbin, and a fill factor computed on bare
  copper is already optimistic about what will physically go on.
- The hot spot is computed, not measured. Copper loss follows the winding
  resistance at temperature, core loss follows a power law steep in flux, and
  the sum crosses the thermal path to a rise that the ambient is added to. The
  insulation rating less the class derating is what that hot spot is compared
  with.
- Screening is what a self-made part has instead of lot acceptance. The
  construction decides which extra step attaches, and the flight lot decides
  whether a destructive sample can be drawn at all — a lot of two cannot spare
  one, so the whole lot is screened without destroying any of it.

## Workflow

1. Validate the case and name the foundations the part does not stand on. If
   any is missing the part is not admissible and the design numbers are not
   worth computing.
2. Resolve the peak flux density from the volt-second product, the turns and
   the core section, and take its utilisation of the core saturation figure.
3. Take the window fill factor from the turns and the conductor section, and
   the current density the winding runs at.
4. Resolve the winding resistance at its operating temperature, take the copper
   loss, take the core loss from the material power law at the working flux and
   frequency, and add them.
5. Carry the total loss across the thermal resistance to a rise, add the
   ambient, and take the margin against the insulation rating less the class 2
   derating.
6. Derive the screening sequence from the construction and the flight lot size,
   subtract what has been done, and return the disposition in precedence order:
   not admissible, then design nonconforming, then screening outstanding, then
   practice satisfied.

## Pitfalls

- Sizing the core from the current alone. The flux comes from the volt-second
  product, and a winding that is comfortable on current density can still drive
  the core into saturation on the first long pulse.
- Designing to the datasheet saturation figure. It is the boundary the material
  stops being a core at, not the point a design should sit at, and the fraction
  held back is what absorbs temperature, tolerance and an off-nominal duty.
- Computing the winding resistance cold. Copper gains roughly four parts in a
  thousand per degree, so a winding sized on a twenty-degree resistance
  dissipates materially more once it is hot, and the rise feeds the resistance
  that produced it.
- Taking the core loss as a small correction. The power law is steep in flux,
  so a modest increase in the working flux can multiply the core loss several
  times over and turn a comfortable thermal design into a marginal one.
- Reading a hot spot against the bare insulation class rating. The class 2
  derating sits below it, and the margin between them is the reason the part
  survives the mission rather than the acceptance test.
- Planning a destructive lot sample the lot cannot spare. A flight lot below
  the sampling floor has no part to give up, and the sequence has to change
  rather than the lot.
- Comparing a computed utilisation, fill or margin with its limit by bare
  arithmetic. The core law runs through a fractional power that is not
  correctly rounded, so a case sitting exactly on a limit can land a few units
  in the last place the wrong side of it.

## Behavior contract (gate 3)

The policy merge, case validation, admissibility gaps, volt-second peak flux
and its utilisation, window fill factor, current density, winding resistance at
temperature, copper and core loss, temperature rise, hot spot and its margin
against the derated insulation rating, the screening sequence with its lot
sampling floor and the four-way disposition in precedence order are exercised
by the gate 3 contract test:
scripts/test_q60_class_2_self_made_magnetics.py against
scripts/q60_class_2_self_made_magnetics_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_2_self_made_magnetics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
