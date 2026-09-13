---
name: e2008-sca-identification-and-traceability
description: "Audit the permanent coding of delivered cell assemblies against the traceability depth the process document sets, under ECSS-E-ST-20-08C clause 6.1.4. Use when a delivery register has to show each assembly stays identifiable after it is bonded into a panel: judge whether the marking survives the processing the assembly will see, read the depth the code fields and the register actually reach, compare it with the depth the process document demands, detect a code repeated across the delivered set, and name the weakest assembly. Trigger: ecss, e-st-20-08c, sca-permanent-coding-scheme, delivered-cell-assembly-traceability-depth, cell-assembly-marking-permanence, sca-code-uniqueness-register, process-document-traceability-depth, sca-delivery-lot-coding-audit."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-sca-identification-and-traceability, sca-permanent-coding-scheme, delivered-cell-assembly-traceability-depth, cell-assembly-marking-permanence, sca-code-uniqueness-register, process-document-traceability-depth, sca-delivery-lot-coding-audit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Identification and Traceability (space-systems/ecss/e2008-sca-identification-and-traceability)

Use when the task is clause 6.1.4 of ECSS-E-ST-20-08C: every delivered
cell assembly carries a permanent code, and that code has to still work
after the assembly stops being a loose item -- after it is handled,
bonded down, cured and cycled. How far the code has to reach is not a
constant; the process identification document sets the depth, and the
scheme is graded against that depth rather than against a house habit.

## Domain quick reference

- Two properties make a coding scheme, and both have to hold. The mark
  has to be permanent against the processing the assembly will actually
  see, and the code has to reach the depth the process document asks
  for. Either one failing leaves the assembly unidentified, but they
  fail for different reasons and have different repairs.
- Permanence is a property of the pairing, never of the marking method
  alone. An engraved code survives everything. A fired-on ink code
  survives bonding and cure and loses legibility under cycling. An
  adhered label survives shipping and is gone at the first cure. A
  record-only scheme marks nothing at all and has no fallback of any
  kind.
- Depth runs in four steps: nothing, the delivery lot, the individual
  assembly, and the constituent lots the assembly was built from. A lot
  code cannot tell two assemblies apart. A serial identifies the
  assembly and reaches no further on its own. Constituent depth is
  reached either by coding the constituent lot into the mark or by a
  serial plus a delivery register that resolves it.
- A register only helps if the hardware can be used to enter it. A
  register that resolves constituent lots but keys on something the
  assembly does not carry is a table nobody can look anything up in.
- Uniqueness is a property of the delivered set, not of one code. A
  code repeated across two assemblies resolves to a set rather than to
  an assembly, and it cannot be found by grading any single assembly --
  only by comparing the set.
- The useful summary is the share of the delivery that reaches the
  required depth plus the weakest assembly by name, because a shortfall
  measured in steps tells a process engineer what to change and a pass
  count does not.

## Workflow

1. Take the delivery with its identifier, the depth the process
   identification document requires, and one record per assembly: its
   code, the marking method, the processing the assembly will see, the
   fields the code carries and whether a delivery register resolves the
   constituent lots.
2. Decide permanence from the marking method against the exposure, not
   from the method alone, and report a mark that is lost at a later
   step as a finding aimed at that step.
3. Read the depth the scheme actually reaches from the coded fields
   together with the register, and flag a register that has no serial
   to key on.
4. Compare the reached depth with the required depth and record the
   shortfall in steps. Reject a process document that requires no depth
   at all; it grades nothing.
5. Grade each assembly: coding not established when the mark does not
   survive or no field identifies anything, below the required depth
   when it survives but falls short, and compliant otherwise.
6. Compare the codes across the delivered set for repeats, then roll
   up: the verdict, the assemblies with no coding established, the
   compliant share and the weakest assembly by verdict then by the size
   of its shortfall.

## Pitfalls

- Grading the marking method and stopping there. An engraved code and
  an adhered label look equally identified in the stores; one of them
  is anonymous the moment the assembly is bonded down, and the adequacy
  question is always the method against the processing.
- Treating a serial as the end of the chain. A serialised assembly
  whose constituent lots are unreachable satisfies a process document
  that asks for assembly depth and fails one that asks for constituent
  depth, and only the document decides which.
- Crediting a delivery register that the hardware cannot be used to
  enter. The register is only a bridge when the mark carries the key it
  is indexed on.
- Checking uniqueness one assembly at a time. A repeated code is
  invisible in every individual record and only appears when the
  delivered set is compared with itself.
- Reporting a shortfall as a pass flag. Two steps short and one step
  short call for different repairs, and a flag reports them
  identically.
- Comparing a compliant share against its expectation with bare
  arithmetic. The share is a quotient of two assembly counts, so a
  delivery landing exactly on its expected share can evaluate a unit in
  the last place below it and read as short on one platform and as met
  on another.

## Behavior contract (gate 3)

The marking permanence pairing, the reached-depth reading, the
shortfall in steps against the process document, the delivered-set
uniqueness check, the per-assembly grading and the delivery roll-up are
exercised by the gate 3 contract test:
scripts/test_e2008_sca_identification_and_traceability.py against
scripts/e2008_sca_identification_and_traceability_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_sca_identification_and_traceability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
