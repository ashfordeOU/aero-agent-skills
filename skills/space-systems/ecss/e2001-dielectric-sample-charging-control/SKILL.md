---
name: e2001-dielectric-sample-charging-control
description: "Use when determine whether a dielectric coupon has been discharged enough before a secondary-emission-yield measurement under ECSS-E-ST-20-01C clause 9.4.2.4: validate the pre-measurement surface-voltage map, reduce it to a magnitude and a spread figure, compare both against the pre-measurement acceptance limits, confirm the neutralization technique is one of the admissible ones (electron-flood, ultraviolet-photoemission, low-energy-plasma, grounded-mesh-contact), size the neutralization dwell from the dielectric-relaxation-time of the coupon stack, and re-check the post-neutralization map before the probe beam is applied. Trigger: ecss, e-st-20-electrical-scope, dielectric-sample-neutralization, surface-voltage-spread, dielectric-relaxation-time, electron-flood-neutralization, secondary-emission-yield-preconditioning, pre-measurement-discharge."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-dielectric-sample-charging-control, dielectric-sample-neutralization, surface-voltage-spread, dielectric-relaxation-time, electron-flood-neutralization, pre-measurement-discharge]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Dielectric Sample Discharge Control (space-systems/ecss/e2001-dielectric-sample-charging-control)

Use when the task is the pre-measurement discharge control of
ECSS-E-ST-20-01C clause 9.4.2.4 -- bringing a dielectric coupon's
surface potential down in both magnitude and point-to-point spread
before a secondary-emission-yield measurement starts, so the probe
beam lands at the energy the instrument commanded rather than at that
energy shifted by an unknown retained potential.

## Domain quick reference

- A dielectric coupon arrives at the chamber holding charge from
  handling, from pump-down, or from a previous irradiation. That
  retained potential adds to or subtracts from the commanded landing
  energy, so a yield curve taken on a charged coupon is a yield curve
  taken at the wrong energies -- and the error is largest exactly where
  the multipaction-relevant first crossover sits, at low energy.
- Two figures describe the state of the surface, and both are
  controlled. Magnitude is the largest absolute potential anywhere on
  the map; spread is the difference between the highest and lowest
  reading. A map that is uniformly at a modest potential is a shifted
  measurement that could in principle be corrected; a map with a large
  spread is a coupon whose landing energy varies across the beam-swept
  area and cannot be corrected at all.
- Neutralization techniques admissible before a yield measurement are
  the ones that add mobile charge or a conduction path without
  altering the emitting surface: an electron-flood at an energy below
  the first crossover, ultraviolet-photoemission, exposure to a
  low-energy-plasma, and temporary grounded-mesh-contact. A technique
  that heats, abrades, solvent-wipes or ion-sputters the coupon is not
  a discharge step -- it changes the very surface treatment the
  measurement is supposed to characterize.
- Dwell time is not guessed. The bulk decay of a dielectric follows
  its relaxation time, the product of vacuum permittivity, relative
  permittivity and volume resistivity. A high-resistivity polymer has
  a relaxation time of hours, so passive grounding alone will not
  reach the acceptance limit inside a test slot and an active
  technique is required.
- The check is performed twice: once on the as-received map to decide
  whether neutralization is needed at all, and once on the
  post-neutralization map to confirm it worked. A coupon whose spread
  refuses to close after the planned dwell is a coupon with an
  embedded charge layer or a conductive-path defect, and it is
  rejected rather than measured.

## Workflow

1. Validate the surface-voltage map: a non-empty sequence of finite
   numeric readings taken at named points. Reject an empty map, a
   non-numeric reading, or a post-map whose point count differs from
   the pre-map, before any figure is derived.
2. Reduce the map to its two controlled figures: magnitude (largest
   absolute reading) and spread (highest minus lowest reading).
3. Compare both figures against the acceptance limits. A figure
   exactly at its limit is inside it; absorb representation error at
   the boundary with a relative tolerance rather than widening the
   limit, because both figures are differences of measured values.
4. Categorize the as-received state: ready when both figures are
   inside their limits, needs-neutralization when either exceeds,
   and reject-coupon when the spread exceeds a hard multiple of its
   limit, which indicates an embedded charge layer no surface
   technique will clear.
5. When neutralization is needed, confirm the proposed technique is
   admissible; reject an unrecognized technique and reject one that
   modifies the emitting surface.
6. Size the dwell: compute the coupon's dielectric-relaxation-time
   from relative permittivity and volume resistivity, then compute the
   dwell that decays the present magnitude to the target, scaled by
   the technique's effectiveness factor. Flag a dwell that does not
   fit the available chamber slot.
7. Re-check the post-neutralization map against the same limits,
   confirm the magnitude actually fell, and release the coupon for
   measurement only when both figures are inside their limits.

## Pitfalls

- Controlling magnitude and ignoring spread -- a coupon can sit at a
  small average potential while individual points differ by hundreds
  of volts, which smears the low-energy end of the yield curve without
  ever breaching a magnitude limit.
- Grounding the rear face and declaring the front discharged -- the
  front surface of a high-resistivity coupon decays on its relaxation
  time, not on the time constant of the ground strap, so a passive
  wait that is short compared with that relaxation time changes
  nothing.
- Using a solvent wipe, a bake or an ion-beam clean as the discharge
  step -- these do reduce surface potential, and they also change the
  surface treatment the coupon exists to represent, so the measured
  yield stops describing the real hardware.
- Flooding with electrons above the first crossover -- an electron
  flood only neutralizes while it deposits more charge than it emits;
  above the crossover the flood charges the coupon positive instead of
  discharging it.
- Reading a post-neutralization map that still exceeds the limits as
  "close enough after a long dwell" -- a spread that refuses to close
  is a coupon finding, and measuring it anyway silently corrupts the
  yield data the multipactor margin is built on.
- Treating an exactly-at-limit reading as a failure and widening the
  limit to clear it -- the limit is the engineering acceptance
  criterion; only the representation error at the boundary is
  absorbed.

## Behavior contract (gate 3)

The map validation, magnitude and spread reduction, acceptance
categorization, technique admissibility, relaxation-time and dwell
sizing, and post-neutralization re-check logic is exercised by the
gate 3 contract test:
scripts/test_e2001_dielectric_sample_charging_control.py against
scripts/e2001_dielectric_sample_charging_control_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_dielectric_sample_charging_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
