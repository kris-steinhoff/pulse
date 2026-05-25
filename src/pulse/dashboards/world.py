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
            StockSymbol("^FTSE", name="FTSE 100"),
            StockSymbol("^GDAXI", name="DAX"),
            StockSymbol("^N225", name="Nikkei 225"),
            StockSymbol("^HSI", name="Hang Seng"),
            StockSymbol("BZ=F", name="Brent Crude"),
            StockSymbol("GC=F", name="Gold"),
        ],
        title="Stocks",
        id="stocks",
    )
    yield RssWidget(
        feeds=[
            RssFeed("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml", short="BBC"),
            RssFeed(
                "Al Jazeera",
                "https://www.aljazeera.com/xml/rss/all.xml",
                short="AJ",
            ),
            RssFeed(
                "Guardian",
                "https://www.theguardian.com/world/rss",
                short="Guar",
            ),
            RssFeed(
                "NPR",
                "https://feeds.npr.org/1001/rss.xml",
                short="NPR",
            ),
            RssFeed(
                "Deutsche Welle",
                "https://rss.dw.com/rdf/rss-en-all",
                short="DW",
            ),
            RssFeed(
                "France 24",
                "https://www.france24.com/en/rss",
                short="F24",
            ),
        ],
        title="News",
        id="news",
    )
