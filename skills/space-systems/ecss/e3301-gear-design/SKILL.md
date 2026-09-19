---
name: e3301-gear-design
description: "Design a mechanism gear mesh against ECSS-E-ST-33-01C clause 4.7.5.4.7. Use when a spur or helical stage must be shown good for tooth strength, flank wear, backlash and life together: forming the tangential tooth force from module and torque, computing the Lewis bending stress and the Hertzian flank contact stress, derating both material allowables for the required tooth load cycles, sweeping backlash across the thermal range for the gear-to-housing expansion mismatch, and checking the lubricant against that range, the flank stress and the gear material. Trigger: ecss, e-st-33-01-mechanisms-scope, gear-tooth-bending-stress, gear-flank-contact-stress, gear-backlash-thermal-range, gear-lubricant-compatibility, gear-tooth-load-cycles, lewis-form-factor."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-gear-design, gear-tooth-bending-stress, gear-flank-contact-stress, gear-backlash-thermal-range, gear-lubricant-compatibility, gear-tooth-load-cycles, lewis-form-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Gear Design (space-systems/ecss/e3301-gear-design)

Use when the task is the gear design of ECSS-E-ST-33-01C clause
4.7.5.4.7 -- showing that a mesh inside a space mechanism carries its
torque without breaking a tooth or pitting a flank, keeps a positive
and bounded backlash over the whole thermal range, sits in a lubricant
it is compatible with, and does all of that for the required number of
tooth load cycles.

## Domain quick reference

- A gear mesh has two independent strength checks, not one. Tooth
  bending is a root-fillet stress that scales linearly with tooth force;
  flank durability is a Hertzian contact stress that scales with the
  square root of it. A change that fixes one -- a finer module, a wider
  face, a different material -- moves the other by a different amount,
  so both are recomputed after every change.
- The Lewis form factor is a function of tooth count, and it falls
  sharply below about twenty teeth. A pinion chosen small to fit a
  packaging envelope pays for it twice: fewer teeth carry the same
  torque at a smaller pitch diameter, and each of those teeth is
  intrinsically weaker in bending.
- Flank contact stress carries the elastic coefficient of the material
  pair. A steel pinion running on a polymer wheel is a far softer
  contact than steel on steel, which lowers the stress and lowers the
  allowable much further; the pairing is assessed as a pair.
- Allowables are quoted at a reference life. Above it they are derated
  on a Woehler slope; below it no credit is taken, because a short-life
  mechanism does not get a stronger material.
- Backlash is a thermal quantity. The centre distance moves with the
  difference between the gear expansion and the housing expansion, and
  that motion appears at the mesh multiplied by twice the tangent of the
  pressure angle. A steel mesh in an aluminium housing loses backlash
  cold and gains it hot, so both extremes are checked against a floor
  above zero and a bound above the nominal.
- Lubricant selection is three checks at once: the qualification
  temperature range against the lubricant rating, the flank contact
  stress against the load the film is credited to, and the gear material
  against what the lubricant may sit on. A dry film that needs a
  metallic substrate and a grease that degrades on fresh steel under
  boundary conditions both fail on the third check, not the first.

## Workflow

1. Validate the mesh: module, pinion and wheel tooth counts, face width
   and transmitted torque, and both materials. A tooth count below the
   tabulated form-factor range is an input error, not a value to
   extrapolate.
2. Derive the pitch diameters, the centre distance and the tangential
   tooth force at the pinion pitch circle.
3. Compute the Lewis bending stress with the form factor of the pinion
   tooth count and the dynamic factor of the drive.
4. Compute the elastic coefficient of the material pair and from it the
   flank contact stress at the same tooth force.
5. Derate both allowables for the required tooth load cycles and compare
   each stress against its derated allowable, absorbing representation
   error at the boundary with a named tolerance.
6. Sweep the backlash across the cold case, the assembly temperature and
   the hot case; hold the minimum above the floor and, when a bound is
   specified, the maximum below it.
7. Run the lubricant against the temperature range, the computed flank
   stress and the gear material, and return every finding with the
   numbers that produced it.

## Pitfalls

- Sizing on bending alone. A tooth that passes Lewis comfortably can
  still pit its flank within the mission cycle count, and pitting is the
  failure mode that shows up in a life test rather than a proof load.
- Taking the backlash measured at assembly as the backlash in orbit. The
  number that matters is the cold-case minimum with the housing
  expansion mismatch applied, and it can be a large fraction of the
  assembled value.
- Checking the cold case only. An oversized hot-case backlash costs
  pointing accuracy and can let the mesh rattle through a launch
  vibration case, so the upper bound is a requirement too.
- Applying the life derating below the reference life. It is a knockdown
  above the reference, never a credit below it; a short-life mechanism
  keeps the tabulated allowable and no more.
- Choosing a lubricant on temperature range alone. The contact stress
  the film is credited to, and the substrate the film needs, fail
  independently of temperature and are the checks most often skipped.
- Reusing a qualified mesh at a higher torque because the stresses still
  look comfortable. Both allowables depend on the cycle count, so a
  duty-cycle change re-opens the strength case even when the geometry is
  untouched.

## Behavior contract (gate 3)

The mesh validation, tangential force, Lewis form factor and bending
stress, elastic coefficient and flank contact stress, life derating,
thermal backlash sweep and lubricant compatibility screen are exercised
by the gate 3 contract test: scripts/test_e3301_gear_design.py against
scripts/e3301_gear_design_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e3301_gear_design.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
