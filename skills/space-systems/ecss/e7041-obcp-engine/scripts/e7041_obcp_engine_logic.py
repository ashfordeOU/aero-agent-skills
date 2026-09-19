"""On-board control procedure engine admission and utilisation.

Anchor: ECSS-E-ST-70-41C clause 6.18.2.3 (the OBCP engine). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the engine capability declaration: state, concurrency limits,
   procedure store, per-cycle step budget and the supported procedure
   languages with their versions.
2. Validate each procedure: language, language version, code and data
   footprint, per-cycle step demand.
3. Account for what the engine currently holds: store consumed by the loaded
   set, step budget consumed by the running set.
4. Admit or refuse a load and a start against the engine state and each
   bounded resource in turn, naming the resource that refused.
5. Apply a sequence of requests in order, because every acceptance changes
   the resources the next request is graded against.
6. Report utilisation as four independent fractions.
"""

__all__ = [
    "ENGINE_STATES",
    "LOAD_REFUSALS",
    "START_REFUSALS",
    "validate_engine",
    "validate_procedure",
    "validate_procedure_set",
    "language_supported",
    "store_used_bytes",
    "free_store_bytes",
    "steps_used_per_cycle",
    "free_steps_per_cycle",
    "can_load",
    "can_start",
    "engine_utilisation",
    "apply_requests",
    "assess_obcp_engine",
]

ENGINE_STATES = ("running", "stopped")

LOAD_REFUSALS = (
    "engine-stopped",
    "procedure-already-loaded",
    "language-not-supported",
    "language-version-not-supported",
    "loaded-procedure-limit-reached",
    "insufficient-engine-store",
)

START_REFUSALS = (
    "engine-stopped",
    "procedure-not-loaded",
    "procedure-already-running",
    "running-procedure-limit-reached",
    "step-budget-per-cycle-exceeded",
)


def _require_int(value, label, minimum=0):
    """Return value as an int at or above a minimum, refusing bools."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return int(value)


def _require_text(value, label):
    """Return value as a non-empty stripped string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def validate_engine(engine):
    """Return a normalised engine capability declaration."""
    if not isinstance(engine, dict):
        raise ValueError("engine must be a mapping, got %r" % (engine,))
    engine_id = _require_text(engine.get("engine_id"), "engine_id")
    state = engine.get("state", "running")
    if state not in ENGINE_STATES:
        raise ValueError(
            "engine state %r is not one of %s" % (state, ", ".join(ENGINE_STATES))
        )
    max_loaded = _require_int(engine.get("max_loaded"), "max_loaded", 0)
    max_running = _require_int(engine.get("max_running"), "max_running", 0)
    if max_running > max_loaded:
        raise ValueError(
            "engine %s declares max_running %d above max_loaded %d; a procedure "
            "cannot run without being loaded" % (engine_id, max_running, max_loaded)
        )
    store = _require_int(engine.get("store_bytes"), "store_bytes", 1)
    steps = _require_int(engine.get("step_budget_per_cycle"),
                         "step_budget_per_cycle", 1)
    languages = engine.get("supported_languages")
    if not isinstance(languages, (list, tuple)) or not languages:
        raise ValueError(
            "engine %s must support at least one procedure language" % engine_id
        )
    normalised = []
    for item in languages:
        if not isinstance(item, dict):
            raise ValueError("each supported language must be a mapping")
        language = _require_text(item.get("language"), "language")
        versions = item.get("versions")
        if not isinstance(versions, (list, tuple)) or not versions:
            raise ValueError(
                "language %s must declare at least one supported version" % language
            )
        seen = []
        for version in versions:
            text = _require_text(version, "language version")
            if text in seen:
                raise ValueError(
                    "language %s declares version %s twice" % (language, text)
                )
            seen.append(text)
        if any(entry["language"] == language for entry in normalised):
            raise ValueError("language %s is declared twice" % language)
        normalised.append({"language": language, "versions": sorted(seen)})
    return {
        "engine_id": engine_id,
        "state": state,
        "max_loaded": max_loaded,
        "max_running": max_running,
        "store_bytes": store,
        "step_budget_per_cycle": steps,
        "supported_languages": normalised,
    }


