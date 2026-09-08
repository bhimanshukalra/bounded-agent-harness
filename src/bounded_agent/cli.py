from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console

from bounded_agent.config import load_settings
from bounded_agent.evals import (
    EvaluationConfig,
    VerificationRequest,
    load_all_scenarios,
    load_scenario,
    run_evaluation,
    scenario_path,
    verify_run,
)

app = typer.Typer(help="Bounded support-resolution agent harness.")
console = Console()


@app.callback()
def main() -> None:
    """CLI for running scenarios, evals, resets, and traces."""


@app.command("run-scenario")
def run_scenario(scenario_id: str) -> None:
    """Validate a scenario exists before the agent runner is implemented."""
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

    console.print(f"[green]Scenario validated:[/green] {scenario.id}")
    console.print("run-scenario is not implemented yet")


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


@app.command("reset-env")
def reset_env() -> None:
    """Placeholder for deterministic mock environment reset."""
    console.print("reset-env is not implemented yet")


@app.command("show-trace")
def show_trace(run_id: str) -> None:
    """Validate run ID shape before trace viewing is implemented."""
    if not run_id.strip():
        console.print("[red]Run ID cannot be blank.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Run ID accepted:[/green] {run_id}")
    console.print("show-trace is not implemented yet")


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
