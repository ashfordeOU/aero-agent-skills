---
name: q6012-die-packaging-and-storage
description: "Evaluate the carriers, seal and store conditions holding a bare die batch between delivery and assembly, per ECSS-Q-ST-60-12C clause 10.2.5: validate the arrangement, score the mechanical, moisture, electrostatic and environmental barriers, take the weakest as the protection actually given, track out-of-seal floor life in whole days, and pair every finding with the action that restores it. Refuses an unknown carrier or seal, a fractional day count and inverted store limits. Use when dies are waiting in stores and someone has to say whether they may still be built. Trigger: ecss, q-st-60-12c-clause-10-2-5, bare-die-carrier-protection, die-moisture-barrier-seal, die-out-of-seal-floor-life, die-store-temperature-humidity, die-electrostatic-dissipative-carrier."
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
  tags: [ecss, q-st-60-12-die-packaging-and-storage, q6012-die-packaging-and-storage, bare-die-carrier-protection, die-moisture-barrier-seal, die-out-of-seal-floor-life, die-store-temperature-humidity, die-electrostatic-dissipative-carrier]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Die Packaging And Storage (space-systems/ecss/q6012-die-packaging-and-storage)

Use when accepted bare dies are sitting in stores with an assembly still some
way off, and the question is whether the way they are packed and kept will
still leave them usable when that assembly comes — the protection the package
would normally have given them has to be supplied by the carrier, the seal and
the store instead.

## Domain quick reference

- A bare die arrives without the three things its package used to provide:
  mechanical protection, a moisture barrier, and an electrostatic path to
  ground. Storage has to replace all three, and each one fails on its own
  terms, so they are scored separately rather than rolled into one number.
- Protection is the weakest barrier, not the average of the barriers. A gel
  pack in an unsealed box is an unsealed box, and averaging a strong carrier
  against a missing seal produces a comfortable middling score for an
  arrangement that will ruin the batch.
- A seal is only as good as what is inside it. A barrier bag with no desiccant
  is a bag, and a bag with no humidity indicator cannot be told from a bag
  that was breached three months ago, so both are graded against what the seal
  type is expected to carry.
- Floor life is counted in whole days, deliberately. The question of whether a
  batch whose floor life is exactly spent needs a bake has one answer, and
  making it a floating-point comparison invites a different answer on a
  different machine.
- A finding without an action is not useful in a stores context. Every barrier
  that has failed is reported with the specific thing that restores it, so a
  recoverable batch is separated from an unrecoverable one.

## Workflow

1. Validate the arrangement: known carrier and seal tokens, a whole-day floor
   life and exposure count, a humidity between nought and a hundred, a store
   temperature band that is not inverted, and no unknown keys.
2. Score the mechanical barrier from the carrier and the electrostatic barrier
   from whether that carrier is dissipative at all.
3. Score the moisture barrier from the seal type, reduced when the desiccant
   the seal is expected to hold is absent and again when the humidity
   indicator is absent; lift it for a batch that is not moisture sensitive.
4. Score the environmental barrier as the worse of the store temperature and
   the store humidity against their declared limits.
5. Take the weakest barrier as the protection index and name it, breaking ties
   on the declared barrier order so the answer is reproducible.
6. Report findings, the ordered actions that restore each failed barrier, the
   remaining floor life, and whether the batch goes to assembly as it stands.

## Pitfalls

- Averaging the barrier scores. The average of a good carrier and an absent
  seal reads as adequate protection, and the batch is lost to moisture while
  the score said it was fine.
- Treating the bag as the moisture barrier. The bag plus fresh desiccant plus
  a readable indicator is the moisture barrier; any one missing and the batch
  has less protection than the paperwork claims.
- Counting floor life in fractional days. The boundary case is the one that
  matters and it is the one a floating-point day count decides differently on
  different machines.
- Forgetting the electrostatic path. A non-dissipative tray is the one failure
  here with no partial credit; it is not a degraded barrier, it is an absent
  one, and the batch does not go to assembly until it is replaced.
- Reporting a verdict with no route back. Most stores findings are recoverable
  by a bake, a re-bag or a transfer, and a bare inadequate scraps material
  that a named action would have saved.

## Behavior contract (gate 3)

The arrangement validation, the four barrier scores, the weakest-barrier
protection index with its named governing barrier, the whole-day floor life
and bake decision, and the findings paired with restoring actions are
exercised by the gate 3 contract test:
scripts/test_q6012_die_packaging_and_storage.py against
scripts/q6012_die_packaging_and_storage_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_die_packaging_and_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
