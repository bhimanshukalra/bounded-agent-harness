import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from bounded_agent.domain import AgentState


class StrictRunState(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PersistedRunState(StrictRunState):
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    ticket_id: str = Field(min_length=1)
    scenario_id: str | None = None
    db_path: Path
    trace_path: Path
    agent_state: AgentState
    observations: list[dict[str, Any]] = Field(default_factory=list)
    terminal: bool = False


class RunStateStore:
    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir

    def path_for(self, run_id: str) -> Path:
        return self.runs_dir / run_id / "state.json"

    def save(self, state: PersistedRunState) -> Path:
        path = self.path_for(state.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(state.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
        return path

    def load(self, run_id: str) -> PersistedRunState:
        path = self.path_for(run_id)
        if not path.exists():
            raise FileNotFoundError(f"persisted run state was not found: {path}")
        persisted = PersistedRunState.model_validate_json(path.read_text(encoding="utf-8"))
        if persisted.run_id != run_id:
            raise ValueError("persisted run state run_id does not match requested run_id")
        return persisted
