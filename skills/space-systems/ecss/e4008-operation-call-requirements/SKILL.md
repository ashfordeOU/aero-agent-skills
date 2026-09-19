---
name: e4008-operation-call-requirements
description: "Validate the operation calls a simulation configuration issues against the eight obligations of ECSS-E-ST-40-08 clause 5.2.4.2. Use when the task is grading an ordered configuration sequence: confirming the operation is declared, published and invokable before the run starts, that every argument names a parameter and no parameter is bound twice, that each in and inout parameter is supplied while out parameters are left to the model, that values match their declared types and inclusive ranges, and that the target instance already exists at the step the call is reached. Trigger: ecss, e-st-40-08, configuration-operation-call, operation-parameter-direction, inout-parameter-supply, out-parameter-no-value, configuration-time-invokability, call-before-instantiation-ordering."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-operation-call-requirements, configuration-operation-call, operation-parameter-direction, out-parameter-no-value, configuration-time-invokability, call-before-instantiation-ordering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling Platform — Operation Call Requirements (space-systems/ecss/e4008-operation-call-requirements)

Use when the task is the operation-call check of ECSS-E-ST-40-08 clause
5.2.4.2 -- deciding whether a call the configuration makes on a model
instance can be issued at all, whether its argument list binds, and
whether it sits at a legal point in the configuration sequence.

## Domain quick reference

- A configuration is an ordered sequence, not a set. Instances are
  created and operations are called on them, and a call that precedes
  the creation of its target has nothing to run against. Grading the
  calls as an unordered collection loses that item entirely.
- Publication and configuration-time invokability are two different
  properties. A published operation that only makes sense while the
  simulation is stepping is declared, visible and still not a
  configuration action; reporting it as undeclared sends the reviewer
  hunting for a spelling mistake.
- Parameter direction governs who supplies the value. In and inout
  parameters are the caller's obligation; an out parameter is the
  model's product and giving it a value is a defect, not a harmless
  extra. The two failures are separate items because the repairs are
  opposite -- add an argument versus delete one.
- Inout is the direction most often mis-handled. It is supplied by the
  caller and written back by the model, so omitting it is a missing
  argument even though the model will also write to it.
- An operation with no parameters is normal. A reset or an arm call
  binds nothing and should grade clean rather than trip an arity rule.
- Declared numeric bounds are inclusive, and a boolean is not an
  integer. Both are cheap ways to turn a legal call red or let a
  mis-wired one through.
- An undeclared operation cannot be graded on its arguments, so its
  shape items are recorded as failed-and-ungraded rather than passed;
  only the sequencing item, which does not depend on the declaration,
  is still meaningful.

## Workflow

1. Build the operation table once from the target type's declarations,
   refusing a duplicate operation, a duplicate parameter, an unknown
   direction or an unsupported parameter type.
2. Walk the configuration steps in order, adding each instantiated
   instance to a created set and refusing a document that creates the
   same instance twice.
3. At each call, grade the sequencing item first against the created
   set -- it is the one item that survives an unrecognised operation.
4. Resolve the operation. Treat unpublished exactly as undeclared for
   the first item, and mark the remaining shape items failed rather
   than silently passed.
5. Grade configuration-time invokability separately from publication.
6. Walk the supplied arguments: unknown name, second binding, a value
   on an out parameter, then type, then constraint -- stopping at the
   first failure for that argument so one defect makes one finding.
7. Walk the declared parameters for any in or inout parameter that
   received nothing.
8. Roll up per-call records with the eight verdicts, the satisfied
   count and findings prefixed by target and operation.

## Pitfalls

- Grading calls without their position in the sequence. Every call can
  be individually well-formed and the document still call into an
  instance that does not exist yet.
- Treating an out parameter as optional-and-harmless. Supplying it
  overwrites a value the model owns, and the call may be rejected at
  run time for a reason the configuration review never raised.
- Omitting an inout argument because the model writes to it. It is an
  input as well, and the initial value is the caller's to provide.
- Reporting a run-time-only operation as undeclared. It is declared;
  the defect is when it is being called, not whether it exists.
- Applying an arity rule that assumes at least one parameter. A
  parameterless operation is a normal configuration action.
- Using strict comparisons on inclusive parameter bounds, or accepting
  a boolean where an integer parameter was declared.

## Behavior contract (gate 3)

Operation-table construction, publication and invokability gating,
argument-name resolution, duplicate binding, direction handling for in,
out and inout parameters, type and inclusive-constraint conformance,
creation-before-call sequencing and the eight-item roll-up are
exercised by the gate 3 contract test:
scripts/test_e4008_operation_call_requirements.py against
scripts/e4008_operation_call_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_operation_call_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
