---
name: q2007-organization
description: "Define the test-centre organization ECSS-Q-ST-20-07 clause 5.3.1 asks for, and say whether the chart in place supports quality and safety management. Use when a test centre's structure is being drawn or audited: refuse a chart never defined, prove the reporting structure is one tree by catching an orphan parent, a reporting cycle and a second root, name the quality and safety functions no unit actually holds, walk each assurance holder up its reporting chain and flag one that reports through the test-operations line, and separate a required interface nobody declared from a declared interface naming a unit the chart does not hold. Trigger: ecss, q-st-20-07-clause-5-3-1, test-centre-organization-structure, test-centre-assurance-independence, test-centre-function-assignment, test-centre-interface-declaration."
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
  tags: [ecss, q-st-20-07-test-centre-quality-and-safety-scope, q2007-organization, q-st-20-07-clause-5-3-1, test-centre-organization-structure, test-centre-assurance-independence, test-centre-function-assignment, test-centre-interface-declaration, test-centre-reporting-chain]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test-Centre Quality and Safety — Organization (space-systems/ecss/q2007-organization)

Use when the task is clause 5.3.1 of ECSS-Q-ST-20-07: the test centre
defines the organization behind its quality and safety management — the
units, the reporting structure joining them, the functions that have to
live somewhere in it, and the interfaces those functions work across.

## Domain quick reference

- A chart is a tree and the tree has to be provable before anything else
  is asked of it. A unit reporting to a parent the chart does not hold
  is an orphan, a unit reachable from itself is a cycle, and a chart
  with two roots is two organizations. Every later walk runs up a
  reporting chain, so none of them terminate until these are cleared.
- A function exists where somebody holds it, not where the chart draws a
  box. A unit named after quality assurance that holds no assurance
  function leaves the function unassigned, and the naming is exactly
  what makes that gap easy to miss on a visual review.
- A function held by two units is not a gap. It is shared ownership,
  carried as an advisory, because two holders is a coordination question
  and zero holders is a compliance one.
- Assurance only assures when it does not report to what it grades. The
  test is a walk from each assurance holder to the root, and an
  operations unit anywhere on that chain is the defect — one level up or
  three, the reporting pressure is the same.
- The reverse arrangement is not symmetrical. Operations reporting under
  assurance keeps the grading line clean and is not a finding.
- An interface is a declared pair and both ends have to exist. A
  required pair with no declaration is a gap; a declaration naming an
  unheld unit is a wrong entry. Two required functions living inside one
  unit need no declaration at all, because there is no interface to
  cross.

## Workflow

1. Validate the chart: non-empty unit identifiers, recognised function
   names, no unit registered twice, no unit reporting to itself, no
   interface joining a unit to itself and no interface declared twice.
2. Take the structural defects first — orphan parents, reporting cycles,
   no root, more than one root — and stop there if any are present. A
   chart that is not a tree cannot answer the later questions.
3. Take the required functions no unit holds, and separately the
   required functions more than one unit holds.
4. Walk each quality and safety assurance holder up its reporting chain
   to the root and record any chain passing through a unit that holds
   the test-operations function.
5. Take the interface gaps against the required function pairs, skipping
   a pair whose function nobody holds because that is already reported
   as an unassigned function, and treating two functions inside one unit
   as joined.
6. Take the declared interfaces naming a unit the chart does not hold.
7. Close on one verdict in order: organization undefined, structure
   invalid, function unassigned, assurance independence compromised,
   interface undeclared, or organization defined. Report the named
   units, functions and pairs alongside it, and carry the shared
   functions as advisories.

## Pitfalls

- Reading a unit's name as a function assignment. The box labelled
  quality assurance can hold nothing, and a review that reads the chart
  visually will pass a centre with no assurance function at all.
- Checking independence only one level up. An assurance unit reporting
  to a test floor that reports to operations is under operations; only
  the full walk to the root finds it.
- Counting a shared function as a compliance defect. Two holders need
  coordinating; the clause is answered as long as somebody holds it.
- Asking about functions before the chart is a tree. A reporting cycle
  makes the independence walk non-terminating, which is why the
  structural check is a stop and not a finding alongside the others.
- Reporting a required interface as missing when nobody holds one of its
  functions. The real defect is the unassigned function, and reporting
  both doubles one problem and hides its cause.

## Behavior contract (gate 3)

The unit and interface validation, the orphan, cycle and root checks,
the reporting-chain walk, the unassigned and shared functions, the
assurance independence defects, the dangling interfaces, the interface
gaps and the ordered verdict are exercised by the gate 3 contract test:
scripts/test_q2007_organization.py against
scripts/q2007_organization_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_organization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
