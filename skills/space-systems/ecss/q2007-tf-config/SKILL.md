---
name: q2007-tf-config
description: "Verify that a test facility is under configuration control as ECSS-Q-ST-20-07 clause 5.6.2 asks, and say what the state of the baseline obliges the test centre to do. Use when a campaign is about to run in a facility whose hardware, software, fluid lines and fixed instrumentation have moved since the last baseline: refuse a facility never baselined, check that every configuration item carries an identification, replay the approved and applied change records from the baseline version forward, and report any item whose as-run configuration that chain does not reach. Trigger: ecss, q-st-20-07-test-facility-clause-5-6-2, test-facility-configuration-baseline, test-facility-as-run-configuration-drift, test-facility-unapproved-change-applied, test-facility-configuration-item-identification."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-tf-config, q-st-20-07-test-facility-clause-5-6-2, test-facility-configuration-baseline, test-facility-as-run-configuration-drift, test-facility-unapproved-change-applied, test-facility-configuration-item-identification, test-facility-change-chain-replay]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres — Test Facility Configuration Control (space-systems/ecss/q2007-tf-config)

Use when the task is clause 5.6.2 of ECSS-Q-ST-20-07: a test facility is
about to carry a campaign, its configuration has to be identified and
its changes controlled, and the question is whether the facility
standing in the hall today is the one the baseline describes.

## Domain quick reference

- A facility is a configuration, not a room. Chambers, shakers, fluid
  lines, fixed instrumentation, control software and the fixtures that
  hold the article are each configuration items, and a facility with no
  item list has nothing for a change to be controlled against.
- Identification is what makes an item controllable. An item on the list
  with no identification cannot be pointed at by a change record, so
  identification coverage is measured across the whole baseline rather
  than assumed from the presence of a list.
- A change is a move between two versions, not an event. A record that
  does not advance the version it names says nothing about what the
  facility became, and is an input error rather than a finding.
- Approved and applied are two different flags and both matter. A change
  approved and not yet applied is work in front of the campaign; a
  change applied and not approved is the control failure the clause
  exists to catch, and it outranks everything downstream of it.
- The as-run configuration is the evidence. Replaying the approved and
  applied changes from the baseline version gives the configuration the
  records say the facility should be in; an item the chain does not
  reach is drift, whichever direction it drifted in.
- A chain that breaks part way is not a smaller chain. An approved and
  applied change whose from-version no other record produces means the
  records are inconsistent, and reading only the changes that happen to
  link up would hide exactly that.

## Workflow

1. Validate the configuration policy first: the identification coverage
   the facility owes and how many changes may sit pending approval while
   a campaign runs. A coverage outside zero to one is refused.
2. Refuse a facility with no baseline; that closes the assessment on the
   facility not being baselined rather than on any later finding.
3. Validate the baseline items: a label and a whole version each, no
   item twice. Carry the identification string, blank or not, because
   the blank ones are the coverage measurement.
4. Validate the change records: a change identifier, the item it names,
   a from-version strictly below its to-version, and both flags as real
   booleans. Refuse the same change identifier twice.
5. Separate the applied-and-not-approved records; if any exist, close
   there, naming them.
6. Replay the approved and applied changes per item from the baseline
   version, refusing a chain whose remaining records do not link.
7. Compare the replayed version with the as-run record item by item.
   Refuse an as-run item the baseline never declared; collect the rest
   as drift.
8. Close on one verdict in order: not baselined, unapproved change
   applied, configuration drift, identification incomplete, changes
   pending approval, or configuration under control.

## Pitfalls

- Reading a change log as a configuration. The log says what was
  proposed; only the replay from the baseline says what the facility
  should now be, and only the as-run record says what it is.
- Treating an unapplied approved change as drift. It is planned work,
  and folding it into the expected version makes a controlled facility
  look uncontrolled while hiding the records that are genuinely wrong.
- Skipping a change whose from-version does not link. That silently
  repairs an inconsistent record set; the break is the finding.
- Measuring identification on the items that have it. Coverage is over
  the whole baseline, so the unidentified items have to stay in the
  denominator.
- Letting a drift finding outrank an unapproved applied change. The
  drift is a symptom; the uncontrolled change is the clause failure, and
  reporting the symptom first sends the correction to the wrong place.

## Behavior contract (gate 3)

The policy validation, baseline validation, identification coverage, the
change-record validation, the unapproved-applied separation, the change
chain replay and its break refusal, the as-run drift comparison and the
verdict ordering are exercised by the gate 3 contract test:
scripts/test_q2007_tf_config.py against
scripts/q2007_tf_config_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_tf_config.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
