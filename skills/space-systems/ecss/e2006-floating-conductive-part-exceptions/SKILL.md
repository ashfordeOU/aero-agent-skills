---
name: e2006-floating-conductive-part-exceptions
description: "Use when determine whether an isolated conductive part may stay ungrounded under ECSS-E-ST-20-06C clause 6.3.2: compute its capacitance to the structural reference from the exposed-area and dielectric-standoff geometry, estimate the floating-potential it reaches under the charging environment or through its leakage-resistance, evaluate the stored electrostatic-energy and the peak discharge-current that energy could deliver, and grant the small-isolated-conductor exception only when exposed-area, capacitance and stored-energy all stay inside the project limits. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c, floating-conductive-part, isolated-conductor-exception, exposed-area-limit, stored-electrostatic-energy, capacitance-to-structure, electrostatic-discharge-hazard."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-floating-conductive-part-exceptions, floating-conductive-part, isolated-conductor-exception, exposed-area-limit, stored-electrostatic-energy, capacitance-to-structure, electrostatic-discharge-hazard]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Scope — Floating Conductive Part Exceptions (space-systems/ecss/e2006-floating-conductive-part-exceptions)

Use when the task is the clause 6.3.2 exception of ECSS-E-ST-20-06C —
deciding whether a conductive part that is not tied to the structural
reference is small enough to be left that way, or whether it has to be
grounded.

## Domain quick reference

- The exception is granted on three independent criteria, and all three
  have to hold: the part's exposed area, its capacitance to the
  structural reference, and the electrostatic energy it can store at the
  potential it floats to. Any one criterion alone is not the rule —
  a physically tiny fastener sitting behind a thin dielectric can still
  hold a large capacitance, and a large panel at low potential can still
  store a damaging amount of energy.
- Capacitance comes from the geometry, so the part has to declare one of
  three consistent forms: a measured capacitance, a plate-like standoff
  (exposed area over a dielectric gap, scaled by the relative
  permittivity), or a compact body approximated by its equivalent
  radius. Declaring more than one form invites a silent contradiction;
  declaring none leaves the criterion unevaluated, which is a finding
  rather than a pass.
- The floating potential is bounded by the charging environment, but a
  part with a finite leakage path to the structural reference never
  reaches it: the leakage resistance clamps the potential to the
  collected current times that resistance. Take the lower of the two.
  A part with no leakage path at all floats to the environment value.
- Stored energy scales with the square of the potential, so halving the
  potential quarters the energy — clamping through a deliberate high-
  value bleed resistor is usually cheaper than re-designing the part.
  The peak discharge current the stored energy can deliver follows from
  the charge divided by the discharge rise time, and is what couples
  into nearby harness as a transient.
- Energy bands separate a benign discharge from one credible for upset
  and one credible for damage. The band is an engineering aid for
  prioritising; the exception itself is decided by the limits.

## Workflow

1. Collect the part's exposed area, its declared capacitance form, any
   leakage resistance to the structural reference, and the discharge
   rise time to be assumed. Reject a part declaring two capacitance
   forms at once, and a part declaring none.
2. Resolve the capacitance to the structural reference from whichever
   single form was declared.
3. Bound the floating potential: take the environment-driven potential,
   and where a leakage path exists compute the clamped potential from
   the collected current across that resistance; the governing value is
   the lower of the two.
4. Compute the stored electrostatic energy at the governing potential,
   and the peak discharge current it could deliver over the assumed
   rise time.
5. Test the three exception criteria — exposed area, capacitance, stored
   energy — against the project limits, absorbing float representation
   error at a boundary with a relative tolerance rather than by raising
   a limit. Record every criterion that fails, not just the first.
6. Grant the exception only when all three criteria hold. Otherwise the
   part is to be bonded to the structural reference; report the criteria
   that drove the decision and the energy band for prioritisation.

## Pitfalls

- Granting the exception on small size alone. A small part behind a
  thin, high-permittivity standoff can exceed the capacitance criterion
  while passing the area criterion comfortably.
- Using the environment potential when a leakage path exists. The clamp
  is often one or two decades lower, and ignoring it refuses parts that
  actually comply.
- Using the clamped potential when the leakage path is not a real
  designed path. A resistance nobody specified and nobody inspects is
  not a clamp; treat the part as fully floating.
- Stopping at the first failing criterion. The set of failures is what
  tells a designer whether to shrink the part, thicken the standoff or
  add a bleed path.
- Raising a limit so an exact-boundary part passes. The drift is
  representation error in a product of powers of ten; absorb it in the
  comparison and leave the limit where the project set it.

## Behavior contract (gate 3)

The capacitance-form resolution, leakage clamp, stored-energy and peak
discharge-current computation, three-criterion exception decision and
inventory aggregation are exercised by the gate 3 contract test:
scripts/test_e2006_floating_conductive_part_exceptions.py against
scripts/e2006_floating_conductive_part_exceptions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_floating_conductive_part_exceptions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
