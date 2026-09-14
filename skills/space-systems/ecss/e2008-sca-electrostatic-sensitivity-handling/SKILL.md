---
name: e2008-sca-electrostatic-sensitivity-handling
description: "Assess whether the handling and storage applied to an electrostatic-discharge-sensitive photovoltaic assembly keep it under the voltage it survives, per ECSS-E-ST-20-08C clause 6.8.2: categorize the assembly from its withstand voltage and discharge model, grade every obliged protected-area control inside its own band rather than merely present, check the packaging shields rather than only dissipates, measure the storage envelope and the shelf life already spent, and turn residual charge into the voltage it leaves. Use when an ESD-sensitive assembly is handled, packed or stored and the control set needs grading. Trigger: ecss, e-st-20-08c, esd-sensitive-assembly-handling, photovoltaic-assembly-protected-area-controls, esd-ground-path-resistance-band, esd-shielding-packaging-category, esd-sensitive-storage-envelope, esd-withstand-voltage-categorization."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-sca-electrostatic-sensitivity-handling, esd-sensitive-assembly-handling, photovoltaic-assembly-protected-area-controls, esd-ground-path-resistance-band, esd-shielding-packaging-category, esd-sensitive-storage-envelope, esd-withstand-voltage-categorization]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- ESD-Sensitive Handling and Storage (space-systems/ecss/e2008-sca-electrostatic-sensitivity-handling)

Use when the task is the electrostatic-sensitivity rule of ECSS-E-ST-20-08C
clause 6.8.2 -- deciding whether the way an assembly was handled, packed and
stored actually kept the voltage it could see below the voltage it is known to
survive, and naming the controls that carry that statement.

## Domain quick reference

- Sensitivity is derived, not declared. A withstand voltage measured against a
  discharge model puts the assembly in a band, and the band is what decides
  how many controls the handling owes. The same assembly sits in different
  bands under the human-body, machine and charged-device models, so the model
  travels with the number or the number means nothing.
- Every control has two ends. A ground path that is too resistive never bleeds
  the charge away; a ground path that is too conductive turns the operator
  into a discharge route and is a personnel hazard on top of a component one.
  A wrist strap reading a few ohms is a worse record than one reading nothing,
  because it looks like a pass.
- Present is not the same as in band. A protected area with every control
  fitted and two of them out of band protects nothing in particular, so
  coverage is counted on in-band controls and a fitted-but-drifted control is
  reported as a finding rather than as a tick.
- Packaging families are not grades of the same thing. Low-charging and
  dissipative packaging stop the bag itself becoming a source; only shielding
  packaging puts a conductive boundary between the assembly and an external
  field. The most sensitive bands need the boundary, and swapping a shielding
  bag for a pink dissipative one is a change of protection class, not of
  stationery.
- Humidity is a control, not weather. Below roughly thirty percent relative
  humidity, triboelectric charging rises steeply and the same handling motion
  generates far more charge, so a dry room quietly removes a control nobody
  recorded removing.
- Residual charge on a floating assembly shows up as a voltage through the
  assembly's own capacitance, V = Q / C. A small assembly has a small
  capacitance, so the same nanocoulomb left on it is a much higher voltage,
  and comparing charge with charge instead of voltage with voltage hides that.
- Storage is handling spread over time. The envelope has to hold for the whole
  stored period and the declared storage life has to still have time left in
  it; an assembly whose life is spent is not non-conforming, it is unqualified
  until it is re-checked.

## Workflow

1. Categorize the assembly: take the withstand voltage together with the
   discharge model it was measured against and derive the sensitivity band and
   its rank. A withstand voltage with no model attached is an input error.
2. Read off the controls that rank obliges. The base set covers the operator
   ground path and the worksurface; more sensitive ranks add floor and
   footwear, tooling, ionization and a humidity floor.
3. Grade each obliged control against its own band, both ends. Name the ones
   with no reading separately from the ones that read out of band, and treat a
   reading the rank does not oblige as out of scope rather than as credit.
4. Check the packaging family against the minimum the rank allows, and say
   which family was needed when it falls short.
5. Measure the storage temperature and humidity against the declared envelope
   and work out the share of storage life already spent.
6. Where a residual charge and an assembly capacitance are both recorded,
   convert them into the voltage left across the assembly and compare it with
   the withstand voltage; report the margin, not just the verdict.
7. Roll up: a missing control, an out-of-band control, inadequate packaging or
   a residual voltage over the withstand voltage blocks the handling; an
   envelope excursion or a spent storage life restricts it; anything else is
   compliant, with the controls that carry it listed.

## Pitfalls

- Reading the sensitivity band off the assembly type instead of a measurement.
  Two assemblies of the same build can differ by a decade in withstand voltage
  once the bypass diode and the coverglass ground are taken into account.
- Comparing a withstand voltage quoted under one discharge model with a band
  drawn for another. The models charge and discharge the part differently and
  their numbers are not interchangeable.
- Accepting a wrist strap on continuity alone. Continuity passes a dead short,
  which is exactly the failure that makes the strap dangerous.
- Counting a fitted control as a control. A drifted worksurface is fitted,
  labelled, in the audit record and doing nothing.
- Substituting dissipative packaging for shielding packaging. It solves the
  bag's own charging and leaves the external field untouched.
- Ignoring the room humidity because the bench passed. Charge generation is a
  property of the room, and a dry room raises what the controls have to bleed.
- Comparing residual charge with a withstand voltage. Charge only becomes a
  voltage once the assembly capacitance is applied, and the small assembly is
  the one that gets hurt.
- Treating a spent storage life as a reject. The assembly is not condemned; it
  is simply no longer covered by the check that let it be stored.
- Comparing a reading with a band edge by bare arithmetic. Band edges are
  derived limits and instrument readings carry representation error, so a
  value physically on an edge can evaluate a few units in the last place
  outside it; the comparison absorbs that while the limit stays untouched.

## Behavior contract (gate 3)

The sensitivity categorization, obliged-control derivation, two-ended control
banding, coverage counting, packaging adequacy, residual-charge voltage
conversion, storage envelope and shelf-life checks and the blocking versus
restricting rollup are exercised by the gate 3 contract test:
scripts/test_e2008_sca_electrostatic_sensitivity_handling.py against
scripts/e2008_sca_electrostatic_sensitivity_handling_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_sca_electrostatic_sensitivity_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
