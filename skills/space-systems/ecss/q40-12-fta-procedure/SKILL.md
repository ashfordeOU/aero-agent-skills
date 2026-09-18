---
name: q40-12-fta-procedure
description: "Execute a fault tree analysis to the IEC 61025 procedure adopted by ECSS-Q-ST-40-12C: validate the tree for dangling references, cycles and malformed AND, OR and k-out-of-n gates, expand it to minimal cut sets, evaluate those cut sets qualitatively by order, quantify the top event exactly by inclusion-exclusion and against the rare-event and min-cut-upper-bound estimates, rank contributors by Birnbaum, Fussell-Vesely and criticality importance, sweep the sensitivity of any basic event, and assemble the reporting record. Use when a tree has been drawn and the cut sets, top-event probability, importance ranking or sensitivity numbers are owed. Trigger: ecss, q-st-40-12c, iec-61025-fta-procedure, minimal-cut-set-expansion, fault-tree-top-event-quantification, fault-tree-importance-ranking, fault-tree-sensitivity-sweep."
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
  tags: [ecss, q-st-40-12c-fault-tree-analysis, q-st-40-12c, q40-12-fta-procedure, iec-61025-fta-procedure, minimal-cut-set-expansion, fault-tree-top-event-quantification, fault-tree-importance-ranking, fault-tree-sensitivity-sweep]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Fault Tree Analysis — Procedure Execution (space-systems/ecss/q40-12-fta-procedure)

Use when the task is the procedure clause of ECSS-Q-ST-40-12C — running the
adopted IEC 61025 method on a tree that already exists: construction checks,
cut set expansion, qualitative and quantitative evaluation, importance,
sensitivity, and the record that leaves the desk.

## Domain quick reference

- The procedure runs in one order and each step consumes the one before it.
  The cut sets come out of the construction, the probability comes out of the
  cut sets, and the importance and sensitivity numbers come out of the
  quantification. A number produced out of order has no traceable basis.
- Only coherent gate logic is expanded here: AND, OR and k-out-of-n. A
  k-out-of-n gate expands to every k-subset of its inputs, so a two-of-three
  vote yields three order-two cut sets. A non-coherent gate needs a different
  expansion and is refused rather than approximated.
- Construction is graded before expansion: an input that names nothing, an
  identifier used for both a gate and a basic event, a gate with a single
  input, a voting gate whose k sits outside one to n, and any cycle are all
  defects that make every downstream number meaningless.
- A cut set is minimal when no proper subset of it is also a cut set. A
  superset left in the list double counts in the quantification and inflates
  every importance share, so minimisation is part of the expansion rather than
  a tidy-up afterwards.
- The qualitative product stands on its own: the order profile, and the
  order-one cut sets, which are single point failures. That result exists
  before any probability is attached and often decides the design change.
- Three quantifications answer different questions. Inclusion-exclusion over
  the minimal cut sets is exact but costs two to the power of the cut set
  count, so it is bounded. The rare-event sum is an upper estimate that
  over-counts the overlap. The min-cut-upper-bound sits between them and stays
  affordable on a large tree.
- Importance is not one measure. Birnbaum is the swing in the top event
  between the contributor being certain and being impossible, and ignores how
  likely it is. Fussell-Vesely is the share of the top event carried by the
  cut sets that contain it. Criticality weights Birnbaum by the contributor's
  own probability. A design change is argued on Birnbaum; a data improvement
  is argued on Fussell-Vesely.
- Sensitivity is the honest treatment of a weak input: scale one basic event
  probability across a range and report how far the top event moves, so the
  reader sees which number the conclusion actually rests on.

## Workflow

1. Validate the tree. Reject dangling references, repeated inputs, duplicate
   identifiers, malformed voting gates and cycles before anything is expanded,
   and list any gate the top event never develops.
2. Expand to minimal cut sets, minimising as you go so the intermediate lists
   never carry supersets, and stop with an explicit error if the expansion
   runs away rather than truncating silently.
3. Evaluate qualitatively: build the order profile and name every order-one
   cut set as a single point failure.
4. Quantify. Take the exact value where the cut set count allows it, and carry
   the rare-event and min-cut-upper-bound values alongside so the reader can
   see the size of the approximation.
5. Rank the contributors under all three importance measures, and state which
   measure the recommendation is argued on.
6. Sweep the sensitivity of the basic events whose data basis is weakest, and
   report the factor at which the conclusion changes.
7. Assemble the record: tree, cut sets, order profile, every probability with
   its method, the importance table, the sweep, and the verdict against the
   declared target.

## Pitfalls

- Quoting the rare-event sum as the answer. It omits the overlap terms, so it
  is an over-estimate that grows with the number of cut sets, and on a tree
  with one cut set it is identical to the exact value, which is exactly why it
  looks safe until it is not.
- Comparing a quantified probability with a target by bare arithmetic. The
  exact value is a sum of signed products, so a case that sits exactly on its
  target can land a few units in the last place above it; the comparison
  absorbs that representation error while the target stays untouched.
- Taking a product over an unordered set of events. Float multiplication is
  not associative, so an unordered product can differ between runs and between
  machines; every product here is taken over a sorted event list so a rerun
  reproduces the same value.
- Reading a low Fussell-Vesely share as a robust contributor. The share is
  weighted by how likely the event already is, so an event with a very low
  probability and a huge Birnbaum swing looks unimportant right up to the
  point the probability estimate turns out to be wrong.
- Leaving an undeveloped gate on the sheet. It appears in the drawing, carries
  no cut sets and silently contributes nothing, so the tree reviewers approve
  is not the tree that was quantified.

## Behavior contract (gate 3)

The construction validation, cut set expansion and minimisation, order
profile, three quantification methods, three importance measures, sensitivity
sweep and reporting verdict are exercised by the gate 3 contract test:
scripts/test_q40_12_fta_procedure.py against
scripts/q40_12_fta_procedure_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_12_fta_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
