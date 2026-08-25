from pathlib import Path

from bounded_agent.config import Settings, load_settings
from bounded_agent.domain import Scenario


def scenario_path(scenario_id: str, settings: Settings | None = None) -> Path:
    active_settings = settings or load_settings()
    return active_settings.scenarios_dir / f"{scenario_id}.json"


def load_scenario(scenario_id: str, settings: Settings | None = None) -> Scenario:
    path = scenario_path(scenario_id, settings)
    return Scenario.model_validate_json(path.read_text())


def load_all_scenarios(settings: Settings | None = None) -> list[Scenario]:
    active_settings = settings or load_settings()
    return [
        Scenario.model_validate_json(path.read_text())
        for path in sorted(active_settings.scenarios_dir.glob("*.json"))
    ]
