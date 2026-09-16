---
name: e2008-bare-cell-marking
description: "Use when a bare cell delivery register, cell marking scheme or wafer-lot traceability claim has to be reviewed. Audit the permanent traceability code marked on delivered bare solar cells under ECSS-E-ST-20-08C clause 7.1.3: decide whether the marking method and the place it is put are admissible on a brittle cell at all, whether the mark stays readable through the welding, bonding, cure and cycling the cell will see, how much illuminated area the mark costs against the policy cap, what depth the coded fields and the delivery register actually reach against the depth the process document sets, and whether a code repeats across the delivered set. Trigger: ecss, e-st-20-08c, bare-cell-permanent-marking, bare-cell-traceability-depth, bare-cell-mark-placement-admissibility, bare-cell-active-area-mark-loss, bare-cell-code-uniqueness-register, wafer-lot-traceability-claim."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-bare-cell-marking, bare-cell-permanent-marking, bare-cell-traceability-depth, bare-cell-mark-placement-admissibility, bare-cell-active-area-mark-loss, bare-cell-code-uniqueness-register, wafer-lot-traceability-claim]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells — Marking (space-systems/ecss/e2008-bare-cell-marking)

Use when the task is clause 7.1.3 of ECSS-E-ST-20-08C: every delivered bare
cell carries a permanent code, and that code has to keep working after the
cell stops being a loose item -- after it is welded into a string,
coverglassed, cured and cycled. How far the code has to reach is not a
constant; the process identification document sets the depth, and the scheme
is graded against that depth rather than against a house habit.

## Domain quick reference

- A bare cell pulls three requirements against each other. The mark has to
  survive downstream processing, it has to sit somewhere that neither costs
  illuminated area nor starts a crack in a brittle wafer, and it has to reach
  the depth the process document asks for. Each one fails for its own reason
  and each has its own repair.
- Two method-and-place pairings are refused outright rather than merely
  reported. A laser cut into the front active area is a crack initiator on a
  thin cell and removes illuminated area at the same time; an adhered label
  on the rear metallisation sits inside the bond line the cell is later
  attached through.
- Permanence is a property of the pairing of method and exposure, never of
  the method alone. An engraved code survives the full campaign. A fired-on
  ink code survives welding and cure and loses legibility under cycling. An
  adhered label is gone at the first welding step. A record-only scheme marks
  nothing and has no fallback of any kind.
- A mark placed inside the illuminated area costs power for the life of the
  mission, so its footprint is carried as a fraction of the active area and
  held against a declared cap. Outside that area the footprint costs nothing,
  however large it is, so the location decides whether the number matters.
- Depth runs in four steps: nothing, the production lot, the individual cell,
  and the wafer lot behind it. A lot code cannot tell two cells apart. A
  serial identifies the cell and reaches no further on its own. Wafer-lot
  depth is reached either by coding the wafer lot into the mark or by a serial
  plus a delivery register that resolves it.
- A register only helps when the hardware can be used to enter it. A register
  that resolves wafer lots but keys on something the cell does not carry is a
  table nobody can look anything up in.
- Uniqueness is a property of the delivered set, not of one code. A code
  repeated across two cells resolves to a set rather than to a cell, and it
  cannot be found by grading any single cell -- only by comparing the set.

## Workflow

1. Take the delivery with its identifier, the depth the process
   identification document requires, and one record per cell: its code, the
   marking method, where the mark is put, the processing the cell will see,
   the mark footprint and active area, the coded fields, and whether a
   delivery register resolves the wafer lots.
2. Decide placement admissibility from the method against the location, and
   refuse the two pairings that damage the cell or the bond line rather than
   carrying them as ordinary findings.
3. Decide permanence from the method against the exposure, not from the
   method alone, and aim the finding at the step that loses the mark.
4. Work out the illuminated area the mark costs, which is zero outside the
   active area and the footprint fraction inside it, then hold it against the
   policy cap with a comparison that absorbs representation error.
5. Read the depth the scheme actually reaches from the coded fields together
   with the register, and flag a register that has no serial to key on.
6. Compare the reached depth with the required depth and record the shortfall
   in steps. Refuse a process document that requires no depth at all; it
   grades nothing.
7. Grade each cell, compare the codes across the delivered set for repeats,
   then roll up: the verdict, the cells with no marking established, the
   compliant share and the weakest cell by verdict then by shortfall.

## Pitfalls

- Grading the marking method and stopping there. An engraved code and an
  adhered label look equally identified in the stores; one of them is
  anonymous the moment the cell is welded into a string.
- Reading the mark location as a cosmetic choice. On a bare cell the location
  decides whether the mark is a crack initiator, a bond-line contaminant, or
  a permanent power loss, and the method alone tells you none of that.
- Counting a large mark outside the illuminated area against the area cap. A
  border mark costs no power at any size, and charging it hides the small
  front mark that genuinely does.
- Treating a serial as the end of the chain. A serialised cell whose wafer lot
  is unreachable satisfies a process document that asks for cell depth and
  fails one that asks for wafer-lot depth, and only the document decides.
- Crediting a delivery register the hardware cannot be used to enter. The
  register is a bridge only when the mark carries the key it is indexed on.
- Checking uniqueness one cell at a time. A repeated code is invisible in
  every individual record and appears only when the set is compared with
  itself.
- Comparing an area fraction or a compliant share against its limit by bare
  arithmetic. Both are quotients of measured or counted quantities, so a mark
  cut exactly to the cap can evaluate a unit in the last place above it and
  read as over on one platform and as met on another.

## Behavior contract (gate 3)

The placement admissibility pairings and the two refusals, the permanence
table, the active-area loss fraction and its cap, the reached-depth reading,
the shortfall in steps against the process document, the delivered-set
uniqueness check, the per-cell grading and the delivery roll-up are exercised
by the gate 3 contract test: scripts/test_e2008_bare_cell_marking.py against
scripts/e2008_bare_cell_marking_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e2008_bare_cell_marking.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
