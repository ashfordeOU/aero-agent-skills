---
name: q60-class-2-asic-requirements
description: "Determine which flow of the dedicated ASIC development standard a class 2 application specific integrated circuit enters under ECSS-Q-ST-60C clause 5.6.2, and what that referral costs: compare the candidate build against the referenced one axis by axis, group the movements into silicon, design and assembly, build the activity plan the device category carries, split it into work the heritage still covers and work the movements reopen, and check the reuse evidence and the currency of the qualification behind it. Use when an ASIC is about to be bought or reused on a heritage claim. Trigger: ecss, q-st-60c-clause-5-6-2, class-2-asic-referral, dedicated-asic-standard-flow, asic-heritage-movement-axes, asic-activity-inheritance-split, asic-qualification-currency-window."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-2-asic-requirements, class-2-asic-referral, dedicated-asic-standard-flow, asic-heritage-movement-axes, asic-activity-inheritance-split, asic-qualification-currency-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 ASIC Referral (space-systems/ecss/q60-class-2-asic-requirements)

Use when the task is the clause 5.6.2 referral of ECSS-Q-ST-60C: a class 2
application specific integrated circuit is in front of you, and the general
component rules are not the rules it is developed or reused under. The
dedicated ASIC and programmable-device development standard is. The work is
deciding which flow of that standard the device enters, which activities the
flow carries, and — because this is a class 2 device — which of those
activities the referenced qualification still covers.

## Domain quick reference

- The general component rules stop at the package. A catalogue part is bought
  against a specification and screened; an ASIC is a design the project
  caused to exist, and the evidence that it works is evidence somebody has to
  produce. Clause 5.6.2 does not restate that evidence — it refers the device
  out to the standard that owns it.
- A candidate build differs from a qualified one along three independent
  groups. Silicon movements are the foundry, the technology node, the mask
  set and the process option. Design movements are the design database, the
  cell library and the functional scope. Assembly movements are the package,
  the die attach and the lid seal. The groups are independent because they
  invalidate different evidence.
- Class 2 is not class 1 with a smaller test list. It is the same activity
  set with more of it allowed to rest on a reference — but only where the
  reference still holds. An activity rests on heritage when none of the
  movement groups that would invalidate it moved.
- Two activities never rest on heritage. The requirements review belongs to
  this order and this application, and the lot acceptance test definition
  belongs to the lot being bought. Both are re-performed even when every axis
  stood still.
- Device category changes the plan, not the inheritance rule. A full-custom
  part adds layout verification, an array part adds configuration
  verification, a mixed-signal part adds analogue characterisation and
  isolation analysis. Each addition then inherits or reopens by the same test
  as everything else.
- Two silicon movements are a different device, not a delta. One foundry
  change with everything else held is a delta the standard can bound; a
  foundry change together with a mask set change leaves nothing of the
  original silicon evidence to bound it against.
- A reuse claim with no report reference, no usage record, no delta analysis
  and no review of the foundry's process change notices is not a weak claim.
  It is an unrouted device: nothing can be inherited, because nothing has been
  pointed at.

## Workflow

1. Validate the case: part number, device category, procurement origin, and
   for anything but a new development both build records, the evidence
   references and the age of the referenced qualification.
2. Send a new development straight to the full flow. It has no heritage to
   argue about and the whole activity plan is in front of it.
3. Compare candidate against reference across every heritage axis and group
   what moved into silicon, design and assembly movements.
4. Check the required reuse evidence is actually named. A short list stops
   the referral before any route is picked; there is nothing to inherit from.
5. Test the currency of the referenced qualification against the window, and
   record a lapse as a finding that keeps a plain reuse off the table.
6. Route: two or more silicon movements to the full flow, any movement to the
   delta flow, a lapsed but otherwise unmoved heritage to the delta flow,
   everything still to a reviewed reuse.
7. Build the activity plan for the category and split it into inherited work
   and work to run again. A full flow and a blocked referral inherit nothing.
8. Report the route, the axes that moved, the split, the share of the plan
   being re-performed, the missing evidence and every finding.

## Pitfalls

- Treating the referral as paperwork and running the general component flow
  anyway. Screening a part whose internal design was never verified tests the
  package, not the device.
- Averaging the movement groups into one delta count. A single assembly
  movement reopens package qualification and nothing else; a single silicon
  movement reopens radiation, prototyping and the process-dependent
  characterisation. Counting them together hides which is which.
- Letting the requirements review or the lot acceptance test definition ride
  on the reference because the silicon did not move. They are tied to this
  application and this lot, not to the die.
- Reading a clean delta as a licence to skip the evidence check. The delta is
  computed from two records; the evidence is what makes those records
  admissible in the first place.
- Extending the currency window to keep a convenient reuse alive. The window
  describes how long the referenced evidence is argued to hold, not how long
  the schedule needs it to.
- Adding a category's extra activities to the plan and then inheriting them
  by default. They reopen on the same movement test as everything else, and
  for a mixed-signal part almost every movement reaches them.

## Behavior contract (gate 3)

The policy validation, build record validation, movement detection and
grouping, category activity plan, inheritance split, re-perform ratio, reuse
evidence check, qualification currency test and route selection are exercised
by the gate 3 contract test:
scripts/test_q60_class_2_asic_requirements.py against
scripts/q60_class_2_asic_requirements_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_2_asic_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
