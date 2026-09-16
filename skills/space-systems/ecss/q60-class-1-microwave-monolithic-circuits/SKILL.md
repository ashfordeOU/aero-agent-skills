---
name: q60-class-1-microwave-monolithic-circuits
description: "Use when an amplifier or converter stage needs a class 1 MMIC. Evaluate a microwave monolithic integrated circuit for class 1 use under ECSS-Q-ST-60C clause 4.6.5: take the foundry process, the source category and the delivery form, check the operating band sits inside the band the part was characterized over, resolve the channel temperature from baseplate, thermal resistance and dissipated power against the derating limit, compare applied against rated drive, group the electrostatic sensitivity, then return the procurement and evaluation activities the source and the bare die oblige with a usability verdict. Trigger: ecss, q-st-60c-clause-4-6-5, class-1-mmic-selection, mmic-foundry-source-category, mmic-characterized-band-coverage, mmic-channel-temperature-derating, mmic-rf-drive-derating, mmic-bare-die-handling-controls."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-1-microwave-monolithic-circuits, class-1-mmic-selection, mmic-foundry-source-category, mmic-characterized-band-coverage, mmic-channel-temperature-derating, mmic-rf-drive-derating, mmic-bare-die-handling-controls]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Microwave Monolithic Circuits (space-systems/ecss/q60-class-1-microwave-monolithic-circuits)

Use when the task is clause 4.6.5 of ECSS-Q-ST-60C: a class 1 radio-frequency
chain needs a microwave monolithic integrated circuit, and the decision spans
the design that calls for it, the source it is chosen from, the purchase that
brings it in and the application that then runs it.

## Domain quick reference

- The part is bought as a component and used as a circuit, and the two halves
  do not separate. A faultlessly procured device is still unusable if the
  stage runs it outside the band it was characterized over, above the drive
  it was rated at, or hotter than the channel temperature the reliability
  estimate assumed.
- The source category is what somebody other than the project has already
  demonstrated. A space-qualified catalogue part arrives with that
  demonstration behind it; a custom die from a qualified foundry arrives with
  the process demonstrated but not the design; a commercial foundry part
  arrives with neither, which is why it carries a foundry assessment, an
  evaluation programme and a radiation evaluation before it carries anything
  else.
- The characterized band is the only band the data covers. Extrapolating a
  gain or a match figure past the edge of the measured sweep is not
  engineering judgement, it is an assumption about a device whose parasitics
  were never measured there, and the width that falls outside is the honest
  statement of the gap.
- Channel temperature is a computed quantity, not a rating to be read off.
  It follows from the baseplate the module sits on, the junction-to-case
  thermal resistance and the power actually dissipated, and it is the input
  the degradation rate is exponential in.
- A bare die moves the package onto the equipment builder. Hermeticity,
  visual inspection, handling and the attach and interconnect processes all
  become the project's qualification problem, which is why the delivery form
  changes the activity set and not just the shipping method.
- Microwave die are among the most electrostatic-sensitive parts on a board.
  A withstand voltage in the low hundreds puts the part in a category where
  ordinary bench practice is not sufficient and reinforced controls attach to
  every handling step.

## Workflow

1. Validate the selection case: the foundry process, the source category, the
   delivery form, both frequency bands, the thermal path and the drive
   levels. A missing field is an input error, because the verdict is a
   conjunction and an absent term cannot be assumed benign.
2. Compare the operating band with the characterized band, report the share
   that is covered and the width in gigahertz that falls outside.
3. Resolve the channel temperature from the baseplate, the thermal resistance
   and the dissipated power, and take its margin against the class 1 derating
   limit.
4. Take the applied drive as a share of the rated drive and compare it with
   the drive derating limit, absorbing representation error exactly at the
   limit.
5. Assemble the activities the source category obliges, add what a bare die
   obliges, and add reinforced handling controls when the electrostatic
   withstand voltage sits below the control threshold.
6. Return the verdict: not usable when the band, the thermal or the drive
   check fails or the policy bars the source; usable with additional
   activities when anything beyond plain lot acceptance attaches; usable as
   procured otherwise.

## Pitfalls

- Reading a datasheet plot past its last measured point. The curve ends
  where the sweep ended, and a stage placed above that edge is running on an
  extrapolation nobody measured.
- Taking the maximum channel temperature from the datasheet as the operating
  point. The rated maximum is a destruction boundary; the class 1 derating
  limit sits below it, and the margin between them is the reason the part
  survives the mission rather than the acceptance test.
- Deriving the channel temperature from the baseplate the analysis assumed
  rather than the one the module sees. The thermal resistance is a property
  of the part; the baseplate temperature is a property of the installation,
  and the second is the one that drifts between analysis and hardware.
- Treating a bare die as a cheaper package. Removing the package moves
  hermeticity, visual inspection and the attach process onto the project,
  and those activities cost more than the package did.
- Quoting a drive level in decibels and comparing it as if it were linear. A
  derating limit expressed as a share of rated drive is a ratio of powers,
  and mixing the two representations is how a stage ends up a factor over its
  limit while the arithmetic looks right.
- Comparing a computed channel temperature or drive ratio with its limit by
  bare arithmetic. Both are computed, so a case sitting exactly on its limit
  can land a few units in the last place above it; the comparison absorbs
  that representation error while the limit stays untouched.

## Behavior contract (gate 3)

The policy merge, case validation, band coverage and out-of-band span,
channel temperature and margin, drive ratio, Arrhenius acceleration,
electrostatic sensitivity grouping, activity assembly and usability verdict
are exercised by the gate 3 contract test:
scripts/test_q60_class_1_microwave_monolithic_circuits.py against
scripts/q60_class_1_microwave_monolithic_circuits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_microwave_monolithic_circuits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
