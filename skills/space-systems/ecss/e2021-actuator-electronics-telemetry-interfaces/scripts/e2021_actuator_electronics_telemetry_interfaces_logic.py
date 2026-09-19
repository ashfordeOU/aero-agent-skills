"""Housekeeping routing from both actuator electronics chains.

Anchor: ECSS-E-ST-20-21C clause 5.2.4 (paraphrased into an
implementable procedure; no standard text is reproduced).

The housekeeping of both actuator electronics chains has to reach both
telemetry acquisition paths. The reason is asymmetric with the command
side: a command that cannot be sent is a lost function, while
housekeeping that cannot be read is a lost function nobody notices.
An arm status that is only visible through the nominal acquisition path
goes dark the moment that path fails, and the operator is then flying a
chain whose state is unknown while the chain itself is still healthy.

Procedure implemented here:

1. Validate the declared housekeeping channels: which parameter, from
   which electronics chain, out to which acquisition paths, and whether
   the fan-out to the two paths is buffered.
2. Compare the declared set against the parameters each chain owes,
   and name the chain and parameter pairs that are absent altogether.
3. Categorize the declared channels by how many acquisition paths they
   reach. A channel on one path only is observable today and dark after
   one acquisition failure.
4. Check the buffering of every channel that fans out to both paths. An
   unbuffered fan-out couples the two acquisition paths through the
   source, so a short on one path can pull the same measurement down on
   the other.
5. Remove each acquisition path in turn and report the housekeeping
   that survives, then close with a verdict, the observability coverage
   and findings naming each gap.

Stdlib only, offline, deterministic.
"""

CHAIN_NOMINAL = "nominal-electronics"
CHAIN_REDUNDANT = "redundant-electronics"
ELECTRONICS_CHAINS = (CHAIN_NOMINAL, CHAIN_REDUNDANT)

PATH_NOMINAL = "nominal-acquisition"
PATH_REDUNDANT = "redundant-acquisition"
ACQUISITION_PATHS = (PATH_NOMINAL, PATH_REDUNDANT)

# The housekeeping each electronics chain owes. Arm, select and fire
# status say where the chain sits in the actuation sequence; the firing
# current monitor is the only evidence that a commanded pulse was
# actually delivered.
REQUIRED_PARAMETERS = (
    "arm-status",
    "select-status",
    "fire-status",
    "firing-current-monitor",
)

FINDING_PARAMETER_ABSENT = "housekeeping-parameter-absent"
FINDING_SINGLE_PATH_CHANNEL = "housekeeping-on-one-path-only"
FINDING_UNBUFFERED_FANOUT = "unbuffered-acquisition-fanout"
FINDING_PATH_LOSS_BLINDS_CHAIN = "acquisition-loss-blinds-a-chain"


def _non_empty_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_channel(channel):
    """Validate one housekeeping channel and return a normalized copy."""
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    parameter = _non_empty_text("channel parameter", channel.get("parameter"))
    source = channel.get("source_chain")
    if source not in ELECTRONICS_CHAINS:
        raise ValueError(
            "channel %s has unknown source_chain %r (expected one of %s)"
            % (parameter, source, ", ".join(ELECTRONICS_CHAINS))
        )
    paths = channel.get("acquisition_paths")
    if not isinstance(paths, (list, tuple)):
        raise ValueError(
            "channel %s acquisition_paths must be a sequence" % parameter
        )
    if not paths:
        raise ValueError(
            "channel %s reaches no acquisition path" % parameter
        )
    seen = []
    for path in paths:
        if path not in ACQUISITION_PATHS:
            raise ValueError(
                "channel %s has unknown acquisition path %r (expected one of %s)"
                % (parameter, path, ", ".join(ACQUISITION_PATHS))
            )
        if path in seen:
            raise ValueError(
                "channel %s lists acquisition path %s twice" % (parameter, path)
            )
        seen.append(path)
    ordered = tuple(p for p in ACQUISITION_PATHS if p in seen)
    return {
        "parameter": parameter,
        "source_chain": source,
        "acquisition_paths": ordered,
        "buffered": _boolean(
            "channel %s buffered" % parameter, channel.get("buffered", True)
        ),
        "path_count": len(ordered),
    }


def validate_housekeeping(channels):
    """Validate the declared housekeeping set and normalize it."""
    if not isinstance(channels, (list, tuple)):
        raise ValueError("channels must be a sequence of mappings")
    if not channels:
        raise ValueError("channels must not be empty")
    normalized = [validate_channel(c) for c in channels]
    seen = set()
    for record in normalized:
        key = channel_key(record)
        if key in seen:
            raise ValueError("duplicate housekeeping channel %s" % (key,))
        seen.add(key)
    return normalized


