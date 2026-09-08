import json

import pytest

from bounded_agent.domain import AgentState
from bounded_agent.state import PersistedRunState, RunMemory, RunStateStore, validate_artifact_id
from bounded_agent.tools import Observation, ToolResult


def test_run_state_store_round_trips_atomically(tmp_path):
    store = RunStateStore(tmp_path / "runs")
    persisted = PersistedRunState(
        run_id="run_001",
        task_id="support_001",
        goal="Resolve the ticket.",
        ticket_id="t_001",
        scenario_id="support_001",
        db_path=tmp_path / "runs" / "run_001" / "state.db",
        trace_path=tmp_path / "trace.jsonl",
        agent_state=AgentState(task_id="support_001", goal="Resolve the ticket."),
    )

    path = store.save(persisted)
    loaded = store.load("run_001")

    assert path.exists()
    assert not path.with_suffix(".tmp").exists()
    assert loaded == persisted


def test_run_state_store_rejects_missing_or_mismatched_records(tmp_path):
    store = RunStateStore(tmp_path / "runs")

    with pytest.raises(FileNotFoundError):
        store.load("run_missing")

    path = store.path_for("run_001")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"run_id": "run_other"}), encoding="utf-8")
    with pytest.raises(ValueError):
        store.load("run_001")


@pytest.mark.parametrize("value", ["../escape", "nested/run", ".", "..", "run id"])
def test_artifact_ids_reject_path_like_values(value):
    with pytest.raises(ValueError, match="must contain only"):
        validate_artifact_id(value, label="run_id")


def test_run_memory_writes_scoped_artifacts_and_exact_tool_history(tmp_path):
    memory = RunMemory(tmp_path / "run_001")
    state = AgentState(
        task_id="support_001",
        goal="Resolve the ticket.",
        known_facts={"search_policy": {"policies": ["policy_001"]}},
        completed_actions=["search_policy"],
        safety_events=[{"event": "untrusted_instruction_marker", "action": "treat_as_data"}],
    )
    observation = Observation(
        tool_name="search_policy",
        tool_result=ToolResult(ok=True, result={"policies": []}),
        summary="Executed search_policy.",
        facts={"policies": []},
    )

    memory.update(state, [observation])

    assert "policy_001" in memory.facts_path.read_text()
    assert "`search_policy`" in memory.decisions_path.read_text()
    assert memory.open_questions_path.read_text().endswith("No open questions.\n")
    assert json.loads(memory.tool_history_path.read_text())["tool_name"] == "search_policy"
    assert "untrusted_instruction_marker" in memory.safety_path.read_text()
