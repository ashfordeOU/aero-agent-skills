---
name: e2008-diode-contact-adherence-purpose
description: "Determine what an attachment strength check on protection diode contacts has to demonstrate under ECSS-E-ST-20-08C clause 9.6.6.2.1: settle first whether the device carries attached contacts at all, because one that carries none is outside the check entirely, fold the downstream welding, cure, handling, launch and cycling stressors into one demand index, map each onto the evidence parameter it is watched through, derive the pull load the service peak and its declared margin ask for, and size the sample that lets a destructive result speak for the lot. Use when scoping or defending a protection diode contact adherence campaign. Trigger: ecss, e-st-20-08c-clause-9-6-6-2-1, protection-diode-contact-adherence-purpose, diode-attached-contact-presence, diode-terminal-attachment-demand-index, diode-contact-pull-load-margin, diode-adherence-sample-coverage."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-diode-contact-adherence-purpose, protection-diode-contact-adherence-purpose, diode-attached-contact-presence, diode-terminal-attachment-demand-index, diode-contact-pull-load-margin, diode-adherence-sample-coverage, protection-diode-attachment-evidence-map]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Diode Contact Adherence Purpose (space-systems/ecss/e2008-diode-contact-adherence-purpose)

Use when the task is to state and defend why the contacts of a
protection diode are pulled under ECSS-E-ST-20-08C clause 9.6.6.2.1 --
whether this device is even in scope, which downstream steps the
attachment has to survive, and whether the planned pull and sample can
produce a number that describes anything beyond the devices destroyed.

## Domain quick reference

- The clause carries a condition before it carries a requirement.
  Protection diodes reach a panel in more than one construction: some
  arrive with terminals attached to the die, some as a bare die or a
  diffused region with nothing attached. Only the first kind has an
  attachment a pull can describe.
- Applying the check to a device with no attached contacts does not
  return a conservative answer. It returns a number about the grip of
  the tooling, entered in the record as though it were about the part.
- Where contacts are present, the strength has to outlast the welding of
  the terminal into the string, the shrinkage of an adhesive as it
  cures, the handling of panel integration, the broadband loading of
  launch, and the coefficient mismatch a mission's worth of thermal
  cycles drives through the joint.
- Those stressors carry weights that sum to one, so the demand index is
  a share of the downstream life rather than a score. A device meeting
  almost none of them does not earn a destructive check; one meeting
  most of them does.
- A stressor is only worth declaring if something is recorded against
  it, so each maps onto an evidence parameter -- weld pull strength,
  die attach shear, terminal peel, fatigue margin, resistance drift.
- The pull load is not the service peak. It is the peak multiplied by a
  declared margin, and pulling to the peak itself proves only that the
  joint survives the load it already survives.
- The sample has two floors, not one: a share of the lot and an absolute
  device count. Three devices out of four hundred clears neither, and
  two devices out of four clears the share while proving nothing.

## Workflow

1. Validate the purpose policy first: pull load margin, demand floor,
   sample coverage floor and minimum device count. A margin below one is
   refused rather than used.
2. Settle contact presence before anything else. With no attached
   contacts, close there -- the verification is not applicable and no
   pull plan is owed.
3. Group the declared downstream stressors, rejecting an unrecognised
   one rather than ignoring it, count a repeated one once, and map each
   onto the evidence parameter it is watched through. Append the shared
   objective whenever any stressor is present.
4. With contacts present but no stressor declared, close there: nothing
   states what the attachment is being asked to survive.
5. Derive the demand index, the required pull load from the service peak
   and its margin, and the sample coverage. A value landing exactly on
   its floor passes; the comparison tolerance absorbs representation
   error and the floor does not move.
6. Report every finding, not the first, and close on one verdict:
   verification not applicable, stressors not declared, demand below
   threshold, pull load insufficient, sample coverage insufficient, or
   verification justified.

## Pitfalls

- Pulling a device that has nothing attached. The tooling grips the die,
  the number is about the grip, and the record cannot tell afterwards
  which of the two it measured.
- Declaring the check applicable across a mixed procurement. Two diode
  constructions in one lot means two answers, and the one that carries
  no contacts silently drags the lot statistic wherever the tooling
  happened to land.
- Justifying the pull by the mission alone. Most of the demand is spent
  before launch, in the weld schedule and the cure, and an argument
  built only on cycling understates what the joint is being asked for.
- Declaring a stressor and recording nothing for it. The campaign then
  produces a pass that says only that nobody looked, which reads in the
  record exactly like a pass that says the joint held.
- Pulling to the service peak. The margin is the whole point of a
  destructive check; without it the result restates the load the part is
  already known to carry.
- Reading sample coverage as the only sample question. A share of a huge
  lot can be met by a handful of devices whose spread says nothing, so
  the absolute count floor sits alongside it.
- Comparing a derived index or coverage against its floor by bare
  arithmetic. Both come out of sums and divisions that land a few units
  in the last place either side of a limit on different hosts, so the
  comparison absorbs that error while the floor itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, contact presence categories, stressor grouping
and evidence mapping, the attachment demand index, the required pull
load from the service peak and its margin, the sample coverage and
device count floors, the finding inventory and the purpose verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_diode_contact_adherence_purpose.py against
scripts/e2008_diode_contact_adherence_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_diode_contact_adherence_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
