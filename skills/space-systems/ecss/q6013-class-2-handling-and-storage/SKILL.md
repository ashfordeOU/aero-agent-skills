---
name: q6013-class-2-handling-and-storage
description: "Use when a bonded store, an issue to the line or a shelf-life review must become one release, release-with-actions or quarantine verdict. Evaluate the protected handling and controlled storage regime around a commercial EEE lot bought at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.4: band the part by its declared electrostatic withstand, derive the protection measures that band owes, credit only a substitution that is recorded and approved, report the store temperature and humidity as an excursion and as a margin to the nearest limit, count the dry-pack floor life consumed net of a dry-cabinet pause, read the shelf-life and re-inspection clocks, and name every handler whose qualification has lapsed. Trigger: ecss, q-st-60-13c-clause-5-4, class-two-commercial-eee-handling, recorded-equivalent-esd-substitution, dry-cabinet-floor-life-credit, storage-environment-margin-fraction, handler-esd-qualification-lapse, stored-lot-release-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-handling-and-storage, class-two-commercial-eee-handling, recorded-equivalent-esd-substitution, dry-cabinet-floor-life-credit, storage-environment-margin-fraction, handler-esd-qualification-lapse, stored-lot-release-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Handling and Storage (space-systems/ecss/q6013-class-2-handling-and-storage)

Use when the task is clause 5.4 of ECSS-Q-ST-60-13C at the intermediate
assurance class: a commercial EEE lot is inside a bonded store, and the
question is whether the regime around it still matches the sensitivity,
moisture behaviour and age of the parts in the bag.

## Domain quick reference

- The intermediate class is not the highest class with the numbers relaxed.
  It is the class that accepts an equivalent substitute for a protection
  measure, and the whole gap reading turns on whether that substitution was
  written down. An approved substitute closes the gap; the same bench
  arrangement with no approval reference leaves it open.
- Damage in the store is the damage that leaves no mark. A latent
  electrostatic injury passes incoming inspection and fails after
  integration, months after the event that caused it, which is why the
  measures are graded on being operated rather than on whether anything
  visibly went wrong.
- Sensitivity is banded and the band sets the regime. A part surviving a few
  hundred volts is not a stricter version of a part surviving several
  thousand; it owes ionisation and a verified personnel ground, because the
  baseline leaves gaps a low-band part does not survive.
- Two numbers describe the same environment reading and they answer different
  questions. The excursion says how far outside the band the store went; the
  margin fraction says how much of its half-span an inside reading still
  holds. A store sitting exactly on its upper limit is inside and has nothing
  left, and only the second number says so.
- Moisture behaviour arrives with the part. Once the dry pack is opened the
  clock runs whether or not anyone is working, a sealed dry cabinet pauses it
  rather than resetting it, and an approved bake returns allowance. A level
  carrying no floor life is not a rationing problem at all.
- Shelf life and the periodic re-inspection interval are two clocks on one
  lot. A lot well inside its shelf life can still owe a re-inspection,
  because the terminations and the packaging age on their own schedule.
- A qualified store is not a qualified handler. The regime is operated by
  people, and a lapsed electrostatic qualification on the operator who opens
  the bag defeats every measure on the equipment list.

## Workflow

1. Validate the record: a non-blank lot identity, a finite non-negative
   withstand voltage, environment limits that span a real band, a positive
   shelf life and re-inspection interval, and a review date at or after
   entry. A review that precedes storage entry is an input error.
2. Band the part from its declared withstand voltage and derive the measures
   that band owes: the marked protected area, grounded worksurface,
   personnel ground and shielding transport bag for every band, plus
   ionisation and a periodic personnel-ground verification for the most
   sensitive bands.
3. Read the measures the store operates against the owed set. Credit a
   substitution only where it names the measure it replaces, names a
   different substitute and carries an approval reference; report the rest as
   refused rather than silently dropping them.
4. Grade the environment twice. Return the signed excursion, with the
   boundary absorbed by a named tolerance rather than by moving a limit, and
   the margin fraction to the nearest limit so an inside reading running at
   the edge is still visible.
5. Count the dry-pack floor life consumed since the pack was opened, net of
   the dry-cabinet hours and any approved bake, and refuse credits that
   together exceed the recorded exposure.
6. Read the shelf-life clock and the re-inspection clock independently,
   taking the re-inspection reference from the last recorded inspection
   where there is one and from storage entry otherwise.
7. Name every declared handler whose qualification expired before the review
   date, treating an expiry falling on the review date as still current, and
   grade the gap harder for a sensitive band.
8. Rank the findings, most severe first, and close on one verdict: released,
   released-with-actions, or quarantined.

## Pitfalls

- Crediting a substitution that exists only as practice. The intermediate
  class permits the substitute and still asks for the record; an
  unreferenced arrangement is an open gap however sensible the bench looks.
- Grading the store on what it owns rather than what it operates. A wrist
  strap in a drawer and an ioniser switched off at the wall both read as
  present on an equipment list, and neither protects a band 0 part.
- Reducing an environment reading to inside or outside. A store on its upper
  limit and a store in the middle of its band are the same yes, and the
  margin fraction is the only place that difference survives.
- Counting floor life from when work started. The clock starts when the dry
  pack is opened, so a pack opened on Friday and handled on Monday has
  already spent the weekend against its allowance.
- Reading a valid shelf life as a releasable lot. The re-inspection interval
  runs on its own, and a lot with two years of shelf life left can still owe
  an inspection before it is issued.
- Auditing the equipment and not the people. A lapsed handler qualification
  is a gap in the regime, and on a sensitive band it is the same size of gap
  as a missing ioniser.

## Behavior contract (gate 3)

The sensitivity banding, owed-measure derivation, recorded-substitution
credit, environment excursion and margin fraction, dry-pack floor-life
accounting, shelf-life and re-inspection clocks, handler qualification gaps
and the storage verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_handling_and_storage.py against
scripts/q6013_class_2_handling_and_storage_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_handling_and_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
