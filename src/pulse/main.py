import atexit
import signal
from datetime import datetime

import typer
from rich.markdown import Markdown
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from pulse import dashboards
from pulse.ai import ApfelServer

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
            "  a         AI summary\n"
            "  r         Refresh data\n"
            "  q / Esc   Quit (or close help)\n\n"
            f"[dim]{now}[/dim]"
        )
        with Vertical(id="help-box"):
            yield Static("Help", id="help-title")
            yield Static(body)


class AiSummaryScreen(ModalScreen):
    """Modal that asks the local apfel server to summarize current data."""

    BINDINGS = [
        Binding("escape,a,q", "dismiss", "Close"),
    ]

    CSS = """
    AiSummaryScreen {
        align: center middle;
    }
    #ai-box {
        width: 80;
        height: 24;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    #ai-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #ai-scroll {
        height: 1fr;
        scrollbar-size-vertical: 1;
    }
    #ai-body {
        height: auto;
    }
    """

    def __init__(self, server: ApfelServer, snapshot_text: str) -> None:
        super().__init__()
        self._server = server
        self._snapshot_text = snapshot_text

    def compose(self) -> ComposeResult:
        with Vertical(id="ai-box"):
            yield Static("AI Summary", id="ai-title")
            with VerticalScroll(id="ai-scroll", can_focus=True):
                yield Static("Generating summary…", id="ai-body")

    def on_mount(self) -> None:
        self.query_one("#ai-scroll", VerticalScroll).focus()
        self.generate()

    @work
    async def generate(self) -> None:
        body = self.query_one("#ai-body", Static)
        try:
            summary = await self._server.summarize(self._snapshot_text)
        except Exception as exc:
            body.update(Text(f"AI summary failed: {exc}", style="bold red"))
            return
        body.update(Markdown(summary))


class PulseDashboard(App):
    """A Textual app for the Pulse dashboard."""

    BINDINGS = [
        ("a", "ai_summary", "AI summary"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("question_mark", "help", "Help"),
        ("r", "refresh_data", "Refresh"),
    ]

    def __init__(self, dashboard_name: str, refresh_interval: float) -> None:
        self.dashboard = dashboards.load(dashboard_name)
        self.CSS = getattr(self.dashboard, "CSS", "")
        self.refresh_interval_seconds = refresh_interval
        self.ai_server = ApfelServer()
        super().__init__()
        self.title = getattr(self.dashboard, "TITLE", f"Pulse — {dashboard_name}")

    def compose(self) -> ComposeResult:
        yield from self.dashboard.compose()

    def on_mount(self) -> None:
        self.set_interval(self.refresh_interval_seconds, self.action_refresh_data)

    def on_unmount(self) -> None:
        self.ai_server.stop()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_ai_summary(self) -> None:
        self.push_screen(AiSummaryScreen(self.ai_server, self._collect_snapshot()))

    def action_refresh_data(self) -> None:
        for node in self.query("*"):
            refresh = getattr(node, "refresh_data", None)
            if callable(refresh):
                refresh()

    def _collect_snapshot(self) -> str:
        sections: list[str] = [f"# {self.title}"]
        seen: set[int] = set()
        for node in self.query("*"):
            snapshot = getattr(node, "snapshot", None)
            if not callable(snapshot) or id(node) in seen:
                continue
            seen.add(id(node))
            try:
                text = snapshot()
            except Exception as exc:
                text = f"(snapshot failed: {exc})"
            if text:
                sections.append(text)
        return "\n\n".join(sections)


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
    app = PulseDashboard(dashboard, refresh_interval * 60)
    atexit.register(app.ai_server.stop)

    def _terminate(signum: int, frame: object) -> None:
        app.ai_server.stop()
        raise SystemExit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(sig, _terminate)
        except (ValueError, OSError):
            pass

    app.ai_server.start()
    try:
        app.run()
    finally:
        app.ai_server.stop()


def main():
    cli()


if __name__ == "__main__":
    main()
