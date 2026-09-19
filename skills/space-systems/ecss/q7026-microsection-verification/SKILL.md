---
name: q7026-microsection-verification
description: "Evaluate a crimp microsection where cross-section examination is required. Use when a barrel has been sectioned, polished and examined and the compression inside it has to be graded: derive the compression ratio from the sectioned conductor area against the undeformed area, compare it with the band for that contact, count and size the voids, check the core strands deformed and not only the outer ones, measure the barrel wall at its thinnest, confirm the cut sits inside the crimp zone, and grade the sections taken against the lot and its setup changes. Trigger: ecss, q-st-70-26-crimping, crimp-microsection-compression-ratio, crimp-section-void-count, crimp-barrel-wall-thinning, crimp-section-plane-location, crimp-microsection-sample-frequency."
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
  tags: [ecss, q-st-70-26-crimping, q7026-microsection-verification, crimp-microsection-compression-ratio, crimp-section-void-count, crimp-barrel-wall-thinning, crimp-section-plane-location, crimp-microsection-sample-frequency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Microsection Verification (space-systems/ecss/q7026-microsection-verification)

Use when the Quality clause of ECSS-Q-ST-70-26 calls for cross-section
examination: grading the compression that actually happened inside the
barrel, on a sample that is destroyed to produce the evidence.

## Domain quick reference

- The section is the only direct view of the compression. Crimp height
  measures the outside of the barrel and pull-off measures the outcome;
  neither can see the strands, the voids or the wall.
- Compression is a ratio of two areas, the sectioned conductor against
  the undeformed area of the same strands, and it is two-sided. Too
  little and the strands are still round with gas paths between them;
  too much and the material has been driven past its limit and the
  strands are cut.
- Because it is a quotient of two measured areas, a compression ratio
  routinely lands a few units in the last place either side of a
  specified band edge, which is exactly the case the comparison has to
  absorb without moving the band.
- A void is not a small defect. It is a gas path in a joint that is
  supposed to be solid metal, and it is a place the cold weld did not
  form. Counted voids that nobody sized leave the area they occupy
  unknown.
- A correct area can hide a wrong crimp. If the outer strands flattened
  and the core stayed round, the total area passes and the middle of
  the bundle has no weld in it, so the deformed strand count is read
  separately from the area.
- Barrel wall thinning is a structural reading, not a cosmetic one. The
  thinnest wall in the section is where a crack opens under thermal
  cycling, long after every acceptance test has passed.
- Where the cut was taken decides whether anything else means anything.
  A section outside the crimp zone measured a barrel the die never
  closed on, and that is an invalid section, not a failing crimp: the
  crimp is re-sectioned rather than dispositioned.
- The programme has a rate. Sections are owed per quantity of crimps
  and per setup change, and a section that turned out invalid does not
  discharge the obligation it was taken against.

## Workflow

1. Validate the limits table: a two-sided compression band that does
   not start at zero, void count and void area allowances, a deformed
   strand fraction, a wall fraction above zero, and a crimp zone with
   real width.
2. Take the entry for the contact in hand, refusing an untabulated part
   rather than borrowing a neighbour's band.
3. Locate the cut first. A section plane outside the crimp zone makes
   everything else unplaceable, so the section is marked invalid and
   the crimp goes back to be re-sectioned.
4. Derive the compression ratio from the sectioned and undeformed
   areas, refusing a sectioned area larger than the undeformed one, and
   grade it against the band in both directions.
5. Count the voids against the count allowance and, where they were
   sized, against the area fraction of the bore. Counted but unsized
   voids leave the reading incomplete rather than passing.
6. Read the deformed strand count against the strand count, and the
   thinnest barrel wall against the nominal.
7. Roll the programme up: valid sections only against the rate the lot
   and its setup changes demanded, the compression range across the
   valid sections, and the sections that were not accepted by
   identifier.

## Pitfalls

- Treating a good crimp height as evidence of good compression. The
  height is the outside of the barrel and the section is the inside.
- Grading compression against a floor only. An under-compressed crimp
  has a perfectly acceptable-looking section until the ratio is
  compared with the ceiling as well.
- Comparing an area quotient with a band edge by bare arithmetic. The
  ratio is computed from two measured areas and will land a few units
  in the last place past a limit it was specified to meet, so the
  comparison absorbs that representation error while the band stays
  untouched.
- Reading total conductor area and stopping. An outer ring of flattened
  strands around a round core produces the right area and the wrong
  joint.
- Counting voids without sizing them. A count with no area says how
  many discontinuities there are and nothing about how much of the
  joint is missing.
- Leaving the barrel wall unmeasured because the conductor looked
  right. The wall is the part that fails later and never at acceptance.
- Dispositioning a crimp from a section taken outside the crimp zone.
  That section is about a piece of barrel nobody compressed, so it is
  invalid, and calling it a reject blames the crimp for the cut.
- Counting an invalid section toward the sectioning rate. The
  obligation it was taken against is still open.
- Reporting a programme result without the number of sections the lot
  and its setup changes demanded. A single section on a lot of two
  hundred reads like four unless the rate is on the page.

## Behavior contract (gate 3)

The limits table validation and its refusal of an untabulated contact,
the compression ratio derivation and its two-sided band, the void count
and area grading including the counted-but-unsized case, the deformed
strand check, the wall thinning check, the section plane validity that
suppresses the other dispositions, the unread-characteristic review
outcome, the required section count from lot size and setup changes and
the programme rollup over valid sections only are exercised by the gate 3
contract test: scripts/test_q7026_microsection_verification.py against
scripts/q7026_microsection_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7026_microsection_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
