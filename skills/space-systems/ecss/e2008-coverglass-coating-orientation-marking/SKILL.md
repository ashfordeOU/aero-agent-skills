---
name: e2008-coverglass-coating-orientation-marking
description: "Use when a coverglass orientation scheme, coating-side marking or lot packaging convention has to be reviewed. Verify that the face of a delivered coverglass carrying the optical coating is identifiable under clause 8.3.3 of ECSS-E-ST-20-08C, so orientation survives the trip from tray to bond: decide whether an indicator may sit where it is declared at all, whether it still names a face once the piece is turned over, whether it survives the clean before bonding, what it costs inside the clear aperture against a declared cap, how many cues stay usable at the point of use, and whether one convention holds across the lot. Trigger: ecss, e-st-20-08c, coverglass-coated-face-identification, coverglass-orientation-indicator-admissibility, coverglass-flip-ambiguity, coverglass-clear-aperture-indicator-loss, coverglass-lot-orientation-convention."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-coverglass-coating-orientation-marking, coverglass-coated-face-identification, coverglass-orientation-indicator-admissibility, coverglass-flip-ambiguity, coverglass-clear-aperture-indicator-loss, coverglass-lot-orientation-convention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses -- Coating Orientation Marking (space-systems/ecss/e2008-coverglass-coating-orientation-marking)

Use when the task is clause 8.3.3 of ECSS-E-ST-20-08C: a coverglass is a thin,
near-symmetric plate whose two faces do completely different jobs, and the
delivery has to say which one carries the coating in a way that still works
when somebody lifts the piece out of a tray with tweezers.

## Domain quick reference

- The piece is almost symmetric and its two faces are not interchangeable at
  all. One goes outboard under the optical coating; the other goes inboard into
  the adhesive. Installed the wrong way up, the coverglass is not a degraded
  part, it is the wrong part.
- Three properties are graded separately because they fail separately.
  Admissibility asks whether the indicator may sit where it is declared. Face
  resolution asks whether it still names a face after a flip. Survival asks
  whether it is still there after the clean before bonding. A scheme can pass
  any two and be useless.
- Three pairings are refused outright rather than merely reported. Ink inside
  the clear aperture is an optical defect over the cell for the life of the
  mission; an adhesive label on the cell-facing face sits in the bond line; a
  feature of the outline declared on a face is a record that does not say where
  the feature is.
- Face resolution is the property a reviewer skips. A cut corner is cut through
  the full thickness, so turning the piece over mirrors it: it fixes the
  rotation of the piece and says nothing about which way up it is. A bevel
  ground into one face, or an arrow cut into the rim pointing at a face, does
  say.
- Packaging orientation is not marking. The tray knows which way up the pieces
  were packed and the pieces do not, so the knowledge is lost at the first
  handling step and cannot be recovered from the hardware.
- Permanence is a property of the pairing of means and clean, never of the
  means alone. Ground geometry survives everything. A label survives a solvent
  wipe and not an ultrasonic bath. Ink is gone at the first wipe.
- An indicator inside the clear aperture costs transmission for the life of the
  mission, so its footprint is carried as a fraction of the aperture and held
  against a declared cap. Outside the aperture the footprint costs nothing,
  however large, so the location decides whether the number matters at all.
- Cue count is the last per-piece reading: how many indicators are admissible,
  resolve the faces and survive preparation all at once. One is usually enough;
  a project that wants a second independent cue says so in policy.
- One thing no single piece can show is whether the lot follows one convention.
  Half a lot marking the coated face and half marking the uncoated face is
  ambiguous even though every piece is individually marked, because the
  operator has to know which rule a piece follows before reading its indicator.

## Workflow

1. Take the lot with its identifier and one record per piece: which face the
   scheme marks, the clear aperture, the clean the piece sees before bonding,
   and the cues it carries with their means, location and footprint.
2. Decide admissibility from the means against the location, and refuse the
   three pairings that damage the optics, the bond line or the record itself.
3. Decide face resolution from the means: does the indicator still name a face
   once the piece has been turned over.
4. Decide survival from the means against the clean, and aim the finding at the
   step that removes the indicator.
5. Work out the aperture the cues cost, which is zero outside the clear
   aperture and the footprint fraction inside it, then hold it against the cap
   with a comparison that absorbs representation error.
6. Count the cues that are admissible, resolve the faces and survive at once,
   and compare that with the count the policy asks for.
7. Grade each piece, then compare the lot with itself for one convention -- one
   marked face and one usable indicator means -- and roll up: the verdict, the
   pieces with no orientation established, the unambiguous share and the
   weakest piece.

## Pitfalls

- Grading the indicator means and stopping there. An engraved rim arrow and a
  printed arrow look equally marked in the stores; one of them is gone before
  the piece reaches the bond station.
- Accepting a cut corner as an orientation feature. It mirrors under a flip, so
  it orients the piece in plane and leaves both faces equally plausible.
- Treating the tray as the marking scheme. Packaging orientation holds only
  until the lid comes off, and nothing on the glass records it.
- Putting the indicator where it is easiest to read. Inside the aperture it
  costs transmission forever; on the cell-facing face it sits in the bond line.
- Counting a large rim indicator against the aperture cap. A rim mark costs
  nothing at any size, and charging it hides the small face mark that genuinely
  does cost transmission.
- Reading survival from the means alone. The clean the piece actually sees is
  half the answer, and a label that passes a wipe fails a bath.
- Calling a piece marked because it carries an indicator. A cue counts only
  when it is admissible, resolves the faces and survives, all three at once.
- Checking the convention one piece at a time. A lot split between two marked
  faces is ambiguous even though no single record is, and only comparing the
  set shows it.
- Comparing an aperture fraction or an unambiguous share against its limit by
  bare arithmetic. Both are quotients of measured or counted quantities, so an
  indicator cut exactly to the cap can evaluate a unit in the last place above
  it and read as over on one platform and as met on another.

## Behavior contract (gate 3)

The indicator admissibility pairings and the three refusals, the flip
resolution reading, the survival table against the pre-bond clean, the clear
aperture loss fraction and its cap, the usable cue count, the per-piece
grading, the lot convention comparison and the lot roll-up are exercised by the
gate 3 contract test:
scripts/test_e2008_coverglass_coating_orientation_marking.py against
scripts/e2008_coverglass_coating_orientation_marking_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_coating_orientation_marking.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
