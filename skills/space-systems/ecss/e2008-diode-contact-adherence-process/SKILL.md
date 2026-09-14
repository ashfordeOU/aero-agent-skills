---
name: e2008-diode-contact-adherence-process
description: "Execute the ambient pressure chamber loading every protection diode of a lot passes through before its contacts are pulled under ECSS-E-ST-20-08C clause 9.6.6.2.2: confirm the whole population went in rather than a convenient subset, hold the tray packing cap and terminal clearance that keep the soak reaching each package, check the pressure band and the declared dwell, refuse to sentence a lot from a partial load, then group each anode terminal, cathode terminal and die attach reading and sentence every device by its weakest site. Use when running or auditing a protection diode contact adherence run. Trigger: ecss, e-st-20-08c-clause-9-6-6-2-2, protection-diode-chamber-loading, diode-lot-loading-completeness, diode-terminal-pull-grouping, diode-die-attach-pull-site, diode-tray-packing-fraction."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-diode-contact-adherence-process, protection-diode-chamber-loading, diode-lot-loading-completeness, diode-terminal-pull-grouping, diode-die-attach-pull-site, diode-tray-packing-fraction, protection-diode-terminal-clearance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Diode Contact Adherence Process (space-systems/ecss/e2008-diode-contact-adherence-process)

Use when the task is the run itself under ECSS-E-ST-20-08C clause
9.6.6.2.2 -- all of the protection diodes into the ambient pressure
chamber, held there for the declared dwell, and only then pulled at the
anode terminal, the cathode terminal and the die attach beneath them.
The loading is the part usually treated as housekeeping and is the part
that decides whether the pull numbers mean anything.

## Domain quick reference

- This is a population run, not a sample run. The lot is sentenced from
  what went in, so devices left on the bench are not covered by the
  result and a partial load is reported as partial rather than averaged
  across the devices that did go in.
- The chamber runs inside a band around ambient. A volume that drifted
  out of it ran a different conditioning, and every device inside
  reached a state nobody can name afterwards.
- The dwell is what turns a tray of devices into conditioned devices.
  Cut it short and the pull that follows describes an as-received joint
  wearing a conditioned joint's label.
- Tray geometry is part of the conditioning. Packages edge to edge
  shadow each other from the circulating air, so the tray carries a
  packing cap and each device carries a terminal clearance; a tray
  filled past the cap conditions its outer ring and warms the rest.
- A device is sentenced by its weakest site. A string does not care
  which of its joints let go, so the worst of the three readings is the
  device's answer and the per-site detail is kept alongside it.
- Detachment is a different event from a low reading. A site that came
  apart fails the lot outright rather than being diluted into a reject
  fraction, because a fraction describes a spread and a detachment
  describes a joint that was never made.
- The reject fraction is the last gate, not the first. It only means
  anything once the load was complete and the conditioning was the
  declared one.

## Workflow

1. Validate the loading and acceptance policy first: ambient pressure
   band, tray packing cap, terminal clearance, soak dwell, pull limit,
   detachment threshold and reject cap. A detachment threshold sitting
   at or above the pull limit is refused rather than used.
2. Take the load completeness -- devices in the chamber over devices in
   the population -- and refuse a count larger than the population
   itself. Anything short of the whole population closes the run as not
   evaluated, whatever the pull readings say.
3. Derive the tray packing fraction from the declared geometry and the
   loaded count, refusing a load that does not fit the tray.
4. Check the chamber pressure against its band, the packing against its
   cap, the terminal clearance and the dwell against their floors. A
   value landing exactly on a bound passes; the comparison tolerance
   absorbs representation error and the bound does not move.
5. Group every site reading as adherent, below limit or detached, then
   sentence each device by its weakest site and keep the per-site detail
   with it.
6. Count the rejects, take the fraction against the cap, and close on
   one verdict: lot not evaluated, conditioning deficient, lot failed,
   or lot passed. Report every finding, not the first.

## Pitfalls

- Loading the tray with whatever fits and pulling the rest another day.
  The result covers what went in; a lot sentenced from a partial load
  carries a number that never described the devices left out.
- Averaging a partial load into a pass. The devices on the bench have no
  reading at all, and a fraction computed over the ones pulled quietly
  assumes the missing ones would have matched.
- Treating the tray layout as housekeeping. Packing and clearance decide
  which devices were conditioned at all, and a crowded tray returns a
  pass earned by its outer ring.
- Starting the pulls before the dwell has run. The readings then
  describe the joint as delivered, which is a real number about the
  wrong thing and reads in the record like the right one.
- Diluting a detachment into the reject fraction. One device in twenty
  that came apart is inside any sane fraction and outside any sane lot.
- Sentencing a device by its best site, or by an average of three. The
  weakest joint is the one that opens the protection path, so it is the
  one the device is sentenced by.
- Comparing a packing fraction or a reject fraction against its bound by
  bare arithmetic. Both come out of divisions that land a few units in
  the last place either side of a limit on different hosts, so the
  comparison absorbs that error while the bound itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, load completeness against the population, the
tray packing fraction, the ambient pressure band, terminal clearance and
soak dwell checks, the per-site pull grouping, the weakest-site device
sentence, the detachment override, the reject fraction and the run
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_diode_contact_adherence_process.py against
scripts/e2008_diode_contact_adherence_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_diode_contact_adherence_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
