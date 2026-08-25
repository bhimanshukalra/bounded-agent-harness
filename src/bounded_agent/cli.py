import typer

app = typer.Typer(help="Bounded support-resolution agent harness.")


@app.callback()
def main() -> None:
    """CLI for running scenarios, evals, resets, and traces."""
