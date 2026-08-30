from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console

from bounded_agent.config import load_settings
from bounded_agent.evals import load_all_scenarios, load_scenario, scenario_path

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
def run_eval() -> None:
    """Validate scenario fixtures before the eval runner is implemented."""
    scenarios = load_all_scenarios()
    console.print(f"[green]Validated {len(scenarios)} scenario(s).[/green]")
    console.print("run-eval is not implemented yet")


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
