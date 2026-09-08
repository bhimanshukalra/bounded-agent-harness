import json
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console

from bounded_agent.config import load_settings
from bounded_agent.evals import (
    EvaluationConfig,
    FixedWorkflowDecisionSource,
    VerificationRequest,
    load_all_scenarios,
    load_scenario,
    run_evaluation,
    scenario_path,
    verify_run,
)
from bounded_agent.loop import AgentRunner, RunnerConfig
from bounded_agent.state import RunStateStore, reset_scenario_environment

app = typer.Typer(help="Bounded support-resolution agent harness.")
console = Console()


@app.callback()
def main() -> None:
    """CLI for running scenarios, evals, resets, and traces."""


@app.command("run-scenario")
def run_scenario(scenario_id: str, run_id: str = "local-run") -> None:
    """Execute one deterministic bounded scenario and persist its artifacts."""
    settings = load_settings()
    path = scenario_path(scenario_id, settings)

    if not path.exists():
        console.print(f"[red]Scenario not found:[/red] {scenario_id}")
        raise typer.Exit(code=1)

    try:
        scenario = load_scenario(scenario_id, settings)
    except ValidationError as exc:
        console.print(f"[red]Scenario failed validation:[/red] {scenario_id}")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc

    trace_path = settings.runs_dir / run_id / "trace.jsonl"
    trace_path.unlink(missing_ok=True)
    runner = AgentRunner(
        FixedWorkflowDecisionSource(scenario),
        config=RunnerConfig(
            max_steps=scenario.initial_state.get("max_steps", settings.default_max_steps),
            trace_path=trace_path,
        ),
        settings=settings,
    )
    result = runner.run_scenario(scenario.id, run_id)
    render_run_result(result.terminal_result, result.db_path, settings.runs_dir / run_id / "memory")


@app.command("run-eval")
def run_eval(
    scenarios: str = "support_001",
    runners: str = "agent_loop,fixed_workflow_baseline",
    eval_run_id: str = "local-eval",
) -> None:
    """Run deterministic bounded and baseline evaluation attempts."""
    selected = [scenario_id.strip() for scenario_id in scenarios.split(",") if scenario_id.strip()]
    selected_runners = [runner_type.strip() for runner_type in runners.split(",") if runner_type.strip()]
    try:
        summary = run_evaluation(
            EvaluationConfig(
                eval_run_id=eval_run_id,
                scenario_ids=selected,
                runner_types=selected_runners,
            ),
            load_settings(),
        )
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Evaluation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Evaluation complete:[/green] {summary.eval_run_id}")
    console.print(f"Verified pass rate: {summary.metrics['verified_pass_rate']:.0%}")
    console.print(f"Artifacts: {summary.artifact_dir}")


@app.command("demo")
def demo() -> None:
    """Show the deterministic duplicate-charge demo workflow."""
    settings = load_settings()
    scenario = load_scenario("support_001", settings)
    trace_path = settings.project_root / "reports" / "demo-trace.md"

    console.print("[bold]Bounded support-resolution demo[/bold]")
    console.print(f"Scenario: {scenario.id}")
    console.print(f"Task: {scenario.task}")
    console.print("Workflow:")
    console.print(
        "Support ticket -> inspect account state -> propose safe action -> "
        "request approval when needed -> apply bounded tool call -> write trace/report."
    )
    console.print(f"Expected terminal state: {scenario.expected_terminal_state.value}")
    console.print("Expected bounded behavior: request approval before applying any refund.")
    console.print(f"Trace/report: {trace_path}")


@app.command("resume-scenario")
def resume_scenario(run_id: str) -> None:
    """Resume a nonterminal deterministic scenario from durable run state."""
    settings = load_settings()
    try:
        persisted = RunStateStore(settings.runs_dir).load(run_id)
        if persisted.scenario_id is None:
            raise ValueError("only scenario-backed runs can be resumed")
        scenario = load_scenario(persisted.scenario_id, settings)
        runner = AgentRunner(
            FixedWorkflowDecisionSource(scenario),
            config=RunnerConfig(trace_path=persisted.trace_path),
            settings=settings,
        )
        result = runner.resume_scenario(run_id)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Resume failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    render_run_result(result.terminal_result, result.db_path, settings.runs_dir / run_id / "memory")


