---
name: q2030-comp-labelling
description: "Audit harness labelling and marking against the complementary content, format and durability requirements of ECSS-Q-ST-20-30C clause 7.6. Use when the task is decomposing a label token into the fields the project format prescribes, grading each field against the character set its position carries, scaling the minimum character height to the distance the marking is read from, placing the label inside its window from the termination, requiring both ends of a wire routed through a bundle to be marked, grading abrasion and solvent legibility evidence, and catching a token carried by two wires. Trigger: ecss, q-st-20-30c, complementary-harness-labelling, harness-label-token-format, marking-character-height-scaling, label-placement-window, label-durability-cycles, duplicate-harness-label-token, both-end-wire-marking."
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
  tags: [ecss, q-st-20-electrical-harness-scope, q-st-20-30c, q2030-comp-labelling, complementary-harness-labelling, harness-label-token-format, marking-character-height-scaling, label-placement-window, duplicate-harness-label-token]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Harness Manufacturing — Complementary Labelling and Marking (space-systems/ecss/q2030-comp-labelling)

Use when the task is the complementary labelling layer of ECSS-Q-ST-20-30C
clause 7.6 -- the space-specific demands on what a harness marking says,
how it is formed and how long it stays readable, on top of the workmanship
marking criteria the standard delegates to its adopted chapter.

## Domain quick reference

- A harness label is a traceability token, not a description. Its value
  comes from decomposing cleanly into the fields the project format
  prescribes, so a label that cannot be parsed has already failed however
  sensible it reads to a person standing at the bench.
- Content is graded field by field, because each position carries its own
  character set and length. A project code in lower case, a harness number
  without its prefix letter or a serial carrying a letter all parse and
  all still fail, and naming which field failed is what makes the finding
  actionable.
- Character height is not an absolute. It scales with the distance the
  marking has to be read from, so the same marking that is comfortable on
  a bench harness is illegible on an installed one behind a bracket, and
  the read distance belongs in the requirement rather than in the
  inspector's judgement.
- Placement is a window, not a preference. Too close to the termination
  and the marking is under the backshell or the strain relief; too far
  down the wire and it is lost inside the bundle at the first breakout.
- A wire that disappears into a bundle owes marking at both ends. One end
  identifies the wire at the connector it is being worked on; the far end
  is what makes a fault traceable without unlacing the harness.
- Durability is evidence, not a material claim. The marking survived a
  recorded number of abrasion and solvent exposures while staying legible,
  and those counts are what is graded against the project requirement.
- Uniqueness is the whole point. Two wires carrying the same token are
  worse than two unmarked wires, because the marking now actively
  misdirects the next person to trace them.

## Workflow

1. Validate each label record: an identifier, the token, the character
   height, the read distance and the distance from its termination.
2. Decompose the token against the prescribed field order and refuse a
   token whose field count does not match; an empty field is a refusal
   too, not an optional position.
3. Grade every parsed field against the character set and length its
   position carries, naming the field in the finding.
4. Compute the minimum character height from the read distance and grade
   the actual height against it, absorbing an exact equality with a
   tolerance instead of rounding the height up.
5. Grade the distance from the termination against the placement window
   at both edges.
6. Where the wire is routed through a bundle, confirm both ends carry the
   marking.
7. Grade the abrasion and solvent legibility counts against the project
   requirement and report each shortfall with its margin.
8. Collect every token in the harness, report any carried more than once,
   and roll all findings into one verdict.

## Pitfalls

- Accepting a label because a person could read it. The format is what
  makes the token machine-traceable through the as-built record; human
  legibility is necessary and nowhere near sufficient.
- Grading the token as one string. A single regular expression over the
  whole label tells the operator it is wrong without telling them which
  field to fix, and the rework comes back wrong twice.
- Using one minimum character height everywhere. The requirement follows
  the read distance, so an installed harness read from half a metre away
  needs taller marking than the same wire on the bench.
- Treating placement as tidiness. A label under the backshell cannot be
  read without demating, and a label past the first breakout is on the
  wrong side of it.
- Marking only the connector end of a bundled wire. The far end is the
  one a fault investigation needs, and adding it later means unlacing.
- Claiming durability from the marker material's datasheet. The
  requirement is graded on the legibility that survived recorded
  exposure, and a substitution of marker or solvent invalidates it.
- Letting a duplicate token through because both wires are in different
  connectors. The token is unique across the harness; scoping uniqueness
  to a connector is how two wires end up indistinguishable in the as-built
  record.

## Behavior contract (gate 3)

The token decomposition, the per-field content grading, the read-distance
character-height scaling, the placement-window grading, the both-end
marking rule, the abrasion and solvent durability verdict, the duplicate
token search and the whole-set roll-up are exercised by the gate 3
contract test: scripts/test_q2030_comp_labelling.py against
scripts/q2030_comp_labelling_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2030_comp_labelling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
