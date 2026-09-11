"""
e1011_verif_sim_logic.py
ECSS-E-ST-10-11C §4.11.4 — HFE verification via crew-in-the-loop simulation.
stdlib only; offline; deterministic.
"""

VALID_PARTICIPANT_ROLES = frozenset({
    "commander", "pilot", "mission-specialist",
    "flight-engineer", "payload-specialist",
})

WORKLOAD_SCALE_MIN = 1
WORKLOAD_SCALE_MAX = 10

DEFAULT_MIN_TASK_COMPLETION = 0.90
DEFAULT_MAX_ERROR_RATE = 0.10
DEFAULT_MAX_WORKLOAD = 7.0


class SimulationError(ValueError):
    """Raised when inputs violate the simulation verification model."""


class Scenario:
    """A single crew-in-the-loop simulation scenario with acceptance criteria."""

    def __init__(
        self,
        scenario_id,
        tasks,
        required_participant_count,
        min_task_completion=None,
        max_error_rate=None,
        max_workload_rating=None,
    ):
        if not scenario_id or not isinstance(scenario_id, str):
            raise SimulationError("scenario_id must be a non-empty string")
        if not tasks or not isinstance(tasks, list):
            raise SimulationError(
                f"Scenario {scenario_id}: tasks must be a non-empty list"
            )
        if (
            not isinstance(required_participant_count, int)
            or required_participant_count < 1
        ):
            raise SimulationError(
                f"Scenario {scenario_id}: required_participant_count must be a positive integer"
            )

        self.scenario_id = scenario_id
        self.tasks = list(tasks)
        self.required_participant_count = required_participant_count
        self.min_task_completion = (
            min_task_completion
            if min_task_completion is not None
            else DEFAULT_MIN_TASK_COMPLETION
        )
        self.max_error_rate = (
            max_error_rate
            if max_error_rate is not None
            else DEFAULT_MAX_ERROR_RATE
        )
        self.max_workload_rating = (
            max_workload_rating
            if max_workload_rating is not None
            else DEFAULT_MAX_WORKLOAD
        )


class Participant:
    """A crew participant in the simulation."""

    def __init__(self, participant_id, role, qualified):
        if not participant_id or not isinstance(participant_id, str):
            raise SimulationError("participant_id must be a non-empty string")
        if role not in VALID_PARTICIPANT_ROLES:
            raise SimulationError(
                f"Unknown participant role '{role}'. "
                f"Valid roles: {sorted(VALID_PARTICIPANT_ROLES)}"
            )
        if not isinstance(qualified, bool):
            raise SimulationError(
                f"Participant {participant_id}: qualified must be a bool"
            )
        self.participant_id = participant_id
        self.role = role
        self.qualified = qualified


class ScenarioResult:
    """Aggregated performance data recorded after a scenario run."""

    def __init__(
        self,
        scenario_id,
        participant_ids,
        task_completion_rate,
        error_rate,
        workload_ratings,
    ):
        if not scenario_id or not isinstance(scenario_id, str):
            raise SimulationError("scenario_id must be a non-empty string")
        if not isinstance(participant_ids, list) or not participant_ids:
            raise SimulationError(
                f"Result for {scenario_id}: participant_ids must be a non-empty list"
            )
        if not isinstance(task_completion_rate, (int, float)) or not (
            0.0 <= task_completion_rate <= 1.0
        ):
            raise SimulationError(
                f"Result for {scenario_id}: task_completion_rate must be in [0, 1]"
            )
        if not isinstance(error_rate, (int, float)) or not (
            0.0 <= error_rate <= 1.0
        ):
            raise SimulationError(
                f"Result for {scenario_id}: error_rate must be in [0, 1]"
            )
        if not isinstance(workload_ratings, list) or not workload_ratings:
            raise SimulationError(
                f"Result for {scenario_id}: workload_ratings must be a non-empty list"
            )
        for rating in workload_ratings:
            if not isinstance(rating, (int, float)) or not (
                WORKLOAD_SCALE_MIN <= rating <= WORKLOAD_SCALE_MAX
            ):
                raise SimulationError(
                    f"Result for {scenario_id}: workload rating {rating} out of "
                    f"range [{WORKLOAD_SCALE_MIN}, {WORKLOAD_SCALE_MAX}]"
                )

        self.scenario_id = scenario_id
        self.participant_ids = list(participant_ids)
        self.task_completion_rate = task_completion_rate
        self.error_rate = error_rate
        self.workload_ratings = list(workload_ratings)


