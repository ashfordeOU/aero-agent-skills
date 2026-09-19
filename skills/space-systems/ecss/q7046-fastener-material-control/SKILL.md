---
name: q7046-fastener-material-control
description: "Assess the material declaration behind a threaded fastener lot: the alloy, its stress-corrosion category, the couple it forms with the structure, and the temperature band it was characterized over. Use when someone must say whether a proposed fastener material may fly on this joint: take the stress-corrosion category from the admitted alloy rather than a datasheet, hold a moderate-resistance alloy to half yield and bar a low-resistance one from sustained tension altogether, judge the fastener-to-structure couple by potential difference against a limit that tightens with the environment, raise the embrittlement-susceptible strength level before the plating shop sees the part, and refuse a declaration carrying no heat number. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-alloy-admissibility, fastener-scc-resistance-category, fastener-sustained-tension-limit, fastener-galvanic-couple-limit, fastener-embrittlement-strength-level, fastener-heat-number-declaration."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-fastener-material-control, fastener-alloy-admissibility, fastener-scc-resistance-category, fastener-sustained-tension-limit, fastener-galvanic-couple-limit, fastener-embrittlement-strength-level, fastener-heat-number-declaration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Material Control (space-systems/ecss/q7046-fastener-material-control)

Use when the task is the materials clause of ECSS-Q-ST-70-46 read with
the companion stress-corrosion standard ECSS-Q-ST-70-36 -- deciding
whether the alloy a fastener is cut from may carry this joint, in this
structure, at this temperature, with the finish route that follows.

## Domain quick reference

- An alloy is admitted by name, not by description. "Corrosion
  resistant steel" names a shelf, not a material, and the properties
  that decide the question -- stress-corrosion category, position in
  the galvanic series, strength level, characterized temperature band
  -- differ across the alloys that share that shelf.
- Stress-corrosion resistance is the property that limits sustained
  tensile stress, and it is a category rather than a number. A
  high-resistance alloy runs to the general design fraction of yield.
  A moderate-resistance alloy is held to half yield and carries that
  restriction in writing. A low-resistance alloy takes no sustained
  tensile load at all.
- The distinction is not between alloy families but between tempers of
  the same family. The same aluminium composition is high-resistance
  in an overaged temper and low-resistance in the peak-strength one,
  so the temper is part of the material identity and a declaration
  that omits it cannot be assessed.
- A stress-corrosion failure gives no warning and leaves no load
  excursion behind. That is why the limit sits on the sustained
  stress, which is the preload and the thermal term that never goes
  away, rather than on the peak stress the joint sees once.
- A fastener and the structure it clamps are one galvanic couple. The
  couple is judged by the potential difference between the two alloys
  against a limit that tightens as the service environment gets wetter
  and saltier, and the more anodic member is the one that dissolves --
  usually the structure, which is why a noble fastener is not the safe
  default it looks like.
- Above the susceptibility threshold an alloy is hydrogen-embrittlement
  prone, which does not bar it. It constrains the finish route, and
  the constraint has to leave the materials engineer as a written
  control rather than arriving at the plating shop as silence.
- Temperature is a covering check at both ends. A cold end outside the
  characterized band is a finding even when the hot end is
  comfortable, because cryogenic ductility is not implied by
  room-temperature data.

## Workflow

1. Resolve the alloy against the admitted list and reject an
   unrecognized name rather than mapping it to something close, since
   every later step reads that record.
2. Read the stress-corrosion category, derive the sustained tensile
   stress limit from it and the declared yield, and compare the
   sustained stress the joint actually holds.
3. Separate the two stress-corrosion outcomes: a low-resistance alloy
   under any sustained tension is a rejection, while a
   moderate-resistance alloy inside its limit is an acceptance that
   owes a written control.
4. Form the galvanic couple with the structure alloy, take the
   potential difference, compare it against the environment limit and
   name the anodic member.
5. Test the strength level against the embrittlement threshold; where
   it is exceeded, reject an electrolytic finish with no relief bake
   and otherwise issue the finish constraint as a control.
6. Check the mission temperature band against the characterized band
   at both ends, confirm the heat number is present, then roll the
   worst declaration up into the build disposition.

## Pitfalls

- Reading stress-corrosion resistance off the family. Temper decides
  it, and the peak-strength temper of a family whose overaged temper
  is high-resistance is exactly the material that cracks under a
  preload nobody thought twice about.
- Applying the limit to the peak load. The sustained stress is the
  preload plus the thermal term, and it is present for the whole
  mission; a limit checked against a launch transient looks satisfied
  while the part sits above it for years.
- Choosing the most noble fastener available. The couple is a
  difference, so a very noble fastener in an aluminium structure drives
  the structure anodic and moves the corrosion from a replaceable part
  to one that is not.
- Treating embrittlement susceptibility as a materials footnote. It is
  a constraint on a process two departments away, and unless it leaves
  the declaration as a written control the plating shop has no reason
  to know the bake exists.
- Accepting a declaration without a heat number. Every downstream
  certificate, test record and quarantine boundary is keyed on it, so
  a lot without one cannot be tied to its evidence later, whatever the
  paperwork promises.
- Comparing a stress or a potential against its limit by bare
  arithmetic. Both are differences of measured floats, so a case
  sitting exactly on a limit can land a few units in the last place
  outside it; the comparison absorbs that while the limit stays
  untouched.

## Behavior contract (gate 3)

The alloy lookup, stress-corrosion category limit, galvanic couple
difference, embrittlement threshold, temperature coverage, declaration
validation and build roll-up are exercised by the gate 3 contract test:
scripts/test_q7046_fastener_material_control.py against
scripts/q7046_fastener_material_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_fastener_material_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
