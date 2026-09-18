---
name: q7003-sealing-process
description: "Verify the sealing of a dyed black anodic coating under the ECSS-Q-ST-70-03C process clause. Use when a hot-water or nickel-acetate seal has to be set or defended after dyeing, before a lot is released: hold the tank inside the temperature band its method carries, scale the seal time to the depth of coating being closed, grade the water for conductivity and for the silicate and phosphate that poison the reaction, place the acetate concentration and pH inside their windows, bound the wait between the dye and the seal, and accept the result on absorptance given up and on dye bleed. Trigger: ecss, q-st-70-03-black-anodizing-scope, hot-water-anodic-seal, nickel-acetate-seal-bath, seal-time-coating-depth-scaling, seal-water-silicate-poisoning, dye-bleed-after-sealing."
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
  tags: [ecss, q-st-70-03-black-anodizing-scope, q7003-sealing-process, hot-water-anodic-seal, nickel-acetate-seal-bath, seal-time-coating-depth-scaling, seal-water-silicate-poisoning, dye-bleed-after-sealing, dye-to-seal-hold-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Black Anodizing — Sealing Process (space-systems/ecss/q7003-sealing-process)

Use when the task is the sealing step of the ECSS-Q-ST-70-03C process
clause -- closing the pores of a coating that has just been dyed
black, by hot water or by a nickel-acetate bath, and showing that what
came out of the tank actually holds the colour it went in with.

## Domain quick reference

- Sealing is a hydration reaction, not a coating operation. The
  aluminium oxide takes on water and swells until the pores close from
  the inside. Nothing is added to the surface, which is why a sealed
  part looks the same as an unsealed one and why the only honest
  evidence is a measurement.
- The two routes trade temperature against time. Hot water works near
  boiling and needs the longer soak; a nickel-acetate bath
  precipitates a hydroxide at the pore mouth, runs cooler and closes
  faster. Each carries its own temperature band and its own time
  constant, and mixing the two sets is the commonest process-sheet
  error on this step.
- Seal time follows coating depth. A thicker coating is a longer pore
  to close, so the time scales with the thickness above a floor that
  differs by method, and a fixed soak set for a thin coating leaves a
  thick one sealed only at its mouth.
- The water is a reagent. Conductivity above the limit says there are
  ions in it that take part in the reaction; silicate and phosphate
  are worse than that, because either one blocks the pore mouth with a
  film that stops the hydration while the tank temperature and the
  clock both read perfect.
- A dyed but unsealed coating is an open one. It bleeds colour into
  any water it meets and picks up whatever is in the air, so the wait
  between the dye and the seal is bounded, and a part held over a
  shift change is not the part that was dyed.
- The result is graded on what it gives up. Absorptance measured
  before and after the seal says how much dye the tank pulled back
  out, and a wipe test says what is still loose on the surface. A seal
  that costs a visible amount of black was not a seal, it was a leach.

## Workflow

1. Validate the run record and reject an unknown sealing method rather
   than defaulting it to either route.
2. Hold the tank inside the temperature band the chosen method
   carries, treating either bound itself as acceptable.
3. Derive the seal time the coating depth needs by that method and
   compare it with the declared soak, accepting a soak that lands
   exactly on the requirement.
4. Grade the water: conductivity against its ceiling, silicate and
   phosphate against theirs.
5. Grade the bath chemistry: pH for either route, and the acetate
   concentration for the acetate route only.
6. Bound the hold between the dye and the seal tank.
7. Take the absorptance before and after the seal, report the loss as
   a non-negative number, grade it with the bleed rating, then report
   the required time, the loss, the findings and one verdict per run.

## Pitfalls

- Sealing to a fixed soak time. The requirement is set by the depth of
  pore being closed, so the same clock that seals a thin coating fully
  leaves a thick one open below the surface, where nothing visible
  reports it until the part is handled or flown.
- Running an acetate bath at hot-water temperature. It is not a
  conservative choice: above its own window the hydroxide precipitates
  as a bloom on the surface rather than in the pore, and the part
  comes out smudged as well as unsealed.
- Grading the water by conductivity alone. Silicate and phosphate sit
  far below the conductivity limit at concentrations that already stop
  the seal, so a water report with one number in it cannot clear the
  tank.
- Treating the wait before sealing as queueing. An unsealed dyed
  coating is losing colour and gaining contamination the whole time,
  and the seal that finally closes it locks in whatever it collected.
- Calling the seal good because the part still looks black. The
  measurement that matters is the absorptance difference across the
  seal and what a wipe lifts afterwards; a part that lost a visible
  fraction of its dye into the tank passes a glance and fails both.

## Behavior contract (gate 3)

The method windows, depth-scaled seal time, water-quality limits, bath
chemistry, dye-to-seal hold, absorptance-loss arithmetic, bleed rating
and run verdict are exercised by the gate 3 contract test:
scripts/test_q7003_sealing_process.py against
scripts/q7003_sealing_process_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7003_sealing_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
