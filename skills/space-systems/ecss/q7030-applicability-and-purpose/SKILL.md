---
name: q7030-applicability-and-purpose
description: "Determine whether a proposed electrical connection is a solderless wrapped connection the ECSS-Q-ST-70-30 requirements govern, and which controls it takes on. Use when a wrapped joint, a terminal post or a backplane is being brought under the wire-wrapping standard. Test the joining method, test the post for the sharp corners the wire has to bite into, test the conductor for solid construction and a gauge inside the covered span, count the gas-tight contact areas the wrap would produce from turns times corners, and return the requirement areas plus a within-scope, within-scope-with-actions or outside-scope disposition. Trigger: ecss, q-st-70-30, wire-wrap-scope-eligibility, wire-wrap-terminal-post-corners, wire-wrap-solid-conductor-rule, wire-wrap-covered-gauge-span, wire-wrap-gas-tight-contact-count, wire-wrap-requirement-area-set."
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
  tags: [ecss, q-st-70-30-wire-wrapping, q-st-70-30, q7030-applicability-and-purpose, wire-wrap-scope-eligibility, wire-wrap-terminal-post-corners, wire-wrap-solid-conductor-rule, wire-wrap-covered-gauge-span, wire-wrap-gas-tight-contact-count, wire-wrap-requirement-area-set]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wire Wrapping — Applicability and Purpose (space-systems/ecss/q7030-applicability-and-purpose)

Use when the task is the scope question of ECSS-Q-ST-70-30: whether a connection
in front of you is a solderless wrapped connection the standard governs, whether
the terminal and the wire can carry one, and what the wrap is actually for. This
leaf decides applicability; the wire, tool and preparation leaves carry the
controls it hands over.

## Domain quick reference

- A wrapped connection is a cold weld made by tension, not a fastening. The wire
  is drawn round a corner under enough force that the two metals deform into
  each other and exclude air from the interface, which is why the connection is
  gas-tight and why it keeps its resistance for decades without solder.
- That mechanism is also the scope test. Wherever the mechanism cannot happen,
  the requirements do not apply and cannot be made to apply: a round post has no
  corner to deform against, a stranded conductor lets its strands share the
  tension unevenly, and a soldered or crimped joint reaches its contact by a
  different route with its own process standard behind it.
- The count that matters is turns times sharp corners, because each corner of
  each turn is one gas-tight contact area. A four-corner post at six turns
  carries twenty-four independent contact areas, which is what makes the
  connection tolerant of a few of them degrading.
- Gauge span is a tool and terminal question, not a preference. A wire thicker
  than the span cannot be driven round the corner by the bit; a thinner one
  breaks before it reaches the tension the weld needs.
- Being inside scope is taking on a set of controls, not receiving a permission.
  Wire and terminal specification, tool certification, stripping, turn count,
  inspection and rework limits all arrive together, and a modified wrap or a
  flight application adds to that set rather than replacing part of it.

## Workflow

1. Normalise the connection record and test the joining method: only a
   solderless wrap is the process these requirements govern.
2. Test the terminal: the post shape has to be one that presents corners, and it
   has to present at least the minimum number of sharp corners.
3. Test the conductor: solid construction, and a gauge inside the covered span
   at both ends, with the thicker and thinner exclusions reported separately.
4. Count the gas-tight contact areas as turns times sharp corners and raise a
   finding when a connection inside scope would not reach the owed count.
5. Where the connection is inside scope, return the requirement areas it has
   taken on, adding the insulation-turn area for a modified wrap and the
   operator certification area for a flight application.
6. Close with one disposition: within-scope, within-scope-with-actions, or
   outside-scope with every exclusion named.

## Pitfalls

- Reading a wrap as a mechanical fastening. Once the joint is thought of as wire
  held on a post, every scope rule looks arbitrary and the round post, the
  stranded wire and the low turn count all look like acceptable variations.
- Wrapping a radiused or round post because it fits. The tool will make the
  turns and the joint will look correct; there is no corner to form the contact
  against, so the connection has the appearance of a wrap and none of its life.
- Accepting stranded wire on the grounds that it is more flexible. Flexibility
  is the defect here: the strands do not take the tension together, so the
  contact areas form at different pressures or not at all.
- Grading the joint on turns alone. Turns without corners are still nothing, and
  a six-turn wrap on a two-corner post carries half the contact areas of the
  same wrap on a four-corner post.
- Treating an out-of-scope connection as a waiver case. A soldered or crimped
  joint is not a wrap with a deviation; it belongs to a different process
  standard and is graded there.
- Taking scope as approval. Being inside scope means the wire, tool, stripping,
  turn count, inspection and rework controls all now apply to the connection.

## Behavior contract (gate 3)

The joining-method, terminal-shape, corner-count, conductor-construction and
gauge-span exclusions, the gas-tight contact count, the requirement-area set for
conventional, modified and flight connections, and the scope disposition are
exercised by the gate 3 contract test:
scripts/test_q7030_applicability_and_purpose.py against
scripts/q7030_applicability_and_purpose_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7030_applicability_and_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
