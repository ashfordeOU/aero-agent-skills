---
name: q7026-applicability-and-connections
description: "Determine whether an electrical connection falls inside the crimped-connection practice of ECSS-Q-ST-70-26C and which crimp category governs it. Use when a harness definition mixes joining methods and each crimped barrel has to be bounded before tooling is chosen. Separates machined-contact, stamped-contact, splice, lug and coaxial-ferrule crimps from soldered, welded, wire-wrapped and insulation-displacement joints the practice does not cover, applies the conductor-count limit per category, refuses a mixed solid-and-stranded barrel, and scores barrel fill against its window. Trigger: ecss, q-st-70-26, crimped-connection-scope, crimp-category-selection, crimp-barrel-fill-ratio, crimp-conductor-count-limit, out-of-scope-joining-method."
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
  tags: [ecss, q-st-70-26-crimping-scope, q7026-applicability-and-connections, crimped-connection-scope, crimp-category-selection, crimp-barrel-fill-ratio, crimp-conductor-count-limit, out-of-scope-joining-method]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Applicability and Connection Types (space-systems/ecss/q7026-applicability-and-connections)

Use when the task is the framework step of ECSS-Q-ST-70-26C — deciding
which joints in a harness definition the crimping practice governs at
all, which crimp category each governed joint belongs to, and what that
category permits inside one barrel.

## Domain quick reference

- Scope is decided by the joining method first, and everything else is
  downstream of that answer. A soldered, welded, wire-wrapped,
  insulation-displacement or screw-clamp joint is not a crimp. Calling
  one a crimp because it sits in the same harness is how a
  qualification argument ends up covering a joint it never tested.
- Inside the crimp family the termination type is the category:
  machined contact, stamped and formed contact, in-line splice,
  terminal lug, coaxial ferrule. The category is not cosmetic — it
  carries the conductor-count limit.
- A contact barrel takes one conductor. The splice is the termination
  built to take several, and the lug takes at most a pair. Doubling a
  second wire into a contact barrel because it fits is the defect this
  clause exists to stop.
- Barrel loading is a ratio, not a gauge number. Total conductor
  cross-section over barrel bore cross-section has a floor as well as a
  ceiling: too little metal and the crimp has nothing to deform around,
  too much and the barrel cannot close without shearing strands.
- A barrel offered both solid and stranded conductors is refused
  whatever the fill says. The two yield differently under the die, so
  once the solid conductor has taken its set the stranded one is
  carrying the joint alone.
- A refusal names itself. Out of scope and in-scope-but-overloaded are
  different findings and go to different people.

## Workflow

1. Validate the connection: identifier, joining method, termination
   type, a non-empty conductor list with cross-sections and
   construction, and a barrel bore.
2. Fold the joining method as written — case, spacing and past tense —
   into a known token, and refuse a method nobody recognises rather
   than assuming it is a crimp.
3. Decide scope from the method alone. An out-of-scope joint stops
   here, with its method named in the finding and no category.
4. Map the termination type to its crimp category and look up the
   conductor limit that category carries.
5. Sum conductor cross-section, divide by barrel bore and categorize
   the fill as underfilled, acceptable or overfilled against the
   window, inclusive of both bounds.
6. Refuse a barrel mixing solid and stranded conductors independently
   of the fill result.
7. Collect every finding against the connection identifier, and roll
   the harness up into counts by category, an in-scope count and the
   list of findings.

## Pitfalls

- Treating anything in a connector as a crimp. The method field is the
  gate, and an insulation-displacement joint answers to a different
  practice entirely.
- Reading the conductor limit off the wire gauge instead of off the
  category. A splice and a contact take the same wire and not the same
  number of them.
- Judging barrel loading by ceiling only. An underfilled barrel fails
  in service quietly, long after the pull test that passed it.
- Accepting a solid-plus-stranded barrel because the fill computes
  inside the window.
- Losing the identifier when rolling a harness up. A finding nobody can
  trace to a connection is a finding nobody acts on.

## Behavior contract (gate 3)

Method and termination folding, scope decision, category mapping,
conductor limits, barrel fill ratio and its window, mixed-construction
refusal, per-connection assessment and the harness roll-up are
exercised by the gate 3 contract test:
scripts/test_q7026_applicability_and_connections.py against
scripts/q7026_applicability_and_connections_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7026_applicability_and_connections.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
