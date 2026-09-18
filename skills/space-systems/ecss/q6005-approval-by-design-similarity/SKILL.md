---
name: q6005-approval-by-design-similarity
description: "Determine whether a candidate hybrid microcircuit may take the shortened approval route of ECSS-Q-ST-60-05C clause 7.3.3 on documented likeness to an already approved circuit, and size what still has to be run. Use when a supplier offers a reference part in place of a full approval programme: rate every design and process attribute identical, minor-variant, major-variant or incompatible, refuse the route on an incompatible decisive attribute, on too many decisive major variants, on a lapsed or off-line reference, or on a reference held to a less demanding quality level, then derive the delta test groups and the sample the candidate still owes. Trigger: ecss, q-st-60-05-hybrid-microcircuits, hybrid-approval-by-similarity, reference-circuit-likeness, decisive-attribute-divergence, delta-test-group-derivation, shortened-approval-route."
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
  tags: [ecss, q-st-60-05-hybrid-microcircuits, hybrid-approval-by-similarity, reference-circuit-likeness, decisive-attribute-divergence, delta-test-group-derivation, shortened-approval-route]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Approval by Design Similarity (space-systems/ecss/q6005-approval-by-design-similarity)

Use when the task is the shortened approval route of ECSS-Q-ST-60-05C clause
7.3.3: granting a hybrid circuit its approval on documented likeness to a
circuit that already holds one, rather than running the whole programme again.

## Domain quick reference

- Likeness is a claim about a pair, never a property of one part. The answer
  is always "alike enough to the named reference for these purposes", and the
  reference has to be named, approved and still inside its validity window
  before any attribute is compared.
- Four things disqualify the reference itself, whatever the attributes say: it
  is not approved, its approval has aged out, it came off a different
  manufacturing line, or it was held to a less demanding quality level than
  the candidate is asking for. A reference cannot lend credit it never had.
- The attributes are not equal. Substrate technology, package family, sealing
  method, die attach, wire bonding and the manufacturing line decide whether
  the reference says anything at all; design rules, dissipation, element
  counts and layout topology only shade the answer. Weight them accordingly.
- Each attribute is rated identical, minor-variant, major-variant or
  incompatible. One incompatible decisive attribute ends the route outright.
  Several decisive attributes at major-variant also end it: enough small
  departures stop being a variant of the reference and start being a new
  design wearing the reference's name.
- What survives is a delta programme, not a waiver. Every attribute that moved
  pulls its own test groups back in -- a moved wire bond process owes bond
  pull and operating life, a moved seal owes hermeticity and residual gas --
  and the sample grows with the number of major variants.
- The weighted divergence index puts two candidates against one reference on a
  common scale, so the campaign can be ordered from the safest claim to the
  weakest. It ranks; it never grants.

## Workflow

1. Name the candidate and the single reference circuit. A candidate that
   points at itself, or at a part with no approval of its own, is not a
   similarity case.
2. Record the reference's approval state, the age of that approval in months,
   and the quality level each side is held to.
3. Rate every decisive attribute, and as many supporting attributes as the
   dossier supports. Reject the dossier outright when a decisive attribute is
   left unrated -- silence is not "identical".
4. Run the blocking checks first: unapproved reference, approval past the
   validity window, reference level below the candidate's, an incompatible
   decisive attribute, too many decisive major variants.
5. If nothing blocks, take the union of the test groups owed by the attributes
   that moved, and size the delta sample from the major-variant count.
6. Report the route, the governing attribute, the divergence index and the
   findings. Full credit is only for a pair with nothing moved at all.
7. Across a campaign, rank the granted candidates by index and carry the union
   of delta groups as the programme that still has to be paid for.

## Pitfalls

- Treating an approved reference as permanently approved. The validity window
  is part of the claim, and a lapsed approval carries nothing forward.
- Letting a pile of minor variants pass unexamined because none of them is
  major on its own. The delta groups accumulate whether the departures are
  minor or major; only the sample size cares which.
- Claiming likeness against a reference from a different manufacturing line.
  The line is a decisive attribute precisely because process control, not
  drawing content, is what the earlier approval actually demonstrated.
- Reading a lower quality level on the reference as a conservative choice. It
  is the opposite: the reference was never asked the harder questions.
- Averaging the attribute ratings into a single "mostly similar" verdict. One
  incompatible decisive attribute is not offset by ten identical ones.
- Reporting the partial route as a waiver. The delta groups are work, and the
  sample is larger, not smaller, as the major variants pile up.

## Behavior contract (gate 3)

The attribute weighting, divergence rating, blocking checks, delta-group
derivation, sample sizing and campaign ranking are exercised by the gate 3
contract test: scripts/test_q6005_approval_by_design_similarity.py against
scripts/q6005_approval_by_design_similarity_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6005_approval_by_design_similarity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
