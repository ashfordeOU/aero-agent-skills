---
name: n2-diagram
description: "Use when you must build or review an N2 interface diagram for an aerospace systems engineering model: derive the NxN interface matrix from the function or component list and the interface pair list, count the interfaces per element from the row and column sums, flag the missing data links against the required interface list, and identify isolated elements with no interfaces. Produces the interface matrix, the per-element interface counts, and the missing link and isolation report that gate the interface requirements review. Trigger: N2 diagram, N2 interface matrix, interface pair, data link, interface count, missing interface."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: mbse
  tags: [n2-diagram, n2-interface-matrix, n2-chart, interface-pair-count, missing-data-link]
  version: 0.1.0
  author: AeroSkills
---

# N2 Interface Diagram (systems-engineering-safety/mbse/n2-diagram)

Use when the task is interface analysis for a model-based systems
engineering program: building the N2 interface matrix from the
element list and interface pairs, counting interfaces per element,
and reviewing the model for missing data links and isolated
elements.

## Domain quick reference

- An N2 diagram arranges the system functions or components along
  the matrix diagonal; every off-diagonal cell (row i, column j)
  records the data interfaces from element i to element j.
- Cell value: the number of interface pairs from the row element to
  the column element (1 for a single link, 2 for a duplicated pair,
  0 for none).
- Interface count per element: row sum (outgoing) plus column sum
  (incoming); each interface is counted once per endpoint.
- Total interface entries: sum of every off-diagonal cell; equals
  the number of interface pairs when the pairs are unique.
- Missing data link: a required interface pair whose cell value is
  zero; the review lists each absent pair in the required order.
- Isolated element: an element with zero outgoing and zero incoming
  interfaces; the review flags it as unconnected.
- N2 interface analysis supports the interface requirements capture
  in the ARP4754A system development process: functions and their
  data interfaces are defined and reviewed before integration.

## Workflow

1. Collect the ordered element list (functions or components) and
   the interface pair list (source, target).
2. Build the matrix with build_matrix; validate that every endpoint
   exists and no self interface is present.
3. Compute the per-element counts with interface_counts and the
   total with total_interfaces.
4. Compare the matrix against the required interface list with
   missing_links; list every absent pair.
5. Identify elements with no connections with isolated_elements.
6. Render the matrix with render_matrix and gate the interface
   requirements review on the missing link and isolation report.

## Pitfalls

- Reversing the pair order: an interface from A to B sits in row A
  column B, not row B column A; the direction matters for the
  review.
- Double counting by design: the per-element count is the row plus
  column sum, so an element that sends k and receives m links has
  count k + m.
- Treating the diagonal as an interface cell: the diagonal holds the
  element itself, and a self interface pair is an input error, not a
  link.
- Forgetting the required list: missing_links only compares against
  the required pairs you provide; the function cannot invent
  requirements.
- Mixing decomposition levels in one matrix: the N2 diagram is a
  single-level view, so keep every element at the same level.
- Ignoring isolated elements: a zero-count element is a modeling
  gap, not a harmless empty row.

## Behavior contract (gate 3)

The matrix build, count, and review logic is exercised by the gate 3
contract test: scripts/test_n2_diagram.py against
scripts/n2_diagram_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_n2_diagram.py

## Compliance

- Standards referenced, not reproduced: ARP4754A text is proprietary
  (SAE); summary-only per standards-map.yaml. The N2 chart method is
  common systems engineering methodology.
- compliance: STANDARDS-REF, gated: false.
