---
name: q7040-post-braze-treatments
description: "Derive the post-braze treatment a brazement owes and decide whether it may leave the cleaning bay. Use when a part has come out of the braze cycle and the cleaning route has to be set from the process rather than from how the joint looks: build the ordered operation list from the flux family and the parent alloy, add a chemical step only where the residue is a corrosive halide, hold the removal to the window before the residue vitrifies, evidence the removal through final-rinse conductivity against the feed water, and require passivation only on the steel that carries a chromium-oxide film. Trigger: ecss, q-st-70-40-brazing, braze-flux-residue-removal, braze-final-rinse-conductivity, braze-stainless-passivation, braze-residue-removal-window, post-braze-cleaning-sequence."
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
  tags: [ecss, q-st-70-40-brazing, q7040-post-braze-treatments, braze-flux-residue-removal, braze-final-rinse-conductivity, braze-stainless-passivation, post-braze-cleaning-sequence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Brazing — Post-Braze Treatments (space-systems/ecss/q7040-post-braze-treatments)

Use when the task is the post-braze clause of ECSS-Q-ST-70-40: setting
the cleaning, residue-removal and passivation sequence a brazement owes
after it leaves the heat, and deciding whether that sequence actually
closed.

## Domain quick reference

- What a part owes afterwards is set by what was used to make the filler
  flow, not by how the joint looks. A clean joint out of a fluxed
  process still carries residue.
- A vacuum or clean inert-gas furnace cycle is flux-free. It leaves
  nothing to remove, and adding a chemical cleaning step to it
  introduces a corrosion risk instead of removing one.
- A vacuum cycle recorded together with a flux is not a conservative
  entry; it is two records contradicting each other, and it is resolved
  before the part moves.
- Borax and boric residues are glassy and hygroscopic. The halide
  families — fluoride and chloride bearing — are actively corrosive and
  keep attacking the parent metal for as long as they are on the part,
  so they take a mechanical and a chemical step, not a rinse alone.
- Removal has a deadline. The residue is soluble while it is warm and
  hydrated; once it cools and dries it vitrifies, and the hot-water
  quench that would have lifted it no longer will. The tighter the
  corrosivity, the shorter the window.
- Removal is evidenced, not asserted. The evidence is the conductivity
  of the final rinse measured against the conductivity of the feed
  water: a rinse leaving the part much more conductive than it arrived
  is still carrying ionic residue, whatever the part looks like.
- Passivation restores the chromium-oxide film that the braze thermal
  cycle and the cleaning both degrade on an austenitic stainless steel.
  It is meaningless on aluminium, titanium, copper and nickel alloys,
  and specifying it there is a process error.
- Passivation runs after the residue has gone. Passivating over a
  residue seals it under the restored film.

## Workflow

1. Read the process and the flux family off the braze record and refuse
   the pair that cannot coexist.
2. Build the ordered operation list: controlled cool, then residue
   removal where a residue exists, with the mechanical and chemical
   steps added only for a corrosive halide, then the final rinse and its
   conductivity verification, then passivation where the alloy carries a
   film, then drying and the visual check.
3. Compare the operations actually recorded against that list and report
   the gaps in the order they were owed, so the recovery runs in
   sequence rather than in the order somebody noticed them.
4. Check the hours from the end of the braze to the start of removal
   against the window for the flux family, absorbing representation
   error at the boundary with a named tolerance.
5. Evaluate the final rinse as a ratio against the feed conductivity
   rather than as an absolute number, so a facility on harder water is
   not graded against somebody else's supply.
6. Release the part only when no operation is missing, the removal was
   inside its window and the rinse evidences a clean surface. Report
   every finding, not only the first.

## Pitfalls

- Grading the cleaning on appearance. A vitrified halide film is
  transparent and the part looks finished; the conductivity reading is
  what sees it.
- Adding a chemical cleaning step to a vacuum-brazed part because the
  route looks thorough. There is no residue to attack, so the chemistry
  attacks the parent metal instead.
- Measuring the final rinse without measuring the feed. The absolute
  number carries the facility's water in it and says nothing about what
  came off the part.
- Passivating before the residue is off. The film goes down over the
  residue and the corrosion continues underneath it.
- Letting a part sit over a shift change before removal because the
  paperwork allows the operation in any order. The window runs from the
  end of the braze, not from the start of the shift that will do it.
- Widening the rinse allowance to pass an exact-equality reading. The
  equality is a representation question, handled by the tolerance inside
  the comparison; the allowance stays as specified.

## Behavior contract (gate 3)

The flux-family residue and corrosivity split, the removal window, the
passivation applicability rule, the ordered operation list with its
process and flux contradiction check, the ordered gap list, the
ratio-based final-rinse assessment with its boundary tolerance and the
release verdict are exercised by the gate 3 contract test:
scripts/test_q7040_post_braze_treatments.py against
scripts/q7040_post_braze_treatments_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7040_post_braze_treatments.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
