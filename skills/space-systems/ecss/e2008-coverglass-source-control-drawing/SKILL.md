---
name: e2008-coverglass-source-control-drawing
description: "Use when a coverglass source control drawing or coating procurement content review is on the table. Audit the source control drawing a coated coverglass is bought against, the content set ECSS-E-ST-20-08C Annex D expects fixed before order: name the heading the drawing leaves silent, test every dimension for a band that brackets its nominal and is drawn tightly enough to control the part, check the transmission window runs cut-on to cut-off and is wide enough to be a window, confirm the coating stack names a face and a function per layer and carries the antireflection and ultraviolet-reject layers, and rank an absent heading above one written down wrong. Trigger: ecss, e-st-20-08c-annex-d, coverglass-source-control-drawing, coverglass-coating-stack-content, coverglass-optical-window-limits, coverglass-dimension-tolerance-band, coverglass-procurement-drawing-content."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-coverglass-source-control-drawing, e-st-20-08c-annex-d, coverglass-source-control-drawing, coverglass-coating-stack-content, coverglass-optical-window-limits, coverglass-dimension-tolerance-band, coverglass-procurement-drawing-content]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coated Coverglass -- Source Control Drawing Content (space-systems/ecss/e2008-coverglass-source-control-drawing)

Use when the task is Annex D of ECSS-E-ST-20-08C: a coated coverglass is
procured against a source control drawing, and somebody has to decide whether
that drawing actually controls the part. The drawing is the whole of the
agreement. Any property it does not state is a property the supplier is free
to choose, and a coverglass that meets a silent drawing perfectly can still be
the wrong part. This leaf grades the drawing on content, on tolerance, on
optics and on the coating stack.

## Domain quick reference

- Silence is a decision, and it is the supplier's. A heading nobody wrote is
  not an open point flagged for later, it is a free choice already delegated,
  and it surfaces at incoming inspection when there is nothing to reject
  against.
- A nominal without a band controls nothing. Thickness and planar size are
  bought numbers; stating 0.100 mm with no limits buys anything the coating
  house can make and call 0.100 mm.
- A band has to bracket what it brackets. A minimum and maximum that both sit
  above the nominal is a transcription error that reads as a tolerance, and it
  passes any check that only tests minimum below maximum.
- A band can also be too generous to mean anything. A thickness band an order
  wider than the process spread is a tolerance in name only, so the band is
  measured as a fraction of its own nominal rather than in absolute units.
- The optical window has a direction. Cut-on below cut-off is what makes a
  passband; the two swapped describes a filter that blocks everything, and a
  zero-width window is the same statement written differently.
- The coating stack is what makes the coverglass a coverglass. An
  antireflection layer and an ultraviolet-reject layer are the reason the part
  exists; a conductive layer is a mission choice and belongs to policy.
- A layer needs a face. The same coating on the front and on the rear are
  different parts, and a stack listing functions without faces has not said
  which one is being bought.

## Workflow

1. Read the drawing identifier and the content mapping; the identifier is what
   every later finding is reported against.
2. Audit the content against the required heading set, treating an empty
   string, an empty list and an empty mapping as absent rather than as
   present-but-blank.
3. Assess each dimension: refuse an inverted band outright, report a nominal
   with no band as untoleranced, and compute the band as a fraction of its own
   nominal before comparing it to the policy ceiling.
4. Assess the optical window: cut-on against cut-off, the window width against
   the policy floor, and the stated transmittance for a value a filter could
   actually reach.
5. Assess the coating stack: every layer names a face and a function, and the
   functions the part exists to provide are all present.
6. Collect the findings in one list, keeping an absent heading ahead of a
   heading that is present but unusable.
7. Return a drawing verdict that is releasable only when every heading is
   stated, every dimension is usable, the window is usable and the stack is
   complete.

## Pitfalls

- Reading the drawing for what it says and never for what it omits. The
  headings that fail a procurement are the ones nobody looked for, because a
  page with no gap in it looks finished.
- Testing a tolerance band only for minimum below maximum. That test passes a
  band sitting entirely to one side of the nominal, which is the transcription
  error that actually happens.
- Comparing band widths in absolute units across dimensions. A 0.01 mm band is
  tight on a 40 mm length and meaningless on a 0.1 mm thickness, so the
  comparison has to be made against the nominal.
- Treating a swapped cut-on and cut-off as an obvious typo and correcting it
  quietly. The drawing may genuinely have been issued that way, and the
  correction destroys the evidence that it was.
- Accepting a coating stack as a list of coating names. Without a face per
  layer the stack does not say which side of the glass is being coated, and
  both readings are buildable.
- Merging the arms into one pass or fail. An absent heading asks the purchaser
  to make a decision; an unusable band asks the draughtsman to fix one, and a
  merged verdict asks both people for the same work.

## Behavior contract (gate 3)

The required content set, the content audit, the dimensional band assessment,
the optical window assessment, the coating stack assessment and the whole
drawing verdict are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_source_control_drawing.py against
scripts/e2008_coverglass_source_control_drawing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_source_control_drawing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
