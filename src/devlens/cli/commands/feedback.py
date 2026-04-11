import typer


def feedback_command(latest: bool = typer.Option(True, "--latest", help="Show latest feedback.")) -> None:
    target = "latest feedback" if latest else "feedback"
    typer.echo(f"{target} stub.")
