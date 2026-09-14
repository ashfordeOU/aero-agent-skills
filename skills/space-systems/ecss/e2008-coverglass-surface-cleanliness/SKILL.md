---
name: e2008-coverglass-surface-cleanliness
description: "Use when a coverglass delivery has been examined for soiling and each item needs a dispositioned cleanliness verdict. Assess every delivered coverglass against the surface cleanliness requirement of ECSS-E-ST-20-08C clause 8.7.1.3.7: screen both optical surfaces for particulate, film, fingerprint and staining deposits, compute the permanent obscured-area fraction and the oversize particle count per surface, separate removable soiling from contamination that survives a clean, disposition each surface as accept, clean-and-reinspect, refer-for-review or reject, and hold the delivery lot open until both surfaces of every coverglass carry a record. Trigger: ecss, e-st-20-08c, clause-8-7-1-3-7, coverglass-optical-surface-cleanliness, coverglass-particulate-obscuration, coverglass-removable-soiling-screen, coverglass-post-clean-reinspection, coverglass-delivery-lot-completeness."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-surface-cleanliness, coverglass-optical-surface-cleanliness, coverglass-particulate-obscuration, coverglass-removable-soiling-screen, coverglass-post-clean-reinspection, coverglass-delivery-lot-completeness, solar-cell-assembly-optical-defects]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Surface Cleanliness (space-systems/ecss/e2008-coverglass-surface-cleanliness)

Use when the task is the delivery cleanliness screen of ECSS-E-ST-20-08C
clause 8.7.1.3.7 -- confirming that the coverglasses handed over carry no
soiling and no contamination on either of their optical surfaces, and
keeping the lot open until every one of them has been looked at on both
sides.

## Domain quick reference

- The screen is per item, per surface and exhaustive. A coverglass has an
  outer optical surface facing the environment and an inner one that ends
  up in the bond line against the cell, and the record count is compared
  against the declared lot size. A short record set leaves the lot open
  however clean the screened items were.
- The inner surface is the one that stops being inspectable. Once the
  assembly is built the bond line is closed, so a one-sided screen is not
  a finding that can be cleared later -- it is a finding that can never be
  cleared at all.
- Soiling and contamination are the same appearance and different
  findings. Soiling comes off: a particle, a handling film, a fingerprint.
  It is not a property of the glass, it contributes nothing to any
  permanent-obscuration allowance, and it sends the item back to be
  cleaned. Contamination is what survives the clean -- an etched stain, a
  baked residue, a deposit bonded into the coating -- and it stays in the
  optical path for the life of the array.
- Because soiling is curable, the cleaning does not close the item; the
  re-inspection after the cleaning does. A record carrying a clean
  instruction and no post-clean result is an open item, not a passing one,
  and residue that survived the clean is re-read as contamination.
- A permanent deposit is bounded on its own area first, so that one large
  stain cannot hide behind a generous cumulative figure.
- Small permanent deposits still accumulate. A cumulative obscured-area
  fraction per surface catches the coverglass that passed every
  single-deposit limit and is nevertheless hazy, and an oversize particle
  count catches the surface that is peppered rather than dirty.
- A particle is measured on diameter and its obscuration derived from it;
  a film, fingerprint or stain carries a declared area directly.

## Workflow

1. Take the declared coverglass count for the delivery and the inspection
   records. Reject a record set larger than the declared count, and report
   the shortfall when it is smaller.
2. For each coverglass, walk both optical surfaces. Note which of the two
   are present and carry the missing one through as an item finding.
3. On each surface, disposition every deposit: removable soiling goes to
   clean-and-reinspect, permanent contamination inside the single-deposit
   area allowance goes to review, and anything above it rejects.
4. Sum the permanent obscuration only, compare the fraction against the
   per-surface allowance, and count the permanent particles at or above
   the oversize diameter against the count allowance.
5. Apply the post-clean rule: soiling with no second look holds the
   surface open, a clean second look releases it, and residue found at the
   second look escalates to review.
6. Roll up: the worst surface verdict becomes the item verdict, the worst
   item verdict becomes the lot verdict, and the lot closes only when the
   record set is complete on both surfaces and nothing is outstanding.

## Pitfalls

- Screening the outer surface only. It is the one you can still see after
  the assembly is bonded, which is exactly why it is the one that does not
  need the record most.
- Sampling the lot. The clause asks for the delivered coverglasses, and a
  sampled screen reports a verdict the evidence does not support.
- Counting removable soiling toward the permanent obscuration allowance.
  That fails items that a clean would have released, and it buries the
  cumulative figure that exists to catch real haze.
- Closing an item on the cleaning instruction. The evidence of cleanliness
  is the post-clean re-inspection result, not the intent to clean.
- Treating residue that survived the clean as more soiling. It survived,
  so it is contamination and it belongs in front of a review.
- Accepting a surface because every deposit passed its own limit. The
  cumulative area fraction and the oversize particle count exist for
  exactly that case.
- Comparing an obscured fraction with an allowance by bare arithmetic. The
  fraction is a sum of derived areas divided by a measured area, so a
  surface exactly on the allowance can evaluate a few units in the last
  place above it; the comparison absorbs that representation error while
  the allowance stays untouched.

## Behavior contract (gate 3)

The per-deposit dispositioning, the removable-versus-permanent split, the
cumulative obscured-area fraction, the oversize particle count, the
post-clean re-inspection rule, the two-surface completeness rule and the
lot rollup are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_surface_cleanliness.py against
scripts/e2008_coverglass_surface_cleanliness_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_surface_cleanliness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
