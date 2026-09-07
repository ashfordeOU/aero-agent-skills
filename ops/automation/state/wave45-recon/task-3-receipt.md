# WAVE-45 PROPULSION PROBE RECEIPTS (task-3, whole family FRESH)

HEAD `5cc8fef3`, read-only probe except this receipt. Baseline: wave-44 +2
(mixed-flow-exhaust turbofan, nozzle-area-ratio-selection rocket); scramjet CLOSED
DEFINITIVELY, not re-opened; wave-39/43 declines stood (drag loss, PPT,
resistojet, pressurant, ablative, turboshaft/engine-matching/axial-stage).

## Count and enumeration

`find skills/propulsion -mindepth 3 -name SKILL.md` returns exactly 48 leaves:
axial-compressor 6 (axial-compressor-stage, compressor-map, multi-stage-compressor,
polytropic-efficiency, turbine-blade-cooling, turbine-stage), combustion 1
(cea-rocket-combustion), electric 3 (electrothermal-thruster, gridded-ion-thruster,
hall-thruster), engine-airframe 1 (engine-airframe-integration), gas-turbine-cycle 10
(afterburner-cycle, brayton-optimum-pressure-ratio, combustor-design, gas-turbine-cycle,
intercooled-cycle, propelling-nozzle, real-cycle-effects, regenerative-cycle,
subsonic-inlet-recovery, turbojet-cycle), ramjet 2 (ramjet-cycle, ramjet-inlet),
rocket 16 (cold-gas-thruster, combustion-chamber-design, hybrid-rocket-motor,
injector-design, nozzle-area-ratio-selection, nozzle-design, propellant-selection,
rocket-engine-cycle, rocket-gravity-loss, rocket-nozzle-divergence-loss,
rocket-nozzle-flow-separation, rocket-sizing, rocket-staging, solid-rocket-motor,
thrust-chamber-cooling, thrust-vector-control), turbofan 5 (bypass-ratio-trade,
mixed-flow-exhaust, turbofan-cycle, turbofan-design-point, turbofan-off-design),
turbomachinery 2 (centrifugal-compressor, rocket-turbopump), turboprop 2
(free-turbine, turboprop-cycle). Router parity: 48 rows in skills/propulsion/SKILL.md.
Corpus: 96 propulsion tasks of 1238 total, exactly 2 per leaf.

## Verdict

2 GO candidates, both clean station-level producers with zero-owner tokens.
Everything else declines or is a closed vein. Consistent with wave-44 thinness.

## Ranked GO candidates

### GO-1 (rank 1): propulsion/electric/mpd-thruster (suggested leaf name: mpd-thruster)

Magnetoplasmadynamic (self-field electromagnetic) thruster steady operating point:
thrust from the current-squared self-field law, exhaust velocity and specific
impulse from the mass flow, jet power, and a documented reference-only
thrust-to-power band verdict for the steady self-field MPD class.

(a) Zero-owner greps across the whole skills/ tree (quoted, case-insensitive):
- `grep -ril 'magnetoplasmadynamic' skills/` -> 0 files
- `grep -ril 'mpd.thruster' skills/` -> 0 files
- `grep -ril 'self-field' skills/` -> 0 files
- `grep -ril 'applied-field' skills/` -> 0 files
Plain 'mpd' matches only the MMPDS substring in structures/data-sources (materials
standard), unrelated. Corpus: 'magnetoplasmadynamic' 0 tasks, 'mpd' 1 task
(MMPDS-style allowables, structures).

(b) Sibling fences. hall-thruster SKILL.md claims only the crossed-field
electrostatic-acceleration slot: "This leaf implements the standard HET performance
model (Goebel and Katz style decomposition)... converting discharge power into
thrust through an axial electric field in a crossed-field discharge." The
electrothermal-thruster Pitfalls enumerate the pack's three mechanisms and none is
electromagnetic: "hall and gridded thrusters accelerate charged beams through
crossed fields or grids, while this leaf only heats propellant and uses no
extraction electrodes - do not apply the perveance or beam-current machinery
here." Gridded-ion owns electrostatic grid extraction. Self-field JxB
electromagnetic acceleration is claimed by none of the three.

