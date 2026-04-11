import typer

from devlens.cli.commands.analyze import analyze_command
from devlens.cli.commands.feedback import feedback_command
from devlens.cli.commands.history import history_command
from devlens.cli.commands.skills import skills_command

app = typer.Typer(help="DevLens CLI")

app.command("analyze")(analyze_command)
app.command("history")(history_command)
app.command("skills")(skills_command)
app.command("feedback")(feedback_command)

