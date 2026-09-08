import json
from pathlib import Path
from typing import Any

from bounded_agent.domain import AgentState


class RunMemory:
    def __init__(self, run_dir: Path) -> None:
        self.directory = run_dir / "memory"

    @property
    def facts_path(self) -> Path:
        return self.directory / "facts.md"

    @property
    def decisions_path(self) -> Path:
        return self.directory / "decisions.md"

    @property
    def open_questions_path(self) -> Path:
        return self.directory / "open_questions.md"

    @property
    def tool_history_path(self) -> Path:
        return self.directory / "tool_history.jsonl"

    @property
    def safety_path(self) -> Path:
        return self.directory / "safety.md"

    def update(self, state: AgentState, observations: list[Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self.facts_path.write_text(render_facts(state), encoding="utf-8")
        self.decisions_path.write_text(render_decisions(state), encoding="utf-8")
        self.open_questions_path.write_text(render_open_questions(observations), encoding="utf-8")
        self.tool_history_path.write_text(render_tool_history(observations), encoding="utf-8")
        self.safety_path.write_text(render_safety_events(state), encoding="utf-8")


def render_facts(state: AgentState) -> str:
    lines = ["# Facts", ""]
    for tool_name, facts in sorted(state.known_facts.items()):
        lines.append(f"## {tool_name}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(facts, indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def render_decisions(state: AgentState) -> str:
    lines = ["# Decisions", ""]
    for index, action in enumerate(state.completed_actions, start=1):
        lines.append(f"{index}. `{action}`")
    for approval_id in state.pending_approval_ids:
        lines.append(f"- Pending approval: `{approval_id}`")
    if len(lines) == 2:
        lines.append("No durable decisions recorded.")
    lines.append("")
    return "\n".join(lines)


def render_open_questions(observations: list[Any]) -> str:
    lines = ["# Open Questions", ""]
    for observation in observations:
        if observation.tool_result.error is not None:
            lines.append(f"- `{observation.tool_name}`: {observation.tool_result.error.message}")
    if len(lines) == 2:
        lines.append("No open questions.")
    lines.append("")
    return "\n".join(lines)


def render_tool_history(observations: list[Any]) -> str:
    return "".join(
        json.dumps(observation.model_dump(mode="json"), sort_keys=True) + "\n"
        for observation in observations
    )


def render_safety_events(state: AgentState) -> str:
    lines = ["# Safety Events", ""]
    for event in state.safety_events:
        lines.append("```json")
        lines.append(json.dumps(event, indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")
    if len(lines) == 2:
        lines.append("No safety events recorded.")
        lines.append("")
    return "\n".join(lines)
