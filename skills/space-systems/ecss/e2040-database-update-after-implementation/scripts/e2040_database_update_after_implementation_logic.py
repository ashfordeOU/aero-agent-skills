"""As-built repository deposit at the close of the implementation phase.

Anchor: ECSS-E-ST-20-40C clause 5.7.3 (paraphrased into an
implementable procedure; no standard text is reproduced).

This is the as-built record, distinct from the layout-phase deposit
that fed implementation. Procedure implemented here:

1. Derive the owed as-built set from the device: the final netlist,
   the production test program and the implementation report per
   technology, plus the final programming file per technology when the
   implementation is loaded rather than fabricated.
2. Validate each deposit: kind, technology, baseline label, lifecycle
   state, digest and tool-chain record.
3. Select the active deposit per owed entry. Two active deposits for
   one entry is a finding: the repository does not say which one was
   delivered.
4. Prove identity by digest. The deposited digest has to equal the
   digest read back from the device or lot; a deposit with no
   read-back digest is unproven rather than matched.
5. Check the freeze and the regeneration record: a baseline label that
   names a moving branch, a missing tool-chain version, or missing run
   parameters for a non-deterministic implementation.
6. Report completeness as the fraction of owed entries with a clean
   active deposit, naming the gaps.

Stdlib only, offline, deterministic.
"""

KIND_FINAL_NETLIST = "final-netlist"
KIND_PRODUCTION_TEST_PROGRAM = "production-test-program"
KIND_IMPLEMENTATION_REPORT = "implementation-report"
KIND_FINAL_PROGRAMMING_FILE = "final-programming-file"

TECHNOLOGY_DEPENDENT_KINDS = (
    KIND_FINAL_NETLIST,
    KIND_PRODUCTION_TEST_PROGRAM,
    KIND_IMPLEMENTATION_REPORT,
)
LOADED_IMPLEMENTATION_KINDS = (KIND_FINAL_PROGRAMMING_FILE,)
VALID_KINDS = TECHNOLOGY_DEPENDENT_KINDS + LOADED_IMPLEMENTATION_KINDS

# Only these kinds are loaded into hardware, so only these carry a
# digest that can be read back from a device or a lot.
DIGEST_BEARING_KINDS = (KIND_FINAL_PROGRAMMING_FILE,)

DEVICE_KIND_ASIC = "asic"
DEVICE_KIND_FPGA = "fpga"
DEVICE_KIND_IP_CORE = "ip-core"
VALID_DEVICE_KINDS = (DEVICE_KIND_ASIC, DEVICE_KIND_FPGA, DEVICE_KIND_IP_CORE)
LOADED_DEVICE_KINDS = (DEVICE_KIND_FPGA,)

STATE_ACTIVE = "active"
STATE_RETIRED = "retired"
VALID_STATES = (STATE_ACTIVE, STATE_RETIRED)

BASELINE_KIND_FROZEN_TAG = "frozen-baseline-tag"
BASELINE_KIND_MOVING_BRANCH = "moving-branch"
VALID_BASELINE_KINDS = (BASELINE_KIND_FROZEN_TAG, BASELINE_KIND_MOVING_BRANCH)

FINDING_MISSING_DEPOSIT = "owed-as-built-item-not-deposited"
FINDING_TWO_ACTIVE_DEPOSITS = "two-active-deposits-for-one-owed-entry"
FINDING_DIGEST_MISMATCH = "deposit-digest-differs-from-the-device-read-back"
FINDING_DIGEST_UNPROVEN = "deposit-without-a-device-read-back-digest"
FINDING_NOT_FROZEN = "deposit-pointing-at-a-moving-branch"
FINDING_NO_TOOLCHAIN_RECORD = "deposit-without-a-recorded-tool-chain-version"
FINDING_NO_RUN_PARAMETERS = "non-deterministic-deposit-without-run-parameters"
FINDING_UNEXPECTED_DEPOSIT = "deposit-outside-the-owed-as-built-set"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _optional_text(label, value):
    if value is None:
        return None
    return _text(label, value)


