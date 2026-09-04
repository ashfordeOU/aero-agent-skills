---
name: pointing-error-budget
description: "Use when you must assemble the spacecraft pointing error budget for the attitude determination and control system: combine independent 1-sigma error contributors (determination noise, gyro propagation, control deadband, jitter, thermal distortion) by root-sum-square, convert to 3-sigma, check it against the pointing requirement, allocate the remaining budget to a not-yet-sized contributor, and rank error sources by variance share. Produces the RSS pointing error, the requirement verdict, the allocated contributor budget, and the dominant error source, the assembly layer from sensor metrology to payload pointing. Trigger: rss pointing error, 3 sigma requirement, error budget allocation, control deadband, jitter budget, dominant error source."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: adcs
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: adcs
  tags: [pointing-error-budget, pointing-accuracy, rss-pointing-error, jitter-budget, adcs-error-allocation]
  version: 0.1.0
  author: AeroSkills
---

# Pointing Error Budget (space-systems/adcs/pointing-error-budget)

Use when the task is the ADCS pointing error chain: summing the
independent 1-sigma error contributors of the attitude determination
and control system into one RSS pointing error, converting it to
3-sigma, checking it against the pointing requirement, allocating the
remaining budget to the contributor that is not yet sized (typically
the control deadband), and ranking the contributors by variance share.
This leaf is the assembly layer between the sensor noise metrology of
the ADCS and the payload or antenna that consumes the delivered
pointing error. Pure Python, stdlib only, unit-agnostic with the ADCS
example in arcsec.

## Domain quick reference

- RSS combination: rss_1sigma = sqrt(sum(c_i^2)) over the independent
  1-sigma contributors. Independence is assumed; correlated errors are
  summed linearly, not by RSS.
- 3-sigma conversion: rss_3sigma = 3 * rss_1sigma (normal distribution
  convention).
- Requirement verdict: requirement_met = rss_3sigma <= requirement_3sigma.
- Budget allocation to one remaining contributor: remaining_1sigma =
  sqrt((requirement_3sigma / 3)^2 - sum(c_fixed^2)). The fixed RSS must
  stay below requirement / 3 or the radicand is negative and the
  allocation fails.
- Variance share: share_i = c_i^2 / sum(c_j^2); the dominant error
  source is the contributor with the largest share.
- Units: the functions are unit-agnostic; the reference ADCS chain uses
  arcsec (1-sigma) and the requirement uses arcsec (3-sigma).

## Workflow

1. List the independent 1-sigma contributors in arcsec: star tracker
   determination noise, gyro propagation, control deadband, jitter,
   thermal distortion (add other known terms as needed).
2. Combine them with rss_pointing_error to get the 1-sigma RSS.
3. Convert with three_sigma_error and judge the requirement with
   three_sigma_verdict against the 3-sigma pointing requirement.
4. When one contributor is not yet sized (the control deadband in the
   reference chain), allocate its budget with allocate_error_budget
   using the requirement and the fixed contributors.
5. Rank the contributors by variance share with
   dominant_error_source; pass a dict of {name: value} to get the
   dominant contributor name back.
6. Assemble the full picture with pointing_error_budget, which returns
   the RSS values, the verdict, the dominant index and share, and the
   per-contributor variance shares in one dict.
7. Confirm the deterministic checks with the contract test
   scripts/test_pointing_error_budget.py.

## Worked example

Reference ADCS chain (arcsec, 1-sigma): star tracker determination
noise 3, gyro propagation 2, control deadband 25, jitter 8, thermal
distortion 5; pointing requirement 90 arcsec 3-sigma.

- rss_pointing_error([3, 2, 25, 8, 5]) = sqrt(9 + 4 + 625 + 64 + 25) =
  sqrt(727) = 26.962938 arcsec.
- three_sigma_error([3, 2, 25, 8, 5]) = 3 * 26.962938 = 80.888813
  arcsec.
- three_sigma_verdict([3, 2, 25, 8, 5], 90) = True: 80.888813 <= 90,
  the requirement is met with margin.
- allocate_error_budget(90, [3, 2, 8, 5]) = sqrt(30^2 - (9 + 4 + 64 +
  25)) = sqrt(798) = 28.248894 arcsec, the budget left for the control
  deadband. It exceeds the 25 arcsec actual deadband, consistent with
  the requirement verdict True.
- dominant_error_source([3, 2, 25, 8, 5]) = (index 2, control deadband,
  share 625/727 = 0.8597), so the control deadband carries 86.0% of the
  error variance.

## Verification

- Confirm rss_pointing_error([3, 2, 25, 8, 5]) returns 26.962938 arcsec
  and three_sigma_error returns 80.888813 arcsec.
- Confirm adding a zero contributor leaves the RSS unchanged, reversing
  the input order leaves it unchanged, and a contributor equal to the
  RSS of the others raises the total by sqrt(2).
- Confirm the verdict boundary: a requirement exactly equal to the
  3-sigma value returns True.
- Confirm allocate_error_budget(90, [3, 2, 8, 5]) returns 28.248894
  arcsec, and that shrinking the requirement shrinks the allocation.
- Confirm ValueError is raised for an empty contributor list, any
  negative contributor, a non-positive requirement, a negative radicand
  in the allocation (fixed contributors already over the 1-sigma
  budget), and an all-zero contributor list in the dominant-source
  ranking.
- Run the contract test offline: python3
  scripts/test_pointing_error_budget.py (34 tests, deterministic).

## Related leaves

- space-systems/adcs/attitude-control-sizing: actuator sizing sibling;
  boundary is actuator sizing and margins versus this leaf's error
  chain sum.
- space-systems/adcs/attitude-determination-quest: determination
  sibling whose residual feeds this leaf's determination-noise entry.
- space-systems/subsystems/antenna-aperture-sizing: downstream consumer
  of the delivered pointing error as a signal loss term.
- space-systems/adcs/gyro-allan-variance: sensor noise metrology that
  characterizes the gyro propagation entry.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_pointing_error_budget.py

The test covers the reference-chain contract (RSS 26.962938 arcsec,
3-sigma 80.888813 arcsec, verdict True at 90 arcsec, allocation
28.248894 arcsec, control deadband dominant at 86.0% variance share),
the RSS identities (zero padding, order invariance, single component,
sqrt(2) growth), the verdict boundary, allocation monotonicity and
negative-radicand rejection, dominant-source ranking on the [1, 100]
case at 99.99%, dict-name support, the convenience-dict keys, run-to-
run determinism, and ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: the ECSS ADCS error-budget
  convention (reference-only per standards-map.yaml). The relations
  above are standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
