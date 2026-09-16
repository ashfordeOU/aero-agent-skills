---
name: e2008-blocking-diode-adherence-process
description: "Use when a blocking diode adherence run is loaded or audited. Execute the ambient pressure chamber entry every blocking diode of a lot passes through before its contact adherence is examined, under ECSS-E-ST-20-08C clause 12.6.4.2.2: reconcile the loaded serials against the lot roster so a missing, repeated or foreign device is named rather than lost in a total, hold entry completeness at the whole lot instead of a convenient subset, check the residence dwell every batch holds in its own right, cap the batch count and the changeover between them, and hold the ambient pressure band. Trigger: ecss, e-st-20-electrical-scope, e-st-20-08c-clause-12-6-4-2-2, blocking-diode-chamber-entry-manifest, blocking-diode-lot-entry-completeness, blocking-diode-chamber-residence-dwell, blocking-diode-foreign-device-detection, blocking-diode-adherence-batch-sequence."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c-clause-12-6-4-2-2, e2008-blocking-diode-adherence-process, blocking-diode-chamber-entry-manifest, blocking-diode-lot-entry-completeness, blocking-diode-chamber-residence-dwell, blocking-diode-foreign-device-detection, blocking-diode-adherence-batch-sequence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Adherence Chamber Entry (space-systems/ecss/e2008-blocking-diode-adherence-process)

Use when the task is the run itself under ECSS-E-ST-20-08C clause
12.6.4.2.2 -- every blocking diode of the lot into the ambient pressure
chamber, held there for the residence dwell, and only then examined for
contact adherence. The word doing the work is "every", and it is the
part of the procedure normally satisfied by a sentence rather than by a
record.

## Domain quick reference

- Entry is a reconciliation, not a count. A total tells a full tray from
  an empty one and nothing else, and every interesting defect here
  leaves the total intact.
- Three things go wrong at the tray and only one of them is a shortage.
  A device can be missing, a device can belong to another lot, and a
  serial can appear twice because one part was logged onto two trays. A
  swap produces the first two at once and leaves the count unchanged.
- A missing device is the finding that outranks the rest. The lot
  sentence is handed out afterwards to devices that were never in the
  chamber, and nothing downstream records which ones they were.
- A foreign or repeated serial comes next. The pull data is real; it
  simply belongs to a population other than the one it will be filed
  under, and the lot statistic quietly absorbs it.
- A lot too large for one chamber is split, and splitting is allowed.
  Shortening is not: every batch holds the residence dwell in its own
  right, so the shortest batch is the one that governs.
- The batch count itself has a limit, because each additional run is
  another ambient the population was conditioned in, and the changeover
  between runs has one for the same reason.
- The chamber runs inside a band around ambient while the devices sit
  there. A volume that drifts out of the band conditions the attachment
  by a route the examination afterwards does not account for.

## Workflow

1. Validate the entry policy first: completeness floor, ambient pressure
   band, residence dwell, batch limit and changeover cap. A band whose
   lower edge sits above its upper edge is refused rather than used.
2. Reconcile the loaded serials against the roster. Refuse a roster that
   repeats a serial -- it cannot say how many devices the lot holds --
   then name the missing, the foreign and the repeated separately rather
   than netting them off against each other.
3. Take the entry completeness from the reconciled count and the lot
   size, refusing a reconciled count larger than the lot.
4. Derive the batch schedule: devices accounted for, the shortest dwell
   any batch held, and the total chamber time including changeovers.
5. Check the batch sheets against the reconciled manifest, the shortest
   dwell against its floor, the batch count and changeover against their
   caps, and the pressure against its band. A value landing exactly on a
   floor passes; the comparison tolerance absorbs representation error
   and the floor does not move.
6. Report every finding, not the first, and close on one verdict: lot
   entry incomplete, foreign device in chamber, chamber entry deficient,
   or chamber entry accepted.

## Pitfalls

- Reconciling by count. Six in and six on the roster is equally true of
  a correct tray and of a tray with one device swapped for another lot's
  part, and only one of those produces a usable lot result.
- Netting a missing device off against a foreign one. They are two
  separate defects with two separate owners, and a net of zero closes
  both without anyone reading either.
- Loading the devices that were to hand and sentencing the lot. This
  clause asks for the whole population, so a convenient subset produces
  a pass that covers parts which never saw the chamber.
- Treating a repeated serial as a clerical slip. It means one physical
  part is represented twice and another is represented not at all, which
  is the swap case wearing a different label.
- Averaging the dwell across batches. The floor applies to each batch,
  so an over-long first run does not buy a short second one, and an
  average hides exactly the batch that failed.
- Splitting the lot across as many runs as the schedule needs. Each
  additional chamber run is another ambient, and past the batch cap the
  population is no longer one conditioned group.
- Letting the changeover stretch while a tray is swapped. The later
  batches then start from a different laboratory ambient than the first,
  and the examination cannot say which batch a drift came from.
- Comparing a derived share or dwell against its floor by bare
  arithmetic. Both come out of divisions and sums that land a few units
  in the last place either side of a limit on different hosts, so the
  comparison absorbs that error while the floor is never relaxed.

## Behavior contract (gate 3)

The policy validation, the serial reconciliation into entered, missing,
foreign and repeated groups, the lot entry completeness, the batch
residence schedule with its shortest dwell and total chamber time, the
batch and changeover caps, the ambient pressure band, the finding
inventory and the entry verdict are exercised by the gate 3 contract
test: scripts/test_e2008_blocking_diode_adherence_process.py against
scripts/e2008_blocking_diode_adherence_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_adherence_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
