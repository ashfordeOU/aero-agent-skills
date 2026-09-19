---
name: q6005-pre-seal-burn-in
description: "Compute what a biased thermal soak run on an open hybrid microcircuit package actually delivered, and decide whether the unit survived it, under ECSS-Q-ST-60-05 clause 10.3.3. Use when a burn-in log has to be graded rather than counted: convert the chamber hours to equivalent hours at the reference condition through the Arrhenius relation, test every segment against the permitted band, discard the hours before a break long enough to cool the unit, weigh each monitored parameter's drift against its allowance, and return one verdict. Trigger: ecss, q-st-60-05, pre-seal-burn-in, open-package-thermal-soak, burn-in-arrhenius-equivalent-hours, burn-in-interruption-restart, pre-and-post-soak-parameter-drift, pre-seal-burn-in-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-pre-seal-burn-in, open-package-thermal-soak, burn-in-arrhenius-equivalent-hours, burn-in-interruption-restart, pre-and-post-soak-parameter-drift, pre-seal-burn-in-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Pre-Seal Burn-In (space-systems/ecss/q6005-pre-seal-burn-in)

Use when the task is clause 10.3.3 of ECSS-Q-ST-60-05: the powered thermal
soak run while the hybrid package is still open, so that whatever it
precipitates can be seen and repaired without breaking a seal. Where the
step sits in the run is graded under the screening sequence; the
thermographic image and the photographic record have leaves of their own.

## Domain quick reference

- A soak is worth what it delivers at the reference condition, not what the
  chamber log says in hours. A cooler chamber run for the nominal time
  delivers less stress, and the Arrhenius conversion is what everyone means
  when they call a soak equivalent.
- The activation energy decides how steeply that conversion moves. A
  programme that names one uses it; a programme that names none inherits a
  documented default rather than an assumption nobody wrote down.
- The band is a band. Too cool and the soak precipitates nothing worth
  finding; too hot and it damages the assembly it was run to sort, with no
  lid holding anything down.
- Bias is what makes this burn-in rather than a bake. An unbiased soak
  precipitates a different and much smaller set of defects, and it is not a
  substitute.
- Interruptions accumulate up to a point. A short break leaves the unit hot
  and the soak continues; a long one lets it return to ambient, and the
  hours before it no longer form part of one continuous soak.
- The chamber band is read over every segment, not only the continuous tail.
  A chamber that left the band did so whether or not the soak was later
  restarted, and the assembly was there for it.
- The result is the electrical drift across the soak, not the chamber log. A
  parameter that moved past its allowance moved because something in the
  assembly is unstable, and that unit is what the soak was run to find.
- The package stays open throughout, because the whole point of running the
  soak here is that a repair costs nothing to reach.

## Workflow

1. Take the soak log as segments: hours, chamber temperature, and the break
   that followed each one.
2. Validate the log — positive hours, a real temperature, a break that is
   not negative — and reject a soak with no segment at all.
3. Walk the log and restart the accumulation at every break longer than the
   permitted interruption, keeping the count of restarts.
4. Convert each surviving segment to equivalent hours at the reference
   condition, and add them.
5. Compare the delivered equivalent hours with the floor the programme asks
   for, tolerance included so an exact landing counts.
6. Test every declared segment against the permitted chamber band and name
   each temperature that left it.
7. Grade the soak conditions, overruling a declared duration or band with
   what the log actually shows.
8. Take each monitored parameter's drift as a fraction of its pre-soak
   reading and compare it with the allowance.
9. Name the verdict: invalid while a mandatory condition or the index is
   short, rejected on a drifting parameter, passed with open actions on a
   restart or an unrecorded condition, passed only when nothing is
   outstanding.

## Pitfalls

- Adding chamber hours and calling the total a soak. Hours at a cooler
  chamber are not the hours the requirement is written in.
- Running cool because the assembly is open and fragile, then reporting the
  nominal duration. The equivalent hours are what was delivered, and they
  are far short.
- Ignoring a long interruption because the total hours still add up. The
  unit returned to ambient, and a restarted soak is a shorter soak.
- Grading the chamber band only over the segments that survived the last
  restart. The excursion happened to the assembly either way.
- Treating an unbiased bake as a burn-in. It precipitates a different set of
  defects and leaves the ones the clause is aimed at in place.
- Measuring only after the soak. Drift is a difference, and without the
  pre-soak reading there is nothing to subtract.
- Sealing before the drifting units are dispositioned. The repair was free
  while the package was open and is not free afterwards.

## Behavior contract (gate 3)

The Arrhenius acceleration factor, equivalent-hours conversion, chamber-band
test, interruption restart rule, delivered-duration sufficiency, parameter
drift fraction and allowance, soak-condition grading, condition index and
burn-in verdict are exercised by the gate 3 contract test:
scripts/test_q6005_pre_seal_burn_in.py against
scripts/q6005_pre_seal_burn_in_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6005_pre_seal_burn_in.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
