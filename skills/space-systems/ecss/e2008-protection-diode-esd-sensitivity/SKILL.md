---
name: e2008-protection-diode-esd-sensitivity
description: "Assess whether the handling and storage regime applied to an electrostatic-discharge-sensitive protection diode keeps it under the voltage it survives, per ECSS-E-ST-20-08C clause 9.10.2: derive the sensitivity band from the withstand voltage and the discharge model it was measured with, grade every obliged control on its own band and on how stale its last verification is, refuse a merely dissipative bag where shielding is owed, measure the store against a two-sided humidity band whose floor is the ESD limit, and turn residual charge into the volts it delivers with the declared margin applied. Use when an ESD-sensitive diode is handled, packed or stored. Trigger: ecss, e-st-20-08c, clause-9-10-2, protection-diode-esd-sensitivity-band, protection-diode-esd-control-verification-age, protection-diode-terminal-shorting-control, protection-diode-esd-shielding-packaging, protection-diode-esd-storage-humidity-floor."
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
  tags: [ecss, e-st-20-08-protection-diode-scope, e2008-protection-diode-esd-sensitivity, e-st-20-08c-clause-9-10-2, protection-diode-esd-sensitivity-band, protection-diode-esd-control-verification-age, protection-diode-terminal-shorting-control, protection-diode-esd-shielding-packaging, protection-diode-esd-storage-humidity-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Protection Diodes -- ESD-Sensitive Handling and Storage (space-systems/ecss/e2008-protection-diode-esd-sensitivity)

Use when the task is clause 9.10.2 of ECSS-E-ST-20-08C: a protection
diode has been found sensitive to electrostatic discharge, and whether
the way it was handled, packed and stored actually kept the voltage it
could see below the voltage it is known to survive.

## Domain quick reference

- Sensitivity is derived, not declared, and it is derived against a named
  discharge model. The same withstand voltage places a part in a
  different band under a human body model than under a machine model, so
  a number quoted without its model places nothing at all.
- A withstand voltage sitting exactly on a band limit belongs to the less
  sensitive band, and the comparison absorbs representation error rather
  than moving the limit.
- An obliged control is graded three ways, not one. Present is the
  weakest of the three: a ground path measured outside its own resistance
  band is not a ground path, and a measurement taken long enough ago that
  its verification interval has run out no longer says anything about the
  bench the part was on today. A wrist strap measured in band eleven
  months ago is not a verified wrist strap.
- The obliged set grows with sensitivity, and a discrete diode owes a
  control a bonded cell does not: its terminals are shorted together, so
  the leads stop being an antenna for a field the package would otherwise
  never see. That control is itself graded in a band -- a shorting bar
  measuring kilohms is not a short.
- Four passes out of five obliged controls is not a compliant control
  set. A control nobody offered is graded absent rather than skipped, or
  a regime that owes five and reports four reads as green.
- Shielding and dissipative are different claims, not two grades of one
  claim. A dissipative bag bleeds charge off its own surface; it does not
  keep an external field off the part inside, so the two sensitive bands
  oblige shielding outright.
- The storage envelope is two-sided on both axes, and the humidity FLOOR
  is the one an ESD regime exists for. A store that is too humid is a
  corrosion problem; a store that is too dry is the ESD problem, because
  dry air is what lets ordinary handling build the charge everything else
  in the regime is there to bleed away. A ceiling without a floor is half
  a check. Shelf life already spent is graded alongside it.
- Residual charge measured on the part is not the finding. The finding is
  the voltage that charge delivers across the package capacitance, and a
  smaller package capacitance turns the same charge into more volts.
- That voltage is taken against the withstand voltage with the declared
  margin applied, so a part that clears the limit only on the nose is
  still reported rather than passed.

## Workflow

1. Derive the sensitivity band from the withstand voltage and the
   discharge model it was measured with, validating that the threshold
   table rises and names every model.
2. Resolve which controls that band obliges, and grade each one on
   presence, on its own measured band, and on the age of the measurement
   against its verification interval.
3. Grade any control that was never offered as absent rather than
   skipping it, and report separately any offered control the band does
   not oblige.
4. Grade the packaging against the minimum category the band obliges,
   refusing a dissipative bag where shielding is owed.
5. Measure the store against two-sided temperature and humidity bands,
   naming which side a reading fell out of, and grade the shelf life
   already spent against the declared life.
6. Convert the residual charge and the package capacitance into the
   voltage the charge delivers, apply the declared margin factor, and
   compare with the withstand voltage under a named tolerance.
7. Report every arm's findings together and call the regime compliant
   only when the finding list is empty.

## Pitfalls

- Quoting a withstand voltage without its discharge model. The number on
  its own places the part in no band, and the model it came from is what
  makes the band mean anything.
- Grading a control as present and stopping. Presence is a third of the
  question; the measured value and the age of that measurement are the
  other two thirds, and staleness is the one routinely dropped.
- Treating the verification interval as paperwork. A ground path verified
  outside its interval is an unverified ground path today, whatever it
  measured last year.
- Skipping a control nobody offered. An obliged control absent from the
  record is a deficiency, not an omission from the report, and a set that
  grades four of five has graded four.
- Accepting a dissipative bag as shielding. Bleeding surface charge and
  excluding an external field are different jobs, and only one of them is
  what a sensitive part in a stores rack needs.
- Putting a ceiling on humidity and no floor. The dry end is the ESD end;
  a one-sided humidity limit passes exactly the store most likely to
  charge the part during handling.
- Reporting residual charge as the finding. Charge is not a stress; the
  voltage it delivers across the package capacitance is, and a small
  package turns a small charge into a large voltage.
- Dropping the margin factor to make a part clear. A part that clears its
  withstand voltage only without the declared margin has not cleared it.
- Moving a band limit to pass a reading that sits exactly on it. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the declared band stays as declared.
- Reporting a bare rejection. A stale wrist strap, a dissipative bag, a
  dry store and an uncleared residual charge each break the regime for a
  different reason, and the report names which.

## Behavior contract (gate 3)

The discharge model set and the rising withstand-voltage threshold table
with its project override, the band derivation with an exact limit
falling to the less sensitive band, the per-band obliged control set
including terminal shorting, the three-way control grading on presence,
own band and verification age with absent controls graded rather than
skipped, the packaging ladder and the minimum category per band, the
two-sided temperature and humidity bands with the humidity floor named
and shelf life graded alongside, the charge-to-voltage conversion and its
margin-applied comparison under a named tolerance, and the conjunctive
regime verdict are exercised by the gate 3 contract test:
scripts/test_e2008_protection_diode_esd_sensitivity.py against
scripts/e2008_protection_diode_esd_sensitivity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_protection_diode_esd_sensitivity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