def validate_procedure(procedure):
    """Return a normalised on-board control procedure record."""
    if not isinstance(procedure, dict):
        raise ValueError("procedure must be a mapping, got %r" % (procedure,))
    procedure_id = _require_text(procedure.get("procedure_id"), "procedure_id")
    language = _require_text(procedure.get("language"), "language")
    version = _require_text(procedure.get("language_version"), "language_version")
    code = _require_int(procedure.get("code_bytes"), "code_bytes", 1)
    data = _require_int(procedure.get("data_bytes", 0), "data_bytes", 0)
    steps = _require_int(procedure.get("steps_per_cycle"), "steps_per_cycle", 1)
    return {
        "procedure_id": procedure_id,
        "language": language,
        "language_version": version,
        "code_bytes": code,
        "data_bytes": data,
        "footprint_bytes": code + data,
        "steps_per_cycle": steps,
    }


def validate_procedure_set(procedures):
    """Return the procedures keyed by identifier."""
    if not isinstance(procedures, (list, tuple)) or not procedures:
        raise ValueError("at least one procedure is required")
    catalogue = {}
    for procedure in procedures:
        norm = validate_procedure(procedure)
        if norm["procedure_id"] in catalogue:
            raise ValueError("procedure %s is declared twice" % norm["procedure_id"])
        catalogue[norm["procedure_id"]] = norm
    return catalogue


def language_supported(engine, language, language_version):
    """Return (supported, reason) for a procedure language and version."""
    norm = validate_engine(engine)
    lang = _require_text(language, "language")
    version = _require_text(language_version, "language_version")
    for entry in norm["supported_languages"]:
        if entry["language"] == lang:
            if version in entry["versions"]:
                return (True, None)
            return (False, "language-version-not-supported")
    return (False, "language-not-supported")


def store_used_bytes(catalogue, loaded_ids):
    """Return the engine store consumed by the loaded procedures."""
    total = 0
    for procedure_id in loaded_ids:
        if procedure_id not in catalogue:
            raise ValueError("loaded procedure %s is not declared" % procedure_id)
        total += catalogue[procedure_id]["footprint_bytes"]
    return total


def free_store_bytes(engine, catalogue, loaded_ids):
    """Return the engine store still available for another procedure."""
    norm = validate_engine(engine)
    return norm["store_bytes"] - store_used_bytes(catalogue, loaded_ids)


def steps_used_per_cycle(catalogue, running_ids):
    """Return the per-cycle step demand of the running procedures."""
    total = 0
    for procedure_id in running_ids:
        if procedure_id not in catalogue:
            raise ValueError("running procedure %s is not declared" % procedure_id)
        total += catalogue[procedure_id]["steps_per_cycle"]
    return total


def free_steps_per_cycle(engine, catalogue, running_ids):
    """Return the per-cycle step budget still available."""
    norm = validate_engine(engine)
    return norm["step_budget_per_cycle"] - steps_used_per_cycle(catalogue, running_ids)


def can_load(engine, catalogue, loaded_ids, procedure_id):
    """Return (accepted, reason) for loading one procedure into the engine."""
    norm = validate_engine(engine)
    if procedure_id not in catalogue:
        raise ValueError("procedure %r is not declared" % (procedure_id,))
    procedure = catalogue[procedure_id]
    if norm["state"] != "running":
        return (False, "engine-stopped")
    if procedure_id in loaded_ids:
        return (False, "procedure-already-loaded")
    supported, reason = language_supported(
        norm, procedure["language"], procedure["language_version"]
    )
    if not supported:
        return (False, reason)
    if len(loaded_ids) >= norm["max_loaded"]:
        return (False, "loaded-procedure-limit-reached")
    if procedure["footprint_bytes"] > free_store_bytes(norm, catalogue, loaded_ids):
        return (False, "insufficient-engine-store")
    return (True, "loaded")