(c) Standards-map id: `grep -n 'id: ecss' standards-map.yaml` -> line 94
`  - id: ecss`, exists; ecss reference-only matches the electric pack convention
(hall-thruster, gridded-ion-thruster, electrothermal-thruster all use it).

(d) Published deterministic anchor: self-field electromagnetic thrust law
T = (mu0/(4 pi)) * J^2 * ln(r_a / r_c), the current-squared law of the steady MPD
thruster, Jahn, "Physics of Electric Propulsion", McGraw-Hill 1968; reported in the
Sutton Rocket Propulsion Elements electric-propulsion chapter. Deterministic worked
anchor: J = 10 kA, r_a/r_c = 10 gives T = 1e-7 * 1e8 * ln(10) = 23.0 N; v_e = T/m_dot;
Isp = v_e/g0; jet power P_j = T^2 / (2 m_dot). Typical self-field MPD operating bands
(Isp 1000-4000 s class, thrust-to-power ~10-40 mN/kW) are reported reference-only,
never enforced, matching the electrothermal-thruster band-verdict pattern.

(e) Two wordable Hit@1 corpus queries with distinctive hyphenated tokens:
1. "size an mpd-thruster for the 10 kA discharge current with the 10 to 1
   anode-to-cathode radius ratio: compute the self-field electromagnetic thrust
   from the current-squared thrust law and the exhaust velocity from the 0.1 g/s
   argon mass flow"
2. "analyze the magnetoplasmadynamic-thruster self-field arc operating points:
   thrust from the discharge-current-squared thrust law at 5 kA and 10 kA, jet
   power and specific impulse from the argon mass flow, and the thrust-to-power
   band verdict for the steady-state mpd-thruster class"
Tokens mpd-thruster, magnetoplasmadynamic-thruster, self-field arc,
discharge-current-squared exist on no router row today, so Hit@1 is clean.

(f) Tag discipline: tags limited to distinctive hyphenated compounds
(mpd-thruster, magnetoplasmadynamic-thruster, self-field-thrust-law,
electromagnetic-acceleration, discharge-current-scaling). No generic single-word
tags (no bare thruster, current, power, impulse).

### GO-2 (rank 2): propulsion/rocket/hydrazine-monopropellant-thruster (suggested leaf name: hydrazine-monopropellant-thruster)

Chemical monopropellant hydrazine thruster station math: catalytic decomposition
energy balance to the chamber temperature with the ammonia-dissociation fraction
as documented input, then isentropic nozzle expansion to exhaust velocity and
vacuum specific impulse, with published decomposition-temperature and impulse
bands reported reference-only.

(a) Zero-owner greps across the whole skills/ tree (quoted):
- `grep -ril 'hydrazine decomposition' skills/` -> 0 files
- `grep -ril 'catalytic decomposition' skills/` -> 0 files
- `grep -ril 'catalyst bed' skills/` -> 0 files
- `grep -ril 'N2H4' skills/` -> 0 files
'monopropellant' appears in 4 files, all tank or feed-cycle rows: rocket-engine-cycle
(propellant table row, feed analysis only) and space-systems propellant-tank-sizing
(tank volume row). Corpus: 'hydrazine' 0 tasks, 'monopropellant' 1 task (the
space-systems tank-sizing task at line 3751), 'catalyst' 0 tasks.

