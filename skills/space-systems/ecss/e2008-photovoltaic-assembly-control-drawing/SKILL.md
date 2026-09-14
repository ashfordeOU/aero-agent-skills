---
name: e2008-photovoltaic-assembly-control-drawing
description: "Audit the source control drawing for a complete photovoltaic assembly against the content Annex A of ECSS-E-ST-20-08C calls for: resolve every content block as specified, open or absent rather than as present or missing; refuse a nominal carried without a tolerance band as a control; check each constituent item cites a drawing that exists at the issue cited; and weight completeness by how much of the assembly each block governs instead of counting blocks. Use when a photovoltaic assembly drawing package is offered for release and its content has to carry the assembly. Trigger: ecss, e-st-20-08c, photovoltaic-assembly-source-control-drawing-audit, photovoltaic-assembly-drawing-content-block-state, photovoltaic-assembly-constituent-drawing-issue-standing, photovoltaic-assembly-dimension-tolerance-control, photovoltaic-assembly-drawing-completeness-share."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-photovoltaic-assembly-control-drawing, photovoltaic-assembly-source-control-drawing-audit, photovoltaic-assembly-drawing-content-block-state, photovoltaic-assembly-constituent-drawing-issue-standing, photovoltaic-assembly-dimension-tolerance-control, photovoltaic-assembly-drawing-completeness-share, photovoltaic-assembly-drawing-release-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Photovoltaic Assembly Source Control Drawing (space-systems/ecss/e2008-photovoltaic-assembly-control-drawing)

Use when the task is the content rule of ECSS-E-ST-20-08C Annex A -- what the
source control drawing for a complete photovoltaic assembly has to carry
before it can be released, and how much of the assembly the drawing as written
actually controls.

## Domain quick reference

- A source control drawing is not a picture of an assembly. It is the document
  naming the characteristics the supplier is not free to change, so anything
  the drawing shows but does not control is something the supplier may change
  without telling anybody.
- A content block has three outcomes, not two. It can be absent from the
  package, present but left open -- a box carrying TBD, a note promising a
  later issue -- or present and specified. Only the third one controls
  anything, and folding open into present is how an incomplete drawing reads
  as complete.
- A dimension is controlled by its tolerance band, never by its nominal. A
  nominal shown alone is a drawn intention. A dimension marked for reference
  says so honestly and controls nothing by design.
- A band can also be too wide to be a control. Past roughly a tenth of the
  nominal it admits every part the supplier could make, which is a note
  wearing a tolerance's clothes rather than a limit anyone could reject
  against.
- A zero-width band is the mirror failure: no part can be made to it and no
  part can be rejected against it, so it controls nothing either.
- A complete photovoltaic assembly is an assembly of constituent items that
  each carry their own drawing, and the top drawing controls them only through
  the issue it cites. A draft or cancelled citation points at nothing. A
  superseded citation, or a citation at an issue other than the released one,
  points at something real that is no longer the current something.
- Blocks do not weigh the same. The constituent item list and the electrical
  output carry the assembly; the handling note does not. Completeness weighted
  by what each block governs is a different number from the share of boxes
  filled in, and it is the honest one.

## Workflow

1. Take the package as its drawing number, the content blocks it carries, the
   dimensions it shows and the constituent items it cites.
2. Resolve each content block into specified, open or absent, and name every
   block the annex requires that the package never mentions at all.
3. Grade each dimension: a nominal with no band and a zero-width band control
   nothing, an over-wide band is a note, a reference dimension is honest about
   controlling nothing, and everything else carries computed bounds.
4. Resolve each constituent citation into governing at the released issue,
   off issue, or not governing at all.
5. Weight the specified blocks by what each governs and compare the resulting
   share with the threshold the package is being released against.
6. Disposition the drawing: a missing or absent block, an uncontrolled
   dimension, a non-governing citation or a share under the threshold stops
   the release; an open block or an off-issue citation releases it against
   open items; anything else releases it.
7. Report the share, the open items and the verdict together, never the
   verdict alone.

## Pitfalls

- Reading a filled-in title block as a specified content block. The box being
  drawn is not the box being answered.
- Counting blocks rather than weighting them. Nine of ten blocks specified
  says nothing when the missing one is the constituent item list.
- Accepting a nominal without a tolerance because the number looks precise.
  Precision in the digits is not a limit anyone can reject a part against.
- Treating a very wide tolerance as a conservative one. A band nothing can
  fail is not conservative, it is absent.
- Writing a zero-width band to signal exactness. It rejects every real part
  and is never what the drawing meant.
- Citing a constituent drawing without its issue, or at an issue the supplier
  has already superseded. The citation looks complete and governs the wrong
  document.
- Letting a draft constituent drawing ride because its content is agreed.
  Nobody signed it, so nothing holds the supplier to it.
- Comparing a weighted completeness share with its threshold by bare
  arithmetic. Both are quotients of weights and a package exactly on the
  threshold can evaluate a few units in the last place under it; the
  comparison absorbs that while the threshold stays as written.
- Reporting one verdict with no share behind it. The verdict hides whether
  the package missed by one handling note or by half the drawing.

## Behavior contract (gate 3)

The content block state resolution, dimension tolerance control, over-wide and
zero-width band handling, constituent drawing issue standing, weighted
completeness share and the drawing release disposition are exercised by the
gate 3 contract test:
scripts/test_e2008_photovoltaic_assembly_control_drawing.py against
scripts/e2008_photovoltaic_assembly_control_drawing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_photovoltaic_assembly_control_drawing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
