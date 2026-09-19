---
name: q7046-coating-and-finish-control
description: "Evaluate the finish and lubricant a threaded fastener application proposes, against the deposits that are barred, the thread clearance a coating consumes and the vacuum the part will sit in. Use when a plating and lubrication scheme has to be signed off before parts go to the shop: bar cadmium outright and answer it with substitutes, admit a zinc or tin deposit only above the whisker-suppression alloying floor, budget four thicknesses of pitch diameter for every mating thread before the class allowance is gone, judge a lubricant on mass loss, condensables and its qualified temperature band, then report the preload scatter the nut-factor band really delivers. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-cadmium-free-substitution, fastener-whisker-suppression-alloying, fastener-coating-thread-allowance, fastener-lubricant-outgassing-screen, fastener-nut-factor-scatter."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-coating-and-finish-control, fastener-cadmium-free-substitution, fastener-whisker-suppression-alloying, fastener-coating-thread-allowance, fastener-lubricant-outgassing-screen, fastener-nut-factor-scatter, fastener-finish-schedule-rollup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Coating and Finish Control (space-systems/ecss/q7046-coating-and-finish-control)

Use when the task is the finish side of the ECSS-Q-ST-70-46 materials
clause -- choosing the plating, conversion coat and lubricant a
fastener application may carry, and proving the choice before the parts
are in the tank rather than after they will not gauge.

## Domain quick reference

- Screening comes before engineering. Cadmium is barred for flight
  hardware, and a pure zinc or pure tin deposit is barred as a whisker
  source unless the deposit carries enough alloying addition to
  suppress the growth. A screened-out finish is answered with the
  permitted substitutes for the same job, because a bare refusal sends
  the question straight back.
- A whisker is not a corrosion problem, which is why a corrosion
  argument never rescues a pure tin deposit. The failure is a metal
  filament growing out of the deposit over months and shorting
  something nearby, and it is suppressed by alloy content, not by
  environment.
- A coating consumes thread clearance at four times its thickness.
  The deposit lands on both flanks and the pitch diameter is measured
  across them, so five micrometres of plate moves the pitch diameter
  by twenty, and a nut plated to the same schedule takes the same
  amount from the other side.
- That is why the allowance is a joint budget, not a per-part limit.
  An internal deposit spends the external budget, and a plating
  schedule written for the bolt alone will pass every thickness
  measurement and still refuse to assemble.
- A lubricant that flies is a vacuum material first. Total mass loss
  and the condensable fraction are the screening limits, and a grease
  that behaves perfectly on a bench fails both while depositing on
  whatever optical surface is nearby.
- A lubricant qualified warm is not qualified cold. The service band
  is checked at both ends, because a dry film that is happy at two
  hundred degrees can shed at cryogenic temperature.
- The finish is also a friction specification. The preload
  calculation assumed a nut-factor band; the finish and lubricant pair
  delivers one, and if the delivered band is wider the joint's preload
  window was never as narrow as it was drawn.

## Workflow

1. Screen the proposed finish first, using the declared alloying
   addition where the register makes admissibility depend on it, and
   collect the substitutes for anything screened out.
2. Budget the thread allowance across both mating threads at four
   thicknesses each, and report the thickest external deposit the
   remaining allowance still admits rather than only a pass or fail.
3. Screen the lubricant against the mass-loss and condensable limits
   before considering whether it lubricates well.
4. Check the lubricant service band against the mission band at both
   ends and raise a cold end and a hot end as separate findings.
5. Compute the preload span the torque delivers across the declared
   nut-factor band, take the scatter that band implies, and compare it
   against the scatter the joint design assumed.
6. Roll the worst application up into the schedule disposition and
   list the substitutions on offer per part.

## Pitfalls

- Treating a barred deposit as a waiver conversation. The substitute
  exists, so the finding worth raising is which substitute fits this
  application, not whether an exception can be argued.
- Rescuing a pure tin deposit on corrosion grounds. Corrosion is not
  the objection; a filament growing across a gap months later is, and
  no amount of salt-spray data speaks to it.
- Budgeting the plate thickness once. Four times the thickness comes
  off the pitch diameter, and a nut plated to the same schedule takes
  the same again, so a schedule checked on the bolt alone is short by
  half the real consumption.
- Qualifying a lubricant on friction alone. A grease can deliver a
  beautiful nut factor and still put its condensables on a nearby
  optical surface before the first orbit is complete.
- Assuming a dry film that works hot works cold. The band is checked
  at both ends, and a film that sheds at cryogenic temperature leaves
  a joint that gauged perfectly and galls on the way in.
- Comparing a consumed allowance or a scatter fraction against its
  limit by bare arithmetic. Both are quotients of measured floats, so
  a case exactly on a limit can land a few units in the last place
  outside it; the comparison absorbs that while the limit stays
  untouched.

## Behavior contract (gate 3)

The finish screening and substitutes, whisker-suppression alloying
floor, four-thickness thread-allowance budget, outgassing screen,
lubricant band coverage, nut-factor preload scatter and schedule
roll-up are exercised by the gate 3 contract test:
scripts/test_q7046_coating_and_finish_control.py against
scripts/q7046_coating_and_finish_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_coating_and_finish_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