@app.command("reset-env")
def reset_env(scenario_id: str, run_id: str = "local-reset") -> None:
    """Reset the deterministic mock environment for a scenario run."""
    try:
        result = reset_scenario_environment(scenario_id, run_id, load_settings())
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Reset failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Environment reset:[/green] {result.scenario_id}")
    console.print(f"Database: {result.db_path}")


@app.command("show-trace")
def show_trace(run_id: str, event_type: str | None = None) -> None:
    """Print persisted trace events, optionally filtered by event type."""
    persisted = load_persisted_run(run_id)
    try:
        events = [json.loads(line) for line in persisted.trace_path.read_text().splitlines() if line]
    except FileNotFoundError as exc:
        console.print(f"[red]Trace unavailable:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    selected = [event for event in events if event_type is None or event["event_type"] == event_type]
    for event in selected:
        console.print_json(json.dumps(event, sort_keys=True))
    console.print(f"Events: {len(selected)}")


@app.command("show-run")
def show_run(run_id: str) -> None:
    """Print read-only durable run-state metadata and artifact paths."""
    persisted = load_persisted_run(run_id)
    console.print_json(json.dumps(persisted.model_dump(mode="json"), sort_keys=True))


@app.command("show-memory")
def show_memory(run_id: str, artifact: str = "facts") -> None:
    """Print one read-only durable memory artifact for a run."""
    allowed = {"facts", "decisions", "open_questions", "safety", "tool_history"}
    if artifact not in allowed:
        console.print(f"[red]Unknown memory artifact:[/red] {artifact}")
        raise typer.Exit(code=1)
    suffix = "jsonl" if artifact == "tool_history" else "md"
    path = load_persisted_run(run_id).db_path.parent / "memory" / f"{artifact}.{suffix}"
    try:
        console.print(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        console.print(f"[red]Memory artifact unavailable:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("show-result")
def show_result(run_id: str) -> None:
    """Print the persisted terminal result for a run."""
    path = load_persisted_run(run_id).db_path.parent / "result.json"
    print_json_artifact(path, "Terminal result")


@app.command("show-verification")
def show_verification(run_id: str) -> None:
    """Print the persisted independent verifier result for a run."""
    settings = load_settings()
    print_json_artifact(settings.eval_runs_dir / run_id / "verification.json", "Verifier result")


@app.command("verify-run")
def verify_run_command(run_id: str, scenario_id: str | None = None) -> None:
    """Verify a completed scenario run without mutating its artifacts."""
    try:
        result = verify_run(
            VerificationRequest(run_id=run_id, scenario_id=scenario_id),
            load_settings(),
        )
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Verification failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if result.passed:
        console.print(f"[green]Verification passed:[/green] {result.run_id}")
        return
    console.print(f"[red]Verification failed:[/red] {result.run_id}")
    for failure in result.failures:
        console.print(f"- {failure}")
    raise typer.Exit(code=1)


@app.command("validate-scenarios")
def validate_scenarios() -> None:
    """Load all scenario JSON files into the Scenario model."""
    settings = load_settings()
    scenario_dir = settings.scenarios_dir
    scenario_paths = sorted(Path(scenario_dir).glob("*.json"))

    if not scenario_paths:
        console.print(f"[red]No scenario files found in:[/red] {scenario_dir}")
        raise typer.Exit(code=1)

    scenarios = load_all_scenarios(settings)
    console.print(f"[green]Validated {len(scenarios)} scenario(s).[/green]")


def load_persisted_run(run_id: str):
    try:
        return RunStateStore(load_settings().runs_dir).load(run_id)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Run unavailable:[/red] {exc}")
        raise typer.Exit(code=1) from exc


def print_json_artifact(path: Path, label: str) -> None:
    try:
        console.print_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        console.print(f"[red]{label} unavailable:[/red] {exc}")
        raise typer.Exit(code=1) from exc


def render_run_result(terminal_result, db_path: Path | None, memory_path: Path) -> None:
    console.print(f"[green]Run complete:[/green] {terminal_result.run_id}")
    console.print(f"Terminal state: {terminal_result.terminal_state.value}")
    console.print(f"Trace: {terminal_result.trace_path}")
    console.print(f"Result: {db_path.parent / 'result.json' if db_path else 'unavailable'}")
    console.print(f"Memory: {memory_path}")
