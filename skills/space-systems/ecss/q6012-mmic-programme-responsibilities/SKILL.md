---
name: q6012-mmic-programme-responsibilities
description: "Allocate the programme duties of a monolithic microwave circuit between customer and supplier under ECSS-Q-ST-60-12C clause 6: take the procurement mode, a foundry-led development or a catalogue part selection, read the party each applicable duty defaults to in that mode, then name the non-transferable duty handed to the wrong side, the applicable duty nobody owns, the duty both sides claim, the duty carried over from the other mode, and the agreed departure left without a deviation record. Use when an MMIC responsibility matrix is agreed, reviewed or inherited with a design. Trigger: ecss, q-st-60-12c-clause-6, mmic-responsibility-matrix, mmic-foundry-led-procurement, mmic-catalogue-part-procurement, mmic-duty-allocation-gap, mmic-non-transferable-duty, mmic-responsibility-deviation-record."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-mmic-programme-responsibilities, mmic-responsibility-matrix, mmic-foundry-led-procurement, mmic-catalogue-part-procurement, mmic-duty-allocation-gap, mmic-non-transferable-duty]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC — Programme Responsibilities (space-systems/ecss/q6012-mmic-programme-responsibilities)

Use when the task is the clause 6 step of ECSS-Q-ST-60-12C: settling who
does what on a monolithic microwave circuit programme. The duties are the
same duties in every programme; what moves is which side of the contract
each one sits on, and that depends on whether a circuit is being
developed at a foundry for this mission or an existing part is being
bought from a catalogue.

## Domain quick reference

- The procurement mode reshapes the duty list before it reallocates it.
  A catalogue part has already been designed, so the design, the design
  rules and the mask set are not duties in that mode at all — they are
  history. A matrix that still carries them is describing a different
  procurement from the one being run.
- A duty with no owner and a duty with two owners fail the same way, at
  different times. The unowned duty surfaces when someone asks for its
  output and nobody has it; the doubly owned duty surfaces when the two
  answers disagree and neither party can be held to theirs.
- Some duties cannot move whatever the parties agree. The mission
  requirement and the decision to fly a part stay with the side carrying
  the mission; process qualification and design-rule compliance stay with
  the side that owns the process, because only they can change it. An
  agreement moving one of these is not a deviation to record — it is a
  duty nobody can actually discharge.
- Everything else is movable, and moving it is normal. A customer with a
  microwave test facility may take evaluation testing; a supplier with a
  radiation programme may take characterization. What the standard asks
  for is that the departure from the default is agreed and written down,
  not that the default is kept.
- The default itself flips with the mode for some duties. Evaluation
  testing sits with the customer on a development, because the part is
  new and the customer is the one who needs the evidence; on a catalogue
  part it sits with the supplier, whose evaluation predates the order.
  Mask retention and obsolescence follow the same logic in reverse.
- Coverage is a number and so is the split. The fraction of applicable
  duties with an owner says whether the matrix is finished; the share
  each party carries says whether it is plausible.

## Workflow

1. Fix the procurement mode and derive the duties that arise in it,
   discarding the duties that belong only to the other mode.
2. Group the proposed matrix by duty, collapsing repeated identical
   entries and keeping every distinct party claimed for a duty.
3. For each duty, compare the claimed owner with the mode default; a
   departure on a non-transferable duty is a finding on its own, and a
   departure on a movable duty is a finding only while the deviation is
   unrecorded.
4. Raise a conflict wherever two parties are both accountable for one
   duty, and a mode finding wherever a duty from the other mode appears.
5. List the applicable duties nobody has taken, naming the party each
   would default to, so the gap comes with its remedy.
6. Compute the duty coverage and each party's share of the owned duties.
7. Report one verdict naming the most severe finding, with the full
   finding list and the coverage numbers behind it.

## Pitfalls

- Copying a matrix between modes. A responsibility matrix written for a
  foundry-led development carries design duties that do not exist for a
  catalogue part, and reusing it quietly assigns work that nobody will
  ever do.
- Reading a shared duty as a covered duty. "Both parties" on a line is an
  unresolved question, not an allocation, and it is cheapest to resolve
  before the first non-conformance rather than during it.
- Agreeing a transfer that cannot be performed. Moving process
  qualification to the customer is a sentence anyone can sign and nobody
  can execute, because the party who would have to act does not control
  the process.
- Treating a recorded deviation as a weaker allocation. A movable duty
  with a written agreement is fully allocated; the record exists so the
  next reviewer does not read it as an error.
- Judging the matrix by its length. Thirteen lines with two gaps is worse
  than eleven complete ones, which is why the coverage is computed
  against the duties the mode actually raises.
- Leaving obsolescence and mask retention to the end. It is the duty most
  often unowned, and the one whose owner is hardest to appoint years
  after the order.

## Behavior contract (gate 3)

The mode validation, applicable-duty derivation, default-owner lookup,
transferability rule, grouping of repeated and conflicting claims, gap
detection, coverage and share arithmetic and the precedence of the
reported verdict are exercised by the gate 3 contract test:
scripts/test_q6012_mmic_programme_responsibilities.py against
scripts/q6012_mmic_programme_responsibilities_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_mmic_programme_responsibilities.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
