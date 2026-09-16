---
name: e2008-protection-diode-pull-test
description: "Use when a protection diode pull run is planned or its records are reviewed. Evaluate whether the positive and negative contacts of a protection diode were shown to carry load under the pull of ECSS-E-ST-20-08C clause 9.6.11, after environmental loading rather than before it: confirm the thermal cycles and the humidity soak the lot owed were completed first, resolve each recorded pull onto the contact normal and reject a grip dragged too far off it, divide the normal force by the bonded area that carried it, sentence every device by whichever contact releases first, and refuse to sentence a lot from a sample too thin to represent it. Trigger: ecss, e-st-20-08c-clause-9-6-11, protection-diode-pull-test, protection-diode-positive-contact-bond-strength, protection-diode-negative-contact-bond-strength, diode-pull-after-environmental-conditioning, protection-diode-pull-off-normal-angle, protection-diode-pull-lot-sentencing."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-protection-diode-pull-test, protection-diode-positive-contact-bond-strength, protection-diode-negative-contact-bond-strength, diode-pull-after-environmental-conditioning, protection-diode-pull-off-normal-angle, protection-diode-pull-lot-sentencing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Protection Diode Pull Test (space-systems/ecss/e2008-protection-diode-pull-test)

Use when the task is the protection diode pull test of ECSS-E-ST-20-08C clause
9.6.11 -- judging whether the bond under the positive contact and the bond
under the negative contact of a protection diode were shown to carry load
after the device had been through its environmental block, and whether the
forces that came off the machine can be read as bond strengths at all.

## Domain quick reference

- The clause puts mechanical loading on top of environmental loading, and the
  order is the point. A contact pulled straight off the line reports the
  as-built joint; the array flies the joint that thermal cycling and a humidity
  soak have already worked on, and only the second number belongs in a
  qualification record.
- Two contacts are assessed, not one. The positive and negative contacts of a
  protection diode are laid down by different steps, carry different bonded
  areas and release at different loads, so a device is sentenced by whichever
  lets go first rather than by the average of the two.
- A recorded force is not yet a bond strength. The machine pulls along its own
  axis, so a grip set off the contact normal puts only the cosine component
  into the joint and turns the rest into shear the test was not asking about.
- Area finishes the conversion. A wide contact takes more force than a narrow
  one of identical quality, so the number that compares across package styles
  is the normal force divided by the bonded area that carried it.
- The off-normal allowance is a measurement limit, not a strength limit.
  Past it the geometry, not the joint, dominates the reading, and the honest
  report is that the pull cannot be read -- not a corrected number pushed
  through anyway.
- A lot is sentenced from a sample. Too few devices on the machine is a
  sampling finding in its own right, and it does not become a bond finding
  because the few that were pulled happened to hold.

## Workflow

1. Validate the pull policy first: minimum bond strength, off-normal
   allowance, the thermal cycles and humidity soak owed, the sample share and
   the contacts required. An allowance at or past ninety degrees, or a sample
   share above one, is refused rather than used.
2. Read the conditioning record before any force. Report a short cycle count
   and a short soak together, so the lot is repaired once rather than twice,
   and close the run there.
3. Read the lot size and the devices that were actually pulled, rejecting a
   duplicate device identifier and a contact repeated within one device.
4. For each contact, resolve the recorded pull onto the contact normal, keep
   the machine reading beside the resolved force, and divide by the bonded
   area to get a bond strength.
5. Close on an off-normal pull before sentencing anything, naming every grip
   that went past the allowance -- those readings are not strengths.
6. Check that every required contact was pulled on every device, then check
   that the sample reaches the share the policy asks of the lot.
7. Sentence each device by its weaker contact and carry that contact's name
   into the record beside its strength.
8. Close on one verdict: environmental block incomplete, pull dragged off
   normal, contact sites missing, pull sample not representative, bond
   strength below minimum, or bond strength demonstrated.

## Pitfalls

- Pulling the lot before the environmental block finishes because the machine
  was free that week. The number is real and answers a question nobody asked.
- Quoting the machine force as the bond strength. Two package styles with
  identical process quality will disagree by the ratio of their bonded areas.
- Correcting a wildly off-normal pull with a cosine and reporting it as a
  clean result. Past the allowance the grip geometry, not the joint, sets the
  reading, and the correction only makes the defect harder to see.
- Averaging the positive and negative contacts of one device. The mean of a
  strong contact and a weak one looks healthy and is not.
- Dropping a device with an unpulled contact from the population. The unpulled
  contact is the finding; removing the device makes the finding vanish.
- Sentencing a lot from whatever devices were to hand. A thin sample can pass
  every one of its members and still say nothing about the lot behind it.

## Behavior contract (gate 3)

The policy validation, the environmental block shortfalls, the off-normal
resolution and allowance, the bonded-area conversion, the minimum-strength
comparison, the required-contact coverage, the sample share, the weaker-contact
sentencing and the run verdict are exercised by the gate 3 contract test:
scripts/test_e2008_protection_diode_pull_test.py against
scripts/e2008_protection_diode_pull_test_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2008_protection_diode_pull_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
