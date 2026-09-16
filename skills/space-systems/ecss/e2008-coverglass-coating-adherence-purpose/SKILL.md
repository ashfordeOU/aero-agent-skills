---
name: e2008-coverglass-coating-adherence-purpose
description: "Use when a coated lot needs its post-conditioning bond defended. Determine what a coverglass coating adherence verification must establish once environmental conditioning is over, under ECSS-E-ST-20-08C clause 8.7.11.2.1: separate the bond a coater delivers from the bond an interface retains after moisture and temperature have worked on it, derive the mismatch shear and the margin it leaves against the declared strength, price what a detached area costs in transmission and in charge bleed, and confirm the check is scheduled after the conditioning rather than before it. Trigger: ecss, e-st-20-08c-clause-8-7-11-2-1, coverglass-coating-adherence-purpose, post-conditioning-coating-attachment, coating-interface-mismatch-shear-margin, coverglass-coating-detachment-optical-loss, adherence-check-sequence-after-conditioning."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-coating-adherence-purpose, post-conditioning-coating-attachment, coating-interface-mismatch-shear-margin, coverglass-coating-detachment-optical-loss, adherence-check-sequence-after-conditioning]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Coating Adherence Purpose (space-systems/ecss/e2008-coverglass-coating-adherence-purpose)

Use when the task is to state and defend why a coverglass coating is
checked for attachment to the glass body after environmental
conditioning under ECSS-E-ST-20-08C clause 8.7.11.2.1 -- which
conditionings make the check necessary, what it has to deliver, and
where in the sequence it has to sit to deliver it.

## Domain quick reference

- Every function the coating has -- the reflection it suppresses, the
  charge it bleeds, the ultraviolet it turns back -- exists only while
  the film is still attached. Attachment is a property of the
  interface, and the interface is the part of the article the
  deposition process never directly proves.
- The word the clause turns on is after. A coating adheres when it
  leaves the coater; that is what a coater is for. What the mission
  needs is whether it still adheres once water has reached the
  interface and once film and glass have pulled against each other
  across a temperature swing.
- The mismatch shear is derived, not measured: modulus times expansion
  mismatch times excursion, divided by one minus the Poisson ratio. The
  margin it leaves against a declared interfacial strength is the
  number the cycling case is argued on, and the direction of the swing
  does not change it.
- A detached patch is not a hole. It is bare glass, which still
  transmits, just less well than a coated face, so a detached area
  fraction prices out as a transmission the assembly retains rather
  than as an area it loses.
- Charge bleed fails differently from transmission. Transmission
  degrades in proportion to the detached area; the conductive path
  fails when the detachment breaks continuity across the face, which
  happens at a fraction the optical budget would have refused long
  before.
- A humidity soak, a thermal vacuum run or a long storage interval
  earns the check on its own. A temperature excursion earns it once it
  is wide enough that the mismatch shear is worth deriving.
- Four outcomes are distinct and none substitutes for another: the
  check is unnecessary, it is unplanned, it is planned in the wrong
  place in the sequence, or it is planned correctly and the numbers
  fall short.

## Workflow

1. Validate the purpose policy first: margin floor, detached-area
   ceiling, retained-transmission floor, the fraction at which the
   conductive path breaks and the excursion the check is wanted above.
   A conduction-break fraction under the optical ceiling is refused,
   because it would make the optical limit unreachable.
2. Group the declared conditionings, refusing an unrecognised one
   rather than ignoring it, and map each to what the adherence check
   feeds it. Append the shared objective whenever any is present.
3. Decide whether the verification is required at all: a moisture,
   vacuum or storage conditioning present, or an excursion at or above
   the threshold. An excursion landing exactly on the threshold earns
   the check; the comparison tolerance absorbs representation error and
   the threshold does not move.
4. Derive the mismatch shear, the margin of safety it leaves, the
   retained transmission at the declared detached fraction and whether
   the conductive path survives it. These are reported whatever the
   verdict, because they are what the check was wanted for.
5. Separate an unplanned verification from a missequenced one. A check
   with no conditioning ahead of it, and a check scheduled before the
   conditioning, are reported as themselves rather than folded into one
   another.
6. Judge the numbers only once the check is required, planned and
   correctly placed, and report every shortfall found -- margin,
   detached area, transmission and charge bleed -- not only the first.
7. Close on one verdict: verification not required, verification not
   planned, verification precedes conditioning, adherence margin
   shortfall, or coating adherence purpose established.

## Pitfalls

- Citing the coater's own adherence result. It is a real measurement of
  a bond that no longer exists in the state the mission will see, and
  the whole clause is about the difference.
- Quoting the detached area as a transmission loss. Bare glass still
  transmits, so the loss is the difference between the coated and the
  bare surface over that area, which is a much smaller number and a
  defensible one.
- Assuming charge control degrades with area. It does not; it survives
  intact until continuity breaks, and then it is gone, so an area-
  weighted estimate of it is wrong in both directions.
- Signing off the sequence because the check appears in it. Where it
  appears is the substance: ahead of the conditioning it answers a
  question about the coater.
- Treating a wide excursion as the only trigger. A humidity soak loads
  the interface chemically rather than mechanically, and it earns the
  check on its own at any excursion.
- Comparing a derived margin or transmission against its floor by bare
  arithmetic. Both are quotients and sums of floats that can land a few
  units in the last place either side of a limit, so the comparison
  absorbs that error while the floor itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, mismatch shear derivation, margin of safety,
retained transmission and its loss, the conductive path check, the
conditioning inventory and objective mapping, the requirement decision,
the sequence placement check and the purpose verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_coverglass_coating_adherence_purpose.py against
scripts/e2008_coverglass_coating_adherence_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_coating_adherence_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
