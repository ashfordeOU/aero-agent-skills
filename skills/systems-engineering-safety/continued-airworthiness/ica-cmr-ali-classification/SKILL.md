---
name: ica-cmr-ali-classification
description: "Use when you must classify certification maintenance items: sort each candidate from certification into airworthiness limitation items (life-limited parts, damage-tolerance inspections, fuel-tank flammability checks), certification maintenance requirements, or routine scheduled maintenance using a fixed certification-driver rule table, then compute the ALS coverage of a maintenance program as matched required items over the total required and check per-item interval compliance against the type-certificate ALS maximum intervals. Produces a per-item verdict with rationale, class counts, the ALS coverage fraction, and the non-compliant and missing ALS item lists. Trigger: airworthiness limitations section, ALS coverage, certification maintenance requirement, life-limited part, damage-tolerance inspection, fuel-tank flammability, instructions for continued airworthiness."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: continued-airworthiness
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: continued-airworthiness
  tags: [ica-cmr-ali-classification, airworthiness-limitation-items, certification-maintenance-requirements, als-coverage, life-limited-part-review, instructions-for-continued-airworthiness]
  version: 0.1.0
  author: AeroSkills
---

# ICA/CMR/ALI Classification (systems-engineering-safety/continued-airworthiness/ica-cmr-ali-classification)

Use when certification maintenance items must be sorted into the three
maintenance-program families of the continued airworthiness world:
airworthiness limitation items (ALI), certification maintenance
requirements (CMR) and routine scheduled maintenance, and when the
maintenance program must then be checked against the airworthiness
limitations (ALS) of the type certificate. This leaf implements the
fixed certification-driver rule table in pure Python, stdlib only: the
driver on each item decides its family, ALS coverage counts the
canonical ALS items present in the program, and interval compliance
flags ALS items whose program interval exceeds the type-certificate
maximum. It pairs with the routine-program derivation leaf in this pack,
which supplies the MSG-3 context that the non-mandatory items sit in.

## Domain quick reference

- Item shape: every candidate is a tuple (name, driver, interval),
  where driver is one of ALLOWED_DRIVERS = ("LLP", "DT", "FF", "CMR",
  "ROUTINE"): life-limited part, damage-tolerance inspection,
  fuel-tank flammability check, certification maintenance requirement,
  routine task.
- Classification rule: driver in ALI_DRIVERS = ("LLP", "DT", "FF") ->
  kind ALI (mandatory, published in the Airworthiness Limitations
  Section of the ICA); driver == "CMR" -> kind CMR (mandatory and
  authority-controlled); driver == "ROUTINE" -> kind routine
  (non-mandatory, MSG-3 program context).
- ALS coverage: matched / required, where required is the number of
  canonical items in ALS_MAX_INTERVALS (three for the anchor program)
  and matched is how many of those canonical names appear in the
  program. Coverage is presence-based: it counts the canonical name,
  whatever driver the item was entered with.
- Interval compliance: applies only to canonical items whose kind is
  canonical; an item is compliant when its program interval is at most
  its ALS maximum. Intervals keep the item's own unit.
- Anchor type-certificate ALS maxima (ALS_MAX_INTERVALS): APU shaft LLP
  20000 flight cycles, wing spar DT inspection 4000 flight cycles,
  fuel-tank flammability check 12000 flight hours.
- Regulatory frame: FAR 25.1529 makes the ICA with its airworthiness
  limitations mandatory material, and the fuel-tank flammability item
  sits in the FAR 25.981 flammability context; both are named only, not
  reproduced.

## Workflow

1. Collect the candidate items as (name, driver, interval) tuples from
   the certification data, one tuple per maintenance or limitation
   item.
2. Classify each item with classify_item(name, driver, interval) and
   record the per-item kind ALI, CMR or routine with its rationale.
3. Run the whole program through ica_cmr_ali_review(items) to get
   per_item verdicts, class_counts, the ALS coverage dict, the
   non_compliant names and the missing_als_items names in one call.
4. Report the ALS coverage fraction from the coverage dict, matched
   over required, as the headline program metric.
5. Spot-check any single canonical item with
   interval_compliance(name, interval) when a supplier interval needs
   an individual verdict against its ALS maximum.
6. Reconcile the outputs: class counts must sum to the number of
   items, and coverage_fraction must equal matched / required exactly.
7. Confirm the deterministic checks with the contract test
   scripts/test_ica_cmr_ali_classification.py.

## Worked example

