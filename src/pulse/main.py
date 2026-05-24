from datetime import datetime

import typer
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from pulse import dashboards

cli = typer.Typer(help="Pulse: A personal dashboard")


class HelpScreen(ModalScreen):
    """Modal showing keybindings and widget info."""

    BINDINGS = [
        Binding("question_mark,escape,q", "dismiss", "Close"),
    ]

    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-box {
        width: 60;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    #help-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = (
            "[b]Keybindings[/b]\n"
            "  ?        Show this help\n"
            "  d        Toggle dark mode\n"
            "  q / Esc  Quit (or close help)\n\n"
            f"[dim]{now}[/dim]"
        )
        with Vertical(id="help-box"):
            yield Static("Pulse — Help", id="help-title")
            yield Static(body)


class PulseDashboard(App):
    """A Textual app for the Pulse dashboard."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("question_mark", "help", "Help"),
    ]

    def __init__(self, dashboard_name: str) -> None:
        self.dashboard = dashboards.load(dashboard_name)
        self.CSS = getattr(self.dashboard, "CSS", "")
        super().__init__()
        self.title = getattr(self.dashboard, "TITLE", f"Pulse — {dashboard_name}")

    def compose(self) -> ComposeResult:
        yield from self.dashboard.compose()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_help(self) -> None:
        self.push_screen(HelpScreen())


@cli.command()
def run(
    dashboard: str = typer.Argument(
        ...,
        help=f"Dashboard to show. One of: {', '.join(dashboards.AVAILABLE)}",
    ),
) -> None:
    """Run the Pulse dashboard."""
    if dashboard not in dashboards.AVAILABLE:
        raise typer.BadParameter(
            f"Unknown dashboard '{dashboard}'. Available: {', '.join(dashboards.AVAILABLE)}"
        )
    PulseDashboard(dashboard).run()


def main():
    cli()


if __name__ == "__main__":
    main()
