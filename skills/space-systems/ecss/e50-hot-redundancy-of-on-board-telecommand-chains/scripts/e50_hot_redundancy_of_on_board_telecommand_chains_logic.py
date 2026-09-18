"""Hot-redundancy assessment for on-board telecommand receiving chains.

Anchor: ECSS-E-ST-50C clause 5.4.9 (hot redundancy of on-board telecommand
chains). One normative item, paraphrased into an implementable procedure; no
standard text is reproduced.

A telecommand chain is the path an uplinked command takes from antenna to
decoder output. If every chain has to be commanded on, a spacecraft that has
lost command authority cannot recover it -- the recovery needs the very
capability that failed. Hot redundancy means at least two chains are powered,
enabled and complete at all times, with no element common to all of them.

Procedure implemented here
--------------------------
1. Validate each chain: named elements in path order, a powered flag, an
   enabled flag, and an activation mode saying whether the chain needs a
   command to become receptive.
2. Decide which chains are hot: powered, enabled, complete against the
   required element roles, and not command-activated.
3. Intersect the element sets of the hot chains to find the elements common to
   all of them -- every one of those is a single point of failure for command
   authority, whatever the chain count says.
4. Compute the minimum number of element failures that severs command
   authority: one if a common element exists, otherwise the number of hot
   chains.
5. Report the hot count, the common elements, the severing depth and a finding
   list.
"""

__all__ = [
    "REQUIRED_ROLES",
    "ACTIVATION_ALWAYS_ON",
    "ACTIVATION_COMMANDED",
    "MINIMUM_HOT_CHAINS",
    "validate_element",
    "validate_chain",
    "chain_is_hot",
    "common_elements",
    "severing_depth",
    "assess_hot_redundancy",
]

# The roles a receiving chain must fill end to end. A chain missing any of
# them cannot deliver a command to the on-board software, however healthy the
# elements it does have.
REQUIRED_ROLES = ("antenna", "receiver", "demodulator", "decoder")

ACTIVATION_ALWAYS_ON = "always-on"
ACTIVATION_COMMANDED = "commanded"

MINIMUM_HOT_CHAINS = 2


def validate_element(element, index, chain_name):
    """Return a validated (role, identifier) element record."""
    if not isinstance(element, dict):
        raise ValueError("chain %r element %d must be a mapping" % (chain_name, index))
    for key in ("role", "id"):
        if key not in element:
            raise ValueError("chain %r element %d missing '%s'" % (chain_name, index, key))
    role = element["role"]
    identifier = element["id"]
    if not isinstance(role, str) or not role.strip():
        raise ValueError("chain %r element %d role must be a non-empty string" % (chain_name, index))
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("chain %r element %d id must be a non-empty string" % (chain_name, index))
    role = role.strip().lower()
    if role not in REQUIRED_ROLES:
        raise ValueError(
            "chain %r element %d has unknown role %r; known: %s"
            % (chain_name, index, element["role"], ", ".join(REQUIRED_ROLES))
        )
    return (role, identifier.strip())


def validate_chain(chain):
    """Return a validated chain record with its element roles and identifiers."""
    if not isinstance(chain, dict):
        raise ValueError("chain must be a mapping")
    for key in ("name", "elements", "powered", "enabled", "activation"):
        if key not in chain:
            raise ValueError("chain missing '%s'" % key)
    name = chain["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("chain name must be a non-empty string")
    for flag in ("powered", "enabled"):
        if not isinstance(chain[flag], bool):
            raise ValueError("chain %r '%s' must be a bool" % (name, flag))
    activation = chain["activation"]
    if activation not in (ACTIVATION_ALWAYS_ON, ACTIVATION_COMMANDED):
        raise ValueError(
            "chain %r activation %r must be %r or %r"
            % (name, activation, ACTIVATION_ALWAYS_ON, ACTIVATION_COMMANDED)
        )
    elements = chain["elements"]
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("chain %r must carry a non-empty element list" % name)
    roles = {}
    identifiers = []
    for index, element in enumerate(elements):
        role, identifier = validate_element(element, index, name)
        if role in roles:
            raise ValueError("chain %r carries two elements in the %r role" % (name, role))
        roles[role] = identifier
        identifiers.append(identifier)
    missing = [role for role in REQUIRED_ROLES if role not in roles]
    return {
        "name": name.strip(),
        "roles": roles,
        "identifiers": identifiers,
        "missing_roles": missing,
        "complete": not missing,
        "powered": chain["powered"],
        "enabled": chain["enabled"],
        "activation": activation,
    }


def chain_is_hot(record):
    """Return True when a validated chain is receptive right now with no action."""
    if not isinstance(record, dict) or "complete" not in record:
        raise ValueError("record must be a validated chain record")
    return bool(
        record["powered"]
        and record["enabled"]
        and record["complete"]
        and record["activation"] == ACTIVATION_ALWAYS_ON
    )


def common_elements(records):
    """Return the element identifiers present in every one of the given chains."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of validated chain records")
    if not records:
        return []
    shared = None
    for record in records:
        if not isinstance(record, dict) or "identifiers" not in record:
            raise ValueError("each record must be a validated chain record")
        ids = set(record["identifiers"])
        shared = ids if shared is None else (shared & ids)
    return sorted(shared)


def severing_depth(records):
    """Return how many element failures it takes to sever command authority."""
    hot = [record for record in records if chain_is_hot(record)]
    if not hot:
        return 0
    if common_elements(hot):
        return 1
    return len(hot)


def assess_hot_redundancy(spec):
    """Run the full clause 5.4.9 hot-redundancy assessment.

    spec keys: chains (sequence of {name, elements, powered, enabled,
    activation}), optional minimum_hot_chains.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "chains" not in spec:
        raise ValueError("spec missing required key 'chains'")
    chains = spec["chains"]
    if not isinstance(chains, (list, tuple)) or not chains:
        raise ValueError("chains must be a non-empty sequence")
    minimum = spec.get("minimum_hot_chains", MINIMUM_HOT_CHAINS)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        raise ValueError("minimum_hot_chains must be an integer of at least one")

    records = []
    seen = set()
    for chain in chains:
        record = validate_chain(chain)
        if record["name"] in seen:
            raise ValueError("duplicate chain name %r" % record["name"])
        seen.add(record["name"])
        record["hot"] = chain_is_hot(record)
        records.append(record)

    hot = [record for record in records if record["hot"]]
    shared = common_elements(hot)
    depth = severing_depth(records)

    findings = []
    if len(hot) < minimum:
        findings.append(
            "%d chain(s) are hot; %d are required to be receptive with no command"
            % (len(hot), minimum)
        )
    for record in records:
        if record["hot"]:
            continue
        reasons = []
        if not record["powered"]:
            reasons.append("unpowered")
        if not record["enabled"]:
            reasons.append("disabled")
        if not record["complete"]:
            reasons.append("missing %s" % ", ".join(record["missing_roles"]))
        if record["activation"] == ACTIVATION_COMMANDED:
            reasons.append("needs a command to become receptive")
        findings.append("chain %s is not hot: %s" % (record["name"], "; ".join(reasons)))
    if shared:
        findings.append(
            "element(s) %s are common to every hot chain and sever command authority alone"
            % ", ".join(shared)
        )

    return {
        "records": records,
        "hot_chains": [record["name"] for record in hot],
        "hot_count": len(hot),
        "common_elements": shared,
        "severing_depth": depth,
        "compliant": len(hot) >= minimum and not shared,
        "findings": findings,
    }
