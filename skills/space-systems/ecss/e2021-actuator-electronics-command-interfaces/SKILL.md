---
name: e2021-actuator-electronics-command-interfaces
description: "Audit the command acceptance of a duplicated actuator electronics set against ECSS-E-ST-20-21C clause 5.2.3. Use when the task is proving each electronics chain takes arm, select and fire from either command chain: build the twelve cell acceptance matrix, name the cells never declared or declared refused, report the coverage as a fraction, separate the cross straps from the home cells and flag a cross strap that declares no isolation, then remove each command chain in turn and say which electronics chain can still take all three commands. Trigger: ecss, e-st-20-21-actuation-scope, actuator-electronics-command-interfaces, arm-select-fire-cross-strapping, command-acceptance-matrix, cross-strap-galvanic-isolation, command-chain-loss-survivability."
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
  tags: [ecss, e-st-20-21-actuation-scope, e2021-actuator-electronics-command-interfaces, arm-select-fire-cross-strapping, command-acceptance-matrix, cross-strap-galvanic-isolation, command-chain-loss-survivability, actuator-command-interface-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuation Electronics — Actuator Electronics Command Interfaces (space-systems/ecss/e2021-actuator-electronics-command-interfaces)

Use when the task is the command interface requirement of
ECSS-E-ST-20-21C clause 5.2.3 -- establishing that each actuator
electronics chain accepts the arm, the select and the fire command
from either command chain, so that losing one command chain does not
also cost an electronics chain.

## Domain quick reference

- Cross strapping is what makes two electronics chains
  interchangeable. If the nominal electronics only listens to the
  nominal command chain, the two chains are paired off one to one, and
  a single command chain failure removes an electronics chain that is
  itself perfectly healthy.
- The acceptance question has three axes, not two: which command, into
  which electronics chain, from which command chain. Three command
  types by two electronics chains by two command chains is twelve
  cells, and full cross strapping means all twelve are accepted.
- Half coverage is the usual shape of the defect. A design that
  declares only the home cells -- nominal electronics from the nominal
  command chain, redundant from redundant -- scores six of twelve and
  looks complete on a one-line-per-chain interface table, because
  nothing in that table is missing, only the pairing is.
- An undeclared cell and a cell declared as refused are the same thing
  for actuation. Both are counted as missing so that an interface
  control document which lists a cell and marks it not implemented
  cannot read as coverage.
- A cross strap carries a duty a home cell does not. It joins two
  chains that redundancy was meant to keep apart, so an unisolated
  cross strap is a path for a fault in one command chain to reach the
  electronics of the other, and the finding is raised only against
  cross straps for exactly that reason.
- The output that decides the design is the loss case. Remove each
  command chain in turn and ask which electronics chain can still take
  all three commands; an electronics chain that accepts two of the
  three from the surviving command chain cannot fire and does not
  count as a survivor.

## Workflow

1. Declare the acceptance cells: command type, receiving electronics
   chain, originating command chain, whether the command is accepted
   and whether the path is isolated. Refuse an unknown name on any of
   the three axes and refuse a cell declared twice.
2. Compare the declared set against the twelve required cells. Report
   the missing ones by all three axes and the coverage as a fraction,
   so a half cross strapped design is a number rather than an
   impression.
3. Separate the cross straps from the home cells using the home
   pairing, then check the isolation of every accepted cross strap and
   raise a finding for each that declares none.
4. Ask the question per command type as well: is arm fully cross
   strapped, is select, is fire. A design often cross straps the arm
   and select paths and leaves fire on its home chain.
5. Remove each command chain in turn and list the electronics chains
   that still accept all three commands from what remains. An empty
   list is the fatal case and is reported as such.
6. Close with a verdict and the findings that block it, each naming
   the cell or the command chain at fault.

## Pitfalls

- Reading a per-chain interface table as coverage. The table shows
  that each electronics chain has a command input; it does not show
  which command chain that input is wired to, and the pairing is the
  whole requirement.
- Counting a cell that is listed and marked not implemented. For
  actuation it is identical to a cell that was never drawn, and
  treating the two differently is how a half cross strapped design
  passes a document review.
- Cross strapping arm and select and leaving fire alone. The chain
  that cannot take a fire command is not commandable, so the two cross
  straps bought nothing on the loss case they were justified by.
- Joining the chains without isolation. A cross strap is a deliberate
  coupling between two chains that were duplicated to be independent,
  and without isolation it hands a fault on one command chain a path
  into the other side's electronics.
- Declaring survival because an electronics chain still answers. The
  survivor test is all three commands from a command chain that is
  still there, not any command from anywhere.

## Behavior contract (gate 3)

Cell validation, the twelve cell requirement, missing cell detection,
coverage fraction, cross strap separation, cross strap isolation,
per-command cross strapping, the command chain loss report and the
compliance verdict are exercised by the gate 3 contract test:
scripts/test_e2021_actuator_electronics_command_interfaces.py against
scripts/e2021_actuator_electronics_command_interfaces_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2021_actuator_electronics_command_interfaces.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
