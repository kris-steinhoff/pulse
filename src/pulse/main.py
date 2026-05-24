import typer
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from rich.text import Text

cli = typer.Typer(help="Pulse: A personal dashboard")


class PulseDashboard(App):
    """A Textual app for the Pulse dashboard."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Static(
            Text("Hello World!", style="bold magenta", justify="center"), id="hello"
        )
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark


@cli.command()
def run():
    """Run the Pulse dashboard."""
    app = PulseDashboard()
    app.run()


def main():
    cli()


if __name__ == "__main__":
    main()
