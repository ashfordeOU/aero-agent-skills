---
name: e2008-displacement-damage-test-purpose
description: "Use when such a campaign is scoped. Determine whether a technology owes the non-ionising exposure ECSS-E-ST-20-08C clause 12.6.11.2.1 reserves for displacement-sensitive parts, and size it: exempt a majority-carrier part, take lifetime down the Messenger-Spratt law, compare the surviving diffusion length with the base width, convert fluence into damage dose through non-ionising energy loss, restate it in the mission equivalence, and refuse a plan short of the end-of-life point or of parts. Trigger: ecss, e-st-20-08c-clause-12-6-11-2-1, blocking-diode-displacement-damage-sensitivity, non-ionising-energy-loss-equivalence, displacement-damage-dose-budget, messenger-spratt-lifetime-damage-constant, base-transport-diffusion-length-margin, non-ionising-exposure-plan-adequacy."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-displacement-damage-test-purpose, blocking-diode-displacement-damage-sensitivity, non-ionising-energy-loss-equivalence, displacement-damage-dose-budget, messenger-spratt-lifetime-damage-constant, base-transport-diffusion-length-margin, non-ionising-exposure-plan-adequacy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Displacement Damage Test Purpose (space-systems/ecss/e2008-displacement-damage-test-purpose)

Use when the task is clause 12.6.11.2.1 of ECSS-E-ST-20-08C -- deciding
why, and whether, a part is given a non-ionising exposure at all. The
clause reserves that exposure for technologies sensitive to displacement
damage, so the work is to say which technologies those are and what the
exposure has to reach.

## Domain quick reference

- Ionising dose and displacement damage are two mechanisms, not two
  names for one. A total-dose campaign charges oxides and shifts
  surfaces; it says nothing about an energetic particle knocking a
  lattice atom off its site.
- Displacement damage works through recombination centres, and
  recombination centres cost minority-carrier lifetime. That is the
  whole chain, and it is why the sensitive technologies are the ones
  whose current has to cross a neutral base.
- A majority-carrier part is exempt on structure, not on numbers. Its
  conduction never depended on injected carriers surviving a transit,
  so lost lifetime does not reach its transport at all.
- A minority-carrier part is judged on two independent quantities.
  Lifetime retention says how much of the starting lifetime remains;
  the diffusion length against the base width says whether the carriers
  still arrive. A part can hold one and lose the other.
- The Messenger-Spratt law adds damage in reciprocal lifetime, not in
  lifetime. 1/tau = 1/tau0 + K times fluence, so the first decade of
  fluence costs almost nothing and a later one costs everything.
- The diffusion length is the square root of diffusivity times
  lifetime, so halving the lifetime only shortens the reach by about
  thirty percent. A retention figure alone therefore overstates how
  much transport a part has actually lost.
- Fluences from different particles are not comparable until they are
  restated through their non-ionising energy loss. A softer particle
  needs more of it to be worth the same damage; a harder one needs
  less.
- Displacement damage dose is fluence times that energy loss, and it is
  the quantity a budget is written in. A bare particle count with no
  particle named is not a level anybody can reproduce.
- An exposure stands in for a whole mission, so it is sized at the
  end-of-life point with margin, and it is run on enough parts for a
  degradation curve to exist.

## Workflow

1. Validate the policy, the technology profile, the environment and any
   proposed plan. Refuse a margin factor below one, which would size
   the exposure short of the point it stands in for.
2. Exempt a majority-carrier technology first and say so, before any
   lifetime arithmetic runs. The exemption is structural and does not
   depend on the fluence.
3. For a minority-carrier technology, take the lifetime left at the
   end-of-life fluence from the Messenger-Spratt law and turn it into a
   retention fraction.
4. Turn that lifetime into a diffusion length and express it as a
   multiple of the base width the carriers have to cross.
5. Call the technology sensitive when either quantity falls through its
   floor, and name each failure separately, because a short lifetime
   and a lost transport margin ask for different design responses.
6. Take the displacement damage dose the environment delivers, and
   restate the end-of-life fluence in the reference equivalence the
   budget is written in.
7. Size the required test fluence as that equivalent end-of-life figure
   times the declared margin factor.
8. Judge a proposed plan by its own equivalent fluence, not by its raw
   particle count, and by its part count. Report both shortfalls when
   both are present, then close on one verdict: exposure not required,
   plan missing, plan short, or plan accepted.

## Pitfalls

- Treating displacement damage as a smaller total-dose problem. The two
  mechanisms scale differently, respond to different particles, and a
  part hard to one can be soft to the other.
- Exposing every part because exposure is cheap. A majority-carrier
  element has no lifetime-limited transport to lose, and the campaign
  spends schedule proving nothing.
- Exempting a part because its retention looks healthy while its base
  is wide. Transport is what the junction needs, and a wide base can
  fail on diffusion length at a retention that still reads well.
- Adding damage in lifetime rather than in reciprocal lifetime. The law
  is linear in the reciprocal, and a linear-in-lifetime shortcut
  overstates the early damage and understates the late.
- Comparing fluences from different particles directly. Without the
  non-ionising energy loss ratio the two numbers describe different
  amounts of damage and the comparison is meaningless.
- Quoting a fluence with no particle and no energy named. Nothing can
  be reproduced from it and nothing can be scaled to it.
- Sizing the exposure at the end-of-life fluence with no margin. The
  environment model carries uncertainty and the test then proves only
  the nominal case.
- Drawing a degradation curve through one or two parts. Part-to-part
  spread in damage constants is real, and a curve through a single
  sample cannot show it.

## Behavior contract (gate 3)

The policy, profile, environment and plan validation, the structural
majority-carrier exemption, the Messenger-Spratt lifetime and its
retention, the diffusion length and the base transport ratio, the
independence of the two sensitivity criteria, displacement damage dose,
non-ionising energy loss equivalence in both directions, the required
test fluence with its margin, plan adequacy on fluence and on part count
together, and every verdict branch are exercised by the gate 3 contract
test: scripts/test_e2008_displacement_damage_test_purpose.py against
scripts/e2008_displacement_damage_test_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_displacement_damage_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
