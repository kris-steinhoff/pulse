import typer
import httpx
from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Container
from rich.text import Text

cli = typer.Typer(help="Pulse: A personal dashboard")


class WeatherPanel(Static):
    """A widget to display current weather in Ann Arbor, MI."""

    def on_mount(self) -> None:
        self.update("Fetching weather for Ann Arbor, MI...")
        self.fetch_weather()

    @work(exclusive=True)
    async def fetch_weather(self) -> None:
        headers = {"User-Agent": "PulseDashboard/1.0"}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "https://api.weather.gov/points/42.2808,-83.7430", headers=headers
                )
                res.raise_for_status()
                data = res.json()

                hourly_url = data["properties"]["forecastHourly"]
                res2 = await client.get(hourly_url, headers=headers)
                res2.raise_for_status()
                forecast = res2.json()

                current = forecast["properties"]["periods"][0]
                temp = current.get("temperature", "N/A")
                unit = current.get("temperatureUnit", "F")
                wind = current.get("windSpeed", "N/A")
                cond = current.get("shortForecast", "N/A")

                weather_text = Text()
                weather_text.append("Ann Arbor Weather\n", style="bold cyan")
                weather_text.append(f"{cond}\n")
                weather_text.append(f"Temperature: {temp}°{unit}\n")
                weather_text.append(f"Wind Speed: {wind}")

                self.update(weather_text)
        except Exception as e:
            self.update(Text(f"Failed to fetch weather: {e}", style="bold red"))


class PulseDashboard(App):
    """A Textual app for the Pulse dashboard."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container():
            yield WeatherPanel(id="weather_panel")
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
