---
name: q60-class-1-component-traceability
description: "Maintain an unbroken identity trail for class 1 EEE parts from goods receipt through storage and kitting into finished assemblies, under ECSS-Q-ST-60C clause 4.5.4: link every issue and every assembly back to the receipt record that owns the lot, reconcile received quantity against issued, scrapped and remaining, reject an assembly that consumed a lot never issued to it, detect a storage bin that mixed two lots into one identity, flag a lot past its storage limit, and trace forward from a lot to the assemblies it reached. Use when a lot must be traced into hardware or an assembly back to its lots. Trigger: ecss, q-st-60c, class-1-eee-traceability, receipt-to-assembly-trail, lot-quantity-reconciliation, mixed-lot-bin-detection, forward-lot-trace, backward-assembly-trace."
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
  tags: [ecss, q-st-60c-eee-components-scope, q60-class-1-component-traceability, class-1-eee-part, eee-receipt-to-assembly-trail, eee-lot-quantity-reconciliation, mixed-lot-bin-detection, eee-lot-forward-and-backward-trace]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Component Traceability (space-systems/ecss/q60-class-1-component-traceability)

Use when the task is the traceability step of ECSS-Q-ST-60C clause 4.5.4
for an EEE part procured to the highest assurance class — showing that
every part in a finished assembly can be named back to the lot, the
manufacturer and the receipt record it came from, and that every part
received can be found again.

## Domain quick reference

- Traceability is a property of the records, not of the parts. The
  receipt record owns the identity: the lot, the part number, the
  manufacturer, the date code and the certificate it arrived with. An
  issue or an assembly that cannot reach back to one of those records is
  carrying a part with no identity, whatever the label on the bag says.
- The trail is only as good as its weakest link, and the weak link is
  usually kitting. Stores knows what it received and manufacturing knows
  what it fitted; what is routinely missing is the record that ties one
  particular issue to one particular assembly.
- Quantities are the cheapest test of the trail. Everything received is
  either issued, scrapped or still on the shelf, so the three must add
  back to what arrived. A shortfall means parts left the lot without a
  record, and that is the failure the clause exists to prevent.
- An assembly that consumed a lot never issued to it is a harder break
  than a miscount: the parts are in flight hardware and the paperwork
  says they came from somewhere else, so neither the lot nor the
  assembly can be trusted until it is resolved.
- One bin holding two lots of the same part number destroys both
  identities at once, and it is invisible in a stores total because the
  count still looks right. It has to be detected structurally, by
  grouping bins and part numbers.
- Storage limits do not break identity but they do break the evidence
  behind it. A lot held past its limit still knows what it is; what it
  no longer has is current solderability evidence, so it is reported
  separately rather than lumped in with a broken chain.
- Both directions are asked for in practice. A failure investigation
  traces forward from a suspect lot to every assembly it reached; an
  acceptance review traces backward from one assembly to every lot it
  drew on.

## Workflow

1. Validate every receipt record for the full identity set, and reject a
   lot owned by more than one receipt.
2. Validate the issue records and sum the issued quantity per lot,
   raising a finding for any issue that draws on a lot no receipt owns.
3. Check every assembly's consumption against the issues actually made
   to it, and list any consumption that was never issued.
4. Group receipts by bin and part number and list the bins that merged
   two lots.
5. Reconcile each lot: received against issued, scrapped and the stores
   count, using the derived remainder only when no stores count was
   supplied.
6. Compare each lot's storage age with its limit, treating a lot sitting
   exactly on the limit as still inside it.
7. Decide a verdict per lot, run the forward trace to the assemblies it
   reached, and report the traceable and untraceable quantities with
   every finding.

## Pitfalls

- Treating a bag label as the identity. The label is a copy; the receipt
  record is the original, and a lot whose receipt record is missing a
  certificate reference is not traceable however well the bag is marked.
- Reconciling with a derived remainder and calling it balanced. Deriving
  the shelf count from the other three numbers makes the arithmetic
  close by construction and hides exactly the shortfall you were looking
  for; use the stores count when there is one.
- Checking only that an assembly's lots exist. The test is whether those
  lots were issued to that assembly; a lot that exists but went to a
  different build is still an unsourced part.
- Missing the mixed bin. Two lots of one part number in one location
  reconcile perfectly at the total level and cannot be told apart at the
  point of issue.
- Reading a storage overrun as a broken chain. The identity is intact;
  it is the solderability evidence that has lapsed, and conflating the
  two sends the lot to the wrong disposition.
- Building only the backward trace. The forward trace is what an alert
  or a failure investigation needs, and it has to work from the same
  records rather than a separate spreadsheet.

## Behavior contract (gate 3)

The receipt identity validation, issue and assembly linking, unsourced
consumption detection, mixed-bin grouping, quantity reconciliation,
storage-limit comparison, per-lot verdict and the forward and backward
traces are exercised by the gate 3 contract test:
scripts/test_q60_class_1_component_traceability.py against
scripts/q60_class_1_component_traceability_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_component_traceability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