(b) Sibling fences. cold-gas-thruster SKILL.md scopes itself to inert gas and
defers hydrazine: "Cold gas thrusters suit small spacecraft RCS duty: simple, safe,
low thrust, modest total impulse; hydrazine and electric options carry far more
impulse per kilogram when the mission demands it." rocket-engine-cycle SKILL.md
limits itself to the feed system: "with a small reference propellant table
(LOX/RP-1, LOX/LH2, N2O4/MMH, monopropellant hydrazine). It covers the feed system
only." electrothermal-thruster heats propellant electrically (NH3, N2, H2, He
table, no N2H4) and states "this leaf only heats propellant, so it neither
accelerates charged beams nor uses extraction electrode assemblies"; chemical
decomposition heat release is a different energy source and is unclaimed.
space-systems propellant-tank-sizing line 95 uses hydrazine only as a tank-sizing
density example ("Hydrazine monopropellant tank: mass 100 kg, density 1008 kg/m3").

(c) Standards-map id: `grep -n 'id: ecss' standards-map.yaml` -> line 94, exists;
ecss reference-only matches the rocket pack convention (cold-gas-thruster,
rocket-engine-cycle and siblings all use ecss).

(d) Published deterministic anchor: the hydrazine catalytic-decomposition energy
balance N2H4 -> (4/3) NH3 + (1/3) N2 exothermic with endothermic ammonia
dissociation, adiabatic decomposition temperature from the heat of decomposition
and product heat capacities at a documented ammonia-dissociation fraction
(~900 K near equilibrium dissociation to ~1,700 K frozen band), then isentropic
nozzle expansion of the decomposed product mixture. Source: Sutton, Rocket
Propulsion Elements, monopropellant section with the published hydrazine vacuum
specific impulse ~230 s class and decomposition temperature range; NASA
hydrazine-thruster design monographs for the catalyst-bed operating band. The
dissociation fraction is an explicit input, so the model is closed form and
deterministic, the same shape as the electrothermal-thruster documented-input
pattern.

(e) Two wordable Hit@1 corpus queries with distinctive hyphenated tokens:
1. "size the hydrazine-monopropellant-thruster for the 5 N spacecraft reaction
   control duty: the catalytic-decomposition chamber temperature from the
   hydrazine-decomposition energy balance at the 0.4 ammonia-dissociation
   fraction, then the nozzle exhaust velocity and vacuum specific impulse for the
   decomposed gas mixture"
2. "run the hydrazine-decomposition energy balance for the monopropellant-thruster
   design point at 22 N: chamber temperature and specific impulse at the frozen
   and the 0.6 ammonia-dissociation limits, and the catalyst-bed temperature band
   check for the RCS thruster"
Tokens hydrazine-monopropellant-thruster, catalytic-decomposition,
hydrazine-decomposition, ammonia-dissociation, catalyst-bed appear nowhere in the
corpus or router rows today, so Hit@1 is clean. The blowdown, plenum, and
choked-mass-flow tokens of cold-gas-thruster are deliberately avoided.

(f) Tag discipline: distinctive hyphenated compounds only
(hydrazine-monopropellant-thruster, catalytic-decomposition,
ammonia-dissociation-fraction, monopropellant-rcs, decomposition-temperature).
No generic single-word tags and no cold-gas blowdown or resistojet tokens.

## Declines table

