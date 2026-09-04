# Wave-34 leaf spec: pointing-error-budget (space-systems, adcs pack)

- Path: skills/space-systems/adcs/pointing-error-budget/
- Pack: adcs. Closest siblings: attitude-control-sizing (checks
  actuator momentum margins and detumble; does not sum the error
  chain), attitude-determination-quest/triad (determination of the
  attitude, not its error budget), star-tracker (measurement
  geometry), sun-pointing (solar geometry tolerance), reaction-wheel-
  control (control law), space-systems/subsystems/antenna-aperture-
  sizing (CONSUMES a given pointing error as a dB pointing loss, a
  downstream user), gnc-autonomy/space/attitude-dynamics (kinematics).
  Repo-wide: no leaf sums the ADCS pointing error chain.
- Standards id: ecss (reference-only; adcs convention). Ledger
  Standard: ecss.
- Family: space-systems

## Claim

Build the ADCS pointing error budget: the RSS combination of
independent 1-sigma error contributors (determination noise, gyro
propagation, control deadband, jitter, thermal distortion), the 3-sigma
conversion and verdict against a pointing requirement, the allocation
of the remaining error budget to the not-yet-sized contributor, and the
dominant error source ranking by variance share. Produces the RSS
pointing error, the requirement verdict, the allocated contributor
budget and the dominant source, the assembly layer between sensor
noise metrology and payload pointing loss.

Does NOT do: actuator sizing or momentum margins (attitude-control-
sizing); attitude determination (quest/triad); star/sun measurement
geometry (star-tracker, sun-pointing); the dB pointing loss of an
antenna given an error (antenna-aperture-sizing consumes this leaf's
output); sensor noise metrology (gyro-allan-variance).

## Model (implement exactly)

Conventions: all component inputs are 1-sigma arcsec values (or any
consistent angular unit; the functions are unit-agnostic but the worked
example uses arcsec). The RSS 1-sigma error is sqrt(sum of squares).
The 3-sigma value is 3x the RSS (normal distribution convention).
Variance share of a component is c_i^2 / sum(c_j^2).

Functions (pure stdlib):
- rss_pointing_error(components_1sigma) -> float sqrt(sum c_i^2).
  ValueError on empty list; any negative component.
- three_sigma_error(components_1sigma) -> 3 * rss.
- three_sigma_verdict(components_1sigma, requirement_3sigma) -> bool
  (three_sigma_error <= requirement). ValueError on requirement <= 0.
- allocate_error_budget(requirement_3sigma, fixed_components_1sigma)
  -> float: the 1-sigma budget left for ONE remaining contributor =
  sqrt((requirement/3)^2 - sum(fixed^2)); ValueError when the fixed
  RSS already exceeds requirement/3 (negative radicand).
- dominant_error_source(components_1sigma) -> tuple (index, name or
  None, variance_share) - the largest-variance component and its
  share. ValueError on empty list.
- pointing_error_budget(components_1sigma, requirement_3sigma) -> dict
  {rss_1sigma, rss_3sigma, requirement_met, dominant_index,
  dominant_variance_share, component_variance_shares (list)}.

The RSS identity to test: adding a zero component does not change the
RSS; a component equal to the RSS of the others raises the total RSS
by sqrt(2).

## Worked example

Reference ADCS error chain (arcsec, 1-sigma): star tracker
determination noise 3, gyro propagation 2, control deadband 25, jitter
8, thermal distortion 5; pointing requirement 90 arcsec 3-sigma.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- rss_pointing_error = sqrt(9 + 4 + 625 + 64 + 25) =
  sqrt(727) = 26.962938 arcsec.
- three_sigma_error = 80.888813 arcsec.
- three_sigma_verdict: 80.888813 <= 90 -> True (requirement met).
- allocate_error_budget(90, fixed = [3, 2, 8, 5]) -> the control
  deadband budget = sqrt(30^2 - (9 + 4 + 64 + 25)) =
  sqrt(900 - 102) = sqrt(798) = 28.248894 arcsec, which exceeds the
  25 arcsec actual deadband (consistent with requirement_met True).
- dominant_error_source: control deadband (25 arcsec), variance share
  625/727 = 86.0%.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty list; negative component; requirement <= 0;
  negative radicand in allocation (fixed already over budget).
- RSS: worked sqrt(727) = 26.962938 to 1e-6; single component returns
  itself; zero-padding invariant; order invariance.
- 3-sigma: 3x RSS exactly; verdict boundary (requirement exactly equal
  to the 3-sigma value returns True).
- Allocation: worked control budget 28.248894 to 1e-6; a requirement
  smaller than 3x the fixed RSS raises ValueError; reducing the
  requirement shrinks the allocation monotonically.
- Dominant source: worked control deadband with share 86.0%; a
  two-component [1, 100] case returns index 1 with share 99.99%.
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-pointing-error-budget.yaml)

Query 1 (copy verbatim):
  "compute the rss pointing error budget of the attitude control system from the 1 sigma determination, gyro, control deadband, jitter and thermal contributors and check the 3 sigma requirement"
  intent: "space-systems; ADCS RSS pointing error budget and 3 sigma requirement verdict"
  expected_skill: "space-systems/adcs/pointing-error-budget"
Query 2 (copy verbatim):
  "allocate the remaining pointing error budget to the control deadband contributor and rank the dominant error source by variance share"
  intent: "space-systems; pointing error budget allocation and dominant source ranking"
  expected_skill: "space-systems/adcs/pointing-error-budget"
Task ids: w34-pointing-error-budget-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must assemble the spacecraft
pointing error budget for the attitude determination and control
system:" and include the outputs in the Claim. First tag:
pointing-error-budget. Additional tags ONLY: pointing-accuracy,
rss-pointing-error, jitter-budget, adcs-error-allocation. NEVER single
generic words (pointing, error, budget, attitude, control, jitter).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): momentum, wheel sizing,
detumble (attitude-control-sizing owns actuator sizing); Wahba, QUEST,
TRIAD, quaternion determination (determination leaves); star ID
(star-tracker); sun angle (sun-pointing); pointing loss dB, aperture
(antenna-aperture-sizing consumes the error downstream); Allan
deviation, angle random walk (gyro-allan-variance). The words "pointing
error budget", "RSS", "3 sigma requirement", "deadband", "error
allocation" are this leaf's own in the ADCS context.

Tags: [pointing-error-budget, pointing-accuracy, rss-pointing-error,
jitter-budget, adcs-error-allocation]

Sibling-citation lines for Related leaves:
space-systems/adcs/attitude-control-sizing (actuator sizing sibling;
boundary: momentum margins vs error budget),
space-systems/adcs/attitude-determination-quest (determination
sibling whose residual feeds this leaf's determination-noise entry),
space-systems/subsystems/antenna-aperture-sizing (downstream consumer
of the pointing error as a dB loss),
space-systems/adcs/gyro-allan-variance (sensor noise metrology feeding
the gyro entry).

Ledger Standard: ecss.
