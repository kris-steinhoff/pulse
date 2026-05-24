"""World dashboard: global indices + world news."""

from textual.app import ComposeResult

from pulse.widgets.rss import RssFeed, RssWidget
from pulse.widgets.stocks import StocksWidget, StockSymbol

TITLE = "Pulse — world"

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
            StockSymbol("^GSPC"),
            StockSymbol("^DJI"),
            StockSymbol("BZ=F", name="Brent Crude"),
            StockSymbol("GC=F", name="Gold"),
        ],
        id="stocks",
    )
    yield RssWidget(
        title="World News",
        feeds=[
            RssFeed(
                "NYT World",
                "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            ),
            RssFeed("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ],
        id="news",
    )
