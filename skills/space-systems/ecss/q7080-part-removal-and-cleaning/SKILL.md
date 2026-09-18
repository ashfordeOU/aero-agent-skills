---
name: q7080-part-removal-and-cleaning
description: "Evaluate the removal, depowdering and cleaning of an additively manufactured part. Use when unfused powder may still be inside it: weigh the part against its nominal solid mass and read the excess as trapped powder, grade every internal passage on bore against powder size, length against bore and the number of open ports it can flush through, size the cut that frees it from the plate against kerf, distortion and datum uncertainty, confirm stress relief came first, grade cleaning residue per unit area, then take the worst and name it. Trigger: ecss, q-st-70-80-additive-manufacturing, am-part-depowdering, am-internal-channel-powder-removal, am-trapped-powder-mass-balance, am-build-plate-part-removal, am-post-build-cleaning-residue."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-part-removal-and-cleaning, am-part-depowdering, am-internal-channel-powder-removal, am-trapped-powder-mass-balance, am-build-plate-part-removal, am-post-build-cleaning-residue]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Part Removal and Cleaning (space-systems/ecss/q7080-part-removal-and-cleaning)

Use when the post-process clause of ECSS-Q-ST-70-80 is the task: deciding
whether an additively manufactured part came off the build plate the way
it had to, whether the unfused powder has actually left it, internal
passages included, and whether what the cleaning recipe left behind is
inside the limit.

## Domain quick reference

- Powder that never left the part is mass, a contamination source and,
  in a fluid passage, a blockage. None of that is visible from the
  outside, so the decision cannot be made on an external inspection.
- The mass balance is the only measurement that sees powder a borescope
  cannot reach. The excess of the as-removed mass over the nominal solid
  mass is trapped powder, graded as a fraction so a small part and a
  large one are judged the same way.
- A part lighter than its nominal mass by more than weighing scatter is
  not a very clean part. It means the mass record and the solid model
  disagree, and nothing can be graded until that is resolved.
- A passage frees itself only if three things hold at once: the bore is
  wide against the powder it has to pass, the length is short against
  that bore, and there is more than one opening for the powder to leave
  by. A bore only a few powder diameters wide bridges rather than flows,
  and a blind pocket has no path out at all whatever its bore.
- A long passage with two openings is a flushing problem, which the
  process can solve with a declared route. A long passage with one
  opening is a design problem, which it cannot.
- The cut that frees the part consumes material, and the part moves the
  instant the plate constraint goes. Kerf, distortion and datum
  uncertainty all come out of the same declared allowance, and a saw
  takes an order more material than a wire.
- Cutting before stress relief releases the as-built residual stress as
  distortion, and no later operation puts the geometry back.
- Cleaning residue is graded per unit of cleaned area. The same
  milligrams on a small part and a large one are different results, and
  a bare mass hides which one happened.

## Workflow

1. Take the mass balance first: as-removed mass against nominal solid
   mass, excess as trapped powder, expressed as a fraction of nominal
   and graded against the declared allowance. Refuse a shortfall beyond
   weighing scatter as an inconsistent record.
2. For every internal passage, form the bore-to-powder ratio and the
   length-to-bore ratio, count the open ports, and grade the three
   together so a long passage with two exits reads as a flushing route
   to declare and a long blind one reads as a reject.
3. Size the removal cut: kerf for the declared method plus the distortion
   expected on release plus the datum uncertainty of the fixture, all
   against the allowance actually left on the part.
4. Confirm stress relief preceded the cut; a part freed before it is an
   immediate finding whatever the allowance was.
5. Grade the cleaning residue per unit area, calling out a result that
   sits in the top of the limit as a recipe with no margin rather than
   as a pass.
6. Take the worst of the mass balance, the passages, the removal and the
   cleanliness as the verdict, name the characteristic that drove it and
   the passage identifiers sitting at that level.
7. Where a ratio or an allowance should land exactly on its limit, grade
   it with the tolerant comparison, because a sum of kerf, distortion and
   datum does not reproduce the hand-written total bit for bit.

## Pitfalls

- Judging depowdering by looking into the ports. A borescope sees the
  first bend and nothing past it, so a part that looks clean at both
  openings can still be carrying powder in the middle of the run.
- Grading trapped powder as a bare mass. Two grams in a small bracket
  and two grams in a large manifold are different results, and only the
  fraction of nominal mass separates them.
- Treating a bore that is merely larger than the powder as drainable.
  Powder bridges an opening several diameters wide, so the ratio, not
  the clearance, is the quantity that decides it.
- Counting a blind pocket as a short passage. Length is not the problem
  there; the absence of a second opening is, and it stays a reject at
  any aspect ratio.
- Leaving only the kerf on the part. The distortion that appears when
  the plate constraint is released and the uncertainty of the fixture
  datum come out of the same allowance, and together they are usually
  larger than the cut.
- Cutting the part free before stress relief to save a furnace cycle.
  The geometry moves on release and the later soak cannot recover it.
- Reporting a cleaning result as a pass when it sits just inside the
  limit. A recipe with no margin passes this part and fails the next one
  for reasons nobody recorded.

## Behavior contract (gate 3)

The mass balance, passage bore and aspect grading, port counting,
removal allowance budget, stress-relief precedence and per-area
cleanliness are exercised by the gate 3 contract test:
scripts/test_q7080_part_removal_and_cleaning.py against
scripts/q7080_part_removal_and_cleaning_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_part_removal_and_cleaning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
