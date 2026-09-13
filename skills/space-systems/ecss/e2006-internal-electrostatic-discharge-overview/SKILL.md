---
name: e2006-internal-electrostatic-discharge-overview
description: "Use when assess internal parts and materials exposed to deep-dielectric-charging for internal-electrostatic-discharge, under ECSS-E-ST-20-06C clause 9.1: attenuate the energetic-electron-flux through the local shield thickness, screen out items below the internal-charging screening threshold, categorize every remaining item as a bulk-dielectric, an ungrounded-conductor or a grounded-conductor, then check its steady-state buried-charge-field against the dielectric-field limit, its stored discharge-energy against the damage limit, or its bleed time-constant against the exposure, and confirm the recorded validation provision actually closes that category. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c-clause-9-1, internal-electrostatic-discharge, deep-dielectric-charging, energetic-electron-flux, buried-charge-field, floating-conductor-bleed-path, radiation-induced-conductivity, shield-thickness-attenuation."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-internal-electrostatic-discharge-overview, internal-electrostatic-discharge, deep-dielectric-charging, energetic-electron-flux, buried-charge-field, floating-conductor-bleed-path]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Internal-Electrostatic-Discharge Overview (space-systems/ecss/e2006-internal-electrostatic-discharge-overview)

Use when the task is the ECSS-E-ST-20-06C clause 9.1 entry point for
internal parts and materials subject to deep-dielectric-charging: the general
provisions that keep buried charge from relaxing as an internal discharge,
and the validation provisions that close each item out.

## Domain quick reference

- Clause 9.1 is about what gets *inside*. Energetic electrons in the outer
  radiation belts pass through the shell, stop in insulators and in metal
  that has no path to structure, and leave a buried charge millimetres from
  the electronics. Nothing about outer-surface control helps here: the
  discharge, when it comes, starts on the wrong side of the shielding.
- The first discriminator is the penetrating flux after local shielding, not
  the free-field flux. It falls off roughly exponentially with the aluminium
  in the way, and below a screening level no item can accumulate enough
  buried charge over a mission to matter, whatever its resistivity. Screening
  an item out is a legitimate closure and it is the cheapest one available.
- Above screening, the item's category decides the physics. A bulk-dielectric
  reaches a steady buried-charge-field where deposition balances conduction
  away, so the field is the deposited current density times the resistivity;
  a high-resistivity insulator under flux is the classic offender, and that
  is why a resistivity ceiling, not a thickness, is the usual control.
- Resistivity under flux is not the dark resistivity. Radiation-induced
  conductivity lowers it while the item is being irradiated, and crediting
  only the dark value overstates the field on every item — the analysis
  becomes so conservative that real findings get lost among false ones.
- An ungrounded-conductor has no steady state at all. It integrates charge
  for as long as it is exposed, and the hazard is the energy its capacitance
  releases when it finally goes, not the potential itself. A grounded-conductor
  is safe only if its bleed path drains charge fast compared with the
  exposure it accumulates over — a bond that exists but is slow is a floating
  part with paperwork.
- The validation provision has to suit the category. Continuity inspection
  says nothing about a dielectric; analysis alone does not close an
  ungrounded conductor, whose behaviour depends on a capacitance nobody
  measured.

## Workflow

1. Establish the penetrating-electron environment for the worst-case orbit
   and mission phase: the incident flux and the exposure duration it is
   sustained over. Reject a non-physical flux or duration up front.
2. Inventory every internal part and material — cable insulation, board
   laminate, potting, connector inserts, spare pads, shield cans, ungrounded
   brackets — with its local shield thickness and the parameters its
   category needs: resistivity for a dielectric, area and capacitance for a
   conductor, bond resistance for a grounded one.
3. Attenuate the incident flux through the local shield thickness and test
   the result against the screening level. Items below it close out there;
   record that, do not carry them further.
4. For a bulk-dielectric, reduce the dark resistivity by the
   radiation-induced conductivity at that flux, compute the steady
   buried-charge-field, and compare it against the internal-field limit.
5. For a conductor, compute the accumulated potential over the applicable
   duration and the energy its capacitance would release, and compare that
   against the discharge-energy limit. For a grounded one, first check the
   bleed time-constant against the exposure — an inadequate bleed path means
   the item charges for the full exposure, not for one time constant.
6. Check the recorded validation provision against the category and confirm
   it carries a report reference. Roll the items up: the clause is met only
   when every item is either screened out or closed with a suitable
   provision and no open finding.

## Pitfalls

- Screening on free-field flux instead of the flux behind the local
  shielding, or the reverse — crediting a box wall that the part does not
  actually sit behind. The attenuation is exponential, so a millimetre of
  bookkeeping error moves the answer by a large factor.
- Using dark resistivity for an item that is being irradiated. The
  radiation-induced conductivity is precisely what keeps flight hardware
  under the field limit, and dropping it turns the analysis into a list of
  findings nobody can act on.
- Treating an ungrounded conductor as a small dielectric problem. It has no
  steady state; it integrates, and the acceptance quantity is released
  energy, governed by a capacitance that has to be estimated rather than
  assumed away.
- Accepting a bond because it exists. A high-resistance path can have a time
  constant longer than the exposure, in which case the part charges as if it
  were floating and the continuity record is misleading.
- Letting a floating-point boundary decide a compliant item. A field built
  from a unit conversion and a division, or an energy from a squared
  potential, can land a few units in the last place above a limit it
  mathematically equals; the comparison absorbs that representation error
  rather than the limit being widened.
- Closing an item with whatever provision was cheapest. The method has to
  match the category, and a provision with no report reference is not a
  provision.

## Behavior contract (gate 3)

The environment validation, shield attenuation, screening, item
categorization, buried-charge-field, floating-potential, stored-energy,
bleed-time-constant and validation-provision logic is exercised by the gate 3
contract test:
scripts/test_e2006_internal_electrostatic_discharge_overview.py against
scripts/e2006_internal_electrostatic_discharge_overview_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_internal_electrostatic_discharge_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