def channel_key(record):
    """Identity of one channel: source electronics chain and parameter."""
    return (record["source_chain"], record["parameter"])


def required_channels():
    """Every chain and parameter pair the clause expects."""
    return tuple(
        (chain, parameter)
        for chain in ELECTRONICS_CHAINS
        for parameter in REQUIRED_PARAMETERS
    )


def absent_channels(channels):
    """Required chain and parameter pairs that are not declared at all."""
    present = {channel_key(r) for r in validate_housekeeping(channels)}
    return tuple(key for key in required_channels() if key not in present)


def single_path_channels(channels):
    """Declared channels that reach one acquisition path only."""
    return tuple(
        sorted(channel_key(r) for r in validate_housekeeping(channels) if r["path_count"] == 1)
    )


def dual_path_channels(channels):
    """Declared channels that reach both acquisition paths."""
    return tuple(
        sorted(channel_key(r) for r in validate_housekeeping(channels) if r["path_count"] == 2)
    )


def unbuffered_fanouts(channels):
    """Channels that fan out to both paths without buffering."""
    return tuple(
        sorted(
            channel_key(r)
            for r in validate_housekeeping(channels)
            if r["path_count"] == 2 and not r["buffered"]
        )
    )


def observability_coverage(channels):
    """Share of the required channels that reach both acquisition paths."""
    dual = set(dual_path_channels(channels))
    required = required_channels()
    covered = sum(1 for key in required if key in dual)
    return covered / float(len(required))


def observable_after_path_loss(channels, lost_path):
    """Required channels still readable once one acquisition path is lost."""
    if lost_path not in ACQUISITION_PATHS:
        raise ValueError(
            "unknown acquisition path %r (expected one of %s)"
            % (lost_path, ", ".join(ACQUISITION_PATHS))
        )
    records = validate_housekeeping(channels)
    surviving = {
        channel_key(r)
        for r in records
        if any(p != lost_path for p in r["acquisition_paths"])
    }
    return tuple(key for key in required_channels() if key in surviving)


def blinded_chains_after_path_loss(channels, lost_path):
    """Electronics chains left with no required housekeeping at all."""
    surviving = set(observable_after_path_loss(channels, lost_path))
    blinded = []
    for chain in ELECTRONICS_CHAINS:
        if not any(key[0] == chain for key in surviving):
            blinded.append(chain)
    return tuple(blinded)


def telemetry_findings(channels):
    """Findings against the housekeeping routing requirement."""
    records = validate_housekeeping(channels)
    findings = []
    for chain, parameter in absent_channels(records):
        findings.append(
            {
                "code": FINDING_PARAMETER_ABSENT,
                "subject": "%s/%s" % (chain, parameter),
                "detail": "%s declares no %s channel" % (chain, parameter),
            }
        )
    for chain, parameter in single_path_channels(records):
        findings.append(
            {
                "code": FINDING_SINGLE_PATH_CHANNEL,
                "subject": "%s/%s" % (chain, parameter),
                "detail": "%s from %s reaches one acquisition path only"
                % (parameter, chain),
            }
        )
    for chain, parameter in unbuffered_fanouts(records):
        findings.append(
            {
                "code": FINDING_UNBUFFERED_FANOUT,
                "subject": "%s/%s" % (chain, parameter),
                "detail": "%s from %s fans out to both paths unbuffered"
                % (parameter, chain),
            }
        )
    for lost in ACQUISITION_PATHS:
        for chain in blinded_chains_after_path_loss(records, lost):
            findings.append(
                {
                    "code": FINDING_PATH_LOSS_BLINDS_CHAIN,
                    "subject": "%s/%s" % (lost, chain),
                    "detail": "losing %s leaves %s with no readable housekeeping"
                    % (lost, chain),
                }
            )
    return sorted(findings, key=lambda f: (f["code"], f["subject"]))


def assess_telemetry_interfaces(channels):
    """Grade a declared actuator electronics housekeeping routing."""
    records = validate_housekeeping(channels)
    findings = telemetry_findings(records)
    return {
        "declared_channel_count": len(records),
        "required_channel_count": len(required_channels()),
        "absent_channels": absent_channels(records),
        "single_path_channels": single_path_channels(records),
        "dual_path_channels": dual_path_channels(records),
        "unbuffered_fanouts": unbuffered_fanouts(records),
        "observability_coverage": observability_coverage(records),
        "observable_after_loss": {
            lost: observable_after_path_loss(records, lost)
            for lost in ACQUISITION_PATHS
        },
        "blinded_chains": {
            lost: blinded_chains_after_path_loss(records, lost)
            for lost in ACQUISITION_PATHS
        },
        "findings": findings,
        "finding_codes": sorted({f["code"] for f in findings}),
        "compliant": not findings,
    }
