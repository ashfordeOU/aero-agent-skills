---
name: q7003-applicability-and-alloys
description: "Determine whether a metal part may carry a black anodic coating with inorganic dyes under the ECSS-Q-ST-70-03C applicability clause. Use when an alloy, a product form, a surface or assembly condition or a drawing tolerance decides whether the black-anodizing route is open, needs a qualification programme, or is closed: categorize the alloy family from its designation and its copper and silicon content, find the entrapment sites and the faces that have to stay electrically conductive, derive the outward growth the specified thickness adds to a surface and to a diameter, compare that growth with the allowance, and report one verdict per part with the duties a conditional case carries. Trigger: ecss, q-st-70-03-black-anodizing-scope, black-anodizing-alloy-applicability, copper-bearing-alloy-qualification, anodic-coating-dimensional-growth, entrapment-risk-assembly, electrical-bonding-face-masking."
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
  tags: [ecss, q-st-70-03-black-anodizing-scope, q7003-applicability-and-alloys, black-anodizing-alloy-applicability, copper-bearing-alloy-qualification, anodic-coating-dimensional-growth, entrapment-risk-assembly, electrical-bonding-face-masking, black-anodize-part-condition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Black Anodizing — Applicability and Alloys (space-systems/ecss/q7003-applicability-and-alloys)

Use when the task is the applicability question of ECSS-Q-ST-70-03C --
deciding, before any bath is booked, whether a given part in a given
alloy and a given condition may be black anodized with inorganic dyes
at all, and what a conditional case owes before it may proceed.

## Domain quick reference

- The process is an anodic one, so it only has a substrate on
  aluminium and its alloys. A part in steel, titanium or a polymer is
  outside the process entirely, and no amount of qualification brings
  it in. That question is asked first because everything below it
  assumes an aluminium substrate.
- Inside aluminium the family decides how the coating grows. The low
  alloyed, manganese-bearing and magnesium-bearing wrought families
  take a dense coating that accepts an inorganic dye evenly. The
  copper-bearing and the high-silicon families grow a thinner, more
  porous and patchier coating, so they are open only through a
  qualification programme run on the actual alloy and temper rather
  than on the family.
- Composition overrides the family digit. A nominally open alloy whose
  copper or silicon content sits above the threshold behaves like the
  family it resembles chemically, not the one its designation places
  it in, so the threshold is applied to the analysed composition and
  can demote an otherwise open alloy on its own.
- A casting is a qualification case whatever its designation. The
  porosity that gives a casting its surface also gives the coating a
  substrate that varies from one part of a part to another, and an
  even black is exactly what that variation defeats.
- Condition matters as much as composition. An organic coating, a
  conversion coating or an earlier anodic layer has to be off the part
  before it enters the line, and a closed assembly that can trap bath
  chemistry stays out until it is vented or the parts are run loose.
- A black anodic coating is an electrical insulator. A face that has
  to stay conductive for bonding or grounding is either masked before
  the part enters the line or the part is not a candidate; discovering
  this after the coating is grown costs the coating.
- The coating grows outward as well as inward. Roughly half the
  thickness stands proud of the original surface, so a treated surface
  gains that half, an outside diameter gains twice it, and a bore or a
  slot loses twice it. A tolerance that cannot take that movement
  makes the part a non-candidate at the specified thickness even when
  the alloy is ideal.

## Workflow

1. Confirm the base metal is aluminium. Reject anything else at once
   rather than carrying it through the alloy logic, because a verdict
   built on a non-aluminium substrate is meaningless.
2. Categorize the alloy: read the family digit off the designation for
   a wrought product, treat every casting as a qualification case, and
   then apply the copper and silicon thresholds to the analysed
   composition so a nominally open alloy can still be demoted.
3. Take the arrival condition. Attach a strip duty to a painted,
   conversion-coated or previously anodized surface instead of
   assuming the line will find it.
4. Take the assembly state. Close out a closed or dissimilar-metal
   assembly; attach a drain-and-rinse duty to a vented one.
5. Take the surface function. An unmasked bonding or grounding face
   closes the part; a masked one carries the masking duty forward.
6. Derive the growth the specified thickness adds to the governing
   feature and compare it with the drawing allowance, treating a part
   that lands exactly on its allowance as acceptable.
7. Grade the specified thickness against the process band, then report
   one verdict per part, the reasons behind it, the duties it carries,
   and whether the whole batch is clear.

## Pitfalls

- Reading the family digit and stopping there. The digit is a
  registry convention, not an analysis; an alloy carrying copper above
  the threshold grows the same poor coating whatever family it was
  filed under, and an applicability answer that never looked at the
  composition has not asked the question the clause asks.
- Treating a casting as its wrought namesake. The two share a
  designation root and almost nothing that matters here, and a casting
  waved through on a wrought precedent is the classic source of a
  patchy, streaked black that no rework recovers.
- Quoting the coating thickness as the dimensional change. Only the
  outward part moves the surface, and on a diameter it moves twice, so
  a tolerance assessment built on the raw thickness is wrong in both
  directions at once and wrong by a factor of four on a bore.
- Leaving the bonding face to the shop. A masking requirement that
  never reached the process sheet becomes an insulated ground path
  found at integration, when the only remedy left is stripping and
  re-running a part that has already been coated.
- Calling a thin specification safe because it is conservative. The
  dye sits in the pores of the coating, so below the dyeable band
  there is nowhere for the colour to go and the part comes out grey
  however long it stays in the dye bath.

## Behavior contract (gate 3)

The alloy categorization, composition thresholds, condition and
assembly duties, bonding-face rule, growth arithmetic, thickness band
and batch verdict are exercised by the gate 3 contract test:
scripts/test_q7003_applicability_and_alloys.py against
scripts/q7003_applicability_and_alloys_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7003_applicability_and_alloys.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
