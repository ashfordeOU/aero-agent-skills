---
name: e7041-managing-the-diagnostic-parameter-report-storage
description: "Model the diagnostic parameter report storage-control configuration of the on-board storage and retrieval service under ECSS-E-ST-70-41C clause 6.15.4.6 and what it costs. Use when the task is which diagnostic reports each packet store writes down and how fast they fill it: adding and deleting diagnostic structure identifiers per store and application process, refusing an identifier that process never defined, resolving an all-structures wildcard, summing size over collection interval into an octet rate, deriving a time to fill, and naming selections whose generation is switched off. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, diagnostic-storage-control, diagnostic-structure-storage-selection, packet-store-fill-rate, packet-store-time-to-fill, dormant-diagnostic-storage-selection."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-managing-the-diagnostic-parameter-report-storage, diagnostic-storage-control, diagnostic-structure-storage-selection, packet-store-fill-rate, packet-store-time-to-fill, dormant-diagnostic-storage-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Diagnostic Parameter Report Storage Control (space-systems/ecss/e7041-managing-the-diagnostic-parameter-report-storage)

Use when the task is the diagnostic parameter report storage-control
configuration of ECSS-E-ST-70-41C clause 6.15.4.6 -- the per-structure
selection that decides which diagnostic reports each packet store
writes down, and the fill rate that selection commits the store to.

## Domain quick reference

- The configuration is keyed three deep: packet store, then
  application process, then diagnostic structure identifier, with an
  all-structures wildcard available at the process level.
- A structure identifier means something only inside the process that
  defined it, and every diagnostic structure carries its own
  collection interval and its own report size. Those two numbers are
  what make this clause different from its housekeeping neighbour.
- Diagnostic structures are sampled fast, because that is what they
  are for. The useful question about a selection is therefore not
  whether it is stored but how long the store it went into lasts.
- Price a selection as size divided by collection interval. The rates
  of a store's selections add; the store capacity divided by that sum
  is the time it takes to fill. Against the interval between ground
  retrievals, that says whether the selection silently costs history.
- A wildcard is priced by resolving it against the definitions that
  exist now, not by an expansion stored when it was set. A structure
  defined later is stored and costs octets from that moment.
- A structure whose generation is switched off is dormant, not stale.
  It costs nothing today and must not be pruned: enabling generation
  converts the whole dormant set into octets per second at once, and
  a fill time computed without it is the number that surprises an
  operator mid-campaign.
- The stores are priced independently. One store filling in seconds
  says nothing about the store beside it, and the assessment has to
  name which store is over budget rather than the configuration.

## Workflow

1. Validate each item and each structure definition: a named packet
   store, a process in range, an identifier in range, a positive
   collection interval, a positive report size, a boolean generation
   state.
2. Reject an undefined packet store, then a process with no
   diagnostic definitions, then an identifier that process never
   defined.
3. Apply the add and delete rules: wildcard clears what it subsumes,
   a specific identifier under a wildcard is rejected, a wildcard is
   never partially deleted, capacity is a per-item rejection.
4. Resolve each store's selections against the current definitions,
   turning a wildcard into the identifiers defined right now.
5. Price each resolved selection -- zero while its generation is off
   -- and sum the rates per store.
6. Divide capacity by the rate for the time to fill; a store taking
   nothing never fills, and that is a verdict, not a division.
7. Compare each fill time against the retrieval period, name the
   stores that fill first, and list the dormant selections alongside
   so the reader can see the cost that is waiting.
8. Report packet store, then process, then identifier, sorted.

## Pitfalls

- Pricing a dormant selection at its nominal rate. Every store then
  looks over budget and the real ones stop being believed.
- Pruning a dormant selection as though it were stale. Its structure
  still exists; only its generation is off, and deleting it loses the
  configuration the campaign was set up with.
- Expanding a wildcard into today's identifiers and pricing that
  snapshot. The structure defined next week is stored and unpriced.
- Reporting one fill time for the configuration. The stores have
  different capacities and different selections, and the mean is true
  of none of them.
- Dividing by a zero rate to get infinity. A store nothing writes into
  has no fill time, and printing one invites a comparison that reads
  as a pass.
- Comparing a fill time against a retrieval period with a strict test
  when the two are meant to be equal. Both sides come from float
  division; compare them to a tolerance.

## Behavior contract (gate 3)

The item and definition validation, the add and delete rules, the
wildcard resolution, the per-structure and per-store octet rates, the
dormant-selection list, the time to fill and the per-store budget
verdict are exercised by the gate 3 contract test:
scripts/test_e7041_managing_the_diagnostic_parameter_report_storage.py
against
scripts/e7041_managing_the_diagnostic_parameter_report_storage_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_managing_the_diagnostic_parameter_report_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
