from dataclasses import dataclass
import httpx
from textual import work
from textual.widgets import Static, Sparkline, Label
from textual.containers import Horizontal
from textual.events import MouseMove
from rich.console import Console, ConsoleOptions
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.renderables.sparkline import Sparkline as SparklineRenderable
from textual.renderables._blend_colors import blend_colors
from textual.app import ComposeResult


@dataclass
class StockSymbol:
    symbol: str
    name: str | None = None


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
    currency: str = ""

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
                self.tooltip = time_str
            else:
                price = self.summary_function(valid_partition)
                suffix = f" {self.currency}" if self.currency else ""
                self.tooltip = f"{time_str}\nPrice: {price:,.2f}{suffix}"

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


MAX_NAME_LEN = 20


def _truncate(name: str) -> str:
    if len(name) <= MAX_NAME_LEN:
        return name
    return name[: MAX_NAME_LEN - 1] + "…"


class StocksWidget(Static):
    """A widget to display stock symbols with spark lines."""

    DEFAULT_CSS = """
    StocksWidget #stocks-title {
        text-style: bold;
        color: $accent;
    }
    StocksWidget .stock-row {
        height: 1;
    }
    StocksWidget .stock-row Label {
        width: 22;
    }
    StocksWidget .stock-row GapSparkline {
        width: 1fr;
        height: 1;
    }
    StocksWidget Horizontal.stock-row > Label.exchange {
        width: 8;
        min-width: 8;
        color: cyan;
        content-align: right middle;
        text-align: right;
        padding: 0 1 0 2;
    }
    """

    def __init__(
        self,
        symbols: list[StockSymbol],
        *args,
        title: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.symbols = symbols
        self.widget_title = title

    def compose(self) -> ComposeResult:
        if self.widget_title:
            yield Label(self.widget_title, id="stocks-title")
        for i, symbol in enumerate(self.symbols):
            display_name = _truncate(symbol.name or symbol.symbol)
            with Horizontal(classes="stock-row"):
                yield Label(display_name, id=f"label_{i}")
                yield GapSparkline(
                    id=f"spark_{i}",
                    summary_function=lambda v: sum(v) / len(v),
                )
                yield Label("", id=f"exchange_{i}", classes="exchange")

    def on_mount(self) -> None:
        self.fetch_data()

    def refresh_data(self) -> None:
        self.fetch_data()

    def process_data(self, data: dict) -> tuple[list[float | None], float]:
        import time

        num_buckets = 168
        start_time = (int(time.time()) // 3600 - (num_buckets - 1)) * 3600

        try:
            timestamps = data["chart"]["result"][0]["timestamp"]
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        except (KeyError, IndexError, TypeError):
            return [None] * num_buckets, start_time

        buckets: list[list[float]] = [[] for _ in range(num_buckets)]
        for t, c in zip(timestamps, closes):
            if c is None or t < start_time:
                continue
            idx = int((t - start_time) // 3600)
            if 0 <= idx < num_buckets:
                buckets[idx].append(c)
        bucketed_data = [(sum(b) / len(b)) if b else None for b in buckets]
        return bucketed_data, start_time

    @work(exclusive=True)
    async def fetch_data(self) -> None:
        headers = {"User-Agent": "PulseDashboard/1.0"}
        async with httpx.AsyncClient() as client:
            for i, symbol in enumerate(self.symbols):
                try:
                    res = await client.get(
                        f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol.symbol}?range=7d&interval=1h",
                        headers=headers,
                    )
                    res.raise_for_status()
                    data_json = res.json()
                    data_points, start_time = self.process_data(data_json)

                    meta = data_json["chart"]["result"][0].get("meta", {})
                    if symbol.name is None:
                        fetched_name = (
                            meta.get("shortName")
                            or meta.get("longName")
                            or symbol.symbol
                        )
                        label = self.query_one(f"#label_{i}", Label)
                        label.update(_truncate(fetched_name))

                    exchange = meta.get("exchangeName") or meta.get("fullExchangeName")
                    if exchange:
                        badge = self.query_one(f"#exchange_{i}", Label)
                        badge.update(Text(exchange[:5]))
                        full = meta.get("fullExchangeName") or exchange
                        badge.tooltip = full

                    spark = self.query_one(f"#spark_{i}", GapSparkline)
                    spark.start_time = start_time
                    spark.currency = meta.get("currency", "")
                    spark.data = data_points

                except Exception as e:
                    try:
                        self.query_one(f"#spark_{i}", GapSparkline).display = False
                    except Exception:
                        pass
                    self.mount(
                        Label(f"Failed to fetch {symbol.name}: {e}", style="bold red")
                    )
