"""Forward event-tree analysis rollup for ARP4761A-class system safety.

Pure stdlib, deterministic, no RNG. Implements the forward dual of fault
tree analysis: from one initiating event with a per-flight-hour frequency,
an ordered list of mitigating functions (each with success probability p),
a full 2**N binary expansion of branch paths, end-state frequency rollup,
failure end-state frequency sum, and dominant-sequence screening against
the per-flight-hour severity targets of the ARP4761A FHA probability-target
mapping (catastrophic 1e-9, hazardous 1e-7, major 1e-5, minor 1e-3,
paraphrased by magnitude only; the targets themselves are analyst inputs
into this module, never derived here).

Skill workflow mapping: step 3 of the SKILL.md workflow (enumerate the
full binary branch tree with build_paths), step 4 (roll up and rank the
end-state frequencies with outcome_frequencies), step 5 (identify the
failure end state and sum its frequency with is_failure_end_state and
top_function_failure_frequency) and step 6 (screen the ranked sequences
against the severity target of each end state's FHA class with
dominant_sequences) are all implemented by this module.
"""

BRANCH_NODES_MAX = 12
"""Hard cap on branch nodes: 2**12 = 4096 paths is the largest expansion."""

# ARP4761A-class per-flight-hour severity targets, magnitude only,
# mirroring the FHA probability-target mapping magnitudes.
CATASTROPHIC = 1e-9
HAZARDOUS = 1e-7
MAJOR = 1e-5
MINOR = 1e-3

_SUCCESS = "S"
_FAILURE = "F"


def _validate_nodes(nodes):
    """Raise ValueError when the node list is not a physical branch tree.

    Accepts a non-empty list of (name, p_success) tuples with every branch
    probability inside [0, 1] (boundaries legal) and at most
    BRANCH_NODES_MAX nodes.
    """
    if not nodes:
        raise ValueError("node list must not be empty")
    if len(nodes) > BRANCH_NODES_MAX:
        raise ValueError(
            "node count %d exceeds BRANCH_NODES_MAX=%d"
            % (len(nodes), BRANCH_NODES_MAX)
        )
    for name, p_success in nodes:
        if not 0.0 <= p_success <= 1.0:
            raise ValueError(
                "branch success probability %r for node %r must lie in "
                "[0, 1]" % (p_success, name)
            )


def _branch_label(name, success):
    """Render one node outcome as the readable sequence token name:S/F."""
    return "%s:%s" % (name, _SUCCESS if success else _FAILURE)


def build_paths(nodes):
    """Enumerate the full binary expansion of the ordered node list.

    nodes is a list of (name, p_success) tuples. Returns one dict per path
    with keys sequence (readable string like "detect:S extinguish:F"),
    path (tuple of bools, True = function succeeds) and probability (the
    product of the branch probabilities: p for a success branch, 1 - p
    for a failure branch). Enumeration order is the ascending binary mask
    with node i mapped to bit i, so the all-failure path (mask 0) comes
    first and the all-success path (mask 2**N - 1) comes last.
    """
    _validate_nodes(nodes)
    count = len(nodes)
    paths = []
    for mask in range(1 << count):
        labels = []
        outcomes = []
        probability = 1.0
        for index, (name, p_success) in enumerate(nodes):
            success = bool((mask >> index) & 1)
            labels.append(_branch_label(name, success))
            outcomes.append(success)
            probability *= p_success if success else (1.0 - p_success)
        paths.append(
            {
                "sequence": " ".join(labels),
                "path": tuple(outcomes),
                "probability": probability,
            }
        )
    return paths


def outcome_frequencies(initiator_frequency, nodes):
    """Roll up every end-state frequency and rank them descending.

    frequency = initiator_frequency x path probability for every path of
    the full expansion. The returned list is sorted descending by
    frequency with ties broken by enumeration order (stable). Each dict
    carries exactly the keys sequence, path, probability, frequency.
    """
    if initiator_frequency < 0.0:
        raise ValueError("initiator frequency must be non-negative")
    paths = build_paths(nodes)
    results = []
    for path in paths:
        results.append(
            {
                "sequence": path["sequence"],
                "path": path["path"],
                "probability": path["probability"],
                "frequency": initiator_frequency * path["probability"],
            }
        )
    results.sort(key=lambda entry: entry["frequency"], reverse=True)
    return results


def is_failure_end_state(path):
    """True exactly when every outcome on the path is False.

    The failure end state under the series-barriers reading: no
    mitigating function contained the initiator, so the top-level safety
    function failed.
    """
    return all(not outcome for outcome in path)


def top_function_failure_frequency(frequencies):
    """Sum the frequency over the paths that reach the failure end state.

    Returns a dict with sequences (the sequence strings reaching the
    failure end state, in input order) and frequency (sum of their
    frequencies). Under the full 2**N expansion exactly one path (all
    failures) reaches the failure end state, so the sum equals that
    path's frequency; the implementation still sums over the flagged
    paths per the rollup definition.
    """
    sequences = []
    total = 0.0
    for entry in frequencies:
        if is_failure_end_state(entry["path"]):
            sequences.append(entry["sequence"])
            total += entry["frequency"]
    return {"sequences": sequences, "frequency": total}


def dominant_sequences(frequencies, severity_target):
    """Flag the sequences whose frequency strictly exceeds the target.

    Returns, in the input frequency-descending order, one dict per
    sequence with keys sequence, frequency and ratio = frequency /
    severity_target. Strict comparison: frequency equal to the target is
    NOT dominant, mirroring the strict target rule of the severity
    rating work. Empty list when nothing exceeds.
    """
    if severity_target <= 0.0:
        raise ValueError("severity target must be positive")
    dominant = []
    for entry in frequencies:
        if entry["frequency"] > severity_target:
            dominant.append(
                {
                    "sequence": entry["sequence"],
                    "frequency": entry["frequency"],
                    "ratio": entry["frequency"] / severity_target,
                }
            )
    return dominant
