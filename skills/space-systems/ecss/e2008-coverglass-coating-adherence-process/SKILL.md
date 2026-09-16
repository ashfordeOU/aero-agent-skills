---
name: e2008-coverglass-coating-adherence-process
description: "Use when a whole-lot conditioning load is being built or reviewed. Plan the loading of every coverglass in the lot into the ambient pressure chamber ahead of an adherence check, under ECSS-E-ST-20-08C clause 8.7.11.2.2: measure the load against the declared roster rather than against whatever reached the bench, split a lot larger than the chamber into whole runs, give each article one recorded rack, slot and batch so an exposure can be attributed to it, keep coated faces turned out and unstacked, and confirm the chamber is vented to the room. Trigger: ecss, e-st-20-08c-clause-8-7-11-2-2, coverglass-lot-chamber-loading, ambient-pressure-chamber-load-completeness, coverglass-rack-batch-split, coverglass-slot-position-map, pre-adherence-conditioning-load."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-coating-adherence-process, coverglass-lot-chamber-loading, ambient-pressure-chamber-load-completeness, coverglass-rack-batch-split, coverglass-slot-position-map, pre-adherence-conditioning-load]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Coating Adherence Process (space-systems/ecss/e2008-coverglass-coating-adherence-process)

Use when the task is clause 8.7.11.2.2 of ECSS-E-ST-20-08C -- getting
the articles into the chamber before the coating attachment is checked.
The population is every coverglass in the lot, not a sample of it, and
that one word is what the whole step turns on.

## Domain quick reference

- The adherence check that follows reports on articles that were
  conditioned. An article that never entered the chamber has no
  conditioned state to report, and a result taken on its neighbours
  does not cover it.
- The roster is declared before the load and the load is measured
  against the roster. Counting the articles that reached the bench
  measures the bench, not the lot.
- Two failures of completeness run in opposite directions. A roster
  article missing from the chamber is an omission; an article in the
  chamber that is not on the roster is a stranger, and its result
  belongs to no declared lot. Both are reported as themselves.
- Capacity is a whole number. A lot larger than the chamber holds is
  split into runs, the run count is the lot size over the capacity
  rounded up, and one article over a capacity boundary costs a whole
  further run.
- Two batches at nominally the same set point are still two exposures,
  so the batch an article sat in is recorded with it. Without that, a
  result from the second run is attributed to the first run's record.
- One article, one slot; one slot, one article. An article whose
  position nobody wrote down cannot have an exposure attributed to it,
  and two articles in one recorded slot mean at least one of those
  records is wrong. The same slot number in another rack is a different
  place, not a duplicate.
- A coated face turned against the rack, or under another article, is
  not a conditioned face, and the adherence check that follows will
  read it as though it were.
- The chamber stays at the pressure of the room. A vent left shut turns
  an ambient exposure into a vessel run, in either direction, whatever
  the gauge on the front says.

## Workflow

1. Validate the loading policy first: slots per rack, rack count, batch
   ceiling, ambient pressure tolerance and whether a slot record is
   demanded. A negative pressure tolerance is refused rather than used.
2. Split the load against the roster into loaded articles, omissions
   and strangers, refusing a duplicated roster entry or an article
   recorded as loaded twice.
3. Size the chamber and the run count before anything else is judged: a
   lot that cannot be conditioned inside the campaign's batch ceiling
   is a planning failure, not a loading one.
4. Judge completeness next, and report every omission and every
   stranger by name rather than as a count. A load that is missing an
   article is not made whole by the others being well placed.
5. Only on a complete load, judge attribution: rack and slot inside the
   chamber, no two articles in one place, a batch recorded, the coated
   face turned out, and nothing stacked. All findings are listed, not
   only the first.
6. Confirm the chamber is vented to the room in both directions before
   the load is called good.
7. Close on one verdict: lot not established, loading incomplete,
   loading not attributable, chamber not vented to ambient, or all
   coverglasses loaded.

## Pitfalls

- Loading what came to the bench. The roster is the population, and a
  load that matches the trolley rather than the roster silently drops
  whatever was left in the store.
- Reporting a stranger as an extra sample. It was conditioned, it may
  well pass, and nothing ties its result to a lot -- which is worse
  than not having tested it.
- Splitting a lot into runs and recording only the set point. The set
  point is what the two runs shared; the batch number is what tells
  them apart when a result has to be traced.
- Treating a slot number as unique across the chamber. Rack two slot
  three and rack one slot three are different places, and folding them
  together invents a clash that is not there.
- Laying the articles face down because the rack was designed for
  something else. The face against the rack is the face the adherence
  check will read, and it was never conditioned.
- Trusting a pressure reading near zero without checking its sign. A
  chamber a little under the room is as far from an ambient exposure as
  one a little over it, which is why the tolerance is applied to the
  magnitude.

## Behavior contract (gate 3)

The policy validation, chamber capacity and batch count, loaded
fraction, roster membership with its omissions and strangers, the
orientation recognition, the rack, slot, batch, facing and stacking
attribution findings, the ambient pressure check and the loading
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_coating_adherence_process.py against
scripts/e2008_coverglass_coating_adherence_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_coating_adherence_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
