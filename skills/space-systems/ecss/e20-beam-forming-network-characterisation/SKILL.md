---
name: e20-beam-forming-network-characterisation
description: "Use when compute the independent circuit characterisation of a spacecraft antenna beam-forming-network under ECSS-E-ST-20C clause 7.2.2.3.4: categorize the network topology as corporate, series, matrix or switched, turn commanded element excitations plus per-path insertion-loss, amplitude-error and phase-error entries into the realized element excitations, separate that departure into a linear phase-gradient that shifts the boresight and a residual scatter that costs aperture-efficiency, add the quantisation floor of a digital phase-shifter, sum the dissipative insertion-loss chain against its allocation, and recombine the element reflections coherently into an input-port-match. Trigger: ecss, e-st-20c-clause-7-2-2-3-4, beam-forming-network-characterisation, element-excitation-error-budget, phase-shifter-quantisation-loss, ruze-gain-loss, beam-pointing-shift, insertion-loss-allocation, input-port-match."
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
  tags: [ecss, e-st-20-electrical-scope, e20-beam-forming-network-characterisation, beam-forming-network-characterisation, element-excitation-error-budget, phase-shifter-quantisation-loss, ruze-gain-loss, beam-pointing-shift, insertion-loss-allocation, input-port-match]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Beam-Forming-Network Characterisation (space-systems/ecss/e20-beam-forming-network-characterisation)

Use when the task is the clause 7.2.2.3.4 case of ECSS-E-ST-20C --
characterising the beam-forming-network of a spacecraft antenna as a
circuit in its own right, separately from the radiating aperture, and
then carrying that circuit result through into what the antenna
actually radiates.

## Domain quick reference

- The network is categorized before anything is computed. A corporate
  divider tree splits one input into many element ports through
  successive dividers; a series feed taps a travelling wave along a
  single line; a matrix network (Butler, Blass, Nolen) maps several
  beam ports onto the same element set; a switched network selects
  between fixed beams. The family decides which departures are
  physically available -- a series feed carries an inherent frequency-
  dependent phase gradient that a corporate tree does not -- so an
  unrecognized topology is a finding about the input, never a default.
- What reaches an element port is not what was commanded. Each path
  adds a dissipative insertion-loss, an amplitude departure and a phase
  departure. The realized excitation is the commanded excitation minus
  the path loss, shifted by the two departures, with the phase folded
  into a single revolution.
- The departure splits into three different effects, and collapsing
  them is the classic error. A common amplitude offset across every
  element is dissipative loss, not an excitation error. A linear phase
  gradient across the elements steers the beam -- it is a pointing
  shift, not a degradation. Only the residual scatter about that
  straight line costs gain, through the Ruze factor exp(-sigma^2) for
  phase and a 1/(1+s^2) efficiency term for amplitude.
- A digital phase-shifter imposes a floor no calibration removes: with
  N bits the least significant step is 360/2^N degrees, the uniform
  residual is that step over sqrt(12), and the peak quantisation lobe
  sits at 1/2^N of the main beam in amplitude -- roughly 6 dB of lobe
  suppression per added bit.
- Element reflections do not vanish at the network input. They return
  through the same split and add as vectors, so the input reflection is
  their vector mean: identical reflections add coherently and reappear
  in full, while opposed ones cancel.

## Workflow

1. Categorize the network topology; reject an unrecognized one before
   any number is produced.
2. Apply each path's insertion-loss, amplitude departure and phase
   departure to the commanded excitation to obtain the realized
   excitation of every element port; a path list shorter or longer than
   the element list is a data defect, not something to pad.
3. Reduce the realized-versus-commanded departure to statistics: the
   common amplitude offset, the residual amplitude scatter about it,
   the least-squares phase gradient across the elements, and the
   residual phase scatter about that gradient.
4. Convert the residual scatter into a gain loss (amplitude efficiency
   term times the Ruze phase term) and, when a digital phase-shifter is
   present, add its quantisation loss to the same total.
5. Convert the phase gradient into a boresight shift for the commanded
   scan angle and element spacing; a gradient that drives the beam past
   the visible region is an input defect, not a large pointing error.
6. Sum the dissipative stages and judge them against the network's
   insertion-loss allocation.
7. Recombine the element reflections as vectors into the input-port
   reflection, convert to standing-wave ratio and return loss, and
   judge against the interface limit.
8. Aggregate: the network is not characterised as compliant until the
   loss allocation, the gain-loss allocation, the pointing allocation
   and the input-port limit are all satisfied.

## Pitfalls

- Reading a uniform amplitude drop across every element as an
  excitation error. It is dissipative loss; counting it twice inflates
  the error budget and hides the real scatter underneath it.
- Charging the linear phase gradient to the gain budget. The gradient
  moves the beam; it is the residual about the gradient that removes
  gain, and treating the raw phase spread as the Ruze input overstates
  the loss on every network with a systematic build tilt.
- Taking the commanded excitation as the aperture illumination because
  the network "was calibrated". Calibration sets the commanded values;
  the residual after calibration, plus the phase-shifter quantisation
  floor, is what the aperture receives.
- Adding element reflections as powers. They return through the same
  divider with defined relative phases and combine as vectors -- a
  power sum understates a coherent case and overstates a cancelling
  one.
- Treating a bit of added phase-shifter resolution as free. Each bit
  buys about 6 dB of quantisation-lobe suppression and a smaller gain
  recovery, against real insertion-loss and control-line cost in the
  same network.

## Behavior contract (gate 3)

The topology categorization, realized-excitation, error-statistics,
gain-loss, quantisation, pointing-shift, insertion-loss-allocation and
input-port-match logic is exercised by the gate 3 contract test:
scripts/test_e20_beam_forming_network_characterisation.py against
scripts/e20_beam_forming_network_characterisation_logic.py (stdlib
unittest, offline, deterministic). Run:
python3 scripts/test_e20_beam_forming_network_characterisation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
