---
name: q6012-wafer-manufacturing-control
description: "Assess the process monitoring and wafer traceability a foundry holds while a microwave die lot is fabricated, per ECSS-Q-ST-60-12C clause 10.2.3: normalise the run record, confirm every mandatory monitored step carries a reading, place each reading in its control band, walk every wafer back through its lot to the mask set, and grade each excursion disposition. Refuses an inverted band, an unknown step, a wafer with two parents and a link cycle, and holds the lot rather than releasing it to acceptance measurement when the chain breaks. Use when a lot still in fabrication must be shown under control. Trigger: ecss, q-st-60-12c-clause-10-2-3, wafer-fabrication-process-monitoring, foundry-wafer-traceability-chain, wafer-control-band-excursion, mask-set-to-wafer-lineage, fabrication-lot-release-hold."
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
  tags: [ecss, q-st-60-12-wafer-manufacturing-control, q6012-wafer-manufacturing-control, wafer-fabrication-process-monitoring, foundry-wafer-traceability-chain, wafer-control-band-excursion, mask-set-to-wafer-lineage, fabrication-lot-release-hold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wafer Manufacturing Control (space-systems/ecss/q6012-wafer-manufacturing-control)

Use when the wafers that will be diced into bare microwave dies are still on
the fabrication line, and the question is whether the foundry is holding the
process under monitoring and the wafers under traceability for the whole of
that time — not whether the finished wafer passes, which is the acceptance
measurement clause that follows this one.

## Domain quick reference

- Monitoring and traceability are two different obligations that fail in two
  different ways. A monitored process can still lose a wafer's identity, and a
  perfectly traced lot can still have run with a step nobody watched. Both are
  graded here, and a run is only released when both hold.
- A step with no reading is not an in-band step. The absent reading is the
  worst case of all, because a coverage count over the readings that exist
  reports a clean process no matter how many steps were skipped, so the
  mandatory steps are enumerated from the registry and the run is checked
  against them rather than summarised from itself.
- A reading is placed in its own band as a signed position, with the lower
  limit at -1 and the upper at +1. That makes readings from a thickness
  monitor, a dimension monitor and an electrical monitor comparable, and it
  makes a reading sitting exactly on a limit visible as an edge case rather
  than rounded into the comfortable interior.
- Traceability is a chain, not a label. Every wafer has to reach the mask set
  through its parent links, so a missing intermediate link is caught even when
  the wafer itself carries an identifier that looks complete. A node with two
  parents is a record defect, not an ambiguity to be resolved by picking one.
- An excursion is closed by a disposition with a record behind it. A
  disposition still under review is an open item; counting it as closed is how
  a lot reaches acceptance with an unresolved process deviation inside it.

## Workflow

1. Normalise the run record, refusing an unknown key so a misspelt field
   cannot silently drop an obligation, and refusing an inverted control band,
   a duplicate reading, a duplicate wafer and a node given two parents.
2. Enumerate the mandatory monitored steps from the registry and report the
   ones the run carries no reading for as unmonitored, not as in band.
3. Place each reading in its band, reporting below-band, above-band, on the
   band edge or in band, and keep the signed position alongside the verdict.
4. Walk every wafer up its parent links to the mask set, refusing a cycle
   rather than looping, and report each wafer whose chain breaks first.
5. Grade every excursion: open if still under review, unsupported if closed
   with no record reference, and out of place if raised at an unmonitored step.
6. Report the monitored and traceable fractions with the findings, and hold
   the lot rather than releasing it to acceptance measurement when any stand.

## Pitfalls

- Computing the in-band fraction over the readings present. A run with two of
  five mandatory steps monitored and both in band reports as fully in control;
  the denominator has to be the registry, never the record.
- Reading an on-limit value as comfortable. A value that lands exactly on a
  control limit is a decision point, and rounding it inward is how a drifting
  process reaches the last wafer before anyone raises it.
- Treating a wafer identifier as traceability. The identifier is the start of
  the chain; a wafer whose lot link is missing is untraceable no matter how
  well formed its own number looks.
- Resolving a two-parent node by picking a parent. Two parents means the
  fabrication records disagree, and choosing one produces a lineage that is
  clean on paper and wrong in fact.
- Counting an under-review excursion as dispositioned. Under review is the
  absence of a disposition, and a lot released on that basis carries an open
  process deviation into acceptance.

## Behavior contract (gate 3)

The run normalisation, mandatory monitor coverage, band placement with the
edge case, parent-link traceability with cycle refusal, excursion grading and
the release-or-hold disposition are exercised by the gate 3 contract test:
scripts/test_q6012_wafer_manufacturing_control.py against
scripts/q6012_wafer_manufacturing_control_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_wafer_manufacturing_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
