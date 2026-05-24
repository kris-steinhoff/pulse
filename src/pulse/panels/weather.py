import httpx
from textual import work
from textual.widgets import Static
from rich.text import Text

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
