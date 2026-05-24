import httpx
from textual import work
from textual.widgets import Static, Sparkline, Label
from textual.events import MouseMove
from rich.console import Console, ConsoleOptions
from rich.segment import Segment
from rich.style import Style
from textual.renderables.sparkline import Sparkline as SparklineRenderable
from textual.renderables._blend_colors import blend_colors
from textual.app import ComposeResult


class GapSparklineRenderable(SparklineRenderable):
    def __rich_console__(self, console: Console, options: ConsoleOptions):
        width = self.width or options.max_width
        height = self.height or 1
        len_data = len(self.data)

        if len_data == 0:
            for _ in range(height - 1):
                yield Segment.line()
            yield Segment("▁" * width, self.min_color)
            return

        valid_data = [x for x in self.data if x is not None]
        if not valid_data:
            for _ in range(height - 1):
                yield Segment.line()
            yield Segment(" " * width)
            return

        bar_line_segments = len(self.BARS)
        bar_segments = bar_line_segments * height - 1
        minimum, maximum = min(valid_data), max(valid_data)
        extent = maximum - minimum or 1
        summary_function = self.summary_function
        min_color, max_color = self.min_color.color, self.max_color.color
        buckets = tuple(self._buckets(list(self.data), num_buckets=width))

        for i in reversed(range(height)):
            current_bar_part_low = i * bar_line_segments
            current_bar_part_high = (i + 1) * bar_line_segments
            bucket_index = 0.0
            bars_rendered = 0
            step = len(buckets) / width
            while bars_rendered < width:
                partition = buckets[int(bucket_index)]
                valid_partition = [x for x in partition if x is not None]
                if not valid_partition:
                    yield Segment(" ", None)
                else:
                    partition_summary = summary_function(valid_partition)
                    height_ratio = (partition_summary - minimum) / extent
                    bar_index = int(height_ratio * bar_segments)
                    if bar_index < current_bar_part_low:
                        bar = " "
                        with_color = False
                    elif bar_index >= current_bar_part_high:
                        bar = "█"
                        with_color = True
                    else:
                        bar = self.BARS[bar_index % bar_line_segments]
                        with_color = True

                    if with_color:
                        bar_color = blend_colors(min_color, max_color, height_ratio)
                        style = Style.from_color(bar_color)
                    else:
                        style = None
                    yield Segment(bar, style)

                bars_rendered += 1
                bucket_index += step
            if i > 0:
                yield Segment.line()


class GapSparkline(Sparkline):
    start_time: float = 0.0

    def on_mouse_move(self, event: MouseMove) -> None:
        import datetime
        from fractions import Fraction

        if not self.data or self.size.width == 0:
            self.tooltip = None
            return

        width = self.size.width
        bucket_step = Fraction(len(self.data), width)

        if 0 <= event.x < width:
            start_idx = int(bucket_step * event.x)
            end_idx = int(bucket_step * (event.x + 1))
            partition = self.data[start_idx:end_idx]
            valid_partition = [x for x in partition if x is not None]

            ts = self.start_time + start_idx * 3600
            dt = datetime.datetime.fromtimestamp(ts)
            time_str = dt.strftime("%b %d, %I:%M %p")

            if not valid_partition:
                self.tooltip = f"{time_str}\nMarket Closed"
            else:
                price = self.summary_function(valid_partition)
                self.tooltip = f"{time_str}\nPrice: {price:,.2f}"

    def render(self):
        data = self.data or []
        _, base = self.background_colors
        min_color = base + (
            self.get_component_styles("sparkline--min-color").color
            if self.min_color is None
            else self.min_color
        )
        max_color = base + (
            self.get_component_styles("sparkline--max-color").color
            if self.max_color is None
            else self.max_color
        )
        return GapSparklineRenderable(
            data,
            width=self.size.width,
            height=self.size.height,
            min_color=min_color.rich_color,
            max_color=max_color.rich_color,
            summary_function=self.summary_function,
        )


class EconomicWidget(Static):
    """A widget to display economic info: S&P 500 and Brent Crude with spark lines."""

    def compose(self) -> ComposeResult:
        yield Label("[bold green]S&P 500 (1 wk)[/bold green]")
        yield GapSparkline(id="sp500_sparkline", summary_function=max)
        yield Label("[bold yellow]Brent Crude (1 wk)[/bold yellow]")
        yield GapSparkline(id="brent_sparkline", summary_function=max)

    def on_mount(self) -> None:
        self.fetch_data()

    def process_data(self, data: dict) -> tuple[list[float | None], float]:
        import time

        timestamps = data["chart"]["result"][0]["timestamp"]
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        end_time = time.time()
        start_time = end_time - 7 * 24 * 3600
        num_buckets = 168
        bucketed_data = [None] * num_buckets
        for t, c in zip(timestamps, closes):
            if c is None or t < start_time:
                continue
            idx = int((t - start_time) / 3600)
            if 0 <= idx < num_buckets:
                bucketed_data[idx] = c
        return bucketed_data, start_time

    @work(exclusive=True)
    async def fetch_data(self) -> None:
        headers = {"User-Agent": "PulseDashboard/1.0"}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "https://query2.finance.yahoo.com/v8/finance/chart/^GSPC?range=7d&interval=1h",
                    headers=headers,
                )
                res.raise_for_status()
                sp500_data, start_time = self.process_data(res.json())

                res2 = await client.get(
                    "https://query2.finance.yahoo.com/v8/finance/chart/BZ=F?range=7d&interval=1h",
                    headers=headers,
                )
                res2.raise_for_status()
                brent_data, _ = self.process_data(res2.json())

                sp500_spark = self.query_one("#sp500_sparkline", GapSparkline)
                sp500_spark.start_time = start_time
                sp500_spark.data = sp500_data

                brent_spark = self.query_one("#brent_sparkline", GapSparkline)
                brent_spark.start_time = start_time
                brent_spark.data = brent_data

        except Exception as e:
            self.query_one("#sp500_sparkline", GapSparkline).display = False
            self.query_one("#brent_sparkline", GapSparkline).display = False
            self.mount(Label(f"Failed to fetch economic data: {e}", style="bold red"))
