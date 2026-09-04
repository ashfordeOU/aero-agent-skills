"""Aircraft electrical load analysis logic (pure stdlib).

Roll up consumer apparent power (kVA) with each consumer duty cycle into
the continuous load, apply the diversity factor for the coincident peak,
total the essential load from the named essential consumers at their full
steady power, and check the generator rating against the single-generator-
out case where the remaining capacity must cover the essential load. This
is the FAR 25.1355 sizing context: no essential load may be lost when any
one power source fails.

Conventions: consumers are given as {name: (power_kva, duty)} with duty in
[0, 1], the fraction of flight time the consumer draws its rated power.
The continuous load sums the duty-weighted powers. The essential load
totals the FULL rated power of the named essential consumers (conservative
full-power bookkeeping, they must be powered continuously in the failure
case).

All functions are deterministic and depend only on their arguments.
"""


def continuous_load(consumers):
    """Return {continuous_kva, rollup} of the duty-weighted consumer load.

    rollup lists the per-consumer duty-weighted kVA values in the same
    order as the input dict.

    ValueErrors: empty dict; any duty outside [0, 1]; any power < 0.
    """
    if not consumers:
        raise ValueError("consumers dict must not be empty")
    rollup = []
    for power_kva, duty in consumers.values():
        if power_kva < 0.0:
            raise ValueError("consumer power must be >= 0 kVA")
        if not (0.0 <= duty <= 1.0):
            raise ValueError("consumer duty must lie in [0, 1]")
        rollup.append(power_kva * duty)
    return {"continuous_kva": sum(rollup), "rollup": rollup}


def diversity_peak(continuous_kva, diversity_factor):
    """Return the coincident peak kVA: diversity_factor * continuous_kva.

    ValueErrors: continuous_kva < 0; diversity_factor outside (0, 1].
    """
    if continuous_kva < 0.0:
        raise ValueError("continuous load must be >= 0 kVA")
    if not (0.0 < diversity_factor <= 1.0):
        raise ValueError("diversity factor must lie in (0, 1]")
    return diversity_factor * continuous_kva


def essential_load(consumers, essential_names):
    """Return {essential_kva, essential_consumers} at full rated power.

    Essential consumers are booked at their FULL power (not duty
    weighted): they must be powered continuously in the failure case.

    ValueErrors: empty consumers dict; essential name not in consumers.
    """
    if not consumers:
        raise ValueError("consumers dict must not be empty")
    total = 0.0
    names = []
    for name in essential_names:
        if name not in consumers:
            raise ValueError("essential consumer %r not in consumers" % name)
        total += consumers[name][0]
        names.append(name)
    return {"essential_kva": total, "essential_consumers": names}


def generator_out_margin(n_generators, generator_kva, essential_kva):
    """Return the single-generator-out margin dict.

    remaining_kva = (n_generators - 1) * generator_kva is the capacity
    left after the worst single generator fails; margin =
    (remaining_kva - essential_kva) / remaining_kva; verdict is PASS when
    margin >= 0 else FAIL. With one generator there is no redundancy:
    remaining_kva 0.0, margin -1.0, verdict FAIL.

    ValueErrors: n_generators < 1; generator_kva <= 0; essential_kva < 0.
    """
    if n_generators < 1:
        raise ValueError("n_generators must be >= 1")
    if generator_kva <= 0.0:
        raise ValueError("generator_kva must be > 0")
    if essential_kva < 0.0:
        raise ValueError("essential_kva must be >= 0")
    remaining_kva = (n_generators - 1) * generator_kva
    if n_generators == 1:
        return {"remaining_kva": 0.0, "margin": -1.0, "verdict": "FAIL"}
    margin = (remaining_kva - essential_kva) / remaining_kva
    verdict = "PASS" if margin >= 0.0 else "FAIL"
    return {"remaining_kva": remaining_kva, "margin": margin, "verdict": verdict}


def load_fraction(continuous_kva, installed_kva):
    """Return the normal load fraction continuous_kva / installed_kva.

    ValueError: installed_kva <= 0.
    """
    if installed_kva <= 0.0:
        raise ValueError("installed_kva must be > 0")
    return continuous_kva / installed_kva


def ela_summary(consumers, diversity_factor, essential_names,
                n_generators, generator_kva):
    """Return the full electrical load analysis summary dict.

    Keys: continuous_kva, rollup, coincident_peak_kva, essential_kva,
    essential_consumers, remaining_kva, margin, verdict, load_fraction,
    installed_kva (n_generators * generator_kva).
    """
    cont = continuous_load(consumers)
    continuous_kva = cont["continuous_kva"]
    peak_kva = diversity_peak(continuous_kva, diversity_factor)
    ess = essential_load(consumers, essential_names)
    out = generator_out_margin(n_generators, generator_kva, ess["essential_kva"])
    installed_kva = n_generators * generator_kva
    return {
        "continuous_kva": continuous_kva,
        "rollup": cont["rollup"],
        "coincident_peak_kva": peak_kva,
        "essential_kva": ess["essential_kva"],
        "essential_consumers": ess["essential_consumers"],
        "remaining_kva": out["remaining_kva"],
        "margin": out["margin"],
        "verdict": out["verdict"],
        "load_fraction": load_fraction(continuous_kva, installed_kva),
        "installed_kva": installed_kva,
    }