| Candidate | Verdict | One-line reason |
|---|---|---|
| scramjet-cycle (standing) | CLOSED DEFINITIVELY | Not re-probed per brief; wave-40/41 closure: no verified Rayleigh energy-bookkeeping anchor, duct math now owned by aerodynamics rayleigh-flow |
| drag loss (standing) | DECLINE | Installed and ram-drag bookkeeping owned by engine-airframe-integration; capture and spillage owned by subsonic-inlet-recovery |
| PPT, pulsed plasma thruster (standing) | DECLINE | Pulsed ablation discharge lacks a clean deterministic closed-form anchor |
| resistojet as standalone leaf (standing) | DECLINE | Electrothermal-thruster owns resistojet and arcjet operating points |
| pressurant (standing) | DECLINE | Space-systems propellant-tank-sizing and vehicle-design fuel-feed-system-sizing own pressurant content |
| ablative cooling (standing) | DECLINE | Empirical char-material data with no standards-map anchor; thrust-chamber-cooling owns regenerative and film cooling |
| turboshaft (standing) | DECLINE | Free-turbine owns the shaft-power cycle content including turboshaft wording |
| engine-matching (standing) | DECLINE | Component-map matching is not closed form; off-design and map leaves own the matching pieces |
| axial-stage (standing) | DECLINE | Axial-compressor-stage and multi-stage-compressor own stage count and stage math |
| ramjet combustor heat addition with fuel-air ratio (fresh) | DECLINE | Composes ramjet-cycle (FAR to total temperature ratio) and aerodynamics rayleigh-flow (thermal choking duct math); no new producer |
| external-compression multi-shock supersonic intake (fresh) | DECLINE | Composes ramjet-inlet (recovery, Kantrowitz contraction ratio, starting) and aerodynamics oblique-shock relations which are explicitly scoped for inlet analyses; token cannibalization risk on the ramjet-inlet router row, and scramjet-adjacent veins stay closed |
| bell and parabolic rocket nozzle contour geometry (fresh) | DECLINE | Percent-length contour construction rests on empirical Rao chart data without one published deterministic closed-form law; fabrication risk per the wave-43 precedent |
| rocket ballistic range and trajectory (fresh) | DECLINE | gnc-autonomy impact-point-prediction owns ballistic range; rocket-staging and rocket-sizing own the staging math incl. equal-stage optimum and minimum stage count |
| ducted fan and shrouded propeller momentum theory (fresh) | DECLINE | Actuator-disk, blade-element, disk-loading and power-loading owned across turboprop-cycle, vehicle-design propeller-sizing and ram-air-turbine-sizing; shroud augmentation is parameterized empirics |
| additional turbofan turbojet cycle parameters (fresh) | DECLINE | Bypass-ratio-trade owns BPR, specific thrust, TSFC and fan-pressure-ratio trade; turbofan-off-design owns ratings; no unowned pure cycle-parameter producer found |
| supersonic pitot intake for turbojet aircraft (fresh) | DECLINE | Ramjet-inlet already owns normal-shock pitot recovery and Kantrowitz at flight Mach; subsonic-inlet-recovery owns the subsonic side; no distinct station gap |

## Closed veins

- Scramjet and scramjet-adjacent analysis: CLOSED DEFINITIVELY (do not re-open).
- Supersonic inlet station math: pitot-type recovery, Kantrowitz starting and
  contraction ratio owned by ramjet-inlet; subsonic ram recovery, capture area and
  spillage owned by subsonic-inlet-recovery; oblique and multi-shock extensions
  closed as composition of aerodynamics shock relations.
- Heat-addition duct flow: aerodynamics/high-speed/rayleigh-flow owns thermal
  choking and the Rayleigh-line station ratios.
- Rocket staging and ballistic: rocket-staging owns per-stage delta-v, payload
  fraction, structural index, equal-stage optimum and minimum stage count;
  rocket-sizing owns the rocket-equation loop; gnc impact-point-prediction owns
  ballistic range.
- Propeller and fan momentum theory: Froude and actuator-disk math owned by
  turboprop-cycle, vehicle-design propeller-sizing, vehicle-design
  ram-air-turbine-sizing, and flight-mechanics rotorcraft blade-element leaves.
- Turbofan and turbojet cycle-parameter trades: bypass-ratio-trade, turbofan
  design-point, turbofan off-design and mixed-flow-exhaust cover the trade space.
- Electric propulsion mechanisms: electrostatic (gridded), crossed-field
  electrostatic (hall), electrothermal (resistojet and arcjet) claimed; the
  electromagnetic self-field slot is the one open mechanism and is GO-1.

## Read-only verification note

Probe performed read-only except this single receipt file. No git operations, no
edits to skills/, eval/, docs/, Makefile, scripts/, ops/automation briefs or
standards-map.yaml. Standards-map ids quoted above verified by grep at lines 94
(ecss) and 193 (far-33).
