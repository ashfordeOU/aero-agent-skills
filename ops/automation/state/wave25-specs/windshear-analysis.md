# Wave-25 leaf spec: windshear-analysis (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/windshear-analysis/
- Pack: performance (existing siblings: takeoff-performance,
  landing-performance, climb-performance, wind-effects, energy-height,
  thrust-required, etc.)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: flight-mechanics

## Claim

Assess the effect of low-altitude windshear and microburst encounters on
aircraft performance and recovery: compute the windshear F-factor from
the headwind shear, downdraft, and the aircraft excess thrust, classify
the shear severity against the escape guidance thresholds, compute the
energy height loss rate in the shear, determine the maximum downdraft
the aircraft can out-climb at the current thrust, and check the recovery
thrust requirement. Produces the F-factor, the severity class, the
energy height trend, the climb capability in the downdraft, and the
recovery verdict.

Does NOT do: the wind triangle and steady headwind/crosswind decomposition
(wind-effects owns groundspeed, crab angle, enroute time), zoom climb
energy trades (energy-height), takeoff/landing distance under steady
wind (takeoff-performance/landing-performance). This leaf is the shear
HAZARD analysis (F-factor, downdraft, recovery margin).

## Model (implement exactly)

Reference guidance (FAA windshear training / AC 25-30 style, paraphrase
reference-only, never reproduce text verbatim):
- F-factor (total windshear hazard metric):
  F = (T - D) / W - d(V_head) / dh * (1/g) * ... simplified standard
  form used in windshear training: F = (T-D)/W - (1/g) * (dVh/dt) +
  (V/g) * (d gamma...) . Use the standard implementation:
  F = (T-D)/W - (1/g) * a_wind  where a_wind is the along-track wind
  acceleration experienced by the aircraft (headwind increasing with
  time is a PERFORMANCE INCREASE, decreasing headwind or increasing
  tailwind is a hazard; downdraft adds a vertical component).
  Provide two forms: (1) F from thrust, drag, weight and the measured
  along-track wind acceleration; (2) F from the headwind gradient and
  the downdraft:
  F = (T-D)/W - (dHW/dh) * (dh/dt)/g + (V_downdraft)/V * ... Keep it
  deterministic: implement the energy-form F = (T-D)/W - (1/(g*V)) *
  dE_specific/dt with the wind contributions as documented module
  functions; the module constant definitions must make the numbers
  reproducible. State your exact formulation in the SKILL body.
- Severity classes (reference-only typical guidance): F < 0.05 low,
  0.05-0.1 moderate, 0.1-0.15 high, > 0.15 severe (state as typical
  training thresholds, not a regulation).
- Energy height loss: dH_e/dt = V * (F_required - F_available)
  integrated over the encounter time to give the altitude loss.
- Downdraft out-climb check: max climb rate in still air (from excess
  thrust) vs the downdraft velocity; if downdraft > max climb rate,
  the aircraft descends (verdict flag).
- Recovery: required thrust increase to achieve F = 0 (or the target F)
  at the current drag and weight; report as the required thrust-to-weight
  increment.
Functions:
- f_factor_from_thrust(t, d, w, a_wind, g=9.80665) -> F
- f_factor_from_wind_gradients(headwind_gradient, downdraft, v, w, t, d) -> F
- severity_class(f_factor) -> str
- energy_height_loss_rate(f_factor, v) -> m/s
- altitude_loss(f_factor, v, time_s) -> m
- max_climb_rate_in_downdraft(excess_thrust, w, downdraft) -> verdict
- required_thrust_increment(f_target, current_f, ...) -> dT
- windshear_verdict(...) -> dict
ValueError on: negative weight, speed, or thrust; w <= 0, v <= 0.

## Worked example

Approach at v = 75 m/s, weight 55000 kg? Provide a transport-like
example (weight, thrust, drag at approach): compute F for a headwind
that decreases at 8 kt/s (convert to m/s^2 along track), downdraft
6 m/s, classify severity, compute altitude loss over a 20 s encounter,
and the required thrust increment for recovery. Assert the module's real
numbers.

## Corpus tasks (ids w25-windshear-analysis-1/2)

Distinctive tokens: windshear, microburst, F-factor, downdraft, headwind
shear, wind shear hazard, escape guidance, energy height loss, shear
encounter. Avoid: headwind decomposition, crab angle, groundspeed,
zoom climb (wind-effects/energy-height claims).

1. "compute the windshear F-factor for the approach encounter with the
   decreasing headwind and the 6 m/s downdraft and classify the severity
   for the escape decision"
2. "check whether the aircraft can out-climb the microburst downdraft
   and find the thrust increment needed for the windshear recovery"

## SKILL body notes

Pair with wind-effects (steady triangle), energy-height (energy state),
climb-performance (excess thrust). Worked example uses module constants
and real outputs. Compliance: guidance referenced by name and paraphrase,
no reproduced text.