def check_participant_qualifications(participants):
    """Return a list of participant IDs that are not qualified."""
    return [p.participant_id for p in participants if not p.qualified]


def check_scenario_coverage(scenarios, results):
    """Return a list of scenario IDs for which no result record exists."""
    result_ids = {r.scenario_id for r in results}
    return [s.scenario_id for s in scenarios if s.scenario_id not in result_ids]


def count_qualified_in_result(result, qualified_ids):
    """Return the count of participants in the result who are qualified."""
    return sum(1 for pid in result.participant_ids if pid in qualified_ids)


def evaluate_scenario_result(scenario, result, qualified_ids):
    """
    Evaluate a ScenarioResult against the Scenario acceptance criteria.

    Returns a dict:
      passed      : bool
      findings    : list[str]  (empty when passed)
      mean_workload: float
    """
    findings = []

    if result.task_completion_rate < scenario.min_task_completion:
        findings.append(
            f"Task completion {result.task_completion_rate:.2%} is below "
            f"threshold {scenario.min_task_completion:.2%}"
        )

    if result.error_rate > scenario.max_error_rate:
        findings.append(
            f"Error rate {result.error_rate:.2%} exceeds threshold "
            f"{scenario.max_error_rate:.2%}"
        )

    mean_workload = sum(result.workload_ratings) / len(result.workload_ratings)
    if mean_workload > scenario.max_workload_rating:
        findings.append(
            f"Mean workload {mean_workload:.2f} exceeds threshold "
            f"{scenario.max_workload_rating:.2f}"
        )

    qualified_count = count_qualified_in_result(result, qualified_ids)
    if qualified_count < scenario.required_participant_count:
        findings.append(
            f"Insufficient qualified participants: required "
            f"{scenario.required_participant_count}, found {qualified_count}"
        )

    return {
        "passed": len(findings) == 0,
        "findings": findings,
        "mean_workload": mean_workload,
    }


def run_simulation_verification(scenarios, participants, results):
    """
    Execute the full ECSS-E-ST-10-11C §4.11.4 simulation verification.

    Parameters
    ----------
    scenarios    : list[Scenario]
    participants : list[Participant]
    results      : list[ScenarioResult]

    Returns
    -------
    dict with keys:
      overall_passed          : bool
      unqualified_participants: list[str]   participant IDs
      uncovered_scenarios     : list[str]   scenario IDs with no result
      scenario_reports        : list[dict]  per-scenario evaluation
    """
    if not scenarios:
        raise SimulationError("At least one scenario is required")
    if not participants:
        raise SimulationError("At least one participant is required")
    if not results:
        raise SimulationError("At least one simulation result is required")

    scenario_ids = [s.scenario_id for s in scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise SimulationError("Duplicate scenario IDs detected in scenario list")

    qualified_ids = frozenset(
        p.participant_id for p in participants if p.qualified
    )
    unqualified = check_participant_qualifications(participants)
    uncovered = check_scenario_coverage(scenarios, results)

    result_map = {r.scenario_id: r for r in results}
    scenario_map = {s.scenario_id: s for s in scenarios}

    scenario_reports = []
    for sid, scenario in scenario_map.items():
        if sid not in result_map:
            continue
        eval_out = evaluate_scenario_result(scenario, result_map[sid], qualified_ids)
        scenario_reports.append(
            {
                "scenario_id": sid,
                "passed": eval_out["passed"],
                "findings": eval_out["findings"],
                "mean_workload": eval_out["mean_workload"],
            }
        )

    overall_passed = (
        len(unqualified) == 0
        and len(uncovered) == 0
        and all(sr["passed"] for sr in scenario_reports)
    )

    return {
        "overall_passed": overall_passed,
        "unqualified_participants": unqualified,
        "uncovered_scenarios": uncovered,
        "scenario_reports": scenario_reports,
    }