Reference program: (APU shaft LLP, LLP, 18000), (wing spar DT
inspection, DT, 4500), (cabin interior check, ROUTINE, 2000),
(hydraulic pump CMR, CMR, 3000).

- classify_item on each entry returns kind ALI for the APU shaft LLP
  and the wing spar DT inspection, kind routine for the cabin interior
  check, and kind CMR for the hydraulic pump CMR, each with a driver
  rationale.
- class_counts from ica_cmr_ali_review: ALI 2, CMR 1, routine 1; the
  counts sum to the 4 submitted items.
- ALS coverage: matched 2 (APU shaft LLP, wing spar DT inspection) of
  required 3, coverage_fraction 0.6666667 (0.6667 within 1e-4).
- Interval compliance: APU shaft LLP at 18000 flight cycles is at or
  under the 20000 maximum, compliant; wing spar DT inspection at 4500
  flight cycles exceeds the 4000 maximum, non-compliant.
- Output lists: non_compliant = ["wing spar DT inspection"];
  missing_als_items = ["fuel-tank flammability check"].

## Verification

- Confirm classify_item("APU shaft LLP", "LLP", 18000) returns kind
  ALI with a rationale naming the life-limited part driver.
- Confirm ica_cmr_ali_review on the worked example returns class
  counts ALI 2, CMR 1, routine 1 and coverage_fraction 0.6667.
- Confirm interval_compliance("wing spar DT inspection", 4500) returns
  compliant False with max_interval 4000.0.
- Confirm the identity checks hold: class counts sum to the item
  count, and coverage_fraction equals matched / required exactly.
- Confirm ValueError rejection of every non-physical input: an unknown
  driver (for example "MSG3"), a non-positive interval (for example
  -5), an empty item list in als_coverage, and a non-canonical name in
  interval_compliance.
- Confirm the module is deterministic: the same item list gives the
  same review dict on every run.
- Run the contract test offline: python3
  scripts/test_ica_cmr_ali_classification.py (33 tests,
  deterministic).

## Related leaves

- systems-engineering-safety/continued-airworthiness/
  in-service-safety-assessment: the field-experience review that later
  revises this program's items and routes corrective action.
- systems-engineering-safety/continued-airworthiness/
  msg3-maintenance-analysis: derives the routine scheduled program
  that the non-mandatory items of this leaf sit inside.
- systems-engineering-safety/certification/mmel-development: the
  operator dispatch-limits list that relaxes which failures may defer
  maintenance on this program.
- systems-engineering-safety/arp4754a/configuration-management: change
  control over the ALS pages when an item or interval is revised.

## Pitfalls

- Filing a CMR into the ALS: CMR items are mandatory and
  authority-controlled, but they are certification maintenance
  requirements, not airworthiness limitation items, and they do not
  belong in the Airworthiness Limitations Section; only the LLP, DT
  and FF certification drivers produce an ALI.
- Applying interval compliance to every item: interval_compliance is a
  canonical-item spot check and raises ValueError for a non-canonical
  name, while non_compliant in the review flags only canonical items
  whose kind is ALI; routine and non-canonical items are never
  interval-flagged.
- Reading coverage as a quality score: ALS coverage counts canonical
  names present in the program, whatever driver they carry, so an item
  entered with the wrong driver still counts as matched and must be
  caught by the per-item classification instead.
- Mixing units across maxima: the anchor maxima are labeled per item,
  flight cycles for the LLP and DT items and flight hours for the
  fuel-tank flammability check; comparing across units is meaningless.
- Inferring missing items from non_compliant: full ALS coverage needs
  every canonical item, so read missing_als_items directly; a program
  can be fully compliant on the items it has and still miss a required
  ALS item.
- Confusing this leaf with field review: deciding mandatory versus
  routine from certification drivers is this leaf's scope; later
  field-experience assessment and its corrective routing live in the
  in-service-safety-assessment sibling.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ica_cmr_ali_classification.py

The test covers the classification truth table (LLP, DT, FF to ALI;
CMR to CMR; ROUTINE to routine), ValueError rejection of unknown
drivers and non-positive intervals, the worked-example ALS coverage of
0.6667 within 1e-4 with class counts (2, 1, 1), compliant and
non-compliant interval cases at and above the ALS maxima, the
canonical-name ValueError, the counts-sum and coverage = matched /
required identities, determinism across runs, and exact documented
dict keys.

## Compliance

- Standards referenced, not reproduced: FAR 25.1529 (instructions for
  continued airworthiness with airworthiness limitations) and FAR
  25.981 (fuel-tank flammability) are named as context only;
  MSG-3 is named as the routine-program context; the rules above are
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
