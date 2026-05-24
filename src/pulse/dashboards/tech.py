"""Tech dashboard: tech stocks + tech news."""

from textual.app import ComposeResult

from pulse.widgets.rss import RssFeed, RssWidget
from pulse.widgets.stocks import StocksWidget, StockSymbol

TITLE = "Pulse — tech"

CSS = """
#stocks {
    height: auto;
}
#news {
    height: 1fr;
}
"""


def compose() -> ComposeResult:
    yield StocksWidget(
        symbols=[
            StockSymbol("AAPL"),
            StockSymbol("MSFT"),
            StockSymbol("GOOGL"),
            StockSymbol("NVDA"),
            StockSymbol("META"),
        ],
        title="Stocks",
        id="stocks",
    )
    yield RssWidget(
        feeds=[
            RssFeed("HN", "https://hnrss.org/frontpage"),
            RssFeed("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
            RssFeed("The Verge", "https://www.theverge.com/rss/index.xml"),
        ],
        title="News",
        id="news",
    )
