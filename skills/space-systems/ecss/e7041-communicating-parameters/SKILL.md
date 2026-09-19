---
name: e7041-communicating-parameters
description: "Validate the parameter interface an on-board control procedure exchanges with the OBCP engine that hosts it, under ECSS-E-ST-70-41C clause 6.18.4.7. Use when an activation is rejected for an argument the ground believes it supplied, or when a procedure runs on a value nobody gave it: binding supplied arguments to declared parameters by name, refusing an undeclared name instead of dropping it, filling an omitted optional input from its declared default, refusing an omitted mandatory one, type- and range-checking every bound value, blocking a write to an input-only parameter, and listing the outputs the engine must keep observable while the run is in progress. Trigger: ecss, e-st-70-41c, obcp-parameter-communication, obcp-activation-argument-binding, obcp-input-only-parameter-write, obcp-observable-output-parameter, obcp-parameter-default-substitution, obcp-undeclared-activation-argument."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-communicating-parameters, obcp-parameter-communication, obcp-activation-argument-binding, obcp-input-only-parameter-write, obcp-observable-output-parameter, obcp-parameter-default-substitution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Communicating Parameters with an OBCP (space-systems/ecss/e7041-communicating-parameters)

Use when the task is the parameter communication of ECSS-E-ST-70-41C
clause 6.18.4.7 -- the six requirements that fix how an on-board
control procedure and the engine hosting it hand values to each other,
and what the ground is allowed to see while a procedure runs.

## Domain quick reference

- The interface is declared before anyone activates anything. A
  procedure states each parameter it communicates: a name, a
  direction, a type, and for an input a range and optionally a
  default. An activation cannot introduce a parameter the procedure
  never declared, and the engine is not permitted to guess one.
- Binding is by name, never by position. An activation supplies a
  mapping of names to values, so reordering the arguments changes
  nothing and a renamed parameter fails loudly instead of quietly
  taking the neighbouring value.
- A name the interface does not declare is a rejection, not something
  to ignore. In practice it means the ground is holding a different
  revision of the procedure than the one loaded on board, and letting
  the activation proceed runs the loaded revision on values chosen for
  a different one.
- Direction is a permission, not documentation. An input is written by
  the activation and read by the procedure; an output is written by
  the procedure and read by the ground; an in-out is both. A value
  supplied for an output, and a procedure writing to an input, are
  both interface violations.
- A default is what an omitted optional input takes, and it is a fact
  about the procedure, not about the activation. A parameter that is
  mandatory has no default: the two are alternatives, because a
  mandatory parameter with a default can never be detected as missing.
- The declared outputs are what the engine keeps observable during the
  run. A procedure that declares none can be watched only by its
  completion report, which is an interface decision worth naming
  rather than an accident to discover during an anomaly.
- Range and type checking happens at binding time, on the engine side.
  A procedure that has to defend itself against its own activation
  arguments is carrying the engine's job in its step logic.

## Workflow

1. Normalise every declared parameter: a non-empty name, a direction
   from the permitted set, a known type, both ends of a range or
   neither, and a permitted value list for an enumerated parameter.
2. Refuse a declaration that is mandatory and also carries a default,
   and refuse a default whose type does not match the declaration.
3. Build the interface as a lookup by name and refuse a name declared
   twice -- a duplicate silently shadows one of the two.
4. Bind the activation: for each supplied name find its parameter,
   reject an undeclared name and a value supplied for an output, then
   type-check and range-check what remains.
5. Sweep the declared inputs the activation did not supply: substitute
   a default where one exists, and raise a missing-mandatory finding
   where one does not.
6. Grade the parameters the running procedure writes back, so a write
   to an input-only parameter is caught against the same interface the
   activation was bound against.
7. List the observable outputs and report an interface that declares
   none, then decide acceptance: defaults and the no-output note are
   informational, everything else blocks the activation.

## Pitfalls

- Dropping an unrecognised argument and activating anyway. The run
  then uses defaults the ground never intended, and the telemetry
  looks like a procedure that misbehaved rather than one that was
  misconfigured.
- Binding by position because the ground and the procedure "agree on
  the order". They agree until one of them is revised.
- Giving a mandatory parameter a default so the activation stops
  failing. The failure was the detection; removing it does not supply
  the value.
- Treating direction as a comment. An in-out parameter and an input
  look identical in a parameter table and behave differently the first
  time a procedure writes back.
- Range-checking inside the procedure instead of at binding. The
  procedure has already started, so a bad value now costs a
  termination rather than a rejected activation.
- Declaring no outputs on a long-running procedure. Nothing is wrong
  until an anomaly, at which point the only evidence is that it has
  not finished.

## Behavior contract (gate 3)

The declaration normalisation, duplicate-name refusal,
mandatory-versus-default exclusivity, name-based binding, undeclared
name rejection, output-supplied rejection, type and range checking,
default substitution, missing-mandatory detection, input-only write
detection and the observable-output listing are exercised by the gate 3
contract test: scripts/test_e7041_communicating_parameters.py against
scripts/e7041_communicating_parameters_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_communicating_parameters.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
