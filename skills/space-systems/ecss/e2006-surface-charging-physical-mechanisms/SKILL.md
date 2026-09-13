---
name: e2006-surface-charging-physical-mechanisms
description: "Use when compute the floating potential of a spacecraft external surface under ECSS-E-ST-20-06C clause 4.1.3: categorize every current contributor as ambient-plasma collection or surface emission, evaluate the potential-dependent electron-collection, ion-collection, secondary-electron-emission, backscattered-electron and photoemission-current terms, solve the current-balance by bisection for the equilibrium potential of a sunlit or eclipsed surface, categorize the resulting surface-charging regime, and derive the differential-charging offset between adjacent dielectric and conductive surfaces against a discharge-onset threshold. Trigger: ecss, e-st-20-06c, surface-charging, plasma-current-balance, secondary-electron-emission, photoemission-current, differential-charging, floating-potential, discharge-onset-threshold, spacecraft-surface-charging."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-surface-charging-physical-mechanisms, e-st-20-06c, surface-charging, plasma-current-balance, secondary-electron-emission, photoemission-current, differential-charging, floating-potential]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Surface-Charging Physical Mechanisms (space-systems/ecss/e2006-surface-charging-physical-mechanisms)

Use when the task is the clause 4.1.3 introduction of ECSS-E-ST-20-06C:
how ambient plasma particles accumulate on an external spacecraft
surface, which current terms compete in the balance that fixes the
equilibrium potential, and how the resulting offsets between adjacent
surfaces become the differential-charging hazard that the rest of the
standard controls.

## Domain quick reference

- Five current terms reach or leave an exposed surface. Two are
  collected from the ambient plasma (thermal electrons, thermal ions);
  three are emitted by the surface itself (secondary electrons,
  backscattered electrons, photoelectrons under solar illumination).
  Each term is categorized into exactly one of those two families
  before it enters the balance. An unrecognized term is rejected, not
  silently dropped.
- The electron flux dominates at equal temperature because electrons
  are far more mobile than ions, so an uncontrolled surface tends to
  charge negative until the accumulated potential retards the very
  population that charges it. That feedback is why every term has to
  be evaluated at the trial potential, not at zero: a negative surface
  retards electrons exponentially with the plasma temperature and
  accelerates ions linearly, and a positive surface does the mirror
  image while also pulling its own low-energy emitted electrons back.
- Secondary-electron-emission follows a peaked yield curve: it rises
  with impact energy, peaks at a material-specific energy of order a
  few hundred electronvolts, then collapses as deeper penetration
  traps the secondaries. In a hot substorm plasma the impacting
  electrons sit far above that peak, the yield is small, and the
  surface is free to charge to kilovolt levels. In a cold dense plasma
  the yield can exceed unity and pins the surface near zero.
- Photoemission is the strongest positive term on a sunlit surface and
  typically holds it within a few volts of the plasma. The same
  spacecraft in eclipse, or a shadowed surface next to a sunlit one,
  loses that term entirely — which is exactly how a large
  differential-charging offset appears across a single vehicle.
- The equilibrium (floating) potential is the potential where the
  signed sum of all five terms vanishes. The differential-charging
  offset is the spread of equilibrium potentials across adjacent
  surfaces; it is compared against a discharge-onset threshold, not
  against the absolute potential, because a uniformly charged vehicle
  is far less hazardous than a modest offset across a dielectric gap.

## Workflow

1. Inventory the current contributors acting on the surface and
   categorize each as collected or emitted. Reject any contributor
   outside the registry before the balance is attempted.
2. Capture the ambient environment: electron and ion current densities
   at zero potential, and the electron and ion temperatures. Capture
   each surface: secondary-yield peak and its energy, backscatter
   fraction, illumination state and photoemission current density.
3. Evaluate each term at a trial potential — exponential retardation
   for the repelled species, linear orbit-limited growth for the
   attracted one, exponential suppression of the emitted populations
   once the surface barrier exceeds their escape energy.
4. Bisect the net current for the potential at which the balance is
   null. A bracket whose lower end carries no net positive current
   (no ion current and no photoemission) has no equilibrium and is an
   input error, not a zero result.
5. Categorize each equilibrium potential into a low, moderate or
   severe band with its polarity, so a kilovolt-level negative surface
   is visible in the report on its own.
6. Take the spread between the most positive and the most negative
   surface and compare it against the discharge-onset threshold. The
   surface set is compliant only when no severe band and no threshold
   exceedance is on the list.

## Pitfalls

- Evaluating the current terms at zero potential and calling the
  largest one the answer — the balance is self-consistent, and a
  surface that starts electron-dominated ends at the potential where
  that dominance has been retarded away.
- Treating the yield curve as monotonic. The peak is the point of the
  curve: reading a hot-plasma impact energy off the rising branch
  overstates the emitted term by orders of magnitude and hides a
  kilovolt-level surface.
- Applying the photoemission term to a shadowed surface. The eclipse
  and sunlit cases differ by that single term and by several kilovolts
  of result; a shared "spacecraft potential" that ignores illumination
  is the classic way a differential-charging hazard is missed.
- Judging compliance on the absolute potential alone. A uniformly
  charged vehicle at a high negative potential can be acceptable while
  a far smaller offset across two adjacent surfaces is not.
- Widening the discharge-onset threshold to absorb a boundary case. An
  offset that sits exactly on the threshold is compliant and the
  comparison absorbs the representation error; an offset above it is a
  finding.

## Behavior contract (gate 3)

The contributor categorization, potential-dependent current terms,
yield curve, current-balance bisection, regime bands and
differential-charging assessment are exercised by the gate 3 contract
test: scripts/test_e2006_surface_charging_physical_mechanisms.py
against scripts/e2006_surface_charging_physical_mechanisms_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_surface_charging_physical_mechanisms.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
