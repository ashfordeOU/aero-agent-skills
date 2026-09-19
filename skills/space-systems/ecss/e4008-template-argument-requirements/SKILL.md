---
name: e4008-template-argument-requirements
description: "Verify a template argument list against the parameters its catalogue element declares, under ECSS-E-ST-40-08 clause 5.2.1.2. Use when the task is binding arguments before instantiation: confirming each argument names a declared parameter, that no parameter is bound twice, that every mandatory parameter is supplied and every unsupplied optional carries a default, that positional arguments run contiguously ahead of the named ones and stay inside the parameter list, that each value matches its declared type and its inclusive constraint, and that a reference value resolves to an element the configuration holds. Trigger: ecss, e-st-40-08, template-argument-binding, declared-parameter-match, mandatory-parameter-coverage, positional-argument-ordering, template-argument-type-conformance, template-argument-constraint-range, template-reference-resolution."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-template-argument-requirements, template-argument-binding, declared-parameter-match, positional-argument-ordering, template-argument-type-conformance, template-reference-resolution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling Platform — Template Argument Requirements (space-systems/ecss/e4008-template-argument-requirements)

Use when the task is the argument-binding check of ECSS-E-ST-40-08
clause 5.2.1.2 -- deciding whether the argument list a configuration
supplies to a parameterised catalogue element can actually be bound to
that element's declared parameters, and which of the nine obligations
it misses when it cannot.

## Domain quick reference

- Binding is a two-sided walk. The argument list is traversed to find
  arguments with no parameter, and the parameter table is traversed to
  find parameters with no argument. Running only the first direction
  passes an argument list that quietly omits a mandatory parameter.
- Positional and named arguments are graded by two separate items. The
  ordering item asks that positional arguments are contiguous from the
  first parameter and all sit ahead of the first named one; the range
  item asks that no position reaches past the declared list. A list can
  be ordered correctly and still overrun, and the repairs differ.
- Mandatory and optional parameters carry opposite obligations. A
  mandatory parameter may not declare a default at all, and an optional
  one left unsupplied must have a default to fall back on; an optional
  parameter with neither an argument nor a default leaves the
  instantiation under-determined.
- Type conformance is checked before the constraint. A value of the
  wrong type cannot be meaningfully compared with a numeric bound, so
  the constraint item is left alone once the type item has failed --
  otherwise one defect is reported twice and inflates the finding count.
- Booleans are not integers here. Accepting a boolean where an integer
  parameter was declared is the cheapest way to let a mis-wired
  argument through, so the type test excludes it explicitly.
- Numeric bounds are inclusive. A value sitting exactly on a declared
  minimum or maximum is compliant, and grading it with a strict
  comparison turns a legal configuration red.

## Workflow

1. Build the parameter table once, refusing a template that declares a
   parameter twice, names an unsupported type, or marks a parameter
   mandatory while also giving it a default.
2. Decide the form of each argument -- positional or named -- refusing
   an argument that gives both, gives neither, or carries no value.
3. Walk the arguments in order, tracking the next expected position and
   whether a named argument has already been seen, so an ordering
   breach is attributed to the argument that caused it.
4. Bind each argument to its parameter, recording a second binding as a
   duplicate rather than letting the later value win silently.
5. Check the value type, then the declared constraint, then reference
   resolution, stopping at the first of the three that fails for that
   argument.
6. Walk the parameter table for anything still unbound: mandatory
   parameters become findings, optional ones take their default, and
   optional ones without a default become findings of their own.
7. Report the resolved argument map, the nine per-item verdicts and the
   satisfied count so a near-miss is distinguishable from a wholesale
   mis-binding.

## Pitfalls

- Treating a missing argument and an unknown argument as one defect.
  They are separate items with separate repairs, and an argument list
  can carry both at once.
- Letting a later argument overwrite an earlier binding. The duplicate
  is the finding; silently taking the last value makes the resolved map
  depend on document order.
- Grading a value against a numeric bound before checking its type. A
  string compared with a minimum raises or coerces, and either way the
  reported defect is the wrong one.
- Using strict inequalities on the declared bounds. The bounds are
  inclusive, and a value that should sit exactly on one will land a few
  representation units either side of it in floating point.
- Accepting a boolean for an integer parameter because it compares
  equal. The declared type is the contract, not the comparison.
- Assuming an unsupplied optional is harmless. Without a default the
  instantiation has no value to use, which is a finding, not a silence.

## Behavior contract (gate 3)

Parameter-table construction, argument form detection, positional
ordering and range, duplicate binding, type conformance, inclusive
constraint checking, reference resolution, default fill-in and the
nine-item roll-up are exercised by the gate 3 contract test:
scripts/test_e4008_template_argument_requirements.py against
scripts/e4008_template_argument_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_template_argument_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
