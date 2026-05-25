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
            StockSymbol("TSM", name="TSMC"),
            StockSymbol("ASML"),
            StockSymbol("005930.KS", name="Samsung"),
            StockSymbol("9988.HK", name="Alibaba"),
        ],
        title="Stocks",
        id="stocks",
    )
    yield RssWidget(
        feeds=[
            RssFeed("HN", "https://hnrss.org/frontpage", short="HN"),
            RssFeed(
                "Ars Technica",
                "https://feeds.arstechnica.com/arstechnica/index",
                short="Ars",
            ),
            RssFeed(
                "The Verge", "https://www.theverge.com/rss/index.xml", short="Verge"
            ),
        ],
        title="News",
        id="news",
    )
