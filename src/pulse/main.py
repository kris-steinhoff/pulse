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
            "  ?         Show this help\n"
            "  d         Toggle dark mode\n"
            "  r         Refresh data\n"
            "  q / Esc   Quit (or close help)\n\n"
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
        ("r", "refresh_data", "Refresh"),
    ]

    def __init__(self, dashboard_name: str, refresh_interval: float) -> None:
        self.dashboard = dashboards.load(dashboard_name)
        self.CSS = getattr(self.dashboard, "CSS", "")
        self.refresh_interval_seconds = refresh_interval
        super().__init__()
        self.title = getattr(self.dashboard, "TITLE", f"Pulse — {dashboard_name}")

    def compose(self) -> ComposeResult:
        yield from self.dashboard.compose()

    def on_mount(self) -> None:
        self.set_interval(self.refresh_interval_seconds, self.action_refresh_data)

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_refresh_data(self) -> None:
        for node in self.query("*"):
            refresh = getattr(node, "refresh_data", None)
            if callable(refresh):
                refresh()


@cli.command()
def run(
    dashboard: str = typer.Argument(
        ...,
        help=f"Dashboard to show. One of: {', '.join(dashboards.AVAILABLE)}",
    ),
    refresh_interval: float = typer.Option(
        5.0,
        "--refresh-interval",
        help="Auto-refresh interval in minutes.",
        min=0.1,
    ),
) -> None:
    """Run the Pulse dashboard."""
    if dashboard not in dashboards.AVAILABLE:
        raise typer.BadParameter(
            f"Unknown dashboard '{dashboard}'. Available: {', '.join(dashboards.AVAILABLE)}"
        )
    PulseDashboard(dashboard, refresh_interval * 60).run()


def main():
    cli()


if __name__ == "__main__":
    main()
