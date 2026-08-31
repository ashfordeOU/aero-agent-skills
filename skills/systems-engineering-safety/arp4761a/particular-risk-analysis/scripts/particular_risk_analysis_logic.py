#!/usr/bin/env python3
"""ARP4761A particular risk analysis logic (paraphrase).

Common-knowledge summary (standards-map.yaml, arp4761a: proprietary
SAE, summary only): particular risk analysis (PRA) assesses the risk
from single events that can affect a system or the aircraft as a
whole, for example rotor burst, tire burst, bird strike, fire, and
lightning. The analysis combines the probability of the event with
the conditional probability that the hazard it creates leads to a
failure condition, and checks hazard zone containment, separation,
and redundant routing mitigations.
"""

import math


def conditional_probability(p_a, p_b_given_a):
    """Combined probability p_a * p_b_given_a of a two-step chain.

    p_a: probability of the particular event (for example rotor
    burst). p_b_given_a: conditional probability that the hazard
    created by the event leads to the failure condition. Both must
    lie in [0, 1]; out-of-range values raise ValueError.
    """
    for name, p in (("p_a", p_a), ("p_b_given_a", p_b_given_a)):
        if not 0.0 <= p <= 1.0:
            raise ValueError("%s must be in [0, 1], got %r" % (name, p))
    return p_a * p_b_given_a


def exposure_probability(rate, hours):
    """Probability of at least one event in the exposure time.

    Poisson process: 1 - exp(-rate * hours). rate is events per
    flight hour, hours the exposure time. For small rate*hours the
    value is approximately rate*hours. Negative inputs raise
    ValueError.
    """
    if rate < 0.0:
        raise ValueError("rate must be >= 0, got %r" % (rate,))
    if hours < 0.0:
        raise ValueError("hours must be >= 0, got %r" % (hours,))
    return 1.0 - math.exp(-rate * hours)


def containment_verdict(overlap):
    """Zone verdict from hazard zone overlap with a protected zone.

    overlap is the fraction of the protected zone penetrated by the
    hazard zone, in [0, 1]. Zero overlap means containment holds:
    verdict 'ok'. Any overlap means the hazard can reach protected
    equipment: verdict 'action' (add containment, separation, or
    redundant routing). Out-of-range values raise ValueError.
    """
    if not 0.0 <= overlap <= 1.0:
        raise ValueError("overlap must be in [0, 1], got %r" % (overlap,))
    return "ok" if overlap == 0.0 else "action"
