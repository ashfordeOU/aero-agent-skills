---
name: e2008-electron-irradiation-test-process
description: "Verify that a one megaelectronvolt electron irradiation of photovoltaic cell assemblies was run the way the referenced methodology of ECSS-E-ST-20-08C clause 6.4.3.11.2 requires: check the beam energy against the equivalent electron, the delivery rate against the allowed window and the sample-plane flux spread against its allowance, integrate flux over every irradiated segment into a cumulative fluence and reconcile it with the planned point, project the remaining power factor from the logarithmic degradation law, and refuse a run that skipped the before or after electrical characterisation. Use when auditing or planning a solar-cell electron irradiation run. Trigger: ecss, e-st-20-08c, clause-6-4-3-11-2, one-mev-electron-irradiation-run, solar-cell-assembly-fluence-accumulation, electron-beam-plane-flux-uniformity, irradiation-remaining-power-factor, irradiation-step-characterisation."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-electron-irradiation-test-process, one-mev-electron-irradiation-run, solar-cell-assembly-fluence-accumulation, electron-beam-plane-flux-uniformity, irradiation-remaining-power-factor, irradiation-step-characterisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Electron Irradiation Test Process (space-systems/ecss/e2008-electron-irradiation-test-process)

Use when the task is the clause 6.4.3.11.2 test process of ECSS-E-ST-20-08C --
judging whether an exposure of cell assemblies to a one megaelectronvolt
electron fluence was actually carried out the way the referenced methodology
requires: with the beam that methodology names, at a delivery rate the method
allows, over a sample plane uniform enough that one holder is one exposure,
and to the fluence the plan asked for with the electrical measurements that
make the resulting degradation readable.

## Domain quick reference

- Trapped-electron damage is collapsed onto a single equivalent particle.
  One megaelectronvolt is not a convenience: the damage coefficients, the
  published degradation curves and the mission fluence the array was sized
  against are all expressed at that energy, so a beam run at another energy
  produces a number no mission analysis can consume.
- The exposure is a fluence, not a time. Flux integrated over every
  irradiated segment is the quantity the plan specifies; beam time on its
  own says nothing until the flux is known, and a run split over several
  segments only reaches its point when the segments are summed.
- Flux has its own window. Too low and the run never finishes. Too high and
  the damage arrives faster than the assembly can relax to, which suppresses
  the short-term anneal that a real orbit allows, so the measured loss is
  not the loss the mission accumulates over years at the same fluence.
- The sample plane decides whether one run is one test. Flux falls off away
  from the beam axis, so coupons at the edge of a crowded holder can take a
  materially smaller exposure than those at the centre while the record
  shows a single fluence for all of them.
- Degradation is logarithmic in fluence. The remaining power factor drops by
  a roughly fixed increment per decade above a reference fluence, so a
  fluence delivered ten percent short is a small error and a fluence
  delivered a decade short is a different article entirely.
- The measurement before the run is as load-bearing as the one after. The
  remaining factor is a ratio, and without the undamaged reference the
  post-irradiation output is an absolute number with nothing to divide by.

## Workflow

1. Validate the irradiation policy first: nominal energy and tolerance, the
   flux window, the plane uniformity allowance, the holder temperature
   window, the pressure ceiling and the fluence tolerance. A flux window
   whose ceiling is not above its floor is refused rather than used.
2. Check the beam itself -- energy against the equivalent electron, plane
   flux spread against the uniformity allowance -- before any exposure
   arithmetic, because both invalidate every sample on the holder at once.
3. Integrate flux over each irradiated segment, accumulate the schedule, and
   screen each segment's rate against the window; an over-rate segment is a
   finding even when the total fluence is exactly right.
4. Confirm the holder temperature and chamber pressure held for the run.
5. Reconcile the delivered fluence against the planned point, with the
   tolerance absorbing representation error rather than lowering the
   requirement. A delivery landing exactly on the tolerance floor is met.
6. Project the remaining power factor and the degradation fraction from the
   logarithmic law at the delivered fluence. These are reported whatever the
   verdict, because they are what the exposure was carried out for.
7. Close on one verdict -- run conditions violated, exposure fluence
   shortfall, characterisation incomplete, or irradiation run conforms --
   reporting every finding raised, not only the one that set the verdict.

## Pitfalls

- Quoting beam hours as the test level. Two runs of equal length at
  different flux are different exposures, and only the integrated fluence
  distinguishes them.
- Running hot to save beam time. Raising the flux by two decades finishes
  the run in an afternoon and suppresses the short-term anneal, so the
  article looks worse than the same fluence would leave it in orbit.
- Reporting one fluence for a crowded holder. Without the plane flux spread
  the edge coupons carry an unstated exposure error that propagates into
  every remaining-factor figure taken from them.
- Taking only the post-irradiation measurement. The remaining factor needs
  the undamaged reference, and a reference measured on a sibling coupon is
  a different article's number.
- Treating a ten percent fluence shortfall as equivalent to a decade one.
  The degradation law is logarithmic, so the two errors are not on the same
  scale and cannot share a single acceptance band.

## Behavior contract (gate 3)

The policy validation, segment fluence integration and cumulative schedule,
beam energy and plane uniformity checks, flux window and environment
screening, the logarithmic remaining power factor, the planned fluence point
reconciliation, the characterisation inventory and the run verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_electron_irradiation_test_process.py against
scripts/e2008_electron_irradiation_test_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_electron_irradiation_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
