---
name: e7041-obcp-definition
description: "Validate an on-board control procedure definition before it is ever loaded, under ECSS-E-ST-70-41C clause 6.18.4.1. Use when the task is deciding whether a procedure the ground wrote can actually run aboard: checking identity and version against the definition store, matching it to an engine that carries the right language and a large enough procedure limit, separating mandatory arguments from defaulted ones, refusing an activation value of the wrong type, digesting a definition so ground and spacecraft cannot disagree about which build is aboard, and sizing a whole definition set against the store. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, obcp-definition, on-board-control-procedure-definition, obcp-engine-procedure-limit, obcp-argument-binding, obcp-definition-store-sizing."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-obcp-definition, on-board-control-procedure-definition, obcp-engine-procedure-limit, obcp-argument-binding, obcp-definition-digest, obcp-definition-store-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — OBCP Definition (space-systems/ecss/e7041-obcp-definition)

Use when the task is the on-board control procedure definition of
ECSS-E-ST-70-41C clause 6.18.4.1 -- the static, checkable description
the ground hands over before a procedure can ever be loaded, let alone
run.

## Domain quick reference

- An on-board control procedure is a small program the spacecraft runs
  by itself, so a sequence that has to react faster than a round trip
  -- a safing chain, a deployment, an instrument warm-up -- does not
  wait for the ground. The definition is everything that has to be true
  about it before it goes aboard.
- A definition settles four things and no more: an identity, the engine
  that interprets it, the arguments the ground may set at activation,
  and the observability level the ground expects to watch it at.
  Anything else belongs to loading or to execution, not here.
- Identity is a pair, not a name. Two procedures can share an id and
  differ in version, and a ground that tracks only the id will
  eventually command the wrong build. Grade the pair.
- An engine is not interchangeable with another engine. It carries a
  language and a maximum procedure size, and a procedure written for
  one is not runnable by another however similar the source looks.
- An argument is mandatory unless it declares a default. That single
  distinction is the whole of the activation contract: a mandatory
  argument with no value at activation is an activation that must not
  be attempted, and a default of the wrong type is a fault planted at
  definition time that only fires much later.
- Observability belongs to the definition because it decides what the
  engine has to instrument before the procedure is loaded. Asking for
  step-level visibility from an engine that only reports at procedure
  level is not an error the engine can repair at run time; the ground
  simply sees less than it was promised.
- A definition store has a finite size in octets. A set of definitions
  that each pass on their own can still not fit together, and the one
  that does not fit is decided by the order they are offered in.

## Workflow

1. Validate the definition: a non-empty id, a version of at least one,
   a named engine, a code size and step count of at least one, and a
   known observability level. Default the level to procedure level only
   when the definition omits it.
2. Validate every declared argument. Reject a duplicate name outright,
   and reject a default whose value does not match its declared type.
3. Resolve the engine. An unnamed or absent engine is a rejection, not
   a finding -- nothing aboard can interpret the procedure.
4. Compare the code size against the engine's procedure limit. Equal to
   the limit fits; over it is a rejection.
5. Compare the requested observability level against what the engine
   supports. A gap here is a finding, because the procedure still runs.
6. Separate mandatory arguments from defaulted ones and report the
   mandatory list, so the activation command can be written correctly.
7. Bind supplied values when an activation is being prepared: refuse an
   undeclared name, refuse a value of the wrong type, fill from the
   default where one exists, and raise on a mandatory argument with no
   value.
8. Digest the graded fields to compare two definitions. Agreement of
   digests, not of ids, is what says the same build is aboard.
9. Accumulate admissible definitions against the store capacity in
   offer order, and report the used, free and fill figures with the
   dispositions grouped.

## Pitfalls

- Tracking a procedure by id alone. The version is half the identity,
  and the half that changes.
- Treating a boolean as an integer argument. Python accepts it
  silently, the on-board engine does not, and the fault surfaces as a
  procedure that took a branch nobody predicted.
- Reading a missing observability level as no observability. An omitted
  level is procedure level by default; no observability is a level the
  definition has to ask for on purpose.
- Rejecting a procedure that is exactly at the engine's size limit. The
  limit is inclusive, and a strict comparison here throws away a
  procedure that fits.
- Letting a rejected definition consume store space. A definition that
  is never loaded occupies nothing, and charging it makes a later
  definition fail for a reason that does not exist.
- Comparing a fill fraction against a capacity with a strict
  inequality. Occupancy is exact in octets, so decide admission on the
  integers and keep the fraction for reporting.

## Behavior contract (gate 3)

The definition and argument validation, type matching, mandatory versus
defaulted separation, activation binding, definition digest, engine
resolution, procedure size limit, observability gap finding and the
store-sizing pass over a definition set are exercised by the gate 3
contract test: scripts/test_e7041_obcp_definition.py against
scripts/e7041_obcp_definition_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_obcp_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
