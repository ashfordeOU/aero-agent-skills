# AeroSkills

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Format: agentskills.io](https://img.shields.io/badge/format-agentskills.io-purple)](https://agentskills.io)
[![Skills: 259 of 1,000+ target](https://img.shields.io/badge/skills-259%20of%201000%2B%20target-blue)](skills/)
[![Standards: 20](https://img.shields.io/badge/standards-20-blue)](STANDARDS.md)
[![Gates: 5/5 REAL](https://img.shields.io/badge/gates-5%2F5%20REAL-green)](docs/harness-contract.md)
[![Status: dev](https://img.shields.io/badge/status-dev-blue)](README.md)

Aerospace engineering skills for AI agents: standards-mapped,
eval-gated, Apache-2.0. The knowledge layer for engineering agents,
not the platform.

*Development status. This repository is the private development home:
skills, gates, and domain packs are actively built and verified here.
Public release is founder-gated; when released it ships as a clean
repo through the company org (Ashforde).*

## Table of contents

- [Why AeroSkills](#why-aeroskills)
- [Compliance notice](#compliance-notice)
- [What's here](#whats-here)
- [Install](#install)
- [Harness integration](#harness-integration)
- [Verify](#verify)
- [Standards map](#standards-map)
- [Security](#security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [FAQ](#faq)

## Why AeroSkills

Ask a general-purpose AI about DO-178C and you get a Wikipedia summary:
the acronyms, none of the clauses. Aerospace engineering is
standards-bound and evidence-driven. A number without a validation
step is useless. AeroSkills encodes the process: when to use a
standard, the workflow, the pitfalls, and the point where the agent
must stop and let a human sign.

Each skill is a SKILL.md file on the open agentskills.io format: YAML
frontmatter the router reads, a body the agent follows. Loaded on
demand, no lock-in, works in any host that reads the format.

Two things separate this library from a folder of prompts:

- **Standards map.** Every skill carries standards frontmatter that
  resolves against standards-map.yaml: the 18 domain standards
  DO-178C, DO-254, ARP4754A, ARP4761A, AS9100, DO-330, DO-160G,
  AS9102, MMPDS, FAR-25, CS-25, FAR-33, ARINC 429, NAS 410, ASME
  Y14.5, ECSS, and NACA TR-824, plus SEP-2640
  as the delivery format (skills over MCP), separate from the domain
  list. Referenced and summarized, never copied.
- **Eval gates.** make validate runs 5 REAL gates before anything
  ships: spec conformance, description quality, a per-skill behavior
  contract test, a no-verbatim copyright scan, and a 182-task Hit@1
  routing corpus. make attest adds 3: number snapshot, brief audit,
  content policy. Deterministic, offline, replayable. Verified means
  the full bar passes on the commit you are looking at: make validate
  5/5 and make attest 3/3, every behavior contract green, router
  deterministic. Not certification, not approval, not airworthy.

## Compliance notice

> **Compliance notice.** AeroSkills is an open, unrestricted library of
> *civil aerospace engineering methodology* for AI agents, published by
> Ashforde OU (Estonia) under Apache-2.0. The content is educational:
> general engineering principles, processes, and tool-usage guidance. It
> is **not** ITAR/EAR-controlled technical data, and no proprietary
> standards text is reproduced. Standards are referenced and
> summarized only: DO-178C, DO-254, ARP4754A, ARP4761A, AS9100,
> DO-330 (© RTCA/EUROCAE), DO-160G (© RTCA/EUROCAE ED-14G),
> AS9102 (© IAQG/SAE), MMPDS (© SAE), and ARINC 429
> (© ARINC/SAE ITC) remain the property of
> their publishers and must be purchased from them; ECSS,
> FAR/CS-25, and FAR-33 are freely available (public regulations or
> free downloads); SEP-2640 is an open specification from the MCP
> working group (see STANDARDS.md).
>
> As published, without restrictions on further dissemination, this
> library falls within the EU dual-use "public domain" exclusion (Annex I
> General Technology Note, Regulation (EU) 2021/821) and is not subject
> to EU dual-use export authorization.
>
> **Responsible use.** Users are solely responsible for their own
> compliance with export-control and sanctions laws applicable to their
> use of this material. This notice is hygiene, not the legal mechanism:
> public availability is what keeps published information decontrolled.
>
> **Not affiliated with or endorsed by** RTCA, EUROCAE, SAE International,
> IAQG, EASA, FAA, or any government.
>
> See [SECURITY.md](SECURITY.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [STANDARDS.md](STANDARDS.md)

## What's here

One hundred forty-seven verified skills (as of 2026-09-01) across
twelve disciplines with live packs, each spec-linted,
behavior-tested, and router-asserted by make validate:

| Family | Skill | Standard | Covers |
|---|---|---|---|
| aerodynamics | airfoil/airfoil-selection | NACA TR-824 | Use when you must select an airfoil section for a wing design: score candidate airfoils by lift-to-drag ratio |
| aerodynamics | airfoil/xfoil-analysis | NACA TR-824 | Use when running XFOIL-style airfoil analysis for a given section: plan viscous and inviscid polar runs, |
| aerodynamics | cfd/cfd-convergence | NACA TR-824 | Use when you must judge whether a computational fluid dynamics run has converged: check that residuals drop |
| aerodynamics | cfd/cfd-turbulence-modeling | NACA TR-824 | Use when you must estimate the wall-normal first cell height for a CFD mesh: compute the y plus value from |
| aerodynamics | drag-polars/drag-polar | NACA TR-824 | Use when you must construct the parabolic drag polar for a wing: compute the induced drag factor from the |
| aerodynamics | high-speed/normal-shock | NACA TR-824 | Use when you must compute normal shock relations for compressible flow: find the downstream Mach number, |
| aerodynamics | high-speed/prandtl-meyer | NACA TR-824 | Use when you must compute Prandtl-Meyer expansion relations for supersonic compressible flow: |
| aerodynamics | drag-polars/lift-curve-slope | NACA TR-824 | Use when you must estimate the lift curve slope of a wing from section data: compute the |
| avionics | do160/environmental-qualification | DO-160G | Use when planning or reviewing DO-160 environmental qualification of airborne equipment: map equipment |
| avionics | do160/lightning-protection | DO-160G | Use when you must evaluate DO-160 lightning protection for airborne equipment: select the section 22 induced |
| avionics | do178c/airworthiness-liaison | DO-178C | Use when you must manage DO-178C airworthiness and certification liaison for an airborne software item: |
| avionics | do178c/configuration-management | DO-178C | Use when you must manage DO-178C software configuration: establish configuration baselines, record and |
| avionics | do178c/development | DO-178C | Use when you must develop DO-178C airborne software lifecycle data for avionics items: capture high-level and |
| avionics | do178c/planning | STANDARDS | Use when planning DO-178C software certification for airborne systems or equipment: determine the software |
| avionics | do178c/tool-qualification | DO-330 | Use when assessing software tool qualification per DO-330 and DO-178C: determine the tool qualification level |
| avionics | do178c/verification | DO-178C | Use when you must verify DO-178C airborne software against its requirements: review software architecture, |
| avionics | do254/configuration-management | DO-254 | Use when you must determine the DO-254 configuration management action for a hardware change: classify the |
| avionics | do254/hardware-planning | DO-254 | Use when you must plan DO-254 design assurance for airborne electronic hardware: classify an item as simple |
| avionics | do254/requirements-capture | DO-254 | Use when you must capture and review DO-254 hardware requirements for a complex airborne electronic hardware |
| avionics | do254/verification | DO-254 | Use when verifying DO-254 airborne electronic hardware: determine the verification methods that apply to a |
| avionics | far-cs25/airworthiness | FAR-25/CS-25 | Use when scoping transport-category airworthiness certification: determine the certification basis (FAR-25 |
| avionics | far-cs25/special-conditions | FAR-25/CS-25 | Use when you must determine whether a novel or unusual transport-category design feature needs a special |
| avionics | flight-management/flight-planning | DO-178C | Use when you must build and check a flight management system flight plan: compute great-circle leg distances |
| avionics | flight-management/vertical-navigation | DO-178C | Use when you must compute the vertical navigation (VNAV) descent path for a flight management system: |
| cross-cutting | sep2640/skill-delivery | SEP-2640 | Use when packaging or delivering domain skills over MCP per SEP-2640: check that a skill package carries a |
| cross-cutting | sep2640/skill-evaluation | SEP-2640 | Use when you must evaluate a delivered skill against SEP-2640-style conformance and quality cri |
| cross-cutting | documentation/engineering-margins | FAR-25/CS-25 | Use when you must compute the margin of safety for a structural element and state it in an engineering |
| cross-cutting | documentation/engineering-report | SEP-2640 | Use when you must draft or review an engineering report and verify its structure: the required |
| cross-cutting | numerics/convergence-verification | NACA TR-824 | Use when you must judge whether a mesh refinement study has converged: compute the observed order of |
| cross-cutting | units-atmos/isa-atmosphere | ECSS | Use when you must apply the international standard atmosphere in aerospace calculations: read temperature, |
| cross-cutting | units-atmos/unit-conversion | NACA TR-824 | Use when you must convert aerospace quantities between SI and imperial or aviation units: lengt |
| cross-cutting | numerics/least-squares-regression | NACA TR-824 | Use when you must fit a straight line to paired measurements by ordinary least squares: |
| cross-cutting | numerics/uncertainty-propagation | NACA TR-824 | Use when you must propagate measurement uncertainties through a calculation with the GUM |
| cross-cutting | numerics/numerical-integration | NACA TR-824 | Use when you must integrate a function numerically: select the composite trapezoid rule, the |
| flight-mechanics | performance/breguet-range | FAR-25/CS-25 | Use when you must estimate the cruise range of a transport aircraft with the Breguet range equation: combine |
| flight-mechanics | performance/climb-performance | FAR-25/CS-25 | Use when you must compute the climb performance of a fixed-wing aircraft from excess power: derive the rate |
| flight-mechanics | performance/takeoff-performance | FAR-25/CS-25 | Use when you must compute takeoff performance from the aircraft weight, wing area, and thrust: determine the |
| flight-mechanics | performance/turn-performance | FAR-25/CS-25 | Use when you must compute sustained turn performance for a fixed-wing aircraft: derive the load factor from |
| flight-mechanics | stability-control/longitudinal-stability | FAR-25/CS-25 | Use when you must assess static longitudinal stability of an aircraft: compute the neutral point from the |
| flight-mechanics | performance/breguet-endurance | FAR-25/CS-25 | Use when you must compute the loiter endurance time of an aircraft with the Breguet endurance |
| flight-mechanics | performance/glide-performance | FAR-25/CS-25 | Use when you must compute unpowered glide performance for a fixed-wing aircraft: derive the |
| flight-mechanics | stability-control/lateral-directional-stability | FAR-25/CS-25 | Use when you must assess the lateral-directional stability of an aircraft: compute the |
| flight-test-operations | envelope/envelope-expansion | FAR-25/CS-25 | Use when you must plan flight test envelope expansion: compute the corner speed (maneuvering speed VA) from |
| flight-test-operations | envelope/v-speeds | FAR-25/CS-25 | Use when you must compute the certification V-speeds for a flight test program: derive Vref, V2, and Vr from |
| flight-test-operations | performance/accelerate-stop-distance | FAR-25/CS-25 | Use when you must compute the rejected takeoff accelerate-stop distance: accelerate to the decision speed V1 |
| flight-test-operations | performance/stall-speed-determination | FAR-25/CS-25 | Use when you must determine the reference stall speed Vs1g for a flight test: derive it from the wing loading |
| flight-test-operations | planning/flight-test-planning | FAR-25/CS-25 | Use when you must plan a flight test program: order the test points with the build-up |
| flight-test-operations | planning/flight-test-instrumentation | FAR-25/CS-25 | Use when you must design flight test instrumentation: select sensors for the measurement parame |
| flight-test-operations | performance/landing-distance-determination | FAR-25/CS-25 | Use when you must determine the landing distance for a flight test: derive the approach speed |
| flight-test-operations | flutter/flutter-testing | FAR-25/CS-25 | Use when you must assess flutter clearance for a flight test: compute the required flutter |
| flight-test-operations | flutter/ground-vibration-testing | FAR-25/CS-25 | Use when you must plan or analyze a ground vibration test (GVT) for flutter clearance: estimate |
| gnc-autonomy | control/python-control-design | ARP4754A | Use when designing and validating feedback control laws with Python control-systems tooling: evaluate gain |
| gnc-autonomy | control/root-locus-design | ARP4754A | Use when you must design a feedback loop with the classical root locus method: compute the closed loop pole |
| gnc-autonomy | navigation/navigation-frames | ECSS | Use when you must convert navigation coordinate frames for an aircraft or spacecraft: transform geodetic |
| gnc-autonomy | optimal-control/dymos-trajectory | ARP4754A | Use when setting up and assessing pseudospectral trajectory optimization with Dymos: plan optimal-control |
| gnc-autonomy | optimal-control/lqr-design | ARP4754A | Use when you must design an LQR state-feedback gain matrix for a scalar-input two-state system such as |
| gnc-autonomy | guidance/proportional-navigation | ARP4754A | Use when you must compute the proportional navigation guidance command for a planar intercept: derive the |
| gnc-autonomy | space/orbit-dynamics | ECSS | Use when analyzing spacecraft orbital mechanics with two-body and J2-perturbed motion: compute velocities |
| gnc-autonomy | space/rendezvous-phasing | ECSS | Use when you must plan an orbital rendezvous phasing maneuver: compute the drift rate needed to cover a phase |
| manufacturing-quality | as9100/counterfeit-prevention | AS9100 | Use when you must plan counterfeit parts prevention for an aerospace procurement: score the counterfeit risk |
| manufacturing-quality | as9100/calibration-control | AS9100 | Use when you must control calibration of inspection, measuring, and test equipment under an AS9 |
| manufacturing-quality | as9100/quality | AS9100 | Use when scoping or preparing AS9100 aerospace quality management work: map an audit focus area to the |
| manufacturing-quality | as9102/delta-fai | AS9102 | Use when you must classify a change and determine the AS9102 delta first article inspection (delta FAI) |
| manufacturing-quality | as9102/first-article-inspection | AS9102 | Use when preparing or reviewing an AS9102 first article inspection (FAI) report: determine whether forms 1, |
| manufacturing-quality | ndt/ndt-method-selection | AS9100 | Use when you must select a non-destructive testing method for an aerospace part: filter the method set by |
| manufacturing-quality | ndt/ultrasonic-inspection | AS9100 | Use when you must perform ultrasonic inspection (UT) on an aerospace part and turn measured ech |
| manufacturing-quality | as9100/nonconformance-control | AS9100 | Determine and record the disposition of nonconforming aerospace product per AS9100 control of |
| manufacturing-quality | as9100/supplier-control | AS9100 | Use when you must control externally provided processes, products, and services: classify the |
| propulsion | axial-compressor/axial-compressor-stage | FAR-33 | Use when you must analyze a single axial compressor stage from its velocity triangle: compute the specific |
| propulsion | axial-compressor/compressor-map | FAR-33 | Use when you must analyze an axial compressor operating map: identify map points, correct mass |
| propulsion | gas-turbine-cycle/gas-turbine-cycle | FAR-33 | Use when you must compute the ideal gas turbine (Brayton) cycle: estimate the thermal efficiency, the |
| propulsion | gas-turbine-cycle/regenerative-cycle | FAR-33 | Use when you must analyze a gas turbine cycle with regeneration: compute the regenerative Brayt |
| propulsion | rocket/nozzle-design | ECSS | Use when you must design a rocket engine nozzle from the chamber conditions: compute the exit Mach number for |
| propulsion | rocket/propellant-selection | ECSS | Use when you must select and screen rocket propellants for a mission: classify propellant famil |
| propulsion | rocket/rocket-sizing | ECSS | Use when you must size launch-vehicle propulsion with the rocket equation: calculate delta-v from specific |
| propulsion | turbofan/bypass-ratio-trade | FAR-33 | Use when you must size the bypass ratio design trade for a turbofan: compute the thrust split between the fan |
| propulsion | turbofan/turbofan-cycle | FAR-33 | Use when you must compute turbofan cycle parameters: calculate the bypass ratio from the fan and core mass |
| space-systems | adcs/attitude-control-sizing | ECSS | Use when you must size the attitude control subsystem actuators for a spacecraft: compute the momentum wheel |
| space-systems | adcs/sun-pointing | ECSS | Use when you must evaluate spacecraft sun pointing for the ADCS safe hold: compute the angle between the sun |
| space-systems | ecss/software-engineering | ECSS | Use when scoping European space software work per the ECSS series: classify space software criticality (A-D) |
| space-systems | ecss/software-verification | ECSS | Use when you must plan the ECSS-E-ST-40C verification of spacecraft flight software: select the verification |
| space-systems | ecss/systems-engineering | ECSS | Use when scoping or gating European space systems engineering per ECSS-E-ST-10C: determine the lifecycle |
| space-systems | orbit-mechanics/sun-synchronous-inclination | ECSS | Use when you must select the sun-synchronous inclination for an Earth orbit at altitude: solve the J2 nodal |
| space-systems | subsystems/communication-link-budget | ECSS | Use when you must build or check a spacecraft communications link budget: compute the free space path loss |
| space-systems | subsystems/power-thermal-budget | ECSS | Use when sizing spacecraft electrical power and thermal budgets per ECSS practice: estimate battery capacity |
| space-systems | subsystems/thermal-design | ECSS | Use when you must size the thermal control subsystem for a spacecraft: compute the radiator area from the |
| space-systems | orbit-mechanics/keplerian-elements | ECSS | Use when you must compute classical orbital elements from a position and velocity state |
| structures | composites/failure-criteria | FAR-25 | Use when you must evaluate a composite lamina against strength failure criteria: compute the Tsai-Wu, |
| structures | composites/laminate-stiffness | FAR-25/CS-25 | Use when you must compute the stiffness of a composite laminate with classical lamination theory: build the |
| structures | damage-tolerance/crack-growth | FAR-25/CS-25 | Use when you must calculate fatigue crack growth for damage-tolerant structure: estimate the mode I stress |
| structures | damage-tolerance/residual-strength | FAR-25 | Use when you must compute the residual strength of a cracked structure for a damage tolerance assessment: |
| structures | fatigue/miner-damage | FAR-25/CS-25 | Use when you must evaluate fatigue life with cumulative damage: sum the Palmgren-Miner damage fractions over |
| structures | fem/calculix-linear | FAR-25 | Use when running or checking linear static finite element analysis for aircraft structure with CalculiX |
| structures | fem/modal-analysis | FAR-25 | Use when you must run a modal analysis of a two degree of freedom mass-spring structural model: compute the |
| structures | materials/mmpsd-allowables | MMPDS | Use when computing statistically based metallic material design allowables per MMPDS: determine A-basis and |
| systems-engineering-safety | arp4754a/requirements-traceability | ARP4754A | Use when planning or auditing requirements traceability per ARP4754A: determine closure status across SRATS, |
| systems-engineering-safety | arp4754a/systems-planning | ARP4754A | Use when you must plan aircraft and system development per ARP4754A: allocate FDAL to functions and IDAL to |
| systems-engineering-safety | arp4754a/validation | ARP4754A | Use when you must run requirements validation for an aircraft or system program per ARP4754A: select the |
| systems-engineering-safety | arp4761a/common-cause-analysis | ARP4761A | Use when you must plan or review common cause analysis for a safety assessment per ARP4761A: score the zonal |
| systems-engineering-safety | arp4761a/fta-fmea | ARP4761A | Use when scoping or executing FTA (fault tree analysis) and FMEA (failure modes and effects analysis) per |
| systems-engineering-safety | arp4761a/particular-risk-analysis | ARP4761A | Use when you must perform or review a particular risk analysis (PRA) per ARP4761A: quantify the |
| systems-engineering-safety | arp4761a/safety-assessment | ARP4761A | Use when planning or conducting the civil-aircraft safety assessment process per ARP4761A: classify |
| systems-engineering-safety | mbse/systems-engineering | ARP4754A | Use when running model-based systems engineering for an aerospace program: sequence the modeling workflow |
| systems-engineering-safety | mbse/sysml-modeling | ARP4754A | Use when you must create or check SysML models for model-based systems engineering in an aerosp |
| vehicle-design | conceptual/tow-estimation | FAR-25/CS-25 | Use when you must estimate the takeoff gross weight in conceptual aircraft sizing: apply the fuel-fraction |
| vehicle-design | cost-estimation/parametric-cost | FAR-25/CS-25 | Use when you must estimate aircraft program cost with parametric CERs: apply the learning curve to the |
| vehicle-design | mass-properties/inertia-estimation | FAR-25/CS-25 | Use when you must estimate mass properties for vehicle design: compute moments of inertia from masses and |
| vehicle-design | sizing/weight-estimation | FAR-25/CS-25 | Use when performing class-I or class-II vehicle weight estimation: compute moments and center of gravity from |
| vehicle-design | sizing/ws-tw-trade | FAR-25/CS-25 | Use when you must size the aircraft by matching wing loading and thrust to weight: compute the takeoff |
| vehicle-design | sizing/tail-sizing | FAR-25/CS-25 | Use when you must size the empennage with tail volume coefficients: compute the horizontal |
| vehicle-design | sizing/landing-gear-sizing | FAR-25/CS-25 | Use when you must size the landing gear for an aircraft at the sizing level: split the |
| vehicle-design | mass-properties/cg-envelope | FAR-25/CS-25 | Use when you must analyze the center-of-gravity envelope of a vehicle: derive the cg station |
Sub-domain packs follow the 12-discipline taxonomy: aerodynamics,
gnc-autonomy, structures, vehicle-design, avionics, space-systems,
systems-engineering-safety, manufacturing-quality, cross-cutting.
All twelve disciplines have live packs. Each live
discipline has a router SKILL.md that describes the
domain, lists its sub-skills, and tells an agent when to route to it;
every SKILL.md carries domain and pack frontmatter so routers and
installers can filter on them. Run `make packs` for the machine
readable inventory.

Every skill ships its own behavior contract in skills/<path>/scripts/,
exercised by make validate gate 3.

## Install

Prereqs: git, make, python3 with PyYAML.

    git clone https://github.com/arjun-0077/aeroskills.git
    cd aeroskills
    make validate        # 5/5 REAL gates, offline
    make packs           # list the domain packs and their skills

The library is organized into installable domain packs, so you can
install only the domain you need. A pack is the set of leaf folders
(the folders that contain SKILL.md) under skills/<pack>/. Copy or
symlink those leaf folders into your host's skills directory, then
restart the session. Full per-host walkthrough:
[docs/harness-integration.md](docs/harness-integration.md).

Example, install only the avionics discipline (DO-178C software
lifecycle, DO-330 tool qualification, DO-160 environmental
qualification, DO-254 hardware assurance, FAR-25/CS-25
airworthiness), Claude Code
user scope:

    mkdir -p ~/.claude/skills
    cp -r skills/avionics/do178c/planning skills/avionics/do178c/development \
          skills/avionics/do178c/verification skills/avionics/do178c/configuration-management \
          skills/avionics/do178c/tool-qualification skills/avionics/do160/environmental-qualification \
          skills/avionics/do254/hardware-planning skills/avionics/do254/verification \
          skills/avionics/far-cs25/airworthiness \
          ~/.claude/skills/

Example, install only the space-systems discipline (ECSS software
and systems engineering, power and thermal budgeting):

    cp -r skills/space-systems/ecss/software-engineering \
          skills/space-systems/ecss/systems-engineering \
          skills/space-systems/subsystems/power-thermal-budget \
          ~/.claude/skills/

Install the full library the same way: copy every pack's leaf folders.
The family entry points (skills/<family>/SKILL.md) are router
documents for agents; hosts load the leaf folders that carry the
actual skills.

One-command registry installs (npx skills add, gh skill install) are
listed for when the repository is public; the manual paths above work
today.

## Harness integration

| Host | Mechanism | Install target |
|---|---|---|
| Claude Code | skills directory (project or user scope) | .claude/skills/ or ~/.claude/skills/ |
| OpenAI Codex | skills directories (repo and user scope) | .agents/skills/ or ~/.agents/skills/ (legacy experimental: ~/.codex/skills/ behind a feature flag) |
| DeepSeek (via harness) | run DeepSeek as the model provider in a SKILL.md host, then use that host's method | see the host row |
| Gemini CLI | native SKILL.md support plus install/link commands | ~/.gemini/skills/ or .gemini/skills/ |
| OpenCode | skills directory, native skill tool | .opencode/skills/ (also .claude/skills/, .agents/skills/) |
| Cursor | skills directory, loads SKILL.md natively | .cursor/skills/ (also .claude/skills/, .codex/skills/, ~/.claude/skills/, ~/.codex/skills/) |
| Generic agentskills.io host | any host that reads the format | host's skills directory |
| SEP-2640 MCP | emerging skills-over-MCP adapter, skills served as resources | skill:// URIs behind directoryRead |

Every host consumes flat <skill-name>/SKILL.md folders, so installing
a domain pack means copying or symlinking each of its leaf folders.
`make packs` lists every leaf in every pack.

Example, avionics discipline, Claude Code user scope (same as Install):

    for d in skills/avionics/do178c/* skills/avionics/do254/* skills/avionics/far-cs25/*; do
      cp -r "$d" ~/.claude/skills/
    done

Example, single skill, Gemini CLI via the native command:

    gemini skills link "$PWD/skills/avionics/do178c/planning"

Known constraint: the legacy experimental Codex loader caps skill
descriptions at 500 characters; AeroSkills descriptions run 575 to
716 characters, so that loader may skip or truncate them until
trimmed (the current Codex skills docs use the agentskills.io format).
Details and the rest of the per-host commands:
[docs/harness-integration.md](docs/harness-integration.md).

## Verify

You do not need to trust the badge. Replay the gates on the commit you
are looking at:

    make validate        # 5/5 REAL gates: spec lint, desc lint, behavior tests, no-verbatim scan, Hit@1 corpus
    make attest          # 3/3: number snapshot offline, brief audit, content-policy sweep

| Gate | What it checks | How to run |
|---|---|---|
| 1 spec lint | agentskills.io conformance + compliance flags | make lint-spec |
| 2 desc lint | description what + when + trigger | make desc-lint |
| 3 behavior tests | per-skill behavior contract, DAL A-E determination | make pytest-contract |
| 4 no-verbatim | standards text copyright control | make no-verbatim |
| 5 Hit@1 corpus | router selects the expected skill | make hit1 |

Verified means the full bar passes on the commit you are looking at:
make validate 5/5 (spec conformance, description quality, per-skill
behavior contract, no-verbatim copyright control, Hit@1 routing) and
make attest 3/3 (number snapshot against the canonical register,
brief audit, content-policy sweep), with the offline router
deterministic. That is what "verified" means in this
repository: nothing more. It is not certification, not approval, not
airworthy.

## Standards map

standards-map.yaml is the machine-readable source of truth; STANDARDS.md
is the human companion. The map records family, publisher, status,
applicability, and the summary-not-copy rule for every mapped standard.
Gated standards (DO-178C, DO-254, ARP4754A, ARP4761A, AS9100, DO-330,
DO-160G, AS9102, MMPDS) never appear verbatim anywhere in this
repository; the no-verbatim gate enforces it.

## Security

Skills are folders that can carry scripts (skills/<path>/scripts/),
and agent hosts execute what they load. Review the SKILL.md and any
scripts before you install, the same way you would review any code
dependency. The no-verbatim gate means standards text is referenced
and summarized, never copied into the library. To report a
vulnerability, see [SECURITY.md](SECURITY.md).

## Roadmap

- Shipped: 259 verified skills across twelve disciplines with live packs
  as of 2026-09-01. The certification spine (DO-178C planning,
  development, verification, and configuration management; DO-254
  hardware planning; ARP4754A systems planning; ARP4761A safety
  assessment; AS9100 quality; FAR-25/CS-25 airworthiness; ECSS space
  software, MBSE, SEP-2640 skill delivery) plus Wave 4 breadth,
  Wave 5 depth, and Wave 3 fan-out: propulsion, flight mechanics,
  flight test and operations, aerodynamics, cross-cutting, and
  space-systems packs opened on the eval-gated pipeline. Every skill
  gated by make validate (5/5) and make attest (3/3).
- Release bar (founder, 2026-08-31): 50+ domains x 20+ verified
  skills = 1,000+ skills, all make-validate green, before any
  release. The 12-discipline tree decomposes into 73 sub-domain packs
  (1,460 skills at 20 each): a planning target, not a shipped count.
  [development/50x20-domain-tree.md](development/50x20-domain-tree.md).
- Next: fill the 47 live sub-domain packs toward 20 skills each (191 ->
  940). Wave 11 added fan-out leaves across flight mechanics, space
  systems, systems engineering and safety, cross-cutting, gnc-autonomy,
  manufacturing quality, propulsion, and vehicle design (8 leaves);
  Wave 9 added the fan-out across systems engineering and safety,
  flight mechanics, manufacturing quality, cross-cutting, and vehicle
  design (15 leaves); Wave 8 added the rescue fan-out (16 leaves across
  structures, space-systems, gnc-autonomy, aerodynamics,
  vehicle-design, cross-cutting); Wave 5 opened propulsion, flight
  mechanics, and flight test and operations on the same eval-gated
  pipeline; the
  remaining sub-domains follow.
- Later: reference builds; a SEP-2640-aligned MCP adapter for
  enterprise delivery; marketplace listings; the same knowledge
  packaged as AI Department Operator packs (role charters, budget
  ledgers, schedules, evidence gates).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR: one skill
per PR, every contributor certifies their submission contains no
controlled data and no verbatim standards text, and every merge must
pass make validate (5/5) and make attest (3/3). New skills land inside
their domain pack (skills/<family>/<pack>/<leaf>/SKILL.md) and
carry domain and pack frontmatter. Smallest disciplines today:
cross-cutting and flight-test-operations (two skills each), then
flight-mechanics and vehicle-design (three each); every
pack grows toward 20 per the 50x20 release bar.

## FAQ

[docs/FAQ.md](docs/FAQ.md) covers the questions buyers actually ask:
license, certification status, export control, what verified means,
and affiliation. The short answers: Apache-2.0, not certified, not
controlled as published, verified = replayable make validate 5/5 plus
make attest 3/3 on the commit you are looking at, and not affiliated
with RTCA, SAE, EASA, FAA, or any government.

## Star request

If AeroSkills saves you an afternoon, star the repository. It tells us
where to spend the next authoring pass.

## License and legal

Apache-2.0. See [LICENSE](LICENSE) · [NOTICE](NOTICE) ·
[SECURITY.md](SECURITY.md) · [CONTRIBUTING.md](CONTRIBUTING.md) ·
[STANDARDS.md](STANDARDS.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Maintainers

Repo operating structure, department inventory, and operating rules:
[docs/company-of-departments.md](docs/company-of-departments.md).
