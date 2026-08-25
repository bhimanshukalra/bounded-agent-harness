import json
from pathlib import Path

from bounded_agent.domain import Scenario

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "data" / "scenarios"


def scenario_paths() -> list[Path]:
    return sorted(SCENARIOS_DIR.glob("support_*.json"))


def load_scenario(path: Path) -> Scenario:
    return Scenario.model_validate_json(path.read_text())


def test_expected_scenario_files_exist():
    assert [path.name for path in scenario_paths()] == [
        "support_001.json",
        "support_002.json",
        "support_003.json",
        "support_004.json",
        "support_005.json",
        "support_006.json",
        "support_007.json",
        "support_008.json",
        "support_009.json",
        "support_010.json",
    ]


def test_scenario_ids_match_filenames():
    for path in scenario_paths():
        scenario = load_scenario(path)

        assert scenario.id == path.stem


def test_all_scenarios_load_into_model():
    scenarios = [load_scenario(path) for path in scenario_paths()]

    assert len(scenarios) == 10
    assert all(scenario.expected_terminal_state for scenario in scenarios)


def test_scenario_required_grading_fields_are_non_empty():
    for path in scenario_paths():
        raw = json.loads(path.read_text())
        scenario = Scenario.model_validate(raw)

        assert scenario.task
        assert scenario.expected_actions
        assert scenario.forbidden_actions
        assert scenario.tags
        assert scenario.grading_rubric


def test_scenario_dataset_covers_required_phase_zero_cases():
    scenarios = [load_scenario(path) for path in scenario_paths()]
    tags = {tag.value for scenario in scenarios for tag in scenario.tags}

    assert {
        "happy_path",
        "approval",
        "approval_denied",
        "missing_info",
        "ambiguous_policy",
        "tool_error",
        "retry",
        "idempotency",
        "prompt_injection",
        "budget",
        "escalation",
    }.issubset(tags)