def _count(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def validate_device(device):
    """Validate the device record and return a normalized copy."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping")
    device_id = _text("device id", device.get("id"))
    kind = device.get("kind")
    if kind not in VALID_DEVICE_KINDS:
        raise ValueError(
            "device %s has unknown kind %r (expected one of %s)"
            % (device_id, kind, ", ".join(VALID_DEVICE_KINDS))
        )
    technologies = device.get("technologies")
    if not isinstance(technologies, (list, tuple)) or not technologies:
        raise ValueError("device %s needs a non-empty technologies list" % device_id)
    normalized = []
    for item in technologies:
        name = _text("device %s technology" % device_id, item)
        if name in normalized:
            raise ValueError("device %s lists technology %r twice" % (device_id, name))
        normalized.append(name)
    return {"id": device_id, "kind": kind, "technologies": normalized}


def is_loaded_implementation(device):
    """True when the implementation is loaded into the part, not fabricated."""
    return validate_device(device)["kind"] in LOADED_DEVICE_KINDS


def owed_as_built_entries(device):
    """The (kind, technology) as-built entries implementation owes."""
    norm = validate_device(device)
    kinds = list(TECHNOLOGY_DEPENDENT_KINDS)
    if norm["kind"] in LOADED_DEVICE_KINDS:
        kinds.extend(LOADED_IMPLEMENTATION_KINDS)
    entries = []
    for technology in norm["technologies"]:
        for kind in kinds:
            entries.append((kind, technology))
    return entries


def validate_deposit(deposit, device):
    """Validate one as-built deposit against the device record."""
    norm_device = validate_device(device)
    if not isinstance(deposit, dict):
        raise ValueError("deposit must be a mapping")
    kind = deposit.get("kind")
    if kind not in VALID_KINDS:
        raise ValueError(
            "deposit has unknown kind %r (expected one of %s)"
            % (kind, ", ".join(VALID_KINDS))
        )
    technology = _text("deposit %s technology" % kind, deposit.get("technology"))
    if technology not in norm_device["technologies"]:
        raise ValueError(
            "deposit %s names technology %r which the device does not use"
            % (kind, technology)
        )
    baseline_label = _text("deposit %s baseline_label" % kind, deposit.get("baseline_label"))
    baseline_kind = deposit.get("baseline_kind", BASELINE_KIND_FROZEN_TAG)
    if baseline_kind not in VALID_BASELINE_KINDS:
        raise ValueError(
            "deposit %s has unknown baseline_kind %r (expected one of %s)"
            % (kind, baseline_kind, ", ".join(VALID_BASELINE_KINDS))
        )
    state = deposit.get("state", STATE_ACTIVE)
    if state not in VALID_STATES:
        raise ValueError(
            "deposit %s has unknown state %r (expected one of %s)"
            % (kind, state, ", ".join(VALID_STATES))
        )
    deterministic = deposit.get("deterministic", True)
    if not isinstance(deterministic, bool):
        raise ValueError("deposit %s deterministic must be a boolean" % kind)
    run_parameter_count = _count(
        "deposit %s run_parameter_count" % kind, deposit.get("run_parameter_count", 0)
    )
    return {
        "kind": kind,
        "technology": technology,
        "baseline_label": baseline_label,
        "baseline_kind": baseline_kind,
        "state": state,
        "deposited_digest": _optional_text(
            "deposit %s deposited_digest" % kind, deposit.get("deposited_digest")
        ),
        "read_back_digest": _optional_text(
            "deposit %s read_back_digest" % kind, deposit.get("read_back_digest")
        ),
        "toolchain_version": _optional_text(
            "deposit %s toolchain_version" % kind, deposit.get("toolchain_version")
        ),
        "deterministic": deterministic,
        "run_parameter_count": run_parameter_count,
    }


def digest_findings(deposit, device):
    """Findings from comparing a deposit digest with the device read-back."""
    norm = validate_deposit(deposit, device)
    if norm["kind"] not in DIGEST_BEARING_KINDS:
        return []
    if norm["deposited_digest"] is None or norm["read_back_digest"] is None:
        return [FINDING_DIGEST_UNPROVEN]
    if norm["deposited_digest"] != norm["read_back_digest"]:
        return [FINDING_DIGEST_MISMATCH]
    return []


def freeze_findings(deposit, device):
    """Findings about the freeze and the regeneration record."""
    norm = validate_deposit(deposit, device)
    findings = []
    if norm["baseline_kind"] != BASELINE_KIND_FROZEN_TAG:
        findings.append(FINDING_NOT_FROZEN)
    if norm["toolchain_version"] is None:
        findings.append(FINDING_NO_TOOLCHAIN_RECORD)
    if not norm["deterministic"] and norm["run_parameter_count"] == 0:
        findings.append(FINDING_NO_RUN_PARAMETERS)
    return findings


def check_deposit(deposit, device):
    """All findings about one as-built deposit."""
    return digest_findings(deposit, device) + freeze_findings(deposit, device)


def completeness_fraction(satisfied, owed):
    """Fraction of owed as-built entries satisfied by a clean deposit."""
    owed_count = _count("owed", owed)
    satisfied_count = _count("satisfied", satisfied)
    if owed_count == 0:
        raise ValueError("owed must be > 0 to form a completeness fraction")
    if satisfied_count > owed_count:
        raise ValueError(
            "satisfied %d cannot exceed owed %d" % (satisfied_count, owed_count)
        )
    return satisfied_count / owed_count


def assess_database_update_after_implementation(device, deposits):
    """Assess the as-built repository deposit against clause 5.7.3."""
    norm_device = validate_device(device)
    if not isinstance(deposits, list):
        raise ValueError("deposits must be a list")
    owed = owed_as_built_entries(norm_device)
    active = {}
    retired = []
    findings = []
    unexpected = []
    for deposit in deposits:
        norm = validate_deposit(deposit, norm_device)
        entry = (norm["kind"], norm["technology"])
        if norm["state"] == STATE_RETIRED:
            retired.append((entry, norm["baseline_label"]))
            continue
        if entry not in owed:
            unexpected.append(entry)
            findings.append((entry, FINDING_UNEXPECTED_DEPOSIT))
            continue
        if entry in active:
            findings.append((entry, FINDING_TWO_ACTIVE_DEPOSITS))
            continue
        active[entry] = norm
    gaps = []
    clean = 0
    digest_results = {}
    for entry in owed:
        deposit = active.get(entry)
        if deposit is None:
            gaps.append(entry)
            findings.append((entry, FINDING_MISSING_DEPOSIT))
            continue
        entry_findings = check_deposit(deposit, norm_device)
        if entry[0] in DIGEST_BEARING_KINDS:
            digest_results[entry] = not [
                name
                for name in entry_findings
                if name in (FINDING_DIGEST_MISMATCH, FINDING_DIGEST_UNPROVEN)
            ]
        if entry_findings:
            for name in entry_findings:
                findings.append((entry, name))
        else:
            clean += 1
    return {
        "device_id": norm_device["id"],
        "owed": owed,
        "owed_count": len(owed),
        "satisfied_count": clean,
        "completeness": completeness_fraction(clean, len(owed)),
        "gaps": gaps,
        "unexpected": unexpected,
        "retired": retired,
        "digest_proven": digest_results,
        "findings": findings,
        "phase_may_close": not findings,
    }
