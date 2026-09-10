"""Deterministic logic for ECSS-E-ST-10-02C 5.2.5 model philosophy.

Offline, stdlib-only module backing the e1002-models skill leaf:
selecting a model philosophy (prototype vs protoflight), validating a
model list for the Verification Plan (VP), checking that a model used
for verification is representative of the item it stands in for, and
flagging when a design change invalidates prior model-based
verification credit.
"""

MODEL_DESIGNATIONS = frozenset({"STM", "EM", "QM", "PFM", "FM", "EQM"})

PHILOSOPHIES = frozenset({"prototype", "protoflight"})

REQUIRED_MODEL_LIST_FIELDS = ("designation", "purpose", "configuration", "stages")


def select_philosophy(
    margin_preservation_required: bool,
    schedule_constrained: bool,
    cost_constrained: bool,
) -> str:
    """Pick prototype vs protoflight for the VP model philosophy.

    Precedence: preserving full qualification margins on the flight
    article outranks schedule/cost pressure, so it forces the
    prototype approach (a disposable QM absorbs qualification
    stresses, the FM is built and only acceptance-tested). Otherwise,
    schedule or cost pressure justifies the protoflight approach (a
    single PFM absorbs qualification-level tests, at reduced duration,
    then is refurbished and flown). With neither driver present,
    prototype is the conservative default.
    """
    if margin_preservation_required:
        return "prototype"
    if schedule_constrained or cost_constrained:
        return "protoflight"
    return "prototype"


def validate_model_list(models: list) -> list:
    """Check a VP model list for completeness.

    Returns a list of human-readable issue strings; an empty list
    means the model list is fit to record in the Verification Plan.
    Each model dict must carry designation/purpose/configuration/
    stages, the designation must be a recognised model type, and
    stages must be a non-empty sequence.
    """
    issues = []
    if not models:
        issues.append("model list is empty: VP must record at least one model")
        return issues

    seen_designations = set()
    for index, model in enumerate(models):
        label = f"model[{index}]"
        missing = [f for f in REQUIRED_MODEL_LIST_FIELDS if model.get(f) is None]
        if missing:
            issues.append(f"{label}: missing required field(s) {missing}")
            continue

        designation = model["designation"]
        if designation not in MODEL_DESIGNATIONS:
            issues.append(
                f"{label}: unrecognised designation '{designation}' "
                f"(expected one of {sorted(MODEL_DESIGNATIONS)})"
            )
        if designation in seen_designations:
            issues.append(f"{label}: duplicate designation '{designation}' in model list")
        seen_designations.add(designation)

        if not model["stages"]:
            issues.append(f"{label}: 'stages' must list at least one verification stage")

    return issues


def check_representativeness(model_configuration: str, item_configuration: str) -> bool:
    """A model can only carry verification credit for a configuration it matches.

    Verification performed on a model is only creditable for the item
    it represents when the tested configuration and the item's
    configuration are the same design standard; a mismatch means the
    result cannot be claimed against the item without re-verification.
    """
    return model_configuration == item_configuration


def protoflight_severity_ok(
    applied_amplitude: float,
    qualification_amplitude: float,
    applied_duration: float,
    qualification_duration: float,
) -> tuple:
    """Check a PFM test campaign against protoflight severity rules.

    Protoflight testing must apply full qualification-level amplitude
    (it is not reduced, since the unit will still be flown after
    surviving it) but may reduce duration/cycle count relative to a
    prototype qualification campaign to limit fatigue/life consumption
    on the article that will fly. Returns (ok, reasons).
    """
    reasons = []
    if applied_amplitude < qualification_amplitude:
        reasons.append(
            "applied amplitude below qualification amplitude: protoflight must not "
            "reduce test severity, only duration"
        )
    if applied_duration > qualification_duration:
        reasons.append(
            "applied duration exceeds qualification duration: protoflight duration "
            "must be at or below the qualification baseline to preserve flight life"
        )
    return (not reasons, reasons)


def needs_reverification(tested_before_change: bool, design_changed_after_test: bool) -> bool:
    """Flag when a design change invalidates prior model-based verification credit.

    If a model was already exercised against a requirement and the
    design of the item (or the model) changes afterwards, the earlier
    result no longer covers the requirement and re-verification must
    be triggered before closure.
    """
    return tested_before_change and design_changed_after_test
