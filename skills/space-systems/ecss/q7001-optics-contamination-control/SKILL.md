---
name: q7001-optics-contamination-control
description: "Compute the end-of-life molecular deposition budget of a sensitive optical surface and decide whether it holds. Use when an aperture, mirror, lens or detector window carries a molecular cleanliness requirement and the contamination-control plan has to apportion that budget across outgassing, plume backflow and handling sources, predict what each one deposits through its view factor and a temperature-dependent sticking coefficient, convert the accumulated areal mass into a condensed film thickness and a throughput loss, and name every source overrunning its own allocation. Trigger: ecss, q-st-70-01c, optics-molecular-deposition-budget, optical-surface-cleanliness-allocation, condensed-film-transmittance-loss, receiver-sticking-coefficient, outgassing-source-apportionment, end-of-life-optical-throughput, sensitive-optics-contamination-control."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-optics-contamination-control, optics-molecular-deposition, optical-surface-cleanliness, condensed-film-transmittance, outgassing-source-apportionment, receiver-sticking-coefficient]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Optics Contamination Control (space-systems/ecss/q7001-optics-contamination-control)

Use when the task is the sensitive-hardware branch of ECSS-Q-ST-70-01C that
applies to optics: turning a single end-of-life molecular cleanliness figure
for an aperture, mirror, lens or detector window into a per-source deposition
allocation, and showing that the predicted condensed film still leaves the
instrument inside its allowable throughput loss.

## Domain quick reference

- Optics are the most stringent receiver on the vehicle because the quantity
  that matters is not a visible deposit but a monolayer-scale film. A few
  tens of nanograms per square centimetre is already a measurable
  transmittance change in the ultraviolet, which is why the budget is written
  in ng/cm2 and not in a visual cleanliness level.
- The budget is an end-of-life number for one surface. It is only auditable
  once it has been apportioned: every contributing source (materials
  outgassing, thruster plume backflow, vent plumes, handling and bagging
  residue) owns a share, and a source is verified against its share, not
  against the whole.
- What a source emits is not what the optic receives. The geometric view
  factor sets the fraction that arrives; the sticking coefficient sets the
  fraction that stays. Sticking is a strong function of receiver temperature,
  so a cryogenic detector window and a warm baffle facing the same source do
  not accumulate the same film.
- Areal mass becomes an optical effect through two conversions: film density
  turns ng/cm2 into a thickness, and an absorption coefficient turns that
  thickness into a transmittance. An optical train with several contaminated
  surfaces multiplies the single-surface transmittance once per surface.
- Deposition is recoverable in principle. A warm-up bake drives re-emission
  and buys margin, but only where the optic tolerates the temperature, so the
  budget is still sized on the un-baked accumulation.

## Workflow

1. Validate the receiver: area, end-of-life budget in ng/cm2, allowable
   fractional throughput loss, film density, absorption coefficient and the
   number of contaminated surfaces in the optical path.
2. Apportion the end-of-life budget across the declared sources in proportion
   to their weight. Reject duplicate source names: an allocation nobody can
   trace back to one source is not an allocation.
3. For each source, resolve the retained fraction. Use its declared sticking
   coefficient where one exists; otherwise read the receiver temperature off
   the tabulated sticking curve and refuse to extrapolate beyond the curve.
4. Compute each source's areal deposition from its outgassing rate, view
   factor, exposure duration and retained fraction, divided by receiver area.
5. Accumulate the sources, convert the total into a condensed film thickness
   and then into a fractional throughput loss across the whole path.
6. Compare the total with the budget and the loss with the allowable loss,
   absorbing representation error at the boundary with a named tolerance
   rather than by relaxing either limit.
7. Report the accumulated deposition, film thickness, throughput loss and
   every source whose prediction overruns its own allocation.

## Pitfalls

- Verifying only the total. A total inside budget can still hide one source
  consuming three quarters of it, which leaves no margin for the growth of
  any other source and is a finding in its own right.
- Treating emitted mass as deposited mass. Skipping the view factor and the
  sticking coefficient overstates deposition by orders of magnitude on a
  warm surface and understates nothing anywhere, so it is not conservative
  in a useful sense; it just makes the budget unusable.
- Using one sticking coefficient for every receiver. The same plume gives a
  cold detector window and a warm baffle wildly different films, and a single
  vehicle-level value silently mis-sizes both.
- Converting ng/cm2 to thickness at unit density by habit. Condensed
  outgassing films are not water; the density used has to be the one the
  absorption coefficient was measured with, or the two conversions disagree.
- Charging the accumulation to a post-bake condition. A recovery bake is an
  operational mitigation with its own temperature limits, not an input to the
  budget the hardware is built and verified against.

## Behavior contract (gate 3)

The receiver and source validation, budget apportionment, sticking-curve
interpolation, per-source deposition, film-thickness and throughput-loss
conversion, and the budget and loss comparisons are exercised by the gate 3
contract test:
scripts/test_q7001_optics_contamination_control.py against
scripts/q7001_optics_contamination_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_optics_contamination_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
