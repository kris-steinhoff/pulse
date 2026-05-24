from datetime import datetime

import typer
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from pulse.panels.weather import WeatherPanel
from pulse.panels.economic import EconomicPanel
from pulse.panels.rss import RssFeed, RssPanel

cli = typer.Typer(help="Pulse: A personal dashboard")


class HelpScreen(ModalScreen):
    """Modal showing keybindings and panel info."""

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
            "[b]Panels[/b]\n"
            "  Weather  NWS forecast for Ann Arbor\n"
            "  Economic S&P 500 and Brent Crude, 7-day sparklines\n"
            "  RSS      Headlines from configured feeds\n\n"
            f"[dim]{now}[/dim]"
        )
        with Vertical(id="help-box"):
            yield Static("Pulse — Help", id="help-title")
            yield Static(body)


class PulseDashboard(App):
    """A Textual app for the Pulse dashboard."""

    CSS = """
    WeatherPanel, EconomicPanel, RssPanel {
        width: 1fr;
    }
    """

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("question_mark", "help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Horizontal():
            yield WeatherPanel(id="weather_panel")
            yield EconomicPanel(id="economic_panel")
            yield RssPanel(
                title="News",
                feeds=[
                    RssFeed("HN", "https://hnrss.org/frontpage"),
                    RssFeed(
                        "NYT",
                        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
                    ),
                ],
                id="news_panel",
            )

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_help(self) -> None:
        self.push_screen(HelpScreen())


@cli.command()
def run():
    """Run the Pulse dashboard."""
    app = PulseDashboard()
    app.run()


def main():
    cli()


if __name__ == "__main__":
    main()
