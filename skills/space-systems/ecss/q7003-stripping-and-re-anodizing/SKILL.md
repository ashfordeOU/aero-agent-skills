---
name: q7003-stripping-and-re-anodizing
description: "Determine whether a rejected anodized part may be stripped and re-anodized, and how many cycles are left. Use when a non-conforming part is about to go back through the line: cost each cycle in base metal on every treated surface, count the cycles the drawing minimum still leaves, the cycles the declared reprocessing ceiling still leaves for that alloy class, and on clad sheet the cycles the remaining cladding still leaves, take the tightest of the three, and separate a part that is out of metal, which no deviation can recover, from one that is only out of cycles, which a documented deviation can. Trigger: ecss, q-st-70-03-anodizing, anodize-stripping-metal-loss, anodize-reprocessing-cycle-limit, clad-sheet-stripping-limit, anodize-rework-disposition."
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
  tags: [ecss, q-st-70-03-anodizing, q7003-stripping-and-re-anodizing, anodize-stripping-metal-loss, anodize-reprocessing-cycle-limit, clad-sheet-stripping-limit, anodize-rework-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Anodizing — Stripping and Re-anodizing (space-systems/ecss/q7003-stripping-and-re-anodizing)

Use when the task is the rework clause of ECSS-Q-ST-70-03: deciding
whether a non-conforming anodized part can be stripped and put back
through the line, and how many such cycles it has left before the answer
becomes no.

## Domain quick reference

- Stripping is not free. The anodic layer grows both outward from the
  original surface and inward into the substrate, so removing it takes
  base metal with it. Each cycle costs metal on every surface that was
  treated, which is why a thickness dimension between two anodized faces
  loses twice what a single-sided feature loses.
- The dimension has to be checked after the proposed cycle, not before
  it. A part that is comfortably in tolerance today can be undersize the
  moment the next strip finishes, and that is the check the shop needs
  before it puts the part in the tank.
- A declared ceiling on reprocessing cycles runs alongside the
  dimensional check and is not implied by it. Repeated etching roughens
  the surface and works the grain boundaries whatever the caliper says,
  so the ceiling is lower for an alloy that is sensitive to that attack
  and lower again for high-strength material.
- Clad sheet carries a third limit that neither of the others sees. The
  cladding is a sacrificial corrosion skin over a stronger core, so
  stripping through it passes every dimensional check while removing the
  protection the material was specified for. The remaining clad
  thickness sets its own cycle count.
- The tightest of the three governs, and which one is tight matters as
  much as the count. A part out of metal cannot be recovered, because no
  concession puts material back. A part out of cycles or out of cladding
  still has material, so a documented deviation is at least a decision
  someone with authority can take.
- The last permitted cycle is worth calling out separately from the ones
  before it. A shop that knows this is the final attempt plans the
  rework differently from one that assumes another go is available.
- A cycle budget is a division, and a budget set as a whole number of
  cycles lands exactly on an integer. Flooring that division raw throws
  away a cycle the part is entitled to, and throws it away on one
  machine and not another.

## Workflow

1. Cost one cycle: the per-surface metal loss times the number of
   treated surfaces, converted to the dimension's units. Reject a
   surface count above two, because a single dimension spans at most two
   faces and anything more is really several dimensions.
2. Count the cycles the drawing minimum leaves. Reject a part that is
   already below its minimum rather than returning a negative budget,
   since that part is a scrap decision and not a rework question.
3. Count the cycles the reprocessing ceiling leaves for the alloy class,
   from the cycles already completed.
4. On clad sheet, count the cycles the remaining cladding leaves. On any
   other alloy class this limit does not apply and is reported as absent
   rather than as zero.
5. Take the tightest limit and record every limit that sits at it, so a
   part held by two constraints at once shows both.
6. Give the disposition: two or more cycles left is permitted, exactly
   one is permitted as the final cycle, and none splits by which limit
   binds -- scrap where metal binds, concession where policy or cladding
   binds. Report the dimension the part would hold after the next cycle
   alongside the verdict.

## Pitfalls

- Checking the dimension before the strip rather than after it. The
  question is whether the part survives the cycle being proposed, and a
  part that is in tolerance now is exactly the part that goes undersize
  during the rework.
- Counting single-sided loss on a two-sided dimension. The cycle cost
  doubles, so the cycle budget halves, and a part planned on the
  single-sided figure runs out of metal twice as fast as the paperwork
  says.
- Treating the reprocessing ceiling as advisory once the dimension still
  has room. The ceiling is there for surface condition and grain
  boundary attack, neither of which the caliper can see, so metal
  remaining is not evidence that another cycle is safe.
- Stripping clad sheet on a bare-alloy cycle budget. Every dimensional
  check passes while the sacrificial skin disappears, and the part that
  comes out is a stronger core with none of the corrosion protection the
  material was chosen for.
- Offering a concession to a part that is out of metal. A deviation can
  accept a condition; it cannot restore material, so the only honest
  answer there is scrap.
- Flooring the cycle budget with bare arithmetic. A budget that is
  exactly a whole number of cycles can evaluate a few units in the last
  place below that integer, so the floor absorbs the representation
  error rather than silently losing the last permitted cycle.

## Behavior contract (gate 3)

The per-cycle metal loss, the dimensional cycle budget, the
reprocessing ceiling, the cladding limit and the rework disposition are
exercised by the gate 3 contract test:
scripts/test_q7003_stripping_and_re_anodizing.py against
scripts/q7003_stripping_and_re_anodizing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7003_stripping_and_re_anodizing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
