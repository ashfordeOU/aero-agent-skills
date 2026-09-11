---
name: e10-ddp-mapping
description: "Use when convert a heritage programme's legacy design data pack onto the ECSS document set following the ECSS-E-ST-10C Annex R mapping guidance: validate each legacy item's disposition, confirm a carried-forward item names at least one recognized ECSS target document, confirm a retired item states why and claims no target, and walk the mapping in the opposite direction to find any owed ECSS document that no legacy content feeds. Trigger: ecss, e-st-10-system-scope, legacy-data-pack, annex-r-mapping, heritage-conversion, document-set, content-retirement, coverage."
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
  tags: [ecss, e-st-10-system-scope, legacy-data-pack, annex-r-mapping, heritage-conversion, document-set]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Legacy Data Pack Mapping (space-systems/ecss/e10-ddp-mapping)

Use when the task is to bring a heritage programme's existing design data
pack onto the ECSS document set, following the informative mapping
guidance of ECSS-E-ST-10C Annex R.

## Domain quick reference

- A heritage conversion loses content in two ways, and they are found by
  walking the mapping in opposite directions. Item-by-item finds content
  that was dropped. Document-by-document finds an owed ECSS document that
  nothing feeds. One walk cannot see the other's defect: every item can
  be mapped and a required document still end up empty.
- Every legacy item gets an explicit disposition. Retiring content is a
  legitimate outcome -- heritage packs carry material the ECSS set
  genuinely does not want -- but it is a decision that must be recorded,
  not an omission.
- A retired item carries a reason. Without one the conversion cannot be
  reviewed, because nobody can tell deliberate retirement from content
  that was simply missed.
- A retired item must claim no target. Content cannot be both carried
  forward and dropped; that combination means two people dispositioned
  the same item differently and neither saw the other.
- A carried-forward item must name at least one recognized target
  document. An unrecognized target is rejected outright rather than
  recorded, because it cannot be checked for coverage later.
- Annex R is informative. It guides the conversion; it does not relax the
  normative DRDs the target documents must still satisfy once populated.
- The retired fraction is worth reporting on its own. A conversion that
  retires most of a heritage pack may be correct, but it is a decision a
  reviewer should see stated rather than infer.

## Workflow

1. Confirm legacy item identifiers are present and unique.
2. Validate each item's disposition, and each target against the
   recognized ECSS document set.
3. For carried-forward items, confirm at least one target is named.
4. For retired items, confirm a reason is recorded and no target is
   claimed.
5. Collect the documents that receive content, then walk the owed
   document list and report each one nothing feeds.
6. Report the retired fraction alongside the findings.
7. The conversion is sound only when nothing was dropped without a
   reason and no owed document was left unsourced.

## Pitfalls

- Auditing the mapping only item-by-item. That proves nothing was
  dropped and says nothing about whether the ECSS set came out complete.
- Treating an unmapped item as implicitly retired. Retirement is a
  decision with a reason attached; silence is just lost content.
- Accepting an item marked retired that still lists a target, on the
  assumption one field is stale. Both were written by someone, and the
  disagreement is the finding.
- Recording a free-text target name. If it does not resolve to a
  document in the set, coverage can never be computed against it.
- Reading Annex R's informative status as permission to skip the target
  documents' own DRDs. The mapping says where content goes, not what the
  destination must contain.
- Reporting a high mapped-item count as success while a required
  document has no source at all.

## Behavior contract (gate 3)

The disposition validation, target validation, per-item mapping,
reverse coverage walk and retired-fraction logic is exercised by the
gate 3 contract test: scripts/test_e10_ddp_mapping.py against
scripts/e10_ddp_mapping_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_ddp_mapping.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
