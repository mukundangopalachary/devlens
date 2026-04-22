import typer

from devlens.cli.commands.analyze import analyze_command
from devlens.cli.commands.ask import ask_command
from devlens.cli.commands.chat import chat_command
from devlens.cli.commands.doctor import doctor_command
from devlens.cli.commands.feedback import feedback_command
from devlens.cli.commands.history import history_command
from devlens.cli.commands.ingest import ingest_command
from devlens.cli.commands.reindex import reindex_command
from devlens.cli.commands.report import report_command
from devlens.cli.commands.sessions import sessions_command
from devlens.cli.commands.skills import skills_command
from devlens.cli.commands.smoke_test import smoke_test_command
from devlens.cli.commands.start import start_command
from devlens.cli.commands.tasks import tasks_command
from devlens.cli.commands.tui import tui_command
from devlens.cli.commands.verify_env import verify_env_command
from devlens.cli.commands.watch import watch_command

app = typer.Typer(help="DevLens CLI")

app.command("analyze")(analyze_command)
app.command("ask")(ask_command)
app.command("chat")(chat_command)
app.command("doctor")(doctor_command)
app.command("ingest")(ingest_command)
app.command("reindex")(reindex_command)
app.command("report")(report_command)
app.command("history")(history_command)
app.command("sessions")(sessions_command)
app.command("skills")(skills_command)
app.command("smoke-test")(smoke_test_command)
app.command("start")(start_command)
app.command("feedback")(feedback_command)
app.command("tasks")(tasks_command)
app.command("tui")(tui_command)
app.command("verify-env")(verify_env_command)
app.command("watch")(watch_command)
