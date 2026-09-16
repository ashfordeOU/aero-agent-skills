---
name: e2008-sca-rear-contact-defects
description: "Use when a rear contact has been inspected and the deposits outside the welding area need grading. Assess the drops and spatter found outside the rear welding area of a solar cell assembly against the size allowed for their kind, under ECSS-E-ST-20-08C clause 6.4.3.1.8: place each deposit by its own footprint rather than by its centre, so one reaching across a welding boundary is graded as the outside deposit it partly is, compare diameter and standoff height with the allowance for a drop or for spatter, roll the outside deposits up into the governed rear area they cover, and refuse a layout whose welding areas leave no governed area to grade at all. Trigger: ecss, e-st-20-08c, clause-6-4-3-1-8, solar-cell-rear-contact-deposits, rear-welding-area-exclusion, weld-drop-size-limit, weld-spatter-size-limit, rear-contact-standoff-height."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-rear-contact-defects, solar-cell-rear-contact-deposits, rear-welding-area-exclusion, weld-drop-size-limit, weld-spatter-size-limit, rear-contact-standoff-height]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- SCA Rear Contact Defects (space-systems/ecss/e2008-sca-rear-contact-defects)

Use when the task is the rear contact screen of ECSS-E-ST-20-08C clause
6.4.3.1.8 -- grading the weld drops and spatter that landed outside the
designated welding area of a solar cell assembly against the size
permitted for them there.

## Domain quick reference

- The welding area is the exemption, not the subject. Material inside it
  is governed by the welding rules for that area; this clause governs
  what landed everywhere else, so the first question about any deposit
  is where it sits rather than how big it is.
- A deposit sits where its footprint sits. Grading by the centre alone
  lets a wide drop centred just inside a welding boundary escape the
  clause while most of it lies on governed metallisation, so the
  footprint decides and a deposit reaching across the boundary is graded
  as an outside one.
- Two sizes fail differently. Diameter consumes rear area the assembly
  needs for bonding; standoff height decides whether the cell still lies
  flat on its substrate, so a small deposit standing proud can be the
  worse of the two and a single size number hides it.
- A drop and spatter are not the same article. Spatter is the fine
  scatter thrown clear of the weld and is held to a tighter size than a
  drop that has run, so the allowance is read per kind.
- Individually acceptable is not collectively acceptable. Many deposits
  each inside their own allowance still cover governed rear area, and
  the covered fraction is what catches a process throwing consistently.
- A layout whose welding areas cover the whole rear face governs nothing.
  Grading it returns a clean result that means nothing at all, so the
  layout is refused rather than graded.
- Overlapping welding areas cannot be subtracted twice. The governed
  area is sized once, from a layout whose areas do not intersect.

## Workflow

1. Validate the limit set first: per-kind diameter and standoff
   allowances, the covered-area fraction and the review margin. A kind
   permitted at no diameter cannot carry a standoff allowance.
2. Read the rear face and its welding areas, refusing an area that runs
   off the face, an area overlapping another, and a layout that leaves
   no governed area, then size what the clause actually governs.
3. Take each deposit as a footprint on that face, rejecting an
   unrecognised kind, a repeated deposit identifier or a footprint that
   reaches past the rear face.
4. Place the footprint: wholly inside a welding area and it is exempt;
   reaching across a boundary or clear of every area and it is governed.
5. Grade each governed deposit on diameter and on standoff height
   against the allowance for its kind, banding an overrun inside the
   review margin as a referral and one past it as a rejection.
6. Total the governed footprints against the governed rear area, band
   that fraction the same way, and close on the worst verdict with the
   exempt, straddling and not-accepted deposits named.

## Pitfalls

- Grading a deposit by its centre coordinate. It is the cheapest test to
  write and it exempts exactly the deposits that most need grading.
- Reading one size allowance for both kinds. Spatter at a drop's
  allowance passes a screen it should not have reached.
- Checking diameter and forgetting standoff. A deposit that covers
  almost nothing can still hold the cell off its substrate.
- Closing on the largest deposit alone. A rear face peppered with
  in-size deposits fails on covered area while every single record looks
  acceptable.
- Sizing the governed area from overlapping welding areas. The overlap
  is subtracted twice, the governed area comes out small, and the
  covered fraction comes out large for no physical reason.
- Comparing a footprint edge with a welding boundary by bare arithmetic.
  A deposit whose edge lands exactly on the boundary can evaluate a few
  units in the last place outside it, so the comparison absorbs that
  representation error while the boundary itself stays untouched.

## Behavior contract (gate 3)

The limit-set validation, the governed-area sizing, the footprint
placement against the welding boundary, the per-kind diameter and
standoff banding, the covered-fraction rollup and the worst-verdict
close are exercised by the gate 3 contract test:
scripts/test_e2008_sca_rear_contact_defects.py against
scripts/e2008_sca_rear_contact_defects_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_rear_contact_defects.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