def can_start(engine, catalogue, loaded_ids, running_ids, procedure_id):
    """Return (accepted, reason) for starting one loaded procedure."""
    norm = validate_engine(engine)
    if procedure_id not in catalogue:
        raise ValueError("procedure %r is not declared" % (procedure_id,))
    procedure = catalogue[procedure_id]
    if norm["state"] != "running":
        return (False, "engine-stopped")
    if procedure_id not in loaded_ids:
        return (False, "procedure-not-loaded")
    if procedure_id in running_ids:
        return (False, "procedure-already-running")
    if len(running_ids) >= norm["max_running"]:
        return (False, "running-procedure-limit-reached")
    if procedure["steps_per_cycle"] > free_steps_per_cycle(
        norm, catalogue, running_ids
    ):
        return (False, "step-budget-per-cycle-exceeded")
    return (True, "running")


def engine_utilisation(engine, catalogue, loaded_ids, running_ids):
    """Return the four independent utilisation fractions of the engine."""
    norm = validate_engine(engine)
    store_used = store_used_bytes(catalogue, loaded_ids)
    steps_used = steps_used_per_cycle(catalogue, running_ids)
    return {
        "loaded_count": len(loaded_ids),
        "max_loaded": norm["max_loaded"],
        "loaded_fraction": (
            len(loaded_ids) / float(norm["max_loaded"]) if norm["max_loaded"] else None
        ),
        "running_count": len(running_ids),
        "max_running": norm["max_running"],
        "running_fraction": (
            len(running_ids) / float(norm["max_running"])
            if norm["max_running"]
            else None
        ),
        "store_used_bytes": store_used,
        "store_bytes": norm["store_bytes"],
        "store_fraction": store_used / float(norm["store_bytes"]),
        "steps_used_per_cycle": steps_used,
        "step_budget_per_cycle": norm["step_budget_per_cycle"],
        "step_fraction": steps_used / float(norm["step_budget_per_cycle"]),
    }


def apply_requests(engine, catalogue, requests, loaded_ids=None, running_ids=None):
    """Apply load and start requests in order, each graded against the last."""
    norm = validate_engine(engine)
    if not isinstance(requests, (list, tuple)):
        raise ValueError("requests must be a sequence")
    loaded = list(loaded_ids or [])
    running = list(running_ids or [])
    results = []
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("each request must be a mapping, got %r" % (request,))
        action = request.get("action")
        if action not in ("load", "start"):
            raise ValueError("action %r is not 'load' or 'start'" % (action,))
        procedure_id = request.get("procedure_id")
        if action == "load":
            accepted, reason = can_load(norm, catalogue, loaded, procedure_id)
            if accepted:
                loaded.append(procedure_id)
        else:
            accepted, reason = can_start(
                norm, catalogue, loaded, running, procedure_id
            )
            if accepted:
                running.append(procedure_id)
        results.append(
            {
                "action": action,
                "procedure_id": procedure_id,
                "accepted": accepted,
                "reason": reason,
            }
        )
    return {"results": results, "loaded_ids": loaded, "running_ids": running}


def assess_obcp_engine(spec):
    """Run the clause 6.18.2.3 engine admission assessment.

    spec keys: engine, procedures, requests (optional), loaded_ids (optional),
    running_ids (optional).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("engine", "procedures"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    engine = validate_engine(spec["engine"])
    catalogue = validate_procedure_set(spec["procedures"])
    outcome = apply_requests(
        engine,
        catalogue,
        spec.get("requests", []) or [],
        spec.get("loaded_ids"),
        spec.get("running_ids"),
    )
    utilisation = engine_utilisation(
        engine, catalogue, outcome["loaded_ids"], outcome["running_ids"]
    )
    findings = []
    for result in outcome["results"]:
        if not result["accepted"]:
            findings.append(
                "%s of procedure %s refused: %s"
                % (result["action"], result["procedure_id"], result["reason"])
            )
    accepted = sum(1 for r in outcome["results"] if r["accepted"])
    return {
        "engine_id": engine["engine_id"],
        "results": outcome["results"],
        "loaded_ids": outcome["loaded_ids"],
        "running_ids": outcome["running_ids"],
        "accepted_count": accepted,
        "refused_count": len(outcome["results"]) - accepted,
        "utilisation": utilisation,
        "findings": findings,
        "clean": not findings,
    }
